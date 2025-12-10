#!/usr/bin/env python3
import sqlite3
import os
from datetime import datetime

def verify_extraction():
    db_path = os.path.join('data', 'backfill.sqlite')
    
    if not os.path.exists(db_path):
        print("❌ Database not found")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📊 Database tables ({len(tables)}): {', '.join(tables)}")
        
        # Check Discord specifically
        discord_tables = [t for t in tables if 'discord' in t]
        if discord_tables:
            print(f"🎮 Discord tables: {', '.join(discord_tables)}")
            
            if 'discord_messages' in tables:
                cursor.execute('SELECT COUNT(*) FROM discord_messages')
                count = cursor.fetchone()[0]
                print(f"✅ Discord messages extracted: {count}")
                
                if count > 0:
                    # Get date range
                    cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM discord_messages')
                    dates = cursor.fetchone()
                    print(f"📅 Date range: {dates[0]} to {dates[1]}")
                    
                    # Sample messages
                    cursor.execute('SELECT username, content FROM discord_messages WHERE content IS NOT NULL LIMIT 3')
                    print("📝 Sample messages:")
                    for username, content in cursor.fetchall():
                        preview = content[:60] + "..." if len(content) > 60 else content
                        print(f"  {username}: {preview}")
            else:
                print("⚠️ discord_messages table not found")
        else:
            print("❌ No Discord tables found")
        
        # Check Telegram data too
        telegram_tables = [t for t in tables if 'messages' in t and 'discord' not in t]
        if telegram_tables:
            print(f"📱 Telegram tables: {', '.join(telegram_tables)}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_extraction()