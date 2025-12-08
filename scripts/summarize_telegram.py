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
    # Try multiple HF API endpoints
    endpoints = [
        f"https://api-inference.huggingface.co/models/{model}",
        f"https://router.huggingface.co/models/{model}",
    ]
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"inputs": inputs}
    
    for url in endpoints:
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code == 200:
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
        except Exception as e:
            print(f"Failed to call {url}: {e}")
            continue
    
    # Fallback to simple extractive summary
    print("All HF API calls failed, using extractive summary fallback")
    return simple_extractive_summary(inputs)


def simple_extractive_summary(text: str, num_sentences: int = 3) -> str:
    """Simple extractive summarization by selecting key sentences from content"""
    # Remove any summarization prompts completely
    if "Summarize" in text and ("summaries" in text or "chat messages" in text):
        # Find content after the prompt
        lines = text.split('\n')
        content_lines = []
        found_content = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Skip prompt lines
            if ("Summarize" in line or "bullet points" in line or "concise" in line) and not found_content:
                continue
            found_content = True
            content_lines.append(line)
        text = '\n'.join(content_lines)
    
    # Clean and extract meaningful sentences
    sentences = []
    for line in text.split('\n'):
        line = line.strip()
        if line and not line.startswith('http') and len(line) > 10:  # Filter short/URL lines
            # Split on periods but keep sentences with content
            parts = [s.strip() for s in line.split('.') if s.strip() and len(s.strip()) > 5]
            sentences.extend(parts)
    
    if not sentences:
        return "No meaningful content to summarize."
    
    # Remove duplicates while preserving order
    unique_sentences = []
    seen = set()
    for sentence in sentences:
        lower = sentence.lower()
        if lower not in seen and len(sentence) > 15:  # Filter very short sentences
            seen.add(lower)
            unique_sentences.append(sentence)
    
    if not unique_sentences:
        return "No substantial content found."
    
    if len(unique_sentences) <= num_sentences:
        return '. '.join(unique_sentences) + '.'
    
    # Select representative sentences from beginning, middle, and end
    selected = []
    selected.append(unique_sentences[0])  # First substantial sentence
    
    if len(unique_sentences) > 2:
        mid_idx = len(unique_sentences) // 2
        selected.append(unique_sentences[mid_idx])  # Middle sentence
    
    if len(unique_sentences) > 1:
        selected.append(unique_sentences[-1])  # Last sentence
    
    return '. '.join(selected) + '.'


async def fetch_messages_text(client: TelegramClient, channel: str, limit: int = 200) -> str:
    entity = await client.get_entity(channel)
    messages = []
    async for msg in client.iter_messages(entity, limit=limit):
        if msg and getattr(msg, "message", None):
            # Format: [YYYY-MM-DD HH:MM:SS UTC] @username: message_text
            timestamp = msg.date.strftime("%Y-%m-%d %H:%M:%S UTC")
            
            # Get sender info (username, first name, or ID)
            sender = "Unknown"
            if hasattr(msg, 'sender') and msg.sender:
                if hasattr(msg.sender, 'username') and msg.sender.username:
                    sender = f"@{msg.sender.username}"
                elif hasattr(msg.sender, 'first_name') and msg.sender.first_name:
                    sender = msg.sender.first_name
                    if hasattr(msg.sender, 'last_name') and msg.sender.last_name:
                        sender += f" {msg.sender.last_name}"
                elif hasattr(msg.sender, 'id'):
                    sender = f"User#{msg.sender.id}"
            
            formatted_msg = f"[{timestamp}] {sender}: {msg.message}"
            messages.append(formatted_msg)
    # messages are returned newest->oldest; reverse to chronological
    messages.reverse()
    return "\n\n".join(messages)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", required=True, help="channel username or id (e.g. @mychannel)")
    parser.add_argument("--limit", type=int, default=200, help="number of recent messages to fetch")
    parser.add_argument("--model", default=os.getenv("HF_MODEL", "facebook/bart-large-cnn"))
    parser.add_argument("--out", default=None, help="optional output file to write summary")
    parser.add_argument("--raw", default=None, help="optional file to save raw extracted messages")
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

    # If no user session file exists and bot_token is set, show a clearer message and exit.
    # This prevents accidental runs in non-interactive environments and avoids bot-account misuse.
    # However, if bot_token is None, allow session creation interactively.
    if not os.path.exists(session_file):
        if bot_token:
            print("\nNo user session detected for Telegram (session file: {} ).".format(session_file))
            print("To read channel history you must either:")
            print("  1) Run interactively so Telethon can create a user session (remove TELEGRAM_BOT_TOKEN from .env and re-run), or")
            print("  2) Create a session ahead of time by running the script locally and completing the phone/code login.")
            print("\nIf you only want the bot to POST summaries (not read messages), keep TELEGRAM_BOT_TOKEN in .env and use a separate user client to fetch messages.")
            print("\nExample interactive run to create session:")
            print("  set -o allexport; source .env; set +o allexport; TELEGRAM_BOT_TOKEN= .venv/bin/python scripts/summarize_telegram.py --channel @your_channel --limit 50")
            raise SystemExit(2)
        else:
            print(f"\nNo session file found ({session_file}). Creating new user session...")
            print("You will be prompted for your phone number and verification code.")

    client = TelegramClient(session_name, api_id, api_hash)
    await client.start(bot_token=bot_token)  # if bot_token is None, will do user login flow

    print(f"Fetching last {args.limit} messages from {args.channel}...")
    text = await fetch_messages_text(client, args.channel, limit=args.limit)
    if not text.strip():
        print("No text messages found.")
        await client.disconnect()
        return

    # Save raw messages if requested
    if args.raw:
        with open(args.raw, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Saved raw messages to {args.raw}")

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
