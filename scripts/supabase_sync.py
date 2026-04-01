#!/usr/bin/env python3
"""Push all creators + platform_presences from SQLite to Supabase."""

import sqlite3
import json
import urllib.request
import urllib.error
import time

SUPABASE_URL = "https://shrbrlmxhdehglczhgjh.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNocmJybG14aGRlaGdsY3poZ2poIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NDg1MzA1MywiZXhwIjoyMDkwNDI5MDUzfQ.yGScX2gcwAz9X5quK51_iGTjyGqri2xxzp1BmMbp4Do"
DB_PATH = "/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db"
BATCH_SIZE = 500

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates",
}

def upsert_batch(table, rows):
    """Upsert a batch of rows via PostgREST."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    data = json.dumps(rows).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=HEADERS, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return resp.status, len(rows)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  ERROR {e.code}: {body[:200]}")
        return e.code, 0

def sync_creators():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Sync creators
    print("=== Syncing creators ===")
    cur.execute("SELECT * FROM creators ORDER BY id")
    rows = [dict(r) for r in cur.fetchall()]
    total = len(rows)
    pushed = 0
    
    for i in range(0, total, BATCH_SIZE):
        batch = rows[i:i+BATCH_SIZE]
        status, count = upsert_batch("creators", batch)
        pushed += count
        pct = int(pushed / total * 100)
        print(f"  Creators: {pushed}/{total} ({pct}%) - HTTP {status}")
        if status >= 400:
            print("  Stopping creators sync due to error")
            break
        time.sleep(0.1)  # gentle rate limit
    
    print(f"\nCreators done: {pushed}/{total}")
    
    # Sync platform_presences
    print("\n=== Syncing platform_presences ===")
    cur.execute("SELECT * FROM platform_presences ORDER BY id")
    rows = [dict(r) for r in cur.fetchall()]
    total = len(rows)
    pushed = 0
    
    for i in range(0, total, BATCH_SIZE):
        batch = rows[i:i+BATCH_SIZE]
        status, count = upsert_batch("platform_presences", batch)
        pushed += count
        pct = int(pushed / total * 100)
        print(f"  Presences: {pushed}/{total} ({pct}%) - HTTP {status}")
        if status >= 400:
            print("  Stopping presences sync due to error")
            break
        time.sleep(0.1)
    
    print(f"\nPresences done: {pushed}/{total}")
    conn.close()
    
    # Verify
    print("\n=== Verifying ===")
    for table in ["creators", "platform_presences"]:
        url = f"{SUPABASE_URL}/rest/v1/{table}?select=count"
        req = urllib.request.Request(url, headers={**HEADERS, "Prefer": "count=exact"})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        print(f"  {table}: {data[0]['count']} rows in Supabase")

if __name__ == "__main__":
    sync_creators()
