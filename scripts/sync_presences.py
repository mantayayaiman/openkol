#!/usr/bin/env python3
"""Quick sync: platform_presences + content_samples to Turso."""
import sqlite3, json, urllib.request, sys, time

LOCAL_DB = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
BATCH = 200

def load_env():
    env = {}
    with open('/Users/aiman/.openclaw/workspace/projects/kreator/.env.local') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                env[k] = v
    return env

env = load_env()
TURSO_URL = env['TURSO_URL'].replace('libsql://', 'https://')
TURSO_TOKEN = env['TURSO_AUTH_TOKEN']

def turso_exec(stmts):
    payload = {"requests": [{"type": "execute", "stmt": s} for s in stmts] + [{"type": "close"}]}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{TURSO_URL}/v2/pipeline", data=data, method='POST')
    req.add_header('Authorization', f'Bearer {TURSO_TOKEN}')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  ❌ {e}")
        return None

def make_arg(a):
    if a is None: return {"type": "null"}
    if isinstance(a, int): return {"type": "integer", "value": str(a)}
    if isinstance(a, float): return {"type": "float", "value": a}
    return {"type": "text", "value": str(a)}

def sync_presences():
    conn = sqlite3.connect(LOCAL_DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM platform_presences ORDER BY id").fetchall()
    conn.close()
    
    print(f"Presences: {len(rows)} rows")
    synced = 0
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i+BATCH]
        stmts = []
        for r in batch:
            stmts.append({
                "sql": """INSERT OR REPLACE INTO platform_presences
                   (id, creator_id, platform, username, url, followers, following, total_likes,
                    total_videos, avg_views, engagement_rate, last_scraped_at, recent_videos,
                    recent_views, recent_new_followers, impressions, platform_uid, top_content)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                "args": [make_arg(x) for x in [
                    r['id'], r['creator_id'], r['platform'], r['username'], r['url'] or '',
                    r['followers'] or 0, r['following'] or 0, abs(r['total_likes'] or 0),
                    r['total_videos'] or 0, r['avg_views'] or 0, r['engagement_rate'] or 0,
                    r['last_scraped_at'], r['recent_videos'] or 0, r['recent_views'] or 0,
                    r['recent_new_followers'] or 0, r['impressions'] or 0, r['platform_uid'] or '',
                    r['top_content'] or ''
                ]]
            })
        result = turso_exec(stmts)
        if result:
            synced += len(batch)
            print(f"  {synced}/{len(rows)} presences")
        sys.stdout.flush()
    return synced

def sync_samples():
    conn = sqlite3.connect(LOCAL_DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM content_samples ORDER BY id").fetchall()
    conn.close()
    
    print(f"Content samples: {len(rows)} rows")
    synced = 0
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i+BATCH]
        stmts = []
        for r in batch:
            stmts.append({
                "sql": """INSERT OR REPLACE INTO content_samples
                   (id, presence_id, url, views, likes, comments, shares, posted_at, caption)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                "args": [make_arg(x) for x in [
                    r['id'], r['presence_id'], r['url'] or '', r['views'] or 0,
                    r['likes'] or 0, r['comments'] or 0, r['shares'] or 0,
                    r['posted_at'] or '', r['caption'] or ''
                ]]
            })
        result = turso_exec(stmts)
        if result:
            synced += len(batch)
            print(f"  {synced}/{len(rows)} samples")
        sys.stdout.flush()
    return synced

print("=== SYNC: Platform Presences (with top_content) ===")
t = time.time()
p = sync_presences()
print(f"\nDone in {time.time()-t:.0f}s — {p} presences synced")
