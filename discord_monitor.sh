#!/bin/bash
"""
Discord Monitor Script for SignalSifter
Standalone monitoring script for Discord channels with cron integration and conflict checking
"""

# Set up environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | sed 's/#.*//g' | xargs)
fi

# Configuration
LOCK_FILE="/tmp/signalsifter_discord_monitor.lock"
LOG_DIR="./logs/discord"
LOG_FILE="$LOG_DIR/monitor_$(date +%Y%m%d).log"
TELEGRAM_LOCK_FILE="/tmp/signalsifter_telegram.lock"

# Channels to monitor (can be overridden by environment)
DEFAULT_CHANNELS="${DISCORD_CHANNELS:-https://discord.com/channels/1296015181985349715/1296015182417629249}"

# Monitoring settings
EXTRACTION_LIMIT=1000
TEST_MODE=${DISCORD_TEST_MODE:-false}
HEALTH_CHECK_ENABLED=${DISCORD_HEALTH_CHECK:-true}

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error logging function
log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$LOG_FILE" >&2
}

# Check if another Discord extraction is running
check_discord_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local pid=$(cat "$LOCK_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log_error "Discord extraction already running (PID: $pid)"
            return 1
        else
            log "Removing stale lock file"
            rm -f "$LOCK_FILE"
        fi
    fi
    return 0
}

