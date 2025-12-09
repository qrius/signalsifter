#!/usr/bin/env python3
"""
Simple Discord Message Element Inspector
"""
import os
import asyncio
import logging
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

async def inspect_message_elements():
    """Inspect what's actually in the Discord message elements"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to Discord
            logger.info("Navigating to Discord channel...")
            await page.goto("https://discord.com/channels/1296015181985349715/1296015182417629249", 
                          wait_until="load", timeout=30000)
            
            # Wait for page to load
            await asyncio.sleep(5)
            
            # Check URL
            logger.info(f"Current URL: {page.url}")
            
            # Try different selectors and inspect the first message
            selectors = [
                'div[id][class*="message"]',
                '[data-list-item-id]',
                'li[id][class*="messageListItem"]',
                '[class*="messageListItem"]',
                '[class*="message-"]'
            ]
            
            for selector in selectors:
                try:
                    elements = await page.locator(selector).all()
                    logger.info(f"Selector '{selector}': {len(elements)} elements")
                    
                    if elements:
                        # Inspect first element
                        first_elem = elements[0]
                        html = await first_elem.inner_html()
                        logger.info(f"First element HTML (first 200 chars): {html[:200]}...")
                        
                        # Try to find common message parts
                        try:
                            message_id = await first_elem.get_attribute('id')
                            logger.info(f"Message ID: {message_id}")
                        except:
                            logger.info("No ID attribute")
                            
                        try:
                            # Look for username
                            username_selectors = [
                                '[class*="username"]',
                                '[class*="author"]',
                                '[data-testid="username"]'
                            ]
                            for username_sel in username_selectors:
                                username_elem = first_elem.locator(username_sel)
                                if await username_elem.count() > 0:
                                    username = await username_elem.first.inner_text()
                                    logger.info(f"Username ({username_sel}): {username}")
                                    break
                        except Exception as e:
                            logger.info(f"Username extraction failed: {e}")
                            
                        try:
                            # Look for content
                            content_selectors = [
                                '[class*="messageContent"]',
                                '[class*="content"]',
                                '[data-testid="message-content"]'
                            ]
                            for content_sel in content_selectors:
                                content_elem = first_elem.locator(content_sel)
                                if await content_elem.count() > 0:
                                    content = await content_elem.first.inner_text()
                                    logger.info(f"Content ({content_sel}): {content[:100]}...")
                                    break
                        except Exception as e:
                            logger.info(f"Content extraction failed: {e}")
                        
                        break  # Stop after first working selector
                        
                except Exception as e:
                    logger.info(f"Selector '{selector}' failed: {e}")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_message_elements())