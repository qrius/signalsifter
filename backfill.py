#!/usr/bin/env python3
"""
Telethon backfill script (updated)
- Adds --no-media flag to skip downloading and storing media files.
- Interactive login on first run (session saved to .session/<SESSION_NAME>.session)
- Channel-by-channel backfill
- Resume from last processed message per channel

Usage:
  python backfill.py --channel "<channel_username_or_id>" [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--no-media]
"""
import os
import json
import argparse
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient, errors
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from dateutil import parser as dtparser
from tqdm import tqdm

load_dotenv()
API_ID = int(os.getenv("TELEGRAM_API_ID") or 0)
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = os.getenv("SESSION_NAME", "telethon_session")
DB_PATH = os.getenv("SQLITE_DB_PATH", "./data/backfill.sqlite")
RAW_DIR = os.getenv("RAW_DIR", "./data/raw")
MEDIA_DIR = os.getenv("MEDIA_DIR", "./data/media")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(MEDIA_DIR, exist_ok=True)

# ensure DB and tables exist
import sqlite3
schema = open("db_schema.sql").read()
conn = sqlite3.connect(DB_PATH)
conn.executescript(schema)
conn.commit()
conn.close()

async def run_backfill(channel, from_date=None, to_date=None, no_media=False):
    # Telethon uses session file named <SESSION_NAME>.session in cwd
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    me = await client.get_me()
    print("Logged in as:", getattr(me, "username", me.stringify()) if me else "unknown")

    try:
        entity = await client.get_entity(channel)
    except Exception as e:
        print("Failed to resolve channel:", channel, e)
        await client.disconnect()
        return

    channel_id = str(entity.id)
    channel_folder = os.path.join(RAW_DIR, channel_id)
    media_folder = os.path.join(MEDIA_DIR, channel_id)
    os.makedirs(channel_folder, exist_ok=True)
    os.makedirs(media_folder, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO channels (tg_id, title, username, created_at) VALUES (?, ?, ?, ?)",
                (channel_id, getattr(entity, 'title', None), getattr(entity, 'username', None), None))
    conn.commit()

    # find last message id stored for resume
    cur.execute("SELECT MAX(message_id) FROM messages WHERE channel_id = ?", (channel_id,))
    row = cur.fetchone()
    last_msg_id = row[0] if row else None

    print("Starting iteration for channel:", channel, "resume after message:", last_msg_id)

    # Count total messages (approx) for progress information
    total = 0
    async for _ in client.iter_messages(entity, reverse=True):
        total += 1
    print("Total messages in channel (approx):", total)

    async for msg in client.iter_messages(entity, reverse=True):
        # filter by date
        msg_date = msg.date
        if from_date and msg_date < from_date:
            continue
        if to_date and msg_date > to_date:
            continue
        if last_msg_id and msg.id <= last_msg_id:
            # already processed earlier messages
            continue

        # store raw JSON
        raw_path = os.path.join(channel_folder, f"message_{msg.id}.json")
        try:
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(msg.to_dict(), default=str))
        except Exception as e:
            print("Failed to write raw json for msg", msg.id, e)
            raw_path = None

        media_path = None
        has_media_flag = 0
        if not no_media and (msg.photo or msg.media):
            try:
                fname = await msg.download_media(file=media_folder)
                media_path = fname
                has_media_flag = 1
            except Exception as e:
                print("Media download failed for msg", msg.id, e)
        else:
            # If skipping media, do not download or mark has_media
            has_media_flag = 0
            media_path = None

        # sender handling robustly
        sender_id = None
        sender_username = None
        sender_name = None
        try:
            if msg.from_id:
                if hasattr(msg.from_id, 'user_id'):
                    sender_id = msg.from_id.user_id
                else:
                    sender_id = msg.from_id
            if getattr(msg, "sender", None):
                sender_username = getattr(msg.sender, "username", None)
                sender_name = getattr(msg.sender, "first_name", None)
        except Exception:
            # fallback: use attributes if available in dict form
            d = msg.to_dict()
            sender_username = d.get("from", {}).get("username") if isinstance(d.get("from"), dict) else None

        # insert into sqlite
        try:
            cur.execute("""INSERT OR IGNORE INTO messages
                       (channel_id, message_id, sender_id, sender_username, sender_name, date, edit_date,
                        is_forwarded, forward_from, reply_to_msg_id, text, has_media, media_path, raw_json_path, processed)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                        (channel_id,
                         msg.id,
                         sender_id,
                         sender_username,
                         sender_name,
                         msg.date.isoformat(),
                         msg.edit_date.isoformat() if msg.edit_date else None,
                         1 if msg.fwd_from else 0,
                         getattr(msg.fwd_from, 'from_name', None) if msg.fwd_from else None,
                         msg.reply_to_msg_id,
                         getattr(msg, 'message', None),
                         has_media_flag,
                         media_path,
                         raw_path))
            conn.commit()
        except Exception as e:
            print("DB insert failed for msg", msg.id, e)
    # update last_backfilled_at
    cur.execute("UPDATE channels SET last_backfilled_at = ? WHERE tg_id = ?", (datetime.utcnow().isoformat(), channel_id))
    conn.commit()
    conn.close()
    await client.disconnect()
    print("Backfill complete for channel:", channel)

if __name__ == "__main__":
    import asyncio
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", required=True, help="channel username or id")
    parser.add_argument("--from", dest="from_date", help="YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", help="YYYY-MM-DD")
    parser.add_argument("--no-media", action="store_true", help="Skip downloading/storing media files")
    args = parser.parse_args()

    from_date = dtparser.parse(args.from_date) if args.from_date else None
    to_date = dtparser.parse(args.to_date) if args.to_date else None

    asyncio.run(run_backfill(args.channel, from_date=from_date, to_date=to_date, no_media=args.no_media))