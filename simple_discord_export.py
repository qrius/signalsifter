#!/usr/bin/env python3
"""
Simple Discord Export Script (No External Dependencies)
Uses only built-in Python modules to export Discord data for NotebookLM
"""

import sqlite3
import json
import re
import os
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
import sys

# Configuration
DB_PATH = "data/backfill.sqlite"
EXPORT_DIR = Path("data/notebooklm_export")

def load_discord_data():
    """Load Discord data from the unified database using raw sqlite3"""
    print("📊 Loading Discord data from database...")
    
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    
    try:
        cursor = conn.cursor()
        
        # Load messages with diagnostics
        cursor.execute("""
        SELECT 
            message_id,
            channel_id,
            user_id,
            username,
            content,
            timestamp,
            edited_timestamp,
            message_type,
            attachments,
            embeds,
            mentions,
            reactions,
            length(content) as content_length
        FROM discord_messages 
        ORDER BY timestamp
        """)
        
        messages = [dict(row) for row in cursor.fetchall()]
        
        # Diagnostic information
        total_messages = len(messages)
        messages_with_content = len([m for m in messages if m['content_length'] > 0])
        unknown_usernames = len([m for m in messages if m['username'] == 'Unknown'])
        
        print(f"✅ Loaded {total_messages} messages")
        print(f"📝 Messages with content: {messages_with_content}/{total_messages}")
        print(f"👤 Messages with 'Unknown' username: {unknown_usernames}/{total_messages}")
        
        if messages_with_content == 0:
            print("⚠️  WARNING: No messages have content! This indicates extraction issues.")
            print("   The export will contain message metadata but no actual message text.")
        
        if unknown_usernames == total_messages:
            print("⚠️  WARNING: All usernames are 'Unknown'! This indicates selector issues.")
        
        # Load users
        cursor.execute("""
        SELECT DISTINCT 
            user_id,
            username,
            COUNT(*) as message_count
        FROM discord_messages 
        GROUP BY user_id, username
        ORDER BY message_count DESC
        """)
        
        users = [dict(row) for row in cursor.fetchall()]
        print(f"✅ Loaded {len(users)} unique users")
        
        # Load channels
        cursor.execute("""
        SELECT DISTINCT 
            channel_id,
            COUNT(*) as message_count,
            MIN(timestamp) as first_message,
            MAX(timestamp) as last_message
        FROM discord_messages 
        GROUP BY channel_id
        """)
        
        channels = [dict(row) for row in cursor.fetchall()]
        print(f"✅ Loaded {len(channels)} channels")
        
        return messages, users, channels
        
    finally:
        conn.close()

