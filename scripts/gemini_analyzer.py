#!/usr/bin/env python3
"""
Gemini API analyzer for Telegram channel messages.
Provides NotebookLM-like analysis capabilities with rate limiting for Google AI Studio free tier.

Usage:
  python scripts/gemini_analyzer.py --messages-file data/raw_messages_detailed_100.txt --out data/analysis/
  
Environment variables (in `.env`):
  GEMINI_API_KEY      # Google AI Studio API key
  
Rate Limits (Free Tier):
  - 2 requests per minute
  - 50 requests per day
  - 2M token context window

Privacy Note:
  - Only processes public Telegram messages
  - Google may use inputs/outputs for model training on free tier
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import re
from collections import Counter, defaultdict

import google.generativeai as genai
from dotenv import load_dotenv
from ratelimit import limits, sleep_and_retry
import requests


load_dotenv()

# Rate limiting configuration for free tier
REQUESTS_PER_MINUTE = 2
REQUESTS_PER_DAY = 50
MAX_TOKENS_PER_REQUEST = 2000000  # 2M context window

# Database configuration
DB_PATH = os.getenv("SQLITE_DB_PATH", "./data/backfill.sqlite")


class GeminiAnalyzer:
    def __init__(self, api_key: str):
        """Initialize Gemini analyzer with rate limiting."""
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        # Rate limiting state
        self.daily_requests = 0
        self.last_request_day = datetime.now().date()
        self.request_times = []
        
    def _check_daily_limit(self) -> bool:
        """Check if daily request limit has been exceeded."""
        current_date = datetime.now().date()
        
        # Reset daily counter if new day
        if current_date != self.last_request_day:
            self.daily_requests = 0
            self.last_request_day = current_date
            
        return self.daily_requests < REQUESTS_PER_DAY
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting: max 2 requests per minute."""
        now = time.time()
        
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        # If we've made 2 requests in the last minute, wait
        if len(self.request_times) >= REQUESTS_PER_MINUTE:
            sleep_time = 60 - (now - self.request_times[0]) + 1  # +1 second buffer
            if sleep_time > 0:
                print(f"Rate limiting: waiting {sleep_time:.1f} seconds...")
                time.sleep(sleep_time)
        
        # Record this request
        self.request_times.append(now)
        self.daily_requests += 1
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars = ~1 token)."""
        return len(text) // 4
    
    def _chunk_messages(self, messages: str, max_tokens: int = 1800000) -> List[str]:
        """Split messages into chunks that fit within token limits (with buffer)."""
        lines = messages.split('\n')
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for line in lines:
            line_tokens = self._estimate_tokens(line)
            
            if current_tokens + line_tokens > max_tokens and current_chunk:
                # Save current chunk and start new one
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_tokens = line_tokens
            else:
                current_chunk.append(line)
                current_tokens += line_tokens
        
        # Add final chunk
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
            
        return chunks
    
    def analyze_messages(self, messages_text: str, analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """
        Analyze Telegram messages using Gemini API with NotebookLM-style insights.
        
        Args:
            messages_text: Raw message text in format [timestamp] @user: message
            analysis_type: Type of analysis (comprehensive, summary, entities)
            
        Returns:
            Dictionary containing analysis results with citations
        """
        if not self._check_daily_limit():
            raise Exception(f"Daily API limit ({REQUESTS_PER_DAY}) exceeded")
        
        # Chunk messages if too large
        chunks = self._chunk_messages(messages_text)
        
        if len(chunks) > 1:
            print(f"Processing {len(chunks)} chunks due to size...")
        
        all_results = []
        
        for i, chunk in enumerate(chunks, 1):
            print(f"Analyzing chunk {i}/{len(chunks)}...")
            
            self._enforce_rate_limit()
            
            prompt = self._build_analysis_prompt(chunk, analysis_type)
            
            try:
                response = self.model.generate_content(prompt)
                result = self._parse_response(response.text, chunk_id=i)
                all_results.append(result)
                
            except Exception as e:
                print(f"API error on chunk {i}: {e}")
                # Fallback analysis
                result = self._fallback_analysis(chunk, chunk_id=i)
                all_results.append(result)
        
        # Combine results from all chunks
        return self._combine_chunk_results(all_results, messages_text)
    
    def _build_analysis_prompt(self, messages: str, analysis_type: str) -> str:
        """Build structured prompt for crypto community analysis."""
        
        base_prompt = """You are an expert cryptocurrency community analyst. Analyze the following Telegram channel messages and provide comprehensive insights similar to NotebookLM's deep analysis capabilities.

