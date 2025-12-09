#!/usr/bin/env zsh
# Schedule daily Gemini analysis for Telegram channels
# Usage: ./scripts/schedule_gemini_daily.sh [channel_name]

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
VENV_PATH="$PROJECT_ROOT/.venv"
CHANNEL="${1:-@Galactic_Mining_Club}"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

echo_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check if we're within API limits
check_api_limits() {
    local channel="$1"
    echo_info "Checking daily API usage limits..."
    
    cd "$PROJECT_ROOT"
    source "$VENV_PATH/bin/activate"
    
    # Get usage stats
    local stats_output
    if stats_output=$(.venv/bin/python scripts/daily_gemini_sync.py --channel "$channel" --stats 2>&1); then
        echo "$stats_output"
        
        # Extract remaining requests from output
        local remaining
        remaining=$(echo "$stats_output" | grep "API requests remaining" | grep -o '[0-9]*' | head -1)
        
        if [[ -n "$remaining" && "$remaining" -gt 0 ]]; then
            echo_success "API requests available: $remaining"
            return 0
        else
            echo_warning "Daily API limit reached or exceeded"
            return 1
        fi
    else
        echo_error "Failed to check API usage: $stats_output"
        return 1
    fi
}

# Function to run daily analysis
run_daily_analysis() {
    local channel="$1"
    local timestamp=$(date +"%Y-%m-%d_%H%M%S")
    local log_file="$LOG_DIR/gemini_daily_${timestamp}.log"
    
    echo_info "Starting daily Gemini analysis for: $channel"
    echo_info "Log file: $log_file"
    
    cd "$PROJECT_ROOT"
    source "$VENV_PATH/bin/activate"
    
    # Run the analysis with comprehensive logging
    {
        echo "=== Daily Gemini Analysis Started: $(date) ==="
        echo "Channel: $channel"
        echo "Project: $PROJECT_ROOT"
        echo ""
        
        # Run with timeout (30 minutes max)
        if timeout 1800 .venv/bin/python scripts/daily_gemini_sync.py --channel "$channel"; then
            echo ""
            echo "=== Analysis Completed Successfully: $(date) ==="
            echo_success "Daily analysis completed for $channel"
            return 0
        else
            local exit_code=$?
            echo ""
            echo "=== Analysis Failed: $(date) ==="
            echo "Exit code: $exit_code"
            
            if [[ $exit_code -eq 124 ]]; then
                echo_error "Analysis timed out (30 minutes limit)"
            else
                echo_error "Analysis failed with exit code: $exit_code"
            fi
            return $exit_code
        fi
    } 2>&1 | tee "$log_file"
}

# Function to setup cron job
setup_cron_job() {
    local channel="$1"
    local cron_time="${2:-0 9}"  # Default: 9 AM daily
    
    echo_info "Setting up cron job for daily analysis..."
    echo_info "Schedule: $cron_time * * * (daily at specified time)"
    echo_info "Channel: $channel"
    
    # Create cron command
    local cron_cmd="$cron_time * * * cd $PROJECT_ROOT && $PROJECT_ROOT/scripts/schedule_gemini_daily.sh '$channel' >> $LOG_DIR/cron.log 2>&1"
    
    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "schedule_gemini_daily.sh"; then
        echo_warning "Cron job already exists for Gemini daily analysis"
        echo_info "Current cron jobs containing 'schedule_gemini_daily.sh':"
        crontab -l 2>/dev/null | grep "schedule_gemini_daily.sh" || true
        
        echo ""
        echo "To update, run:"
        echo "  crontab -e"
        echo "And modify the line to:"
        echo "  $cron_cmd"
    else
        # Add to existing crontab
        (crontab -l 2>/dev/null; echo "$cron_cmd") | crontab -
        echo_success "Cron job added successfully!"
        echo_info "Daily analysis will run at: $cron_time (24-hour format)"
    fi
    
    echo ""
    echo_info "Current crontab:"
    crontab -l 2>/dev/null || echo "No cron jobs found"
}

# Function to remove cron job
remove_cron_job() {
    echo_info "Removing Gemini daily analysis cron job..."
    
    if crontab -l 2>/dev/null | grep -q "schedule_gemini_daily.sh"; then
        # Remove lines containing our script
        (crontab -l 2>/dev/null | grep -v "schedule_gemini_daily.sh") | crontab -
        echo_success "Cron job removed successfully"
    else
        echo_warning "No cron job found for Gemini daily analysis"
    fi
}

# Function to show recent logs
show_logs() {
    local num_lines="${1:-50}"
    
    echo_info "Recent Gemini analysis logs (last $num_lines lines):"
    echo ""
    
    # Find most recent log file
    local latest_log
    latest_log=$(find "$LOG_DIR" -name "gemini_daily_*.log" -type f -exec ls -t {} + 2>/dev/null | head -1)
    
    if [[ -n "$latest_log" && -f "$latest_log" ]]; then
        echo_info "Latest log file: $(basename "$latest_log")"
        echo "----------------------------------------"
        tail -n "$num_lines" "$latest_log"
    else
        echo_warning "No log files found in $LOG_DIR"
    fi
}

# Function to show usage
show_usage() {
    cat << EOF
Schedule daily Gemini analysis for Telegram channels

Usage: 
  $0 [channel_name]                    # Run analysis now
  $0 --setup [channel] [time]          # Setup cron job (time: "0 9" for 9 AM)  
  $0 --remove                          # Remove cron job
  $0 --logs [num_lines]                # Show recent logs
  $0 --status [channel]                # Check API usage status
  $0 --help                           # Show this help

Examples:
  $0 @Galactic_Mining_Club            # Run analysis now
  $0 --setup @Galactic_Mining_Club "0 9"  # Setup daily at 9 AM
  $0 --setup @Galactic_Mining_Club "30 14" # Setup daily at 2:30 PM
  $0 --logs 100                       # Show last 100 log lines
  $0 --status @Galactic_Mining_Club   # Check today's API usage

Environment:
  Requires GEMINI_API_KEY in .env file
  Logs stored in: $LOG_DIR
  Virtual environment: $VENV_PATH

EOF
}

# Main script logic
case "${1:-}" in
    --setup)
        setup_cron_job "${2:-@Galactic_Mining_Club}" "${3:-0 9}"
        ;;
    --remove)
        remove_cron_job
        ;;
    --logs)
        show_logs "${2:-50}"
        ;;
    --status)
        check_api_limits "${2:-@Galactic_Mining_Club}"
        ;;
    --help|-h)
        show_usage
        ;;
    "")
        # Default: run analysis for Galactic_Mining_Club
        CHANNEL="@Galactic_Mining_Club"
        echo_info "No channel specified, using default: $CHANNEL"
        
        if check_api_limits "$CHANNEL"; then
            run_daily_analysis "$CHANNEL"
        else
            echo_error "Skipping analysis due to API limits"
            exit 1
        fi
        ;;
    --*)
        echo_error "Unknown option: $1"
        show_usage
        exit 1
        ;;
    *)
        # Channel specified
        if check_api_limits "$1"; then
            run_daily_analysis "$1"
        else
            echo_error "Skipping analysis due to API limits"
            exit 1
        fi
        ;;
esac