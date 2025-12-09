#!/usr/bin/env python3
"""
Sonic English Channel - Complete Status and Analysis Monitor
"""

import os
import sqlite3
import json
from datetime import datetime

def check_sonic_extraction_status():
    """Monitor Sonic English data extraction progress."""
    
    print("🎵 Sonic English Channel Status Report")
    print("=" * 60)
    
    # Check database
    db_path = "/Users/ll/Sandbox/SignalSifter/data/backfill.sqlite"
    
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            
            # Find Sonic channels
            cur.execute("""
                SELECT tg_id, username, title, created_date 
                FROM channels 
                WHERE username LIKE '%Sonic%' OR title LIKE '%Sonic%'
            """)
            channels = cur.fetchall()
            
            if channels:
                print("✅ Sonic channels in database:")
                for tg_id, username, title, created in channels:
                    print(f"  📊 Channel: {username or 'N/A'}")
                    print(f"      Title: {title}")
                    print(f"      ID: {tg_id}")
                    print(f"      Added: {created}")
                    
                    # Count messages
                    cur.execute("SELECT COUNT(*) FROM messages WHERE channel_id = ?", (tg_id,))
                    total_messages = cur.fetchone()[0]
                    
                    # Count by date range
                    cur.execute("""
                        SELECT DATE(created_date) as date, COUNT(*) as count
                        FROM messages 
                        WHERE channel_id = ?
                        GROUP BY DATE(created_date)
                        ORDER BY date DESC
                        LIMIT 10
                    """, (tg_id,))
                    daily_counts = cur.fetchall()
                    
                    print(f"      📈 Total Messages: {total_messages:,}")
                    
                    if daily_counts:
                        print(f"      📅 Recent Daily Activity:")
                        for date, count in daily_counts:
                            print(f"         {date}: {count:,} messages")
                    
                    # Check processed status
                    cur.execute("SELECT COUNT(*) FROM messages WHERE channel_id = ? AND processed = 1", (tg_id,))
                    processed = cur.fetchone()[0]
                    
                    cur.execute("SELECT COUNT(*) FROM messages WHERE channel_id = ? AND processed = 0", (tg_id,))
                    unprocessed = cur.fetchone()[0]
                    
                    print(f"      ✅ Processed: {processed:,}")
                    print(f"      ⏳ Unprocessed: {unprocessed:,}")
                    
                    if total_messages > 0:
                        completion = (processed / total_messages) * 100
                        print(f"      📊 Processing: {completion:.1f}% complete")
                    
                    print()
                    
            else:
                print("⏳ No Sonic channels found yet (extraction in progress)")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Database check failed: {e}")
    else:
        print("⏳ Database not found (extraction not started)")
    
    # Check output directories
    output_dirs = [
        "/Users/ll/Sandbox/SignalSifter/data/sonic_english",
        "/Users/ll/Sandbox/SignalSifter/data/sonic_english_recent"
    ]
    
    print("\n📁 Output Directory Status:")
    for dir_path in output_dirs:
        if os.path.exists(dir_path):
            files = os.listdir(dir_path)
            print(f"✅ {os.path.basename(dir_path)}: {len(files)} files")
            for file in files:
                file_path = os.path.join(dir_path, file)
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    print(f"    📄 {file}: {size:,} bytes")
        else:
            print(f"⏳ {os.path.basename(dir_path)}: Not created yet")

def prepare_analysis_when_ready():
    """Prepare analysis commands for when data is ready."""
    
    print("\n🔮 Analysis Preparation:")
    print("Once extraction completes, run these commands:")
    
    commands = [
        "# Quick analysis of recent data:",
        ".venv/bin/python analyze_sonic_english.py --quick",
        "",
        "# Full Gemini analysis:",
        ".venv/bin/python scripts/daily_gemini_sync.py --channel Sonic_English",
        "",  
        "# Custom Sonic analysis with extracted data:",
        ".venv/bin/python -c \"",
        "import sqlite3, json",
        "from dotenv import load_dotenv",
        "import google.generativeai as genai",
        "# ... custom analysis code ...",
        "\"",
        "",
        "# Generate comprehensive report:",
        ".venv/bin/python analyze_sonic_english.py --full-report"
    ]
    
    for cmd in commands:
        print(f"  {cmd}")

def show_framework_status():
    """Show analysis framework status."""
    
    framework_file = "/Users/ll/Sandbox/SignalSifter/data/sonic_english/analysis_framework.json"
    
    if os.path.exists(framework_file):
        with open(framework_file, 'r') as f:
            framework = json.load(f)
        
        print(f"\n📋 Analysis Framework:")
        print(f"✅ Channel: {framework['channel']}")
        print(f"✅ URL: {framework['url']}")
        print(f"✅ Period: {framework['extraction_period']}")
        print(f"✅ Focus Areas: {len(framework['analysis_focus'])}")
        
        for focus in framework['analysis_focus']:
            print(f"    • {focus}")
            
        print(f"✅ Created: {framework['created']}")
    else:
        print(f"\n⏳ Analysis framework not yet created")

def main():
    """Main monitoring function."""
    
    check_sonic_extraction_status()
    show_framework_status()
    prepare_analysis_when_ready()
    
    print(f"\n🎯 Summary:")
    print("• Sonic English extraction configured for 6 months of data")
    print("• Analysis framework ready for blockchain/DeFi insights")
    print("• Gemini AI integration prepared for comprehensive analysis") 
    print("• Run this script periodically to monitor progress")
    
    print(f"\n📋 Next Steps:")
    print("1. Monitor extraction progress")
    print("2. Wait for sufficient data (target: 1000+ messages)")
    print("3. Run comprehensive Gemini analysis")
    print("4. Generate Sonic protocol community insights")

if __name__ == "__main__":
    main()