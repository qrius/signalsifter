#!/usr/bin/env python3
"""
Discord Channel Pipeline Runner
Coordinates browser extraction → processing → analysis for Discord channels.
Updated to use Playwright browser automation instead of bot API.

Usage:
  python run_discord_pipeline.py --url "https://discord.com/channels/1296015181985349715/1356175241172488314"
  python run_discord_pipeline.py --url "https://discord.com/channels/1296015181985349715/1356175241172488314" --months 6
  python run_discord_pipeline.py --url "https://discord.com/channels/1296015181985349715/1356175241172488314" --skip-extraction --analysis-only
  python run_discord_pipeline.py --browser-extract --url "discord_url" --full-pipeline

Environment variables (in `.env`):
  DISCORD_EMAIL          # Discord account email
  DISCORD_PASSWORD       # Discord account password
  GEMINI_API_KEY         # Google AI Studio API key  
  SQLITE_DB_PATH         # SQLite database path
"""

import os
import sys
import argparse
import asyncio
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Add current directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

load_dotenv()

def parse_discord_url(url: str):
    """Parse Discord URL to extract guild_id and channel_id"""
    import re
    
    pattern = r'https://discord\.com/channels/(\d+)/(\d+)(?:/(\d+))?'
    match = re.match(pattern, url)
    
    if match:
        return int(match.group(1)), int(match.group(2))
    
    raise ValueError(f"Invalid Discord URL format: {url}")

def check_requirements():
    """Check that required environment variables are set"""
    missing = []
    
    if not os.getenv("DISCORD_EMAIL"):
        missing.append("DISCORD_EMAIL")
    
    if not os.getenv("DISCORD_PASSWORD"):
        missing.append("DISCORD_PASSWORD")
    
    if not os.getenv("GEMINI_API_KEY"):
        missing.append("GEMINI_API_KEY")
    
    if missing:
        print("❌ Missing required environment variables:")
        for var in missing:
            print(f"  - {var}")
        print("\nPlease add these to your .env file")
        return False
    
    return True

def run_command(cmd, description, check_result=True):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=check_result)
        
        if result.stdout:
            print("Output:", result.stdout.strip())
        
        if result.stderr and check_result:
            print("Errors:", result.stderr.strip())
            
        return result.returncode == 0
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}")
        if e.stdout:
            print("Output:", e.stdout.strip())
        if e.stderr:
            print("Error:", e.stderr.strip())
        return False
    except Exception as e:
        print(f"❌ Failed to run command: {e}")
        return False

async def run_discord_extraction(channel_url, limit=None, months=None, dry_run=False, test_mode=False):
    """Run Discord browser-based message extraction"""
    cmd = [
        sys.executable, "discord_browser_extractor.py",
        "--url", channel_url
    ]
    
    if test_mode:
        cmd.extend(["--test-limit", "50", "--dry-run"])
    elif dry_run:
        cmd.append("--dry-run")
    
    if limit and not test_mode:
        cmd.extend(["--limit", str(limit)])
    
    if months and not test_mode:
        cmd.extend(["--months", str(months)])
    
    # Add verbose logging for non-test runs
    if not test_mode:
        cmd.append("--verbose")
    
    return run_command(cmd, f"Extracting messages from Discord channel via browser automation")

def run_discord_processing(server_id=None, channel_id=None, limit=500):
    """Run Discord message processing"""
    cmd = [
        sys.executable, "discord_processor.py",
        "--limit", str(limit)
    ]
    
    if server_id:
        cmd.extend(["--server-id", str(server_id)])
    
    if channel_id:
        cmd.extend(["--channel-id", str(channel_id)])
    
    return run_command(cmd, f"Processing Discord messages (limit: {limit})")

