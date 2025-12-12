#!/usr/bin/env python3
"""
Real-time Discord Extraction Monitor
Provides live monitoring of extraction progress
"""

import sqlite3
import time
import sys
from datetime import datetime

class ExtractionMonitor:
    def __init__(self, db_path="data/backfill.sqlite"):
        self.db_path = db_path
        self.last_count = 0
        self.start_time = datetime.now()
        
    def get_current_stats(self):
        """Get current database statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Basic stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT username) as users,
                    MIN(DATE(timestamp)) as earliest,
                    MAX(DATE(timestamp)) as latest,
                    COUNT(*) FILTER (WHERE datetime(timestamp) >= datetime('now', '-1 hour')) as recent_hour,
                    COUNT(*) FILTER (WHERE datetime(timestamp) >= datetime('now', '-10 minutes')) as recent_10min
                FROM discord_messages
            """)
            
            stats = cursor.fetchone()
            conn.close()
            
            return {
                'total': stats[0],
                'users': stats[1], 
                'earliest': stats[2],
                'latest': stats[3],
                'recent_hour': stats[4],
                'recent_10min': stats[5]
            }
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            return None
    
    def monitor_extraction(self, refresh_seconds=10):
        """Monitor extraction progress in real-time"""
        print("🔍 REAL-TIME EXTRACTION MONITOR")
        print("=" * 60)
        print("Press Ctrl+C to stop monitoring\n")
        
        try:
            while True:
                stats = self.get_current_stats()
                
                if stats:
                    current_time = datetime.now()
                    runtime = current_time - self.start_time
                    
                    # Calculate rate
                    new_messages = stats['total'] - self.last_count
                    rate_per_min = (new_messages / refresh_seconds) * 60 if refresh_seconds > 0 else 0
                    
                    # Display status
                    print(f"\r🕐 {current_time.strftime('%H:%M:%S')} | "
                          f"📊 {stats['total']:4d} total | "
                          f"👥 {stats['users']:2d} users | "
                          f"📈 +{new_messages:2d} (+{rate_per_min:.1f}/min) | "
                          f"⏱️  {str(runtime).split('.')[0]} runtime", end="")
                    
                    # Update for next iteration
                    self.last_count = stats['total']
                    
                    # Detailed update every 5th refresh
                    if int(runtime.total_seconds()) % (refresh_seconds * 5) < refresh_seconds:
                        print(f"\n   📅 Date range: {stats['earliest']} → {stats['latest']}")
                        print(f"   🕐 Recent activity: {stats['recent_10min']} messages (10min), {stats['recent_hour']} messages (1hr)")
                        
                else:
                    print(f"\r❌ Database unavailable", end="")
                
                time.sleep(refresh_seconds)
                
        except KeyboardInterrupt:
            print(f"\n\n🏁 Monitoring stopped")
            
            # Final stats
            final_stats = self.get_current_stats()
            if final_stats:
                print(f"📊 Final Status:")
                print(f"   Total Messages: {final_stats['total']}")
                print(f"   Unique Users: {final_stats['users']}")
                print(f"   Date Coverage: {final_stats['earliest']} to {final_stats['latest']}")
    
    def quick_status(self):
        """Get a quick status snapshot"""
        stats = self.get_current_stats()
        
        if stats:
            print(f"📊 EXTRACTION STATUS SNAPSHOT")
            print(f"   Total Messages: {stats['total']:,}")
            print(f"   Unique Users: {stats['users']}")
            print(f"   Date Range: {stats['earliest']} → {stats['latest']}")
            print(f"   Recent Activity: {stats['recent_10min']} (10min), {stats['recent_hour']} (1hr)")
        else:
            print("❌ Unable to get status")

def main():
    """Main monitoring function"""
    monitor = ExtractionMonitor()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "quick":
            monitor.quick_status()
        elif sys.argv[1] == "watch":
            refresh_rate = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            monitor.monitor_extraction(refresh_rate)
    else:
        monitor.monitor_extraction()

if __name__ == "__main__":
    main()