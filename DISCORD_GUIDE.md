# Discord Extraction System - Complete Guide

## Overview

The SignalSifter Discord extraction system provides comprehensive message extraction from Discord channels using browser automation. It's designed to handle various Discord features including message threading, reactions, embeds, and media attachments.

## System Architecture

```
Discord Browser Extractor
├── Authentication Layer (discord_browser_extractor.py)
├── Database Schema (discord_db_schema.py) 
├── Message Processing (discord_processor.py)
├── Health Monitoring (discord_health_check.py)
├── Automation Scripts (discord_monitor.sh)
└── Analysis Pipeline (scripts/discord_gemini_analyzer.py)
```

## Installation & Setup

### 1. Environment Setup

```bash
# Create isolated Python environment
python3 -m venv signalsifter-env
source signalsifter-env/bin/activate

# Install required packages
pip install playwright telethon python-dotenv fake-useragent beautifulsoup4 pandas

# Install Playwright browser
python -m playwright install chromium
```

### 2. Configuration

Add Discord credentials to your `.env` file:

```bash
# Discord Browser Automation Credentials
DISCORD_EMAIL=your_email@example.com
DISCORD_PASSWORD=your_discord_password

# Discord Monitoring Configuration
DISCORD_CHANNELS=https://discord.com/channels/SERVER_ID/CHANNEL_ID
DISCORD_TEST_MODE=false
DISCORD_HEALTH_CHECK=true
```

## Usage Examples

### Basic Message Extraction

```bash
# Extract 3 months of messages
python discord_browser_extractor.py \
  --url "https://discord.com/channels/1296015181985349715/1296015182417629249" \
  --months 3 \
  --verbose

# Extract specific number of messages
python discord_browser_extractor.py \
  --url "https://discord.com/channels/SERVER_ID/CHANNEL_ID" \
  --limit 1000 \
  --verbose
```

### Advanced Options

```bash
# Headless extraction for automation
python discord_browser_extractor.py \
  --url "CHANNEL_URL" \
  --months 6 \
  --headless \
  --verbose

# Dry run (no database storage)
python discord_browser_extractor.py \
  --url "CHANNEL_URL" \
  --limit 100 \
  --dry-run \
  --verbose

# Test extraction (limited messages)
python discord_browser_extractor.py \
  --url "CHANNEL_URL" \
  --test-limit 50 \
  --verbose
```

## Database Schema

The Discord system uses a comprehensive SQLite schema:

### Tables

1. **discord_servers**: Server/guild information
2. **discord_channels**: Channel metadata and settings
3. **discord_messages**: Message content, reactions, embeds
4. **discord_extraction_log**: Process tracking and resume support
5. **discord_status**: System health and monitoring

### Relationships

- Messages → Channels (foreign key)
- Channels → Servers (foreign key)  
- Extraction logs → Channels (foreign key)
- Proper indexing for performance

## Features

### Authentication
- **Automatic Login**: Uses stored credentials for seamless access
- **2FA Support**: Falls back to manual intervention when needed
- **Session Persistence**: Maintains login state across runs
- **Security**: Uses persistent browser profiles for authentication

### Anti-Detection
- **Human-like Behavior**: Random delays and realistic interaction patterns
- **User Agent Rotation**: Dynamic user agent strings
- **Rate Limiting**: Configurable message extraction rates
- **Stealth Mode**: Removes automation indicators

### Data Extraction
- **Complete Messages**: Content, timestamps, author information
- **Rich Media**: Embeds, attachments, reactions
- **Thread Support**: Message threading and reply chains
- **Metadata**: Edit history, pin status, mentions

### Error Handling
- **Resume Support**: Continue interrupted extractions
- **Graceful Failures**: Handle network issues and rate limits
- **Comprehensive Logging**: Detailed logs for debugging
- **Status Monitoring**: Real-time health checks

## Automation

### Cron Integration

Use `discord_monitor.sh` for scheduled extractions:

```bash
# Make executable
chmod +x discord_monitor.sh

# Add to crontab for daily extraction at 2 AM
0 2 * * * /path/to/SignalSifter/discord_monitor.sh
```

### Health Monitoring

Monitor system status with the health check:

```bash
# Run health check
python discord_health_check.py

# Check specific channel
python discord_health_check.py --channel "CHANNEL_URL"
```

## Integration with Analysis Pipeline

### Entity Processing

Process extracted messages for insights:

```bash
python discord_processor.py --channel-id CHANNEL_ID
```

### AI Analysis

Generate AI-powered analysis reports:

```bash
python scripts/discord_gemini_analyzer.py --channel-id CHANNEL_ID
```

### Full Pipeline

Run complete extraction and analysis:

```bash
python run_discord_pipeline.py --url "CHANNEL_URL" --months 3
```

## Troubleshooting

### Common Issues

1. **Login Failures**
   - Check credentials in `.env` file
   - Ensure 2FA is handled manually if required
   - Verify Discord account has channel access

2. **Extraction Errors**
   - Check logs in `logs/discord/` directory
   - Verify channel URL format
   - Ensure stable internet connection

3. **Database Issues**
   - Check SQLite file permissions
   - Verify database schema creation
   - Clear corrupt extraction logs if needed

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
python discord_browser_extractor.py \
  --url "CHANNEL_URL" \
  --verbose \
  --test-limit 10
```

## Performance Considerations

### Rate Limiting
- Default: 1000 messages per hour
- Configurable delay between requests
- Respects Discord's usage policies

### Resource Usage
- Headless mode reduces memory usage
- Persistent browser profiles minimize setup time
- Efficient database queries with proper indexing

### Scalability
- Resume support for large extractions
- Background processing capabilities
- Modular design for easy extension

## Security Notes

- Store credentials securely in `.env` file
- Use application-specific passwords when possible
- Regular credential rotation recommended
- Monitor extraction logs for unusual activity

## Contributing

When extending the Discord system:

1. Follow existing code patterns
2. Add comprehensive logging
3. Include error handling
4. Update documentation
5. Test with various Discord features

## Support

For issues or questions:
1. Check the logs in `logs/discord/`
2. Review this documentation
3. Test with `--dry-run` flag first
4. Use `--verbose` for detailed output