# Check if Telegram extraction is running (conflict avoidance)
check_telegram_conflict() {
    if [ -f "$TELEGRAM_LOCK_FILE" ]; then
        local pid=$(cat "$TELEGRAM_LOCK_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "Telegram extraction running (PID: $pid), waiting..."
            return 1
        else
            log "Removing stale Telegram lock file"
            rm -f "$TELEGRAM_LOCK_FILE"
        fi
    fi
    return 0
}

# Create lock file
create_lock() {
    echo $$ > "$LOCK_FILE"
    log "Created lock file with PID: $$"
}

# Remove lock file
remove_lock() {
    rm -f "$LOCK_FILE"
    log "Removed lock file"
}

# Health check function
run_health_check() {
    if [ "$HEALTH_CHECK_ENABLED" = "true" ]; then
        log "Running Discord health check..."
        if python3 discord_health_check.py --quick-check; then
            log "Health check passed"
            return 0
        else
            log_error "Health check failed"
            return 1
        fi
    fi
    return 0
}

# Extract from a single channel
extract_channel() {
    local channel_url="$1"
    local is_test="$2"
    
    log "Starting extraction for: $channel_url"
    
    # Build command arguments
    local cmd_args="--url '$channel_url'"
    
    if [ "$is_test" = "true" ]; then
        cmd_args="$cmd_args --test-limit 50 --dry-run"
        log "Running in test mode (50 messages, dry-run)"
    else
        cmd_args="$cmd_args --limit $EXTRACTION_LIMIT"
        log "Running production extraction (limit: $EXTRACTION_LIMIT)"
    fi
    
    # Add verbose logging for production runs
    if [ "$is_test" != "true" ]; then
        cmd_args="$cmd_args --verbose"
    fi
    
    # Run extraction
    local start_time=$(date +%s)
    if eval "python3 discord_browser_extractor.py $cmd_args"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log "Extraction completed successfully in ${duration}s"
        
        # Run processing if not in test mode
        if [ "$is_test" != "true" ]; then
            log "Starting message processing..."
            if python3 discord_processor.py --limit 1000; then
                log "Message processing completed"
                
                # Run Gemini analysis
                log "Starting Gemini analysis..."
                if python3 scripts/gemini_analyzer.py --platform discord --channel-url "$channel_url"; then
                    log "Gemini analysis completed"
                else
                    log_error "Gemini analysis failed"
                fi
            else
                log_error "Message processing failed"
            fi
        fi
        
        return 0
    else
        log_error "Extraction failed for $channel_url"
        return 1
    fi
}

# Main monitoring function
run_monitoring() {
    local is_test="$1"
    
    # Create log directory
    mkdir -p "$LOG_DIR"
    
    log "=== Discord Monitor Started ==="
    log "Test mode: $is_test"
    log "Health check: $HEALTH_CHECK_ENABLED"
    
    # Check for conflicts
    if ! check_discord_lock; then
        exit 1
    fi
    
    # Wait for Telegram if it's running
    local wait_count=0
    while ! check_telegram_conflict; do
        sleep 30
        wait_count=$((wait_count + 1))
        if [ $wait_count -gt 10 ]; then  # Wait max 5 minutes
            log_error "Timeout waiting for Telegram extraction to complete"
            exit 1
        fi
    done
    
    # Create lock file
    create_lock
    
    # Set up cleanup on exit
    trap 'remove_lock; exit' INT TERM EXIT
    
    # Run health check
    if ! run_health_check; then
        log_error "Health check failed, aborting monitoring"
        exit 1
    fi
    
    # Process channels
    local success_count=0
    local failure_count=0
    local total_start_time=$(date +%s)
    
    # Convert channels string to array
    IFS=',' read -ra CHANNELS <<< "$DEFAULT_CHANNELS"
    
    for channel_url in "${CHANNELS[@]}"; do
        channel_url=$(echo "$channel_url" | xargs)  # Trim whitespace
        
        if [ -n "$channel_url" ]; then
            if extract_channel "$channel_url" "$is_test"; then
                success_count=$((success_count + 1))
            else
                failure_count=$((failure_count + 1))
            fi
            
            # Add delay between channels
            if [ ${#CHANNELS[@]} -gt 1 ]; then
                log "Waiting 60 seconds before next channel..."
                sleep 60
            fi
        fi
    done
    
    # Final summary
    local total_end_time=$(date +%s)
    local total_duration=$((total_end_time - total_start_time))
    
    log "=== Discord Monitor Completed ==="
    log "Total duration: ${total_duration}s"
    log "Successful extractions: $success_count"
    log "Failed extractions: $failure_count"
    log "Total channels processed: $((success_count + failure_count))"
    
    # Update SESSION_NOTES.md
    update_session_notes "$success_count" "$failure_count" "$total_duration" "$is_test"
    
    if [ $failure_count -eq 0 ]; then
        log "All extractions completed successfully"
        exit 0
    else
        log_error "Some extractions failed"
        exit 1
    fi
}

# Update SESSION_NOTES.md with monitoring results
update_session_notes() {
    local success_count="$1"
    local failure_count="$2"
    local duration="$3"
    local is_test="$4"
    
    local session_file="SESSION_NOTES.md"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local mode="production"
    
    if [ "$is_test" = "true" ]; then
        mode="test"
    fi
    
    # Create or append to session notes
    cat >> "$session_file" << EOF

## Discord Monitoring Run - $timestamp

- **Mode**: $mode
- **Duration**: ${duration}s
- **Channels processed**: $((success_count + failure_count))
- **Successful extractions**: $success_count
- **Failed extractions**: $failure_count
- **Status**: $([ $failure_count -eq 0 ] && echo "✅ Success" || echo "❌ Partial failure")

EOF
    
    log "Updated SESSION_NOTES.md"
}

# Catch-up mode for missed runs
run_catchup_mode() {
    log "=== Discord Catch-up Mode ==="
    
    # Check when last successful run was
    local last_run_file="$LOG_DIR/last_successful_run"
    local now=$(date +%s)
    local catchup_needed=false
    
    if [ -f "$last_run_file" ]; then
        local last_run=$(cat "$last_run_file")
        local hours_since_last=$(( (now - last_run) / 3600 ))
        
        if [ $hours_since_last -gt 36 ]; then  # More than 1.5 days
            log "Last successful run was ${hours_since_last} hours ago, running catch-up"
            catchup_needed=true
        fi
    else
        log "No previous run record found, running catch-up"
        catchup_needed=true
    fi
    
    if [ "$catchup_needed" = "true" ]; then
        # Run with extended extraction for catch-up
        EXTRACTION_LIMIT=2000
        run_monitoring false
        
        # Record successful run
        echo "$now" > "$last_run_file"
    else
        log "No catch-up needed"
    fi
}

# Show usage information
show_usage() {
    cat << EOF
Discord Monitor Script for SignalSifter

Usage:
    $0 [OPTIONS]

Options:
    --run               Run normal monitoring
    --test              Run in test mode (50 messages, dry-run)
    --catchup           Run catch-up mode for missed runs
    --health-check      Run health check only
    --status            Show current status
    --help              Show this help message

Environment Variables:
    DISCORD_CHANNELS    Comma-separated list of Discord channel URLs
    DISCORD_TEST_MODE   Set to 'true' for test mode
    DISCORD_HEALTH_CHECK Set to 'false' to disable health checks

Examples:
    $0 --run                    # Normal monitoring
    $0 --test                   # Test mode
    $0 --catchup                # Catch-up mode
    $0 --health-check           # Health check only

EOF
}

# Show current status
show_status() {
    echo "=== Discord Monitor Status ==="
    
    if [ -f "$LOCK_FILE" ]; then
        local pid=$(cat "$LOCK_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Status: RUNNING (PID: $pid)"
        else
            echo "Status: STALE LOCK FILE"
        fi
    else
        echo "Status: NOT RUNNING"
    fi
    
    echo "Log directory: $LOG_DIR"
    echo "Latest log: $(ls -t $LOG_DIR/monitor_*.log 2>/dev/null | head -1 || echo 'None')"
    
    if [ -f "$LOG_DIR/last_successful_run" ]; then
        local last_run=$(cat "$LOG_DIR/last_successful_run")
        local last_run_date=$(date -r "$last_run" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo 'Unknown')
        echo "Last successful run: $last_run_date"
    else
        echo "Last successful run: Never"
    fi
    
    echo "Configured channels: $DEFAULT_CHANNELS"
}

# Main script logic
main() {
    case "${1:-}" in
        --run)
            run_monitoring false
            ;;
        --test)
            run_monitoring true
            ;;
        --catchup)
            run_catchup_mode
            ;;
        --health-check)
            python3 discord_health_check.py
            ;;
        --status)
            show_status
            ;;
        --help|-h)
            show_usage
            ;;
        "")
            log_error "No command specified. Use --help for usage information."
            exit 1
            ;;
        *)
            log_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"