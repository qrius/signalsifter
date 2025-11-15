#!/usr/bin/env python3
"""
Processor: reads unprocessed messages from SQLite, runs deterministic extraction,
downloads/ensures media exists, runs OCR on images, writes entities, and marks messages processed.

Run:
  python processor.py --limit 500
"""
import os
import re
import json
import argparse
import sqlite3
from dotenv import load_dotenv
from tqdm import tqdm
from PIL import Image
import pytesseract
import dateparser

load_dotenv()
DB_PATH = os.getenv("SQLITE_DB_PATH", "./data/backfill.sqlite")
MEDIA_DIR = os.getenv("MEDIA_DIR", "./data/media")
OCR_DIR = os.getenv("OCR_DIR", "./data/ocr")
os.makedirs(OCR_DIR, exist_ok=True)

# regexes
RE_0X = re.compile(r'0x[a-fA-F0-9]{40}')
RE_URL = re.compile(r'(https?://[^\s]+)')
# basic wallet fallback - simple Alphanumeric string heuristics for non-0x (not perfect)
RE_SIMPLE_ADDRESS = re.compile(r'\b[A-Za-z0-9]{32,64}\b')

def extract_dates(text):
    if not text:
        return []
    found = dateparser.search.search_dates(text, languages=['en']) if hasattr(dateparser.search, 'search_dates') else []
    dates = [d[1].isoformat() for d in found] if found else []
    return dates

def ocr_image(path):
    try:
        text = pytesseract.image_to_string(Image.open(path))
        return text.strip()
    except Exception as e:
        print("OCR failed for", path, e)
        return ""

def process_batch(limit=200):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, channel_id, message_id, text, has_media, media_path, raw_json_path FROM messages WHERE processed = 0 ORDER BY date LIMIT ?", (limit,))
    rows = cur.fetchall()
    for row in tqdm(rows):
        row_id, channel_id, message_id, text, has_media, media_path, raw_json = row
        entities = []
        # extract 0x addresses
        for m in RE_0X.findall(text or ""):
            entities.append(("contract", m, m.lower(), 1.0))
        # urls
        for u in RE_URL.findall(text or ""):
            entities.append(("url", u, u, 1.0))
        # simple addresses
        for s in RE_SIMPLE_ADDRESS.findall(text or ""):
            # ignore short obvious words
            if len(s) >= 32 and not s.lower().startswith("http"):
                entities.append(("wallet", s, s, 0.6))
        # dates
        for d in extract_dates(text or ""):
            entities.append(("date", d, d, 0.8))
        # OCR
        ocr_text = None
        if has_media and media_path:
            # If media_path is relative to project, ensure exists
            if os.path.exists(media_path):
                ocr_text = ocr_image(media_path)
                if ocr_text:
                    entities.append(("ocr_text", ocr_text[:200], ocr_text, 0.75))
                    # save OCR to file
                    ocr_out_dir = os.path.join(OCR_DIR, channel_id)
                    os.makedirs(ocr_out_dir, exist_ok=True)
                    ocr_file = os.path.join(ocr_out_dir, f"{message_id}.txt")
                    with open(ocr_file, "w", encoding="utf-8") as f:
                        f.write(ocr_text)
        # insert entities
        for ent in entities:
            typ, raw, norm, conf = ent
            cur.execute("INSERT INTO entities (message_row_id, type, raw_value, normalized_value, confidence) VALUES (?, ?, ?, ?, ?)",
                        (row_id, typ, raw, norm, conf))
        # mark processed and save ocr text
        cur.execute("UPDATE messages SET processed = 1, ocr_text = ? WHERE id = ?", (ocr_text, row_id))
        conn.commit()
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()
    process_batch(limit=args.limit)