#!/usr/bin/env python3
"""
Simple Discord Extraction Test
Test the updated Discord extraction without full dependencies
"""

import sqlite3
import json
import sys
import os

def test_current_extraction():
    """Test what we have in the database and simulate improved extraction"""
    
    print("🧪 DISCORD EXTRACTION TEST")
    print("=" * 50)
    
    DB_PATH = "data/backfill.sqlite"
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found: {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        cursor = conn.cursor()
        
        # Check current messages
        cursor.execute("SELECT COUNT(*) as total FROM discord_messages")
        total = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as with_content FROM discord_messages WHERE content IS NOT NULL AND content != '' AND length(content) > 0")
        with_content = cursor.fetchone()['with_content']
        
        cursor.execute("SELECT COUNT(*) as unknown_users FROM discord_messages WHERE username = 'Unknown' OR username IS NULL")
        unknown_users = cursor.fetchone()['unknown_users']
        
        print(f"📊 Current Database Status:")
        print(f"   Total messages: {total}")
        print(f"   Messages with content: {with_content}")
        print(f"   Messages with unknown users: {unknown_users}")
        print()
        
        if total == 0:
            print("❌ No messages in database. Need to run extraction first.")
            return False
        
        # Get sample message to analyze structure
        cursor.execute("SELECT * FROM discord_messages LIMIT 1")
        sample = cursor.fetchone()
        
        print(f"📝 Sample Message Analysis:")
        print(f"   Message ID: {sample['message_id']}")
        print(f"   Username: '{sample['username']}'")
        print(f"   Content length: {len(sample['content'] or '')}")
        print(f"   Timestamp: {sample['timestamp']}")
        print()
        
        # Simulate what extraction should find
        print("🔍 Extraction Issues Detected:")
        
        issues = []
        if with_content == 0:
            issues.append("❌ No message content extracted - CSS selectors failed")
        
        if unknown_users == total:
            issues.append("❌ All usernames are 'Unknown' - username selectors failed")
        
        if not issues:
            issues.append("✅ Extraction appears to be working correctly")
        
        for issue in issues:
            print(f"   {issue}")
        
        print()
        
        # Recommendations
        print("🛠️  RECOMMENDED FIXES:")
        
        if with_content == 0:
            print("   1. Update content selectors:")
            print("      - Try: .messageContent-2t3eCI")
            print("      - Try: .markup-eYLPri") 
            print("      - Try: div[id^=\"message-content-\"]")
        
        if unknown_users == total:
            print("   2. Update username selectors:")
            print("      - Try: .username-h_Y3Us")
            print("      - Try: .headerText-2z4IhQ .username-h_Y3Us")
        
        print("   3. Test with updated selectors in discord_browser_extractor.py")
        print("   4. Re-run extraction: python3 discord_browser_extractor.py --url <URL> --limit 5")
        
        return True
        
    finally:
        conn.close()

def simulate_fixed_extraction():
    """Simulate what the extraction should produce with working selectors"""
    
    print("\n🎯 SIMULATION: What Fixed Extraction Should Produce")
    print("=" * 60)
    
    # Simulate realistic Discord data
    simulated_messages = [
        {
            'message_id': 'chat-messages-1296015182417629249-1440348309691699286',
            'username': 'CryptoTrader42',
            'content': 'Hey everyone! Just saw some interesting movement in the market today',
            'timestamp': '2025-11-18 14:29:57.408000+00:00'
        },
        {
            'message_id': 'chat-messages-1296015182417629249-1440348446253912138', 
            'username': 'BlockchainBob',
            'content': 'Yeah I noticed that too. The volume has been pretty high lately',
            'timestamp': '2025-11-18 14:30:29.967000+00:00'
        },
        {
            'message_id': 'chat-messages-1296015182417629249-1440348524322623599',
            'username': 'CryptoTrader42', 
            'content': 'Anyone have thoughts on the recent developments? 🚀',
            'timestamp': '2025-11-18 14:30:48.580000+00:00'
        }
    ]
    
    print("📝 Expected Message Examples:")
    for i, msg in enumerate(simulated_messages, 1):
        print(f"\n   Message {i}:")
        print(f"   👤 Username: {msg['username']}")
        print(f"   💬 Content: {msg['content']}")
        print(f"   ⏰ Timestamp: {msg['timestamp']}")
    
    print(f"\n✅ With working selectors, you should see:")
    print(f"   - Real usernames instead of 'Unknown'")
    print(f"   - Actual message content instead of empty strings")
    print(f"   - Proper conversation flow")
    
    print(f"\n📤 This would then export to NotebookLM as:")
    print(f"   - Rich conversation analysis")
    print(f"   - User interaction patterns") 
    print(f"   - Actual discussable content for AI analysis")

if __name__ == "__main__":
    success = test_current_extraction()
    if success:
        simulate_fixed_extraction()
    
    print(f"\n🎯 NEXT STEPS:")
    print(f"1. The CSS selectors have been updated in discord_browser_extractor.py")
    print(f"2. Test with: python3 discord_browser_extractor.py --url <DISCORD_URL> --limit 3")  
    print(f"3. Check if content and usernames are now captured")
    print(f"4. If working, re-export for NotebookLM with real content")