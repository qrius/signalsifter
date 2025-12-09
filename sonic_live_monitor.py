#!/usr/bin/env python3
"""
Live Sonic English Data Monitor and Quick Analysis
Run this while extraction is in progress
"""

import os
import sqlite3
import time
from datetime import datetime

def monitor_sonic_extraction():
    """Monitor Sonic English extraction progress in real-time."""
    
    print("🎵 Sonic English - Live Extraction Monitor")
    print("=" * 60)
    
    db_path = "data/backfill.sqlite"
    
    while True:
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                
                # Find Sonic channels
                cur.execute("""
                    SELECT tg_id, username, title 
                    FROM channels 
                    WHERE username LIKE '%Sonic%' OR title LIKE '%Sonic%'
                """)
                sonic_channels = cur.fetchall()
                
                if sonic_channels:
                    for tg_id, username, title in sonic_channels:
                        print(f"\n📊 Channel: {username}")
                        print(f"    Title: {title}")
                        
                        # Count total messages
                        cur.execute("SELECT COUNT(*) FROM messages WHERE channel_id = ?", (tg_id,))
                        total = cur.fetchone()[0]
                        
                        # Count processed
                        cur.execute("SELECT COUNT(*) FROM messages WHERE channel_id = ? AND processed = 1", (tg_id,))
                        processed = cur.fetchone()[0]
                        
                        # Recent messages (last hour) 
                        cur.execute("""
                            SELECT COUNT(*) FROM messages 
                            WHERE channel_id = ? AND date > datetime('now', '-1 hour')
                        """, (tg_id,))
                        recent = cur.fetchone()[0]
                        
                        # Latest message
                        cur.execute("""
                            SELECT date, text 
                            FROM messages 
                            WHERE channel_id = ? 
                            ORDER BY date DESC 
                            LIMIT 1
                        """, (tg_id,))
                        latest = cur.fetchone()
                        
                        print(f"    📈 Total Messages: {total:,}")
                        print(f"    ✅ Processed: {processed:,}")
                        print(f"    🕐 Last Hour: {recent:,}")
                        
                        if latest:
                            date, message_text = latest
                            preview = message_text[:100] + "..." if message_text and len(message_text) > 100 else (message_text or "No text")
                            print(f"    📄 Latest: {date}")
                            print(f"         {preview}")
                        
                        # Calculate extraction rate
                        if total > 0:
                            completion = (processed / total) * 100
                            print(f"    🎯 Processing: {completion:.1f}% complete")
                else:
                    print("⏳ Sonic English channel not detected yet...")
                
                conn.close()
                
            except Exception as e:
                print(f"❌ Database error: {e}")
        else:
            print("⏳ Database not created yet...")
        
        print(f"\n🕒 {datetime.now().strftime('%H:%M:%S')} - Checking again in 30 seconds...")
        print("-" * 60)
        
        # Wait 30 seconds before next check
        time.sleep(30)

if __name__ == "__main__":
    try:
        monitor_sonic_extraction()
    except KeyboardInterrupt:
        print(f"\n\n✅ Monitoring stopped.")
        print("📋 To resume: python sonic_live_monitor.py")
        print("🔍 To analyze data: python analyze_sonic_english.py")