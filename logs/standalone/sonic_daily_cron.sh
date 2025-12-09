#!/bin/bash
# Daily Sonic English sync - runs independently
cd "/Users/ll/Sandbox/SignalSifter"
source .venv/bin/activate
python scripts/daily_gemini_sync.py --channel @Sonic_English >> logs/standalone/daily_cron.log 2>&1
