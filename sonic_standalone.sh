#!/bin/bash
# Standalone Sonic English automation script for iTerm2/external terminals
# This runs independently of VS Code and survives project switching

set -e

# Get the absolute path to the SignalSifter project
# If running from within SignalSifter directory
if [ -f "./sonic_standalone.sh" ] && [ -f "./.venv/bin/activate" ]; then
    PROJECT_ROOT="$(pwd)"
else
    # Use script location
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$SCRIPT_DIR"
fi

echo "🚀 SONIC ENGLISH STANDALONE AUTOMATION"
echo "======================================"
echo "📁 Project: $PROJECT_ROOT"
echo "⚙️  Running independently of VS Code..."
echo ""

# Change to project directory
cd "$PROJECT_ROOT"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    echo "🔧 Activating Python virtual environment..."
    source .venv/bin/activate
else
    echo "❌ Virtual environment not found at $PROJECT_ROOT/.venv"
    echo "💡 Please run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if we have necessary dependencies
echo "📦 Checking dependencies..."
python -c "import telethon, google.generativeai" 2>/dev/null || {
    echo "❌ Missing dependencies. Installing..."
    pip install -r requirements.txt
}

# Create logs directory for external runs
mkdir -p logs/standalone

# Function to run incremental sync
run_incremental_sync() {
    echo "📥 Running incremental message extraction..."
    
    # Run with output to both console and log file
    python scripts/daily_gemini_sync.py --channel @Sonic_English 2>&1 | tee logs/standalone/sonic_sync_$(date +%Y%m%d_%H%M%S).log
    
    local exit_code=${PIPESTATUS[0]}
    if [ $exit_code -eq 0 ]; then
        echo "✅ Incremental sync completed successfully"
        return 0
    else
        echo "❌ Incremental sync failed with exit code: $exit_code"
        return $exit_code
    fi
}

# Function to setup automated daily runs
setup_automation() {
    echo "⏰ Setting up daily automation..."
    
    # Create a standalone cron script
    cat > logs/standalone/sonic_daily_cron.sh << EOF
#!/bin/bash
# Daily Sonic English sync - runs independently
cd "$PROJECT_ROOT"
source .venv/bin/activate
python scripts/daily_gemini_sync.py --channel @Sonic_English >> logs/standalone/daily_cron.log 2>&1
EOF
    
    chmod +x logs/standalone/sonic_daily_cron.sh
    
    # Show cron setup instructions
    echo ""
    echo "📋 To setup daily automation, add this to your crontab:"
    echo "   crontab -e"
    echo ""
    echo "   Add this line (runs daily at 2 AM):"
    echo "   0 2 * * * $PROJECT_ROOT/logs/standalone/sonic_daily_cron.sh"
    echo ""
    echo "📁 Cron script created at: logs/standalone/sonic_daily_cron.sh"
    echo "📊 Cron logs will go to: logs/standalone/daily_cron.log"
}

# Function to run in background with nohup
run_background() {
    echo "🔄 Running in background (survives terminal close)..."
    
    # Create background script
    cat > logs/standalone/background_sync.sh << EOF
#!/bin/bash
cd "$PROJECT_ROOT"
source .venv/bin/activate

while true; do
    echo "\$(date): Starting Sonic English sync..."
    python scripts/daily_gemini_sync.py --channel @Sonic_English
    
    if [ \$? -eq 0 ]; then
        echo "\$(date): Sync completed successfully"
    else
        echo "\$(date): Sync failed, retrying in 1 hour..."
    fi
    
    # Wait 24 hours before next sync
    sleep 86400
done
EOF
    
    chmod +x logs/standalone/background_sync.sh
    
    # Run in background with nohup
    nohup logs/standalone/background_sync.sh > logs/standalone/background.log 2>&1 &
    local bg_pid=$!
    
    echo "✅ Background process started with PID: $bg_pid"
    echo "📊 Monitor with: tail -f logs/standalone/background.log"
    echo "🛑 Stop with: kill $bg_pid"
    echo ""
    echo "📋 Process info saved to: logs/standalone/background_pid.txt"
    echo "$bg_pid" > logs/standalone/background_pid.txt
}

# Function to check status
check_status() {
    echo "📊 SONIC ENGLISH AUTOMATION STATUS"
    echo "=================================="
    
    # Check if background process is running
    if [ -f "logs/standalone/background_pid.txt" ]; then
        local pid=$(cat logs/standalone/background_pid.txt)
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "✅ Background sync running (PID: $pid)"
        else
            echo "❌ Background sync not running"
        fi
    else
        echo "ℹ️  No background sync configured"
    fi
    
    # Show recent log entries
    echo ""
    echo "📋 Recent activity:"
    if [ -f "logs/standalone/background.log" ]; then
        tail -5 logs/standalone/background.log
    else
        echo "   No background activity logs found"
    fi
    
    # Check database status
    echo ""
    echo "💾 Database status:"
    if [ -f "data/backfill.sqlite" ]; then
        local msg_count=$(sqlite3 data/backfill.sqlite "SELECT COUNT(*) FROM messages WHERE channel_id = '1369376451';" 2>/dev/null || echo "Error")
        echo "   Messages in database: $msg_count"
        
        local latest_msg=$(sqlite3 data/backfill.sqlite "SELECT date FROM messages WHERE channel_id = '1369376451' ORDER BY date DESC LIMIT 1;" 2>/dev/null || echo "Error")
        echo "   Latest message: $latest_msg"
    else
        echo "   Database not found"
    fi
}

# Function to stop background process
stop_background() {
    if [ -f "logs/standalone/background_pid.txt" ]; then
        local pid=$(cat logs/standalone/background_pid.txt)
        if ps -p "$pid" > /dev/null 2>&1; then
            kill "$pid"
            echo "✅ Background process stopped (PID: $pid)"
            rm logs/standalone/background_pid.txt
        else
            echo "ℹ️  Background process not running"
        fi
    else
        echo "ℹ️  No background process configured"
    fi
}

# Main menu
echo "🎛️  Choose an option:"
echo "   1) Run one-time incremental sync"
echo "   2) Setup daily automation (cron)"  
echo "   3) Start background sync (continuous)"
echo "   4) Check status"
echo "   5) Stop background sync"
echo ""

read -p "Enter choice (1-5): " choice

case $choice in
    1)
        run_incremental_sync
        ;;
    2)
        setup_automation
        ;;
    3)
        run_background
        ;;
    4)
        check_status
        ;;
    5)
        stop_background
        ;;
    *)
        echo "❌ Invalid choice. Please run again and select 1-5."
        exit 1
        ;;
esac

echo ""
echo "🎯 Standalone automation ready!"
echo "📁 All logs in: $PROJECT_ROOT/logs/standalone/"