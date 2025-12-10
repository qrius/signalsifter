#!/usr/bin/env python3
"""
Discord DOM Inspector - Find Current Working Selectors
Inspect actual Discord DOM to find working selectors for 2025 interface
"""

import asyncio
from playwright.async_api import async_playwright
import json

async def inspect_discord_dom():
    """Inspect current Discord DOM structure to find working selectors"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("🔍 Inspecting Discord DOM structure...")
        await page.goto("https://discord.com/channels/1296015181985349715/1296015182417629249")
        await page.wait_for_timeout(5000)
        
        # Find message elements first
        message_selectors = [
            '[id^="chat-messages-"]',
            '[class*="message-"][id]', 
            '[data-list-item-id]',
            'li[id][class*="messageListItem"]'
        ]
        
        working_message_selector = None
        message_count = 0
        
        for selector in message_selectors:
            count = await page.locator(selector).count()
            if count > 0:
                working_message_selector = selector
                message_count = count
                print(f"✅ Found {count} messages with: {selector}")
                break
        
        if not working_message_selector:
            print("❌ No message elements found")
            await browser.close()
            return
        
        # Inspect first message in detail
        first_message = page.locator(working_message_selector).first
        
        print(f"\n📝 Analyzing first message structure...")
        
        # Get the HTML structure
        html = await first_message.inner_html()
        
        # Test various selectors on the first message
        selectors_to_test = {
            "username": [
                "h3 span",
                "button span", 
                "[role='button'] span",
                "span[class*='username']",
                "span[class*='author']",
                "[data-text-variant='text-md/semibold']",
                "[class*='headerText'] span",
                ".username",
                "button[class*='button'] span"
            ],
            "content": [
                "div[id^='message-content']",
                "div[class*='messageContent']", 
                "div[class*='markup']",
                "[data-slate-editor]",
                "div[class*='content'] div",
                "div[role='document']",
                "span[data-slate-string='true']"
            ],
            "timestamp": [
                "time",
                "[datetime]",
                "time[id^='message-timestamp']",
                "span[class*='timestamp']",
                "time[data-timestamp]"
            ]
        }
        
        working_selectors = {}
        
        for category, selector_list in selectors_to_test.items():
            print(f"\n🔍 Testing {category} selectors:")
            working_selectors[category] = []
            
            for selector in selector_list:
                try:
                    elem = first_message.locator(selector)
                    count = await elem.count()
                    
                    if count > 0:
                        text = await elem.first.inner_text()
                        attrs = {}
                        
                        # Get useful attributes
                        for attr in ['class', 'id', 'data-text-variant', 'datetime', 'data-timestamp']:
                            try:
                                attr_val = await elem.first.get_attribute(attr)
                                if attr_val:
                                    attrs[attr] = attr_val
                            except:
                                pass
                        
                        print(f"  ✅ {selector}")
                        print(f"     Count: {count}")
                        print(f"     Text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
                        print(f"     Attrs: {attrs}")
                        
                        working_selectors[category].append({
                            'selector': selector,
                            'count': count,
                            'text': text[:100],
                            'attributes': attrs
                        })
                    else:
                        print(f"  ❌ {selector} (no matches)")
                        
                except Exception as e:
                    print(f"  ❌ {selector} (error: {e})")
        
        # Test on multiple messages for consistency
        print(f"\n🔄 Testing selectors on multiple messages...")
        consistency_test = {}
        
        test_count = min(5, message_count)
        for i in range(test_count):
            msg_elem = page.locator(working_message_selector).nth(i)
            
            for category, results in working_selectors.items():
                if category not in consistency_test:
                    consistency_test[category] = {}
                
                for result in results[:3]:  # Test top 3 working selectors
                    selector = result['selector']
                    if selector not in consistency_test[category]:
                        consistency_test[category][selector] = {'success': 0, 'total': 0}
                    
                    consistency_test[category][selector]['total'] += 1
                    
                    try:
                        elem = msg_elem.locator(selector)
                        if await elem.count() > 0:
                            text = await elem.first.inner_text()
                            if text and text.strip():
                                consistency_test[category][selector]['success'] += 1
                    except:
                        pass
        
        # Print consistency results
        print(f"\n📊 SELECTOR CONSISTENCY RESULTS (tested on {test_count} messages):")
        print("=" * 60)
        
        best_selectors = {}
        
        for category, selectors in consistency_test.items():
            print(f"\n{category.upper()} SELECTORS:")
            best_rate = 0
            best_selector = None
            
            for selector, stats in selectors.items():
                rate = stats['success'] / stats['total'] * 100 if stats['total'] > 0 else 0
                print(f"  {selector}: {stats['success']}/{stats['total']} ({rate:.1f}%)")
                
                if rate > best_rate:
                    best_rate = rate
                    best_selector = selector
            
            if best_selector and best_rate > 0:
                best_selectors[category] = {'selector': best_selector, 'rate': best_rate}
                print(f"  🏆 BEST: {best_selector} ({best_rate:.1f}%)")
        
        # Generate updated selector code
        print(f"\n🔧 RECOMMENDED SELECTOR UPDATES:")
        print("=" * 50)
        
        if 'username' in best_selectors:
            print(f"USERNAME_SELECTORS = [")
            print(f"    '{best_selectors['username']['selector']}',")
            for result in working_selectors.get('username', [])[:5]:
                if result['selector'] != best_selectors['username']['selector']:
                    print(f"    '{result['selector']}',")
            print(f"]")
        
        if 'content' in best_selectors:
            print(f"\nCONTENT_SELECTORS = [")
            print(f"    '{best_selectors['content']['selector']}',")
            for result in working_selectors.get('content', [])[:5]:
                if result['selector'] != best_selectors['content']['selector']:
                    print(f"    '{result['selector']}',")
            print(f"]")
        
        if 'timestamp' in best_selectors:
            print(f"\nTIMESTAMP_SELECTORS = [")
            print(f"    '{best_selectors['timestamp']['selector']}',")
            for result in working_selectors.get('timestamp', [])[:5]:
                if result['selector'] != best_selectors['timestamp']['selector']:
                    print(f"    '{result['selector']}',")
            print(f"]")
        
        # Save results to file
        results = {
            'analysis_timestamp': '2025-12-09',
            'message_selector': working_message_selector,
            'message_count': message_count,
            'working_selectors': working_selectors,
            'consistency_test': consistency_test,
            'best_selectors': best_selectors
        }
        
        with open('discord_dom_analysis.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📄 Results saved to: discord_dom_analysis.json")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_discord_dom())