-- SQLite schema for backfill
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS channels (
  id INTEGER PRIMARY KEY,
  tg_id TEXT UNIQUE,
  title TEXT,
  username TEXT,
  created_at TEXT,
  last_backfilled_at TEXT
);

CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  channel_id TEXT,
  message_id INTEGER,
  sender_id INTEGER,
  sender_username TEXT,
  sender_name TEXT,
  date TEXT,
  edit_date TEXT,
  is_forwarded INTEGER DEFAULT 0,
  forward_from TEXT,
  reply_to_msg_id INTEGER,
  text TEXT,
  has_media INTEGER DEFAULT 0,
  media_path TEXT,
  raw_json_path TEXT,
  ocr_text TEXT,
  processed INTEGER DEFAULT 0,
  UNIQUE(channel_id, message_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_channel_date ON messages(channel_id, date);

CREATE TABLE IF NOT EXISTS entities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  message_row_id INTEGER,
  type TEXT,
  raw_value TEXT,
  normalized_value TEXT,
  confidence REAL,
  FOREIGN KEY(message_row_id) REFERENCES messages(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS summaries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  channel_id TEXT,
  generated_at TEXT,
  window_start TEXT,
  window_end TEXT,
  summary_md TEXT
);