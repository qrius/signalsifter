#!/usr/bin/env python3
"""
Comprehensive Gemini Integration Status
"""

import os
import sys
import json
from datetime import datetime

def check_status():
    print("🔮 Gemini Integration Status Report")
    print("=" * 60)
    
    # 1. Check API Key
    try:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv('GEMINI_API_KEY')
        
        if api_key and api_key != 'your_api_key_here':
            print(f"✅ API Key: {api_key[:10]}...{api_key[-5:]}")
        else:
            print("❌ API Key: Not configured")
            return False
    except Exception as e:
        print(f"❌ Environment: {e}")
        return False
    
    # 2. Check Dependencies  
    try:
        import google.generativeai as genai
        print("✅ Dependencies: google-generativeai installed")
    except ImportError:
        print("❌ Dependencies: google-generativeai missing")
        print("   Run: .venv/bin/pip install google-generativeai")
        return False
    
    # 3. Check Data Files
    data_files = [
        "/Users/ll/Sandbox/SignalSifter/data/raw_messages_detailed_100.txt",
        "/Users/ll/Sandbox/SignalSifter/data/raw_messages_galactic_mining_club.txt"
    ]
    
    available_data = []
    for file_path in data_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            available_data.append((file_path, size))
            print(f"✅ Data: {os.path.basename(file_path)} ({size:,} bytes)")
        else:
            print(f"❌ Data: {os.path.basename(file_path)} not found")
    
    if not available_data:
        print("❌ No data files available for analysis")
        return False
    
    # 4. Check Demo Analysis (Already Working)
    demo_report = "/Users/ll/Sandbox/SignalSifter/data/analysis/demo_analysis_report.md"
    if os.path.exists(demo_report):
        print(f"✅ Demo Analysis: Working (see {demo_report})")
        
        # Show demo results preview
        with open(demo_report, 'r') as f:
            content = f.read()
            lines = content.split('\n')[:10]
            preview = '\n'.join(lines)
        
        print(f"\n📋 Demo Results Preview:")
        print("-" * 40)
        print(preview + "...")
        print("-" * 40)
    else:
        print("⚠️  Demo Analysis: Not found")
    
    # 5. Test API Connection
    print(f"\n🧪 Testing API Connection...")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        response = model.generate_content("Say 'Hello from Gemini!' if this works.")
        if response and response.text:
            result = response.text.strip()
            print(f"✅ API Test: {result}")
            
            # 6. Test with Real Data Sample
            print(f"\n📊 Testing with Real Data...")
            
            # Use the largest available data file
            data_file = max(available_data, key=lambda x: x[1])[0]
            
            with open(data_file, 'r', encoding='utf-8') as f:
                sample_data = f.read()[:1000]  # First 1000 chars
            
            analysis_prompt = f"""Briefly analyze this Galactic Mining Club data sample:

{sample_data}

Respond with: "Analysis: [1-2 sentences about what you see]" """
            
            analysis_response = model.generate_content(analysis_prompt)
            
            if analysis_response and analysis_response.text:
                analysis_result = analysis_response.text.strip()
                print(f"✅ Real Data Test: {analysis_result}")
                
                # Save successful test
                test_result = {
                    "timestamp": datetime.now().isoformat(),
                    "api_test": result,
                    "data_analysis": analysis_result,
                    "data_file_used": data_file,
                    "status": "success"
                }
                
                os.makedirs("/Users/ll/Sandbox/SignalSifter/data/analysis", exist_ok=True)
                result_file = "/Users/ll/Sandbox/SignalSifter/data/analysis/gemini_integration_test.json"
                
                with open(result_file, 'w') as f:
                    json.dump(test_result, f, indent=2)
                
                print(f"\n🎉 SUCCESS! Gemini integration is fully working!")
                print(f"📄 Test results saved: {result_file}")
                
                print(f"\n📋 Next Steps:")
                print("1. ✅ Demo analysis already working")
                print("2. 🔄 Run full analysis: .venv/bin/python scripts/daily_gemini_sync.py")
                print("3. ⏰ Setup automation: bash scripts/schedule_gemini_daily.sh setup")
                print("4. 📊 View results in data/analysis/")
                
                return True
                
            else:
                print("❌ Real Data Test: No response")
                return False
        else:
            print("❌ API Test: No response")
            return False
            
    except Exception as e:
        print(f"❌ API Test Failed: {e}")
        if "API_KEY" in str(e).upper():
            print("🔧 Check API key validity at: https://ai.google.dev/")
        return False

if __name__ == "__main__":
    success = check_status()
    exit(0 if success else 1)