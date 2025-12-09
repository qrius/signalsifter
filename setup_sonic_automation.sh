#!/bin/bash
# Setup incremental automation for Sonic English channel

echo "🔧 Setting up incremental Sonic English automation..."

cd /Users/ll/Sandbox/SignalSifter

# Run daily sync for Sonic English
echo "📥 Running incremental sync for @Sonic_English..."
.venv/bin/python scripts/daily_gemini_sync.py --channel @Sonic_English

# Setup automated daily sync (runs at 2 AM daily)
echo "⏰ Setting up daily cron job..."
bash scripts/schedule_gemini_daily.sh @Sonic_English

echo "✅ Automation setup complete!"
echo "📊 Daily incremental updates will:"
echo "   - Extract new messages since last export"
echo "   - Generate updated Gemini analysis"
echo "   - Respect API rate limits (2 req/min, 50/day)"
echo "   - Log all operations"
echo ""
echo "📁 Results will be updated in: data/sonic_english/"
echo "📋 Check status with: bash scripts/schedule_gemini_daily.sh status"