#!/usr/bin/env python3
"""
Comprehensive Discord Data Analysis for SignalSifter
Analyzes extracted Discord messages to provide insights on:
- User activity patterns
- Content analysis
- Temporal trends  
- Message statistics
- Community engagement metrics
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import json
import re
from collections import Counter
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class DiscordDataAnalyzer:
    def __init__(self, db_path="data/backfill.sqlite"):
        """Initialize analyzer with database connection"""
        self.db_path = db_path
        self.df = None
        
    def load_data(self):
        """Load Discord messages from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = """
            SELECT 
                message_id,
                username,
                display_name,
                user_id,
                content,
                timestamp,
                channel_id,
                server_id,
                reactions,
                embeds,
                mentions,
                is_bot,
                is_pinned,
                parent_id
            FROM discord_messages 
            ORDER BY timestamp ASC
            """
            
            self.df = pd.read_sql_query(query, conn)
            conn.close()
            
            # Convert timestamp to datetime
            self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
            
            # Add derived columns
            self.df['date'] = self.df['timestamp'].dt.date
            self.df['hour'] = self.df['timestamp'].dt.hour
            self.df['day_of_week'] = self.df['timestamp'].dt.day_name()
            self.df['content_length'] = self.df['content'].fillna('').str.len()
            self.df['has_content'] = self.df['content_length'] > 0
            self.df['word_count'] = self.df['content'].fillna('').apply(lambda x: len(x.split()) if x else 0)
            
            print(f"✓ Loaded {len(self.df)} messages from Discord database")
            return True
            
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return False
    
    def basic_statistics(self):
        """Generate basic statistics about the dataset"""
        if self.df is None:
            print("❌ No data loaded")
            return
        
        print("\n" + "="*60)
        print("📊 BASIC DISCORD DATA STATISTICS")
        print("="*60)
        
        # Overall stats
        total_messages = len(self.df)
        messages_with_content = len(self.df[self.df['has_content']])
        unique_users = self.df['username'].nunique()
        date_range = f"{self.df['date'].min()} to {self.df['date'].max()}"
        days_covered = (self.df['date'].max() - self.df['date'].min()).days + 1
        
        print(f"📈 Total Messages: {total_messages:,}")
        print(f"💬 Messages with Content: {messages_with_content:,} ({messages_with_content/total_messages*100:.1f}%)")
        print(f"👥 Unique Users: {unique_users}")
        print(f"📅 Date Range: {date_range}")
        print(f"🗓️  Days Covered: {days_covered}")
        print(f"📊 Avg Messages/Day: {total_messages/max(days_covered,1):.1f}")
        
        # Content statistics
        if messages_with_content > 0:
            avg_length = self.df[self.df['has_content']]['content_length'].mean()
            avg_words = self.df[self.df['has_content']]['word_count'].mean()
            print(f"📝 Avg Message Length: {avg_length:.1f} characters")
            print(f"🔤 Avg Word Count: {avg_words:.1f} words")
        
        # Bot analysis
        bot_messages = len(self.df[self.df['is_bot'] == True])
        if bot_messages > 0:
            print(f"🤖 Bot Messages: {bot_messages:,} ({bot_messages/total_messages*100:.1f}%)")
        
        return {
            'total_messages': total_messages,
            'messages_with_content': messages_with_content,
            'unique_users': unique_users,
            'days_covered': days_covered,
            'avg_length': avg_length if messages_with_content > 0 else 0
        }
    
    def user_activity_analysis(self):
        """Analyze user activity patterns"""
        if self.df is None:
            return
        
        print("\n" + "="*60)
        print("👥 USER ACTIVITY ANALYSIS")
        print("="*60)
        
        # Most active users
        user_stats = self.df.groupby('username').agg({
            'message_id': 'count',
            'content_length': ['mean', 'sum'],
            'word_count': 'sum',
            'timestamp': ['min', 'max']
        }).round(1)
        
        user_stats.columns = ['message_count', 'avg_length', 'total_chars', 'total_words', 'first_message', 'last_message']
        user_stats = user_stats.sort_values('message_count', ascending=False)
        
        print("\n🏆 TOP 10 MOST ACTIVE USERS:")
        print("-" * 80)
        for i, (username, stats) in enumerate(user_stats.head(10).iterrows()):
            print(f"{i+1:2d}. {username:<20} | {stats['message_count']:4.0f} msgs | {stats['avg_length']:5.1f} avg chars | {stats['total_words']:5.0f} words")
        
        # User engagement metrics
        print(f"\n📊 USER ENGAGEMENT METRICS:")
        total_users = len(user_stats)
        active_users = len(user_stats[user_stats['message_count'] >= 5])
        super_users = len(user_stats[user_stats['message_count'] >= 50])
        
        print(f"   Total Users: {total_users}")
        print(f"   Active Users (5+ messages): {active_users} ({active_users/total_users*100:.1f}%)")
        print(f"   Super Users (50+ messages): {super_users} ({super_users/total_users*100:.1f}%)")
        
        return user_stats
    
    def temporal_analysis(self):
        """Analyze message patterns over time"""
        if self.df is None:
            return
        
        print("\n" + "="*60)
        print("⏰ TEMPORAL ACTIVITY ANALYSIS")
        print("="*60)
        
        # Daily activity
        daily_stats = self.df.groupby('date').agg({
            'message_id': 'count',
            'username': 'nunique',
            'content_length': 'mean'
        }).round(1)
        daily_stats.columns = ['messages', 'active_users', 'avg_length']
        
        print(f"\n📅 DAILY ACTIVITY SUMMARY:")
        print(f"   Peak Day: {daily_stats['messages'].idxmax()} ({daily_stats['messages'].max()} messages)")
        print(f"   Quiet Day: {daily_stats['messages'].idxmin()} ({daily_stats['messages'].min()} messages)")
        print(f"   Avg Messages/Day: {daily_stats['messages'].mean():.1f}")
        
        # Hour of day analysis
        hourly_stats = self.df.groupby('hour')['message_id'].count()
        peak_hour = hourly_stats.idxmax()
        quiet_hour = hourly_stats.idxmin()
        
        print(f"\n🕐 HOURLY ACTIVITY PATTERNS:")
        print(f"   Peak Hour: {peak_hour}:00 ({hourly_stats[peak_hour]} messages)")
        print(f"   Quiet Hour: {quiet_hour}:00 ({hourly_stats[quiet_hour]} messages)")
        
        # Day of week analysis  
        weekday_stats = self.df.groupby('day_of_week')['message_id'].count()
        # Reorder days properly
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        weekday_stats = weekday_stats.reindex([d for d in day_order if d in weekday_stats.index])
        
        print(f"\n📆 WEEKLY ACTIVITY PATTERNS:")
        for day, count in weekday_stats.items():
            bar = "█" * int(count / weekday_stats.max() * 20)
            print(f"   {day:<10} {count:4d} {bar}")
        
        return {
            'daily_stats': daily_stats,
            'hourly_stats': hourly_stats,
            'weekday_stats': weekday_stats
        }
    
    def content_analysis(self):
        """Analyze message content patterns"""
        if self.df is None:
            return
        
        print("\n" + "="*60)
        print("💬 CONTENT ANALYSIS")
        print("="*60)
        
        # Filter messages with content
        content_df = self.df[self.df['has_content']].copy()
        
        if len(content_df) == 0:
            print("❌ No messages with content found")
            return
        
        # Content length distribution
        print(f"📝 MESSAGE LENGTH STATISTICS:")
        print(f"   Average: {content_df['content_length'].mean():.1f} characters")
        print(f"   Median: {content_df['content_length'].median():.1f} characters")
        print(f"   Longest: {content_df['content_length'].max()} characters")
        print(f"   Shortest: {content_df['content_length'].min()} characters")
        
        # Word analysis
        all_content = ' '.join(content_df['content'].fillna('').astype(str))
        words = re.findall(r'\b\w+\b', all_content.lower())
        word_freq = Counter(words)
        
        print(f"\n🔤 WORD ANALYSIS:")
        print(f"   Total Words: {len(words):,}")
        print(f"   Unique Words: {len(word_freq):,}")
        print(f"   Avg Words/Message: {len(words)/len(content_df):.1f}")
        
        # Most common words (excluding common stop words)
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'a', 'an', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
        
        filtered_words = {word: count for word, count in word_freq.items() 
                         if word not in stop_words and len(word) > 2}
        
        print(f"\n🏆 TOP 15 MOST COMMON WORDS:")
        print("-" * 40)
        for i, (word, count) in enumerate(sorted(filtered_words.items(), key=lambda x: x[1], reverse=True)[:15]):
            print(f"{i+1:2d}. {word:<15} {count:4d} times")
        
        # Message types
        urls = content_df['content'].str.contains(r'http[s]?://', case=False, na=False).sum()
        questions = content_df['content'].str.contains(r'\?', na=False).sum()
        long_messages = len(content_df[content_df['content_length'] > 200])
        
        print(f"\n📊 MESSAGE TYPES:")
        print(f"   Messages with URLs: {urls} ({urls/len(content_df)*100:.1f}%)")
        print(f"   Questions (?): {questions} ({questions/len(content_df)*100:.1f}%)")
        print(f"   Long messages (>200 chars): {long_messages} ({long_messages/len(content_df)*100:.1f}%)")
        
        return {
            'word_frequency': dict(word_freq.most_common(50)),
            'content_stats': {
                'avg_length': content_df['content_length'].mean(),
                'total_words': len(words),
                'unique_words': len(word_freq)
            }
        }
    
    def engagement_analysis(self):
        """Analyze user engagement and interactions"""
        if self.df is None:
            return
        
        print("\n" + "="*60)
        print("🎯 ENGAGEMENT & INTERACTION ANALYSIS")
        print("="*60)
        
        # Reaction analysis
        reactions_df = self.df[self.df['reactions'].notna()].copy()
        
        if len(reactions_df) > 0:
            print(f"😊 REACTION STATISTICS:")
            print(f"   Messages with reactions: {len(reactions_df)} ({len(reactions_df)/len(self.df)*100:.1f}%)")
            
            # Parse reaction data
            all_reactions = []
            for reactions_json in reactions_df['reactions']:
                try:
                    reactions = json.loads(reactions_json)
                    for reaction in reactions:
                        all_reactions.extend([reaction.get('emoji', 'unknown')] * reaction.get('count', 1))
                except:
                    pass
            
            if all_reactions:
                reaction_counts = Counter(all_reactions)
                print(f"   Total reactions: {len(all_reactions)}")
                print(f"   Top reactions: {dict(list(reaction_counts.most_common(5)))}")
        
        # Mention analysis
        mentions_df = self.df[self.df['mentions'].notna()].copy()
        
        if len(mentions_df) > 0:
            print(f"\n@ MENTION STATISTICS:")
            print(f"   Messages with mentions: {len(mentions_df)} ({len(mentions_df)/len(self.df)*100:.1f}%)")
        
        # Thread/reply analysis
        replies_df = self.df[self.df['parent_id'].notna()].copy()
        
        if len(replies_df) > 0:
            print(f"\n💬 THREAD/REPLY STATISTICS:")
            print(f"   Reply messages: {len(replies_df)} ({len(replies_df)/len(self.df)*100:.1f}%)")
        
        # Embed analysis
        embeds_df = self.df[self.df['embeds'].notna()].copy()
        
        if len(embeds_df) > 0:
            print(f"\n📎 EMBED STATISTICS:")
            print(f"   Messages with embeds: {len(embeds_df)} ({len(embeds_df)/len(self.df)*100:.1f}%)")
    
    def generate_comprehensive_report(self, output_file="discord_analysis_report.txt"):
        """Generate a comprehensive analysis report"""
        print("\n" + "="*60)
        print("📋 GENERATING COMPREHENSIVE REPORT")
        print("="*60)
        
        # Redirect print output to file
        import sys
        original_stdout = sys.stdout
        
        with open(output_file, 'w', encoding='utf-8') as f:
            sys.stdout = f
            
            print("DISCORD DATA ANALYSIS REPORT")
            print("="*50)
            print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Database: {self.db_path}")
            print()
            
            # Run all analyses
            basic_stats = self.basic_statistics()
            user_stats = self.user_activity_analysis()
            temporal_data = self.temporal_analysis()
            content_data = self.content_analysis()
            self.engagement_analysis()
            
            print("\n" + "="*50)
            print("END OF REPORT")
        
        # Restore stdout
        sys.stdout = original_stdout
        
        print(f"✅ Comprehensive report saved to: {output_file}")
        return output_file
    
    def export_data_for_further_analysis(self, output_dir="discord_analysis_exports"):
        """Export processed data for further analysis"""
        import os
        
        if self.df is None:
            print("❌ No data to export")
            return
        
        # Create output directory
        Path(output_dir).mkdir(exist_ok=True)
        
        # Export main dataset
        self.df.to_csv(f"{output_dir}/discord_messages_processed.csv", index=False)
        print(f"✅ Exported main dataset: {output_dir}/discord_messages_processed.csv")
        
        # Export user statistics
        if hasattr(self, '_user_stats'):
            self.user_stats.to_csv(f"{output_dir}/user_statistics.csv")
            print(f"✅ Exported user stats: {output_dir}/user_statistics.csv")
        
        # Export daily activity
        daily_activity = self.df.groupby('date').agg({
            'message_id': 'count',
            'username': 'nunique'
        })
        daily_activity.to_csv(f"{output_dir}/daily_activity.csv")
        print(f"✅ Exported daily activity: {output_dir}/daily_activity.csv")
        
        print(f"\n📁 All exports saved to: {output_dir}/")

def main():
    """Main analysis function"""
    print("🔍 Starting Discord Data Analysis...")
    
    # Initialize analyzer
    analyzer = DiscordDataAnalyzer()
    
    # Load data
    if not analyzer.load_data():
        print("❌ Failed to load data. Exiting.")
        return
    
    # Run all analyses
    try:
        basic_stats = analyzer.basic_statistics()
        user_stats = analyzer.user_activity_analysis() 
        temporal_data = analyzer.temporal_analysis()
        content_data = analyzer.content_analysis()
        analyzer.engagement_analysis()
        
        # Generate report
        report_file = analyzer.generate_comprehensive_report()
        
        # Export data
        analyzer.export_data_for_further_analysis()
        
        print(f"\n🎉 Analysis complete! Check {report_file} for full results.")
        
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()