#!/usr/bin/env python3
"""Quick database status check"""

import sqlite3
from datetime import datetime

def check_db_status():
    try:
        conn = sqlite3.connect("data/backfill.sqlite")
        cursor = conn.cursor()
        
        # Total messages
        cursor.execute("SELECT COUNT(*) FROM discord_messages")
        total = cursor.fetchone()[0]
        
        # Messages with content (not empty)
        cursor.execute("SELECT COUNT(*) FROM discord_messages WHERE content != '' AND content IS NOT NULL")
        with_content = cursor.fetchone()[0]
        
        # Messages with usernames (not Unknown)
        cursor.execute("SELECT COUNT(*) FROM discord_messages WHERE username != 'Unknown' AND username IS NOT NULL AND username != ''")
        with_usernames = cursor.fetchone()[0]
        
        # Recent messages
        cursor.execute("SELECT username, SUBSTR(content, 1, 60) as preview FROM discord_messages ORDER BY rowid DESC LIMIT 3")
        recent = cursor.fetchall()
        
        print(f"=== Database Status ===")
        print(f"Total messages: {total}")
        print(f"With content: {with_content} ({(with_content/total*100) if total > 0 else 0:.1f}%)")
        print(f"With usernames: {with_usernames} ({(with_usernames/total*100) if total > 0 else 0:.1f}%)")
        print(f"\n=== Recent Messages ===")
        for i, (username, content) in enumerate(recent, 1):
            print(f"{i}. User: '{username}' | Content: '{content}'")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db_status()