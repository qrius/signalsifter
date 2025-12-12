#!/usr/bin/env python3
"""
Weekly Discord Extraction Strategy
Extracts Discord messages week by week to ensure comprehensive coverage
"""

import asyncio
import subprocess
import sys
from datetime import datetime, timedelta
import sqlite3

class WeeklyDiscordExtractor:
    def __init__(self, channel_url):
        self.channel_url = channel_url
        self.db_path = "data/backfill.sqlite"
        
    def get_current_coverage(self):
        """Check what date range we already have in the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_messages,
                    MIN(DATE(timestamp)) as earliest_date,
                    MAX(DATE(timestamp)) as latest_date
                FROM discord_messages 
                WHERE content IS NOT NULL AND content != ''
            """)
            
            result = cursor.fetchone()
            conn.close()
            
            if result[0] > 0:
                print(f"📊 Current database: {result[0]} messages from {result[1]} to {result[2]}")
                return result[1], result[2], result[0]
            else:
                print("📊 Database is empty")
                return None, None, 0
                
        except Exception as e:
            print(f"❌ Error checking database: {e}")
            return None, None, 0
    
    def run_extraction_with_limit(self, limit, description=""):
        """Run extraction with a specific message limit"""
        try:
            print(f"\n🚀 Starting extraction: {description}")
            print(f"   Target: {limit} messages")
            
            # Run the extraction command
            cmd = [
                "python3", "discord_browser_extractor.py",
                "--url", self.channel_url,
                "--limit", str(limit),
                "--verbose"
            ]
            
            # Activate virtual environment and run command
            full_cmd = f"source signalsifter-env/bin/activate && {' '.join(cmd)}"
            
            print(f"🔧 Command: {' '.join(cmd)}")
            
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )
            
            if result.returncode == 0:
                print(f"✅ Extraction completed successfully")
                print(f"📝 Output: {result.stdout[-200:]}")  # Last 200 chars
                return True
            else:
                print(f"❌ Extraction failed with return code: {result.returncode}")
                print(f"📝 Error: {result.stderr[-200:]}")  # Last 200 chars of error
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ Extraction timed out after 30 minutes")
            return False
        except Exception as e:
            print(f"❌ Extraction error: {e}")
            return False
    
    def progressive_extraction(self):
        """Run progressive extraction with increasing limits"""
        print("🎯 Starting Progressive Discord Extraction Strategy")
        print("=" * 60)
        
        # Check current status
        earliest, latest, current_count = self.get_current_coverage()
        
        # Define extraction targets (progressive limits)
        extraction_rounds = [
            (500, "Initial batch - 500 messages"),
            (1000, "Extended batch - 1000 messages"), 
            (2000, "Deep extraction - 2000 messages"),
            (5000, "Comprehensive - 5000 messages"),
            (10000, "Full archive - 10000 messages")
        ]
        
        successful_extractions = 0
        
        for limit, description in extraction_rounds:
            print(f"\n{'='*60}")
            print(f"🎯 EXTRACTION ROUND: {description}")
            print(f"{'='*60}")
            
            # Check current count before extraction
            _, _, pre_count = self.get_current_coverage()
            
            if self.run_extraction_with_limit(limit, description):
                successful_extractions += 1
                
                # Check count after extraction
                _, _, post_count = self.get_current_coverage()
                new_messages = post_count - pre_count
                
                print(f"📈 Added {new_messages} new messages (total: {post_count})")
                
                # If we got very few new messages, the channel might be exhausted
                if new_messages < 10:
                    print(f"⚠️  Only {new_messages} new messages found - channel likely exhausted")
                    break
                    
            else:
                print(f"❌ Extraction round failed: {description}")
                # Don't break - try the next round
                
            print(f"\n⏳ Waiting 30 seconds before next round...")
            import time
            time.sleep(30)
        
        print(f"\n🏁 Progressive extraction completed!")
        print(f"   Successful rounds: {successful_extractions}/{len(extraction_rounds)}")
        
        # Final status
        _, _, final_count = self.get_current_coverage()
        print(f"   Final message count: {final_count}")
        
        return final_count

def main():
    """Main function"""
    channel_url = "https://discord.com/channels/1296015181985349715/1296015182417629249"
    
    extractor = WeeklyDiscordExtractor(channel_url)
    final_count = extractor.progressive_extraction()
    
    print(f"\n🎉 Extraction strategy complete!")
    print(f"📊 Total messages extracted: {final_count}")
    
    if final_count > 500:
        print(f"\n✅ Good coverage achieved! Ready for analysis.")
    else:
        print(f"\n⚠️  Limited coverage - consider manual extraction or different approach.")

if __name__ == "__main__":
    main()