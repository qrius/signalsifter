# SignalSifter Discord Module

A comprehensive Discord message extraction and analysis system that mirrors the existing Telegram functionality. Extract messages from Discord channels, perform entity recognition, OCR on images, and generate AI-powered insights using Google's Gemini AI.

## 🚀 Quick Start

### 1. Setup Discord Bot

1. **Create a Discord Application:**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Click "New Application" and give it a name
   - Navigate to "Bot" section and click "Add Bot"
   - Copy the **Bot Token** (keep this secret!)

2. **Configure Bot Permissions:**
   - In the Bot section, enable these **Privileged Gateway Intents:**
     - ✅ Message Content Intent
   - In the OAuth2 → URL Generator:
     - **Scopes:** `bot`
     - **Bot Permissions:** 
       - ✅ Read Messages/View Channels
       - ✅ Read Message History
       - ✅ View Guild Information

3. **Invite Bot to Server:**
   - Use the generated OAuth2 URL to invite your bot to the target Discord server
   - Make sure the bot has access to the channel you want to analyze

### 2. Environment Setup

Add your Discord bot token to `.env`:

```env
# Discord Bot Configuration
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# Gemini AI Configuration (for analysis)
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 📊 Usage Examples

### Extract and Analyze Discord Channel

**Using Discord URL (Recommended):**
```bash
# Complete pipeline: extraction → processing → analysis
python run_discord_pipeline.py --url "https://discord.com/channels/1296015181985349715/1356175241172488314"
```

**Using Guild and Channel IDs:**
```bash
# Extract from specific guild/channel
python run_discord_pipeline.py --guild-id 1296015181985349715 --channel-id 1356175241172488314
```

**With Date Filtering:**
```bash
# Extract messages from specific date range
python run_discord_pipeline.py \
  --url "https://discord.com/channels/1296015181985349715/1356175241172488314" \
  --from 2024-01-01 --to 2024-12-31
```

### Individual Components

**1. Message Extraction Only:**
```bash
python discord_extractor.py --url "https://discord.com/channels/1296015181985349715/1356175241172488314"
```

**2. Entity Processing Only:**
```bash
python discord_processor.py --guild-id 1296015181985349715 --channel-id 1356175241172488314
```

**3. AI Analysis Only:**
```bash
python scripts/discord_gemini_analyzer.py \
  --guild-id 1296015181985349715 \
  --channel-id 1356175241172488314 \
  --analysis-type comprehensive
```

### Pipeline Control Options

```bash
# Skip extraction (if already done)
python run_discord_pipeline.py --url "discord_url" --skip-extraction

# Analysis only (skip extraction and processing)
python run_discord_pipeline.py --url "discord_url" --analysis-only

# Check pipeline status
python run_discord_pipeline.py --url "discord_url" --status-only
```

## 🏗️ Architecture

### Core Components

```
Discord Module Structure:
├── discord_extractor.py          # Message & media extraction
├── discord_processor.py          # Entity extraction & OCR
├── scripts/discord_gemini_analyzer.py  # AI analysis
├── run_discord_pipeline.py       # Pipeline orchestration
└── data/
    ├── raw/                      # Raw JSON message files
    │   └── {guild_id}/
    │       └── {channel_id}/
    ├── media/                    # Downloaded attachments
    │   └── {guild_id}/{channel_id}/
    ├── discord_analysis/         # AI analysis reports
    └── backfill.sqlite          # Unified database
```

### Database Schema

The Discord module extends the existing SQLite schema with Discord-specific tables:

- **`discord_guilds`** - Server information
- **`discord_channels`** - Channel metadata  
- **`discord_messages`** - Message content, embeds, reactions
- **`discord_entities`** - Extracted entities (URLs, mentions, contracts)
- **`discord_analysis_logs`** - AI analysis tracking

## 🔍 Extracted Data

### Message Data
- **Content:** Message text with Discord formatting
- **Metadata:** Author, timestamps, edit history
- **Embeds:** Rich embed content (titles, descriptions, fields)
- **Attachments:** Images, files, media downloads
- **Reactions:** Emoji reactions and counts
- **Mentions:** User, role, and channel mentions
- **Threads:** Thread context and replies

### Entity Extraction
- **🔗 URLs:** Web links and resources
- **💰 Crypto:** Contract addresses (0x...), wallet addresses
- **📅 Dates:** Temporal references and events
- **👤 Mentions:** User (@user), channel (#channel), role (@role) mentions
- **😊 Emojis:** Custom server emojis
- **📨 Invites:** Discord invite codes
- **🖼️ OCR Text:** Text extracted from images

### AI Analysis (Gemini)
- **📊 Community Analysis:** Member engagement patterns
- **📈 Content Trends:** Discussion topics and themes
- **👥 User Insights:** Key contributors and interactions
- **🔍 Entity Summary:** Important resources and references
- **📱 Platform Features:** Discord-specific behavior analysis

## 🎯 Analysis Types

### 1. Comprehensive Analysis
```bash
python scripts/discord_gemini_analyzer.py \
  --guild-id GUILD_ID --channel-id CHANNEL_ID \
  --analysis-type comprehensive
