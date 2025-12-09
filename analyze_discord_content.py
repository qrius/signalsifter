#!/usr/bin/env python3
"""
Discord Message Content Analysis
"""
import sqlite3
import json
from datetime import datetime
from collections import Counter, defaultdict
import re

def analyze_discord_content():
    try:
        conn = sqlite3.connect('discord_data.db')
        cursor = conn.cursor()
        
        # Get all messages with content
        cursor.execute('''
            SELECT message_id, username, content, timestamp, edited_timestamp, mentions, reactions
            FROM discord_messages 
            WHERE content IS NOT NULL AND content != ""
            ORDER BY timestamp ASC
        ''')
        
        messages = cursor.fetchall()
        
        if not messages:
            print("❌ No messages with content found")
            return
            
        print(f"📊 DISCORD CONTENT ANALYSIS")
        print(f"=" * 50)
        print(f"Total messages with content: {len(messages)}")
        
        # Analyze by user
        user_stats = Counter()
        user_messages = defaultdict(list)
        
        # Content patterns
        mentions = []
        reactions_count = 0
        edited_count = 0
        word_count = 0
        
        # Time analysis
        daily_activity = defaultdict(int)
        hourly_activity = defaultdict(int)
        
        for msg_id, username, content, timestamp, edited_ts, mentions_data, reactions_data in messages:
            user_stats[username] += 1
            user_messages[username].append(content)
            
            # Parse timestamp
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            daily_activity[dt.strftime('%Y-%m-%d')] += 1
            hourly_activity[dt.hour] += 1
            
            # Content analysis
            if content:
                words = len(content.split())
                word_count += words
                
                # Find mentions
                if '@' in content:
                    user_mentions = re.findall(r'@(\w+)', content)
                    mentions.extend(user_mentions)
            
            if edited_ts:
                edited_count += 1
            
            if reactions_data and reactions_data != 'null':
                reactions_count += 1
        
        # User activity analysis
        print(f"\n👥 USER ACTIVITY:")
        for username, count in user_stats.most_common(10):
            avg_words = sum(len(msg.split()) for msg in user_messages[username]) / len(user_messages[username])
            print(f"  {username}: {count} messages (avg {avg_words:.1f} words)")
        
        # Content statistics
        print(f"\n📝 CONTENT STATISTICS:")
        print(f"  Total words: {word_count:,}")
        print(f"  Average words per message: {word_count/len(messages):.1f}")
        print(f"  Messages edited: {edited_count}")
        print(f"  Messages with reactions: {reactions_count}")
        
        # Most mentioned users
        if mentions:
            mention_counts = Counter(mentions)
            print(f"\n🔥 MOST MENTIONED USERS:")
            for user, count in mention_counts.most_common(5):
                print(f"  @{user}: {count} mentions")
        
        # Daily activity pattern
        print(f"\n📅 DAILY ACTIVITY (Last 10 days):")
        sorted_days = sorted(daily_activity.items(), key=lambda x: x[0])[-10:]
        for date, count in sorted_days:
            print(f"  {date}: {count} messages")
        
        # Hourly activity pattern
        print(f"\n🕐 HOURLY ACTIVITY PATTERN:")
        peak_hours = sorted(hourly_activity.items(), key=lambda x: x[1], reverse=True)[:5]
        for hour, count in peak_hours:
            time_str = f"{hour:02d}:00"
            print(f"  {time_str}: {count} messages")
        
        # Sample interesting messages
        print(f"\n💬 SAMPLE MESSAGES:")
        
        # Longest messages
        cursor.execute('''
            SELECT username, content, timestamp 
            FROM discord_messages 
            WHERE content IS NOT NULL AND LENGTH(content) > 100
            ORDER BY LENGTH(content) DESC 
            LIMIT 3
        ''')
        long_messages = cursor.fetchall()
        
        if long_messages:
            print(f"\n📝 Longest messages:")
            for username, content, timestamp in long_messages:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                preview = content[:100] + "..." if len(content) > 100 else content
                print(f"  {dt.strftime('%m-%d %H:%M')} {username}: {preview}")
        
        # Recent messages
        cursor.execute('''
            SELECT username, content, timestamp 
            FROM discord_messages 
            WHERE content IS NOT NULL
            ORDER BY timestamp DESC 
            LIMIT 5
        ''')
        recent = cursor.fetchall()
        
        print(f"\n🔥 Most recent messages:")
        for username, content, timestamp in recent:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            preview = content[:80] + "..." if len(content) > 80 else content
            print(f"  {dt.strftime('%m-%d %H:%M')} {username}: {preview}")
        
        # Keywords/topics analysis
        all_content = " ".join([msg[2] for msg in messages if msg[2]])
        words = re.findall(r'\b[a-zA-Z]{4,}\b', all_content.lower())
        common_words = Counter(words).most_common(10)
        
        print(f"\n🏷️  COMMON TOPICS/KEYWORDS:")
        for word, count in common_words:
            if word not in ['that', 'this', 'with', 'they', 'have', 'will', 'from', 'been', 'were']:
                print(f"  {word}: {count} times")
        
        conn.close()
        print(f"\n✅ Analysis complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    analyze_discord_content()