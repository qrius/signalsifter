#!/usr/bin/env python3
"""Quick script to check database status and unlock if needed."""

import sqlite3
import os
import sys
import time

db_path = "/Users/ll/Sandbox/SignalSifter/data/backfill.sqlite"

print(f"Checking database: {db_path}")
print(f"File exists: {os.path.exists(db_path)}")
print(f"File size: {os.path.getsize(db_path)} bytes")

try:
    # Try to connect with a short timeout
    conn = sqlite3.connect(db_path, timeout=5)
    
    # Try a simple query
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM channels;")
    channel_count = cursor.fetchone()[0]
    print(f"✅ Database accessible! Found {channel_count} channels")
    
    # Check for messages
    cursor.execute("SELECT COUNT(*) FROM messages;")
    message_count = cursor.fetchone()[0]
    print(f"✅ Found {message_count} messages")
    
    # Check for Sonic English specifically
    cursor.execute("SELECT COUNT(*) FROM messages WHERE channel_id = (SELECT id FROM channels WHERE username = 'Sonic_English');")
    sonic_count = cursor.fetchone()[0]
    print(f"✅ Found {sonic_count} Sonic English messages")
    
    conn.close()
    print("✅ Database check complete - no locks detected")
    
except sqlite3.OperationalError as e:
    if "database is locked" in str(e):
        print(f"❌ Database is locked: {e}")
        print("Attempting to force unlock...")
        
        try:
            # Try to unlock by opening and immediately closing
            conn = sqlite3.connect(db_path, timeout=1)
            conn.execute("BEGIN IMMEDIATE;")
            conn.rollback()
            conn.close()
            print("✅ Unlock attempt completed")
        except Exception as unlock_e:
            print(f"❌ Unlock failed: {unlock_e}")
    else:
        print(f"❌ Database error: {e}")
        
except Exception as e:
    print(f"❌ Unexpected error: {e}")