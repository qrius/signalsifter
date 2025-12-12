#!/usr/bin/env python3
"""
Monitor historical Discord extraction progress with focus on reaching November 12-26 period
"""

import sqlite3
import time
from datetime import datetime, timedelta
import os

def get_extraction_stats():
    """Get current extraction statistics"""
    db_path = 'data/backfill.sqlite'
    if not os.path.exists(db_path):
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_messages,
                MIN(DATE(timestamp)) as earliest_date,
                MAX(DATE(timestamp)) as latest_date,
                COUNT(DISTINCT username) as unique_users
            FROM discord_messages
        """)
        total_stats = cursor.fetchone()
        
        # Bot vs human breakdown
        cursor.execute("""
            SELECT 
                'Total' as category, COUNT(*) as count
            FROM discord_messages
            UNION ALL
            SELECT 
                'Human' as category, COUNT(*) as count
            FROM discord_messages 
            WHERE username NOT IN ('Dyno', 'STBL') AND (is_bot != 1 OR is_bot IS NULL)
            UNION ALL
            SELECT 
                'Bots (Dyno/STBL)' as category, COUNT(*) as count
            FROM discord_messages 
            WHERE username IN ('Dyno', 'STBL') OR is_bot = 1
        """)
        breakdown = cursor.fetchall()
        
        # Recent messages by date
        cursor.execute("""
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as messages,
                COUNT(CASE WHEN username NOT IN ('Dyno', 'STBL') AND (is_bot != 1 OR is_bot IS NULL) THEN 1 END) as human_msgs
            FROM discord_messages
            GROUP BY DATE(timestamp)
            ORDER BY date ASC
            LIMIT 10
        """)
        daily_stats = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_stats': total_stats,
            'breakdown': breakdown,
            'daily_stats': daily_stats
        }
    except Exception as e:
        print(f"Error querying database: {e}")
        return None

def check_target_period_coverage():
    """Check if we have coverage for November 12-26, 2025"""
    target_start = datetime(2025, 11, 12)
    target_end = datetime(2025, 11, 26)
    
    db_path = 'data/backfill.sqlite'
    if not os.path.exists(db_path):
        return False, None
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as messages_in_target,
                COUNT(CASE WHEN username NOT IN ('Dyno', 'STBL') AND (is_bot != 1 OR is_bot IS NULL) THEN 1 END) as human_msgs_in_target,
                MIN(timestamp) as earliest_in_period,
                MAX(timestamp) as latest_in_period
            FROM discord_messages
            WHERE DATE(timestamp) BETWEEN '2025-11-12' AND '2025-11-26'
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        has_coverage = result[0] > 0 if result else False
        return has_coverage, result
        
    except Exception as e:
        print(f"Error checking target period: {e}")
        return False, None

def main():
    """Monitor extraction with focus on target period"""
    print("🎯 Monitoring Historical Discord Extraction")
    print("Target Period: November 12-26, 2025")
    print("Filtering: Excluding Dyno and STBL bot messages")
    print("-" * 60)
    
    last_total = 0
    start_time = time.time()
    
    while True:
        try:
            stats = get_extraction_stats()
            
            if stats:
                total_messages, earliest, latest, unique_users = stats['total_stats']
                
                # Show progress
                new_messages = total_messages - last_total
                runtime = time.time() - start_time
                
                print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Runtime: {runtime:.0f}s")
                print(f"📊 Total Messages: {total_messages} (+{new_messages})")
                print(f"👥 Unique Users: {unique_users}")
                print(f"📅 Date Range: {earliest} → {latest}")
                
                # Bot breakdown
                print("\n🤖 Message Breakdown:")
                for category, count in stats['breakdown']:
                    print(f"  {category}: {count}")
                
                # Check target period
                has_target, target_stats = check_target_period_coverage()
                if has_target and target_stats:
                    target_total, target_human, target_earliest, target_latest = target_stats
                    print(f"\n🎯 Target Period (Nov 12-26):")
                    print(f"  Messages: {target_total}")
                    print(f"  Human Messages: {target_human}")
                    print(f"  Coverage: {target_earliest} → {target_latest}")
                    
                    if target_human >= 50:  # Reasonable number of human messages
                        print("✅ Target period has sufficient coverage!")
                else:
                    print("\n⏳ Target period not reached yet...")
                
                # Show daily breakdown for earliest dates
                if stats['daily_stats']:
                    print(f"\n📈 Daily Breakdown (Earliest Dates):")
                    for date, total, human in stats['daily_stats']:
                        print(f"  {date}: {total} total, {human} human")
                
                last_total = total_messages
                
            else:
                print("⏳ Waiting for database...")
            
            time.sleep(15)  # Check every 15 seconds
            
        except KeyboardInterrupt:
            print(f"\n\n🛑 Monitoring stopped by user")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()