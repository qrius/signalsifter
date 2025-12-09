# SignalSifter - Telegram Channel Analysis & AI Insights

**A comprehensive Telegram channel analysis system with automated AI-powered insights using Google Gemini API.**

## 🎉 **Sonic English Implementation - COMPLETE**

Successfully delivered a **NotebookLM alternative** for Sonic Protocol blockchain community analysis:

- ✅ **21,400+ messages** extracted from @Sonic_English (8+ months of historical data)
- ✅ **Automated daily sync** with incremental processing 
- ✅ **Gemini 1.5 Pro** AI analysis with 2M token context window
- ✅ **Independent automation** (runs outside VS Code via iTerm2)
- ✅ **Rate-limited processing** (2 req/min, 50/day - Google AI Studio free tier)
- ✅ **NotebookLM-ready exports** with timestamped analysis

## 🚀 **Quick Start - Sonic English Automation**

### **From iTerm2 or External Terminal:**
```bash
cd /Users/ll/Sandbox/SignalSifter
./sonic_standalone.sh
```

**Options:**
1. **One-time sync** - Extract new messages and generate analysis
2. **Daily automation** - Setup cron job for automatic daily updates
3. **Background sync** - Continuous 24/7 monitoring
4. **Check status** - Monitor automation status
5. **Stop background** - Stop running processes

### **Output Locations:**
- **Daily Analysis:** `data/gemini_analysis/sonic_english_daily_analysis_YYYY-MM-DD_HHMMSS.md`
- **Complete Messages:** `data/sonic_english/sonic_messages_export.txt` (21,400+ messages)
- **Analysis Reports:** `data/sonic_english/comprehensive_sonic_analysis.md`
- **Logs:** `logs/standalone/`

## 📊 **For NotebookLM Upload:**

**Primary Source Files:**
1. `data/sonic_english/sonic_messages_export.txt` - Complete 8+ month message history
2. `data/sonic_english/comprehensive_sonic_analysis.md` - AI-generated insights
3. `data/gemini_analysis/sonic_english_daily_*.md` - Daily incremental reports

## ⚙️ **Core Architecture**

### **Key Components:**
- **`sonic_standalone.sh`** - Main automation script (runs independently)
- **`scripts/daily_gemini_sync.py`** - Incremental processing pipeline
- **`scripts/gemini_analyzer.py`** - AI analysis engine (Gemini 1.5 Pro)
- **`backfill.py`** - Message extraction core
- **`data/backfill.sqlite`** - Message database (21,400+ messages)

### **Automation Features:**
- **Incremental Processing** - Only analyzes new messages since last run
- **Rate Limiting** - Respects Google AI Studio free tier limits
- **Error Recovery** - Handles API failures and database locks
- **Background Operation** - Survives terminal/VS Code closure
- **Comprehensive Logging** - All operations tracked

## 🔧 **Setup Requirements**

### **Environment Variables (.env):**
```bash
# Telegram API (from https://my.telegram.org)
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash

# Gemini API (from https://aistudio.google.com/app/apikey)  
GEMINI_API_KEY=your_gemini_key

# Database
SQLITE_DB_PATH=./data/backfill.sqlite
```

### **Dependencies:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 📈 **Sonic Protocol Analysis Results**

The implementation successfully analyzed the Sonic English Telegram community revealing:

### **Community Insights:**
- **Technical Focus:** Wallet troubleshooting, staking, cross-chain migration
- **Security Emphasis:** Account security education, scam prevention
- **Active Support:** Community moderators providing user assistance
- **Migration Activity:** Fantom to Sonic blockchain transition discussions

### **Temporal Coverage:**
- **Date Range:** April 2025 - December 2025 (8+ months)
- **Message Volume:** 21,400+ messages with full text content
- **User Attribution:** Username tracking for community analysis
- **Media Tracking:** Attachment presence flagged for context

### **AI Analysis Capabilities:**
- **Sentiment Analysis:** Community mood and trend tracking
- **Topic Extraction:** Key discussion themes identification  
- **Timeline Analysis:** Event correlation and development tracking
- **Citation System:** Timestamp-based source attribution

## 🔄 **Automation Workflow**

1. **Message Extraction:** New Sonic English messages since last sync
2. **Data Processing:** Format messages for AI analysis
3. **Gemini Analysis:** Generate comprehensive insights with citations
4. **Report Generation:** Save timestamped markdown reports
5. **Database Updates:** Track processing status and timestamps
6. **Export Updates:** Refresh NotebookLM source files

## 📁 **Project Structure**

```
SignalSifter/
├── sonic_standalone.sh          # Main automation launcher
├── scripts/
│   ├── daily_gemini_sync.py    # Incremental processing
│   ├── gemini_analyzer.py      # AI analysis engine
│   └── schedule_gemini_daily.sh # Cron automation
├── data/
│   ├── backfill.sqlite         # Message database (21,400+)
│   ├── sonic_english/          # Analysis outputs
│   │   ├── sonic_messages_export.txt
│   │   └── comprehensive_sonic_analysis.md
│   └── gemini_analysis/        # Daily reports
└── logs/standalone/            # Automation logs
```

## 🎯 **Success Metrics**

- ✅ **21,400+ messages** extracted and processed
- ✅ **8+ months** of historical data coverage
- ✅ **100% automation** - runs independently of development environment
- ✅ **Daily incremental updates** maintaining fresh analysis
- ✅ **NotebookLM integration** ready with structured exports
- ✅ **Rate-limited compliance** respecting free tier API limits
- ✅ **Comprehensive logging** for monitoring and debugging

## 🚀 **Future Enhancements**

The automation framework supports:
- **Multi-channel analysis** (add more Telegram channels)
- **Custom analysis types** (sentiment, entities, summaries)  
- **Extended AI models** (switch between Gemini variants)
- **Webhook integration** (real-time notifications)
- **Advanced scheduling** (custom cron patterns)

---

**Built for:** Sonic Protocol blockchain community analysis  
**Technology:** Python + Telethon + Google Gemini 1.5 Pro  
**Output:** NotebookLM-ready analysis with comprehensive insights