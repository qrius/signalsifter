#!/usr/bin/env python3
"""
Simple message capture while you manually scroll Discord
No browser automation - just captures what's visible as you scroll
"""

import asyncio
import sqlite3
from datetime import datetime
from playwright.async_api import async_playwright
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ManualScrollCapture:
    def __init__(self):
        self.db_path = 'data/backfill.sqlite'
        self.seen_messages = set()
        
    async def connect_to_existing_browser(self):
        """Connect to your existing Discord browser session"""
        playwright = await async_playwright().start()
        
        # Connect to existing browser if possible, otherwise launch new
        try:
            browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
            pages = browser.contexts[0].pages
            if pages:
                self.page = pages[0]  # Use first existing page
                logger.info("Connected to existing browser session")
            else:
                self.page = await browser.contexts[0].new_page()
        except:
            # Launch new browser if can't connect
            browser = await playwright.chromium.launch(
                headless=False,
                args=['--remote-debugging-port=9222']
            )
            context = await browser.new_context()
            self.page = await context.new_page()
            logger.info("Launched new browser - navigate to Discord channel manually")
            
        return playwright, browser
    
    async def capture_visible_messages(self):
        """Capture all currently visible messages on page"""
        try:
            # Multiple selectors to try
            selectors = [
                '[id^="chat-messages-"]',
                '[class*="message"][id*="chat-messages"]',
                'li[id*="chat-messages"]'
            ]
            
            captured = 0
            
            for selector in selectors:
                elements = await self.page.locator(selector).all()
                if not elements:
                    continue
                    
                logger.debug(f"Found {len(elements)} messages with selector: {selector}")
                
                for elem in elements:
                    try:
                        msg_id = await elem.get_attribute('id')
                        if not msg_id or msg_id in self.seen_messages:
                            continue
                            
                        # Get timestamp
                        time_elem = elem.locator('time').first
                        timestamp_str = None
                        if await time_elem.count() > 0:
                            timestamp_str = await time_elem.get_attribute('datetime')
                        
                        if not timestamp_str:
                            continue
                            
                        # Get username
                        username = 'Unknown'
                        # Try different username selectors
                        user_selectors = [
                            'span[data-text]',
                            '[class*="username"]',
                            'h3 span'
                        ]
                        
                        for u_sel in user_selectors:
                            u_elem = elem.locator(u_sel).first
                            if await u_elem.count() > 0:
                                user_text = await u_elem.get_attribute('data-text')
                                if not user_text:
                                    user_text = await u_elem.inner_text()
                                if user_text and user_text.strip():
                                    username = user_text.strip().replace('@', '')
                                    break
                        
                        # Get message content
                        content = await elem.inner_text()
                        
                        # Save to database
                        if await self.save_message(msg_id, timestamp_str, username, content):
                            captured += 1
                            self.seen_messages.add(msg_id)
                            
                    except Exception as e:
                        logger.debug(f"Error processing message: {e}")
                        
                break  # Use first working selector
            
            return captured
            
        except Exception as e:
            logger.error(f"Error capturing messages: {e}")
            return 0
    
    async def save_message(self, msg_id, timestamp_str, username, content):
        """Save message to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Parse timestamp
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # Insert message (ignore duplicates)
            cursor.execute('''
                INSERT OR IGNORE INTO discord_messages 
                (message_id, timestamp, username, content, channel_id, server_id, extraction_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                msg_id,
                timestamp,
                username,
                content[:2000],  # Limit content
                'manual_scroll',
                'manual_scroll',
                datetime.now()
            ))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            return success
            
        except Exception as e:
            logger.debug(f"Error saving message: {e}")
            return False
    
    def get_current_stats(self):
        """Get current database stats"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    MIN(DATE(timestamp)) as earliest,
                    MAX(DATE(timestamp)) as latest,
                    MIN(timestamp) as earliest_full
                FROM discord_messages
            ''')
            
            result = cursor.fetchone()
            conn.close()
            return result
            
        except Exception as e:
            logger.error(f"Database error: {e}")
            return (0, None, None, None)

async def main():
    """Main capture loop"""
    capture = ManualScrollCapture()
    
    print("🎯 MANUAL SCROLL CAPTURE")
    print("=" * 50)
    print("Instructions:")
    print("1. Make sure Discord is open in your browser")
    print("2. Navigate to the STBL channel")
    print("3. This script will capture messages as you scroll")
    print("4. Scroll UP slowly to load older messages")
    print("5. Press Ctrl+C when done")
    print("")
    
    try:
        playwright, browser = await capture.connect_to_existing_browser()
        
        print("🔄 Starting capture loop...")
        print("Scroll up in Discord to load older messages!")
        
        total_captured = 0
        
        while True:
            # Capture visible messages
            new_captures = await capture.capture_visible_messages()
            
            if new_captures > 0:
                total_captured += new_captures
                
                # Get current stats
                total, earliest, latest, earliest_full = capture.get_current_stats()
                
                print(f"\n📥 Captured {new_captures} new messages")
                print(f"📊 Total: {total} messages")
                print(f"📅 Range: {earliest} → {latest}")
                print(f"🕐 Earliest: {earliest_full}")
                
                # Check progress toward November 18th target
                if earliest and earliest <= '2025-11-18':
                    print("🎉 SUCCESS! Reached November 18th or earlier!")
                elif earliest:
                    target_date = datetime(2025, 11, 18)
                    current_date = datetime.strptime(earliest, '%Y-%m-%d')
                    days_to_go = (current_date - target_date).days
                    print(f"⏳ {days_to_go} more days to reach Nov 18th target")
                
                print("Continue scrolling UP for older messages...")
            
            # Check every 2 seconds
            await asyncio.sleep(2)
            
    except KeyboardInterrupt:
        print(f"\n🛑 Capture stopped")
        total, earliest, latest, earliest_full = capture.get_current_stats()
        print(f"Final: {total} total messages, earliest: {earliest}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        
    finally:
        try:
            await browser.close()
            await playwright.stop()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())