The messages are in format: [YYYY-MM-DD HH:MM:SS UTC] @username: message_content

Focus on:
1. **Key Topics & Themes** - Main discussion topics, trending subjects
2. **Market Sentiment** - Bullish/bearish sentiment, trading psychology  
3. **Technical Analysis** - Price discussions, chart patterns, market movements
4. **Project Updates** - New developments, announcements, partnerships
5. **Community Dynamics** - Active participants, engagement patterns
6. **Risk & Opportunities** - Investment discussions, risk management
7. **External Events** - Market news, regulatory updates, industry developments

For each insight, provide specific citations using the exact timestamp and username format from the messages.

CRITICAL: Use this exact citation format: [2025-12-07 17:20:13 UTC] @username

Messages to analyze:
"""
        
        comprehensive_instructions = """
Provide a detailed analysis report with:

## Executive Summary
Brief overview of key developments and sentiment (2-3 sentences)

## Detailed Analysis

### Market Sentiment & Trading Activity
- Overall sentiment (bullish/bearish/neutral)
- Key price discussions and predictions
- Trading strategies mentioned
- Risk management approaches
*Include citations for each point*

### Key Topics & Discussions
- Main themes discussed
- Project updates or announcements  
- Technical developments
- Community concerns or excitement
*Include citations for each point*

### Community Insights
- Most active participants
- Engagement patterns
- Notable conversations or debates
- Community sentiment shifts
*Include citations for each point*

### Extracted Entities
- Cryptocurrencies mentioned (with price context)
- Projects and protocols discussed
- Trading platforms or tools
- External links and resources
- Wallet addresses or transaction hashes
*Include citations for each point*

## Key Quotes & Citations
List 5-10 most significant messages with full citations

## Risk Assessment
- Potential concerns or warnings discussed
- Market risks identified by community
- Investment cautions mentioned
*Include citations for each point*

"""
        
        if analysis_type == "comprehensive":
            return base_prompt + messages + "\n" + comprehensive_instructions
        else:
            return base_prompt + messages + "\n\nProvide a focused analysis based on the specified type."
    
    def _parse_response(self, response_text: str, chunk_id: int) -> Dict[str, Any]:
        """Parse Gemini response into structured format."""
        return {
            "chunk_id": chunk_id,
            "analysis": response_text,
            "timestamp": datetime.now().isoformat(),
            "citations": self._extract_citations(response_text)
        }
    
    def _extract_citations(self, text: str) -> List[Dict[str, str]]:
        """Extract citation references from analysis text."""
        # Pattern: [YYYY-MM-DD HH:MM:SS UTC] @username
        citation_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC)\] @(\w+)'
        citations = []
        
        for match in re.finditer(citation_pattern, text):
            citations.append({
                "timestamp": match.group(1),
                "username": match.group(2),
                "full_citation": match.group(0)
            })
        
        return citations
    
    def _fallback_analysis(self, messages: str, chunk_id: int) -> Dict[str, Any]:
        """Provide basic analysis when API fails."""
        lines = messages.split('\n')
        usernames = []
        cryptocurrencies = []
        
        crypto_keywords = ['BTC', 'ETH', 'LUNA', 'OSMO', 'ATOM', 'NFT', 'DeFi', '$']
        
        for line in lines:
            if '@' in line and ':' in line:
                try:
                    username = line.split('@')[1].split(':')[0]
                    usernames.append(username)
                except:
                    pass
                    
            # Simple crypto detection
            for keyword in crypto_keywords:
                if keyword in line.upper():
                    cryptocurrencies.append(keyword)
        
        user_counts = Counter(usernames)
        crypto_counts = Counter(cryptocurrencies)
        
        analysis = f"""## Fallback Analysis (API Unavailable) - Chunk {chunk_id}

### Activity Summary
- Total messages analyzed: {len([l for l in lines if l.strip()])}
- Active users: {len(user_counts)}
- Crypto mentions: {len(crypto_counts)}

