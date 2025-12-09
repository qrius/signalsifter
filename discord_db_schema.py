#!/usr/bin/env python3
"""
Discord Database Schema for SignalSifter
Creates and manages Discord-specific database tables with proper relationships
"""

import sqlite3
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import os

class DiscordDatabase:
    """Manages Discord database schema and operations"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), 'data', 'backfill.sqlite')
        
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with foreign key support"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn
        
    def create_discord_tables(self):
        """Create all Discord-related tables"""
        conn = self.get_connection()
        try:
            # Discord Servers table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discord_servers (
                    server_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    member_count INTEGER,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    platform TEXT DEFAULT 'discord'
                )
            """)
            
            # Discord Channels table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discord_channels (
                    channel_id TEXT PRIMARY KEY,
                    server_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    type TEXT DEFAULT 'text',
                    topic TEXT,
                    position INTEGER,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    platform TEXT DEFAULT 'discord',
                    FOREIGN KEY (server_id) REFERENCES discord_servers (server_id)
                )
            """)
            
            # Discord Messages table (main table)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discord_messages (
                    message_id TEXT PRIMARY KEY,
                    channel_id TEXT NOT NULL,
                    server_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    display_name TEXT,
                    content TEXT,
                    timestamp TIMESTAMP NOT NULL,
                    edited_timestamp TIMESTAMP,
                    message_type TEXT DEFAULT 'default',
                    parent_id TEXT,
                    thread_id TEXT,
                    reactions TEXT,
                    embeds TEXT,
                    attachments TEXT,
                    mentions TEXT,
                    is_bot BOOLEAN DEFAULT FALSE,
                    is_pinned BOOLEAN DEFAULT FALSE,
                    platform TEXT DEFAULT 'discord',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (channel_id) REFERENCES discord_channels (channel_id),
                    FOREIGN KEY (server_id) REFERENCES discord_servers (server_id),
                    FOREIGN KEY (parent_id) REFERENCES discord_messages (message_id)
                )
            """)
            
            # Discord Extraction Log table (for resume functionality)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discord_extraction_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    extraction_type TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    last_message_id TEXT,
                    last_timestamp TIMESTAMP,
                    messages_extracted INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running',
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (channel_id) REFERENCES discord_channels (channel_id)
                )
            """)
            
            # Discord Status table (for monitoring)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discord_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    server_id TEXT NOT NULL,
                    channel_name TEXT,
                    total_messages INTEGER DEFAULT 0,
                    last_extraction_time TIMESTAMP,
                    next_scheduled_time TIMESTAMP,
                    extraction_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    health_check_status TEXT DEFAULT 'ok',
                    last_error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (channel_id) REFERENCES discord_channels (channel_id),
                    FOREIGN KEY (server_id) REFERENCES discord_servers (server_id),
                    UNIQUE(channel_id)
                )
            """)
            
            # Create indexes for better performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_discord_messages_channel_id ON discord_messages (channel_id)",
                "CREATE INDEX IF NOT EXISTS idx_discord_messages_timestamp ON discord_messages (timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_discord_messages_user_id ON discord_messages (user_id)",
                "CREATE INDEX IF NOT EXISTS idx_discord_messages_parent_id ON discord_messages (parent_id)",
                "CREATE INDEX IF NOT EXISTS idx_discord_messages_thread_id ON discord_messages (thread_id)",
                "CREATE INDEX IF NOT EXISTS idx_discord_extraction_log_channel_id ON discord_extraction_log (channel_id)",
                "CREATE INDEX IF NOT EXISTS idx_discord_extraction_log_status ON discord_extraction_log (status)",
                "CREATE INDEX IF NOT EXISTS idx_discord_status_channel_id ON discord_status (channel_id)",
            ]
            
            for index_sql in indexes:
                conn.execute(index_sql)
            
            conn.commit()
            self.logger.info("Discord database tables created successfully")
            
        except sqlite3.Error as e:
            self.logger.error(f"Error creating Discord tables: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def insert_server(self, server_id: str, name: str, description: str = None, 
                     member_count: int = None, created_at: datetime = None) -> bool:
        """Insert or update Discord server information"""
        conn = self.get_connection()
        try:
            if created_at is None:
                created_at = datetime.utcnow()
                
            conn.execute("""
                INSERT OR REPLACE INTO discord_servers 
                (server_id, name, description, member_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (server_id, name, description, member_count, created_at))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            self.logger.error(f"Error inserting server {server_id}: {e}")
            return False
        finally:
            conn.close()
    
    def insert_channel(self, channel_id: str, server_id: str, name: str,
                      channel_type: str = 'text', topic: str = None,
                      position: int = None, created_at: datetime = None) -> bool:
        """Insert or update Discord channel information"""
        conn = self.get_connection()
        try:
            if created_at is None:
                created_at = datetime.utcnow()
                
            conn.execute("""
                INSERT OR REPLACE INTO discord_channels 
                (channel_id, server_id, name, type, topic, position, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (channel_id, server_id, name, channel_type, topic, position, created_at))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            self.logger.error(f"Error inserting channel {channel_id}: {e}")
            return False
        finally:
            conn.close()
    
    def insert_message(self, message_data: Dict[str, Any]) -> bool:
        """Insert Discord message with all metadata"""
        conn = self.get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO discord_messages 
                (message_id, channel_id, server_id, user_id, username, display_name,
                 content, timestamp, edited_timestamp, message_type, parent_id, 
                 thread_id, reactions, embeds, attachments, mentions, is_bot, is_pinned)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message_data.get('message_id'),
                message_data.get('channel_id'),
                message_data.get('server_id'),
                message_data.get('user_id'),
                message_data.get('username'),
                message_data.get('display_name'),
                message_data.get('content'),
                message_data.get('timestamp'),
                message_data.get('edited_timestamp'),
                message_data.get('message_type', 'default'),
                message_data.get('parent_id'),
                message_data.get('thread_id'),
                message_data.get('reactions'),
                message_data.get('embeds'),
                message_data.get('attachments'),
                message_data.get('mentions'),
                message_data.get('is_bot', False),
                message_data.get('is_pinned', False)
            ))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            self.logger.error(f"Error inserting message {message_data.get('message_id')}: {e}")
            return False
        finally:
            conn.close()
    
    def log_extraction_start(self, channel_id: str, extraction_type: str) -> int:
        """Log the start of an extraction process"""
        conn = self.get_connection()
        try:
            cursor = conn.execute("""
                INSERT INTO discord_extraction_log 
                (channel_id, extraction_type, start_time, status)
                VALUES (?, ?, ?, 'running')
            """, (channel_id, extraction_type, datetime.utcnow()))
            
            log_id = cursor.lastrowid
            conn.commit()
            return log_id
            
        except sqlite3.Error as e:
            self.logger.error(f"Error logging extraction start: {e}")
            return None
        finally:
            conn.close()
    
    def update_extraction_progress(self, log_id: int, last_message_id: str, 
                                 last_timestamp: datetime, messages_count: int):
        """Update extraction progress"""
        conn = self.get_connection()
        try:
            conn.execute("""
                UPDATE discord_extraction_log 
                SET last_message_id = ?, last_timestamp = ?, messages_extracted = ?
                WHERE id = ?
            """, (last_message_id, last_timestamp, messages_count, log_id))
            
            conn.commit()
            
        except sqlite3.Error as e:
            self.logger.error(f"Error updating extraction progress: {e}")
        finally:
            conn.close()
    
    def complete_extraction(self, log_id: int, status: str = 'completed', error_message: str = None):
        """Mark extraction as completed or failed"""
        conn = self.get_connection()
        try:
            conn.execute("""
                UPDATE discord_extraction_log 
                SET end_time = ?, status = ?, error_message = ?
                WHERE id = ?
            """, (datetime.utcnow(), status, error_message, log_id))
            
            conn.commit()
            
        except sqlite3.Error as e:
            self.logger.error(f"Error completing extraction: {e}")
        finally:
            conn.close()
    
    def get_last_extraction(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get the last successful extraction for a channel"""
        conn = self.get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM discord_extraction_log 
                WHERE channel_id = ? AND status = 'completed'
                ORDER BY end_time DESC LIMIT 1
            """, (channel_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
            
        except sqlite3.Error as e:
            self.logger.error(f"Error getting last extraction: {e}")
            return None
        finally:
            conn.close()
    
    def update_channel_status(self, channel_id: str, server_id: str, 
                            channel_name: str, total_messages: int = None):
        """Update channel status for monitoring"""
        conn = self.get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO discord_status 
                (channel_id, server_id, channel_name, total_messages, 
                 last_extraction_time, extraction_count, updated_at)
                VALUES (?, ?, ?, ?, ?, 
                       COALESCE((SELECT extraction_count FROM discord_status WHERE channel_id = ?), 0) + 1,
                       CURRENT_TIMESTAMP)
            """, (channel_id, server_id, channel_name, total_messages, 
                  datetime.utcnow(), channel_id))
            
            conn.commit()
            
        except sqlite3.Error as e:
            self.logger.error(f"Error updating channel status: {e}")
        finally:
            conn.close()
    
    def get_channel_stats(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel statistics"""
        conn = self.get_connection()
        try:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_messages,
                    MIN(timestamp) as earliest_message,
                    MAX(timestamp) as latest_message,
                    COUNT(DISTINCT user_id) as unique_users
                FROM discord_messages 
                WHERE channel_id = ?
            """, (channel_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
            
        except sqlite3.Error as e:
            self.logger.error(f"Error getting channel stats: {e}")
            return None
        finally:
            conn.close()

if __name__ == "__main__":
    # Initialize Discord database
    db = DiscordDatabase()
    db.create_discord_tables()
    print("Discord database schema created successfully!")