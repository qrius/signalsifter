#!/usr/bin/env python3
"""
Wrapper to run the channel pipeline:
1) backfill.py (optionally --no-media)
2) processor.py in a loop until no unprocessed messages remain
3) summarizer.py to produce Markdown summary
4) compute_stats.py to produce contributor CSV

Usage:
  python run_channel_pipeline.py --channel "<channel_tg_id_or_username>" [--from YYYY-MM-DD] [--to YYYY-MM-DD]
    [--no-media] [--process-limit 200] [--window-days 7] [--out-dir ./data/output]

This script is intended to be invoked inside the Docker container or locally with the same virtualenv.
"""
import os
import argparse
import subprocess
import sqlite3
import time
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

DB_PATH = os.getenv("SQLITE_DB_PATH", "./data/backfill.sqlite")

def count_unprocessed(channel_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM messages WHERE channel_id = ? AND processed = 0", (channel_id,))
    c = cur.fetchone()[0]
    conn.close()
    return c

def run_cmd(cmd_list):
    print("Running:", " ".join(cmd_list))
    res = subprocess.run(cmd_list)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd_list)}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", required=True)
    parser.add_argument("--from", dest="from_date", help="YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", help="YYYY-MM-DD")
    parser.add_argument("--no-media", action="store_true", help="Do not download media during backfill")
    parser.add_argument("--process-limit", type=int, default=200, help="Number of messages per processor batch")
    parser.add_argument("--window-days", type=int, default=int(os.getenv("DEFAULT_CHUNK_DAYS", "7")))
    parser.add_argument("--out-dir", default="./data/summaries")
    args = parser.parse_args()

    since_arg = ["--from", args.from_date] if args.from_date else []
    to_arg = ["--to", args.to_date] if args.to_date else []
    no_media_flag = ["--no-media"] if args.no_media else []

    # 1) Backfill
    backfill_cmd = ["python", "backfill.py", "--channel", args.channel] + since_arg + to_arg + no_media_flag
    run_cmd(backfill_cmd)

    # Convert channel to numeric tg_id if needed for DB lookups
    # Try to find the channel id in DB via channels table
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT tg_id FROM channels WHERE tg_id = ? OR username = ?", (args.channel, args.channel))
    r = cur.fetchone()
    conn.close()
    channel_db_id = r[0] if r else args.channel

    # 2) Processor loop until no unprocessed messages remain
    while True:
        remaining = count_unprocessed(channel_db_id)
        print(f"Unprocessed messages for channel {channel_db_id}: {remaining}")
        if remaining == 0:
            break
        # run processor
        proc_cmd = ["python", "processor.py", "--limit", str(args.process_limit)]
        run_cmd(proc_cmd)
        # small sleep to avoid tight-loop
        time.sleep(1)

    # 3) Summarize (generate Markdown)
    os.makedirs(args.out_dir, exist_ok=True)
    md_out = os.path.join(args.out_dir, f"channel_{channel_db_id}_summary.md")
    sum_cmd = ["python", "summarizer.py", "--channel_id", channel_db_id, "--window-days", str(args.window_days), "--out", md_out]
    run_cmd(sum_cmd)
    print("Summary written to:", md_out)

    # 4) Compute contributor stats CSV
    stats_dir = os.path.join(args.out_dir, "stats")
    os.makedirs(stats_dir, exist_ok=True)
    csv_out = os.path.join(stats_dir, f"channel_{channel_db_id}_contributors.csv")
    stats_cmd = ["python", "compute_stats.py", "--channel", channel_db_id, "--top", "200", "--out", csv_out]
    run_cmd(stats_cmd)
    print("Contributor CSV written to:", csv_out)

if __name__ == "__main__":
    main()