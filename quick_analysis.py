#!/usr/bin/env python3
import sqlite3
from datetime import datetime

# Quick Discord content summary
conn = sqlite3.connect('discord_data.db')
cursor = conn.cursor()

# Get basic counts
cursor.execute('SELECT COUNT(*) FROM discord_messages')
total = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM discord_messages WHERE content IS NOT NULL AND content != ""')
with_content = cursor.fetchone()[0]

print(f"📊 EXTRACTION SUMMARY:")
print(f"Total messages: {total}")
print(f"With content: {with_content}")

if with_content > 0:
    # Date range
    cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM discord_messages')
    dates = cursor.fetchone()
    min_date, max_date = dates
    
    min_dt = datetime.fromisoformat(min_date.replace('Z', '+00:00'))
    max_dt = datetime.fromisoformat(max_date.replace('Z', '+00:00'))
    
    print(f"Date range: {min_dt.strftime('%Y-%m-%d')} to {max_dt.strftime('%Y-%m-%d')}")
    print(f"Time span: {(max_dt - min_dt).days} days")
    
    # Top users
    cursor.execute('SELECT username, COUNT(*) FROM discord_messages GROUP BY username ORDER BY COUNT(*) DESC LIMIT 5')
    print("\nTop users:")
    for username, count in cursor.fetchall():
        print(f"  {username}: {count} messages")
    
    # Sample messages
    cursor.execute('SELECT username, content, timestamp FROM discord_messages WHERE content IS NOT NULL ORDER BY timestamp DESC LIMIT 3')
    print("\nRecent messages:")
    for username, content, timestamp in cursor.fetchall():
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        preview = content[:50] + "..." if len(content) > 50 else content
        print(f"  {dt.strftime('%m-%d')} {username}: {preview}")

conn.close()