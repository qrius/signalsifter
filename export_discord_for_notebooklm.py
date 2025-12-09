#!/usr/bin/env python3
"""
Standalone Discord to NotebookLM Export Script
Exports Discord data from the unified database for NotebookLM analysis
"""

import sqlite3
import pandas as pd
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
import sys
import os

# Configuration
DB_PATH = "data/backfill.sqlite"
EXPORT_DIR = Path("data/notebooklm_export")

def load_discord_data():
    """Load Discord data from the unified database"""
    print("📊 Loading Discord data from database...")
    
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Load messages with diagnostics
        messages_query = """
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
        """
        messages_df = pd.read_sql_query(messages_query, conn)
        
        # Diagnostic information
        total_messages = len(messages_df)
        messages_with_content = len(messages_df[messages_df['content_length'] > 0])
        unknown_usernames = len(messages_df[messages_df['username'] == 'Unknown'])
        
        print(f"✅ Loaded {total_messages} messages")
        print(f"📝 Messages with content: {messages_with_content}/{total_messages}")
        print(f"👤 Messages with 'Unknown' username: {unknown_usernames}/{total_messages}")
        
        if messages_with_content == 0:
            print("⚠️  WARNING: No messages have content! This indicates extraction issues.")
            print("   The export will contain message metadata but no actual message text.")
        
        if unknown_usernames == total_messages:
            print("⚠️  WARNING: All usernames are 'Unknown'! This indicates selector issues.")
        
        # Load users
        users_query = """
        SELECT DISTINCT 
            user_id,
            username,
            COUNT(*) as message_count
        FROM discord_messages 
        GROUP BY user_id, username
        ORDER BY message_count DESC
        """
        users_df = pd.read_sql_query(users_query, conn)
        print(f"✅ Loaded {len(users_df)} unique users")
        
        # Load channels
        channels_query = """
        SELECT DISTINCT 
            channel_id,
            COUNT(*) as message_count,
            MIN(timestamp) as first_message,
            MAX(timestamp) as last_message
        FROM discord_messages 
        GROUP BY channel_id
        """
        channels_df = pd.read_sql_query(channels_query, conn)
        print(f"✅ Loaded {len(channels_df)} channels")
        
        return messages_df, users_df, channels_df
        
    finally:
        conn.close()

def format_message_for_export(row):
    """Format a single message for NotebookLM"""
    timestamp = pd.to_datetime(row['timestamp']).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Handle missing content
    content = row['content'] if pd.notna(row['content']) and row['content'].strip() else "[No content captured]"
    username = row['username'] if pd.notna(row['username']) and row['username'] != 'Unknown' else f"User_{row['user_id'][-8:]}"
    
    # Basic message
    formatted = f"**{username}** ({timestamp})\n{content}"
    
    # Add edited indicator
    if pd.notna(row['edited_timestamp']):
        edited_time = pd.to_datetime(row['edited_timestamp']).strftime("%Y-%m-%d %H:%M:%S UTC")
        formatted += f"\n*[Edited: {edited_time}]*"
    
    # Add attachments info
    if pd.notna(row['attachments']) and row['attachments'] != '[]':
        try:
            attachments = json.loads(row['attachments'])
            if attachments:
                formatted += f"\n*[Attachments: {len(attachments)} file(s)]*"
        except:
            pass
    
    # Add reactions info
    if pd.notna(row['reactions']) and row['reactions'] != '[]':
        try:
            reactions = json.loads(row['reactions'])
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

