#!/usr/bin/env python3
"""
Discord Processor: reads unprocessed Discord messages from SQLite, runs entity extraction,
downloads/ensures media exists, runs OCR on images, writes entities, and marks messages processed.

Similar to processor.py but handles Discord message format and media attachments.

Run:
  python discord_processor.py --limit 500
  python discord_processor.py --guild-id 1296015181985349715 --channel-id 1356175241172488314
"""

import os
import re
import json
import argparse
import sqlite3
from dotenv import load_dotenv
from tqdm import tqdm
from PIL import Image
import pytesseract
import dateparser
from typing import List, Tuple, Optional

load_dotenv()

DB_PATH = os.getenv("SQLITE_DB_PATH", "./data/backfill.sqlite")
MEDIA_DIR = os.getenv("MEDIA_DIR", "./data/media")
OCR_DIR = os.getenv("OCR_DIR", "./data/ocr")

os.makedirs(OCR_DIR, exist_ok=True)

# Entity extraction patterns (same as Telegram processor)
RE_0X = re.compile(r'0x[a-fA-F0-9]{40}')
RE_URL = re.compile(r'(https?://[^\s]+)')
RE_SIMPLE_ADDRESS = re.compile(r'\b[A-Za-z0-9]{32,64}\b')

# Discord-specific patterns
RE_USER_MENTION = re.compile(r'<@!?(\d+)>')
RE_CHANNEL_MENTION = re.compile(r'<#(\d+)>')
RE_ROLE_MENTION = re.compile(r'<@&(\d+)>')
RE_CUSTOM_EMOJI = re.compile(r'<a?:(\w+):(\d+)>')
RE_DISCORD_INVITE = re.compile(r'discord\.gg/([a-zA-Z0-9]+)')

def extract_dates(text: str) -> List[str]:
    """Extract dates from text using dateparser"""
    if not text:
        return []
    
    try:
        found = dateparser.search.search_dates(text, languages=['en']) if hasattr(dateparser.search, 'search_dates') else []
        dates = [d[1].isoformat() for d in found] if found else []
        return dates
    except Exception as e:
        print(f"Date extraction failed: {e}")
        return []

def ocr_image(path: str) -> str:
    """Extract text from image using OCR"""
    try:
        text = pytesseract.image_to_string(Image.open(path))
        return text.strip()
    except Exception as e:
        print(f"OCR failed for {path}: {e}")
        return ""

def extract_discord_entities(text: str, embed_data: str = None) -> List[Tuple[str, str, str, float]]:
    """
    Extract entities from Discord message content and embeds
    
    Returns list of (type, raw_value, normalized_value, confidence) tuples
    """
    entities = []
    
    if not text:
        text = ""
    
    # Contract addresses (0x...)
    for match in RE_0X.findall(text):
        entities.append(("contract", match, match.lower(), 1.0))
    
    # URLs
    for match in RE_URL.findall(text):
        entities.append(("url", match, match, 1.0))
    
    # Simple wallet addresses (non-0x)
    for match in RE_SIMPLE_ADDRESS.findall(text):
        if len(match) >= 32 and not match.lower().startswith("http"):
            entities.append(("wallet", match, match, 0.6))
    
    # Discord-specific entities
    # User mentions
    for match in RE_USER_MENTION.findall(text):
        entities.append(("user_mention", match, match, 0.9))
    
    # Channel mentions
    for match in RE_CHANNEL_MENTION.findall(text):
        entities.append(("channel_mention", match, match, 0.9))
    
    # Role mentions
    for match in RE_ROLE_MENTION.findall(text):
        entities.append(("role_mention", match, match, 0.9))
    
    # Custom emojis
    for match in RE_CUSTOM_EMOJI.findall(text):
        emoji_name, emoji_id = match
        entities.append(("custom_emoji", f"{emoji_name}:{emoji_id}", emoji_name, 0.8))
    
    # Discord invites
    for match in RE_DISCORD_INVITE.findall(text):
        entities.append(("discord_invite", match, match, 0.9))
    
    # Dates
    for date_str in extract_dates(text):
        entities.append(("date", date_str, date_str, 0.8))
    
    # Extract entities from embeds
    if embed_data:
        try:
            embeds = json.loads(embed_data)
            for embed in embeds:
                # Extract from embed title, description, and fields
                embed_text = ""
                if embed.get("title"):
                    embed_text += embed["title"] + " "
                if embed.get("description"):
                    embed_text += embed["description"] + " "
                
                # Extract from embed fields
                if embed.get("fields"):
                    for field in embed["fields"]:
                        if field.get("name"):
                            embed_text += field["name"] + " "
                        if field.get("value"):
                            embed_text += field["value"] + " "
                
                # Extract URLs from embeds
                for match in RE_0X.findall(embed_text):
                    entities.append(("contract", match, match.lower(), 0.9))
                
                for match in RE_URL.findall(embed_text):
                    entities.append(("url", match, match, 0.9))
                    
                for date_str in extract_dates(embed_text):
                    entities.append(("date", date_str, date_str, 0.7))
                    
        except Exception as e:
            print(f"Error processing embed data: {e}")
    
    return entities

