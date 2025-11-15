#!/usr/bin/env python3
"""
Compute weighted contributor ranking for a channel and export CSV.

Usage:
  python compute_stats.py --channel <channel_tg_id> --top 50 --out ./data/stats/channel_<id>_contributors.csv
"""
import os
import csv
import argparse
import sqlite3
from collections import defaultdict

DB_PATH = os.getenv("SQLITE_DB_PATH", "./data/backfill.sqlite")

def compute(channel_id, top=50):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Count messages per sender
    cur.execute("""
      SELECT sender_username, COUNT(*) as msg_count