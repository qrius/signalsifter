#!/usr/bin/env python3
"""
Username Selector Diagnostic Script
Analyze the DOM structure to understand why username extraction is failing
"""

import asyncio
import logging
from playwright.async_api import async_playwright
from fake_useragent import UserAgent

class UsernameDebugger:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
    async def debug_username_selectors(self):
        """Debug username selector matching"""
        
        async with async_playwright() as p:
            # Launch browser with Discord-friendly settings
            browser = await p.chromium.launch(
                headless=False,  # Keep visible for debugging
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-first-run',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            ua = UserAgent()
            context = await browser.new_context(
                user_agent=ua.random,
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = await context.new_page()
            
            try:
                # Navigate to Discord channel
                url = "https://discord.com/channels/1296015181985349715/1296015182417629249"
                await page.goto(url, wait_until='networkidle', timeout=60000)
                
                # Wait for messages to load
                await page.wait_for_selector('div[id][class*="message"]', timeout=30000)
                await asyncio.sleep(5)  # Let page fully load
                
                # Get all message elements
                messages = page.locator('div[id][class*="message"]')
                message_count = await messages.count()
                
                self.logger.info(f"Found {message_count} messages on page")
                
                # Analyze first few messages
                for i in range(min(3, message_count)):
                    message = messages.nth(i)
                    self.logger.info(f"\n=== MESSAGE {i+1} ===")
                    
                    # Get message HTML structure
                    message_html = await message.inner_html()
                    self.logger.info(f"Message HTML preview: {message_html[:200]}...")
                    
                    # Test our username selectors
                    username_selectors = [
                        'h3 span:first-child',
                        'h3 button span',
                        'h3 > span',
                        'button[tabindex="0"] span',
                        'span[data-text-variant*="semibold"]',
                        'span[data-text-variant="text-md/semibold"]',
                        '[role="button"] span:first-child',
                        'header span:first-child',
                        '[role="heading"] span',
                        'h3 [role="button"] span',
                        'h3 span',
                        'button span'
                    ]
                    
                    found_username = False
                    for selector in username_selectors:
                        try:
                            username_elem = message.locator(selector)
                            count = await username_elem.count()
                            
                            if count > 0:
                                # Test first match
                                text = await username_elem.first.inner_text()
                                text = text.strip()
                                
                                self.logger.info(f"  Selector '{selector}': {count} matches, first text: '{text}'")
                                
                                if (text and len(text) > 0 and len(text) < 50 and 
                                    not text.startswith('http') and ':' not in text):
                                    self.logger.info(f"  ✅ VALID USERNAME FOUND: '{text}'")
                                    found_username = True
                                else:
                                    self.logger.info(f"  ❌ Invalid username text: '{text}'")
                            else:
                                self.logger.debug(f"  Selector '{selector}': 0 matches")
                                
                        except Exception as e:
                            self.logger.debug(f"  Error with selector '{selector}': {e}")
                    
                    if not found_username:
                        self.logger.warning(f"  🔴 NO VALID USERNAME FOUND for message {i+1}")
                        
                        # Try to find all text elements and see what's available
                        all_spans = message.locator('span')
                        span_count = await all_spans.count()
                        self.logger.info(f"  Found {span_count} span elements total:")
                        
                        for j in range(min(10, span_count)):
                            span_text = await all_spans.nth(j).inner_text()
                            self.logger.info(f"    Span {j+1}: '{span_text.strip()}'")
                    
                    self.logger.info("-" * 50)
                
            except Exception as e:
                self.logger.error(f"Error during debugging: {e}")
                
            finally:
                await browser.close()

async def main():
    debugger = UsernameDebugger()
    await debugger.debug_username_selectors()

if __name__ == "__main__":
    asyncio.run(main())