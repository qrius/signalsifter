#!/usr/bin/env python3
"""
Decode Discord snowflake ID to get timestamp
"""
from datetime import datetime, timezone

def decode_snowflake(snowflake_id):
    """Decode Discord snowflake to get creation timestamp"""
    # Discord epoch is January 1, 2015 00:00:00 UTC
    DISCORD_EPOCH = 1420070400000  # milliseconds
    
    # Convert to int if string
    if isinstance(snowflake_id, str):
        snowflake_id = int(snowflake_id)
    
    # Extract timestamp from snowflake (first 42 bits)
    timestamp_ms = (snowflake_id >> 22) + DISCORD_EPOCH
    timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    
    return timestamp

if __name__ == "__main__":
    message_id = "1439884177678925875"
    timestamp = decode_snowflake(message_id)
    
    print(f"Discord Message ID: {message_id}")
    print(f"Created at: {timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"Local date: {timestamp.astimezone().strftime('%Y-%m-%d %H:%M:%S')}")