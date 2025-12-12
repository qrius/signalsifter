#!/usr/bin/env python3
"""Simple Discord Analysis - Quick Stats"""

import sqlite3
import sys

def analyze_discord_data():
    try:
        # Connect to database
        conn = sqlite3.connect('data/backfill.sqlite')
        cursor = conn.cursor()
        
        print("=" * 50)
        print("DISCORD DATA ANALYSIS SUMMARY")
        print("=" * 50)
        
        # Basic stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_messages,
                COUNT(DISTINCT username) as unique_users,
                MIN(DATE(timestamp)) as earliest_date,
                MAX(DATE(timestamp)) as latest_date,
                COUNT(*) FILTER (WHERE content IS NOT NULL AND content != '') as messages_with_content
            FROM discord_messages
        """)
        
        basic_stats = cursor.fetchone()
        
        print(f"📊 Total Messages: {basic_stats[0]:,}")
        print(f"👥 Unique Users: {basic_stats[1]}")
        print(f"📅 Date Range: {basic_stats[2]} to {basic_stats[3]}")
        print(f"💬 Messages with Content: {basic_stats[4]:,}")
        
        # Top users
        print(f"\n🏆 TOP ACTIVE USERS:")
        cursor.execute("""
            SELECT username, COUNT(*) as msg_count
            FROM discord_messages 
            GROUP BY username 
            ORDER BY msg_count DESC 
            LIMIT 5
        """)
        
        for i, (username, count) in enumerate(cursor.fetchall(), 1):
            print(f"   {i}. {username}: {count} messages")
        
        # Daily activity (last 7 days)
        print(f"\n📈 RECENT DAILY ACTIVITY:")
        cursor.execute("""
            SELECT DATE(timestamp) as date, COUNT(*) as messages
            FROM discord_messages 
            GROUP BY DATE(timestamp) 
            ORDER BY date DESC 
            LIMIT 7
        """)
        
        for date, count in cursor.fetchall():
            print(f"   {date}: {count} messages")
        
        # Content analysis
        print(f"\n📝 CONTENT ANALYSIS:")
        cursor.execute("""
            SELECT 
                AVG(LENGTH(content)) as avg_length,
                MAX(LENGTH(content)) as max_length
            FROM discord_messages 
            WHERE content IS NOT NULL AND content != ''
        """)
        
        content_stats = cursor.fetchone()
        if content_stats[0]:
            print(f"   Average message length: {content_stats[0]:.1f} characters")
            print(f"   Longest message: {content_stats[1]} characters")
        
        conn.close()
        print(f"\n✅ Analysis complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = analyze_discord_data()
    sys.exit(0 if success else 1)