#!/bin/bash
# Fix Sonic English automation issues

echo "🔧 FIXING SONIC ENGLISH AUTOMATION"
echo "=================================="

cd /Users/ll/Sandbox/SignalSifter

# Check .env file
if [ ! -f ".env" ]; then
    echo "❌ .env file not found"
    echo "💡 Creating .env file from example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env from example"
    else
        echo "Creating basic .env file..."
        cat > .env << EOF
# Telegram API credentials
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here

# Gemini API key (get from https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=your_gemini_api_key_here

# Database path
SQLITE_DB_PATH=./data/backfill.sqlite
EOF
        echo "✅ Created basic .env file"
    fi
else
    echo "✅ .env file exists"
fi

# Check if GEMINI_API_KEY is set
if grep -q "GEMINI_API_KEY=your_gemini_api_key_here" .env 2>/dev/null || ! grep -q "GEMINI_API_KEY=" .env 2>/dev/null; then
    echo ""
    echo "⚠️  GEMINI_API_KEY needs to be configured"
    echo ""
    echo "📋 Setup steps:"
    echo "   1. Go to: https://aistudio.google.com/app/apikey"
    echo "   2. Create a new API key"
    echo "   3. Edit .env file and replace 'your_gemini_api_key_here' with your actual key"
    echo ""
    echo "Example .env line:"
    echo "   GEMINI_API_KEY=AIzaSyAbCdEf1234567890..."
    echo ""
    echo "❌ Cannot run automation without valid API key"
    exit 1
else
    echo "✅ GEMINI_API_KEY appears to be configured"
fi

# Test the daily sync directly with better error handling
echo ""
echo "🧪 Testing daily sync script..."
source .venv/bin/activate

python -c "
import sys
sys.path.append('./scripts')
try:
    from daily_gemini_sync import DailyGeminiSync
    print('✅ Daily sync imports work')
except Exception as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo "✅ Scripts are properly configured"
    echo ""
    echo "🎯 Ready to run automation!"
    echo "   Run: ./sonic_standalone.sh"
else
    echo "❌ Script configuration needs attention"
    exit 1
fi