#!/bin/bash
# Quick test of Sonic English automation setup

cd /Users/ll/Sandbox/SignalSifter

echo "🚀 SONIC ENGLISH AUTOMATION - STATUS CHECK"
echo "=========================================="

# Check virtual environment
if [ -f ".venv/bin/activate" ]; then
    echo "✅ Virtual environment found"
    source .venv/bin/activate
else
    echo "❌ Virtual environment not found"
    exit 1
fi

# Check dependencies
echo "📦 Checking dependencies..."
python -c "import telethon, google.generativeai" 2>/dev/null && echo "✅ Dependencies installed" || echo "❌ Missing dependencies"

# Check database
if [ -f "data/backfill.sqlite" ]; then
    echo "✅ Database found"
    msg_count=$(sqlite3 data/backfill.sqlite "SELECT COUNT(*) FROM messages WHERE channel_id = '1369376451';" 2>/dev/null || echo "Error")
    echo "   Messages in database: $msg_count"
else
    echo "❌ Database not found"
fi

# Check output directories
echo "📁 Output directories:"
[ -d "data/gemini_analysis" ] && echo "   ✅ data/gemini_analysis/" || echo "   ❌ data/gemini_analysis/ (will be created)"
[ -d "data/sonic_english" ] && echo "   ✅ data/sonic_english/" || echo "   ❌ data/sonic_english/"
[ -d "logs/standalone" ] && echo "   ✅ logs/standalone/" || echo "   ❌ logs/standalone/ (will be created)"

echo ""
echo "🎯 Ready to run automation!"
echo "   Run: ./sonic_standalone.sh"
echo "   Choose option 1 for one-time sync"
echo "   Choose option 3 for background sync"