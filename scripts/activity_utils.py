#!/usr/bin/env python3
"""
Activity utilities for channel analytics with participant-focused engagement scoring.
Provides on-demand calculation of activity metrics with configurable thresholds.
"""

import os
import sqlite3
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict

from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("SQLITE_DB_PATH", "./data/backfill.sqlite")


def validate_threshold_or_fail(threshold_value: str) -> int:
    """
    Validate ACTIVITY_MESSAGE_THRESHOLD is a positive integer.
    
    Args:
        threshold_value: String value from environment variable
        
    Returns:
        Validated threshold as integer
        
    Raises:
        SystemExit: If validation fails, exits with status code 1
    """
    try:
        threshold = int(threshold_value)
        if threshold <= 0:
            print(f"❌ ERROR: ACTIVITY_MESSAGE_THRESHOLD must be positive, got: {threshold}")
            sys.exit(1)
        return threshold
    except (ValueError, TypeError):
        print(f"❌ ERROR: ACTIVITY_MESSAGE_THRESHOLD must be a valid integer, got: {threshold_value}")
        sys.exit(1)


def get_channels_with_activity(min_messages: int) -> List[Dict[str, Any]]:
    """
    Get channels that have more than min_messages since last activity calculation.
    
    Args:
        min_messages: Minimum message count to be considered active
        
    Returns:
        List of channel dictionaries with activity info
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Get channels with their last activity calculation timestamp
    cur.execute("""
        SELECT tg_id, username, title, last_activity_calculated
        FROM channels 
        WHERE tg_id IS NOT NULL
    """)
    
    channels = []
    for tg_id, username, title, last_calculated in cur.fetchall():
        # Count messages since last calculation
        if last_calculated:
            cur.execute("""
                SELECT COUNT(*) FROM messages 
                WHERE channel_id = ? AND date > ? AND processed = 1
            """, (tg_id, last_calculated))
        else:
            # If never calculated, count today's messages
            today = datetime.now().strftime('%Y-%m-%d')
            cur.execute("""
                SELECT COUNT(*) FROM messages 
                WHERE channel_id = ? AND DATE(date) = ? AND processed = 1
            """, (tg_id, today))
        
        new_message_count = cur.fetchone()[0]
        
        if new_message_count >= min_messages:
            channels.append({
                'tg_id': tg_id,
                'username': username or f"Channel_{tg_id}",
                'title': title or 'Unknown',
                'new_messages': new_message_count,
                'last_calculated': last_calculated
            })
    
    conn.close()
    return channels


def get_current_day_stats(channel_id: str) -> Dict[str, Any]:
    """
    Get comprehensive activity statistics for a channel for the current day only.
    
    Args:
        channel_id: Telegram channel ID
        
    Returns:
        Dictionary with current day statistics
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Total messages today
    cur.execute("""
        SELECT COUNT(*) FROM messages 
        WHERE channel_id = ? AND DATE(date) = ? AND processed = 1
    """, (channel_id, today))
    total_messages = cur.fetchone()[0]
    
    # Unique participants today
    cur.execute("""
        SELECT COUNT(DISTINCT sender_username) FROM messages 
        WHERE channel_id = ? AND DATE(date) = ? AND processed = 1 
        AND sender_username IS NOT NULL
    """, (channel_id, today))
    unique_participants = cur.fetchone()[0]
    
    # Reply count (messages with reply_to_msg_id)
    cur.execute("""
        SELECT COUNT(*) FROM messages 
        WHERE channel_id = ? AND DATE(date) = ? AND processed = 1 
        AND reply_to_msg_id IS NOT NULL
    """, (channel_id, today))
    reply_count = cur.fetchone()[0]
    
    # Average message length today
    cur.execute("""
        SELECT AVG(LENGTH(text)) FROM messages 
        WHERE channel_id = ? AND DATE(date) = ? AND processed = 1 
        AND text IS NOT NULL
    """, (channel_id, today))
    avg_message_length = cur.fetchone()[0] or 0
    
    # Top contributors today
    cur.execute("""
        SELECT sender_username, COUNT(*) as msg_count
        FROM messages 
        WHERE channel_id = ? AND DATE(date) = ? AND processed = 1 
        AND sender_username IS NOT NULL
        GROUP BY sender_username 
        ORDER BY msg_count DESC 
        LIMIT 5
    """, (channel_id, today))
    top_contributors = cur.fetchall()
    
    conn.close()
    
    # Calculate reply ratio
    reply_ratio = (reply_count / total_messages) if total_messages > 0 else 0
    
    return {
        'channel_id': channel_id,
        'date': today,
        'total_messages': total_messages,
        'unique_participants': unique_participants,
        'reply_count': reply_count,
        'reply_ratio': reply_ratio,
        'avg_message_length': round(avg_message_length, 1),
        'top_contributors': top_contributors
    }


