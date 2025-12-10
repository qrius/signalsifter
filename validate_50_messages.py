#!/usr/bin/env python3
"""
Quick validation script for Discord extraction over 50 messages
"""

import sqlite3
import json
from datetime import datetime

def validate_50_messages():
    """Validate extraction quality over current database"""
    
    print("=== DISCORD EXTRACTION VALIDATION ===")
    print(f"Validation Time: {datetime.now()}")
    
    try:
        conn = sqlite3.connect("data/backfill.sqlite")
        cursor = conn.cursor()
        
        # 1. Basic counts
        cursor.execute("SELECT COUNT(*) FROM discord_messages")
        total_messages = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM discord_messages WHERE content != '' AND content IS NOT NULL")
        messages_with_content = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM discord_messages WHERE username != 'Unknown' AND username IS NOT NULL AND username != ''")
        messages_with_usernames = cursor.fetchone()[0]
        
        # 2. Content analysis
        content_success_rate = (messages_with_content / total_messages * 100) if total_messages > 0 else 0
        username_success_rate = (messages_with_usernames / total_messages * 100) if total_messages > 0 else 0
        
        # 3. Sample messages
        cursor.execute("""
            SELECT username, SUBSTR(content, 1, 80) as preview, timestamp 
            FROM discord_messages 
            ORDER BY rowid DESC 
            LIMIT 10
        """)
        recent_messages = cursor.fetchall()
        
        # 4. Results
        print(f"\n📊 EXTRACTION METRICS:")
        print(f"Total Messages: {total_messages}")
        print(f"Messages with Content: {messages_with_content} ({content_success_rate:.1f}%)")
        print(f"Messages with Usernames: {messages_with_usernames} ({username_success_rate:.1f}%)")
        
        # 5. Success criteria (target: >80% content, >90% usernames)
        content_pass = content_success_rate >= 80
        username_pass = username_success_rate >= 90
        overall_pass = content_pass and username_pass
        
        print(f"\n✅ SUCCESS CRITERIA:")
        print(f"Content Extraction: {'✅ PASS' if content_pass else '❌ FAIL'} ({content_success_rate:.1f}% >= 80%)")
        print(f"Username Extraction: {'✅ PASS' if username_pass else '❌ FAIL'} ({username_success_rate:.1f}% >= 90%)")
        print(f"Overall Status: {'✅ VALIDATION PASSED' if overall_pass else '❌ VALIDATION FAILED'}")
        
        # 6. Sample data
        print(f"\n📋 SAMPLE MESSAGES:")
        for i, (username, content, timestamp) in enumerate(recent_messages[:5], 1):
            print(f"{i}. User: '{username}' | Content: '{content}' | Time: {timestamp}")
        
        # 7. Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if not content_pass:
            print("- Fix content selectors - messages returning empty content")
        if not username_pass:
            print("- Fix username selectors - usernames showing as 'Unknown'")
        if total_messages < 50:
            print(f"- Need more messages for full validation (currently {total_messages}/50)")
        if overall_pass:
            print("- Extraction quality is excellent! Ready for production scale.")
        
        conn.close()
        
        # 8. Return validation result
        return {
            "total_messages": total_messages,
            "content_success_rate": content_success_rate,
            "username_success_rate": username_success_rate,
            "overall_pass": overall_pass,
            "needs_50_messages": total_messages < 50
        }
        
    except Exception as e:
        print(f"❌ Validation Error: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    result = validate_50_messages()
    
    # If we need 50 messages, suggest extraction
    if result.get("needs_50_messages"):
        print(f"\n🔄 NEXT STEP: Run extraction to get 50 messages:")
        print(f"source signalsifter-env/bin/activate && python3 discord_browser_extractor.py --url 'https://discord.com/channels/1296015181985349715/1296015182417629249' --limit 50 --verbose")