def process_discord_batch(limit: int = 200, server_id: str = None, channel_id: str = None):
    """Process unprocessed Discord messages from browser extraction"""
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if we have processed column, add if not
    cur.execute("PRAGMA table_info(discord_messages)")
    columns = [column[1] for column in cur.fetchall()]
    if 'processed' not in columns:
        cur.execute("ALTER TABLE discord_messages ADD COLUMN processed INTEGER DEFAULT 0")
        conn.commit()
    
    # Build query for new table structure
    query = """SELECT message_id, channel_id, server_id, user_id, username, 
                     content, timestamp, reactions, embeds, attachments, mentions, 
                     parent_id, thread_id, is_bot, is_pinned
               FROM discord_messages 
               WHERE processed = 0"""
    params = []
    
    if server_id:
        query += " AND server_id = ?"
        params.append(server_id)
    
    if channel_id:
        query += " AND channel_id = ?"
        params.append(channel_id)
    
    query += " ORDER BY timestamp LIMIT ?"
    params.append(limit)
    
    cur.execute(query, params)
    rows = cur.fetchall()
    
    if not rows:
        print("No unprocessed Discord messages found")
        conn.close()
        return
    
    print(f"Processing {len(rows)} Discord messages...")
    
    # Create entities table if it doesn't exist
    cur.execute("""CREATE TABLE IF NOT EXISTS discord_entities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT NOT NULL,
        type TEXT NOT NULL,
        raw_value TEXT NOT NULL,
        normalized_value TEXT,
        confidence REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (message_id) REFERENCES discord_messages (message_id)
    )""")
    
    for row in tqdm(rows):
        message_id, channel_id, server_id, user_id, username, content, timestamp, reactions, embeds, attachments, mentions, parent_id, thread_id, is_bot, is_pinned = row
        
        entities = []
        
        # Extract entities from message content and embeds
        entities.extend(extract_discord_entities(content, embeds))
        
        # Process attachments for OCR (if any were downloaded)
        ocr_text = None
        if attachments:
            try:
                attachment_list = json.loads(attachments) if attachments else []
                for attachment in attachment_list:
                    # Note: Browser extraction doesn't download attachments automatically
                    # This would need to be implemented separately if needed
                    pass
                                    
            except Exception as e:
                print(f"Error processing attachments for message {message_id}: {e}")
                
        # Process reactions for additional entity extraction
        if reactions:
            try:
                reaction_list = json.loads(reactions) if reactions else []
                for reaction in reaction_list:
                    # Extract custom emoji IDs from reactions
                    if 'emoji' in reaction:
                        emoji = reaction['emoji']
                        if ':' in emoji and emoji.startswith('<'):
                            entities.append(("reaction_emoji", emoji, emoji, 0.7))
            except Exception as e:
                print(f"Error processing reactions for message {message_id}: {e}")
                
        # Process mentions for entity extraction
        if mentions:
            try:
                mention_list = json.loads(mentions) if mentions else []
                for mention in mention_list:
                    entities.append(("mentioned_user", mention, mention, 0.8))
            except Exception as e:
                print(f"Error processing mentions for message {message_id}: {e}")
        
        # Insert entities into database
        for entity_type, raw_val, norm_val, confidence in entities:
            try:
                cur.execute("""INSERT INTO discord_entities 
                              (message_id, type, raw_value, normalized_value, confidence)
                              VALUES (?, ?, ?, ?, ?)""",
                           (message_id, entity_type, raw_val, norm_val, confidence))
            except Exception as e:
                print(f"Failed to insert entity for message {message_id}: {e}")
        
        # Update OCR text if found
        if ocr_text:
            try:
                # Add ocr_text column to discord_messages if it doesn't exist
                cur.execute("PRAGMA table_info(discord_messages)")
                columns = [column[1] for column in cur.fetchall()]
                if 'ocr_text' not in columns:
                    cur.execute("ALTER TABLE discord_messages ADD COLUMN ocr_text TEXT")
                
                cur.execute("UPDATE discord_messages SET ocr_text = ? WHERE message_id = ?", 
                           (ocr_text, message_id))
            except Exception as e:
                print(f"Failed to update OCR text for message {message_id}: {e}")
        
        # Mark as processed
        try:
            cur.execute("UPDATE discord_messages SET processed = 1 WHERE message_id = ?", (message_id,))
        except Exception as e:
            print(f"Failed to mark message {message_id} as processed: {e}")
    
    conn.commit()
    conn.close()
    print(f"Processing complete. Processed {len(rows)} Discord messages.")