def calculate_engagement_score(channel_stats: Dict[str, Any]) -> float:
    """
    Calculate engagement score prioritizing participant diversity.
    
    Formula: (unique_participants * 2) + (total_messages * 1) + (reply_ratio * 1.5)
    
    Args:
        channel_stats: Channel statistics from get_current_day_stats()
        
    Returns:
        Engagement score as float
    """
    participants_score = channel_stats['unique_participants'] * 2
    message_score = channel_stats['total_messages'] * 1
    reply_score = channel_stats['reply_ratio'] * 1.5
    
    return round(participants_score + message_score + reply_score, 2)


def rank_channels_by_engagement(channel_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rank channels by engagement score with total messages as tie-breaker.
    
    Args:
        channel_list: List of channels with statistics
        
    Returns:
        Sorted list of channels by engagement score (descending)
    """
    # Calculate engagement scores for all channels
    for channel in channel_list:
        channel['engagement_score'] = calculate_engagement_score(channel)
    
    # Sort by engagement score (desc), then by total messages (desc) for tie-breaking
    return sorted(
        channel_list, 
        key=lambda x: (x['engagement_score'], x['total_messages']), 
        reverse=True
    )


def get_daily_totals() -> Dict[str, Any]:
    """
    Get aggregate statistics for all channels for the current day.
    
    Returns:
        Dictionary with daily aggregate statistics
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Total messages across all channels today
    cur.execute("""
        SELECT COUNT(*) FROM messages 
        WHERE DATE(date) = ? AND processed = 1
    """, (today,))
    total_messages = cur.fetchone()[0]
    
    # Total unique participants across all channels today
    cur.execute("""
        SELECT COUNT(DISTINCT sender_username) FROM messages 
        WHERE DATE(date) = ? AND processed = 1 
        AND sender_username IS NOT NULL
    """, (today,))
    total_participants = cur.fetchone()[0]
    
    # Number of active channels (with at least 1 message today)
    cur.execute("""
        SELECT COUNT(DISTINCT channel_id) FROM messages 
        WHERE DATE(date) = ? AND processed = 1
    """, (today,))
    active_channels = cur.fetchone()[0]
    
    # Total channels in database
    cur.execute("SELECT COUNT(*) FROM channels WHERE tg_id IS NOT NULL")
    total_channels = cur.fetchone()[0]
    
    # Total replies today
    cur.execute("""
        SELECT COUNT(*) FROM messages 
        WHERE DATE(date) = ? AND processed = 1 
        AND reply_to_msg_id IS NOT NULL
    """, (today,))
    total_replies = cur.fetchone()[0]
    
    conn.close()
    
    # Calculate overall reply ratio
    overall_reply_ratio = (total_replies / total_messages) if total_messages > 0 else 0
    
    return {
        'date': today,
        'total_messages': total_messages,
        'total_participants': total_participants,
        'active_channels': active_channels,
        'total_channels': total_channels,
        'total_replies': total_replies,
        'overall_reply_ratio': round(overall_reply_ratio, 3)
    }


def update_channel_activity_timestamp(channel_id: str) -> None:
    """
    Update the last_activity_calculated timestamp for a channel.
    
    Args:
        channel_id: Telegram channel ID
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    cur.execute("""
        UPDATE channels 
        SET last_activity_calculated = ? 
        WHERE tg_id = ?
    """, (timestamp, channel_id))
    
    conn.commit()
    conn.close()


if __name__ == "__main__":
    # Test the utilities
    print("🔧 Testing Activity Utils")
    print("=" * 40)
    
    # Test threshold validation
    test_threshold = os.getenv("ACTIVITY_MESSAGE_THRESHOLD", "5")
    threshold = validate_threshold_or_fail(test_threshold)
    print(f"✅ Threshold validation: {threshold}")
    
    # Test daily totals
    totals = get_daily_totals()
    print(f"📊 Daily totals: {totals}")
    
    # Test active channels
    active = get_channels_with_activity(threshold)
    print(f"📈 Active channels ({threshold}+ msgs): {len(active)}")
    
    for channel in active[:3]:  # Show first 3
        stats = get_current_day_stats(channel['tg_id'])
        engagement = calculate_engagement_score(stats)
        print(f"   {channel['username']}: {stats['total_messages']} msgs, {stats['unique_participants']} users, engagement: {engagement}")