#!/usr/bin/env python3
"""
Weekly Discord Extractor for Better Coverage
Extracts Discord messages week by week to ensure comprehensive data collection
"""

import asyncio
import sys
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path

# Import the main extractor
from discord_browser_extractor import DiscordBrowserExtractor

class WeeklyDiscordExtractor:
    def __init__(self, channel_url, weeks_back=8):
        """Initialize weekly extractor"""
        self.channel_url = channel_url
        self.weeks_back = weeks_back
        self.db_path = "data/backfill.sqlite"
        
    def get_weekly_ranges(self):
        """Generate weekly date ranges for extraction"""
        end_date = datetime.now()
        ranges = []
        
        for week in range(self.weeks_back):
            week_end = end_date - timedelta(weeks=week)
            week_start = week_end - timedelta(days=7)
            ranges.append((week_start, week_end, week + 1))
            
        return ranges
    
    def check_existing_coverage(self, start_date, end_date):
        """Check if we already have good coverage for this week"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM discord_messages 
                WHERE DATE(timestamp) BETWEEN DATE(?) AND DATE(?)
            """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count
            
        except Exception as e:
            print(f"Error checking coverage: {e}")
            return 0
    
    async def extract_week(self, start_date, end_date, week_num):
        """Extract messages for a specific week"""
        print(f"\n{'='*60}")
        print(f"📅 WEEK {week_num}: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"{'='*60}")
        
        # Check existing coverage
        existing_count = self.check_existing_coverage(start_date, end_date)
        print(f"📊 Existing messages for this week: {existing_count}")
        
        if existing_count > 50:  # Good coverage threshold
            print(f"✅ Week {week_num} already has good coverage ({existing_count} messages), skipping...")
            return existing_count
        
        # Configure extractor for this week
        config = {
            'verbose': True,
            'rate_limit': 2000,  # Higher rate limit for efficiency
        }
        
        extractor = DiscordBrowserExtractor(config)
        
        try:
            # Setup browser
            await extractor.setup_browser(headless=True)  # Use headless for efficiency
            
            # Login to Discord
            if not await extractor.login_to_discord(self.channel_url):
                print(f"❌ Failed to login for week {week_num}")
                return 0
            
            # Calculate how many messages to extract (estimate ~50-100 per week for active channel)
            estimated_limit = 150  # Liberal estimate per week
            
            # Extract messages with a reasonable limit
            messages = await extractor.extract_channel_messages(
                self.channel_url,
                limit=estimated_limit,
                months_back=None,  # Don't use months_back, use limit instead
                dry_run=False
            )
            
            # Filter messages to this week's date range (post-processing filter)
            week_messages = []
            for msg in messages:
                msg_date = msg.get('timestamp')
                if msg_date:
                    # Convert to datetime if it's a string
                    if isinstance(msg_date, str):
                        try:
                            msg_date = datetime.fromisoformat(msg_date.replace('Z', '+00:00'))
                        except:
                            continue
                    
                    # Check if message is in this week's range
                    if hasattr(msg_date, 'date'):
                        msg_date = msg_date.date()
                    elif hasattr(msg_date, 'year'):
                        msg_date = msg_date.date()
                    else:
                        continue
                        
                    if start_date.date() <= msg_date <= end_date.date():
                        week_messages.append(msg)
            
            print(f"✅ Week {week_num}: Extracted {len(week_messages)} messages in date range")
            return len(week_messages)
            
        except Exception as e:
            print(f"❌ Error extracting week {week_num}: {e}")
            return 0
            
        finally:
            await extractor.cleanup()
    
    async def run_weekly_extraction(self):
        """Run the complete weekly extraction process"""
        print("🚀 Starting Weekly Discord Extraction")
        print(f"📋 Target: {self.weeks_back} weeks of data")
        print(f"🔗 Channel: {self.channel_url}")
        
        # Get weekly ranges
        weekly_ranges = self.get_weekly_ranges()
        
        total_messages = 0
        successful_weeks = 0
        
        for start_date, end_date, week_num in weekly_ranges:
            try:
                messages_count = await self.extract_week(start_date, end_date, week_num)
                total_messages += messages_count
                
                if messages_count > 0:
                    successful_weeks += 1
                    
                # Brief pause between weeks to avoid rate limiting
                if week_num < len(weekly_ranges):
                    print("⏸️  Brief pause between weeks...")
                    await asyncio.sleep(5)
                    
            except Exception as e:
                print(f"❌ Week {week_num} failed: {e}")
                continue
        
        print(f"\n{'='*60}")
        print(f"🎉 WEEKLY EXTRACTION COMPLETE")
        print(f"{'='*60}")
        print(f"✅ Successful weeks: {successful_weeks}/{len(weekly_ranges)}")
        print(f"📊 Total messages extracted: {total_messages}")
        
        # Final database check
        self.check_final_coverage()
        
        return total_messages
    
    def check_final_coverage(self):
        """Check final database coverage"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_messages,
                    COUNT(DISTINCT username) as unique_users,
                    MIN(DATE(timestamp)) as earliest_date,
                    MAX(DATE(timestamp)) as latest_date,
                    COUNT(DISTINCT DATE(timestamp)) as days_covered
                FROM discord_messages
            """)
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                total, users, earliest, latest, days = result
                print(f"\n📈 FINAL DATABASE STATS:")
                print(f"   📊 Total Messages: {total:,}")
                print(f"   👥 Unique Users: {users}")
                print(f"   📅 Date Range: {earliest} to {latest}")
                print(f"   🗓️  Days with Data: {days}")
                
                if total > 0:
                    print(f"   📊 Avg Messages/Day: {total/max(days,1):.1f}")
            
        except Exception as e:
            print(f"Error checking final coverage: {e}")

async def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python weekly_discord_extractor.py <discord_channel_url> [weeks_back]")
        print("Example: python weekly_discord_extractor.py 'https://discord.com/channels/1296015181985349715/1296015182417629249' 8")
        sys.exit(1)
    
    channel_url = sys.argv[1]
    weeks_back = int(sys.argv[2]) if len(sys.argv) > 2 else 8  # Default 8 weeks (2 months)
    
    extractor = WeeklyDiscordExtractor(channel_url, weeks_back)
    
    try:
        total_messages = await extractor.run_weekly_extraction()
        print(f"\n🎉 Extraction complete! {total_messages} total messages extracted.")
        return 0
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)