def run_discord_analysis(channel_url, analysis_type="comprehensive", limit=1000):
    """Run Discord Gemini analysis"""
    cmd = [
        sys.executable, "scripts/gemini_analyzer.py",
        "--platform", "discord",
        "--channel-url", channel_url,
        "--analysis-type", analysis_type,
        "--limit", str(limit)
    ]
    
    return run_command(cmd, f"Running Gemini analysis ({analysis_type})")

def get_pipeline_status(server_id=None, channel_id=None):
    """Get status of messages and processing for the channel"""
    import sqlite3
    
    db_path = os.getenv("SQLITE_DB_PATH", "./data/backfill.sqlite")
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Check if Discord tables exist
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'discord_%'")
        tables = [row[0] for row in cur.fetchall()]
        
        if 'discord_messages' not in tables:
            return {
                'messages_total': 0,
                'messages_processed': 0,
                'entities_total': 0,
                'last_message': None,
                'error': 'Discord tables not found - run extraction first'
            }
        
        # Build query filters
        where_clause = "WHERE 1=1"
        params = []
        
        if server_id:
            where_clause += " AND server_id = ?"
            params.append(str(server_id))
        
        if channel_id:
            where_clause += " AND channel_id = ?"
            params.append(str(channel_id))
        
        # Get message counts
        cur.execute(f"SELECT COUNT(*) FROM discord_messages {where_clause}", params)
        total_messages = cur.fetchone()[0]
        
        cur.execute(f"SELECT COUNT(*) FROM discord_messages {where_clause} AND processed = 1", params)
        processed_messages = cur.fetchone()[0]
        
        # Get entity count
        if 'discord_entities' in tables:
            join_clause = "FROM discord_entities de JOIN discord_messages dm ON de.message_id = dm.message_id"
            cur.execute(f"SELECT COUNT(*) {join_clause} {where_clause.replace('WHERE 1=1', 'WHERE 1=1')}", params)
            total_entities = cur.fetchone()[0]
        else:
            total_entities = 0
        
        # Get last message date
        cur.execute(f"SELECT MAX(timestamp) FROM discord_messages {where_clause}", params)
        last_message = cur.fetchone()[0]
        
        conn.close()
        
        return {
            'messages_total': total_messages,
            'messages_processed': processed_messages,
            'entities_total': total_entities,
            'last_message': last_message
        }
        
    except Exception as e:
        return {'error': str(e)}

