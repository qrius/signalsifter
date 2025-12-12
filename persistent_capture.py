#!/usr/bin/env python3
"""
Persistent Discord message capture - keeps browser open
"""

import asyncio
import sqlite3
import logging
from playwright.async_api import async_playwright
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PersistentDiscordCapture:
    def __init__(self):
        self.debug_port = 9222
        self.db_path = 'data/backfill.sqlite'
    
    async def connect_to_existing_chrome(self):
        """Connect to existing Chrome browser without closing it"""
        try:
            playwright = await async_playwright().start()
            
            # Connect to existing Chrome
            browser = await playwright.chromium.connect_over_cdp(f"http://localhost:{self.debug_port}")
            
            # Find Discord page
            contexts = browser.contexts
            discord_page = None
            
            for context in contexts:
                pages = context.pages
                for page in pages:
                    if 'discord.com/channels' in page.url:
                        logger.info(f"Found Discord page: {page.url}")
                        discord_page = page
                        break
                if discord_page:
                    break
            
            return playwright, browser, discord_page
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return None, None, None
    
    async def capture_visible_messages(self, page):
        """Capture messages visible on current page"""
        try:
            # Selectors for Discord messages
            selectors = [
                '[id^="chat-messages-"]',
                'li[id^="chat-messages-"]',
                '[class*="message"]'
            ]
            
            captured_count = 0
            
            for selector in selectors:
                messages = page.locator(selector)
                count = await messages.count()
                
                if count > 0:
                    print(f"📋 Found {count} messages with selector: {selector}")
                    
                    for i in range(count):
                        try:
                            message = messages.nth(i)
                            
                            # Get message ID
                            msg_id = await message.get_attribute('id')
                            if not msg_id:
                                continue
                            
                            # Get timestamp
                            timestamp_elem = message.locator('time')
                            if await timestamp_elem.count() == 0:
                                continue
                                
                            timestamp_str = await timestamp_elem.get_attribute('datetime')
                            if not timestamp_str:
                                continue
                            
                            # Get username
                            username = 'Unknown'
                            username_elem = message.locator('span[class*="username"]')
                            if await username_elem.count() > 0:
                                username = await username_elem.first.inner_text()
                            
                            if not username or username == 'Unknown':
                                username_elem = message.locator('h3 span').first
                                if await username_elem.count() > 0:
                                    username = await username_elem.inner_text()
                            
                            # Clean username
                            if username:
                                username = username.strip().replace('@', '')
                            else:
                                username = 'Unknown'
                            
                            # Get message content
                            content = await message.inner_text()
                            
                            # Parse timestamp
                            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            
                            # Save to database
                            if await self.save_message_to_db(msg_id, timestamp, username, content):
                                captured_count += 1
                                
                        except Exception as e:
                            logger.debug(f"Error processing message {i}: {e}")
                            continue
                    
                    # Use first working selector
                    break
            
            return captured_count
            
        except Exception as e:
            logger.error(f"Error capturing messages: {e}")
            return 0
    
    async def save_message_to_db(self, msg_id, timestamp, username, content):
        """Save message to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert message (ignore duplicates)
            cursor.execute('''
                INSERT OR IGNORE INTO discord_messages 
                (message_id, timestamp, username, content, channel_id, server_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                msg_id,
                timestamp,
                username,
                content[:2000],  # Limit content length
                'persistent_capture',
                'persistent_capture'
            ))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            return success
            
        except Exception as e:
            logger.debug(f"Database error: {e}")
            return False
    
    def get_db_stats(self):
        """Get current database statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    MIN(DATE(timestamp)) as earliest,
                    MAX(DATE(timestamp)) as latest,
                    COUNT(DISTINCT username) as users
                FROM discord_messages
            ''')
            
            result = cursor.fetchone()
            conn.close()
            return result
            
        except Exception as e:
            logger.error(f"Database error: {e}")
            return (0, None, None, 0)

async def main():
    """Main capture function - keeps browser open"""
    capture = PersistentDiscordCapture()
    
    print("🎯 PERSISTENT DISCORD CAPTURE")
    print("=" * 50)
    print("This version keeps your browser open for multiple captures!")
    print()
    print("Instructions:")
    print("1. Open Chrome with: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
    print("2. Navigate to Discord channel in that Chrome window")  
    print("3. Navigate to the specific message or scroll position you want")
    print("4. Run this script to capture what's currently visible")
    print("5. Browser stays open - navigate to different positions and run again")
    print()
    
    # Connect to existing Chrome
    playwright, browser, page = await capture.connect_to_existing_chrome()
    
    if not page:
        print("❌ Could not find Discord page")
        print("Please:")
        print("1. Make sure Chrome is running with debugging port")
        print("2. Navigate to a Discord channel in that Chrome window")
        print("3. Run this script again")
        return
    
    try:
        print(f"✅ Connected to Discord page: {page.url}")
        print("🔄 Capturing messages from current page state...")
        
        # Get stats before capture
        total_before, _, _, _ = capture.get_db_stats()
        
        # Capture messages
        captured = await capture.capture_visible_messages(page)
        
        # Get updated stats
        total_after, earliest, latest, users = capture.get_db_stats()
        
        print(f"\n📊 CAPTURE RESULTS:")
        print(f"📥 New messages captured: {captured}")
        print(f"📈 Total messages in DB: {total_after} (was {total_before})")
        print(f"📅 Date range: {earliest} → {latest}")
        print(f"👥 Unique users: {users}")
        
        if captured > 0:
            print("🎉 SUCCESS! Captured new messages!")
            
            # Check if we got November content
            if earliest and earliest <= '2025-11-20':
                print("🌟 EXCELLENT! You've reached November content!")
            
        else:
            print("ℹ️  No new messages (already in database)")
        
        print(f"\n🔄 Browser stays open - navigate to different position and run again!")
        
    except Exception as e:
        logger.error(f"Capture failed: {e}")
        
    finally:
        # DON'T close browser - keep it open for next capture
        print("🌐 Browser kept open for next capture")
        await playwright.stop()  # Only stop playwright connection

if __name__ == "__main__":
    asyncio.run(main())