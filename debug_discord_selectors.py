#!/usr/bin/env python3
"""
Debug script to test Discord selectors and see what's available on the page
"""

import asyncio
import os
from playwright.async_api import async_playwright

async def debug_selectors():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to Discord
        print("Navigating to Discord...")
        await page.goto("https://discord.com/channels/1296015181985349715/1296015182417629249")
        
        # Wait for page to load and check if we're authenticated
        await page.wait_for_timeout(5000)
        
        # Check current URL to see if we were redirected
        current_url = page.url
        print(f"Current URL: {current_url}")
        
        # Check page title
        title = await page.title()
        print(f"Page title: {title}")
        
        # Check if we see a login screen
        login_elements = await page.locator('input[name="email"], input[name="username"], [class*="login"]').count()
        print(f"Login elements found: {login_elements}")
        
        if login_elements > 0:
            print("❌ Not authenticated - login required")
            return
        
        # Wait additional time for messages to load
        print("Waiting for messages to load...")
        await page.wait_for_timeout(10000)
        
        print("=== Testing Message Selectors ===")
        
        # Test different message selectors
        selectors = [
            'div[id^="chat-messages-"]',
            '[class*="message-"][id]',
            '[data-list-item-id]',
            'li[id][class*="messageListItem"]',
            'div[id][class*="message"]',
            '[role="listitem"]',
            '.message',
            '[class*="messageContainer"]'
        ]
        
        for selector in selectors:
            try:
                count = await page.locator(selector).count()
                print(f"Selector: {selector} -> Found {count} elements")
                
                if count > 0:
                    # Get first element and examine its structure
                    first_elem = page.locator(selector).first
                    html = await first_elem.inner_html()
                    print(f"  Sample HTML (first 200 chars): {html[:200]}...")
                    
            except Exception as e:
                print(f"Selector: {selector} -> ERROR: {e}")
        
        print("\n=== Testing Within First Message ===")
        
        # Find the first message and test selectors within it
        message_selectors = [
            'div[id^="chat-messages-"]',
            '[data-list-item-id]',
            'div[id][class*="message"]'
        ]
        
        first_message = None
        for msg_selector in message_selectors:
            if await page.locator(msg_selector).count() > 0:
                first_message = page.locator(msg_selector).first
                print(f"Using message selector: {msg_selector}")
                break
        
        if first_message:
            # Test content selectors
            content_selectors = [
                '[id^="message-content-"]',
                '.messageContent-2t3eCI',
                '[class*="messageContent"]',
                '.content',
                '[data-testid="message-content"]'
            ]
            
            for selector in content_selectors:
                try:
                    count = await first_message.locator(selector).count()
                    if count > 0:
                        text = await first_message.locator(selector).inner_text()
                        print(f"Content selector: {selector} -> '{text[:100]}...'")
                except Exception as e:
                    print(f"Content selector: {selector} -> ERROR: {e}")
                    
            # Test timestamp selectors
            timestamp_selectors = [
                'time',
                '[datetime]',
                '.timestamp',
                '[class*="timestamp"]'
            ]
            
            for selector in timestamp_selectors:
                try:
                    count = await first_message.locator(selector).count()
                    if count > 0:
                        elem = first_message.locator(selector).first
                        datetime_attr = await elem.get_attribute('datetime')
                        text = await elem.inner_text()
                        print(f"Timestamp selector: {selector} -> datetime='{datetime_attr}' text='{text}'")
                except Exception as e:
                    print(f"Timestamp selector: {selector} -> ERROR: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_selectors())