#!/usr/bin/env python3
"""Check current database status."""

import sqlite3
import os

DB_PATH = "./data/backfill.sqlite"

def check_database():
    """Check current database contents."""
    
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        cursor = conn.cursor()
        
        # Check channels
        cursor.execute("SELECT COUNT(*) FROM channels")
        channel_count = cursor.fetchone()[0]
        print(f"📊 Total channels: {channel_count}")
        
        # List channels
        cursor.execute("SELECT username, title FROM channels")
        channels = cursor.fetchall()
        for username, title in channels:
            print(f"   📺 @{username}: {title}")
        
        # Check messages
        cursor.execute("SELECT COUNT(*) FROM messages")
        message_count = cursor.fetchone()[0]
        print(f"📊 Total messages: {message_count}")
        
        # Check for Sonic English specifically
        cursor.execute("""
            SELECT COUNT(*) FROM messages m 
            JOIN channels c ON m.channel_id = c.id 
            WHERE c.username = 'Sonic_English'
        """)
        sonic_count = cursor.fetchone()[0]
        print(f"🎵 Sonic English messages: {sonic_count}")
        
        if sonic_count > 0:
            cursor.execute("""
                SELECT date, text FROM messages m
                JOIN channels c ON m.channel_id = c.id 
                WHERE c.username = 'Sonic_English'
                ORDER BY date DESC
                LIMIT 3
            """)
            recent = cursor.fetchall()
            print("📝 Recent Sonic messages:")
            for date, text in recent:
                preview = text[:100] + "..." if len(text) > 100 else text
                print(f"   {date}: {preview}")
        
        conn.close()
        print("✅ Database accessible")
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    check_database()