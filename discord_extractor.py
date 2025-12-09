#!/usr/bin/env python3
"""
Discord backfill script for SignalSifter
- Extracts messages from Discord channels/servers
- Similar functionality to Telethon backfill but for Discord
- Stores messages, media, and metadata in SQLite

Usage:
  python discord_extractor.py --url "https://discord.com/channels/1296015181985349715/1356175241172488314"
  python discord_extractor.py --guild-id 1296015181985349715 --channel-id 1356175241172488314
  python discord_extractor.py --guild-id 1296015181985349715 --channel-id 1356175241172488314 --from 2023-01-01 --to 2023-12-31 --no-media

Environment variables (in `.env`):
  DISCORD_BOT_TOKEN       # Discord Bot Token (get from Discord Developer Portal)
  SQLITE_DB_PATH         # Path to SQLite database
  RAW_DIR               # Directory for raw JSON files
  MEDIA_DIR             # Directory for media files
"""

import os
import json
import argparse
import sqlite3
import asyncio
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Optional, Tuple
from dotenv import load_dotenv
import discord
from discord.ext import commands
from tqdm import tqdm

load_dotenv()

# Discord configuration
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DB_PATH = os.getenv("SQLITE_DB_PATH", "./data/backfill.sqlite")
RAW_DIR = os.getenv("RAW_DIR", "./data/raw")
MEDIA_DIR = os.getenv("MEDIA_DIR", "./data/media")

# Ensure directories exist
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs("./data", exist_ok=True)

def parse_discord_url(url: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Parse Discord URL to extract guild_id and channel_id
    
    Examples:
      https://discord.com/channels/1296015181985349715/1356175241172488314
      https://discord.com/channels/@me/1356175241172488314 (DM - not supported)
    
    Returns:
        Tuple of (guild_id, channel_id) or (None, None) if parsing fails
    """
    try:
        # Discord URL pattern: https://discord.com/channels/{guild_id}/{channel_id}
        pattern = r'https://discord\.com/channels/(\d+)/(\d+)(?:/(\d+))?'
        match = re.match(pattern, url)
        
        if match:
            guild_id = int(match.group(1))
            channel_id = int(match.group(2))
            return guild_id, channel_id
        
        # Handle @me (DM) channels
        if "@me" in url:
            print("Direct messages are not supported. Please use server channels.")
            return None, None
            
    except Exception as e:
        print(f"Error parsing Discord URL: {e}")
    
    return None, None

def ensure_discord_schema():
    """Ensure Discord-compatible database schema exists"""
    
    # Read existing schema and add Discord-specific tables
    discord_schema = """
-- Discord-specific tables for SignalSifter

CREATE TABLE IF NOT EXISTS discord_guilds (
  id INTEGER PRIMARY KEY,
  discord_id TEXT UNIQUE,
  name TEXT,
  description TEXT,
  member_count INTEGER,
  created_at TEXT,
  last_backfilled_at TEXT,
  last_gemini_export TEXT
);

CREATE TABLE IF NOT EXISTS discord_channels (
  id INTEGER PRIMARY KEY,
  discord_id TEXT UNIQUE,
  guild_id TEXT,
  name TEXT,
  topic TEXT,
  type TEXT,  -- text, voice, category, forum, etc.
  position INTEGER,
  created_at TEXT,
  last_backfilled_at TEXT,
  FOREIGN KEY(guild_id) REFERENCES discord_guilds(discord_id)
);

CREATE TABLE IF NOT EXISTS discord_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id TEXT,
  channel_id TEXT,
  message_id TEXT,
  author_id TEXT,
  author_username TEXT,
  author_display_name TEXT,
  created_at TEXT,
  edited_at TEXT,
  content TEXT,
  has_embeds INTEGER DEFAULT 0,
  has_attachments INTEGER DEFAULT 0,
  attachment_paths TEXT,  -- JSON array of local file paths
  embed_data TEXT,       -- JSON of embed data
  reply_to_message_id TEXT,
  thread_id TEXT,        -- For thread messages
  is_pinned INTEGER DEFAULT 0,
  mention_count INTEGER DEFAULT 0,
  reaction_count INTEGER DEFAULT 0,
  raw_json_path TEXT,
  processed INTEGER DEFAULT 0,
  gemini_processed INTEGER DEFAULT 0,
  UNIQUE(guild_id, channel_id, message_id)
);

CREATE INDEX IF NOT EXISTS idx_discord_messages_channel_date ON discord_messages(channel_id, created_at);
CREATE INDEX IF NOT EXISTS idx_discord_messages_activity ON discord_messages(guild_id, channel_id, created_at, processed);

