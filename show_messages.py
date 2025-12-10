#!/usr/bin/env python3
"""
Simple script to display extracted Discord messages
"""

import sqlite3
from datetime import datetime

def main():
    conn = sqlite3.connect("data/backfill.sqlite")
    cursor = conn.cursor()
    
    # Get all messages ordered by timestamp
    cursor.execute("""
        SELECT timestamp, username, content 
        FROM discord_messages 
        ORDER BY timestamp DESC 
        LIMIT 50
    """)
    
    messages = cursor.fetchall()
    
    print(f"=== EXTRACTED DISCORD MESSAGES ({len(messages)} total) ===\n")
    
    for i, (timestamp_str, username, content) in enumerate(messages, 1):
        # Format timestamp
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            time_str = timestamp_str
        
        # Clean content for display
        content_preview = content[:100].replace('\n', ' ') if content else ""
        
        print(f"{i:2d}. [{time_str}] {username}: {content_preview}")
    
    conn.close()

if __name__ == "__main__":
    main()