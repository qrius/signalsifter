# SignalSifter Quick Start

## Next Steps After Restart

### 1. Create Required Directories
```bash
cd /Users/ll/Sandbox/SignalSifter
mkdir -p .session data/raw data/media data/ocr data/summaries
```

### 2. Build Docker Image
```bash
docker build -t signalsifter-backfiller .
```

### 3. Run Interactive Backfill (FIRST TIME)
```bash
docker run --rm -it \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/.session:/app/.session" \
  --env-file .env \
  signalsifter-backfiller \
  "python backfill.py --channel '@your_channel' --from 2024-01-01 --to 2024-01-15 --no-media"
```

**⚠️ IMPORTANT - First Run Login:**
- Telethon will ask: `Please enter your phone (or bot token):`
- Enter your phone with country code: `+1234567890`
- A **code will arrive in your Telegram app** (not SMS)
- Paste the code when prompted: `Please enter the code you received:`
- Session saves to `.session/telethon_session.session` for future runs

**Replace `@your_channel`** with your actual channel username or numeric ID.

---

### 4. Process Messages (After Backfill)
```bash
docker run --rm -it \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/.session:/app/.session" \
  --env-file .env \
  signalsifter-backfiller \
  "python processor.py"
```

### 5. Generate Summary
```bash
# Get channel_id from: ls data/raw/
docker run --rm -it \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/.session:/app/.session" \
  --env-file .env \
  signalsifter-backfiller \
  "python summarizer.py --channel <channel_id>"
```

---

## Alternative: docker-compose

```bash
# Build
docker-compose build

# Backfill
docker-compose run backfiller python backfill.py --channel "@your_channel" --from 2024-01-01 --to 2024-01-15 --no-media

# Process
docker-compose run backfiller python processor.py

# Summarize
docker-compose run backfiller python summarizer.py --channel <channel_id>
```

---

## Full Pipeline (All Steps at Once)
```bash
docker run --rm -it \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/.session:/app/.session" \
  --env-file .env \
  signalsifter-backfiller \
  "python run_channel_pipeline.py --channel '@your_channel' --from 2024-01-01 --to 2024-01-15 --no-media"
```

---

## Output Location
- SQLite DB: `data/backfill.sqlite`
- Raw JSON: `data/raw/<channel_id>/message_*.json`
- Media: `data/media/<channel_id>/`
- OCR: `data/ocr/<channel_id>/`
- Summary: `data/summaries/channel_<id>_summary.md`

---

## Tips
- Always use `--no-media` for testing to save disk space
- Session file persists login - subsequent runs are headless
- Scripts auto-resume from last processed message