def get_processing_stats(server_id: str = None, channel_id: str = None):
    """Get statistics about message processing"""
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Build base query
    base_query = "FROM discord_messages WHERE 1=1"
    params = []
    
    if server_id:
        base_query += " AND server_id = ?"
        params.append(server_id)
    
    if channel_id:
        base_query += " AND channel_id = ?"
        params.append(channel_id)
    
    # Get total messages
    cur.execute(f"SELECT COUNT(*) {base_query}", params)
    total_messages = cur.fetchone()[0]
    
    # Get processed messages
    cur.execute(f"SELECT COUNT(*) {base_query} AND processed = 1", params)
    processed_messages = cur.fetchone()[0]
    
    # Get messages with entities
    cur.execute(f"""SELECT COUNT(DISTINCT dm.message_id) 
                   FROM discord_messages dm 
                   JOIN discord_entities de ON dm.message_id = de.message_id
                   WHERE 1=1 {base_query.replace('FROM discord_messages WHERE 1=1', '')}""", params)
    messages_with_entities = cur.fetchone()[0]
    
    # Get entity counts by type
    cur.execute(f"""SELECT de.type, COUNT(*) 
                   FROM discord_entities de 
                   JOIN discord_messages dm ON dm.message_id = de.message_id
                   WHERE 1=1 {base_query.replace('FROM discord_messages WHERE 1=1', '')}
                   GROUP BY de.type 
                   ORDER BY COUNT(*) DESC""", params)
    entity_counts = cur.fetchall()
    
    conn.close()
    
    print("\n=== Discord Processing Statistics ===")
    if server_id:
        print(f"Server ID: {server_id}")
    if channel_id:
        print(f"Channel ID: {channel_id}")
    
    print(f"Total messages: {total_messages}")
    print(f"Processed messages: {processed_messages}")
    print(f"Unprocessed messages: {total_messages - processed_messages}")
    print(f"Messages with entities: {messages_with_entities}")
    
    if entity_counts:
        print("\nEntity counts by type:")
        for entity_type, count in entity_counts:
            print(f"  {entity_type}: {count}")
    else:
        print("\nNo entities found")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Discord messages for entity extraction")
    parser.add_argument("--limit", type=int, default=200, help="Maximum number of messages to process")
    parser.add_argument("--server-id", help="Process messages from specific server only")
    parser.add_argument("--channel-id", help="Process messages from specific channel only")
    parser.add_argument("--stats", action="store_true", help="Show processing statistics instead of processing")
    
    args = parser.parse_args()
    
    if args.stats:
        get_processing_stats(args.server_id, args.channel_id)
    else:
        process_discord_batch(args.limit, args.server_id, args.channel_id)