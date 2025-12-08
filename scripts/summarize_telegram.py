#!/usr/bin/env python3
"""Fetch Telegram channel messages and summarize using Hugging Face Inference API.

Usage:
  python scripts/summarize_telegram.py --channel my_channel_username --limit 200

Environment variables (in `.env`):
  TELEGRAM_API_ID
  TELEGRAM_API_HASH
  HF_TOKEN            # Hugging Face token with read/inference scope
  HF_MODEL (opt)      # model id, e.g. 'facebook/bart-large-cnn'

Notes:
  - On first run Telethon may prompt for login (phone/code) to create a session file.
  - For bot login you can also supply TELEGRAM_BOT_TOKEN and Telethon will use it.
"""

from __future__ import annotations

import argparse
import asyncio
import math
import os
import textwrap
from typing import List

import requests
from dotenv import load_dotenv
from telethon import TelegramClient


load_dotenv()


def chunk_text(text: str, max_chars: int = 3000) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        # try to cut at newline or space for nicer boundaries
        if end < len(text):
            cut = text.rfind('\n', start, end)
            if cut <= start:
                cut = text.rfind(' ', start, end)
            if cut > start:
                end = cut
        chunks.append(text[start:end].strip())
        start = end
    return [c for c in chunks if c]


def call_hf_inference(model: str, token: str, inputs: str) -> str:
    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"inputs": inputs}
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    # data may be a list of dicts or dict depending on model
    if isinstance(data, list):
        # attempt common keys
        first = data[0]
        if isinstance(first, dict):
            return first.get("summary_text") or first.get("generated_text") or str(first)
        return str(data)
    if isinstance(data, dict):
        return data.get("summary_text") or data.get("generated_text") or str(data)
    return str(data)


async def fetch_messages_text(client: TelegramClient, channel: str, limit: int = 200) -> str:
    entity = await client.get_entity(channel)
    texts = []
    async for msg in client.iter_messages(entity, limit=limit):
        if msg and getattr(msg, "message", None):
            texts.append(msg.message)
    # messages are returned newest->oldest; reverse to chronological
    texts.reverse()
    return "\n\n".join(texts)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", required=True, help="channel username or id (e.g. @mychannel)")
    parser.add_argument("--limit", type=int, default=200, help="number of recent messages to fetch")
    parser.add_argument("--model", default=os.getenv("HF_MODEL", "facebook/bart-large-cnn"))
    parser.add_argument("--out", default=None, help="optional output file to write summary")
    args = parser.parse_args()

    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    # allow session name override via .env (defaults to 'signalsifter_session')
    session_name = os.getenv("SESSION_NAME", "signalsifter_session")
    session_file = f"{session_name}.session"
    hf_token = os.getenv("HF_TOKEN")

    if not api_id or not api_hash:
        raise SystemExit("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in the environment or .env")
    if not hf_token:
        raise SystemExit("HF_TOKEN (Hugging Face token with read/inference scope) must be set")

    # Telethon expects int api_id
    api_id = int(api_id)

    # If no user session file exists, show a clearer message and exit rather than
    # starting an unexpected interactive login. This prevents accidental runs
    # in non-interactive environments and avoids bot-account misuse (bots
    # cannot read channel history).
    if not os.path.exists(session_file):
        print("\nNo user session detected for Telegram (session file: {} ).".format(session_file))
        print("To read channel history you must either:")
        print("  1) Run interactively so Telethon can create a user session (remove TELEGRAM_BOT_TOKEN from .env and re-run), or")
        print("  2) Create a session ahead of time by running the script locally and completing the phone/code login.")
        print("\nIf you only want the bot to POST summaries (not read messages), keep TELEGRAM_BOT_TOKEN in .env and use a separate user client to fetch messages.")
        print("\nExample interactive run to create session:")
        print("  set -o allexport; source .env; set +o allexport; TELEGRAM_BOT_TOKEN= .venv/bin/python scripts/summarize_telegram.py --channel @your_channel --limit 50")
        raise SystemExit(2)

    client = TelegramClient(session_name, api_id, api_hash)
    await client.start(bot_token=bot_token)  # if bot_token is None, will do user login flow

    print(f"Fetching last {args.limit} messages from {args.channel}...")
    text = await fetch_messages_text(client, args.channel, limit=args.limit)
    if not text.strip():
        print("No text messages found.")
        await client.disconnect()
        return

    # chunk and summarize each chunk, then combine
    chunks = chunk_text(text, max_chars=3000)
    print(f"Text length: {len(text)} chars -> {len(chunks)} chunk(s)")

    summaries = []
    for i, c in enumerate(chunks, start=1):
        print(f"Summarizing chunk {i}/{len(chunks)} (approx {len(c)} chars)")
        prompt = f"Summarize the following chat messages in a few concise bullet points:\n\n{c}"
        try:
            summary = call_hf_inference(args.model, hf_token, prompt)
        except Exception as e:
            print(f"Error calling HF inference: {e}")
            summary = ""
        summaries.append(summary)

    combined = "\n\n".join(summaries)
    # optional final summarize pass if there were multiple chunks
    if len(summaries) > 1:
        print("Creating final combined summary...")
        final_prompt = "Summarize these summaries into a single concise summary:\n\n" + combined
        try:
            final_summary = call_hf_inference(args.model, hf_token, final_prompt)
        except Exception as e:
            print(f"Final summarization failed: {e}")
            final_summary = combined
    else:
        final_summary = combined

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(final_summary)
        print(f"Saved summary to {args.out}")
    else:
        print('\n' + '=' * 40 + '\nFINAL SUMMARY:\n' + '=' * 40 + '\n')
        print(final_summary)

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
