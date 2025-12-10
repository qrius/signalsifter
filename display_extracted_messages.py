#!/usr/bin/env python3
"""
Extract and display timestamp, user, and content from Discord messages
"""

import sqlite3
from datetime import datetime

def display_extracted_messages():
    try:
        conn = sqlite3.connect("data/backfill.sqlite")
        cursor = conn.cursor()
        
        # Get all messages with timestamp, username, content
        cursor.execute("""
            SELECT timestamp, username, content, message_id
            FROM discord_messages 
            ORDER BY timestamp DESC 
            LIMIT 50
        """)
        
        messages = cursor.fetchall()
        
        print(f"=== EXTRACTED MESSAGES ({len(messages)} total) ===")
        print()
        
        for i, (timestamp, username, content, msg_id) in enumerate(messages, 1):
            # Format timestamp
            try:
                if timestamp:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    formatted_time = "No timestamp"
            except:
                formatted_time = timestamp or "No timestamp"
            
            # Clean up content
            content_preview = (content or "").strip()
            if len(content_preview) > 100:
                content_preview = content_preview[:97] + "..."
            
            print(f"{i:2d}. [{formatted_time}] {username}: {content_preview}")
        
        # Summary statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN content != '' AND content IS NOT NULL THEN 1 END) as with_content,
                COUNT(CASE WHEN username != 'Unknown' AND username IS NOT NULL AND username != '' THEN 1 END) as with_usernames,
                COUNT(DISTINCT username) as unique_users
            FROM discord_messages
        """)
        
        total, with_content, with_usernames, unique_users = cursor.fetchone()
        
        print(f"\n=== EXTRACTION SUMMARY ===")
        print(f"Total messages: {total}")
        print(f"With content: {with_content} ({(with_content/total*100) if total > 0 else 0:.1f}%)")
        print(f"With usernames: {with_usernames} ({(with_usernames/total*100) if total > 0 else 0:.1f}%)")
        print(f"Unique users: {unique_users}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    display_extracted_messages()