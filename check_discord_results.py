#!/usr/bin/env python3
"""
Quick Discord extraction results checker
"""
import sqlite3
from datetime import datetime

def check_results():
    try:
        conn = sqlite3.connect('discord_data.db')
        cursor = conn.cursor()
        
        # Get message count
        cursor.execute('SELECT COUNT(*) FROM discord_messages')
        count = cursor.fetchone()[0]
        print(f"✅ Total messages extracted: {count}")
        
        if count > 0:
            # Get date range
            cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM discord_messages')
            dates = cursor.fetchone()
            min_date, max_date = dates
            
            # Parse dates
            min_dt = datetime.fromisoformat(min_date.replace('Z', '+00:00'))
            max_dt = datetime.fromisoformat(max_date.replace('Z', '+00:00'))
            span_days = (max_dt - min_dt).days
            
            print(f"📅 Date range: {min_dt.strftime('%Y-%m-%d')} to {max_dt.strftime('%Y-%m-%d')}")
            print(f"⏱️  Time span: {span_days} days ({span_days/30.44:.1f} months)")
            
            # Content success rate
            cursor.execute('SELECT COUNT(*) FROM discord_messages WHERE content IS NOT NULL AND content != ""')
            with_content = cursor.fetchone()[0]
            success_rate = (with_content / count) * 100
            print(f"📝 Messages with content: {with_content}/{count} ({success_rate:.1f}%)")
            
            # Check if we reached 2 months target (Oct 9, 2025)
            target_date = datetime(2025, 10, 9, tzinfo=min_dt.tzinfo)
            if min_dt <= target_date:
                print("🎯 SUCCESS: Reached 2+ months of chat history!")
            else:
                days_short = (target_date - min_dt).days
                print(f"⚠️  SHORT: Missing {days_short} days to reach full 2 months")
            
            # Show recent samples
            cursor.execute('SELECT username, content, timestamp FROM discord_messages ORDER BY timestamp DESC LIMIT 3')
            recent = cursor.fetchall()
            print(f"\n🔥 Most recent messages:")
            for username, content, timestamp in recent:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                content_preview = (content[:50] + '...') if content and len(content) > 50 else content or '[No content]'
                print(f"  {dt.strftime('%m-%d %H:%M')} {username}: {content_preview}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_results()