### Most Active Users
{chr(10).join([f"- @{user}: {count} messages" for user, count in user_counts.most_common(5)])}

### Cryptocurrency Mentions
{chr(10).join([f"- {crypto}: {count} mentions" for crypto, count in crypto_counts.most_common(10)])}

### Note
This is a simplified analysis due to API limitations. Key message patterns detected but detailed sentiment and context analysis unavailable.
"""
        
        return {
            "chunk_id": chunk_id,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat(),
            "citations": [],
            "fallback": True
        }
    
    def _combine_chunk_results(self, results: List[Dict[str, Any]], original_messages: str) -> Dict[str, Any]:
        """Combine analysis results from multiple chunks."""
        if len(results) == 1:
            return results[0]
        
        combined_analysis = "# Combined Analysis Report\n\n"
        combined_analysis += f"*Analyzed {len(results)} chunks due to message volume*\n\n"
        
        all_citations = []
        
        for i, result in enumerate(results, 1):
            combined_analysis += f"## Chunk {i} Analysis\n\n"
            combined_analysis += result["analysis"]
            combined_analysis += "\n\n---\n\n"
            all_citations.extend(result.get("citations", []))
        
        # Add overall summary
        combined_analysis += "## Overall Summary\n\n"
        combined_analysis += "This analysis covers multiple message segments. Key themes and insights have been extracted from each chunk above.\n"
        
        return {
            "analysis": combined_analysis,
            "timestamp": datetime.now().isoformat(),
            "citations": all_citations,
            "chunks_processed": len(results),
            "total_messages": len(original_messages.split('\n')),
            "combined": True
        }


def load_messages_from_file(file_path: str) -> str:
    """Load messages from raw messages file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Messages file not found: {file_path}")


def save_analysis_result(result: Dict[str, Any], output_dir: str, channel_name: str = "unknown"):
    """Save analysis results to files."""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    
    # Save full analysis
    analysis_file = os.path.join(output_dir, f"{channel_name}_gemini_analysis_{timestamp}.md")
    with open(analysis_file, 'w', encoding='utf-8') as f:
        f.write(f"# Gemini Analysis: {channel_name}\n")
        f.write(f"Generated: {result['timestamp']}\n\n")
        f.write(result['analysis'])
    
    # Save metadata
    metadata_file = os.path.join(output_dir, f"{channel_name}_gemini_metadata_{timestamp}.json")
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": result['timestamp'],
            "citations_count": len(result.get('citations', [])),
            "chunks_processed": result.get('chunks_processed', 1),
            "total_messages": result.get('total_messages', 0),
            "combined": result.get('combined', False),
            "fallback": result.get('fallback', False)
        }, f, indent=2)
    
    print(f"Analysis saved to: {analysis_file}")
    print(f"Metadata saved to: {metadata_file}")


def main():
    parser = argparse.ArgumentParser(description="Analyze Telegram messages using Gemini API")
    parser.add_argument("--messages-file", required=True, help="Path to raw messages file")
    parser.add_argument("--out", default="./data/gemini_analysis/", help="Output directory")
    parser.add_argument("--channel", default="unknown", help="Channel name for file naming")
    parser.add_argument("--analysis-type", default="comprehensive", 
                       choices=["comprehensive", "summary", "entities"],
                       help="Type of analysis to perform")
    
    args = parser.parse_args()
    
    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY must be set in environment or .env file")
    
    # Load messages
    print(f"Loading messages from: {args.messages_file}")
    messages_text = load_messages_from_file(args.messages_file)
    
    if not messages_text.strip():
        raise SystemExit("No messages found in file")
    
    print(f"Loaded {len(messages_text)} characters from {len(messages_text.split('\\n'))} lines")
    
    # Initialize analyzer
    analyzer = GeminiAnalyzer(api_key)
    
    # Perform analysis
    print(f"Starting {args.analysis_type} analysis...")
    try:
        result = analyzer.analyze_messages(messages_text, args.analysis_type)
        
        # Save results
        save_analysis_result(result, args.out, args.channel)
        
        print(f"Analysis complete! Citations found: {len(result.get('citations', []))}")
        
    except Exception as e:
        print(f"Analysis failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())