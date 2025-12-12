#!/usr/bin/env python3
"""
Debug what messages are currently visible in Discord
Shows timestamps to help verify scroll position
"""

import asyncio
import logging
from playwright.async_api import async_playwright
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DebugVisibleMessages:
    def __init__(self):
        self.debug_port = 9222
    
    async def setup_page_connection(self):
        """Connect to existing Chrome browser"""
        try:
            playwright = await async_playwright().start()
            
            # Connect to existing Chrome with debugging port
            browser = await playwright.chromium.connect_over_cdp(f"http://localhost:{self.debug_port}")
            
            # Find Discord page
            contexts = browser.contexts
            for context in contexts:
                pages = context.pages
                for page in pages:
                    if 'discord.com/channels' in page.url:
                        logger.info(f"Found Discord page: {page.url}")
                        return playwright, browser, page
            
            return playwright, browser, None
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return None, None, None
    
    async def show_visible_timestamps(self, page):
        """Show timestamps of currently visible messages"""
        try:
            print("🔍 ANALYZING VISIBLE MESSAGES...")
            
            # Try different message selectors
            selectors = [
                '[id^="chat-messages-"]',
                '[class*="message"]',
                'li[id^="chat-messages-"]'
            ]
            
            timestamps = []
            
            for selector in selectors:
                messages = page.locator(selector)
                count = await messages.count()
                
                if count > 0:
                    print(f"📋 Found {count} messages with selector: {selector}")
                    
                    # Get first 10 and last 10 message timestamps
                    sample_indices = list(range(min(10, count))) + list(range(max(0, count-10), count))
                    sample_indices = sorted(set(sample_indices))  # Remove duplicates and sort
                    
                    for i in sample_indices:
                        try:
                            message = messages.nth(i)
                            
                            # Look for timestamp
                            timestamp_elem = message.locator('time')
                            if await timestamp_elem.count() > 0:
                                timestamp_str = await timestamp_elem.get_attribute('datetime')
                                if timestamp_str:
                                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                    timestamps.append((i, timestamp))
                                    
                        except Exception as e:
                            logger.debug(f"Error processing message {i}: {e}")
                            continue
                    
                    break  # Use first working selector
            
            if timestamps:
                timestamps.sort(key=lambda x: x[1])  # Sort by timestamp
                
                print(f"\n📅 VISIBLE MESSAGE TIMESTAMPS:")
                print(f"📍 Showing timestamps from {len(timestamps)} sample messages")
                print("=" * 60)
                
                for idx, (msg_idx, ts) in enumerate(timestamps):
                    date_str = ts.strftime("%Y-%m-%d %H:%M:%S")
                    if idx == 0:
                        print(f"🟢 EARLIEST: Message #{msg_idx}: {date_str}")
                    elif idx == len(timestamps) - 1:
                        print(f"🔴 LATEST:   Message #{msg_idx}: {date_str}")
                    elif idx < 5 or idx >= len(timestamps) - 5:
                        print(f"   Message #{msg_idx}: {date_str}")
                    elif idx == 5 and len(timestamps) > 10:
                        print("   ... (middle messages omitted) ...")
                
                earliest = timestamps[0][1]
                latest = timestamps[-1][1]
                
                print("\n" + "=" * 60)
                print(f"📊 SUMMARY:")
                print(f"   Earliest visible: {earliest.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Latest visible:   {latest.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Time span: {(latest - earliest).days} days, {(latest - earliest).seconds // 3600} hours")
                
                # Check if we're in the target range
                if earliest.date() <= datetime(2025, 11, 20).date():
                    print("🎉 SUCCESS! You can see messages from November 20th or earlier!")
                    print("   Now run: python3 direct_capture.py")
                elif earliest.date() <= datetime(2025, 11, 26).date():
                    print("⚠️  CLOSE! You're seeing late November content.")
                    print("   Scroll up more to reach November 17-20th")
                else:
                    print("❌ NEED MORE SCROLLING: Still seeing December content")
                    print("   Keep scrolling up to reach November 17-20th")
                    
            else:
                print("❌ No timestamps found in visible messages")
                
        except Exception as e:
            logger.error(f"Error analyzing messages: {e}")

async def main():
    """Main debug function"""
    debug = DebugVisibleMessages()
    
    print("🔍 DISCORD SCROLL POSITION DEBUG")
    print("=" * 50)
    print("This will show you what message timestamps are currently visible")
    print("to help verify if you've scrolled back to November 17th")
    print()
    
    # Setup connection
    playwright, browser, page = await debug.setup_page_connection()
    
    if not page:
        print("❌ Could not connect to Discord page")
        print("Please:")
        print("1. Make sure Chrome is running with: chrome --remote-debugging-port=9222")
        print("2. Navigate to Discord channel in that Chrome window")
        print("3. Run this script again")
        return
    
    try:
        print(f"✅ Connected to Discord page: {page.url}")
        await debug.show_visible_timestamps(page)
        
    except Exception as e:
        logger.error(f"Debug failed: {e}")
        
    finally:
        try:
            await browser.close()
            await playwright.stop()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())