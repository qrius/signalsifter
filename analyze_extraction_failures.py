#!/usr/bin/env python3
"""
Discord Message Extraction Failure Analysis
Analyze why 14% of messages return no data during extraction
"""

import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessageFailureAnalyzer:
    def __init__(self):
        self.failure_reasons = {
            'no_message_id': 0,
            'no_timestamp': 0,
            'invalid_timestamp': 0,
            'no_username': 0,
            'no_content': 0,
            'exception_error': 0,
            'success': 0
        }
        self.detailed_failures = []
    
    async def analyze_message_element(self, message_element, index):
        """Analyze a single message element for extraction issues"""
        try:
            # Check message ID
            message_id = await message_element.get_attribute('id')
            if not message_id:
                message_id = await message_element.get_attribute('data-list-item-id')
            
            if not message_id:
                self.failure_reasons['no_message_id'] += 1
                self.detailed_failures.append({
                    'index': index,
                    'reason': 'no_message_id',
                    'element_html': await message_element.innerHTML()[:200]
                })
                return False
            
            # Check timestamp
            timestamp_selectors = [
                'time[datetime]',
                '[datetime]',
                '[data-timestamp]',
                '[class*="timestamp"]',
                'time'
            ]
            
            timestamp_str = None
            for selector in timestamp_selectors:
                try:
                    timestamp_elem = message_element.locator(selector).first
                    if await timestamp_elem.count() > 0:
                        timestamp_str = await timestamp_elem.get_attribute('datetime')
                        if not timestamp_str:
                            timestamp_str = await timestamp_elem.get_attribute('data-timestamp')
                        if timestamp_str:
                            break
                except Exception:
                    continue
            
            if not timestamp_str:
                self.failure_reasons['no_timestamp'] += 1
                self.detailed_failures.append({
                    'index': index,
                    'reason': 'no_timestamp',
                    'message_id': message_id,
                    'element_html': await message_element.innerHTML()[:200]
                })
                return False
            
            # Validate timestamp
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except Exception as e:
                self.failure_reasons['invalid_timestamp'] += 1
                self.detailed_failures.append({
                    'index': index,
                    'reason': 'invalid_timestamp',
                    'message_id': message_id,
                    'timestamp_str': timestamp_str,
                    'error': str(e)
                })
                return False
            
            # Check username
            username_selectors = [
                '[class*="username"]:not([class*="system"])',
                '[class*="author"] [class*="username"]',
                '[class*="header"] [class*="username"]',
                'button[class*="username"]',
                'span[class*="username"]',
                '.username-h_Y3Us',
                '[data-testid="message-username"]',
                '.username',
                'h3 span',
                'button span'
            ]
            
            username = "Unknown"
            for selector in username_selectors:
                try:
                    username_elem = message_element.locator(selector).first
                    if await username_elem.count() > 0:
                        username_text = await username_elem.inner_text()
                        if username_text and username_text.strip() and username_text != "Unknown":
                            username = username_text.strip()
                            break
                except Exception:
                    continue
            
            if username == "Unknown":
                self.failure_reasons['no_username'] += 1
                # Don't fail for missing username, but log it
                logger.debug(f"Message {index}: No username found")
            
            # Check content
            content_selectors = [
                '[class*="messageContent"]',
                '[class*="markup"]',
                '[data-slate-editor="true"]',
                '[data-slate-node="element"]',
                'div[class*="content"]:not([class*="avatar"]):not([class*="header"])',
                'div[id^="message-content-"]',
                '.messageContent-2t3eCI',
                '.markup-eYLPri',
                '[data-testid="message-content"]',
                '.messageContent',
                'div[role="paragraph"]'
            ]
            
            content = ""
            for selector in content_selectors:
                try:
                    content_elem = message_element.locator(selector).first
                    if await content_elem.count() > 0:
                        content_text = await content_elem.inner_text()
                        if content_text and content_text.strip():
                            content = content_text.strip()
                            break
                except Exception:
                    continue
            
            if not content:
                self.failure_reasons['no_content'] += 1
                # Don't fail for missing content, but log it
                logger.debug(f"Message {index}: No content found")
            
            # Success case
            self.failure_reasons['success'] += 1
            return True
            
        except Exception as e:
            self.failure_reasons['exception_error'] += 1
            self.detailed_failures.append({
                'index': index,
                'reason': 'exception_error',
                'error': str(e)
            })
            return False
    
    async def analyze_discord_channel(self, url):
        """Analyze message extraction failures in a Discord channel"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            
            logger.info("Navigating to Discord channel...")
            await page.goto(url)
            await page.wait_for_timeout(5000)
            
            # Find all message elements
            message_selectors = [
                '[id^="chat-messages-"]',
                '[class*="message-"][id]',
                '[data-list-item-id]',
                'li[id][class*="messageListItem"]',
                'div[id][class*="message"]'
            ]
            
            messages = None
            working_selector = None
            
            for selector in message_selectors:
                count = await page.locator(selector).count()
                if count > 0:
                    messages = page.locator(selector)
                    working_selector = selector
                    logger.info(f"Found {count} messages using selector: {selector}")
                    break
            
            if not messages:
                logger.error("No messages found with any selector")
                await browser.close()
                return
            
            # Analyze first 20 messages
            message_count = min(await messages.count(), 20)
            logger.info(f"Analyzing {message_count} messages...")
            
            for i in range(message_count):
                message_elem = messages.nth(i)
                await self.analyze_message_element(message_elem, i + 1)
                
                # Add delay to avoid overwhelming
                await page.wait_for_timeout(100)
            
            await browser.close()
            
            # Report results
            self.print_analysis_report()
    
    def print_analysis_report(self):
        """Print detailed analysis report"""
        total_analyzed = sum(self.failure_reasons.values())
        
        print("\n" + "="*60)
        print("DISCORD MESSAGE EXTRACTION FAILURE ANALYSIS")
        print("="*60)
        
        print(f"Total messages analyzed: {total_analyzed}")
        print("\nFailure Breakdown:")
        
        for reason, count in self.failure_reasons.items():
            percentage = (count / total_analyzed * 100) if total_analyzed > 0 else 0
            status = "✅" if reason == "success" else "❌"
            print(f"  {status} {reason.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")
        
        print(f"\nOverall Success Rate: {self.failure_reasons['success']}/{total_analyzed} ({self.failure_reasons['success']/total_analyzed*100:.1f}%)")
        
        # Show detailed failures
        if self.detailed_failures:
            print("\nDETAILED FAILURE ANALYSIS:")
            print("-" * 40)
            
            for failure in self.detailed_failures[:5]:  # Show first 5 failures
                print(f"Message {failure['index']}: {failure['reason']}")
                if 'message_id' in failure:
                    print(f"  Message ID: {failure['message_id']}")
                if 'error' in failure:
                    print(f"  Error: {failure['error']}")
                if 'element_html' in failure:
                    print(f"  HTML Sample: {failure['element_html'][:100]}...")
                print()
        
        # Recommendations
        print("RECOMMENDATIONS:")
        print("-" * 20)
        
        if self.failure_reasons['no_message_id'] > 0:
            print("• Add more message ID selectors for different Discord layouts")
        
        if self.failure_reasons['no_timestamp'] > 0:
            print("• Expand timestamp detection selectors")
        
        if self.failure_reasons['no_username'] > 0:
            print("• Improve username extraction for different message types")
        
        if self.failure_reasons['no_content'] > 0:
            print("• Add fallback content extraction methods")
        
        if self.failure_reasons['exception_error'] > 0:
            print("• Add better error handling for edge cases")

async def main():
    analyzer = MessageFailureAnalyzer()
    
    # Analyze the test channel
    channel_url = "https://discord.com/channels/1296015181985349715/1296015182417629249"
    
    await analyzer.analyze_discord_channel(channel_url)

if __name__ == "__main__":
    asyncio.run(main())