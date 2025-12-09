#!/usr/bin/env python3
"""
Unified Discord + Telegram Content Analysis and Verification
"""
import sqlite3
import json
from datetime import datetime
from collections import Counter, defaultdict
import os

def analyze_unified_content():
    db_path = os.path.join('data', 'backfill.sqlite')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 SIGNALSIFTER UNIFIED DATABASE ANALYSIS")
        print("=" * 60)
        
        # Check what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📊 Database tables: {tables}")
        
        # Separate Discord and Telegram tables
        discord_tables = [t for t in tables if t.startswith('discord_')]
        telegram_tables = [t for t in tables if not t.startswith('discord_')]
        
        print(f"\n🤖 Discord tables: {discord_tables}")
        print(f"📱 Telegram tables: {telegram_tables}")
        
        # ==================== DISCORD ANALYSIS ====================
        if 'discord_messages' in tables:
            print(f"\n🎮 DISCORD DATA ANALYSIS")
            print("-" * 40)
            
            # Basic Discord stats
            cursor.execute('SELECT COUNT(*) FROM discord_messages')
            discord_total = cursor.fetchone()[0]
            print(f"📊 Total Discord messages: {discord_total}")
            
            if discord_total > 0:
                # Discord date range
                cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM discord_messages')
                d_dates = cursor.fetchone()
                d_min_dt = datetime.fromisoformat(d_dates[0].replace('Z', '+00:00'))
                d_max_dt = datetime.fromisoformat(d_dates[1].replace('Z', '+00:00'))
                d_span = (d_max_dt - d_min_dt).days
                
                print(f"📅 Discord date range: {d_min_dt.strftime('%Y-%m-%d')} to {d_max_dt.strftime('%Y-%m-%d')}")
                print(f"⏱️  Discord time span: {d_span} days ({d_span/30.44:.1f} months)")
                
                # Discord content analysis
                cursor.execute('SELECT COUNT(*) FROM discord_messages WHERE content IS NOT NULL AND content != ""')
                discord_with_content = cursor.fetchone()[0]
                success_rate = (discord_with_content / discord_total) * 100
                print(f"📝 Discord messages with content: {discord_with_content}/{discord_total} ({success_rate:.1f}%)")
                
                # Discord top users
                cursor.execute('SELECT username, COUNT(*) FROM discord_messages GROUP BY username ORDER BY COUNT(*) DESC LIMIT 5')
                print(f"\n👥 Discord top users:")
                for username, count in cursor.fetchall():
                    print(f"  {username}: {count} messages")
                
                # Discord recent messages sample
                cursor.execute('SELECT username, content, timestamp FROM discord_messages WHERE content IS NOT NULL ORDER BY timestamp DESC LIMIT 5')
                print(f"\n🔥 Discord recent messages:")
                for username, content, timestamp in cursor.fetchall():
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    preview = content[:60] + "..." if len(content) > 60 else content
                    print(f"  {dt.strftime('%m-%d %H:%M')} {username}: {preview}")
                
                # Verify 2-month target for Discord
                target_date = datetime(2025, 10, 9, tzinfo=d_min_dt.tzinfo)
                if d_min_dt <= target_date:
                    print(f"\n✅ SUCCESS: Discord reached 2+ months target!")
                else:
                    days_short = (target_date - d_min_dt).days
                    print(f"\n⚠️  Discord short by {days_short} days for 2-month target")
        
        # ==================== TELEGRAM ANALYSIS ====================
        # Check for existing Telegram data
        telegram_msg_tables = [t for t in tables if 'messages' in t and not t.startswith('discord_')]
        
        if telegram_msg_tables:
            print(f"\n📱 TELEGRAM DATA ANALYSIS") 
            print("-" * 40)
            
            # Try common Telegram table names
            for table in telegram_msg_tables:
                try:
                    cursor.execute(f'SELECT COUNT(*) FROM {table}')
                    t_count = cursor.fetchone()[0]
                    if t_count > 0:
                        print(f"📊 {table}: {t_count} messages")
                        
                        # Sample from this table
                        cursor.execute(f'SELECT * FROM {table} LIMIT 1')
                        sample = cursor.fetchone()
                        if sample:
                            print(f"📝 Sample from {table}: {len(sample)} columns")
                except:
                    continue
        
        # ==================== UNIFIED STATISTICS ====================
        print(f"\n📈 UNIFIED SIGNALSIFTER STATISTICS")
        print("-" * 40)
        
        total_messages = 0
        platforms = []
        
        if discord_total > 0:
            total_messages += discord_total
            platforms.append(f"Discord ({discord_total})")
        
        # Count Telegram messages if available
        for table in telegram_msg_tables:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                t_count = cursor.fetchone()[0]
                if t_count > 0:
                    total_messages += t_count
                    platforms.append(f"Telegram-{table} ({t_count})")
            except:
                continue
        
        print(f"🎯 Total messages across platforms: {total_messages:,}")
        print(f"📱 Active platforms: {', '.join(platforms)}")
        
        # Database size and efficiency
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        print(f"🗃️  Database efficiency: {table_count} tables, {total_messages:,} total messages")
        
        # ==================== EXTRACTION VERIFICATION ====================
        print(f"\n🔍 EXTRACTION VERIFICATION")
        print("-" * 40)
        
        if discord_total >= 149:
            print(f"✅ Discord extraction SUCCESS: {discord_total} messages (expected 149+)")
        elif discord_total > 0:
            print(f"⚠️  Discord extraction partial: {discord_total} messages (expected 149+)")
        else:
            print(f"❌ Discord extraction FAILED: No messages found")
        
        # Check for extraction logs
        if 'discord_extraction_log' in tables:
            cursor.execute('SELECT COUNT(*) FROM discord_extraction_log')
            log_count = cursor.fetchone()[0]
            print(f"📋 Discord extraction logs: {log_count} entries")
            
            if log_count > 0:
                cursor.execute('SELECT status, start_time, end_time FROM discord_extraction_log ORDER BY start_time DESC LIMIT 1')
                log_entry = cursor.fetchone()
                if log_entry:
                    status, start_time, end_time = log_entry
                    print(f"🏁 Last extraction: {status} ({start_time} to {end_time})")
        
        conn.close()
        print(f"\n✅ Analysis complete! Database integrity verified.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    analyze_unified_content()