```
**Output:** Full community analysis with engagement patterns, content themes, member insights, and platform-specific behavior.

### 2. Summary Analysis  
```bash
python scripts/discord_gemini_analyzer.py \
  --guild-id GUILD_ID --channel-id CHANNEL_ID \
  --analysis-type summary
```
**Output:** Concise summary of channel activity, key discussions, and notable events.

### 3. Entity Analysis
```bash
python scripts/discord_gemini_analyzer.py \
  --guild-id GUILD_ID --channel-id CHANNEL_ID \
  --analysis-type entities  
```
**Output:** Categorized extraction of people, projects, resources, events, and technical references.

## 📁 Output Files

### Analysis Reports
```
data/discord_analysis/
├── discord_analysis_{guild_id}_{channel_id}_2024-12-08_123456.md
├── discord_analysis_{guild_id}_{channel_id}_2024-12-08_123456_metadata.json
└── discord_messages_{guild_id}_{channel_id}_export.txt
```

### Raw Data
```
data/raw/{guild_id}/{channel_id}/
├── message_1234567890.json
├── message_1234567891.json
└── ...

data/media/{guild_id}/{channel_id}/  
├── msg_1234567890_att_0_image.png
├── msg_1234567891_att_0_document.pdf
└── ...
```

## ⚙️ Configuration Options

### Environment Variables (.env)
```env
# Discord Configuration
DISCORD_BOT_TOKEN=your_bot_token_here

# AI Analysis  
GEMINI_API_KEY=your_gemini_key_here

# Database & Storage
SQLITE_DB_PATH=./data/backfill.sqlite
RAW_DIR=./data/raw
MEDIA_DIR=./data/media
OCR_DIR=./data/ocr

# Rate Limiting (Gemini Free Tier)
# 2 requests/minute, 50 requests/day
```

### Command Line Options
```bash
# Date filtering
--from 2024-01-01 --to 2024-12-31

# Skip media downloads
--no-media

# Processing limits
--processing-limit 1000
--analysis-limit 500

# Analysis configuration
--analysis-type [comprehensive|summary|entities]
```

## 🔧 Troubleshooting

### Common Issues

**1. Bot Permission Errors**
```
Error: 403 Forbidden - Missing Access
```
**Solution:** Ensure bot has "Read Messages" and "Read Message History" permissions in the target channel.

**2. Message Content Intent**
```  
Error: Cannot read message content
```
**Solution:** Enable "Message Content Intent" in Discord Developer Portal → Bot settings.

**3. Guild/Channel Not Found**
```
Error: Channel not found or bot doesn't have access  
```
**Solution:** Verify the bot is invited to the correct server and has channel access.

**4. Rate Limiting (Gemini)**
```
Error: Daily API limit exceeded
```
**Solution:** Gemini free tier allows 50 requests/day. Wait 24 hours or upgrade to paid tier.

### Debug Commands

```bash
# Check database status
python discord_processor.py --stats

# Check pipeline status  
python run_discord_pipeline.py --url "discord_url" --status-only

# Test extraction without processing
python discord_extractor.py --url "discord_url" --no-media
```

## 🚀 Integration with Existing System

The Discord module integrates seamlessly with the existing SignalSifter Telegram system:

- **Shared Database:** Uses same SQLite database with separate Discord tables
- **Same Analysis Engine:** Leverages existing Gemini analyzer with Discord adaptations
- **Consistent Output Format:** Matching analysis report structure 
- **Similar Commands:** Parallel CLI interface to Telegram modules

### Combined Workflows

```bash
# Analyze both Telegram and Discord channels
python backfill.py --channel @telegram_channel
python run_discord_pipeline.py --url "discord_url"

# Combined analysis reports in data/analysis/ and data/discord_analysis/
```

## 📈 Performance & Limits

### Discord API Limits
- **Rate Limit:** 50 requests per second per bot
- **Message History:** No limit on old message access
- **File Size:** 8MB attachment limit (25MB with Nitro)

### Gemini AI Limits (Free Tier)
- **Rate Limit:** 2 requests per minute
- **Daily Limit:** 50 requests per day
- **Context Window:** 2M tokens
- **Cost:** Free (with usage limits)

### Recommended Batch Sizes
- **Extraction:** No limit (Discord handles rate limiting)
- **Processing:** 500 messages per batch
- **Analysis:** 1000 messages per request

## 🔜 Future Enhancements

### Planned Features
- **🧵 Thread Support:** Full thread message extraction and analysis
- **📊 Server-wide Analysis:** Multi-channel guild analysis
- **🔄 Real-time Monitoring:** Live message processing
- **📱 Webhook Integration:** Real-time notifications
- **🤖 Multiple AI Models:** Support for other LLM providers

### Integration Possibilities
- **NotebookLM Export:** Structured data export for NotebookLM
- **Dashboard Interface:** Web-based analysis dashboard  
- **Cross-Platform Analysis:** Combined Discord + Telegram insights

---

**Built for:** Discord community analysis and insights  
**Technology:** Python + discord.py + Google Gemini AI  
**Output:** Comprehensive, citation-rich analysis reports