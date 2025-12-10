#!/usr/bin/env python3
"""
Discord Extraction Validation Script
Automated validation checks for week-long Discord extraction test
"""

import sqlite3
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
import argparse

class DiscordValidationChecker:
    def __init__(self, db_path="data/backfill.sqlite"):
        self.db_path = db_path
        self.validation_results = {
            "timestamp": datetime.now().isoformat(),
            "database_path": db_path,
            "checks": {},
            "summary": {},
            "passed": False
        }
    
    def connect_db(self):
        """Connect to SQLite database"""
        try:
            return sqlite3.connect(self.db_path)
        except sqlite3.Error as e:
            print(f"❌ Database connection failed: {e}")
            sys.exit(1)
    
    def check_completeness(self):
        """Check data completeness metrics"""
        print("📊 Checking data completeness...")
        
        conn = self.connect_db()
        cursor = conn.cursor()
        
        # Total message count
        cursor.execute("SELECT COUNT(*) FROM discord_messages")
        total_messages = cursor.fetchone()[0]
        
        # Messages with content
        cursor.execute("""
            SELECT COUNT(*) FROM discord_messages 
            WHERE content IS NOT NULL AND content != ''
        """)
        messages_with_content = cursor.fetchone()[0]
        
        # Unique users
        cursor.execute("""
            SELECT COUNT(DISTINCT username) FROM discord_messages 
            WHERE username != 'Unknown' AND username IS NOT NULL
        """)
        unique_users = cursor.fetchone()[0]
        
        # Date range coverage
        cursor.execute("""
            SELECT 
                MIN(DATE(timestamp)) as earliest_date,
                MAX(DATE(timestamp)) as latest_date,
                COUNT(DISTINCT DATE(timestamp)) as days_covered
            FROM discord_messages
        """)
        date_info = cursor.fetchone()
        
        conn.close()
        
        completeness = {
            "total_messages": total_messages,
            "messages_with_content": messages_with_content,
            "content_completeness_rate": (messages_with_content / total_messages * 100) if total_messages > 0 else 0,
            "unique_users": unique_users,
            "earliest_date": date_info[0],
            "latest_date": date_info[1],
            "days_covered": date_info[2]
        }
        
        self.validation_results["checks"]["completeness"] = completeness
        
        # Print results
        print(f"   Total messages: {total_messages}")
        print(f"   Messages with content: {messages_with_content} ({completeness['content_completeness_rate']:.1f}%)")
        print(f"   Unique users: {unique_users}")
        print(f"   Date range: {date_info[0]} to {date_info[1]} ({date_info[2]} days)")
        
        return completeness
    
    def check_data_quality(self):
        """Check data quality issues"""
        print("🔍 Checking data quality...")
        
        conn = self.connect_db()
        cursor = conn.cursor()
        
        # Missing critical fields
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN content = '' OR content IS NULL THEN 1 END) as empty_content,
                COUNT(CASE WHEN username = 'Unknown' OR username IS NULL THEN 1 END) as missing_usernames,
                COUNT(CASE WHEN timestamp IS NULL THEN 1 END) as missing_timestamps
            FROM discord_messages
        """)
        quality_stats = cursor.fetchone()
        
        # Check for duplicates
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT message_id, COUNT(*) as count 
                FROM discord_messages 
                GROUP BY message_id 
                HAVING COUNT(*) > 1
            )
        """)
        duplicate_count = cursor.fetchone()[0]
        
        # Content length analysis
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN LENGTH(content) < 3 AND content != '' THEN 1 END) as very_short,
                COUNT(CASE WHEN LENGTH(content) > 2000 THEN 1 END) as very_long,
                AVG(LENGTH(content)) as avg_length
            FROM discord_messages
            WHERE content != ''
        """)
        content_stats = cursor.fetchone()
        
        conn.close()
        
        quality = {
            "total_messages": quality_stats[0],
            "empty_content": quality_stats[1],
            "missing_usernames": quality_stats[2],
            "missing_timestamps": quality_stats[3],
            "duplicate_messages": duplicate_count,
            "very_short_messages": content_stats[0] if content_stats[0] else 0,
            "very_long_messages": content_stats[1] if content_stats[1] else 0,
            "average_content_length": content_stats[2] if content_stats[2] else 0
        }
        
        # Calculate rates
        total = quality["total_messages"]
        if total > 0:
            quality["empty_content_rate"] = quality["empty_content"] / total * 100
            quality["missing_username_rate"] = quality["missing_usernames"] / total * 100
            quality["duplicate_rate"] = quality["duplicate_messages"] / total * 100
        
        self.validation_results["checks"]["quality"] = quality
        
        # Print results
        print(f"   Empty content: {quality['empty_content']} ({quality.get('empty_content_rate', 0):.1f}%)")
        print(f"   Missing usernames: {quality['missing_usernames']} ({quality.get('missing_username_rate', 0):.1f}%)")
        print(f"   Duplicate messages: {quality['duplicate_messages']}")
        print(f"   Average content length: {quality['average_content_length']:.1f} chars")
        
        return quality
    
    def check_temporal_distribution(self):
        """Check message distribution over time"""
        print("📅 Checking temporal distribution...")
        
        conn = self.connect_db()
        cursor = conn.cursor()
        
        # Daily message distribution
        cursor.execute("""
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as message_count
            FROM discord_messages 
            GROUP BY DATE(timestamp)
            ORDER BY date
        """)
        daily_dist = cursor.fetchall()
        
        conn.close()
        
        temporal = {
            "daily_distribution": [{"date": row[0], "count": row[1]} for row in daily_dist],
            "total_days": len(daily_dist),
            "days_with_messages": len([d for d in daily_dist if d[1] > 0])
        }
        
        self.validation_results["checks"]["temporal"] = temporal
        
        print(f"   Days with messages: {temporal['days_with_messages']}/{temporal['total_days']}")
        for day in daily_dist[:7]:  # Show up to 7 days
            print(f"     {day[0]}: {day[1]} messages")
        
        return temporal
    
    def sample_content_review(self, limit=5):
        """Sample recent messages for manual review"""
        print("🔍 Sampling content for review...")
        
        conn = self.connect_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                username,
                SUBSTR(content, 1, 100) as content_preview,
                timestamp,
                LENGTH(content) as content_length
            FROM discord_messages 
            WHERE content != '' AND content IS NOT NULL
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        samples = cursor.fetchall()
        conn.close()
        
        sample_data = []
        for sample in samples:
            sample_info = {
                "username": sample[0],
                "content_preview": sample[1],
                "timestamp": sample[2],
                "content_length": sample[3]
            }
            sample_data.append(sample_info)
            print(f"   [{sample[2]}] {sample[0]}: {sample[1][:50]}... ({sample[3]} chars)")
        
        self.validation_results["checks"]["content_samples"] = sample_data
        return sample_data
    
    def evaluate_success_criteria(self):
        """Evaluate against defined success criteria"""
        print("\n🎯 Evaluating success criteria...")
        
        completeness = self.validation_results["checks"]["completeness"]
        quality = self.validation_results["checks"]["quality"]
        temporal = self.validation_results["checks"]["temporal"]
        
        criteria = {
            "critical": {},
            "quality": {},
            "excellence": {}
        }
        
        # Critical criteria (must have)
        criteria["critical"]["message_count"] = completeness["total_messages"] >= 50
        criteria["critical"]["content_completeness"] = completeness["content_completeness_rate"] >= 80
        criteria["critical"]["username_accuracy"] = quality.get("missing_username_rate", 100) <= 10
        criteria["critical"]["date_coverage"] = temporal["days_with_messages"] >= 5
        criteria["critical"]["no_critical_errors"] = quality["missing_timestamps"] == 0
        
        # Quality criteria (should have)
        criteria["quality"]["good_message_count"] = completeness["total_messages"] >= 100
        criteria["quality"]["excellent_content"] = completeness["content_completeness_rate"] >= 95
        criteria["quality"]["low_duplicates"] = quality.get("duplicate_rate", 0) <= 5
        
        # Excellence criteria (nice to have)
        criteria["excellence"]["rich_content"] = quality["average_content_length"] >= 20
        criteria["excellence"]["consistent_daily"] = temporal["days_with_messages"] >= 7
        
        # Calculate overall success
        critical_passed = all(criteria["critical"].values())
        quality_passed = sum(criteria["quality"].values()) >= 2  # At least 2 of 3
        
        overall_success = critical_passed and quality_passed
        
        self.validation_results["checks"]["success_criteria"] = criteria
        self.validation_results["passed"] = overall_success
        
        # Print results
        print(f"   Critical criteria: {'✅ PASSED' if critical_passed else '❌ FAILED'}")
        for key, passed in criteria["critical"].items():
            print(f"     {key}: {'✅' if passed else '❌'}")
        
        print(f"   Quality criteria: {'✅ PASSED' if quality_passed else '❌ PARTIAL'}")
        for key, passed in criteria["quality"].items():
            print(f"     {key}: {'✅' if passed else '❌'}")
        
        return overall_success
    
    def generate_report(self, output_file=None):
        """Generate validation report"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"validation_report_{timestamp}.json"
        
        # Add summary
        completeness = self.validation_results["checks"]["completeness"]
        quality = self.validation_results["checks"]["quality"]
        
        self.validation_results["summary"] = {
            "overall_status": "PASSED" if self.validation_results["passed"] else "FAILED",
            "total_messages": completeness["total_messages"],
            "content_completeness": f"{completeness['content_completeness_rate']:.1f}%",
            "unique_users": completeness["unique_users"],
            "date_range": f"{completeness['earliest_date']} to {completeness['latest_date']}",
            "days_covered": completeness["days_covered"],
            "data_quality_score": f"{100 - quality.get('empty_content_rate', 0) - quality.get('missing_username_rate', 0):.1f}%"
        }
        
        with open(output_file, 'w') as f:
            json.dump(self.validation_results, f, indent=2)
        
        print(f"\n📄 Validation report saved to: {output_file}")
        return output_file
    
    def run_full_validation(self):
        """Run complete validation suite"""
        print("🚀 Starting Discord extraction validation...\n")
        
        try:
            self.check_completeness()
            print()
            self.check_data_quality()
            print()
            self.check_temporal_distribution()
            print()
            self.sample_content_review()
            print()
            success = self.evaluate_success_criteria()
            
            report_file = self.generate_report()
            
            print(f"\n{'='*60}")
            print(f"🎯 VALIDATION RESULT: {'PASSED ✅' if success else 'FAILED ❌'}")
            print(f"📊 Total Messages: {self.validation_results['checks']['completeness']['total_messages']}")
            print(f"📄 Report: {report_file}")
            print(f"{'='*60}")
            
            return success
            
        except Exception as e:
            print(f"❌ Validation failed with error: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Validate Discord extraction data")
    parser.add_argument("--db", default="data/backfill.sqlite", help="Database path")
    parser.add_argument("--output", help="Output report file")
    parser.add_argument("--quick", action="store_true", help="Quick validation (skip samples)")
    
    args = parser.parse_args()
    
    validator = DiscordValidationChecker(args.db)
    
    if args.quick:
        print("🔄 Running quick validation...")
        validator.check_completeness()
        validator.check_data_quality()
        success = validator.evaluate_success_criteria()
        validator.generate_report(args.output)
    else:
        success = validator.run_full_validation()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()