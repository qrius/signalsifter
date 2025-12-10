#!/usr/bin/env python3
"""
Discord Extraction Monitor
Real-time monitoring for Discord extraction progress during week-long validation test
"""

import sqlite3
import time
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import signal

class ExtractionMonitor:
    def __init__(self, db_path="data/backfill.sqlite", interval=30):
        self.db_path = db_path
        self.interval = interval
        self.running = True
        self.start_time = datetime.now()
        self.baseline_count = 0
        self.monitoring_log = []
        
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\n🛑 Received signal {signum}, shutting down monitor...")
        self.running = False
    
    def connect_db(self):
        """Connect to SQLite database"""
        try:
            return sqlite3.connect(self.db_path, timeout=10)
        except sqlite3.Error as e:
            print(f"⚠️  Database connection failed: {e}")
            return None
    
    def get_extraction_stats(self):
        """Get current extraction statistics"""
        conn = self.connect_db()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            
            # Basic counts
            cursor.execute("SELECT COUNT(*) FROM discord_messages")
            total_messages = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM discord_messages 
                WHERE content IS NOT NULL AND content != ''
            """)
            messages_with_content = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(DISTINCT username) FROM discord_messages 
                WHERE username != 'Unknown' AND username IS NOT NULL
            """)
            unique_users = cursor.fetchone()[0]
            
            # Recent activity (last 5 minutes)
            five_min_ago = datetime.now() - timedelta(minutes=5)
            cursor.execute("""
                SELECT COUNT(*) FROM discord_messages 
                WHERE created_at > ?
            """, (five_min_ago.isoformat(),))
            recent_messages = cursor.fetchone()[0]
            
            # Date range
            cursor.execute("""
                SELECT 
                    MIN(DATE(timestamp)) as earliest,
                    MAX(DATE(timestamp)) as latest,
                    COUNT(DISTINCT DATE(timestamp)) as days
                FROM discord_messages
            """)
            date_info = cursor.fetchone()
            
            # Latest message info
            cursor.execute("""
                SELECT username, SUBSTR(content, 1, 50), timestamp
                FROM discord_messages
                WHERE content != '' AND content IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            latest_message = cursor.fetchone()
            
            conn.close()
            
            stats = {
                "timestamp": datetime.now().isoformat(),
                "total_messages": total_messages,
                "messages_with_content": messages_with_content,
                "unique_users": unique_users,
                "recent_messages": recent_messages,
                "earliest_date": date_info[0],
                "latest_date": date_info[1],
                "days_covered": date_info[2],
                "latest_message": {
                    "username": latest_message[0] if latest_message else None,
                    "content_preview": latest_message[1] if latest_message else None,
                    "timestamp": latest_message[2] if latest_message else None
                } if latest_message else None,
                "content_rate": (messages_with_content / total_messages * 100) if total_messages > 0 else 0
            }
            
            return stats
            
        except sqlite3.Error as e:
            print(f"⚠️  Database query failed: {e}")
            conn.close()
            return None
    
    def display_stats(self, stats, previous_stats=None):
        """Display current statistics with changes"""
        if not stats:
            print("❌ Unable to retrieve stats")
            return
        
        # Calculate changes
        if previous_stats:
            msg_change = stats["total_messages"] - previous_stats["total_messages"]
            content_change = stats["messages_with_content"] - previous_stats["messages_with_content"]
            user_change = stats["unique_users"] - previous_stats["unique_users"]
            
            change_indicator = f"(+{msg_change} msgs, +{content_change} content, +{user_change} users)"
        else:
            change_indicator = "(baseline)"
        
        # Runtime
        runtime = datetime.now() - self.start_time
        runtime_str = str(runtime).split('.')[0]  # Remove microseconds
        
        # Clear screen and display
        print("\033[2J\033[H", end="")  # Clear screen and move to top
        print("=" * 80)
        print(f"📊 DISCORD EXTRACTION MONITOR - Runtime: {runtime_str}")
        print("=" * 80)
        print(f"🕒 Last Update: {stats['timestamp']}")
        print(f"📍 Database: {self.db_path}")
        print()
        print(f"📈 PROGRESS {change_indicator}")
        print(f"   Total Messages:     {stats['total_messages']:,}")
        print(f"   With Content:       {stats['messages_with_content']:,} ({stats['content_rate']:.1f}%)")
        print(f"   Unique Users:       {stats['unique_users']}")
        print(f"   Recent Activity:    {stats['recent_messages']} messages (last 5 min)")
        print()
        print(f"📅 DATE COVERAGE")
        print(f"   Date Range:         {stats['earliest_date']} to {stats['latest_date']}")
        print(f"   Days Covered:       {stats['days_covered']}")
        print()
        
        if stats['latest_message'] and stats['latest_message']['username']:
            print(f"💬 LATEST MESSAGE")
            print(f"   User:               {stats['latest_message']['username']}")
            print(f"   Content:            {stats['latest_message']['content_preview']}...")
            print(f"   Time:               {stats['latest_message']['timestamp']}")
            print()
        
        # Extraction rate
        if previous_stats and len(self.monitoring_log) > 1:
            total_runtime_hours = runtime.total_seconds() / 3600
            if total_runtime_hours > 0:
                rate_per_hour = stats['total_messages'] / total_runtime_hours
                print(f"⚡ EXTRACTION RATE")
                print(f"   Messages/Hour:      {rate_per_hour:.1f}")
                print()
        
        # Status indicators
        print(f"🚦 STATUS INDICATORS")
        status_indicators = []
        
        if stats['total_messages'] > 0:
            status_indicators.append("✅ Extraction Active")
        else:
            status_indicators.append("⚠️  No Messages Yet")
        
        if stats['content_rate'] >= 80:
            status_indicators.append("✅ Good Content Rate")
        elif stats['content_rate'] >= 50:
            status_indicators.append("⚠️  Moderate Content Rate")
        else:
            status_indicators.append("❌ Low Content Rate")
        
        if stats['unique_users'] >= 5:
            status_indicators.append("✅ Multiple Users")
        elif stats['unique_users'] >= 2:
            status_indicators.append("⚠️  Few Users")
        else:
            status_indicators.append("❌ Very Few Users")
        
        if stats['recent_messages'] > 0:
            status_indicators.append("✅ Recent Progress")
        else:
            status_indicators.append("⚠️  No Recent Activity")
        
        for indicator in status_indicators:
            print(f"   {indicator}")
        
        print()
        print(f"🔄 Next update in {self.interval} seconds... (Ctrl+C to stop)")
        print("=" * 80)
    
    def save_monitoring_log(self, filename=None):
        """Save monitoring log to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"extraction_monitor_log_{timestamp}.json"
        
        log_data = {
            "monitoring_session": {
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "interval_seconds": self.interval,
                "database_path": self.db_path
            },
            "measurements": self.monitoring_log
        }
        
        with open(filename, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"\n📄 Monitoring log saved to: {filename}")
        return filename
    
    def check_database_exists(self):
        """Check if database file exists"""
        db_file = Path(self.db_path)
        if not db_file.exists():
            print(f"❌ Database file not found: {self.db_path}")
            print("   Make sure extraction is running or has been started.")
            return False
        return True
    
    def run_monitor(self):
        """Main monitoring loop"""
        if not self.check_database_exists():
            return False
        
        print(f"🚀 Starting Discord extraction monitor...")
        print(f"📍 Database: {self.db_path}")
        print(f"⏱️  Update interval: {self.interval} seconds")
        print(f"🕒 Start time: {self.start_time}")
        print()
        
        previous_stats = None
        
        try:
            while self.running:
                stats = self.get_extraction_stats()
                
                if stats:
                    self.monitoring_log.append(stats)
                    self.display_stats(stats, previous_stats)
                    previous_stats = stats
                else:
                    print("⚠️  Failed to get stats, retrying...")
                
                # Sleep with interruption check
                for _ in range(self.interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            print(f"\n🛑 Monitor stopped by user")
        except Exception as e:
            print(f"\n❌ Monitor error: {e}")
        finally:
            if self.monitoring_log:
                log_file = self.save_monitoring_log()
                
                # Print final summary
                if len(self.monitoring_log) >= 2:
                    first_stats = self.monitoring_log[0]
                    final_stats = self.monitoring_log[-1]
                    total_extracted = final_stats['total_messages'] - first_stats['total_messages']
                    
                    print(f"\n📊 FINAL SUMMARY")
                    print(f"   Messages extracted: {total_extracted}")
                    print(f"   Final count: {final_stats['total_messages']}")
                    print(f"   Content rate: {final_stats['content_rate']:.1f}%")
                    print(f"   Unique users: {final_stats['unique_users']}")
        
        return True

def main():
    parser = argparse.ArgumentParser(description="Monitor Discord extraction progress")
    parser.add_argument("--db", default="data/backfill.sqlite", help="Database path")
    parser.add_argument("--interval", type=int, default=30, help="Update interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    
    args = parser.parse_args()
    
    monitor = ExtractionMonitor(args.db, args.interval)
    
    if args.once:
        stats = monitor.get_extraction_stats()
        if stats:
            monitor.display_stats(stats)
            return 0
        else:
            print("❌ Failed to get extraction stats")
            return 1
    else:
        success = monitor.run_monitor()
        return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())