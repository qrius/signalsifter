#!/usr/bin/env python3
"""
Channel-level summarizer (hybrid format: 1-line + bullets)
- Loads messages from SQLite for a channel and time window
- Chunks by time-window (DEFAULT_CHUNK_DAYS from .env)
- Calls LLM in batches (pluggable: OpenAI used by default)
- Produces a Markdown report and stores it in summaries table
Usage:
  python summarizer.py --channel_id <tg_id_or_username> --window-days 7 --out ./data/summaries/channel_<id>.md
"""
import os
import sqlite3
import argparse
from dotenv import load_dotenv
from datetime import datetime, timedelta
import openai
import textwrap
import requests
import re
from collections import Counter

load_dotenv()
DB_PATH = os.getenv("SQLITE_DB_PATH", "./data/backfill.sqlite")
DEFAULT_CHUNK_DAYS = int(os.getenv("DEFAULT_CHUNK_DAYS", 7))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "hf")  # options: openai, hf, local
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_MODEL = os.getenv("HF_MODEL", "gpt2")
BOT_NAME = os.getenv("BOT_NAME", "SignalSifter")
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

def fetch_messages(channel_id, since=None, until=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    q = "SELECT message_id, sender_username, date, text FROM messages WHERE channel_id = ?"
    params = [channel_id]
    if since:
        q += " AND date >= ?"
        params.append(since.isoformat())
    if until:
        q += " AND date <= ?"
        params.append(until.isoformat())
    q += " ORDER BY date"
    cur.execute(q, params)
    rows = cur.fetchall()
    conn.close()
    return rows

def make_prompt(messages_chunk):
    # Simple prompt template for hybrid summary
    system = "You are a concise analyst that summarizes Telegram channel crypto announcements. Output a 1-line summary and 3-6 bullet points with dates, contract addresses, projects, and important facts."
    user = "Messages:\n\n"
    for mid, usern, date, text in messages_chunk:
        # keep message short
        snippet = (text or "").strip().replace("\n", " ")
        if len(snippet) > 400:
            snippet = snippet[:400] + "..."
        user += f"- [{date}] @{usern or 'unknown'}: {snippet}\n"
    user += "\nProduce:\n1) One-line summary (single sentence).\n2) Bulleted list (3-6) of key facts, each bullet short and include dates / contract addresses where available.\n"
    return system, user

def _hf_call(prompt_text, model_name=HF_MODEL, max_tokens=500):
    if not HF_API_TOKEN:
        raise RuntimeError("No HF_API_TOKEN provided for Hugging Face inference.")
    url = f"https://api-inference.huggingface.co/models/{model_name}"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}", "Content-Type": "application/json"}
    payload = {"inputs": prompt_text, "parameters": {"max_new_tokens": max_tokens, "return_full_text": False}}
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    out = r.json()
    # HF inference output shape varies by model; try to extract text
    if isinstance(out, dict) and out.get("error"):
        raise RuntimeError("HF inference error: " + out.get("error"))
    if isinstance(out, list):
        # typically [{'generated_text': '...'}]
        first = out[0]
        if isinstance(first, dict):
            return first.get("generated_text") or first.get("text") or str(first)
        return str(first)
    return str(out)


def _local_fallback(messages_chunk, max_bullets=5):
    """Very small extractive fallback: pick messages that look most informative.
    Heuristic: score by length + presence of hex-like tokens (contract addresses) + numbers/dates.
    """
    scores = []
    for mid, usern, date, text in messages_chunk:
        t = (text or "").strip()
        score = len(t)
        # reward hex-like tokens (0x...)
        if re.search(r"0x[0-9a-fA-F]{6,}", t):
            score += 200
        # reward presence of dates/numbers
        if re.search(r"\d{4}-\d{2}-\d{2}|\d{2}:\d{2}|\b\d{3,}\b", t):
            score += 50
        scores.append((score, mid, usern, date, t))
    scores.sort(reverse=True, key=lambda x: x[0])
    top = scores[:max_bullets]
    bullets = []
    for s, mid, usern, date, t in top:
        snippet = t
        if len(snippet) > 300:
            snippet = snippet[:300] + "..."
        bullets.append(f"- [{date}] @{usern or 'unknown'}: {snippet}")
    one_line = (top[0][4][:200] + "...") if top else "No messages to summarize."
    out = f"One-line summary: {one_line}\n\nBullets:\n" + "\n".join(bullets)
    return out


