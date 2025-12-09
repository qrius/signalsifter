#!/usr/bin/env python3
"""
Quick Discord extraction progress checker
"""

import sqlite3
import os
from datetime import datetime

def check_progress():
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'backfill.sqlite')
    
    if not os.path.exists(db_path):
        print("❌ Database not found. No extractions yet.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if Discord tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'discord%'")
    tables = cursor.fetchall()
    
    if not tables:
        print("❌ No Discord tables found. Run extraction first.")
        return
    
    print("🔍 Discord Extraction Progress Report")
    print("=" * 50)
    
    # Messages count
    cursor.execute("SELECT COUNT(*) FROM discord_messages")
    msg_count = cursor.fetchone()[0]
    print(f"📊 Total Messages Extracted: {msg_count}")
    
    if msg_count == 0:
        print("⚠️  No messages found. Check if extraction is running.")
        return
    
    # Date range
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM discord_messages")
    date_range = cursor.fetchone()
    if date_range[0]:
        print(f"📅 Date Range: {date_range[0]} to {date_range[1]}")
    
    # Channel info
    cursor.execute("""
        SELECT server_id, channel_id, COUNT(*) as messages 
        FROM discord_messages 
        GROUP BY server_id, channel_id
    """)
    channels = cursor.fetchall()
    
    print(f"\n🏢 Channels ({len(channels)}):")
    for server_id, channel_id, count in channels:
        print(f"  • Server {server_id}, Channel {channel_id}: {count} messages")
    
    # Recent extraction logs with actual message counts
    cursor.execute("""
        SELECT 
            el.status, 
            el.start_time, 
            el.end_time, 
            COALESCE(
                (SELECT COUNT(*) FROM discord_messages dm WHERE dm.channel_id = el.channel_id),
                el.messages_extracted,
                0
            ) as actual_messages,
            el.error_message,
            el.channel_id
        FROM discord_extraction_log el
        ORDER BY el.start_time DESC LIMIT 5
    """)
    logs = cursor.fetchall()
    
    if logs:
        print(f"\n📝 Recent Extractions:")
        for status, start, end, count, error, channel_id in logs:
            end_info = end if end else "Running..."
            error_info = f" (Error: {error})" if error else ""
            channel_info = f" [Channel: {channel_id}]" if channel_id else ""
            print(f"  • {status.upper()}: {start} → {end_info} ({count} messages){error_info}{channel_info}")
    
    conn.close()
    print("\n✅ Progress check complete!")

if __name__ == "__main__":
    check_progress()