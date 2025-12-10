#!/usr/bin/env python3
"""
Discord Selector Diagnostic Tool
Tests current Discord CSS selectors to see what's working
"""

import asyncio
from playwright.async_api import async_playwright
import json
import sys

async def test_discord_selectors(url):
    """Test Discord CSS selectors on a live page"""
    
    print("🔍 Discord Selector Diagnostic Tool")
    print("=" * 50)
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            print(f"📱 Navigating to Discord channel...")
            await page.goto(url, wait_until='networkidle')
            await asyncio.sleep(5)  # Wait for Discord to load
            
            print("🔍 Testing message selectors...")
            
            # Test different message selectors
            selectors_to_test = [
                # Original selectors
                '[data-testid="message-username"]',
                '[data-testid="message-content"]', 
                '[data-testid="message-timestamp"]',
                
                # Alternative selectors
                '[class*="message"]',
                '[class*="username"]',
                '[class*="messageContent"]',
                '[class*="markup"]',
                
                # More generic selectors
                '.messageListItem',
                '.message',
                '.username',
                '.messageContent',
                '.markup',
                
                # Aria labels
                '[role="listitem"]',
                '[aria-label*="message"]'
            ]
            
            results = {}
            
            for selector in selectors_to_test:
                try:
                    elements = await page.locator(selector).all()
                    count = len(elements)
                    
                    sample_text = ""
                    if count > 0:
                        try:
                            sample_text = (await elements[0].inner_text())[:100]
                        except:
                            sample_text = "Error getting text"
                    
                    results[selector] = {
                        'count': count,
                        'sample': sample_text
                    }
                    
                    print(f"✅ {selector}: {count} elements")
                    if sample_text:
                        print(f"   📝 Sample: {sample_text}")
                    
                except Exception as e:
                    results[selector] = {'error': str(e)}
                    print(f"❌ {selector}: Error - {e}")
            
            # Try to get the page structure
            print(f"\n🏗️ Page Structure Analysis...")
            
            try:
                # Get all elements that might be messages
                all_elements = await page.locator('*').all()
                print(f"Total elements on page: {len(all_elements)}")
                
                # Look for elements with message-like attributes
                message_candidates = await page.locator('[class*="message"], [data-list-item-id], [id*="message"]').all()
                print(f"Message candidates: {len(message_candidates)}")
                
                if len(message_candidates) > 0:
                    print(f"\n📋 First message candidate structure:")
                    first_candidate = message_candidates[0]
                    try:
                        html = await first_candidate.innerHTML()
                        print(html[:500] + "..." if len(html) > 500 else html)
                    except:
                        print("Could not get innerHTML")
                
            except Exception as e:
                print(f"Structure analysis failed: {e}")
            
            # Save results
            with open('discord_selector_test_results.json', 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"\n💾 Results saved to discord_selector_test_results.json")
            print(f"🎯 Run this manually and check the browser window for Discord content")
            
            # Wait for manual inspection
            print(f"\n⏳ Keeping browser open for 30 seconds for manual inspection...")
            await asyncio.sleep(30)
            
        finally:
            await browser.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_discord_selectors.py <DISCORD_CHANNEL_URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    asyncio.run(test_discord_selectors(url))