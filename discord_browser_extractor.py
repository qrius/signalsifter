#!/usr/bin/env python3
"""
Discord Browser Extractor for SignalSifter
Playwright-based Discord message extraction with anti-detection and rate limiting
"""

import asyncio
import argparse
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs

from playwright.async_api import async_playwright, Page, Browser
from fake_useragent import UserAgent
import pandas as pd

# Import our Discord database schema
from discord_db_schema import DiscordDatabase

class DiscordBrowserExtractor:
    """Discord message extractor using Playwright browser automation"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.setup_logging()
        
        # Initialize database
        self.db = DiscordDatabase()
        self.db.create_discord_tables()
        
        # Browser settings
        self.browser = None
        self.page = None
        self.context = None
        
        # Extraction settings
        self.rate_limit = self.config.get('rate_limit', 1000)  # messages per hour
        self.scroll_delay_min = self.config.get('scroll_delay_min', 2)  # seconds
        self.scroll_delay_max = self.config.get('scroll_delay_max', 5)  # seconds
        self.max_retries = self.config.get('max_retries', 3)
        
        # Anti-detection settings
        self.user_agent = UserAgent()
        
        # Progress tracking
        self.messages_extracted = 0
        self.extraction_log_id = None
        
    def setup_logging(self):
        """Configure logging for Discord extraction"""
        log_dir = Path("logs/discord")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"discord_extraction_{timestamp}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout) if self.config.get('verbose') else logging.NullHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Discord Browser Extractor initialized")
    
    async def setup_browser(self, headless: bool = False):
        """Initialize Playwright browser with anti-detection measures"""
        self.logger.info("Setting up Playwright browser")
        
        playwright = await async_playwright().start()
        
        # Browser arguments for stealth and compatibility
        browser_args = [
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor"
        ]
        
        # Use persistent context for session management
        user_data_dir = Path.home() / ".SignalSifter" / "discord_browser_profile"
        user_data_dir.mkdir(parents=True, exist_ok=True)
        
        self.browser = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=headless,
            args=browser_args,
            viewport={'width': 1920, 'height': 1080},
            user_agent=self.user_agent.random
        )
        
        # Create new page
        self.page = await self.browser.new_page()
        
        # Inject anti-detection script
        await self.page.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Mock languages and plugins
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        """)
        
        self.logger.info("Browser setup completed")
    
    async def login_to_discord(self) -> bool:
        """Login to Discord using credentials from environment"""
        try:
            # Check if already logged in by looking for Discord app
            await self.page.goto("https://discord.com/app", wait_until="networkidle")
            
            # If we're already in the app, we're logged in
            if "/channels/" in self.page.url or "discord.com/app" in self.page.url:
                self.logger.info("Already logged in to Discord")
                return True
            
            # Need to login
            self.logger.info("Logging in to Discord")
            await self.page.goto("https://discord.com/login", wait_until="networkidle")
            
            # Get credentials from environment
            email = os.getenv('DISCORD_EMAIL')
            password = os.getenv('DISCORD_PASSWORD')
            
            if not email or not password:
                self.logger.error("Discord credentials not found in environment variables")
                self.logger.error("Please set DISCORD_EMAIL and DISCORD_PASSWORD in your .env file")
                return False
            
            # Fill login form
            await self.page.fill('input[name="email"]', email)
            await self.page.fill('input[name="password"]', password)
            
            # Add human-like delay
            await self.human_delay(1, 3)
            
            # Click login button
            await self.page.click('button[type="submit"]')
            
            # Wait for login to complete
            try:
                await self.page.wait_for_url("**/channels/**", timeout=30000)
                self.logger.info("Successfully logged in to Discord")
                return True
            except:
                # Check if we need 2FA or captcha
                if await self.page.locator('input[placeholder*="6-digit"]').count() > 0:
                    self.logger.error("2FA required - not currently supported in automation")
                    return False
                elif await self.page.locator('[data-testid="captcha"]').count() > 0:
                    self.logger.error("CAPTCHA required - manual intervention needed")
                    return False
                else:
                    self.logger.error("Login failed - check credentials")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Login error: {e}")
            return False
    
    async def navigate_to_channel(self, channel_url: str) -> bool:
        """Navigate to a specific Discord channel"""
        try:
            self.logger.info(f"Navigating to channel: {channel_url}")
            
            # Parse channel URL
            if not self.validate_discord_url(channel_url):
                self.logger.error(f"Invalid Discord channel URL: {channel_url}")
                return False
            
            await self.page.goto(channel_url, wait_until="networkidle")
            
            # Wait for messages to load
            await self.page.wait_for_selector('[data-list-id="chat-messages"]', timeout=10000)
            
            # Check if we have access to this channel
            if await self.page.locator('text="You do not have permission"').count() > 0:
                self.logger.error(f"No permission to access channel: {channel_url}")
                return False
            
            self.logger.info("Successfully navigated to channel")
            return True
            
        except Exception as e:
            self.logger.error(f"Navigation error: {e}")
            return False
    
    def validate_discord_url(self, url: str) -> bool:
        """Validate Discord channel URL format"""
        pattern = r'https://discord\.com/channels/(\d+)/(\d+)'
        return bool(re.match(pattern, url))
    
    def parse_discord_url(self, url: str) -> tuple:
        """Parse Discord URL to extract server_id and channel_id"""
        match = re.match(r'https://discord\.com/channels/(\d+)/(\d+)', url)
        if match:
            return match.group(1), match.group(2)
        return None, None
    
    async def human_delay(self, min_seconds: float = None, max_seconds: float = None):
        """Add human-like delay with randomization"""
        min_delay = min_seconds or self.scroll_delay_min
        max_delay = max_seconds or self.scroll_delay_max
        
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
    
    async def rate_limit_delay(self):
        """Calculate and apply rate limiting delay"""
        # Calculate delay based on rate limit (messages per hour)
        delay_per_message = 3600 / self.rate_limit  # seconds per message
        
        # Add some randomization (±25%)
        randomized_delay = delay_per_message * random.uniform(0.75, 1.25)
        
        await asyncio.sleep(randomized_delay)
    
    async def extract_message_data(self, message_element) -> Optional[Dict[str, Any]]:
        """Extract data from a Discord message element"""
        try:
            # Get message ID
            message_id = await message_element.get_attribute('id')
            if not message_id or not message_id.startswith('chat-messages-'):
                return None
            
            message_id = message_id.replace('chat-messages-', '')
            
            # Extract timestamp
            timestamp_elem = message_element.locator('time')
            timestamp_str = await timestamp_elem.get_attribute('datetime') if await timestamp_elem.count() > 0 else None
            
            if not timestamp_str:
                return None
            
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # Extract user information
            username_elem = message_element.locator('[data-testid="message-username"]')
            username = await username_elem.inner_text() if await username_elem.count() > 0 else "Unknown"
            
            # Extract user ID from click handler or avatar
            user_id_elem = message_element.locator('[data-user-id]').first
            user_id = await user_id_elem.get_attribute('data-user-id') if await user_id_elem.count() > 0 else username
            
            # Extract message content
            content_elem = message_element.locator('[data-testid="message-content"]')
            content = await content_elem.inner_text() if await content_elem.count() > 0 else ""
            
            # Extract reactions
            reactions_data = []
            reaction_elements = message_element.locator('[data-testid="message-reaction"]')
            reaction_count = await reaction_elements.count()
            
            for i in range(reaction_count):
                reaction_elem = reaction_elements.nth(i)
                emoji = await reaction_elem.locator('.emoji').get_attribute('alt')
                count_text = await reaction_elem.inner_text()
                count = int(re.search(r'(\d+)', count_text).group(1)) if re.search(r'(\d+)', count_text) else 1
                reactions_data.append({'emoji': emoji, 'count': count})
            
            # Extract embeds information
            embeds_data = []
            embed_elements = message_element.locator('[data-testid="message-embed"]')
            embed_count = await embed_elements.count()
            
            for i in range(embed_count):
                embed_elem = embed_elements.nth(i)
                embed_title = await embed_elem.locator('.embed-title').inner_text() if await embed_elem.locator('.embed-title').count() > 0 else None
                embed_description = await embed_elem.locator('.embed-description').inner_text() if await embed_elem.locator('.embed-description').count() > 0 else None
                embed_url = await embed_elem.locator('a').get_attribute('href') if await embed_elem.locator('a').count() > 0 else None
                
                if embed_title or embed_description or embed_url:
                    embeds_data.append({
                        'title': embed_title,
                        'description': embed_description,
                        'url': embed_url
                    })
            
            # Extract mentions
            mentions_data = []
            mention_elements = message_element.locator('[data-testid="mention"]')
            mention_count = await mention_elements.count()
            
            for i in range(mention_count):
                mention_elem = mention_elements.nth(i)
                mentioned_username = await mention_elem.inner_text()
                mentions_data.append(mentioned_username.replace('@', ''))
            
            # Check for reply/thread information
            reply_elem = message_element.locator('[data-testid="reply-reference"]')
            parent_id = None
            if await reply_elem.count() > 0:
                parent_ref = await reply_elem.get_attribute('data-message-id')
                parent_id = parent_ref
            
            # Check if message is pinned
            is_pinned = await message_element.locator('[data-testid="message-pin-indicator"]').count() > 0
            
            # Check if user is bot
            bot_tag = message_element.locator('[data-testid="bot-tag"]')
            is_bot = await bot_tag.count() > 0
            
            return {
                'message_id': message_id,
                'user_id': user_id,
                'username': username,
                'display_name': username,  # Discord doesn't distinguish display names in this context
                'content': content,
                'timestamp': timestamp,
                'edited_timestamp': None,  # Would need additional detection
                'message_type': 'default',
                'parent_id': parent_id,
                'thread_id': None,  # Would need thread detection
                'reactions': json.dumps(reactions_data) if reactions_data else None,
                'embeds': json.dumps(embeds_data) if embeds_data else None,
                'attachments': None,  # Would need attachment detection
                'mentions': json.dumps(mentions_data) if mentions_data else None,
                'is_bot': is_bot,
                'is_pinned': is_pinned
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting message data: {e}")
            return None
    
    async def scroll_to_load_messages(self, target_count: int = None) -> int:
        """Scroll up to load older messages"""
        messages_loaded = 0
        consecutive_no_new_messages = 0
        
        while True:
            # Get current message count
            current_messages = await self.page.locator('[id^="chat-messages-"]').count()
            
            if target_count and current_messages >= target_count:
                break
            
            # Scroll to top to load older messages
            await self.page.keyboard.press('Home')
            await self.human_delay(2, 4)
            
            # Wait for potential new messages to load
            await asyncio.sleep(2)
            
            new_message_count = await self.page.locator('[id^="chat-messages-"]').count()
            
            if new_message_count == current_messages:
                consecutive_no_new_messages += 1
                if consecutive_no_new_messages >= 3:  # No new messages loaded after 3 tries
                    self.logger.info("Reached the beginning of channel history")
                    break
            else:
                consecutive_no_new_messages = 0
                messages_loaded = new_message_count
                self.logger.info(f"Loaded {new_message_count} messages")
            
            # Apply rate limiting
            await self.rate_limit_delay()
        
        return messages_loaded
    
    async def extract_channel_messages(self, channel_url: str, limit: int = None, 
                                     months_back: int = None, dry_run: bool = False) -> List[Dict[str, Any]]:
        """Extract messages from a Discord channel"""
        try:
            server_id, channel_id = self.parse_discord_url(channel_url)
            if not server_id or not channel_id:
                raise ValueError("Invalid Discord channel URL")
            
            # Start extraction logging
            if not dry_run:
                self.extraction_log_id = self.db.log_extraction_start(channel_id, "browser_extraction")
            
            # Navigate to channel
            if not await self.navigate_to_channel(channel_url):
                return []
            
            # Get channel information
            channel_name = await self.get_channel_name()
            server_name = await self.get_server_name()
            
            if not dry_run:
                # Store server and channel info
                self.db.insert_server(server_id, server_name or "Unknown Server")
                self.db.insert_channel(channel_id, server_id, channel_name or "Unknown Channel")
            
            self.logger.info(f"Extracting from #{channel_name} in {server_name}")
            
            # Calculate how many messages to load based on time period
            target_messages = limit
            if months_back and not limit:
                # Estimate messages needed (rough calculation)
                target_messages = months_back * 1000  # Assume ~1000 messages per month
            
            # Load messages by scrolling
            await self.scroll_to_load_messages(target_messages)
            
            # Extract all visible messages
            messages = []
            message_elements = await self.page.locator('[id^="chat-messages-"]').all()
            
            self.logger.info(f"Found {len(message_elements)} messages to process")
            
            for i, message_elem in enumerate(message_elements):
                message_data = await self.extract_message_data(message_elem)
                
                if message_data:
                    message_data['channel_id'] = channel_id
                    message_data['server_id'] = server_id
                    
                    # Filter by date if months_back is specified
                    if months_back:
                        cutoff_date = datetime.utcnow() - timedelta(days=months_back * 30)
                        if message_data['timestamp'] < cutoff_date:
                            continue
                    
                    messages.append(message_data)
                    
                    if not dry_run:
                        # Store in database
                        self.db.insert_message(message_data)
                        
                        # Update progress
                        if self.extraction_log_id and i % 100 == 0:  # Update every 100 messages
                            self.db.update_extraction_progress(
                                self.extraction_log_id,
                                message_data['message_id'],
                                message_data['timestamp'],
                                len(messages)
                            )
                    
                    # Apply rate limiting
                    await self.rate_limit_delay()
                
                # Progress logging
                if i % 50 == 0:
                    self.logger.info(f"Processed {i+1}/{len(message_elements)} messages")
            
            # Update final status
            if not dry_run and self.extraction_log_id:
                self.db.complete_extraction(self.extraction_log_id, 'completed')
                self.db.update_channel_status(channel_id, server_id, channel_name, len(messages))
            
            self.logger.info(f"Extraction completed: {len(messages)} messages extracted")
            return messages
            
        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            if not dry_run and self.extraction_log_id:
                self.db.complete_extraction(self.extraction_log_id, 'failed', str(e))
            raise
    
    async def get_channel_name(self) -> str:
        """Get the current channel name"""
        try:
            # Look for channel name in header
            name_elem = self.page.locator('[data-testid="channel-name"]')
            if await name_elem.count() > 0:
                return await name_elem.inner_text()
            
            # Alternative selector
            name_elem = self.page.locator('h1[class*="title"]')
            if await name_elem.count() > 0:
                return await name_elem.inner_text()
            
            return "Unknown Channel"
        except:
            return "Unknown Channel"
    
    async def get_server_name(self) -> str:
        """Get the current server name"""
        try:
            # Look for server name in navigation
            name_elem = self.page.locator('[data-testid="guild-name"]')
            if await name_elem.count() > 0:
                return await name_elem.inner_text()
            
            # Alternative selector
            name_elem = self.page.locator('[aria-label*="Server"]')
            if await name_elem.count() > 0:
                return await name_elem.get_attribute('aria-label')
            
            return "Unknown Server"
        except:
            return "Unknown Server"
    
    async def cleanup(self):
        """Clean up browser resources"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()

async def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Discord Browser Extractor for SignalSifter")
    
    parser.add_argument('--url', required=True, help='Discord channel URL')
    parser.add_argument('--limit', type=int, help='Maximum number of messages to extract')
    parser.add_argument('--months', type=int, help='Extract messages from last N months')
    parser.add_argument('--dry-run', action='store_true', help='Extract without saving to database')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--test-limit', type=int, help='Extract limited messages for testing')
    
    args = parser.parse_args()
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Configuration
    config = {
        'verbose': args.verbose,
        'rate_limit': 1000 if not args.test_limit else 50,  # Lower rate for testing
    }
    
    # Initialize extractor
    extractor = DiscordBrowserExtractor(config)
    
    try:
        # Setup browser
        await extractor.setup_browser(headless=args.headless)
        
        # Login to Discord
        if not await extractor.login_to_discord():
            print("Failed to login to Discord. Please check your credentials.")
            return 1
        
        # Extract messages
        limit = args.test_limit or args.limit
        messages = await extractor.extract_channel_messages(
            args.url, 
            limit=limit,
            months_back=args.months,
            dry_run=args.dry_run
        )
        
        print(f"Successfully extracted {len(messages)} messages")
        
        if args.dry_run:
            # Save to file for review
            output_file = f"discord_extraction_dry_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w') as f:
                json.dump(messages, f, indent=2, default=str)
            print(f"Dry run results saved to: {output_file}")
        
        return 0
        
    except Exception as e:
        print(f"Extraction failed: {e}")
        return 1
    
    finally:
        await extractor.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)