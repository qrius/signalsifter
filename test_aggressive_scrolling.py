#!/usr/bin/env python3
"""
Aggressive Discord scrolling test to load more historical messages
"""

import asyncio
import os
from playwright.async_api import async_playwright
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

async def test_aggressive_scrolling():
    """Test more aggressive scrolling to load historical messages"""
    
    channel_url = "https://discord.com/channels/1296015181985349715/1296015182417629249"
    
    playwright = await async_playwright().start()
    
    # Use same browser profile as main extractor
    user_data_dir = os.path.expanduser("~/.SignalSifter/discord_browser_profile")
    
    browser = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(user_data_dir),
        headless=False,  # Keep visible to see what's happening
        viewport={'width': 1920, 'height': 1080}
    )
    
    page = await browser.new_page()
    
    try:
        print("🚀 Starting aggressive scrolling test...")
        
        # Navigate to channel
        await page.goto(channel_url, wait_until="networkidle")
        await asyncio.sleep(3)
        
        # Wait for messages to load
        await page.wait_for_selector('[data-list-id="chat-messages"]', timeout=10000)
        
        print("📊 Starting message count...")
        initial_count = await page.locator('[id^="chat-messages-"]').count()
        print(f"Initial messages loaded: {initial_count}")
        
        # More aggressive scrolling
        max_scrolls = 100
        no_change_count = 0
        current_count = initial_count
        
        for scroll_attempt in range(max_scrolls):
            # Multiple scrolling methods
            await page.keyboard.press('Home')
            await asyncio.sleep(1)
            
            # Scroll with mouse wheel
            await page.mouse.wheel(0, -2000)
            await asyncio.sleep(1)
            
            # Try Page Up key multiple times
            for _ in range(3):
                await page.keyboard.press('PageUp')
                await asyncio.sleep(0.5)
            
            # Check for new messages
            new_count = await page.locator('[id^="chat-messages-"]').count()
            
            if new_count > current_count:
                print(f"📈 Scroll {scroll_attempt}: {new_count} messages (+{new_count - current_count})")
                current_count = new_count
                no_change_count = 0
                
                # Check oldest message date
                try:
                    first_message = page.locator('[id^="chat-messages-"]').first
                    timestamp_elem = first_message.locator('time').first
                    if await timestamp_elem.count() > 0:
                        timestamp_str = await timestamp_elem.get_attribute('datetime')
                        if timestamp_str:
                            message_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            print(f"  └─ Oldest message: {message_date}")
                            
                            # Stop if we've reached October (server creation)
                            if message_date.month == 10 and message_date.year == 2024:
                                print("🎯 Reached server creation time (October 2024)")
                                break
                except Exception as e:
                    print(f"  └─ Error checking date: {e}")
            else:
                no_change_count += 1
                print(f"⏸️  No new messages (attempt {no_change_count}/10)")
                
                if no_change_count >= 10:
                    print("🏁 Stopping - no more messages loading")
                    break
            
            await asyncio.sleep(2)  # Rate limiting
        
        final_count = await page.locator('[id^="chat-messages-"]').count()
        print(f"\n✅ Final result: {final_count} total messages loaded")
        print(f"📈 Improvement: +{final_count - initial_count} additional messages")
        
        # Get date range of loaded messages
        try:
            first_message = page.locator('[id^="chat-messages-"]').first
            last_message = page.locator('[id^="chat-messages-"]').last
            
            first_time = await first_message.locator('time').first.get_attribute('datetime')
            last_time = await last_message.locator('time').last.get_attribute('datetime')
            
            if first_time and last_time:
                first_date = datetime.fromisoformat(first_time.replace('Z', '+00:00'))
                last_date = datetime.fromisoformat(last_time.replace('Z', '+00:00'))
                print(f"📅 Date range: {first_date} to {last_date}")
                days_span = (last_date - first_date).days
                print(f"⏳ Span: {days_span} days")
        except Exception as e:
            print(f"❌ Error getting date range: {e}")
        
        input("\n⏸️  Press Enter to close browser...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_aggressive_scrolling())