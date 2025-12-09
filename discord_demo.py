#!/usr/bin/env python3
"""
Discord Demo Script - SignalSifter
Demonstrates the Discord extraction and analysis capabilities with example usage.

This script shows how to:
1. Extract messages from a Discord channel
2. Process messages for entity extraction
3. Generate AI-powered analysis reports
4. Handle various Discord-specific features

Usage:
  python discord_demo.py --help
  python discord_demo.py --url "https://discord.com/channels/123456/789012"
  python discord_demo.py --demo-mode
"""

import os
import sys
import argparse
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# Import our Discord modules
try:
    from discord_extractor import DiscordExtractor, parse_discord_url, ensure_discord_schema
    from discord_processor import process_discord_batch, get_processing_stats
    from scripts.discord_gemini_analyzer import DiscordGeminiAnalyzer, export_discord_messages_to_file
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all Discord modules are present and dependencies are installed.")
    sys.exit(1)

load_dotenv()

def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"🤖 {title}")
    print(f"{'='*60}")

def print_step(step_num, title):
    """Print a formatted step"""
    print(f"\n📋 STEP {step_num}: {title}")
    print("-" * 40)

def check_requirements():
    """Check if all requirements are met"""
    print_header("DISCORD MODULE REQUIREMENTS CHECK")
    
    missing = []
    
    # Check Discord bot token
    if not os.getenv("DISCORD_BOT_TOKEN"):
        missing.append("DISCORD_BOT_TOKEN")
    else:
        print("✅ Discord bot token found")
    
    # Check Gemini API key (optional)
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  Gemini API key not found (AI analysis will be skipped)")
    else:
        print("✅ Gemini API key found")
    
    # Check dependencies
    try:
        import discord
        print(f"✅ discord.py version: {discord.__version__}")
    except ImportError:
        missing.append("discord.py")
    
    try:
        import google.generativeai as genai
        print("✅ google-generativeai library found")
    except ImportError:
        print("⚠️  google-generativeai library not found (AI analysis will be skipped)")
    
    if missing:
        print(f"\n❌ Missing requirements: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("\n🎉 All requirements satisfied!")
    return True

async def demo_extraction(guild_id, channel_id):
    """Demonstrate Discord message extraction"""
    print_step(1, "MESSAGE EXTRACTION")
    
    print(f"📊 Target: Guild {guild_id}, Channel {channel_id}")
    
    # Initialize extractor
    extractor = DiscordExtractor()
    
    try:
        print("🔌 Connecting to Discord...")
        await extractor.setup()
        
        print("📥 Extracting messages...")
        await extractor.extract_messages(
            guild_id=guild_id,
            channel_id=channel_id,
            from_date=datetime.now() - timedelta(days=30),  # Last 30 days
            no_media=True  # Skip media for demo
        )
        
        print("✅ Extraction completed successfully!")
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        raise
    finally:
        await extractor.cleanup()

def demo_processing(guild_id, channel_id):
    """Demonstrate Discord message processing"""
    print_step(2, "MESSAGE PROCESSING & ENTITY EXTRACTION")
    
    print("🔍 Processing messages for entity extraction...")
    
    # Get stats before processing
    print("\n📊 Before processing:")
    get_processing_stats(str(guild_id), str(channel_id))
    
    # Run processing
    process_discord_batch(
        limit=100,  # Process up to 100 messages for demo
        guild_id=str(guild_id),
        channel_id=str(channel_id)
    )
    
    # Get stats after processing
    print("\n📊 After processing:")
    get_processing_stats(str(guild_id), str(channel_id))
    
    print("✅ Processing completed successfully!")

def demo_analysis(guild_id, channel_id):
    """Demonstrate Discord AI analysis"""
    print_step(3, "AI ANALYSIS WITH GEMINI")
    
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  Skipping AI analysis (GEMINI_API_KEY not configured)")
        return
    
    try:
        analyzer = DiscordGeminiAnalyzer(os.getenv("GEMINI_API_KEY"))
        
        print("🧠 Running comprehensive analysis...")
        results = analyzer.analyze_discord_channel(
            guild_id=str(guild_id),
            channel_id=str(channel_id),
            analysis_type="summary",  # Use summary for demo (faster)
            limit=50  # Analyze last 50 messages
        )
        
        # Save demo results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("./data/discord_analysis/demo")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = output_dir / f"discord_demo_analysis_{timestamp}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# Discord Demo Analysis Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Guild ID:** {guild_id}\n")
            f.write(f"**Channel ID:** {channel_id}\n")
            f.write("\n## Analysis Results\n\n")
            f.write(results.get('analysis', 'No analysis generated'))
        
        print(f"✅ Analysis completed!")
        print(f"📄 Report saved to: {report_file}")
        
        # Show excerpt
        analysis_text = results.get('analysis', '')
        if len(analysis_text) > 300:
            excerpt = analysis_text[:300] + "..."
        else:
            excerpt = analysis_text
            
        print(f"\n📝 Analysis Excerpt:")
        print("-" * 30)
        print(excerpt)
        print("-" * 30)
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        raise

def show_demo_results(guild_id, channel_id):
    """Show summary of demo results"""
    print_header("DEMO RESULTS SUMMARY")
    
    # Database stats
    print("📊 Database Statistics:")
    get_processing_stats(str(guild_id), str(channel_id))
    
    # File locations
    print("\n📁 Generated Files:")
    
    # Raw messages
    raw_dir = Path(f"./data/raw/{guild_id}/{channel_id}")
    if raw_dir.exists():
        raw_files = list(raw_dir.glob("*.json"))
        print(f"  📄 Raw messages: {len(raw_files)} files in {raw_dir}")
    
    # Analysis reports
    analysis_dir = Path("./data/discord_analysis")
    if analysis_dir.exists():
        analysis_files = list(analysis_dir.glob("**/*.md"))
        print(f"  🧠 Analysis reports: {len(analysis_files)} files in {analysis_dir}")
        
        # Show most recent
        if analysis_files:
            latest = max(analysis_files, key=lambda f: f.stat().st_mtime)
            print(f"  📄 Latest report: {latest}")
    
    print(f"\n🎉 Demo completed successfully!")
    print(f"📚 For full documentation, see: README_DISCORD.md")

async def run_demo(guild_id, channel_id):
    """Run the complete Discord demo"""
    print_header("SIGNALSIFTER DISCORD MODULE DEMO")
    print(f"🎯 Target Discord Channel")
    print(f"  Guild ID: {guild_id}")
    print(f"  Channel ID: {channel_id}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Ensure database schema
        ensure_discord_schema()
        
        # Step 1: Extract messages
        await demo_extraction(guild_id, channel_id)
        
        # Step 2: Process messages
        demo_processing(guild_id, channel_id)
        
        # Step 3: AI analysis
        demo_analysis(guild_id, channel_id)
        
        # Show results
        show_demo_results(guild_id, channel_id)
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure your Discord bot token is valid")
        print("2. Ensure the bot has access to the target channel")
        print("3. Check that Message Content Intent is enabled")
        print("4. Verify the guild/channel IDs are correct")
        return 1
    
    return 0

def interactive_setup():
    """Interactive setup for demo"""
    print_header("INTERACTIVE DISCORD DEMO SETUP")
    
    print("This demo will extract and analyze messages from a Discord channel.")
    print("You'll need:")
    print("1. A Discord bot token (configured in .env)")
    print("2. A Discord server where your bot is a member")
    print("3. A channel ID or Discord URL")
    print()
    
    # Get Discord URL or IDs
    while True:
        discord_input = input("Enter Discord URL or type 'manual' for guild/channel IDs: ").strip()
        
        if discord_input.lower() == 'manual':
            try:
                guild_id = int(input("Enter Guild (Server) ID: ").strip())
                channel_id = int(input("Enter Channel ID: ").strip())
                break
            except ValueError:
                print("❌ Please enter valid numeric IDs")
                continue
        else:
            try:
                guild_id, channel_id = parse_discord_url(discord_input)
                print(f"✅ Parsed URL: Guild {guild_id}, Channel {channel_id}")
                break
            except ValueError:
                print("❌ Invalid Discord URL format")
                print("Expected: https://discord.com/channels/GUILD_ID/CHANNEL_ID")
                continue
    
    return guild_id, channel_id

async def main():
    parser = argparse.ArgumentParser(description="Discord Module Demo for SignalSifter")
    
    # Input options
    parser.add_argument("--url", help="Discord channel URL")
    parser.add_argument("--guild-id", type=int, help="Discord Guild (Server) ID")
    parser.add_argument("--channel-id", type=int, help="Discord Channel ID")
    
    # Demo modes
    parser.add_argument("--demo-mode", action="store_true", 
                       help="Run interactive demo setup")
    parser.add_argument("--check-only", action="store_true", 
                       help="Only check requirements, don't run demo")
    
    args = parser.parse_args()
    
    # Check requirements first
    if not check_requirements():
        return 1
    
    if args.check_only:
        return 0
    
    # Get guild and channel IDs
    if args.demo_mode:
        guild_id, channel_id = interactive_setup()
    elif args.url:
        try:
            guild_id, channel_id = parse_discord_url(args.url)
        except ValueError as e:
            print(f"❌ {e}")
            return 1
    elif args.guild_id and args.channel_id:
        guild_id = args.guild_id
        channel_id = args.channel_id
    else:
        print("❌ Must provide --url, --guild-id/--channel-id, or use --demo-mode")
        return 1
    
    # Run the demo
    return await run_demo(guild_id, channel_id)

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(result)
    except KeyboardInterrupt:
        print("\n⚠️  Demo cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)