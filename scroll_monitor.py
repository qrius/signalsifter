#!/usr/bin/env python3
"""
Simple scroll monitoring - monitors database while you manually scroll
"""

import sqlite3
import time
from datetime import datetime
import os

def monitor_extraction_progress():
    """Monitor database changes while user manually scrolls"""
    db_path = 'data/backfill.sqlite'
    
    print("🎯 MANUAL SCROLL MONITOR")
    print("=" * 50)
    print("Instructions:")
    print("1. Open Discord in your browser and navigate to STBL channel")
    print("2. Scroll UP slowly to load older messages (past Nov 18)")
    print("3. Run the automated extractor in another terminal while scrolling")
    print("4. This monitor will show progress in real-time")
    print("5. Press Ctrl+C when done")
    print("")
    
    if not os.path.exists(db_path):
        print("❌ Database not found. Please run an extraction first.")
        return
    
    last_count = 0
    last_earliest = None
    
    try:
        while True:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get current stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    MIN(DATE(timestamp)) as earliest_date,
                    MAX(DATE(timestamp)) as latest_date,
                    COUNT(DISTINCT username) as unique_users,
                    COUNT(CASE WHEN username NOT IN ('Dyno', 'STBL') AND (is_bot != 1 OR is_bot IS NULL) THEN 1 END) as human_messages
                FROM discord_messages
            """)
            
            total, earliest, latest, users, human = cursor.fetchone()
            
            # Check November 12-26 target period
            cursor.execute("""
                SELECT COUNT(*) FROM discord_messages 
                WHERE DATE(timestamp) BETWEEN '2025-11-12' AND '2025-11-26'
            """)
            target_period_count = cursor.fetchone()[0]
            
            # Get earliest actual timestamp
            cursor.execute("SELECT MIN(timestamp) FROM discord_messages")
            earliest_timestamp = cursor.fetchone()[0]
            
            conn.close()
            
            # Show progress if changed
            if total != last_count or earliest != last_earliest:
                print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')}")
                print(f"📊 Total Messages: {total} (+{total - last_count})")
                print(f"👥 Unique Users: {users}")
                print(f"🤖 Human Messages: {human}")
                print(f"📅 Date Range: {earliest} → {latest}")
                print(f"🕐 Earliest Time: {earliest_timestamp}")
                print(f"🎯 Nov 12-26 Period: {target_period_count} messages")
                
                # Check if we reached target
                if earliest and earliest <= '2025-11-18':
                    print("✅ SUCCESS! Reached November 18th or earlier!")
                    if target_period_count >= 20:
                        print("🎉 Target period has good coverage!")
                elif earliest:
                    days_to_go = (datetime.strptime(earliest, '%Y-%m-%d') - datetime(2025, 11, 18)).days
                    print(f"⏳ Need to go back {days_to_go} more days to reach Nov 18")
                
                last_count = total
                last_earliest = earliest
            else:
                print(".", end="", flush=True)  # Progress indicator when no changes
            
            time.sleep(3)  # Check every 3 seconds
            
    except KeyboardInterrupt:
        print(f"\n\n🛑 Monitoring stopped")
        print(f"Final status: {total} messages, earliest: {earliest}")

if __name__ == "__main__":
    monitor_extraction_progress()