def call_llm(system, prompt_text, model="gpt-3.5-turbo", max_tokens=500):
    provider = (LLM_PROVIDER or "hf").lower()
    if provider == "openai":
        if not OPENAI_API_KEY:
            raise RuntimeError("LLM_PROVIDER=openai but OPENAI_API_KEY missing")
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt_text}]
        resp = openai.ChatCompletion.create(model=model, messages=messages, max_tokens=max_tokens, temperature=0.2)
        return resp.choices[0].message.content.strip()
    elif provider == "hf":
        # Hugging Face text-generation style call; combine system + user into single prompt
        combined = system + "\n\n" + prompt_text
        try:
            return _hf_call(combined, model_name=HF_MODEL, max_tokens=max_tokens)
        except Exception as e:
            # fall back to local extractive summarizer
            print("HF call failed, falling back to local summarizer:", e)
            # Try to extract messages from prompt_text (the make_prompt format)
            msgs = []
            for line in prompt_text.splitlines():
                m = re.match(r"- \[(.*?)\] @?(.*?): (.*)$", line)
                if m:
                    date, usern, text = m.groups()
                    msgs.append((None, usern, date, text))
            return _local_fallback(msgs)
    elif provider == "local":
        # Expect prompt_text in make_prompt format; parse messages and run fallback
        msgs = []
        for line in prompt_text.splitlines():
            m = re.match(r"- \[(.*?)\] @?(.*?): (.*)$", line)
            if m:
                date, usern, text = m.groups()
                msgs.append((None, usern, date, text))
        return _local_fallback(msgs)
    else:
        raise RuntimeError(f"Unknown LLM_PROVIDER: {provider}")

def generate_summary_md(channel_id, window_days=DEFAULT_CHUNK_DAYS, since=None, until=None):
    # If since/until provided, ignore window_days and summarize that range
    if since and until:
        messages = fetch_messages(channel_id, since=since, until=until)
        chunks = [messages]
    else:
        # chunk by window_days across full history: build windows from earliest to latest
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT MIN(date), MAX(date) FROM messages WHERE channel_id = ?", (channel_id,))
        r = cur.fetchone()
        conn.close()
        if not r or r[0] is None:
            return None
        start = datetime.fromisoformat(r[0])
        end = datetime.fromisoformat(r[1])
        chunks = []
        window = timedelta(days=window_days)
        cur_start = start
        while cur_start <= end:
            cur_end = min(end, cur_start + window)
            chunks.append(fetch_messages(channel_id, since=cur_start, until=cur_end))
            cur_start = cur_end + timedelta(seconds=1)

    # For MVP, summarize the whole set by combining chunk outputs into one final summary
    partial_summaries = []
    for chunk in chunks:
        if not chunk:
            continue
        system, prompt_text = make_prompt(chunk)
        try:
            s = call_llm(system, prompt_text)
        except Exception as e:
            print("LLM call failed:", e)
            s = "LLM unavailable — fallback: top messages summary unavailable."
        partial_summaries.append(s)

    # Combine partial summaries (simple concat for now)
    combined = "\n\n".join(partial_summaries)
    # Post-process: produce a single markdown file with header that includes BOT_NAME
    md = f"# {BOT_NAME} — Channel Summary: {channel_id}\nGenerated at: {datetime.utcnow().isoformat()} UTC\n\n"
    md += combined
    # store to DB
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO summaries (channel_id, generated_at, window_start, window_end, summary_md) VALUES (?, ?, ?, ?, ?)",
                (channel_id, datetime.utcnow().isoformat(),
                 (since.isoformat() if since else None),
                 (until.isoformat() if until else None),
                 md))
    conn.commit()
    conn.close()
    return md

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel_id", required=True)
    parser.add_argument("--window-days", type=int, default=DEFAULT_CHUNK_DAYS)
    parser.add_argument("--since", help="YYYY-MM-DD")
    parser.add_argument("--until", help="YYYY-MM-DD")
    parser.add_argument("--out", help="path to save markdown", default=None)
    args = parser.parse_args()

    since = datetime.fromisoformat(args.since) if args.since else None
    until = datetime.fromisoformat(args.until) if args.until else None

    md = generate_summary_md(args.channel_id, window_days=args.window_days, since=since, until=until)
    if md and args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md)
        print("Summary written to", args.out)
    elif md:
        print(md)