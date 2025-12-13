# Discord Extraction System - Quick Start Guide

## Prerequisites

1. **Environment Setup**:
   ```bash
   # Install dependencies
   pip install playwright>=1.40.0 fake-useragent>=1.4.0 beautifulsoup4>=4.12.0 pandas>=2.1.0
   
   # Install Playwright browser
   python -m playwright install chromium
   ```

2. **Configure Discord Credentials** in `.env`:
   ```
   DISCORD_EMAIL=your_discord_email
   DISCORD_PASSWORD=your_discord_password
   DISCORD_CHANNELS=https://discord.com/channels/1296015181985349715/1296015182417629249
   ```

## ⚠️ Project Status: Experimental

**Note:** This Discord extraction system is currently **experimental**. See [DISCORD_EXTRACTION_SUMMARY.md](DISCORD_EXTRACTION_SUMMARY.md) for detailed analysis of approaches attempted.

**Current Status:**
- ✅ Browser automation working but unreliable
- ❌ Commercial tool integration failed
- 📊 Successfully extracted 3,400+ messages for proof-of-concept
- 🔄 Requires manual intervention for production use

**For Production Use:** Consider Discord's official API or bot integration instead.

## Quick Test (Recommended First Step)

```bash
# Test with dry-run mode (doesn't save to database)
python discord_browser_extractor.py --url "https://discord.com/channels/1296015181985349715/1296015182417629249" --test-limit 50 --dry-run --verbose

# Test health check
python discord_health_check.py --quick-check
```

## Production Usage

### 1. Individual Components

```bash
# Browser extraction (6 months historical)
python discord_browser_extractor.py --url "https://discord.com/channels/1296015181985349715/1296015182417629249" --months 6

# Message processing
python discord_processor.py --limit 500

# Gemini analysis
python scripts/gemini_analyzer.py --platform discord --channel-url "https://discord.com/channels/1296015181985349715/1296015182417629249"
```

### 2. Full Pipeline

```bash
# Complete pipeline (extraction → processing → analysis)
python run_discord_pipeline.py --url "https://discord.com/channels/1296015181985349715/1296015182417629249" --months 6 --full-pipeline

# Test mode
python run_discord_pipeline.py --url "https://discord.com/channels/1296015181985349715/1296015182417629249" --test-mode --dry-run
```

### 3. Monitoring & Automation

```bash
# Manual monitoring run
./discord_monitor.sh --run

# Test monitoring
./discord_monitor.sh --test

# Check status
./discord_monitor.sh --status

# Health check
python discord_health_check.py --full-check
```

## Cron Automation

Add to crontab (`crontab -e`):
```bash
# Daily monitoring at 3 AM
0 3 * * * /Users/ll/Sandbox/SignalSifter/discord_monitor.sh --run

# Health checks every 6 hours  
0 */6 * * * cd /Users/ll/Sandbox/SignalSifter && python3 discord_health_check.py --quick-check
```

## Database Schema

The system creates these tables:
- `discord_servers` - Server information
- `discord_channels` - Channel metadata  
- `discord_messages` - Message content and metadata
- `discord_entities` - Extracted entities (contracts, URLs, etc.)
- `discord_extraction_log` - Extraction progress tracking
- `discord_status` - Channel monitoring status

## Key Features

- **Browser Automation**: Playwright-based extraction with anti-detection
- **Rate Limiting**: Configurable delays (default: 1000 messages/hour)
- **Resume Capability**: Continues from last extracted message
- **Health Monitoring**: UI change detection and automation validation
- **Entity Extraction**: Contracts, URLs, mentions, reactions, embeds
- **Gemini Integration**: Automated AI analysis pipeline
- **Conflict Avoidance**: Won't run with Telegram extraction simultaneously

## Troubleshooting

1. **Login Issues**: Check Discord credentials in `.env`
2. **Rate Limiting**: Reduce extraction rate or enable longer delays
3. **UI Changes**: Run health check to detect Discord interface changes
4. **Browser Issues**: Ensure Playwright Chromium is installed
5. **Database Issues**: Check SQLite file permissions and disk space

## Files Created

- **Logs**: `./logs/discord/` - Extraction and health check logs
- **Database**: `./data/backfill.sqlite` - SQLite database with Discord tables
- **Browser Profile**: `~/.SignalSifter/discord_browser_profile/` - Persistent browser session
- **Health Data**: `./logs/discord/selector_health.json` - UI health status