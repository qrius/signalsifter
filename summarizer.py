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

load_dotenv()
DB_PATH = os.getenv("SQLITE_DB_PATH", "./data/backfill.sqlite")
DEFAULT_CHUNK_DAYS = int(os.getenv("DEFAULT_CHUNK_DAYS", 7))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
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

def call_llm(system, prompt_text, model="gpt-3.5-turbo", max_tokens=500):
    if not OPENAI_API_KEY:
        raise RuntimeError("No OPENAI_API_KEY provided. Set it in .env or implement another provider in this script.")
    messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt_text}]
    resp = openai.ChatCompletion.create(model=model, messages=messages, max_tokens=max_tokens, temperature=0.2)
    return resp.choices[0].message.content.strip()

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