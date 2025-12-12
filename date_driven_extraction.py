#!/usr/bin/env python3
"""
True Date-Driven Weekly Discord Extraction
Systematically extracts Discord messages week by week using date ranges
"""

import asyncio
import subprocess
import sys
from datetime import datetime, timedelta, timezone
import sqlite3
import time
import json

class DateDrivenDiscordExtractor:
    def __init__(self, channel_url, start_date=None, end_date=None):
        self.channel_url = channel_url
        self.db_path = "data/backfill.sqlite"
        
        # Default to 2 months back from today
        self.end_date = end_date or datetime.now(timezone.utc)
        self.start_date = start_date or (self.end_date - timedelta(days=60))  # 2 months
        
        print(f"📅 Target extraction period: {self.start_date.date()} to {self.end_date.date()}")
    
    def get_coverage_gaps(self):
        """Analyze current database to find coverage gaps by week"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current coverage by week
            cursor.execute("""
                SELECT 
                    DATE(timestamp, 'weekday 0', '-6 days') as week_start,
                    DATE(timestamp, 'weekday 0') as week_end,
                    COUNT(*) as message_count,
                    MIN(DATE(timestamp)) as actual_start,
                    MAX(DATE(timestamp)) as actual_end
                FROM discord_messages 
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY DATE(timestamp, 'weekday 0', '-6 days')
                ORDER BY week_start DESC
            """, (self.start_date.isoformat(), self.end_date.isoformat()))
            
            existing_weeks = cursor.fetchall()
            conn.close()
            
            print(f"\n📊 CURRENT WEEKLY COVERAGE:")
            print("-" * 70)
            
            if existing_weeks:
                for week_start, week_end, count, actual_start, actual_end in existing_weeks:
                    print(f"Week {week_start} to {week_end}: {count:4d} messages ({actual_start} → {actual_end})")
            else:
                print("No existing coverage found")
            
            return existing_weeks
            
        except Exception as e:
            print(f"❌ Error analyzing coverage: {e}")
            return []
    
    def generate_weekly_targets(self):
        """Generate list of weekly date ranges to extract"""
        weekly_targets = []
        
        # Start from the beginning of the target period
        current_date = self.start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Align to Monday (start of week)
        days_since_monday = current_date.weekday()
        week_start = current_date - timedelta(days=days_since_monday)
        
        while week_start <= self.end_date:
            week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
            
            # Don't go beyond our end date
            if week_end > self.end_date:
                week_end = self.end_date
            
            weekly_targets.append({
                'week_start': week_start,
                'week_end': week_end,
                'description': f"Week {week_start.strftime('%m/%d')} - {week_end.strftime('%m/%d')}"
            })
            
            week_start += timedelta(days=7)
        
        return weekly_targets
    
    def check_week_coverage(self, week_start, week_end):
        """Check how many messages we have for a specific week"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM discord_messages 
                WHERE timestamp >= ? AND timestamp <= ?
            """, (week_start.isoformat(), week_end.isoformat()))
            
            count = cursor.fetchone()[0]
            conn.close()
            return count
            
        except Exception as e:
            print(f"❌ Error checking week coverage: {e}")
            return 0
    
    def extract_week_with_limits(self, week_target, max_attempts=3):
        """Extract messages for a specific week using progressive limits"""
        week_start = week_target['week_start']
        week_end = week_target['week_end']
        description = week_target['description']
        
        print(f"\n🎯 EXTRACTING: {description}")
        print(f"   Date range: {week_start.date()} to {week_end.date()}")
        
        # Check existing coverage
        existing_count = self.check_week_coverage(week_start, week_end)
        print(f"   Existing messages: {existing_count}")
        
        if existing_count > 50:  # Already good coverage
            print(f"   ✅ Week already has good coverage ({existing_count} messages)")
            return True
        
        # Progressive extraction limits for this week
        limits = [200, 500, 1000, 2000] if existing_count < 10 else [500, 1000, 2000]
        
        best_count = existing_count
        
        for attempt, limit in enumerate(limits, 1):
            print(f"\n   📥 Attempt {attempt}/{len(limits)}: Extracting up to {limit} messages")
            
            success = self.run_extraction_with_limit(limit, f"{description} - Attempt {attempt}")
            
            if success:
                new_count = self.check_week_coverage(week_start, week_end)
                added = new_count - best_count
                best_count = new_count
                
                print(f"   📈 Added {added} messages (total for week: {new_count})")
                
                # If we got good coverage, move on
                if new_count >= 100 or added < 5:
                    print(f"   ✅ Good coverage achieved for {description}")
                    break
            else:
                print(f"   ❌ Attempt {attempt} failed")
                
            # Wait between attempts
            if attempt < len(limits):
                print(f"   ⏳ Waiting 45 seconds before next attempt...")
                time.sleep(45)
        
        final_count = self.check_week_coverage(week_start, week_end)
        print(f"   🏁 Final week coverage: {final_count} messages")
        
        return final_count > existing_count
    
    def run_extraction_with_limit(self, limit, description=""):
        """Run extraction with a specific message limit"""
        try:
            # Clean up any existing browser locks first
            import subprocess as sp
            sp.run("pkill -f 'chromium|playwright' 2>/dev/null || true", shell=True, capture_output=True)
            sp.run("rm -rf ~/.SignalSifter/discord_browser_profile/SingletonLock 2>/dev/null || true", shell=True, capture_output=True)
            
            # Build extraction command
            cmd = [
                "python3", "discord_browser_extractor.py",
                "--url", self.channel_url,
                "--limit", str(limit),
                "--verbose",
                "--headless"  # Add headless mode to avoid conflicts
            ]
            
            # Run with virtual environment
            full_cmd = f"source signalsifter-env/bin/activate && {' '.join(cmd)}"
            
            print(f"      🔧 Running: --limit {limit}")
            
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )
            
            if result.returncode == 0:
                print(f"      ✅ Extraction completed")
                return True
            else:
                print(f"      ❌ Failed (code {result.returncode})")
                if result.stderr:
                    error_snippet = result.stderr[-150:].strip()
                    print(f"      Error: {error_snippet}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"      ⏰ Timed out after 30 minutes")
            return False
        except Exception as e:
            print(f"      ❌ Exception: {e}")
            return False
    
    def run_systematic_extraction(self):
        """Run systematic week-by-week extraction"""
        print("🚀 STARTING DATE-DRIVEN WEEKLY EXTRACTION")
        print("=" * 60)
        
        # Analyze current coverage
        existing_coverage = self.get_coverage_gaps()
        
        # Generate weekly targets
        weekly_targets = self.generate_weekly_targets()
        
        print(f"\n📋 EXTRACTION PLAN:")
        print(f"   Total weeks to process: {len(weekly_targets)}")
        print(f"   Period: {self.start_date.date()} to {self.end_date.date()}")
        
        successful_weeks = 0
        total_messages_added = 0
        
        # Process each week
        for i, week_target in enumerate(weekly_targets, 1):
            print(f"\n{'='*60}")
            print(f"📅 WEEK {i}/{len(weekly_targets)}: {week_target['description']}")
            print(f"{'='*60}")
            
            pre_count = self.get_total_message_count()
            
            if self.extract_week_with_limits(week_target):
                successful_weeks += 1
                
                post_count = self.get_total_message_count()
                week_added = post_count - pre_count
                total_messages_added += week_added
                
                print(f"✅ Week completed: +{week_added} messages")
            else:
                print(f"⚠️  Week had issues but may have partial data")
            
            # Progress update
            progress = (i / len(weekly_targets)) * 100
            print(f"\n📊 OVERALL PROGRESS: {progress:.1f}% complete")
            print(f"   Successful weeks: {successful_weeks}/{i}")
            print(f"   Total messages added: {total_messages_added}")
            
            # Brief pause between weeks (except last one)
            if i < len(weekly_targets):
                print(f"\n⏳ Waiting 30 seconds before next week...")
                time.sleep(30)
        
        # Final summary
        print(f"\n🏁 WEEKLY EXTRACTION COMPLETE!")
        print(f"   Weeks processed: {successful_weeks}/{len(weekly_targets)}")
        print(f"   Total messages added: {total_messages_added}")
        
        final_coverage = self.get_coverage_gaps()
        return successful_weeks, total_messages_added
    
    def get_total_message_count(self):
        """Get current total message count in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM discord_messages")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0

def main():
    """Main function"""
    channel_url = "https://discord.com/channels/1296015181985349715/1296015182417629249"
    
    # Target last 2 months
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=60)
    
    extractor = DateDrivenDiscordExtractor(channel_url, start_date, end_date)
    
    successful_weeks, total_added = extractor.run_systematic_extraction()
    
    print(f"\n🎉 DATE-DRIVEN EXTRACTION COMPLETE!")
    print(f"📊 Results: {successful_weeks} weeks processed, {total_added} messages added")
    
    if total_added > 1000:
        print(f"✅ Excellent coverage achieved!")
    elif total_added > 500:
        print(f"✅ Good coverage achieved!")
    else:
        print(f"⚠️  Limited coverage - may need additional extraction strategies")

if __name__ == "__main__":
    main()