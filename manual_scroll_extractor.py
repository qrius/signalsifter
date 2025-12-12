#!/usr/bin/env python3
"""
Manual scroll extraction assistant - works with human scrolling
This tool captures messages while you manually scroll through Discord
"""

import asyncio
import sqlite3
from datetime import datetime
from playwright.async_api import async_playwright
import json
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ManualScrollExtractor:
    def __init__(self, db_path='data/backfill.sqlite'):
        self.db_path = db_path
        self.page = None
        self.last_message_count = 0
        self.captured_messages = set()
        
    async def setup_browser(self):
        """Set up browser and connect to existing Discord session"""
        playwright = await async_playwright().start()
        
        # Use existing Discord session if available
        browser = await playwright.chromium.launch_persistent_context(
            user_data_dir=f"{os.path.expanduser('~')}/.SignalSifter/discord_browser_profile",
            headless=False
        )
        
        self.page = await browser.new_page()
        return playwright, browser
        
    async def capture_current_messages(self):
        """Capture all currently visible messages"""
        try:
            # Try different message selectors
            selectors = [
                '[id^="chat-messages-"]',
                '[class*="message"]',
                '[data-list-item-id*="chat-messages"]'
            ]
            
            messages = []
            
            for selector in selectors:
                message_elements = await self.page.locator(selector).all()
                if message_elements:
                    logger.info(f"Found {len(message_elements)} messages with selector: {selector}")
                    
                    for elem in message_elements:
                        try:
                            # Extract message ID to avoid duplicates
                            msg_id = await elem.get_attribute('id')
                            if not msg_id or msg_id in self.captured_messages:
                                continue
                                
                            # Extract timestamp
                            time_elem = elem.locator('time').first
                            timestamp_str = None
                            if await time_elem.count() > 0:
                                timestamp_str = await time_elem.get_attribute('datetime')
                            
                            # Extract username
                            username = 'Unknown'
                            username_selectors = [
                                '[data-text-variant="text-sm/semibold"]',
                                '[class*="username"]',
                                'span[data-text]'
                            ]
                            
                            for u_selector in username_selectors:
                                u_elem = elem.locator(u_selector).first
                                if await u_elem.count() > 0:
                                    username_text = await u_elem.get_attribute('data-text')
                                    if username_text and username_text.strip():
                                        username = username_text.strip()
                                        break
                            
                            # Extract content
                            content = await elem.inner_text() or ""
                            
                            if timestamp_str:
                                message = {
                                    'id': msg_id,
                                    'timestamp': timestamp_str,
                                    'username': username,
                                    'content': content[:1000],  # Limit content length
                                    'raw_html': await elem.inner_html()
                                }
                                messages.append(message)
                                self.captured_messages.add(msg_id)
                                
                        except Exception as e:
                            logger.debug(f"Error extracting message: {e}")
                            continue
                    break  # Use first working selector
                    
            return messages
            
        except Exception as e:
            logger.error(f"Error capturing messages: {e}")
            return []
    
    async def save_messages_to_db(self, messages):
        """Save captured messages to database"""
        if not messages:
            return 0
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            saved_count = 0
            for msg in messages:
                try:
                    # Parse timestamp
                    timestamp = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
                    
                    # Insert message (ignore duplicates)
                    cursor.execute('''
                        INSERT OR IGNORE INTO discord_messages 
                        (message_id, timestamp, username, content, channel_id, server_id, extraction_timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        msg['id'],
                        timestamp,
                        msg['username'],
                        msg['content'],
                        'manual_extraction',
                        'manual_extraction', 
                        datetime.now()
                    ))
                    
                    if cursor.rowcount > 0:
                        saved_count += 1
                        
                except Exception as e:
                    logger.debug(f"Error saving message {msg.get('id', 'unknown')}: {e}")
                    
            conn.commit()
            conn.close()
            
            return saved_count
            
        except Exception as e:
            logger.error(f"Database error: {e}")
            return 0
    
    async def monitor_scrolling(self, check_interval=3):
        """Monitor for new messages while user scrolls manually"""
        logger.info("=== MANUAL SCROLL EXTRACTOR ===")
        logger.info("Instructions:")
        logger.info("1. Navigate to the Discord channel you want to extract")
        logger.info("2. Scroll UP slowly to load older messages")
        logger.info("3. This script will automatically capture messages as you scroll")
        logger.info("4. Press Ctrl+C when done")
        logger.info("")
        logger.info("Starting monitoring...")
        
        total_captured = 0
        
        try:
            while True:
                # Capture current messages
                messages = await self.capture_current_messages()
                
                if messages:
                    # Save new messages
                    saved = await self.save_messages_to_db(messages)
                    if saved > 0:
                        total_captured += saved
                        logger.info(f"📥 Captured {saved} new messages (Total: {total_captured})")
                        
                        # Show date range of captured messages
                        timestamps = [msg['timestamp'] for msg in messages if 'timestamp' in msg]
                        if timestamps:
                            dates = [ts.split('T')[0] for ts in timestamps]
                            earliest = min(dates)
                            latest = max(dates)
                            logger.info(f"📅 Date range: {earliest} to {latest}")
                
                # Wait before next check
                await asyncio.sleep(check_interval)
                
        except KeyboardInterrupt:
            logger.info(f"\n🛑 Extraction stopped. Total captured: {total_captured} messages")
            
        except Exception as e:
            logger.error(f"Error during monitoring: {e}")

async def main():
    """Main function"""
    import os
    
    extractor = ManualScrollExtractor()
    
    try:
        playwright, browser = await extractor.setup_browser()
        
        logger.info("Browser ready! Navigate to your Discord channel and start scrolling...")
        await extractor.monitor_scrolling()
        
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        try:
            if extractor.page:
                await browser.close()
            await playwright.stop()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())