#!/usr/bin/env python3
"""
Direct Discord extraction without browser automation
Uses your existing Discord session in browser
"""

import asyncio
import sqlite3
from datetime import datetime
from playwright.async_api import async_playwright
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DirectCapture:
    def __init__(self):
        self.db_path = 'data/backfill.sqlite'
        
    async def setup_page_connection(self):
        """Connect to existing browser page"""
        playwright = await async_playwright().start()
        
        try:
            # Try to connect to running Chrome with remote debugging
            browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
            contexts = browser.contexts
            if contexts:
                pages = contexts[0].pages
                if pages:
                    for page in pages:
                        url = page.url
                        if 'discord.com/channels' in url:
                            logger.info(f"Found Discord page: {url}")
                            return playwright, browser, page
                            
            logger.info("No Discord page found, please navigate to Discord channel manually")
            return None, None, None
            
        except Exception as e:
            logger.error(f"Cannot connect to browser: {e}")
            logger.info("Please start Chrome with: chrome --remote-debugging-port=9222")
            return None, None, None
    
    async def capture_messages_directly(self, page):
        """Directly capture messages from current page state"""
        try:
            # Wait for page to be ready
            await page.wait_for_load_state('networkidle')
            
            # Try multiple message selectors
            message_selectors = [
                '[id^="chat-messages-"]',
                'li[id*="chat-messages"]',
                '[data-list-item-id*="chat-messages"]'
            ]
            
            captured_count = 0
            
            for selector in message_selectors:
                messages = await page.locator(selector).all()
                if not messages:
                    continue
                    
                logger.info(f"Found {len(messages)} messages with selector: {selector}")
                
                for message in messages:
                    try:
                        # Get message ID
                        msg_id = await message.get_attribute('id')
                        if not msg_id:
                            continue
                        
                        # Get timestamp
                        time_element = message.locator('time').first
                        if await time_element.count() == 0:
                            continue
                            
                        timestamp_str = await time_element.get_attribute('datetime')
                        if not timestamp_str:
                            continue
                        
                        # Get username - try multiple approaches
                        username = 'Unknown'
                        
                        # Method 1: data-text attribute
                        username_elem = message.locator('span[data-text]').first
                        if await username_elem.count() > 0:
                            username = await username_elem.get_attribute('data-text')
                        
                        # Method 2: if that fails, try inner text of username elements
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
                        logger.debug(f"Error processing message: {e}")
                        continue
                
                # Use first working selector
                if messages:
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
                'direct_capture',
                'direct_capture'
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
    """Main extraction function"""
    capture = DirectCapture()
    
    print("🎯 DIRECT DISCORD CAPTURE")
    print("=" * 50)
    print("Prerequisites:")
    print("1. Start Chrome with: chrome --remote-debugging-port=9222")
    print("2. Navigate to Discord channel in that Chrome window")
    print("3. Scroll to the position you want to capture (Nov 20)")
    print("4. Run this script to capture current visible messages")
    print()
    
    # Setup connection
    playwright, browser, page = await capture.setup_page_connection()
    
    if not page:
        print("❌ Could not connect to Discord page")
        print("Please:")
        print("1. Close all Chrome browsers")
        print("2. Start Chrome with: chrome --remote-debugging-port=9222")
        print("3. Navigate to Discord channel")
        print("4. Run this script again")
        return
    
    try:
        print(f"✅ Connected to Discord page: {page.url}")
        print("🔄 Capturing messages from current page state...")
        
        # Capture messages
        captured = await capture.capture_messages_directly(page)
        
        # Get updated stats
        total, earliest, latest, users = capture.get_db_stats()
        
        print(f"\n📊 CAPTURE RESULTS:")
        print(f"📥 New messages captured: {captured}")
        print(f"📈 Total messages in DB: {total}")
        print(f"📅 Date range: {earliest} → {latest}")
        print(f"👥 Unique users: {users}")
        
        if earliest and earliest <= '2025-11-20':
            print("🎉 SUCCESS! Captured messages from November 20th or earlier!")
        
    except Exception as e:
        logger.error(f"Capture failed: {e}")
        
    finally:
        try:
            await browser.close()
            await playwright.stop()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())