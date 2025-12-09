#!/usr/bin/env python3
"""
Daily Gemini sync pipeline for automated Telegram channel analysis.
Extracts new messages since last export and generates incremental analysis.

Usage:
  python scripts/daily_gemini_sync.py --channel @Galactic_Mining_Club
  python scripts/daily_gemini_sync.py --channel @Galactic_Mining_Club --force-reprocess

Environment variables (in `.env`):
  GEMINI_API_KEY      # Google AI Studio API key
  SQLITE_DB_PATH      # Path to SQLite database
  
Features:
  - Incremental message processing since last export
  - Rate-limited API usage respecting free tier limits
  - Comprehensive logging and error handling
  - Structured analysis with citations
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv

# Fix import path for GeminiAnalyzer
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, script_dir)
sys.path.insert(0, project_root)

try:
    from gemini_analyzer import GeminiAnalyzer
except ImportError:
    from scripts.gemini_analyzer import GeminiAnalyzer

load_dotenv()

# Configuration
DB_PATH = os.getenv("SQLITE_DB_PATH", "./data/backfill.sqlite")
ANALYSIS_OUTPUT_DIR = "./data/gemini_analysis/"
RAW_MESSAGES_DIR = "./data/"


class DailyGeminiSync:
    def __init__(self, gemini_api_key: str):
        """Initialize daily sync with database and Gemini analyzer."""
        self.db_path = DB_PATH
        self.analyzer = GeminiAnalyzer(gemini_api_key)
        self.analysis_dir = Path(ANALYSIS_OUTPUT_DIR)
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
    
    def get_channel_info(self, channel_identifier: str) -> Optional[Dict[str, Any]]:
        """Get channel information from database."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Try both tg_id and username
        cur.execute("""
            SELECT tg_id, title, username, last_backfilled_at, last_gemini_export 
            FROM channels 
            WHERE tg_id = ? OR username = ?
        """, (channel_identifier, channel_identifier.lstrip('@')))
        
        row = cur.fetchone()
        conn.close()
        
        if row:
            return {
                "tg_id": row[0],
                "title": row[1], 
                "username": row[2],
                "last_backfilled_at": row[3],
                "last_gemini_export": row[4]
            }
        return None
    
    def get_new_messages_since(self, channel_id: str, since_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extract new messages since last Gemini export."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        query = """
            SELECT id, message_id, sender_username, sender_name, date, text 
            FROM messages 
            WHERE channel_id = ? AND text IS NOT NULL
        """
        params = [channel_id]
        
        if since_date:
            query += " AND date > ?"
            params.append(since_date)
        
        # Order by date for chronological processing
        query += " ORDER BY date ASC"
        
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()
        
        messages = []
        for row in rows:
            messages.append({
                "id": row[0],
                "message_id": row[1],
                "sender_username": row[2] or "Unknown",
                "sender_name": row[3],
                "date": row[4],
                "text": row[5]
            })
        
        return messages
    
    def format_messages_for_analysis(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages in the expected timestamp format for Gemini analysis."""
        formatted_lines = []
        
        for msg in messages:
            # Use sender_username if available, otherwise sender_name, otherwise Unknown
            sender = msg["sender_username"]
            if not sender or sender == "Unknown":
                sender = msg["sender_name"] or "Unknown"
            
            # Ensure sender has @ prefix
            if sender != "Unknown" and not sender.startswith('@'):
                sender = f"@{sender}"
            
            # Format: [YYYY-MM-DD HH:MM:SS UTC] @username: message_text
            formatted_line = f"[{msg['date']}] {sender}: {msg['text']}"
            formatted_lines.append(formatted_line)
        
        return "\n\n".join(formatted_lines)
    
    def update_gemini_export_timestamp(self, channel_id: str, export_timestamp: str):
        """Update last_gemini_export timestamp for channel."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE channels 
            SET last_gemini_export = ? 
            WHERE tg_id = ?
        """, (export_timestamp, channel_id))
        
        conn.commit()
        conn.close()
    
    def mark_messages_as_gemini_processed(self, message_ids: List[int]):
        """Mark messages as processed by Gemini analysis."""
        if not message_ids:
            return
            
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        placeholders = ','.join('?' * len(message_ids))
        cur.execute(f"""
            UPDATE messages 
            SET gemini_processed = 1 
            WHERE id IN ({placeholders})
        """, message_ids)
        
        conn.commit()
        conn.close()
    
    def log_analysis_session(self, channel_id: str, analysis_result: Dict[str, Any], 
                           messages_count: int, analysis_file: str, metadata_file: str):
        """Log analysis session to database."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO gemini_analysis_logs (
                channel_id, analysis_date, messages_processed, api_requests_used,
                chunks_processed, analysis_file_path, metadata_file_path,
                citations_count, analysis_type, success, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            channel_id,
            datetime.now().date().isoformat(),
            messages_count,
            analysis_result.get('chunks_processed', 1),  # API requests ≈ chunks
            analysis_result.get('chunks_processed', 1),
            analysis_file,
            metadata_file,
            len(analysis_result.get('citations', [])),
            'comprehensive',
            1 if not analysis_result.get('fallback') else 0,
            None
        ))
        
        conn.commit()
        conn.close()
    
    def sync_channel(self, channel_identifier: str, force_reprocess: bool = False) -> bool:
        """
        Perform daily sync for a specific channel.
        
        Args:
            channel_identifier: Channel username or tg_id
            force_reprocess: If True, reprocess all messages ignoring last export date
            
        Returns:
            True if sync was successful, False otherwise
        """
        print(f"Starting daily Gemini sync for: {channel_identifier}")
        
        # Get channel info
        channel_info = self.get_channel_info(channel_identifier)
        if not channel_info:
            print(f"Channel not found in database: {channel_identifier}")
            print("Make sure to run backfill first: python backfill.py --channel {channel_identifier}")
            return False
        
        channel_id = channel_info["tg_id"]
        channel_name = channel_info["username"] or channel_id
        
        print(f"Processing channel: {channel_name} (ID: {channel_id})")
        
        # Determine since date
        since_date = None
        if not force_reprocess and channel_info["last_gemini_export"]:
            since_date = channel_info["last_gemini_export"]
            print(f"Incremental processing since: {since_date}")
        else:
            print("Full processing (no previous export or force reprocess)")
        
        # Extract new messages
        messages = self.get_new_messages_since(channel_id, since_date)
        
        if not messages:
            print("No new messages to process")
            return True
        
        print(f"Found {len(messages)} messages to analyze")
        
        # Format messages for analysis
        formatted_messages = self.format_messages_for_analysis(messages)
        
        if not formatted_messages.strip():
            print("No valid message content found")
            return True
        
        print(f"Formatted {len(formatted_messages)} characters for analysis")
        
        try:
            # Perform Gemini analysis
            analysis_result = self.analyzer.analyze_messages(formatted_messages, "comprehensive")
            
            # Save analysis results
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            analysis_file = self.analysis_dir / f"{channel_name}_daily_analysis_{timestamp}.md"
            metadata_file = self.analysis_dir / f"{channel_name}_daily_metadata_{timestamp}.json"
            
            # Save using gemini_analyzer's save function
            try:
                from gemini_analyzer import save_analysis_result
            except ImportError:
                from scripts.gemini_analyzer import save_analysis_result
            save_analysis_result(analysis_result, str(self.analysis_dir), f"{channel_name}_daily")
            
            # Update database records
            current_timestamp = datetime.now().isoformat()
            self.update_gemini_export_timestamp(channel_id, current_timestamp)
            
            # Mark messages as processed
            message_ids = [msg["id"] for msg in messages]
            self.mark_messages_as_gemini_processed(message_ids)
            
            # Log session
            self.log_analysis_session(
                channel_id, analysis_result, len(messages), 
                str(analysis_file), str(metadata_file)
            )
            
            print(f"✅ Daily sync completed successfully!")
            print(f"   Processed: {len(messages)} messages")
            print(f"   Citations: {len(analysis_result.get('citations', []))}")
            print(f"   API requests: {analysis_result.get('chunks_processed', 1)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            
            # Log failed session
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO gemini_analysis_logs (
                    channel_id, analysis_date, messages_processed, 
                    success, error_message
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                channel_id, datetime.now().date().isoformat(), 
                len(messages), 0, str(e)
            ))
            conn.commit()
            conn.close()
            
            return False
    
    def get_daily_usage_stats(self) -> Dict[str, Any]:
        """Get today's API usage statistics."""
        today = datetime.now().date().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                COUNT(*) as sessions,
                SUM(messages_processed) as total_messages,
                SUM(api_requests_used) as total_api_requests,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_sessions
            FROM gemini_analysis_logs 
            WHERE analysis_date = ?
        """, (today,))
        
        row = cur.fetchone()
        conn.close()
        
        return {
            "date": today,
            "sessions": row[0] or 0,
            "total_messages": row[1] or 0,
            "total_api_requests": row[2] or 0,
            "successful_sessions": row[3] or 0,
            "api_requests_remaining": max(0, 50 - (row[2] or 0))
        }


def main():
    parser = argparse.ArgumentParser(description="Daily Gemini sync for Telegram channels")
    parser.add_argument("--channel", help="Channel username or ID (e.g., @Galactic_Mining_Club)")
    parser.add_argument("--force-reprocess", action="store_true", 
                       help="Reprocess all messages ignoring last export date")
    parser.add_argument("--stats", action="store_true", 
                       help="Show today's API usage statistics")
    parser.add_argument("--off-peak-analytics", action="store_true",
                       help="Run off-peak activity analytics after Gemini sync")
    
    args = parser.parse_args()
    
    # Handle off-peak analytics mode
    if args.off_peak_analytics:
        return run_off_peak_analytics()
    
    # Require channel for normal Gemini sync
    if not args.channel:
        print("❌ --channel is required for Gemini sync mode")
        parser.print_help()
        return 1
    
    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY must be set in environment or .env file")
        return 1
    
    # Initialize sync
    sync = DailyGeminiSync(api_key)
    
    # Show stats if requested
    if args.stats:
        stats = sync.get_daily_usage_stats()
        print(f"📊 Daily Usage Stats ({stats['date']}):")
        print(f"   Sessions: {stats['sessions']}")
        print(f"   Messages processed: {stats['total_messages']}")
        print(f"   API requests used: {stats['total_api_requests']}/50")
        print(f"   Successful sessions: {stats['successful_sessions']}")
        print(f"   API requests remaining: {stats['api_requests_remaining']}")
        return 0
    
    # Check daily API limit
    stats = sync.get_daily_usage_stats()
    if stats['api_requests_remaining'] <= 0:
        print(f"❌ Daily API limit reached ({stats['total_api_requests']}/50)")
        print("Try again tomorrow or upgrade to paid tier")
        return 1
    
    print(f"📊 API requests available today: {stats['api_requests_remaining']}/50")
    
    # Perform sync
    success = sync.sync_channel(args.channel, args.force_reprocess)
    
    return 0 if success else 1


def run_off_peak_analytics() -> int:
    """
    Run off-peak activity analytics after Gemini sync completion.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("🌙 Starting off-peak activity analytics...")
    
    try:
        # Import and run dashboard generation
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from channel_dashboard import generate_daily_activity_report
        
        # Generate activity report
        report_path = generate_daily_activity_report()
        
        print(f"✅ Off-peak analytics completed successfully!")
        print(f"📁 Activity report: {report_path}")
        
        return 0
        
    except SystemExit as e:
        # Handle validation failures from activity_utils
        print(f"❌ Off-peak analytics failed: Configuration validation error")
        return e.code if e.code else 1
        
    except Exception as e:
        print(f"❌ Off-peak analytics failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())