#!/usr/bin/env python3
"""Push audit_scores from SQLite to Supabase."""
import sqlite3, json, requests, time

SUPABASE_URL = "https://shrbrlmxhdehglczhgjh.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNocmJybG14aGRlaGdsY3poZ2poIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NDg1MzA1MywiZXhwIjoyMDkwNDI5MDUzfQ.yGScX2gcwAz9X5quK51_iGTjyGqri2xxzp1BmMbp4Do"
DB_PATH = "/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db"
BATCH_SIZE = 500

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=ignore-duplicates"
}

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get all audit scores
rows = cur.execute("""
    SELECT creator_id, overall_score, follower_quality, engagement_authenticity,
           growth_consistency, comment_quality, scored_at, signals_json
    FROM audit_scores
""").fetchall()

print(f"Total audit scores to push: {len(rows)}")

pushed = 0
errors = 0
for i in range(0, len(rows), BATCH_SIZE):
    batch = rows[i:i+BATCH_SIZE]
    records = []
    for r in batch:
        records.append({
            "creator_id": r["creator_id"],
            "overall_score": r["overall_score"],
            "follower_quality": r["follower_quality"],
            "engagement_authenticity": r["engagement_authenticity"],
            "growth_consistency": r["growth_consistency"],
            "comment_quality": r["comment_quality"],
            "scored_at": r["scored_at"] or "",
            "signals_json": r["signals_json"] or "{}"
        })
    
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/audit_scores",
        headers=headers,
        json=records
    )
    
    if resp.status_code in (200, 201):
        pushed += len(batch)
        print(f"  Pushed {pushed}/{len(rows)}")
    else:
        errors += 1
        print(f"  ERROR batch {i//BATCH_SIZE}: {resp.status_code} {resp.text[:200]}")
        # Try smaller batches on error
        if resp.status_code == 400:
            # Might have FK violations - push one by one
            for rec in records:
                r2 = requests.post(
                    f"{SUPABASE_URL}/rest/v1/audit_scores",
                    headers=headers,
                    json=rec
                )
                if r2.status_code in (200, 201):
                    pushed += 1
                # Skip FK violations silently
            print(f"  After retry: {pushed}/{len(rows)}")
    
    time.sleep(0.1)

conn.close()
print(f"\nDone! Pushed: {pushed}, Errors: {errors}")