def format_message_for_export(message):
    """Format a single message for NotebookLM"""
    try:
        timestamp_str = datetime.fromisoformat(message['timestamp'].replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        timestamp_str = str(message['timestamp'])
    
    # Handle missing content
    content = message['content'] if message['content'] and message['content'].strip() else "[No content captured]"
    username = message['username'] if message['username'] and message['username'] != 'Unknown' else f"User_{message['user_id'][-8:] if message['user_id'] else 'unknown'}"
    
    # Basic message
    formatted = f"**{username}** ({timestamp_str})\n{content}"
    
    # Add edited indicator
    if message.get('edited_timestamp'):
        try:
            edited_time = datetime.fromisoformat(message['edited_timestamp'].replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M:%S UTC")
            formatted += f"\n*[Edited: {edited_time}]*"
        except:
            formatted += f"\n*[Edited]*"
    
    # Add attachments info
    if message.get('attachments') and message['attachments'] != '[]':
        try:
            attachments = json.loads(message['attachments'])
            if attachments:
                formatted += f"\n*[Attachments: {len(attachments)} file(s)]*"
        except:
            pass
    
    # Add reactions info
    if message.get('reactions') and message['reactions'] != '[]':
        try:
            reactions = json.loads(message['reactions'])
            if reactions:
                reaction_summary = []
                for reaction in reactions:
                    if 'emoji' in reaction and 'count' in reaction:
                        reaction_summary.append(f"{reaction['emoji']} {reaction['count']}")
                if reaction_summary:
                    formatted += f"\n*[Reactions: {', '.join(reaction_summary)}]*"
        except:
            pass
    
    return formatted + "\n\n"

def create_export_documents(messages, users, channels):
    """Create structured documents for NotebookLM"""
    print("📚 Creating structured documents...")
    
    # Ensure export directory exists
    EXPORT_DIR.mkdir(exist_ok=True)
    
    total_messages = len(messages)
    date_range = f"{messages[0]['timestamp']} to {messages[-1]['timestamp']}" if messages else "No messages"
    
    # Document 1: Complete Conversation Archive
    print("   📄 Creating complete conversation archive...")
    complete_archive = []
    complete_archive.append("# Discord Community Conversation Archive\n")
    complete_archive.append("Complete chronological record of all Discord messages\n\n")
    
    # Add metadata header
    complete_archive.append(f"**Dataset Overview:**\n")
    complete_archive.append(f"- Total Messages: {total_messages:,}\n")
    complete_archive.append(f"- Date Range: {date_range}\n")
    complete_archive.append(f"- Active Users: {len(users)}\n")
    complete_archive.append(f"- Channels: {len(channels)}\n\n")
    complete_archive.append("---\n\n")
    
    # Add all messages chronologically
    for message in messages:
        complete_archive.append(format_message_for_export(message))
    
    # Document 2: User Activity Analysis
    print("   👥 Creating user activity analysis...")
    user_analysis = []
    user_analysis.append("# Discord Community User Activity Analysis\n\n")
    
    # Top users by message count
    top_users = sorted(users, key=lambda x: x['message_count'], reverse=True)[:20]
    user_analysis.append("## Most Active Users\n\n")
    for user in top_users:
        percentage = (user['message_count'] / total_messages) * 100 if total_messages > 0 else 0
        user_analysis.append(f"**{user['username']}**: {user['message_count']:,} messages ({percentage:.1f}%)\n")
    
    # Messages by hour analysis
    user_analysis.append("\n## User Engagement Patterns\n\n")
    
    hourly_activity = defaultdict(int)
    for message in messages:
        try:
            hour = datetime.fromisoformat(message['timestamp'].replace('Z', '+00:00')).hour
            hourly_activity[hour] += 1
        except:
            continue
    
    user_analysis.append("### Activity by Hour of Day\n\n")
    for hour in range(24):
        count = hourly_activity.get(hour, 0)
        percentage = (count / total_messages) * 100 if total_messages > 0 else 0
        if count > 0:
            user_analysis.append(f"**{hour:02d}:00-{hour:02d}:59**: {count:,} messages ({percentage:.1f}%)\n")
    
    # Document 3: Community Insights Summary
    print("   📊 Creating community insights summary...")
    insights = []
    insights.append("# Discord Community Insights & Analytics Summary\n\n")
    
    insights.append("## Key Community Statistics\n\n")
    insights.append(f"- **Total Messages**: {total_messages:,}\n")
    insights.append(f"- **Active Community Members**: {len(users)}\n")
    insights.append(f"- **Discussion Channels**: {len(channels)}\n")
    insights.append(f"- **Time Period**: {date_range}\n")
    avg_per_user = total_messages / len(users) if len(users) > 0 else 0
    insights.append(f"- **Average Messages per User**: {avg_per_user:.1f}\n\n")
    
    # Data quality analysis
    messages_with_content = len([m for m in messages if m.get('content') and m['content'].strip()])
    content_quality = (messages_with_content / total_messages) * 100 if total_messages > 0 else 0
    
    insights.append("## Data Quality Assessment\n\n")
    insights.append(f"- **Messages with Content**: {messages_with_content:,} ({content_quality:.1f}%)\n")
    
    if content_quality < 50:
        insights.append(f"- **⚠️ Data Quality Issue**: Low content capture rate suggests Discord extraction problems\n")
        insights.append(f"- **Recommendation**: Re-run Discord extraction with updated selectors\n")
    elif content_quality < 90:
        insights.append(f"- **⚠️ Partial Data**: Some message content may be missing\n")
    else:
        insights.append(f"- **✅ Good Data Quality**: Most messages have content\n")
    
    insights.append("\n")
    
    # Activity patterns
    insights.append("## Community Activity Patterns\n\n")
    
    # Peak activity hours
    if hourly_activity:
        peak_hour = max(hourly_activity.keys(), key=lambda x: hourly_activity[x])
        peak_count = hourly_activity[peak_hour]
        insights.append(f"- **Peak Activity**: {peak_hour:02d}:00-{peak_hour:02d}:59 ({peak_count:,} messages)\n")
    
    # Most active user
    if users:
        top_user = max(users, key=lambda x: x['message_count'])
        insights.append(f"- **Most Active Member**: {top_user['username']} ({top_user['message_count']:,} messages)\n")
    
    # Content characteristics
    total_chars = sum(len(m.get('content', '')) for m in messages)
    avg_length = total_chars / total_messages if total_messages > 0 else 0
    insights.append(f"- **Average Message Length**: {avg_length:.1f} characters\n\n")
    
    # Export all documents
    documents = {
        'complete_archive.txt': ''.join(complete_archive),
        'user_activity_analysis.txt': ''.join(user_analysis),
        'community_insights.txt': ''.join(insights)
    }
    
    return documents

def export_files(documents, messages, users, channels):
    """Export all documents to files"""
    print("💾 Exporting documents to files...")
    
    exported_files = []
    
    # Export main documents
    for filename, content in documents.items():
        filepath = EXPORT_DIR / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        size_kb = len(content.encode('utf-8')) / 1024
        exported_files.append({
            'filename': filename,
            'filepath': filepath,
            'size_kb': size_kb
        })
        print(f"   ✅ {filename}: {size_kb:.1f}KB")
    
    # Export metadata as JSON
    metadata = {
        'export_info': {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'exporter': 'Simple Discord Export Script (No Dependencies)',
            'version': '2.0'
        },
        'data_summary': {
            'message_count': len(messages),
            'user_count': len(users),
            'channel_count': len(channels),
            'date_range': f"{messages[0]['timestamp']} to {messages[-1]['timestamp']}" if messages else "No messages",
            'oldest_message': str(messages[0]['timestamp']) if messages else None,
            'newest_message': str(messages[-1]['timestamp']) if messages else None
        },
        'files_exported': [f['filename'] for f in exported_files]
    }
    
    metadata_path = EXPORT_DIR / 'export_metadata.json'
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    metadata_size = len(json.dumps(metadata, indent=2).encode('utf-8')) / 1024
    exported_files.append({
        'filename': 'export_metadata.json',
        'filepath': metadata_path,
        'size_kb': metadata_size
    })
    print(f"   ✅ export_metadata.json: {metadata_size:.1f}KB")
    
    # Create README
    messages_with_content = len([m for m in messages if m.get('content') and m['content'].strip()])
    content_quality = (messages_with_content / len(messages)) * 100 if messages else 0
    
    readme_content = f"""# Discord Community Data - NotebookLM Import Guide

## Overview
This export contains Discord community conversations and analysis prepared for NotebookLM AI analysis.

**Data Summary:**
- Messages: {len(messages):,}
- Users: {len(users)}
- Channels: {len(channels)}
- Date Range: {messages[0]['timestamp'] if messages else 'N/A'} to {messages[-1]['timestamp'] if messages else 'N/A'}
- Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

**Data Quality:**
- Messages with Content: {messages_with_content:,} ({content_quality:.1f}%)
{'- ⚠️ Low content quality detected - extraction issues likely' if content_quality < 50 else '- ✅ Good data quality' if content_quality > 90 else '- ⚠️ Partial content captured'}

## Next Steps

1. **If content quality is low (<50%)**: Fix Discord extraction selectors and re-run
2. **If content quality is good (>90%)**: Upload files to NotebookLM for analysis
3. **For partial content**: You can still analyze temporal patterns and metadata

## NotebookLM Import Order

1. Start with `community_insights.txt` for overview
2. Import `complete_archive.txt` for full conversation history
3. Use `user_activity_analysis.txt` for engagement patterns

## Troubleshooting

The Discord extraction captured message timestamps and structure but failed to extract:
- Message content (showing as "[No content captured]")  
- Usernames (showing as "Unknown")

This indicates the CSS selectors in the extraction script need updating for current Discord interface.
"""
    
    readme_path = EXPORT_DIR / 'README.md'
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    readme_size = len(readme_content.encode('utf-8')) / 1024
    exported_files.append({
        'filename': 'README.md',
        'filepath': readme_path,
        'size_kb': readme_size
    })
    print(f"   ✅ README.md: {readme_size:.1f}KB")
    
    return exported_files

def main():
    """Main export pipeline"""
    print("🚀 SIMPLE DISCORD TO NOTEBOOKLM EXPORT")
    print("=" * 50)
    
    try:
        # Load data
        messages, users, channels = load_discord_data()
        
        if not messages:
            print("❌ No messages found in database")
            return False
        
        # Create documents
        documents = create_export_documents(messages, users, channels)
        
        # Export files
        exported_files = export_files(documents, messages, users, channels)
        
        # Summary
        total_size_mb = sum(f['size_kb'] for f in exported_files) / 1024
        print(f"\n🎉 EXPORT COMPLETED SUCCESSFULLY!")
        print(f"📂 Location: {EXPORT_DIR.absolute()}")
        print(f"📊 Files: {len(exported_files)}")
        print(f"📏 Total Size: {total_size_mb:.1f}MB")
        
        # Analysis of what we have
        messages_with_content = len([m for m in messages if m.get('content') and m['content'].strip()])
        content_quality = (messages_with_content / len(messages)) * 100
        
        if content_quality < 50:
            print(f"\n⚠️  DATA QUALITY ISSUE:")
            print(f"   Only {content_quality:.1f}% of messages have content")
            print(f"   This indicates Discord extraction selector problems")
            print(f"   The export contains timestamps and metadata but no message text")
        
        print(f"\n🎯 Next Steps:")
        print(f"   1. Navigate to: {EXPORT_DIR.absolute()}")
        print(f"   2. Review README.md for detailed analysis")
        if content_quality > 50:
            print(f"   3. Upload files to NotebookLM for AI analysis")
        else:
            print(f"   3. Fix Discord extraction and re-run for full content")
        
        return True
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)