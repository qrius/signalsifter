#!/usr/bin/env python3
"""
Channel Dashboard - Generate daily activity reports in markdown format.
Focuses on participant diversity and engagement metrics with clean date-based naming.
"""

import os
import sys
from datetime import datetime
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.activity_utils import (
    validate_threshold_or_fail,
    get_channels_with_activity,
    get_current_day_stats,
    calculate_engagement_score,
    rank_channels_by_engagement,
    get_daily_totals,
    update_channel_activity_timestamp
)
from dotenv import load_dotenv

load_dotenv()


def generate_daily_activity_report() -> str:
    """
    Generate comprehensive daily activity report in markdown format.
    
    Returns:
        Path to generated report file
    """
    # Validate configuration
    threshold_env = os.getenv("ACTIVITY_MESSAGE_THRESHOLD", "5")
    threshold = validate_threshold_or_fail(threshold_env)
    
    # Get current date for report
    today = datetime.now()
    date_str = today.strftime('%Y-%m-%d')
    
    # Ensure reports directory exists
    reports_dir = "data/activity_reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    # Generate report filename
    report_filename = f"{date_str}_activity_report.md"
    report_path = os.path.join(reports_dir, report_filename)
    
    print(f"📊 Generating activity report for {date_str}...")
    print(f"   Using threshold: {threshold} messages")
    
    # Get data for report
    daily_totals = get_daily_totals()
    active_channels = get_channels_with_activity(threshold)
    
    # Get detailed stats for active channels
    channel_details = []
    for channel in active_channels:
        stats = get_current_day_stats(channel['tg_id'])
        stats.update({
            'username': channel['username'],
            'title': channel['title'],
            'new_messages': channel['new_messages']
        })
        channel_details.append(stats)
    
    # Rank channels by engagement
    ranked_channels = rank_channels_by_engagement(channel_details)
    
    # Generate markdown report
    markdown_content = generate_markdown_report(
        date_str, daily_totals, ranked_channels, threshold
    )
    
    # Write report to file
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    # Update activity timestamps for processed channels
    for channel in active_channels:
        update_channel_activity_timestamp(channel['tg_id'])
    
    print(f"✅ Report generated: {report_path}")
    print(f"   Active channels processed: {len(active_channels)}")
    
    return report_path


def generate_markdown_report(
    date_str: str, 
    daily_totals: Dict[str, Any], 
    ranked_channels: List[Dict[str, Any]], 
    threshold: int
) -> str:
    """
    Generate markdown content for the daily activity report.
    
    Args:
        date_str: Date string (YYYY-MM-DD)
        daily_totals: Aggregate statistics for the day
        ranked_channels: List of channels ranked by engagement
        threshold: Message threshold used for filtering
        
    Returns:
        Complete markdown report content
    """
    report = f"""# Daily Activity Report - {date_str}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}  
Minimum Activity Threshold: {threshold} messages

---

## 📊 Daily Summary

### Aggregate Statistics
- **Total Messages**: {daily_totals['total_messages']:,}
- **Total Participants**: {daily_totals['total_participants']:,}
- **Active Channels**: {daily_totals['active_channels']}/{daily_totals['total_channels']}
- **Total Replies**: {daily_totals['total_replies']:,}
- **Overall Reply Ratio**: {daily_totals['overall_reply_ratio']:.1%}

### Activity Overview
- **Channels Above Threshold**: {len(ranked_channels)}
- **Average Messages per Active Channel**: {(daily_totals['total_messages'] / daily_totals['active_channels']) if daily_totals['active_channels'] > 0 else 0:.1f}
- **Average Participants per Active Channel**: {(daily_totals['total_participants'] / daily_totals['active_channels']) if daily_totals['active_channels'] > 0 else 0:.1f}

---

## 🏆 Channel Rankings (by Engagement Score)

*Engagement Formula: (Unique Participants × 2) + (Total Messages × 1) + (Reply Ratio × 1.5)*

"""

    if not ranked_channels:
        report += "No channels met the minimum activity threshold today.\n\n"
    else:
        for i, channel in enumerate(ranked_channels, 1):
            engagement_score = calculate_engagement_score(channel)
            
            report += f"""### #{i} {channel['username']}
**{channel['title']}**

- **Engagement Score**: {engagement_score:.2f}
- **Messages**: {channel['total_messages']:,}
- **Unique Participants**: {channel['unique_participants']:,}
- **Replies**: {channel['reply_count']:,} ({channel['reply_ratio']:.1%})
- **Avg Message Length**: {channel['avg_message_length']:.1f} characters

**Top Contributors Today:**
"""
            if channel['top_contributors']:
                for username, msg_count in channel['top_contributors']:
                    report += f"- @{username}: {msg_count} messages\n"
            else:
                report += "- No identified contributors\n"
            
            report += "\n"

    # Add footer with metadata
    report += f"""---

## 📋 Report Metadata

- **Report Date**: {date_str}
- **Generation Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
- **Activity Threshold**: {threshold} messages minimum
- **Total Channels Analyzed**: {daily_totals['total_channels']}
- **Channels Meeting Threshold**: {len(ranked_channels)}

### Engagement Scoring
- **Participant Diversity Weight**: 2.0 (prioritized)
- **Message Volume Weight**: 1.0
- **Reply Interaction Weight**: 1.5
- **Tie-Breaker**: Total message count

---

*Generated by SignalSifter Activity Analytics*
"""

    return report


def main():
    """Main execution function for manual dashboard generation."""
    print("🎛️ SignalSifter Channel Dashboard")
    print("=" * 50)
    
    try:
        report_path = generate_daily_activity_report()
        
        print(f"\n📋 Activity report generated successfully!")
        print(f"📁 Location: {report_path}")
        
        # Show brief summary
        daily_totals = get_daily_totals()
        threshold_env = os.getenv("ACTIVITY_MESSAGE_THRESHOLD", "5")
        threshold = validate_threshold_or_fail(threshold_env)
        active_channels = get_channels_with_activity(threshold)
        
        print(f"\n📊 Quick Summary:")
        print(f"   • Total messages today: {daily_totals['total_messages']:,}")
        print(f"   • Active channels: {daily_totals['active_channels']}")
        print(f"   • Channels above threshold ({threshold}+): {len(active_channels)}")
        print(f"   • Total participants: {daily_totals['total_participants']:,}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error generating activity report: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)