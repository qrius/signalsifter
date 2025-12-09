```markdown
# SignalSifter — Multi-Platform Message Extraction & Analysis

## Purpose
SignalSifter is a comprehensive message extraction and analysis system supporting both **Telegram** and **Discord** platforms. Extract historical messages, analyze content with AI, and generate insights from communication data.

### Core Features
- **Telegram**: Backfill private channels using your personal account (Telethon)
- **Discord**: Browser-based message extraction with anti-detection measures
- **AI Analysis**: Google Gemini integration for intelligent content analysis
- **Data Processing**: Entity extraction, contributor stats, and comprehensive reporting
- **Storage**: SQLite database with proper relationships and indexing

Branding
- Project / display name: SignalSifter
- Preferred Telegram handle (user account): @signalsifter
- Optional bot handle: @signalsifter_bot (register via @BotFather if desired)

Quickstart (local Docker)
1. Copy `.env.example` → `.env` and fill TELEGRAM_API_ID and TELEGRAM_API_HASH (and OPENAI_API_KEY if you want LLM summarization).
   - Also set BOT_NAME if you wish to override (default: signalsifter).
2. Build Docker image:
   docker build -t signalsifter-backfiller .
3. Create directories for persistent data (on mac host):
   mkdir -p data/raw data/media data/ocr .session
4. Run an interactive backfill for one channel (you will receive the Telethon login code in your Telegram app):
   docker run --rm -it \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/.session:/app/.session \
     --env-file .env \
     signalsifter-backfiller \
     "python backfill.py --channel \"@channel_or_id\" --from 2020-01-01 --to 2023-01-01"

Notes:
- On first run Telethon will prompt for login code (runs interactively). Session file is persisted into .session folder so subsequent runs are headless.
- To run multiple channels, call the CLI per channel. The script resumes automatically by checking max(message_id).

Main commands
- backfill.py: download messages into SQLite, raw JSON and media
- processor.py: process unprocessed messages (extraction + OCR + contributor stats)
- summarizer.py: generate channel-level Markdown summary using LLM or offline fallback
- run_channel_pipeline.py: runs backfill → processor (loop) → summarizer → compute_stats

## Discord Extraction System

### Quick Start (Discord)
1. **Setup Environment**:
   ```bash
   # Create Python virtual environment
   python3 -m venv signalsifter-env
   source signalsifter-env/bin/activate
   
   # Install dependencies
   pip install playwright telethon python-dotenv fake-useragent beautifulsoup4
   python -m playwright install chromium
   ```

2. **Configure Credentials**:
   Add to `.env` file:
   ```bash
   DISCORD_EMAIL=your_email@example.com
   DISCORD_PASSWORD=your_discord_password
   ```

3. **Extract Messages**:
   ```bash
   # Extract 6 months of history from a Discord channel
   python discord_browser_extractor.py \
     --url "https://discord.com/channels/SERVER_ID/CHANNEL_ID" \
     --months 6 --verbose
   
   # Run in headless mode for automated extraction
   python discord_browser_extractor.py \
     --url "https://discord.com/channels/SERVER_ID/CHANNEL_ID" \
     --months 6 --headless --verbose
   ```

### Discord Features
- **Browser Automation**: Playwright-based extraction with anti-detection
- **Smart Authentication**: Automatic login with manual fallback for 2FA
- **Rate Limiting**: Human-like delays and respectful request patterns
- **Resume Support**: Interrupted extractions can be resumed
- **Comprehensive Data**: Messages, reactions, embeds, mentions, and metadata
- **Database Integration**: Full SQLite schema with relationships

### Discord Files
- `discord_browser_extractor.py`: Main extraction engine
- `discord_db_schema.py`: Database schema and operations
- `discord_processor.py`: Message processing and entity extraction
- `discord_health_check.py`: System monitoring and health checks
- `discord_monitor.sh`: Cron automation and scheduling
- `discord_demo.py`: Example usage and demonstrations

Outputs
- data/backfill.sqlite : SQLite DB with messages/entities/summaries (shared with Telegram)
- data/raw/<channel_id>/message_<msgid>.json : raw JSON export
- data/media/<channel_id>/... : downloaded media
- data/ocr/<channel_id>/... : OCR text output
- data/summaries/channel_<id>_summary.md : Markdown summary for channel
- logs/discord/ : Extraction logs and monitoring data
```