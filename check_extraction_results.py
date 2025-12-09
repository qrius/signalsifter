#!/usr/bin/env python3
"""Check extraction results in database."""

import sqlite3
from datetime import datetime

def check_extraction_results():
    print("📊 CHECKING EXTRACTION RESULTS")
    print("=" * 40)
    
    try:
        conn = sqlite3.connect("data/backfill.sqlite")
        cursor = conn.cursor()
        
        # Check total messages
        cursor.execute("SELECT COUNT(*) FROM messages")
        total_messages = cursor.fetchone()[0]
        print(f"📈 Total messages in database: {total_messages}")
        
        # Check total channels
        cursor.execute("SELECT COUNT(*) FROM channels")
        total_channels = cursor.fetchone()[0]
        print(f"📺 Total channels in database: {total_channels}")
        
        # List channels
        cursor.execute("SELECT username, title FROM channels WHERE username IS NOT NULL")
        channels = cursor.fetchall()
        print(f"\n📋 Channels:")
        for username, title in channels:
            print(f"   @{username}: {title}")
        
        # Check for Sonic English specifically
        cursor.execute("""
            SELECT COUNT(*) FROM messages m 
            JOIN channels c ON m.channel_id = c.tg_id 
            WHERE c.username = 'Sonic_English'
        """)
        sonic_messages = cursor.fetchone()[0]
        print(f"\n🎵 Sonic English messages: {sonic_messages}")
        
        if sonic_messages > 0:
            # Get sample Sonic messages
            cursor.execute("""
                SELECT m.date, m.sender_username, m.text FROM messages m
                JOIN channels c ON m.channel_id = c.tg_id 
                WHERE c.username = 'Sonic_English' AND m.text != ''
                ORDER BY m.date DESC 
                LIMIT 5
            """)
            samples = cursor.fetchall()
            
            print(f"\n📝 Recent Sonic English messages:")
            for i, (date, sender, text) in enumerate(samples, 1):
                preview = text[:60] + "..." if len(text) > 60 else text
                print(f"   {i}. [{sender or 'Unknown'}] {preview}")
        
        conn.close()
        
        if total_messages > 0:
            print(f"\n✅ EXTRACTION SUCCESSFUL!")
            print(f"   💾 {total_messages} total messages extracted")
            print(f"   🎵 {sonic_messages} Sonic English messages")
            return True
        else:
            print(f"\n⚠️  No messages found in database")
            return False
            
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

if __name__ == "__main__":
    success = check_extraction_results()
    print(f"\n🎯 Database Status: {'HAS DATA' if success else 'EMPTY'}")