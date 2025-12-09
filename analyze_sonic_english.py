#!/usr/bin/env python3
"""
Sonic English Channel Analysis with Gemini AI
Process 6 months of data from https://t.me/Sonic_English
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

def analyze_sonic_english_data():
    """Analyze Sonic English channel data with Gemini AI."""
    
    print("🎵 Sonic English Channel Analysis")
    print("=" * 60)
    
    # Load environment
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        print("❌ GEMINI_API_KEY not found in .env file")
        return False
    
    print(f"🔑 API Key loaded: {api_key[:10]}...{api_key[-5:]}")
    
    try:
        import google.generativeai as genai
        print("✅ Google Generative AI imported")
        
        # Configure API
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Check for extracted data
        data_paths = [
            "/Users/ll/Sandbox/SignalSifter/data/sonic_english/channel_@Sonic_English_summary.md",
            "/Users/ll/Sandbox/SignalSifter/data/sonic_english_summary.md",
            "/Users/ll/Sandbox/SignalSifter/data/backfill.sqlite"
        ]
        
        # For now, use a sample analysis until extraction completes
        print("📊 Preparing Sonic English analysis framework...")
        
        # Create Sonic-specific analysis prompt
        analysis_prompt = """You are an expert cryptocurrency and blockchain community analyst specializing in Sonic Protocol analysis.

Sonic Protocol is a high-performance blockchain platform focused on:
- Ultra-fast transaction processing
- DeFi ecosystem development  
- Gaming and NFT infrastructure
- Developer-friendly tools and APIs

When analyzing Sonic English community data, focus on:

## Technical Development
- Protocol updates and improvements
- Developer activity and tools
- Network performance metrics
- Integration partnerships

## DeFi Ecosystem
- DEX trading activity
- Liquidity pool developments
- Yield farming opportunities
- Token economics discussions

## Gaming & NFTs
- Game development updates
- NFT marketplace activity
- Gaming partnerships
- User acquisition metrics

## Community Engagement
- Developer onboarding
- Educational content
- Community governance
- Partnership announcements

## Market Analysis
- SONIC token price movements
- Trading volume patterns
- Exchange listings
- Market sentiment indicators

Provide insights with specific citations using exact timestamps: [YYYY-MM-DD HH:MM:SS UTC] @username"""

        # Save analysis framework
        os.makedirs("/Users/ll/Sandbox/SignalSifter/data/sonic_english", exist_ok=True)
        
        framework = {
            "channel": "@Sonic_English",
            "url": "https://t.me/Sonic_English", 
            "extraction_period": "2024-06-10 to 2025-12-07",
            "analysis_focus": [
                "Technical development updates",
                "DeFi ecosystem growth",
                "Gaming and NFT developments", 
                "Community engagement patterns",
                "SONIC token market analysis"
            ],
            "analysis_prompt": analysis_prompt,
            "created": datetime.now().isoformat()
        }
        
        framework_file = "/Users/ll/Sandbox/SignalSifter/data/sonic_english/analysis_framework.json"
        with open(framework_file, 'w') as f:
            json.dump(framework, f, indent=2)
        
        print(f"📄 Analysis framework saved: {framework_file}")
        
        # Test with sample Sonic-related content
        sample_test = """[2024-12-07 10:00:00 UTC] @SonicDev: New Sonic Protocol update v2.1 is live! 🚀
        
Features:
- 50% faster transaction processing
- Enhanced DeFi integration
- New gaming SDK release
- Cross-chain bridge improvements

[2024-12-07 10:15:00 UTC] @CommunityMember: This is huge for gaming projects! When can we expect the NFT marketplace upgrade?

[2024-12-07 10:20:00 UTC] @SonicTeam: NFT marketplace v3 launches next week with:
- Zero-fee minting for verified creators
- Advanced royalty management
- Multi-chain support
- Gaming asset integration"""

        print(f"\n🧪 Testing analysis with sample Sonic content...")
        
        test_response = model.generate_content(f"{analysis_prompt}\n\nAnalyze this sample:\n\n{sample_test}")
        
        if test_response and test_response.text:
            print(f"✅ Test Analysis:")
            print("-" * 50)
            print(test_response.text[:400] + "...")
            print("-" * 50)
            
            # Save test results
            test_result = {
                "timestamp": datetime.now().isoformat(),
                "test_analysis": test_response.text,
                "sample_content": sample_test,
                "status": "ready_for_real_data"
            }
            
            test_file = "/Users/ll/Sandbox/SignalSifter/data/sonic_english/gemini_test.json"
            with open(test_file, 'w') as f:
                json.dump(test_result, f, indent=2)
            
            print(f"📄 Test results saved: {test_file}")
            print(f"\n🎉 Sonic English analysis ready!")
            print(f"⏳ Waiting for data extraction to complete...")
            print(f"📋 Next: Run full analysis once extraction finishes")
            
            return True
        else:
            print("❌ Test analysis failed")
            return False
            
    except Exception as e:
        print(f"❌ Analysis setup failed: {e}")
        return False

def check_extraction_progress():
    """Check progress of Sonic English data extraction."""
    
    print("\n📈 Checking Extraction Progress...")
    
    # Check database for Sonic English data
    db_path = "/Users/ll/Sandbox/SignalSifter/data/backfill.sqlite"
    
    if os.path.exists(db_path):
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            
            # Check for Sonic English channel
            cur.execute("SELECT tg_id, username, title FROM channels WHERE username LIKE '%Sonic%' OR title LIKE '%Sonic%'")
            channels = cur.fetchall()
            
            if channels:
                print("✅ Sonic channels found in database:")
                for tg_id, username, title in channels:
                    print(f"  - {username or 'N/A'}: {title} (ID: {tg_id})")
                    
                    # Count messages
                    cur.execute("SELECT COUNT(*) FROM messages WHERE channel_id = ?", (tg_id,))
                    msg_count = cur.fetchone()[0]
                    print(f"    Messages: {msg_count:,}")
            else:
                print("⏳ Sonic English channel not yet in database (extraction in progress)")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Database check failed: {e}")
    else:
        print("⏳ Database not yet created (extraction starting)")

def main():
    """Main execution function."""
    
    # Setup analysis framework
    framework_ready = analyze_sonic_english_data()
    
    if framework_ready:
        # Check extraction progress
        check_extraction_progress()
        
        print(f"\n📋 Summary:")
        print("✅ Gemini analysis framework ready for Sonic English")
        print("⏳ Data extraction in progress (6 months from Sonic_English)")
        print("🎯 Ready for comprehensive blockchain community analysis")
        print(f"\nNext steps:")
        print("1. Wait for extraction to complete")
        print("2. Run: .venv/bin/python analyze_sonic_english.py --full-analysis")
        print("3. Review: data/sonic_english/sonic_comprehensive_analysis.json")
        
        return True
    else:
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)