async def main():
    parser = argparse.ArgumentParser(description="Discord Channel Analysis Pipeline")
    
    # Input options
    parser.add_argument("--url", help="Discord channel URL")
    parser.add_argument("--browser-extract", action="store_true", help="Use browser extraction")
    
    # Browser extraction options
    parser.add_argument("--months", type=int, help="Extract messages from last N months")
    parser.add_argument("--limit", type=int, help="Maximum number of messages to extract")
    parser.add_argument("--dry-run", action="store_true", help="Run extraction without saving to database")
    parser.add_argument("--test-mode", action="store_true", help="Run in test mode (50 messages)")
    
    # Pipeline control
    parser.add_argument("--skip-extraction", action="store_true", help="Skip message extraction")
    parser.add_argument("--skip-processing", action="store_true", help="Skip entity processing")
    parser.add_argument("--skip-analysis", action="store_true", help="Skip Gemini analysis")
    parser.add_argument("--analysis-only", action="store_true", help="Only run analysis (skip extraction and processing)")
    parser.add_argument("--status-only", action="store_true", help="Only show pipeline status")
    parser.add_argument("--full-pipeline", action="store_true", help="Run complete extraction → processing → analysis")
    
    # Options
    parser.add_argument("--processing-limit", type=int, default=500, help="Messages to process per batch")
    parser.add_argument("--analysis-type", default="comprehensive", 
                       choices=["comprehensive", "summary", "entities"],
                       help="Type of Gemini analysis")
    parser.add_argument("--analysis-limit", type=int, default=1000, help="Messages to analyze")
    
    args = parser.parse_args()
    
    # Validate input
    if not args.url:
        print("❌ Must provide --url with Discord channel URL")
        return 1
    
    # Parse Discord URL
    try:
        server_id, channel_id = parse_discord_url(args.url)
    except ValueError as e:
        print(f"❌ {e}")
        return 1
    
    print(f"🤖 Discord Channel Analysis Pipeline")
    print(f"📊 Server ID: {server_id}")
    print(f"📋 Channel ID: {channel_id}")
    print(f"🔗 Channel URL: {args.url}")
    print(f"📅 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Show status if requested
    if args.status_only:
        print(f"\n📈 Pipeline Status:")
        status = get_pipeline_status(server_id, channel_id)
        
        if status.get('error'):
            print(f"❌ Error: {status['error']}")
        else:
            print(f"  📨 Total Messages: {status['messages_total']}")
            print(f"  ✅ Processed Messages: {status['messages_processed']}")
            print(f"  🏷️  Total Entities: {status['entities_total']}")
            print(f"  🕐 Last Message: {status['last_message']}")
            
            if status['messages_total'] > 0:
                progress = (status['messages_processed'] / status['messages_total']) * 100
                print(f"  📊 Processing Progress: {progress:.1f}%")
        
        return 0
    
    # Check requirements
    if not check_requirements():
        return 1
    
    success = True
    
    try:
        # Step 1: Extraction
        if not args.skip_extraction and not args.analysis_only:
            print(f"\n" + "="*60)
            print(f"🔍 STEP 1: BROWSER-BASED MESSAGE EXTRACTION")
            print(f"="*60)
            
            result = await run_discord_extraction(
                args.url,
                limit=args.limit,
                months=args.months,
                dry_run=args.dry_run,
                test_mode=args.test_mode
            )
            
            if not result:
                print("❌ Extraction failed")
                success = False
            else:
                print("✅ Extraction completed successfully")
        
        # Step 2: Processing
        if success and not args.skip_processing and not args.analysis_only and not args.dry_run:
            print(f"\n" + "="*60)
            print(f"⚙️ STEP 2: MESSAGE PROCESSING")
            print(f"="*60)
            
            result = run_discord_processing(server_id, channel_id, args.processing_limit)
            
            if not result:
                print("❌ Processing failed")
                success = False
            else:
                print("✅ Processing completed successfully")
        
        # Step 3: Analysis
        if success and not args.skip_analysis and not args.dry_run:
            print(f"\n" + "="*60)
            print(f"🧠 STEP 3: GEMINI ANALYSIS")
            print(f"="*60)
            
            # Check if Gemini API key is available
            if not os.getenv("GEMINI_API_KEY"):
                print("⚠️ GEMINI_API_KEY not set, skipping analysis")
            else:
                result = run_discord_analysis(
                    args.url,
                    args.analysis_type, 
                    args.analysis_limit
                )
                
                if not result:
                    print("❌ Analysis failed")
                    success = False
                else:
                    print("✅ Analysis completed successfully")
        
        # Final status
        print(f"\n" + "="*60)
        print(f"📊 PIPELINE SUMMARY")
        print(f"="*60)
        
        status = get_pipeline_status(server_id, channel_id)
        
        if status.get('error'):
            print(f"❌ Error getting status: {status['error']}")
        else:
            print(f"📨 Total Messages: {status['messages_total']}")
            print(f"✅ Processed Messages: {status['messages_processed']}")
            print(f"🏷️ Total Entities: {status['entities_total']}")
            print(f"🕐 Last Message: {status['last_message']}")
        
        if args.dry_run:
            print(f"\n📝 Dry run completed - no data was saved to database")
        elif success:
            print(f"\n🎉 Pipeline completed successfully!")
            print(f"📁 Check ./data/gemini_analysis/ for analysis reports")
            print(f"📁 Check ./logs/discord/ for detailed logs")
        else:
            print(f"\n⚠️ Pipeline completed with errors")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n⚠️ Pipeline interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))