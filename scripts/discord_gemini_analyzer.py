#!/usr/bin/env python3
"""
Discord Gemini Analyzer - extends the base GeminiAnalyzer for Discord message analysis.
Provides NotebookLM-like analysis capabilities for Discord channels.

Usage:
  python scripts/discord_gemini_analyzer.py --guild-id 1296015181985349715 --channel-id 1356175241172488314
  python scripts/discord_gemini_analyzer.py --messages-file data/discord_messages.txt --out data/analysis/
  
Environment variables (in `.env`):
  GEMINI_API_KEY      # Google AI Studio API key
  SQLITE_DB_PATH     # SQLite database path
  
Features:
  - Discord-specific message formatting
  - Handles embeds, mentions, and reactions
  - Guild and channel context awareness
  - Integration with existing Gemini analysis framework
"""

import os
import sys
import json
import sqlite3
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add scripts directory to path for GeminiAnalyzer import
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(script_dir)

from dotenv import load_dotenv
from gemini_analyzer import GeminiAnalyzer, load_messages_from_file

load_dotenv()

DB_PATH = os.getenv("SQLITE_DB_PATH", "./data/backfill.sqlite")

class DiscordGeminiAnalyzer(GeminiAnalyzer):
    """Extended GeminiAnalyzer for Discord-specific message processing"""
    
    def format_discord_messages(self, messages: List[Dict], include_embeds: bool = True, 
                               include_reactions: bool = False) -> str:
        """
        Format Discord messages for Gemini analysis
        
        Args:
            messages: List of Discord message dictionaries
            include_embeds: Whether to include embed content
            include_reactions: Whether to include reaction data
            
        Returns:
            Formatted message text ready for analysis
        """
        formatted_lines = []
        
        for msg in messages:
            timestamp = msg.get('created_at', '').replace('T', ' ').replace('+00:00', ' UTC')
            author = msg.get('author_display_name') or msg.get('author_username', 'Unknown')
            content = msg.get('content', '')
            
            # Handle mentions in content
            content = self._process_discord_mentions(content)
            
            # Basic message format
            if content.strip():
                formatted_lines.append(f"[{timestamp}] @{author}: {content}")
            
            # Add embed content if requested and present
            if include_embeds and msg.get('embed_data'):
                try:
                    embeds = json.loads(msg['embed_data'])
                    for embed in embeds:
                        embed_content = self._format_embed_content(embed)
                        if embed_content:
                            formatted_lines.append(f"[{timestamp}] @{author} [EMBED]: {embed_content}")
                except Exception as e:
                    print(f"Error processing embed for message {msg.get('message_id')}: {e}")
            
            # Add reaction summary if requested
            if include_reactions and msg.get('reaction_count', 0) > 0:
                formatted_lines.append(f"[{timestamp}] @{author} [REACTIONS]: {msg.get('reaction_count')} reactions")
        
        return '\n'.join(formatted_lines)
    
    def _process_discord_mentions(self, content: str) -> str:
        """Process Discord mentions to make them human-readable"""
        if not content:
            return content
        
        # Convert user mentions (<@123456>) to @username format (simplified)
        import re
        content = re.sub(r'<@!?(\d+)>', r'@user_\1', content)
        content = re.sub(r'<#(\d+)>', r'#channel_\1', content)
        content = re.sub(r'<@&(\d+)>', r'@role_\1', content)
        
        return content
    
    def _format_embed_content(self, embed: Dict) -> str:
        """Format embed content into readable text"""
        parts = []
        
        if embed.get('title'):
            parts.append(f"Title: {embed['title']}")
        
        if embed.get('description'):
            parts.append(f"Description: {embed['description']}")
        
        if embed.get('url'):
            parts.append(f"URL: {embed['url']}")
        
        # Format fields
        if embed.get('fields'):
            for field in embed['fields']:
                name = field.get('name', '')
                value = field.get('value', '')
                if name and value:
                    parts.append(f"{name}: {value}")
        
        return ' | '.join(parts)
    
    def _build_discord_analysis_prompt(self, messages_text: str, analysis_type: str, 
                                     guild_name: str = None, channel_name: str = None) -> str:
        """Build Discord-specific analysis prompt"""
        
        base_context = f"""You are analyzing Discord messages from a server channel. The messages are formatted as:
[timestamp] @username: message content
[timestamp] @username [EMBED]: embedded content
[timestamp] @username [REACTIONS]: reaction information

Context:
- Platform: Discord
- Server: {guild_name or 'Unknown Guild'}
- Channel: #{channel_name or 'unknown-channel'}
- Message Format: Discord chat with mentions, embeds, and reactions

Focus Areas for Discord Analysis:
1. Community engagement patterns and member interactions
2. Server roles and hierarchy from mentions and message patterns  
3. Embedded content analysis (links, images, bot posts)
4. Topic trends and discussion themes
5. Member activity and contribution patterns
6. Bot interactions and automated content
7. Cross-channel references and server-wide conversations"""
        
        if analysis_type == "comprehensive":
            return f"""{base_context}

Provide a comprehensive Discord server analysis including:

**Community Analysis:**
- Member engagement patterns and activity levels
- Key contributors and community leaders
- Discussion topics and trends
- Server culture and communication style

**Content Analysis:**
- Main themes and topics of conversation
- Embedded content patterns (links, media, bots)
- Information sharing and resource distribution
- Technical discussions vs casual chat

**Engagement Metrics:**
- Message frequency and timing patterns
- Member interaction networks
- Popular discussion threads
- Community growth indicators

**Citations:** Reference specific messages using [timestamp] format for all insights.

Messages to analyze:
{messages_text}"""
        
        elif analysis_type == "summary":
            return f"""{base_context}

Provide a concise summary of the Discord channel activity including:
- Main discussion topics
- Key community members and their contributions  
- Important announcements or updates
- Notable embedded content or resources shared

Keep the summary focused and include [timestamp] citations.

Messages to analyze:
{messages_text}"""
        
        elif analysis_type == "entities":
            return f"""{base_context}

Extract and categorize key entities from the Discord messages:
- People: Active members, mentioned users, roles
- Projects: Mentioned projects, tools, platforms
- Resources: Shared links, documents, media
- Events: Planned activities, announcements, milestones
- Technical: Code, APIs, blockchain addresses, contracts

Include [timestamp] citations for each entity.

Messages to analyze:
{messages_text}"""
        
        return f"{base_context}\n\nAnalyze these Discord messages:\n{messages_text}"
    
    def analyze_discord_channel(self, guild_id: str, channel_id: str, 
                              analysis_type: str = "comprehensive",
                              limit: int = 1000) -> Dict[str, Any]:
        """
        Analyze Discord channel messages using Gemini
        
        Args:
            guild_id: Discord guild (server) ID
            channel_id: Discord channel ID
            analysis_type: Type of analysis (comprehensive, summary, entities)
            limit: Maximum number of messages to analyze
            
        Returns:
            Analysis results dictionary
        """
        # Load messages from database
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Get guild and channel info
        cur.execute("SELECT name FROM discord_guilds WHERE discord_id = ?", (guild_id,))
        guild_row = cur.fetchone()
        guild_name = guild_row[0] if guild_row else None
        
        cur.execute("SELECT name FROM discord_channels WHERE discord_id = ?", (channel_id,))
        channel_row = cur.fetchone()
        channel_name = channel_row[0] if channel_row else None
        
        # Get messages
        cur.execute("""
            SELECT created_at, author_username, author_display_name, content, 
                   embed_data, reaction_count, message_id
            FROM discord_messages 
            WHERE guild_id = ? AND channel_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (guild_id, channel_id, limit))
        
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            raise ValueError(f"No messages found for guild {guild_id}, channel {channel_id}")
        
        # Convert to message dictionaries
        messages = []
        for row in rows:
            messages.append({
                'created_at': row[0],
                'author_username': row[1],
                'author_display_name': row[2],
                'content': row[3],
                'embed_data': row[4],
                'reaction_count': row[5] or 0,
                'message_id': row[6]
            })
        
        # Format messages for analysis
        messages_text = self.format_discord_messages(messages, include_embeds=True)
        
        if not messages_text.strip():
            raise ValueError("No meaningful content found in messages")
        
        # Build Discord-specific prompt
        prompt = self._build_discord_analysis_prompt(messages_text, analysis_type, 
                                                   guild_name, channel_name)
        
        # Use parent class analysis method
        return self.analyze_messages(messages_text, analysis_type)

def export_discord_messages_to_file(guild_id: str, channel_id: str, 
                                   output_file: str, limit: int = None) -> str:
    """
    Export Discord messages to text file for analysis
    
    Args:
        guild_id: Discord guild ID
        channel_id: Discord channel ID  
        output_file: Output file path
        limit: Maximum number of messages (None for all)
        
    Returns:
        Path to created file
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    query = """
        SELECT created_at, author_username, author_display_name, content, embed_data
        FROM discord_messages 
        WHERE guild_id = ? AND channel_id = ?
        ORDER BY created_at ASC
    """
    params = [guild_id, channel_id]
    
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        raise ValueError(f"No messages found for guild {guild_id}, channel {channel_id}")
    
    # Convert to message format and write to file
    messages = []
    for row in rows:
        messages.append({
            'created_at': row[0],
            'author_username': row[1],
            'author_display_name': row[2],
            'content': row[3],
            'embed_data': row[4]
        })
    
    analyzer = DiscordGeminiAnalyzer(os.getenv("GEMINI_API_KEY"))
    messages_text = analyzer.format_discord_messages(messages, include_embeds=True)
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(messages_text)
    
    print(f"Exported {len(messages)} Discord messages to {output_file}")
    return output_file

def main():
    parser = argparse.ArgumentParser(description="Analyze Discord messages using Gemini AI")
    parser.add_argument("--guild-id", help="Discord guild (server) ID")
    parser.add_argument("--channel-id", help="Discord channel ID")
    parser.add_argument("--messages-file", help="Path to Discord messages file (alternative to guild/channel)")
    parser.add_argument("--out", default="./data/discord_analysis/", help="Output directory")
    parser.add_argument("--analysis-type", default="comprehensive",
                       choices=["comprehensive", "summary", "entities"],
                       help="Type of analysis to perform")
    parser.add_argument("--limit", type=int, default=1000, help="Maximum messages to analyze")
    parser.add_argument("--export-only", action="store_true", 
                       help="Only export messages to file, don't analyze")
    
    args = parser.parse_args()
    
    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY must be set in environment or .env file")
    
    # Create output directory
    os.makedirs(args.out, exist_ok=True)
    
    analyzer = DiscordGeminiAnalyzer(api_key)
    
    if args.messages_file:
        # Analyze from file
        print(f"Loading messages from: {args.messages_file}")
        messages_text = load_messages_from_file(args.messages_file)
        
        if not messages_text.strip():
            raise SystemExit("No messages found in file")
        
        print(f"Analyzing {len(messages_text.splitlines())} lines of Discord messages...")
        results = analyzer.analyze_messages(messages_text, args.analysis_type)
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        output_file = os.path.join(args.out, f"discord_file_analysis_{timestamp}.md")
        
    elif args.guild_id and args.channel_id:
        # Analyze from database
        if args.export_only:
            # Export only
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            export_file = os.path.join(args.out, f"discord_messages_{args.guild_id}_{args.channel_id}_{timestamp}.txt")
            export_discord_messages_to_file(args.guild_id, args.channel_id, export_file, args.limit)
            return
        
        print(f"Analyzing Discord guild {args.guild_id}, channel {args.channel_id}")
        results = analyzer.analyze_discord_channel(args.guild_id, args.channel_id, 
                                                  args.analysis_type, args.limit)
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        output_file = os.path.join(args.out, f"discord_analysis_{args.guild_id}_{args.channel_id}_{timestamp}.md")
        
    else:
        raise SystemExit("Must provide either --messages-file or both --guild-id and --channel-id")
    
    # Save results
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# Discord Analysis Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Analysis Type:** {args.analysis_type}\n")
        
        if args.guild_id and args.channel_id:
            f.write(f"**Guild ID:** {args.guild_id}\n")
            f.write(f"**Channel ID:** {args.channel_id}\n")
        elif args.messages_file:
            f.write(f"**Source File:** {args.messages_file}\n")
        
        f.write(f"\n## Analysis Results\n\n")
        f.write(results.get('analysis', 'No analysis generated'))
        
        if results.get('metadata'):
            f.write(f"\n\n## Analysis Metadata\n\n")
            f.write(f"- **Messages Processed:** {results['metadata'].get('messages_processed', 'N/A')}\n")
            f.write(f"- **API Requests:** {results['metadata'].get('api_requests', 'N/A')}\n")
            f.write(f"- **Citations Found:** {results['metadata'].get('citations_count', 'N/A')}\n")
    
    # Save metadata
    metadata_file = output_file.replace('.md', '_metadata.json')
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(results.get('metadata', {}), f, indent=2)
    
    print(f"\n✅ Analysis complete!")
    print(f"📄 Report: {output_file}")
    print(f"📊 Metadata: {metadata_file}")

if __name__ == "__main__":
    main()