CREATE TABLE IF NOT EXISTS discord_entities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  message_row_id INTEGER,
  type TEXT,
  raw_value TEXT,
  normalized_value TEXT,
  confidence REAL,
  FOREIGN KEY(message_row_id) REFERENCES discord_messages(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS discord_analysis_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id TEXT,
  channel_id TEXT,
  analysis_date TEXT,
  messages_processed INTEGER,
  api_requests_used INTEGER,
  chunks_processed INTEGER,
  analysis_file_path TEXT,
  metadata_file_path TEXT,
  citations_count INTEGER,
  analysis_type TEXT DEFAULT 'comprehensive',
  success INTEGER DEFAULT 1,
  error_message TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
    """
    
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(discord_schema)
    conn.commit()
    conn.close()

class DiscordExtractor:
    def __init__(self):
        self.client = None
        
    async def setup(self):
        """Initialize Discord client"""
        if not DISCORD_BOT_TOKEN:
            raise ValueError("DISCORD_BOT_TOKEN must be set in environment or .env file")
        
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        self.client = discord.Client(intents=intents)
        
        @self.client.event
        async def on_ready():
            print(f'Logged in as {self.client.user} (ID: {self.client.user.id})')
        
        await self.client.login(DISCORD_BOT_TOKEN)
        await self.client.connect()
    
    async def extract_guild_info(self, guild_id: int):
        """Extract and store guild information"""
        guild = self.client.get_guild(guild_id)
        if not guild:
            raise ValueError(f"Bot is not a member of guild {guild_id} or guild doesn't exist")
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        cur.execute("""INSERT OR REPLACE INTO discord_guilds 
                      (discord_id, name, description, member_count, created_at, last_backfilled_at)
                      VALUES (?, ?, ?, ?, ?, ?)""",
                   (str(guild.id), guild.name, guild.description, 
                    guild.member_count, guild.created_at.isoformat(), 
                    datetime.now(timezone.utc).isoformat()))
        
        conn.commit()
        conn.close()
        return guild
    
    async def extract_channel_info(self, channel_id: int):
        """Extract and store channel information"""
        channel = self.client.get_channel(channel_id)
        if not channel:
            raise ValueError(f"Channel {channel_id} not found or bot doesn't have access")
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        cur.execute("""INSERT OR REPLACE INTO discord_channels 
                      (discord_id, guild_id, name, topic, type, position, created_at, last_backfilled_at)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                   (str(channel.id), str(channel.guild.id), channel.name, 
                    getattr(channel, 'topic', None), str(channel.type),
                    getattr(channel, 'position', 0), channel.created_at.isoformat(),
                    datetime.now(timezone.utc).isoformat()))
        
        conn.commit()
        conn.close()
        return channel
    
    async def extract_messages(self, guild_id: int, channel_id: int, 
                             from_date=None, to_date=None, no_media=False):
        """Extract messages from Discord channel"""
        
        # Get guild and channel info
        guild = await self.extract_guild_info(guild_id)
        channel = await self.extract_channel_info(channel_id)
        
        print(f"Extracting from #{channel.name} in {guild.name}")
        
        # Create storage directories
        guild_folder = os.path.join(RAW_DIR, str(guild_id))
        channel_folder = os.path.join(guild_folder, str(channel_id))
        media_folder = os.path.join(MEDIA_DIR, str(guild_id), str(channel_id))
        
        os.makedirs(channel_folder, exist_ok=True)
        os.makedirs(media_folder, exist_ok=True)
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Find last message ID for resume capability
        cur.execute("SELECT MAX(message_id) FROM discord_messages WHERE guild_id = ? AND channel_id = ?", 
                   (str(guild_id), str(channel_id)))
        row = cur.fetchone()
        last_msg_id = int(row[0]) if row and row[0] else None
        
        print(f"Starting extraction for channel {channel_id}, resume after message: {last_msg_id}")
        
        message_count = 0
        
        try:
            async for message in channel.history(limit=None, oldest_first=True):
                # Skip if we've already processed this message
                if last_msg_id and message.id <= last_msg_id:
                    continue
                
                # Date filtering
                if from_date and message.created_at < from_date:
                    continue
                if to_date and message.created_at > to_date:
                    continue
                
                # Store raw JSON
                raw_path = os.path.join(channel_folder, f"message_{message.id}.json")
                try:
                    message_data = {
                        'id': message.id,
                        'author': {
                            'id': message.author.id,
                            'name': message.author.name,
                            'display_name': message.author.display_name,
                            'bot': message.author.bot
                        },
                        'channel_id': message.channel.id,
                        'guild_id': message.guild.id if message.guild else None,
                        'created_at': message.created_at.isoformat(),
                        'edited_at': message.edited_at.isoformat() if message.edited_at else None,
                        'content': message.content,
                        'embeds': [embed.to_dict() for embed in message.embeds],
                        'attachments': [att.to_dict() for att in message.attachments],
                        'reference': message.reference.to_dict() if message.reference else None,
                        'thread': message.thread.id if hasattr(message, 'thread') and message.thread else None,
                        'pinned': message.pinned,
                        'mentions': len(message.mentions),
                        'reactions': [{'emoji': str(reaction.emoji), 'count': reaction.count} 
                                    for reaction in message.reactions]
                    }
                    
                    with open(raw_path, "w", encoding="utf-8") as f:
                        json.dump(message_data, f, indent=2, default=str)
                except Exception as e:
                    print(f"Failed to write raw JSON for message {message.id}: {e}")
                    raw_path = None
                
                # Handle attachments
                attachment_paths = []
                has_attachments = len(message.attachments) > 0
                
                if not no_media and has_attachments:
                    for i, attachment in enumerate(message.attachments):
                        try:
                            # Create safe filename
                            filename = f"msg_{message.id}_att_{i}_{attachment.filename}"
                            filepath = os.path.join(media_folder, filename)
                            
                            await attachment.save(filepath)
                            attachment_paths.append(filepath)
                        except Exception as e:
                            print(f"Failed to download attachment from message {message.id}: {e}")
                
                # Handle embeds
                embed_data = None
                has_embeds = len(message.embeds) > 0
                if has_embeds:
                    embed_data = json.dumps([embed.to_dict() for embed in message.embeds], default=str)
                
                # Get reply information
                reply_to_message_id = None
                if message.reference:
                    reply_to_message_id = str(message.reference.message_id)
                
                # Insert into database
                try:
                    cur.execute("""INSERT OR IGNORE INTO discord_messages
                                 (guild_id, channel_id, message_id, author_id, author_username, 
                                  author_display_name, created_at, edited_at, content, has_embeds, 
                                  has_attachments, attachment_paths, embed_data, reply_to_message_id,
                                  thread_id, is_pinned, mention_count, reaction_count, raw_json_path, processed)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                               (str(guild_id), str(channel_id), str(message.id), str(message.author.id),
                                message.author.name, message.author.display_name, 
                                message.created_at.isoformat(), 
                                message.edited_at.isoformat() if message.edited_at else None,
                                message.content, int(has_embeds), int(has_attachments),
                                json.dumps(attachment_paths) if attachment_paths else None,
                                embed_data, reply_to_message_id, None, int(message.pinned),
                                len(message.mentions), len(message.reactions), raw_path))
                    
                    conn.commit()
                    message_count += 1
                    
                    if message_count % 100 == 0:
                        print(f"Processed {message_count} messages...")
                        
                except Exception as e:
                    print(f"Database insert failed for message {message.id}: {e}")
                    
        except Exception as e:
            print(f"Error during message extraction: {e}")
        
        # Update last backfilled timestamp
        cur.execute("UPDATE discord_channels SET last_backfilled_at = ? WHERE discord_id = ?",
                   (datetime.now(timezone.utc).isoformat(), str(channel_id)))
        conn.commit()
        conn.close()
        
        print(f"Extraction complete. Processed {message_count} messages from #{channel.name}")
        
    async def cleanup(self):
        """Close Discord client"""
        if self.client:
            await self.client.close()

async def run_discord_extraction(url=None, guild_id=None, channel_id=None, 
                               from_date=None, to_date=None, no_media=False):
    """Main extraction function"""
    
    # Parse URL if provided
    if url:
        parsed_guild_id, parsed_channel_id = parse_discord_url(url)
        if not parsed_guild_id or not parsed_channel_id:
            raise ValueError(f"Could not parse Discord URL: {url}")
        guild_id = parsed_guild_id
        channel_id = parsed_channel_id
    
    if not guild_id or not channel_id:
        raise ValueError("Must provide either --url or both --guild-id and --channel-id")
    
    # Ensure database schema
    ensure_discord_schema()
    
    # Initialize extractor
    extractor = DiscordExtractor()
    
    try:
        await extractor.setup()
        await extractor.extract_messages(guild_id, channel_id, from_date, to_date, no_media)
    finally:
        await extractor.cleanup()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract messages from Discord channels")
    parser.add_argument("--url", help="Discord channel URL (e.g., https://discord.com/channels/guild/channel)")
    parser.add_argument("--guild-id", type=int, help="Discord Guild (Server) ID")
    parser.add_argument("--channel-id", type=int, help="Discord Channel ID")
    parser.add_argument("--from", dest="from_date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to", dest="to_date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--no-media", action="store_true", help="Skip downloading attachments")
    
    args = parser.parse_args()
    
    # Parse dates
    from_date = None
    to_date = None
    if args.from_date:
        from_date = datetime.fromisoformat(args.from_date).replace(tzinfo=timezone.utc)
    if args.to_date:
        to_date = datetime.fromisoformat(args.to_date).replace(tzinfo=timezone.utc)
    
    try:
        asyncio.run(run_discord_extraction(
            url=args.url,
            guild_id=args.guild_id,
            channel_id=args.channel_id,
            from_date=from_date,
            to_date=to_date,
            no_media=args.no_media
        ))
    except KeyboardInterrupt:
        print("\nExtraction cancelled by user")
    except Exception as e:
        print(f"Error: {e}")