def create_export_documents(messages_df, users_df, channels_df):
    """Create structured documents for NotebookLM"""
    print("📚 Creating structured documents...")
    
    # Ensure export directory exists
    EXPORT_DIR.mkdir(exist_ok=True)
    
    # Document 1: Complete Conversation Archive
    print("   📄 Creating complete conversation archive...")
    complete_archive = []
    complete_archive.append("# Discord Community Conversation Archive\n")
    complete_archive.append("Complete chronological record of all Discord messages\n\n")
    
    # Add metadata header
    total_messages = len(messages_df)
    date_range = f"{messages_df['timestamp'].min()} to {messages_df['timestamp'].max()}"
    complete_archive.append(f"**Dataset Overview:**\n")
    complete_archive.append(f"- Total Messages: {total_messages:,}\n")
    complete_archive.append(f"- Date Range: {date_range}\n")
    complete_archive.append(f"- Active Users: {len(users_df)}\n")
    complete_archive.append(f"- Channels: {len(channels_df)}\n\n")
    complete_archive.append("---\n\n")
    
    # Add all messages chronologically
    for _, message in messages_df.iterrows():
        complete_archive.append(format_message_for_export(message))
    
    # Document 2: User Activity Analysis
    print("   👥 Creating user activity analysis...")
    user_analysis = []
    user_analysis.append("# Discord Community User Activity Analysis\n\n")
    
    # Top users by message count
    top_users = users_df.head(20)
    user_analysis.append("## Most Active Users\n\n")
    for _, user in top_users.iterrows():
        percentage = (user['message_count'] / total_messages) * 100
        user_analysis.append(f"**{user['username']}**: {user['message_count']:,} messages ({percentage:.1f}%)\n")
    
    # User engagement patterns
    user_analysis.append("\n## User Engagement Patterns\n\n")
    
    # Messages by hour analysis
    messages_df['hour'] = pd.to_datetime(messages_df['timestamp']).dt.hour
    hourly_activity = messages_df.groupby('hour').size()
    
    user_analysis.append("### Activity by Hour of Day\n\n")
    for hour, count in hourly_activity.items():
        percentage = (count / total_messages) * 100
        user_analysis.append(f"**{hour:02d}:00-{hour:02d}:59**: {count:,} messages ({percentage:.1f}%)\n")
    
    # Document 3: Conversation Topics & Themes
    print("   💭 Creating conversation topics analysis...")
    topics_analysis = []
    topics_analysis.append("# Discord Community Topics & Conversation Themes\n\n")
    
    # Content analysis
    all_content = ' '.join(messages_df['content'].fillna('').astype(str))
    
    # Word frequency (basic analysis)
    words = re.findall(r'\b[a-zA-Z]{3,}\b', all_content.lower())
    word_freq = pd.Series(words).value_counts().head(50)
    
    topics_analysis.append("## Most Frequently Used Words\n\n")
    for word, count in word_freq.items():
        if word not in ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use']:
            topics_analysis.append(f"**{word}**: {count:,} occurrences\n")
    
    # Sample conversations for context
    topics_analysis.append("\n## Sample Conversations\n\n")
    
    # Get conversations with multiple participants
    recent_messages = messages_df.tail(50)  # Last 50 messages as sample
    topics_analysis.append("### Recent Community Discussions\n\n")
    
    for _, message in recent_messages.iterrows():
        topics_analysis.append(format_message_for_export(message))
    
    # Document 4: Community Insights Summary
    print("   📊 Creating community insights summary...")
    insights = []
    insights.append("# Discord Community Insights & Analytics Summary\n\n")
    
    insights.append("## Key Community Statistics\n\n")
    insights.append(f"- **Total Messages**: {total_messages:,}\n")
    insights.append(f"- **Active Community Members**: {len(users_df)}\n")
    insights.append(f"- **Discussion Channels**: {len(channels_df)}\n")
    insights.append(f"- **Time Period**: {date_range}\n")
    insights.append(f"- **Average Messages per User**: {total_messages / len(users_df):.1f}\n\n")
    
    # Data quality analysis
    messages_with_content = len(messages_df[messages_df['content'].notna() & (messages_df['content'] != '')])
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
    peak_hour = hourly_activity.idxmax()
    peak_count = hourly_activity.max()
    insights.append(f"- **Peak Activity**: {peak_hour:02d}:00-{peak_hour:02d}:59 ({peak_count:,} messages)\n")
    
    # Most active user
    top_user = users_df.iloc[0]
    insights.append(f"- **Most Active Member**: {top_user['username']} ({top_user['message_count']:,} messages)\n")
    
    # Content characteristics
    avg_length = messages_df['content'].str.len().mean()
    insights.append(f"- **Average Message Length**: {avg_length:.1f} characters\n\n")
    
    # Export all documents
    documents = {
        'complete_archive.txt': ''.join(complete_archive),
        'user_activity_analysis.txt': ''.join(user_analysis),
        'conversation_topics.txt': ''.join(topics_analysis),
        'community_insights.txt': ''.join(insights)
    }
    
    return documents

