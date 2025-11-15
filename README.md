```markdown
# SignalSifter — Telegram Channel Backfiller & Analyzer

Purpose
- Backfill private Telegram channels using your personal account (Telethon).
- Store raw messages + attachments locally, reassemble reply threads, OCR images (Tesseract), extract deterministic entities, compute contributor stats, and produce one Markdown summary per channel (hybrid: 1-line summary + bullets).

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

Outputs
- data/backfill.sqlite : SQLite DB with messages/entities/summaries
- data/raw/<channel_id>/message_<msgid>.json : raw JSON export
- data/media/<channel_id>/... : downloaded media
- data/ocr/<channel_id>/... : OCR text output
- data/summaries/channel_<id>_summary.md : Markdown summary for channel

If you want a commit-ready update with these file changes applied to your repo, tell me and I will prepare a patch/PR content you can apply.
```