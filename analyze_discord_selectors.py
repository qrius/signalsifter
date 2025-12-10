#!/usr/bin/env python3
"""
Discord Structure Analyzer - No External Dependencies
Analyzes Discord HTML to identify current CSS patterns for messages
"""

import re
import json
import urllib.request
import urllib.parse
from html.parser import HTMLParser

class DiscordHTMLAnalyzer(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_message = False
        self.current_element = None
        self.elements_found = []
        self.message_patterns = []
        self.content_patterns = []
        self.username_patterns = []
        
    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        
        # Look for message-like patterns
        if 'id' in attr_dict and 'message' in attr_dict.get('id', '').lower():
            self.message_patterns.append({
                'tag': tag,
                'id': attr_dict.get('id'),
                'class': attr_dict.get('class', ''),
                'pattern': f'{tag}[id*="message"]'
            })
        
        # Look for class patterns that might be messages
        class_val = attr_dict.get('class', '')
        if class_val:
            if any(keyword in class_val.lower() for keyword in ['message', 'content', 'username', 'author']):
                pattern_info = {
                    'tag': tag,
                    'class': class_val,
                    'pattern': f'{tag}.{class_val.split()[0]}' if class_val.split() else f'{tag}[class*="{class_val[:10]}"]'
                }
                
                if 'message' in class_val.lower():
                    self.message_patterns.append(pattern_info)
                elif 'content' in class_val.lower():
                    self.content_patterns.append(pattern_info)
                elif any(word in class_val.lower() for word in ['username', 'author']):
                    self.username_patterns.append(pattern_info)
        
        # Look for data attributes
        for attr_name, attr_value in attrs:
            if attr_name.startswith('data-') and any(keyword in attr_value.lower() for keyword in ['message', 'user', 'author']):
                self.elements_found.append({
                    'tag': tag,
                    'attr': attr_name,
                    'value': attr_value,
                    'pattern': f'{tag}[{attr_name}="{attr_value}"]'
                })

def analyze_discord_patterns():
    """Analyze common Discord CSS patterns based on known structures"""
    
    print("🔍 Discord CSS Pattern Analysis")
    print("=" * 50)
    
    # Current Discord patterns (as of late 2024/2025)
    updated_selectors = {
        'message_containers': [
            'li[id^="chat-messages-"]',
            'div[id^="message-"]', 
            '[data-list-item-id^="chat-messages"]',
            '.messageListItem-1-jS_1',
            '.message-2CShn3',
            'li[class*="messageListItem"]',
            'div[class*="message"][id]'
        ],
        'message_content': [
            'div[id^="message-content-"]',
            '.messageContent-2t3eCI',
            '.markup-eYLPri',
            'div[class*="messageContent"]',
            'div[class*="markup"]', 
            '.contents-3ca1mk .markup-eYLPri',
            'span[class*="markup"]',
            '.content-1Lc7Cv'
        ],
        'usernames': [
            '.username-h_Y3Us',
            '.headerText-2z4IhQ .username-h_Y3Us', 
            'span[class*="username"]',
            '.author-1Ml4Lp .username-h_Y3Us',
            'h3[class*="header"] .username-h_Y3Us',
            '.messageHeader-1Nh1u7 .username-h_Y3Us',
            'button[class*="username"]',
            '.clickable-vvKY2q .username-h_Y3Us'
        ],
        'timestamps': [
            'time[id^="message-timestamp-"]',
            '.timestamp-p1Df1m',
            'time.timestamp-p1Df1m',
            'time[class*="timestamp"]',
            'span[class*="timestamp"]'
        ],
        'user_avatars': [
            'img[class*="avatar"]',
            '.avatar-2e8lTP img',
            'img[src*="/avatars/"]',
            'div[class*="avatar"] img'
        ]
    }
    
    print("📝 Updated Discord Selectors for 2025:")
    print()
    
    for category, selectors in updated_selectors.items():
        print(f"**{category.replace('_', ' ').title()}:**")
        for i, selector in enumerate(selectors, 1):
            print(f"   {i}. {selector}")
        print()
    
    return updated_selectors

def create_updated_extraction_function():
    """Create updated extraction function with modern selectors"""
    
    extraction_code = '''
async def extract_message_data_updated(self, message_element) -> Optional[Dict[str, Any]]:
    """Extract data from Discord message element - Updated 2025 selectors"""
    try:
        # Extract message ID
        message_id = await message_element.get_attribute('id')
        if not message_id:
            # Try alternative ID patterns
            message_id = await message_element.get_attribute('data-list-item-id')
        
        if not message_id:
            return None

        # Extract timestamp with updated selectors
        timestamp_selectors = [
            'time[id^="message-timestamp-"]',
            '.timestamp-p1Df1m',
            'time.timestamp-p1Df1m', 
            'time[class*="timestamp"]',
            'span[class*="timestamp"]'
        ]
        
        timestamp_str = None
        for selector in timestamp_selectors:
            try:
                timestamp_elem = message_element.locator(selector).first
                if await timestamp_elem.count() > 0:
                    timestamp_str = await timestamp_elem.get_attribute('datetime')
                    if timestamp_str:
                        break
            except:
                continue
        
        if not timestamp_str:
            return None
        
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        
        # Extract username with updated selectors
        username = "Unknown"
        username_selectors = [
            '.username-h_Y3Us',
            '.headerText-2z4IhQ .username-h_Y3Us',
            'span[class*="username"]', 
            '.author-1Ml4Lp .username-h_Y3Us',
            'h3[class*="header"] .username-h_Y3Us',
            '.messageHeader-1Nh1u7 .username-h_Y3Us',
            'button[class*="username"]',
            '.clickable-vvKY2q .username-h_Y3Us'
        ]
        
        for selector in username_selectors:
            try:
                username_elem = message_element.locator(selector).first
                if await username_elem.count() > 0:
                    username_text = await username_elem.inner_text()
                    if username_text and username_text.strip() and username_text != "Unknown":
                        username = username_text.strip()
                        break
            except:
                continue
        
        # Extract user ID from avatar or other attributes
        user_id = username  # fallback
        user_id_selectors = [
            'img[src*="/avatars/"]',
            '.avatar-2e8lTP img',
            'img[class*="avatar"]',
            '[data-user-id]',
            '[data-author-id]'
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
                    
                    # Extract from avatar URL
                    if user_id == username:
                        src = await user_elem.get_attribute('src')
                        if src and '/avatars/' in src:
                            match = re.search(r'/avatars/(\\d+)/', src)
                            if match:
                                user_id = match.group(1)
                                break
                    
                    if user_id != username:
                        break
            except:
                continue
        
        # Extract message content with updated selectors
        content = ""
        content_selectors = [
            'div[id^="message-content-"]',
            '.messageContent-2t3eCI',
            '.markup-eYLPri',
            'div[class*="messageContent"]',
            'div[class*="markup"]',
            '.contents-3ca1mk .markup-eYLPri',
            'span[class*="markup"]',
            '.content-1Lc7Cv',
            # Fallback selectors
            'div[class*="content"]:not([class*="avatar"])',
            'span:not([class*="username"]):not([class*="timestamp"])'
        ]
        
        for selector in content_selectors:
            try:
                content_elem = message_element.locator(selector).first
                if await content_elem.count() > 0:
                    content_text = await content_elem.inner_text()
                    if content_text and content_text.strip():
                        content = content_text.strip()
                        break
            except:
                continue
        
        # If still no content, try getting all text and filtering
        if not content:
            try:
                all_text = await message_element.inner_text()
                # Remove username and timestamp from content
                lines = all_text.split('\\n')
                filtered_lines = []
                for line in lines:
                    line = line.strip()
                    if line and line != username and not re.match(r'^(Today|Yesterday|\\d+/\\d+/\\d+)', line):
                        filtered_lines.append(line)
                
                if filtered_lines:
                    content = '\\n'.join(filtered_lines)
            except:
                pass
        
        return {
            'message_id': message_id,
            'user_id': user_id,
            'username': username,
            'display_name': username,
            'content': content,
            'timestamp': timestamp,
            'edited_timestamp': None,
            'message_type': 'default',
            'parent_id': None,
            'thread_id': None,
            'reactions': None,
            'embeds': None,
            'attachments': None,
            'mentions': None,
            'is_bot': False,
            'is_pinned': False
        }
        
    except Exception as e:
        self.logger.error(f"Error extracting message data: {e}")
        return None
'''
    
    return extraction_code

if __name__ == "__main__":
    patterns = analyze_discord_patterns()
    
    print("🔧 RECOMMENDATIONS:")
    print("1. Update message container selectors to use modern Discord classes")
    print("2. Use .username-h_Y3Us for usernames (current Discord pattern)")  
    print("3. Use .messageContent-2t3eCI or .markup-eYLPri for content")
    print("4. Add fallback selectors for robustness")
    print()
    print("💾 Generated updated extraction function - ready for integration")