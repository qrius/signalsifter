#!/usr/bin/env python3
"""
Discord Health Check System for SignalSifter
Monitors Discord UI changes and automation validation
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from playwright.async_api import async_playwright, Page, Browser, TimeoutError
from discord_db_schema import DiscordDatabase

class DiscordHealthCheck:
    """Discord automation health monitoring and UI change detection"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.setup_logging()
        
        # Database for health status tracking
        self.db = DiscordDatabase()
        
        # Browser settings
        self.browser = None
        self.page = None
        
        # UI selectors to monitor for changes
        self.critical_selectors = {
            'login_email': 'input[name="email"]',
            'login_password': 'input[name="password"]',
            'login_button': 'button[type="submit"]',
            'messages_container': '[data-list-id="chat-messages"]',
            'message_item': '[id^="chat-messages-"]',
            'channel_name': '[data-testid="channel-name"]',
            'message_content': '[data-testid="message-content"]',
            'message_username': '[data-testid="message-username"]',
            'message_timestamp': 'time[datetime]',
            'reaction_button': '[data-testid="message-reaction"]',
            'embed_container': '[data-testid="message-embed"]',
            'mention_element': '[data-testid="mention"]'
        }
        
        # Store previous selector validation results
        self.selector_health_file = Path("logs/discord/selector_health.json")
        self.selector_health_file.parent.mkdir(parents=True, exist_ok=True)
        
    def setup_logging(self):
        """Configure logging for health checks"""
        log_dir = Path("logs/discord")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"health_check_{timestamp}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout) if self.config.get('verbose') else logging.NullHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Discord Health Check initialized")
    
    async def setup_browser(self, headless: bool = True):
        """Initialize browser for health checks"""
        self.logger.info("Setting up browser for health check")
        
        playwright = await async_playwright().start()
        
        # Use same persistent profile as extractor
        user_data_dir = Path.home() / ".SignalSifter" / "discord_browser_profile"
        user_data_dir.mkdir(parents=True, exist_ok=True)
        
        self.browser = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=headless,
            viewport={'width': 1920, 'height': 1080}
        )
        
        self.page = await self.browser.new_page()
        self.logger.info("Browser setup completed")
    
    async def check_login_page(self) -> Dict[str, Any]:
        """Check if Discord login page selectors are working"""
        self.logger.info("Checking Discord login page")
        
        result = {
            'status': 'success',
            'timestamp': datetime.utcnow().isoformat(),
            'selectors': {},
            'errors': []
        }
        
        try:
            await self.page.goto("https://discord.com/login", timeout=10000)
            await self.page.wait_for_load_state("networkidle")
            
            # Check critical login selectors
            login_selectors = {
                'email_field': self.critical_selectors['login_email'],
                'password_field': self.critical_selectors['login_password'],
                'login_button': self.critical_selectors['login_button']
            }
            
            for name, selector in login_selectors.items():
                try:
                    element = await self.page.wait_for_selector(selector, timeout=5000)
                    if element:
                        result['selectors'][name] = 'found'
                    else:
                        result['selectors'][name] = 'not_found'
                        result['errors'].append(f"Selector not found: {name} ({selector})")
                except TimeoutError:
                    result['selectors'][name] = 'timeout'
                    result['errors'].append(f"Timeout waiting for: {name} ({selector})")
            
            self.logger.info("Login page check completed")
            return result
            
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(f"Login page check failed: {str(e)}")
            self.logger.error(f"Login page check error: {e}")
            return result
    
    async def check_channel_page(self, channel_url: str = None) -> Dict[str, Any]:
        """Check if Discord channel page selectors are working"""
        if not channel_url:
            channel_url = "https://discord.com/channels/1296015181985349715/1296015182417629249"
        
        self.logger.info(f"Checking Discord channel page: {channel_url}")
        
        result = {
            'status': 'success',
            'timestamp': datetime.utcnow().isoformat(),
            'channel_url': channel_url,
            'selectors': {},
            'errors': []
        }
        
        try:
            await self.page.goto(channel_url, timeout=15000)
            await self.page.wait_for_load_state("networkidle")
            
            # Wait a bit for dynamic content
            await asyncio.sleep(3)
            
            # Check critical channel selectors
            channel_selectors = {
                'messages_container': self.critical_selectors['messages_container'],
                'message_items': self.critical_selectors['message_item'],
                'channel_name': self.critical_selectors['channel_name']
            }
            
            for name, selector in channel_selectors.items():
                try:
                    if name == 'message_items':
                        # Check if we can find at least one message
                        elements = await self.page.locator(selector).count()
                        if elements > 0:
                            result['selectors'][name] = f'found_{elements}_messages'
                        else:
                            result['selectors'][name] = 'no_messages_found'
                            result['errors'].append(f"No messages found with selector: {selector}")
                    else:
                        element = await self.page.wait_for_selector(selector, timeout=5000)
                        if element:
                            result['selectors'][name] = 'found'
                        else:
                            result['selectors'][name] = 'not_found'
                            result['errors'].append(f"Selector not found: {name} ({selector})")
                            
                except TimeoutError:
                    result['selectors'][name] = 'timeout'
                    result['errors'].append(f"Timeout waiting for: {name} ({selector})")
            
            # Check message content selectors if messages exist
            if result['selectors'].get('message_items', '').startswith('found_'):
                await self.check_message_selectors(result)
            
            self.logger.info("Channel page check completed")
            return result
            
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(f"Channel page check failed: {str(e)}")
            self.logger.error(f"Channel page check error: {e}")
            return result
    
    async def check_message_selectors(self, result: Dict[str, Any]):
        """Check message-level selectors on the first few messages"""
        self.logger.info("Checking message-level selectors")
        
        try:
            # Get first few messages
            message_elements = await self.page.locator(self.critical_selectors['message_item']).all()
            
            if not message_elements:
                result['errors'].append("No message elements found for detailed check")
                return
            
            # Check selectors on first message
            first_message = message_elements[0]
            
            message_selectors = {
                'message_content': self.critical_selectors['message_content'],
                'message_username': self.critical_selectors['message_username'],
                'message_timestamp': self.critical_selectors['message_timestamp']
            }
            
            for name, selector in message_selectors.items():
                try:
                    element_count = await first_message.locator(selector).count()
                    if element_count > 0:
                        result['selectors'][name] = 'found'
                    else:
                        result['selectors'][name] = 'not_found'
                        result['errors'].append(f"Message selector not found: {name} ({selector})")
                        
                except Exception as e:
                    result['selectors'][name] = 'error'
                    result['errors'].append(f"Error checking message selector {name}: {str(e)}")
            
        except Exception as e:
            result['errors'].append(f"Message selector check failed: {str(e)}")
    
    async def check_extraction_functionality(self) -> Dict[str, Any]:
        """Test basic extraction functionality"""
        self.logger.info("Testing extraction functionality")
        
        result = {
            'status': 'success',
            'timestamp': datetime.utcnow().isoformat(),
            'tests': {},
            'errors': []
        }
        
        try:
            # Test message ID extraction
            message_elements = await self.page.locator('[id^="chat-messages-"]').all()
            if message_elements:
                first_message = message_elements[0]
                message_id = await first_message.get_attribute('id')
                
                if message_id and message_id.startswith('chat-messages-'):
                    result['tests']['message_id_extraction'] = 'success'
                    extracted_id = message_id.replace('chat-messages-', '')
                    result['tests']['sample_message_id'] = extracted_id
                else:
                    result['tests']['message_id_extraction'] = 'failed'
                    result['errors'].append("Message ID format unexpected")
            else:
                result['tests']['message_id_extraction'] = 'no_messages'
                result['errors'].append("No messages available for ID extraction test")
            
            # Test content extraction
            content_elements = await self.page.locator('[data-testid="message-content"]').all()
            if content_elements:
                sample_content = await content_elements[0].inner_text()
                if sample_content:
                    result['tests']['content_extraction'] = 'success'
                    result['tests']['sample_content_length'] = len(sample_content)
                else:
                    result['tests']['content_extraction'] = 'empty'
            else:
                result['tests']['content_extraction'] = 'no_elements'
                result['errors'].append("No message content elements found")
            
            # Test timestamp extraction
            timestamp_elements = await self.page.locator('time[datetime]').all()
            if timestamp_elements:
                sample_datetime = await timestamp_elements[0].get_attribute('datetime')
                if sample_datetime:
                    result['tests']['timestamp_extraction'] = 'success'
                    result['tests']['sample_timestamp'] = sample_datetime
                else:
                    result['tests']['timestamp_extraction'] = 'no_datetime'
                    result['errors'].append("Timestamp element missing datetime attribute")
            else:
                result['tests']['timestamp_extraction'] = 'no_elements'
                result['errors'].append("No timestamp elements found")
            
            self.logger.info("Extraction functionality test completed")
            return result
            
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(f"Extraction functionality test failed: {str(e)}")
            self.logger.error(f"Extraction test error: {e}")
            return result
    
    def save_health_results(self, results: Dict[str, Any]):
        """Save health check results to file"""
        try:
            with open(self.selector_health_file, 'w') as f:
                json.dump(results, f, indent=2)
            self.logger.info(f"Health results saved to {self.selector_health_file}")
        except Exception as e:
            self.logger.error(f"Failed to save health results: {e}")
    
    def load_previous_results(self) -> Optional[Dict[str, Any]]:
        """Load previous health check results"""
        try:
            if self.selector_health_file.exists():
                with open(self.selector_health_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load previous results: {e}")
        return None
    
    def compare_results(self, current: Dict[str, Any], previous: Dict[str, Any]) -> Dict[str, Any]:
        """Compare current results with previous to detect changes"""
        comparison = {
            'timestamp': datetime.utcnow().isoformat(),
            'changes_detected': False,
            'new_issues': [],
            'resolved_issues': [],
            'status_changes': {}
        }
        
        if not previous:
            comparison['changes_detected'] = True
            comparison['new_issues'].append("No previous results to compare with")
            return comparison
        
        # Compare selector status
        for check_type in ['login_check', 'channel_check', 'extraction_test']:
            if check_type in current and check_type in previous:
                current_selectors = current[check_type].get('selectors', {})
                previous_selectors = previous[check_type].get('selectors', {})
                
                for selector_name in set(current_selectors.keys()) | set(previous_selectors.keys()):
                    current_status = current_selectors.get(selector_name, 'missing')
                    previous_status = previous_selectors.get(selector_name, 'missing')
                    
                    if current_status != previous_status:
                        comparison['changes_detected'] = True
                        comparison['status_changes'][f"{check_type}.{selector_name}"] = {
                            'from': previous_status,
                            'to': current_status
                        }
                        
                        if current_status in ['not_found', 'timeout', 'error'] and previous_status == 'found':
                            comparison['new_issues'].append(f"{check_type}: {selector_name} stopped working")
                        elif current_status == 'found' and previous_status in ['not_found', 'timeout', 'error']:
                            comparison['resolved_issues'].append(f"{check_type}: {selector_name} now working")
        
        return comparison
    
    async def run_full_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check"""
        self.logger.info("Starting full Discord health check")
        
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'unknown',
            'login_check': {},
            'channel_check': {},
            'extraction_test': {},
            'comparison': {}
        }
        
        try:
            await self.setup_browser(headless=True)
            
            # Run all checks
            results['login_check'] = await self.check_login_page()
            results['channel_check'] = await self.check_channel_page()
            results['extraction_test'] = await self.check_extraction_functionality()
            
            # Determine overall status
            all_errors = (
                results['login_check'].get('errors', []) +
                results['channel_check'].get('errors', []) +
                results['extraction_test'].get('errors', [])
            )
            
            if not all_errors:
                results['overall_status'] = 'healthy'
            elif len(all_errors) <= 2:  # Minor issues
                results['overall_status'] = 'degraded'
            else:
                results['overall_status'] = 'unhealthy'
            
            # Compare with previous results
            previous_results = self.load_previous_results()
            results['comparison'] = self.compare_results(results, previous_results)
            
            # Save current results
            self.save_health_results(results)
            
            self.logger.info(f"Health check completed. Status: {results['overall_status']}")
            return results
            
        except Exception as e:
            results['overall_status'] = 'error'
            results['error'] = str(e)
            self.logger.error(f"Health check failed: {e}")
            return results
        
        finally:
            await self.cleanup()
    
    async def run_quick_check(self) -> bool:
        """Run quick health check for monitoring scripts"""
        try:
            await self.setup_browser(headless=True)
            
            # Just check if we can access Discord and find messages
            await self.page.goto("https://discord.com/channels/1296015181985349715/1296015182417629249", timeout=15000)
            await self.page.wait_for_selector('[data-list-id="chat-messages"]', timeout=10000)
            
            message_count = await self.page.locator('[id^="chat-messages-"]').count()
            
            if message_count > 0:
                self.logger.info(f"Quick check passed: found {message_count} messages")
                return True
            else:
                self.logger.error("Quick check failed: no messages found")
                return False
                
        except Exception as e:
            self.logger.error(f"Quick check failed: {e}")
            return False
        
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up browser resources"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()

async def main():
    """Main CLI interface for health checks"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Discord Health Check System")
    parser.add_argument('--quick-check', action='store_true', help='Run quick health check')
    parser.add_argument('--full-check', action='store_true', help='Run comprehensive health check')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--channel-url', help='Specific channel URL to test')
    
    args = parser.parse_args()
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    config = {
        'verbose': args.verbose
    }
    
    health_checker = DiscordHealthCheck(config)
    
    try:
        if args.quick_check:
            success = await health_checker.run_quick_check()
            print("✅ Quick health check passed" if success else "❌ Quick health check failed")
            return 0 if success else 1
            
        elif args.full_check or not any([args.quick_check]):
            results = await health_checker.run_full_health_check()
            
            # Print summary
            print(f"\n=== Discord Health Check Results ===")
            print(f"Overall Status: {results['overall_status'].upper()}")
            print(f"Timestamp: {results['timestamp']}")
            
            # Print issues
            all_errors = (
                results.get('login_check', {}).get('errors', []) +
                results.get('channel_check', {}).get('errors', []) +
                results.get('extraction_test', {}).get('errors', [])
            )
            
            if all_errors:
                print(f"\nIssues found ({len(all_errors)}):")
                for error in all_errors:
                    print(f"  ❌ {error}")
            else:
                print("\n✅ No issues detected")
            
            # Print changes
            comparison = results.get('comparison', {})
            if comparison.get('changes_detected'):
                if comparison.get('new_issues'):
                    print(f"\nNew Issues:")
                    for issue in comparison['new_issues']:
                        print(f"  🚨 {issue}")
                
                if comparison.get('resolved_issues'):
                    print(f"\nResolved Issues:")
                    for issue in comparison['resolved_issues']:
                        print(f"  ✅ {issue}")
            
            return 0 if results['overall_status'] in ['healthy', 'degraded'] else 1
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)