#!/usr/bin/env python3
"""
Username Selector Diagnostic - Find Working Username Selectors
Focus specifically on username extraction from Discord messages
"""

import asyncio
from playwright.async_api import async_playwright

async def diagnose_username_selectors():
    """Diagnose username selector issues in Discord"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("🔍 Diagnosing username selectors...")
        await page.goto("https://discord.com/channels/1296015181985349715/1296015182417629249")
        await page.wait_for_timeout(5000)
        
        # Find message elements
        message_selector = '[data-list-item-id]'
        messages = page.locator(message_selector)
        message_count = await messages.count()
        
        if message_count == 0:
            print("❌ No messages found")
            await browser.close()
            return
        
        print(f"✅ Found {message_count} messages")
        
        # Test first 3 messages for username patterns
        for i in range(min(3, message_count)):
            print(f"\n📝 Analyzing message {i+1}:")
            message = messages.nth(i)
            
            # Get the message HTML structure
            html = await message.inner_html()
            
            # Test comprehensive username selectors
            username_selectors = [
                # Modern Discord patterns
                'h3 span',
                'button span',
                '[role="button"] span',
                'span[data-text-variant*="semibold"]',
                '[class*="headerText"] span',
                
                # Specific Discord class patterns  
                'span[class*="username"]',
                'span[class*="author"]',
                'button[class*="username"]',
                '[class*="messageHeader"] [class*="username"]',
                
                # Header-based selectors
                'header span',
                'h3 button span',
                'h3 > span',
                'h3 button > span',
                
                # Data attribute selectors
                '[data-username]',
                '[data-author]',
                '[aria-label*="user"]',
                
                # Legacy Discord selectors
                '.username-h_Y3Us',
                '.headerText-2z4IhQ .username-h_Y3Us',
                '.author-1Ml4Lp .username-h_Y3Us',
                
                # Generic fallbacks
                'button[type="button"] span',
                '[role="button"][tabindex="0"] span',
                'span:first-child',
                'div > span:first-child'
            ]
            
            found_username = False
            
            for selector in username_selectors:
                try:
                    elem = message.locator(selector)
                    count = await elem.count()
                    
                    if count > 0:
                        # Test each match to see if it looks like a username
                        for j in range(min(count, 3)):  # Test first 3 matches
                            text = await elem.nth(j).inner_text()
                            text = text.strip()
                            
                            # Check if this looks like a username (not timestamp, not content)
                            if (text and len(text) > 0 and len(text) < 50 and 
                                not text.startswith('http') and
                                ':' not in text and
                                'AM' not in text and 'PM' not in text and
                                not text.isdigit() and
                                text not in ['Today', 'Yesterday', 'BOT', 'APP']):
                                
                                # Get element attributes for context
                                attrs = {}
                                for attr in ['class', 'id', 'data-text-variant', 'role']:
                                    try:
                                        attr_val = await elem.nth(j).get_attribute(attr)
                                        if attr_val:
                                            attrs[attr] = attr_val
                                    except:
                                        pass
                                
                                print(f"  ✅ '{text}' via: {selector}")
                                print(f"     Attributes: {attrs}")
                                found_username = True
                                break
                    
                except Exception as e:
                    pass
            
            if not found_username:
                print(f"  ❌ No username found in message {i+1}")
                # Show message structure for debugging
                print(f"  📋 Message HTML preview:")
                lines = html.split('\n')[:5]
                for line in lines:
                    print(f"     {line.strip()[:80]}...")
        
        # Test additional approaches
        print(f"\n🔍 Testing alternative username detection methods:")
        
        first_message = messages.first
        
        # Method 1: Look for clickable elements that might be usernames
        clickable_spans = first_message.locator('span[role="button"], button span, [tabindex="0"] span')
        clickable_count = await clickable_spans.count()
        print(f"  Clickable spans found: {clickable_count}")
        
        for i in range(min(clickable_count, 3)):
            try:
                text = await clickable_spans.nth(i).inner_text()
                if text and len(text.strip()) > 0:
                    print(f"    '{text.strip()}'")
            except:
                pass
        
        # Method 2: Look for elements with font-weight or text styling
        bold_elements = first_message.locator('span[style*="font-weight"], [data-text-variant*="semibold"], [class*="bold"]')
        bold_count = await bold_elements.count()
        print(f"  Bold/semibold elements found: {bold_count}")
        
        for i in range(min(bold_count, 3)):
            try:
                text = await bold_elements.nth(i).inner_text()
                if text and len(text.strip()) > 0:
                    print(f"    '{text.strip()}'")
            except:
                pass
        
        # Method 3: Look in header/h3 elements specifically
        header_elements = first_message.locator('h3, header, [role="heading"]')
        header_count = await header_elements.count()
        print(f"  Header elements found: {header_count}")
        
        for i in range(min(header_count, 1)):
            try:
                header_html = await header_elements.nth(i).innerHTML()
                header_text = await header_elements.nth(i).inner_text()
                print(f"    Header HTML: {header_html[:100]}...")
                print(f"    Header text: '{header_text.strip()}'")
                
                # Look for spans within headers
                header_spans = header_elements.nth(i).locator('span')
                span_count = await header_spans.count()
                print(f"    Spans in header: {span_count}")
                
                for j in range(min(span_count, 3)):
                    try:
                        span_text = await header_spans.nth(j).inner_text()
                        span_class = await header_spans.nth(j).get_attribute('class')
                        print(f"      Span {j+1}: '{span_text.strip()}' (class: {span_class})")
                    except:
                        pass
                        
            except:
                pass
        
        await browser.close()
        
        print(f"\n💡 RECOMMENDATIONS:")
        print(f"- Focus on h3 > span and button > span patterns")
        print(f"- Look for data-text-variant attributes")
        print(f"- Check for clickable/interactive username elements")
        print(f"- Consider font-weight and text styling indicators")

if __name__ == "__main__":
    asyncio.run(diagnose_username_selectors())