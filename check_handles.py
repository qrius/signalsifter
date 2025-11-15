#!/usr/bin/env python3
"""
Check Telegram username availability using your Telethon session.

Usage examples:
  # interactive (will ask for login on first run)
  python check_handles.py --handles signalsifter channelminer threadscout

  # read handles from a file:
  python check_handles.py --file handles.txt

Notes:
- Requires TELEGRAM_API_ID and TELEGRAM_API_HASH in .env (same as your backfiller setup).
- Session file SESSION_NAME.session will be used/created in cwd.
"""
import argparse
import os
import re
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import UsernameNotOccupiedError, UsernameInvalidError

load_dotenv()
API_ID = int(os.getenv("TELEGRAM_API_ID") or 0)
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = os.getenv("SESSION_NAME", "telethon_session")

USERNAME_RE = re.compile(r'^[a-z0-9_]{5,32}$')

async def check_handles(handles):
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    print("Using session:", SESSION_NAME)
    results = []
    for h in handles:
        # normalize forms
        if h.startswith("@"):
            h = h[1:]
        for variant in (h, f"{h}_bot"):
            variant_norm = variant.lower()
            ok_format = bool(USERNAME_RE.match(variant_norm))
            status = {"handle": "@" + variant_norm, "valid_format": ok_format, "taken": None, "info": None}
            if not ok_format:
                status["taken"] = "invalid_format"
                results.append(status)
                print(f"{status['handle']}: INVALID FORMAT (must be 5-32 chars, a-z0-9_)")
                continue
            try:
                ent = await client.get_entity(variant_norm)
                # if we get here it's taken
                status["taken"] = True
                # minimal info: if has username / title
                try:
                    title = getattr(ent, "title", None) or getattr(ent, "username", None) or str(ent)
                except Exception:
                    title = str(ent)
                status["info"] = title
                print(f"{status['handle']}: TAKEN -> {title}")
            except Exception as e:
                # Telethon raises different errors when a username is not occupied or invalid
                # We'll treat failure to resolve as "probably available"
                # But some errors (flood/wrong auth) should be surfaced
                msg = str(e)
                if "Could not find the input entity" in msg or "UsernameNotOccupiedError" in msg or "UsernameInvalidError" in msg:
                    status["taken"] = False
                    print(f"{status['handle']}: AVAILABLE")
                else:
                    status["taken"] = None
                    status["info"] = msg
                    print(f"{status['handle']}: ERROR -> {msg}")
            results.append(status)
    await client.disconnect()
    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--handles", nargs="+", help="List of handle bases to check (without @).")
    parser.add_argument("--file", help="File with one handle per line.")
    args = parser.parse_args()
    handles = []
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            handles = [line.strip() for line in f if line.strip()]
    if args.handles:
        handles.extend(args.handles)
    if not handles:
        print("No handles supplied. Use --handles or --file.")
        return
    results = asyncio.run(check_handles(handles))
    # Optionally save summary
    import json
    with open("handle_check_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("Results saved to handle_check_results.json")

if __name__ == "__main__":
    main()