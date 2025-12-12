#!/usr/bin/env python3
"""
Discord Browser Extractor for SignalSifter

A comprehensive Discord message extraction system using Playwright browser automation.
Designed to extract historical messages from Discord channels with proper rate limiting,
anti-detection measures, and database storage integration.

Features:
- Browser-based automation with anti-detection measures
- Automatic login with fallback to manual authentication
- Rate limiting and human-like delays
- Comprehensive message data extraction (content, reactions, embeds, etc.)
- SQLite database storage with proper relationships
- Resume functionality for interrupted extractions
- Configurable extraction timeframes (by months or message limits)
- Headless and interactive modes

Usage:
    python discord_browser_extractor.py --url "DISCORD_CHANNEL_URL" --months 6 --verbose
    
Requirements:
- Discord credentials in .env file (DISCORD_EMAIL, DISCORD_PASSWORD)
- Playwright browsers installed
- Python dependencies: playwright, fake-useragent, beautifulsoup4

Author: SignalSifter Project
Date: December 2025
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
        
        # Initialize database - use shared database with Telegram data
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'backfill.sqlite')
        self.db = DiscordDatabase(db_path)
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
    
    async def check_authentication(self, target_url: str) -> bool:
        """Check if we can access the target Discord channel without login redirect"""
        try:
            self.logger.info("Checking Discord authentication...")
            
            # Try to navigate to the target channel URL directly
            await self.page.goto(target_url, wait_until="load", timeout=15000)
            await asyncio.sleep(3)
            
            current_url = self.page.url
            
            # If we're redirected to login, we need to authenticate
            if "discord.com/login" in current_url:
                self.logger.info("Not authenticated - redirected to login")
                return False
            elif "/channels/" in current_url:
                self.logger.info("Successfully authenticated - on channel page")
                return True
            else:
                self.logger.info(f"Unexpected URL after navigation: {current_url}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking authentication: {e}")
            return False

    async def login_to_discord(self, target_url: str) -> bool:
        """Login to Discord with manual assistance if needed"""
        try:
            # Check if already authenticated
            if await self.check_authentication(target_url):
                return True
            
            # Need to login - try automated login first
            self.logger.info("Attempting automated Discord login...")
            
            try:
                await self.page.goto("https://discord.com/login", wait_until="load", timeout=15000)
                await asyncio.sleep(2)
                
                # Get credentials from environment
                email = os.getenv('DISCORD_EMAIL')
                password = os.getenv('DISCORD_PASSWORD')
                
                if email and password:
                    self.logger.info("Found credentials, attempting automated login...")
                    
                    # Fill login form
                    await self.page.fill('input[name="email"]', email)
                    await self.human_delay(0.5, 1)
                    await self.page.fill('input[name="password"]', password)
                    await self.human_delay(1, 2)
                    
                    # Click login button
                    await self.page.click('button[type="submit"]')
                    
                    # Wait for login to complete or require manual intervention
                    try:
                        await self.page.wait_for_url("**/channels/**", timeout=15000)
                        self.logger.info("Successfully logged in to Discord automatically")
                        return True
                    except:
                        self.logger.info("Automated login requires manual intervention...")
                
            except Exception as e:
                self.logger.info(f"Automated login failed, switching to manual mode: {e}")
            
            # Manual login mode
            self.logger.info("=" * 60)
            self.logger.info("MANUAL LOGIN REQUIRED")
            self.logger.info("=" * 60)
            self.logger.info("Please complete Discord login in the browser window:")
            self.logger.info("1. Enter your email/password if not already filled")
            self.logger.info("2. Complete any 2FA/captcha verification")
            self.logger.info("3. Wait for Discord to fully load")
            self.logger.info("4. Press Enter in this terminal when ready...")
            self.logger.info("=" * 60)
            
            # Wait for user confirmation
            input("\nPress Enter after you've logged in to Discord...")
            
            # Verify login was successful
            current_url = self.page.url
            if "/channels/" in current_url or "discord.com/app" in current_url:
                self.logger.info("Manual login successful!")
                return True
            else:
                self.logger.error(f"Still not logged in. Current URL: {current_url}")
                return False
                    
        except Exception as e:
            self.logger.error(f"Login error: {e}")
            return False
    
    async def dismiss_popups_and_ads(self):
        """Dismiss Discord popups, ads, and promotional content"""
        try:
            # Common popup/ad selectors to dismiss
            popup_selectors = [
                # Discord Nitro/theme ads
                'button[aria-label*="Close"]',
                'button[aria-label*="close"]', 
                'div[aria-label*="Close"] button',
                '[data-testid="close-button"]',
                'button:has-text("Not now")',
                'button:has-text("Maybe later")',
                'button:has-text("Skip")',
                'button:has-text("Dismiss")',
                'button:has-text("Got it")',
                '.closeButton',
                '.close-button',
                # Theme/Nitro promotion modals
                'div[class*="modal"] button[class*="close"]',
                'div[class*="Modal"] button[class*="close"]',
                # Generic close buttons in overlays
                'div[role="dialog"] button[aria-label*="close"]',
                'div[class*="overlay"] button',
                # X buttons
                'button:has-text("×")',
                'span:has-text("×") + button',
            ]
            
            dismissed_count = 0
            for selector in popup_selectors:
                try:
                    elements = self.page.locator(selector)
                    count = await elements.count()
                    
                    if count > 0:
                        self.logger.info(f"Found {count} popup(s) with selector: {selector}")
                        
                        for i in range(min(count, 3)):  # Dismiss up to 3 of each type
                            try:
                                element = elements.nth(i)
                                if await element.is_visible():
                                    await element.click()
                                    dismissed_count += 1
                                    await asyncio.sleep(0.5)
                            except:
                                pass
                                
                except Exception:
                    continue
            
            if dismissed_count > 0:
                self.logger.info(f"Dismissed {dismissed_count} popups/ads")
                await asyncio.sleep(2)  # Wait for dismissals to take effect
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Error dismissing popups: {e}")
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
            
            # Dismiss any popups or ads first
            await self.dismiss_popups_and_ads()
            
            # Wait for messages to load
            await self.page.wait_for_selector('[data-list-id="chat-messages"]', timeout=10000)
            
            # Dismiss popups again after page load
            await self.dismiss_popups_and_ads()
            
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
            # Get message ID - Updated for current Discord format
            message_id = await message_element.get_attribute('id')
            if not message_id:
                # Try data-list-item-id as fallback
                message_id = await message_element.get_attribute('data-list-item-id')
            
            if not message_id:
                self.logger.debug("No message ID found")
                # Use a fallback ID if none found
                message_id = f"fallback-{hash(str(await message_element.inner_html()))}"
            
            # Handle different Discord message ID formats
            if message_id.startswith('chat-messages-'):
                message_id = message_id.replace('chat-messages-', '')
            elif message_id.startswith('message-'):
                message_id = message_id.replace('message-', '')
            
            # Log the message ID for debugging
            self.logger.debug(f"Processing message with ID: {message_id}")
            
            # For other formats, use the ID as-is (be more lenient)
            # No longer require specific format - accept any ID
            
            # Extract timestamp with current Discord selectors
            timestamp_str = None
            timestamp_selectors = [
                'time[id*="message-timestamp-"]',  # Direct timestamp ID from DOM
                'time[datetime]',  # Time with datetime attribute
                'span.timestamp_c19a55 time',  # Timestamp class with time
                '[datetime]',  # Any datetime attribute
                'time'  # Fallback time element
            ]
            
            for selector in timestamp_selectors:
                try:
                    timestamp_elem = message_element.locator(selector).first
                    if await timestamp_elem.count() > 0:
                        # Try datetime attribute first
                        timestamp_str = await timestamp_elem.get_attribute('datetime')
                        if not timestamp_str:
                            # Try data-timestamp attribute
                            timestamp_str = await timestamp_elem.get_attribute('data-timestamp')
                        if timestamp_str:
                            self.logger.debug(f"Found timestamp using: {selector}")
                            break
                except Exception:
                    continue
            
            if not timestamp_str:
                self.logger.debug("No timestamp found")
                return None
            
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except Exception as e:
                self.logger.debug(f"Failed to parse timestamp '{timestamp_str}': {e}")
                return None
            
            # Extract user information - DEFINITIVE FIX based on console validation
            username = "Unknown"
            
            # First: Try direct attribute extraction (most reliable)
            try:
                # Look for any span with data-text attribute in the message
                data_text_spans = message_element.locator('span[data-text]')
                count = await data_text_spans.count()
                
                for i in range(count):
                    span = data_text_spans.nth(i)
                    data_text = await span.get_attribute('data-text')
                    
                    # Validate it's a username (not timestamp, etc.)
                    if (data_text and len(data_text) > 1 and len(data_text) < 50 and
                        not data_text.startswith('http') and ':' not in data_text and
                        'AM' not in data_text and 'PM' not in data_text and
                        data_text not in ['[', ']', '—', 'Today', 'Yesterday']):
                        
                        # Double-check this element has username-related classes
                        class_attr = await span.get_attribute('class') or ""
                        if 'username' in class_attr:
                            username = data_text
                            self.logger.info(f"Found username via data-text: '{username}'")
                            break
                            
            except Exception as e:
                self.logger.debug(f"Data-text extraction failed: {e}")
            
            # Fallback: Try proven selectors with timeout
            if username == "Unknown":
                username_selectors = [
                    'span.username_c19a55[data-text]',  # Console shows this works
                    'span[class*="username_c19a55"]',   # Console shows this works
                    '.headerText_c19a55 span.username_c19a55'  # Console shows this works
                ]
            
                for selector in username_selectors:
                    try:
                        username_elem = message_element.locator(selector)
                        elem_count = await username_elem.count()
                        
                        if elem_count > 0:
                            # Get the first match and extract data-text
                            first_elem = username_elem.first
                            username_text = await first_elem.get_attribute('data-text')
                            
                            if username_text and len(username_text) > 1:
                                username = username_text.strip()
                                self.logger.info(f"Found username '{username}' using selector: {selector}")
                                break
                                
                    except Exception as e:
                        self.logger.debug(f"Selector '{selector}' failed: {e}")
                        continue
            
            # Final fallback: Skip header text method since it extracts '[' 
            # Console validation shows our selectors work, so if they fail it's a timing issue
            if username == "Unknown":
                self.logger.debug("Username extraction failed - selectors should work based on console validation")
            
            # Extract user ID with multiple approaches
            user_id = username  # fallback to username
            user_id_selectors = [
                '[data-user-id]',
                '[data-author-id]', 
                '.avatar img[src*="avatars"]',
                '.avatar[style*="background-image"]',
                '[class*="avatar"] img'
            ]
            
            for selector in user_id_selectors:
                try:
                    user_elem = message_element.locator(selector).first
                    if await user_elem.count() > 0:
                        # Try data attributes first
                        for attr in ['data-user-id', 'data-author-id']:
                            attr_value = await user_elem.get_attribute(attr)
                            if attr_value:
                                user_id = attr_value
                                break
                        
                        # Extract from avatar URL if needed
                        if user_id == username:
                            src = await user_elem.get_attribute('src')
                            if src and 'avatars/' in src:
                                # Extract user ID from avatar URL pattern
                                import re
                                match = re.search(r'avatars/(\d+)/', src)
                                if match:
                                    user_id = match.group(1)
                                    break
                        
                        if user_id != username:
                            break
                except Exception:
                    continue
            
            # Extract message content with current Discord selectors (Dec 2025)
            content = ""
            content_selectors = [
                # Primary content selectors (EXACT match from DOM)
                'div[id*="message-content-"]',  # Direct message content ID
                'div.messageContent_c19a55',  # Exact content class from DOM
                'div.markup__75297',  # Exact markup class from DOM
                
                # Secondary patterns
                'div[class*="messageContent"]',  # Any message content class
                'div[class*="markup"]',  # Any markup class  
                'div[id^="message-content"]',  # ID-based content containers
                
                # Fallback patterns
                'div[class*="content"]:not([class*="avatar"]):not([class*="header"])',
                'span[data-slate-string="true"]',  # Slate editor strings
                'div[role="document"]',  # Document role containers
                '[data-testid="message-content"]',  # Test ID content
                
                # Generic fallbacks
                'p',  # Simple paragraph elements
                'span:not([class*="timestamp"]):not([class*="username"])'  # Non-metadata spans
            ]
            
            for selector in content_selectors:
                try:
                    content_elem = message_element.locator(selector).first
                    if await content_elem.count() > 0:
                        content_text = await content_elem.inner_text()
                        if content_text and content_text.strip():
                            content = content_text.strip()
                            self.logger.debug(f"Found content ({len(content)} chars) using: {selector}")
                            break
                except Exception:
                    continue
            
            # If still no content, try enhanced text extraction methods
            if not content:
                try:
                    # Method 1: Get all text and filter intelligently
                    all_text = await message_element.inner_text()
                    if all_text:
                        lines = all_text.split('\n')
                        filtered_lines = []
                        
                        # Skip common metadata patterns
                        skip_patterns = [
                            r'^(Today|Yesterday|\d+/\d+/\d+)',  # Date patterns
                            r'^\d{1,2}:\d{2}\s*(AM|PM)',  # Time patterns
                            r'^(BOT|APP)$',  # Bot indicators
                            r'^(pinned|edited)$'  # Action indicators
                        ]
                        
                        for line in lines:
                            line = line.strip()
                            if line and line != username:
                                # Skip if matches any pattern
                                should_skip = False
                                for pattern in skip_patterns:
                                    if re.match(pattern, line, re.IGNORECASE):
                                        should_skip = True
                                        break
                                
                                if not should_skip and len(line) > 2:  # Minimum content length
                                    filtered_lines.append(line)
                        
                        if filtered_lines:
                            content = '\n'.join(filtered_lines)
                            self.logger.debug(f"Extracted content via enhanced filtering: {len(content)} chars")
                    
                    # Method 2: Try direct text nodes if still no content
                    if not content:
                        text_nodes = await message_element.locator('text()').all_inner_texts()
                        meaningful_text = [t.strip() for t in text_nodes if t.strip() and len(t.strip()) > 2]
                        if meaningful_text:
                            content = ' '.join(meaningful_text)
                            self.logger.debug(f"Extracted content via text nodes: {len(content)} chars")
                            
                except:
                    pass
            
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
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def scroll_to_load_messages(self, target_count: int = None, months_back: int = None) -> int:
        """Scroll up to load older messages with better persistence"""
        messages_loaded = 0
        consecutive_no_new_messages = 0
        max_attempts = 30  # Even more persistent - 30 consecutive failures before giving up
        
        # Calculate cutoff date if months_back is specified
        cutoff_date = None
        if months_back:
            from datetime import timezone, timedelta
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=months_back * 30)
            self.logger.info(f"Loading messages back to: {cutoff_date}")
        
        scroll_attempts = 0
        while scroll_attempts < 50:  # Maximum scroll attempts to prevent infinite loops
            # Dismiss any popups that might appear during scrolling
            if scroll_attempts % 5 == 0:  # Every 5 attempts
                await self.dismiss_popups_and_ads()
            # Get current message count
            # Try multiple message selectors (prioritize li elements from DOM)
            message_selectors = [
                'li[id*="chat-messages-"]',  # EXACT match from DOM
                '[id^="chat-messages-"]',
                'li[class*="messageListItem"]',
                '[data-list-item-id]',
                '[class*="message-"][id]',
                'div[id][class*="message"]'  # Legacy fallback
            ]
            
            current_messages = 0
            for selector in message_selectors:
                count = await self.page.locator(selector).count()
                if count > current_messages:
                    current_messages = count
                    self.current_message_selector = selector  # Store the working selector
            
            if target_count and current_messages >= target_count:
                self.logger.info(f"Reached target message count: {current_messages}")
                break
            
            # Check if we've reached the date cutoff by examining the oldest visible message
            if cutoff_date and current_messages > 10:  # Only check if we have some messages loaded
                try:
                    # Get the first (oldest) message timestamp
                    # Use the working selector we found
                    selector = getattr(self, 'current_message_selector', '[id^="chat-messages-"]')
                    first_message = self.page.locator(selector).first
                    timestamp_elem = first_message.locator('time').first
                    if await timestamp_elem.count() > 0:
                        timestamp_str = await timestamp_elem.get_attribute('datetime')
                        if timestamp_str:
                            message_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            if message_date < cutoff_date:
                                self.logger.info(f"Reached date cutoff: {message_date} < {cutoff_date}")
                                break
                except Exception as e:
                    self.logger.debug(f"Error checking date cutoff: {e}")
            
            # Aggressive scrolling with multiple methods
            scroll_method = scroll_attempts % 4
            
            if scroll_method == 0:
                # Method 1: Home key (most reliable)
                await self.page.keyboard.press('Home')
            elif scroll_method == 1:
                # Method 2: Page Up multiple times - slower, more human-like
                for _ in range(2):  # Reduced from 3 to 2
                    await self.page.keyboard.press('PageUp')
                    await asyncio.sleep(1.5)  # Increased from 0.5 to 1.5 seconds
            elif scroll_method == 2:
                # Method 3: Mouse wheel scrolling - much slower
                for _ in range(3):  # Reduced from 5 to 3
                    await self.page.mouse.wheel(0, -800)  # Smaller scroll amount
                    await asyncio.sleep(1.2)  # Increased from 0.3 to 1.2 seconds
            else:
                # Method 4: Direct message container scrolling
                try:
                    message_container = self.page.locator('[data-list-id="chat-messages"], [class*="scroller"], [class*="content"]').first
                    if await message_container.count() > 0:
                        await message_container.evaluate('element => element.scrollTop = 0')
                except Exception as e:
                    self.logger.debug(f"Container scroll failed: {e}")
                    await self.page.keyboard.press('Home')
            
            # Longer human-like delay after scrolling
            await self.human_delay(2, 4)
            
            # Wait for messages to load - much longer wait for server loading
            # Increase wait time significantly to allow Discord server to fetch older messages
            base_wait = 8  # Start with 8 seconds
            additional_wait = consecutive_no_new_messages * 2  # Add 2s per failed attempt
            wait_time = min(base_wait + additional_wait, 20)  # Cap at 20 seconds
            self.logger.debug(f"Waiting {wait_time}s for messages to load from server...")
            await asyncio.sleep(wait_time)
            
            # Use the working selector we identified
            selector = getattr(self, 'current_message_selector', '[id^="chat-messages-"]')
            new_message_count = await self.page.locator(selector).count()
            
            if new_message_count == current_messages:
                consecutive_no_new_messages += 1
                self.logger.debug(f"No new messages loaded, attempt {consecutive_no_new_messages}/{max_attempts}")
                if consecutive_no_new_messages >= max_attempts:
                    self.logger.info("Reached the beginning of channel history or loading limit")
                    break
            else:
                consecutive_no_new_messages = 0
                messages_loaded = new_message_count
                self.logger.info(f"Loaded {new_message_count} messages (+{new_message_count - current_messages})")
            
            scroll_attempts += 1
            
            # Apply rate limiting
            await self.rate_limit_delay()
        
        self.logger.info(f"Final message count: {messages_loaded}")
        return messages_loaded
    
    async def extract_channel_messages(self, channel_url: str, limit: int = None, 
                                     months_back: int = None, dry_run: bool = False) -> List[Dict[str, Any]]:
        """Extract messages from a Discord channel"""
        try:
            server_id, channel_id = self.parse_discord_url(channel_url)
            if not server_id or not channel_id:
                raise ValueError("Invalid Discord channel URL")
            
            # Navigate to channel
            if not await self.navigate_to_channel(channel_url):
                return []
            
            # Get channel information
            channel_name = await self.get_channel_name()
            server_name = await self.get_server_name()
            
            if not dry_run:
                # Store server and channel info first (required for foreign key)
                self.db.insert_server(server_id, server_name or "Unknown Server")
                self.db.insert_channel(channel_id, server_id, channel_name or "Unknown Channel")
                
                # Now start extraction logging (after channel exists in DB)
                self.extraction_log_id = self.db.log_extraction_start(channel_id, "browser_extraction")
            
            self.logger.info(f"Extracting from #{channel_name} in {server_name}")
            
            # Calculate how many messages to load based on time period
            target_messages = limit
            if months_back and not limit:
                # Estimate messages needed (rough calculation)
                target_messages = months_back * 1000  # Assume ~1000 messages per month
            
            # Load messages by scrolling
            await self.scroll_to_load_messages(target_messages, months_back)
            
            # Extract all visible messages
            messages = []
            # Use the selector that worked during scrolling, or try multiple (prioritize li elements)
            message_elements = []
            message_selectors = [
                'li[id*="chat-messages-"]',  # EXACT match from DOM  
                getattr(self, 'current_message_selector', 'li[id*="chat-messages-"]'),
                '[id^="chat-messages-"]',
                'li[class*="messageListItem"]',
                '[data-list-item-id]',
                '[class*="message-"][id]', 
                'div[id][class*="message"]'  # Legacy fallback
            ]
            
            for selector in message_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    if len(elements) > len(message_elements):
                        message_elements = elements
                        self.logger.info(f"Found {len(elements)} messages using selector: {selector}")
                        break
                except Exception as e:
                    self.logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            self.logger.info(f"Found {len(message_elements)} messages to process")
            
            for i, message_elem in enumerate(message_elements):
                message_data = await self.extract_message_data(message_elem)
                
                if not message_data:
                    self.logger.warning(f"Message {i+1} returned no data")
                    continue
                    
                if message_data:
                    message_data['channel_id'] = channel_id
                    message_data['server_id'] = server_id
                    
                    # Filter by date if months_back is specified
                    if months_back:
                        from datetime import timezone
                        cutoff_date = datetime.now(timezone.utc) - timedelta(days=months_back * 30)
                        # Ensure both dates are comparable
                        msg_timestamp = message_data['timestamp']
                        if hasattr(msg_timestamp, 'tzinfo') and msg_timestamp.tzinfo is None:
                            # If message timestamp is naive, assume UTC
                            msg_timestamp = msg_timestamp.replace(tzinfo=timezone.utc)
                        elif not hasattr(msg_timestamp, 'tzinfo'):
                            # If it's not a datetime, skip date filtering
                            pass
                        else:
                            if msg_timestamp < cutoff_date:
                                continue
                    
                    messages.append(message_data)
                    
                    if not dry_run:
                        # Add channel and server IDs to message data before saving
                        message_data['channel_id'] = channel_id
                        message_data['server_id'] = server_id
                        
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
        try:
            if self.page:
                await self.page.close()
        except Exception as e:
            self.logger.warning(f"Error closing page: {e}")
        
        try:
            if self.browser:
                await self.browser.close()
        except Exception as e:
            self.logger.warning(f"Error closing browser: {e}")

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
        if not await extractor.login_to_discord(args.url):
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