def export_files(documents, messages_df, users_df, channels_df):
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
            'exporter': 'Discord NotebookLM Export Script',
            'version': '1.0'
        },
        'data_summary': {
            'message_count': len(messages_df),
            'user_count': len(users_df),
            'channel_count': len(channels_df),
            'date_range': f"{messages_df['timestamp'].min()} to {messages_df['timestamp'].max()}",
            'oldest_message': str(messages_df['timestamp'].min()),
            'newest_message': str(messages_df['timestamp'].max())
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
    
    # Data quality assessment
    messages_with_content = len(messages_df[messages_df['content'].notna() & (messages_df['content'] != '')])
    content_quality = (messages_with_content / len(messages_df)) * 100 if len(messages_df) > 0 else 0
    
    # Create README for NotebookLM import
    readme_content = f"""# Discord Community Data - NotebookLM Import Guide

## Overview
This export contains Discord community conversations and analysis prepared for NotebookLM AI analysis.

**Data Summary:**
- Messages: {len(messages_df):,}
- Users: {len(users_df)}
- Channels: {len(channels_df)}
- Date Range: {messages_df['timestamp'].min()} to {messages_df['timestamp'].max()}
- Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

**Data Quality:**
- Messages with Content: {messages_with_content:,} ({content_quality:.1f}%)
{'- ⚠️ Low content quality detected - see troubleshooting section below' if content_quality < 50 else '- ✅ Good data quality' if content_quality > 90 else '- ⚠️ Partial content captured'}

## Files Included

### 1. complete_archive.txt
Complete chronological record of all Discord messages. Use this for:
- Understanding conversation flow and context
- Analyzing community discussions over time
- Finding specific conversations or topics

### 2. user_activity_analysis.txt
Analysis of user engagement patterns including:
- Most active community members
- Activity patterns by time of day
- User engagement statistics

### 3. conversation_topics.txt
Thematic analysis of community discussions:
- Frequently discussed topics
- Word frequency analysis
- Sample conversations for context

### 4. community_insights.txt
High-level analytics and insights about the community:
- Key statistics and metrics
- Activity patterns and trends
- Community characteristics

### 5. export_metadata.json
Technical metadata about the export process and data structure.

## NotebookLM Import Instructions

1. **Upload Order**: Start with `community_insights.txt` for overview
2. **Primary Analysis**: Use `complete_archive.txt` for detailed conversation analysis
3. **Focused Studies**: Import specific analysis files based on your research questions
4. **Context**: Reference `export_metadata.json` for technical details

## AI Analysis Suggestions

Ask NotebookLM to:
- Identify key themes and topics in community discussions
- Analyze communication patterns and community dynamics  
- Summarize main conversation threads and decisions
- Extract insights about community interests and engagement
- Compare activity patterns across different time periods

## Technical Notes

- All timestamps are in UTC
- Messages preserve original formatting and context
- Reactions and attachments are noted where present
- User privacy: Only public Discord content is included

## Troubleshooting

### Low Content Quality ({content_quality:.1f}% messages with content)

If you see mostly "[No content captured]" messages, this indicates issues with the Discord extraction:

**Common Causes:**
1. **Outdated CSS Selectors**: Discord frequently changes their HTML structure
2. **Authentication Issues**: Extraction may have run on login page instead of channel
3. **Rate Limiting**: Discord may have blocked the extraction bot

**Solutions:**
1. **Update Selectors**: Run `python test_discord_selectors.py <DISCORD_URL>` to test current selectors
2. **Re-run Extraction**: Use `python discord_browser_extractor.py --url <DISCORD_URL> --verbose`
3. **Manual Verification**: Check that the Discord channel is publicly accessible

**Current Status:**
- Message metadata was captured successfully (timestamps, IDs)
- Message content extraction failed - likely due to selector issues
- Usernames show as "Unknown" - indicates username selector problems

**Next Steps:**
1. Test updated Discord selectors with the diagnostic tool
2. Re-run extraction with corrected selectors  
3. Re-export for NotebookLM analysis with full content
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
    print("🚀 DISCORD TO NOTEBOOKLM EXPORT")
    print("=" * 50)
    
    try:
        # Load data
        messages_df, users_df, channels_df = load_discord_data()
        
        # Create documents
        documents = create_export_documents(messages_df, users_df, channels_df)
        
        # Export files
        exported_files = export_files(documents, messages_df, users_df, channels_df)
        
        # Summary
        total_size_mb = sum(f['size_kb'] for f in exported_files) / 1024
        print(f"\n🎉 EXPORT COMPLETED SUCCESSFULLY!")
        print(f"📂 Location: {EXPORT_DIR.absolute()}")
        print(f"📊 Files: {len(exported_files)}")
        print(f"📏 Total Size: {total_size_mb:.1f}MB")
        
        print(f"\n🎯 Next Steps:")
        print(f"   1. Navigate to: {EXPORT_DIR.absolute()}")
        print(f"   2. Review README.md for import guidance")
        print(f"   3. Upload files to NotebookLM")
        print(f"   4. Start with community_insights.txt for overview")
        
        return True
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)