#!/usr/bin/env python3
"""
Sync local SQLite DB → Turso (remote libsql).
Pushes creators, platform_presences, and content_samples to the cloud DB.
Runs incrementally: only syncs rows updated since last sync.

Usage: python3 scripts/sync_to_turso.py [--full]
  --full: Force full resync (not just incremental)

Requires: pip install libsql-experimental  (or use HTTP API)
"""
import sqlite3
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

LOCAL_DB = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
SYNC_STATE_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scripts/sync_state.json'

# Load from .env.local
def load_env():
    env = {}
    env_path = '/Users/aiman/.openclaw/workspace/projects/kreator/.env.local'
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                env[k] = v
    return env

env = load_env()
TURSO_URL = env['TURSO_URL'].replace('libsql://', 'https://')
TURSO_TOKEN = env['TURSO_AUTH_TOKEN']

BATCH_SIZE = 500


def turso_execute(statements):
    """Execute statements via Turso HTTP API."""
    url = f"{TURSO_URL}/v2/pipeline"
    payload = {
        "requests": [
            {"type": "execute", "stmt": stmt} for stmt in statements
        ] + [{"type": "close"}]
    }
    
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Authorization', f'Bearer {TURSO_TOKEN}')
    req.add_header('Content-Type', 'application/json')
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            # Check for errors
            for r in result.get('results', []):
                if r.get('type') == 'error':
                    print(f"  ❌ Turso error: {r['error']}")
            return result
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  ❌ HTTP {e.code}: {body[:200]}")
        return None
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def make_stmt(sql, args=None):
    """Create a Turso statement object."""
    stmt = {"sql": sql}
    if args:
        stmt["args"] = []
        for a in args:
            if a is None:
                stmt["args"].append({"type": "null"})
            elif isinstance(a, bool):
                stmt["args"].append({"type": "integer", "value": str(int(a))})
            elif isinstance(a, int):
                stmt["args"].append({"type": "integer", "value": str(a)})
            elif isinstance(a, float):
                # Turso wants float type with numeric value (not string)
                stmt["args"].append({"type": "float", "value": a})
            elif isinstance(a, str):
                stmt["args"].append({"type": "text", "value": a})
            else:
                stmt["args"].append({"type": "text", "value": str(a)})
    return stmt


def load_sync_state():
    try:
        with open(SYNC_STATE_PATH) as f:
            return json.load(f)
    except:
        return {"last_sync": "2000-01-01T00:00:00"}


def save_sync_state():
    with open(SYNC_STATE_PATH, 'w') as f:
        json.dump({"last_sync": datetime.now(timezone.utc).isoformat()}, f)


def ensure_tables():
    """Create tables in Turso if they don't exist."""
    stmts = [
        make_stmt("""CREATE TABLE IF NOT EXISTS creators (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            bio TEXT DEFAULT '',
            profile_image TEXT DEFAULT '',
            country TEXT NOT NULL,
            primary_platform TEXT NOT NULL,
            categories TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            heat_score REAL DEFAULT 0,
            audience_demographics TEXT DEFAULT '',
            contact_email TEXT DEFAULT ''
        )"""),
        make_stmt("""CREATE TABLE IF NOT EXISTS platform_presences (
            id INTEGER PRIMARY KEY,
            creator_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            username TEXT NOT NULL,
            url TEXT DEFAULT '',
            followers INTEGER DEFAULT 0,
            following INTEGER DEFAULT 0,
            total_likes INTEGER DEFAULT 0,
            total_videos INTEGER DEFAULT 0,
            avg_views INTEGER DEFAULT 0,
            engagement_rate REAL DEFAULT 0,
            last_scraped_at TEXT DEFAULT (datetime('now')),
            recent_videos INTEGER DEFAULT 0,
            recent_views INTEGER DEFAULT 0,
            recent_new_followers INTEGER DEFAULT 0,
            impressions INTEGER DEFAULT 0,
            platform_uid TEXT DEFAULT ''
        )"""),
        make_stmt("""CREATE TABLE IF NOT EXISTS content_samples (
            id INTEGER PRIMARY KEY,
            presence_id INTEGER NOT NULL,
            url TEXT DEFAULT '',
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            posted_at TEXT DEFAULT '',
            caption TEXT DEFAULT ''
        )"""),
    ]
    result = turso_execute(stmts)
    if result:
        print("  ✅ Tables ensured")


def sync_creators(conn, full=False):
    """Sync creators table."""
    state = load_sync_state()
    
    if full:
        rows = conn.execute("SELECT * FROM creators ORDER BY id").fetchall()
    else:
        rows = conn.execute("SELECT * FROM creators WHERE updated_at > ? ORDER BY id", 
                          (state['last_sync'],)).fetchall()
    
    if not rows:
        print("  Creators: nothing to sync")
        return 0
    
    print(f"  Creators: syncing {len(rows)} rows...")
    synced = 0
    
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i+BATCH_SIZE]
        stmts = []
        for r in batch:
            stmts.append(make_stmt(
                """INSERT OR REPLACE INTO creators 
                   (id, name, bio, profile_image, country, primary_platform, categories, 
                    created_at, updated_at, heat_score, audience_demographics, contact_email)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [r['id'], r['name'], r['bio'] or '', r['profile_image'] or '', 
                 r['country'], r['primary_platform'], r['categories'] or '[]',
                 r['created_at'], r['updated_at'], r['heat_score'] or 0,
                 r['audience_demographics'] or '', r['contact_email'] or '']
            ))
        
        result = turso_execute(stmts)
        if result:
            synced += len(batch)
            print(f"    {synced}/{len(rows)} creators pushed")
    
    return synced


def sync_presences(conn, full=False):
    """Sync platform_presences table."""
    state = load_sync_state()
    
    if full:
        rows = conn.execute("SELECT * FROM platform_presences ORDER BY id").fetchall()
    else:
        rows = conn.execute("SELECT * FROM platform_presences WHERE last_scraped_at > ? ORDER BY id",
                          (state['last_sync'],)).fetchall()
    
    if not rows:
        print("  Presences: nothing to sync")
        return 0
    
    print(f"  Presences: syncing {len(rows)} rows...")
    synced = 0
    
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i+BATCH_SIZE]
        stmts = []
        for r in batch:
            stmts.append(make_stmt(
                """INSERT OR REPLACE INTO platform_presences
                   (id, creator_id, platform, username, url, followers, following, total_likes,
                    total_videos, avg_views, engagement_rate, last_scraped_at, recent_videos,
                    recent_views, recent_new_followers, impressions, platform_uid)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [r['id'], r['creator_id'], r['platform'], r['username'], r['url'] or '',
                 r['followers'] or 0, r['following'] or 0, abs(r['total_likes'] or 0),
                 r['total_videos'] or 0, r['avg_views'] or 0, r['engagement_rate'] or 0,
                 r['last_scraped_at'], r['recent_videos'] or 0, r['recent_views'] or 0,
                 r['recent_new_followers'] or 0, r['impressions'] or 0, r['platform_uid'] or '']
            ))
        
        result = turso_execute(stmts)
        if result:
            synced += len(batch)
            print(f"    {synced}/{len(rows)} presences pushed")
    
    return synced


def sync_content_samples(conn, full=False):
    """Sync content_samples table."""
    if full:
        rows = conn.execute("SELECT * FROM content_samples ORDER BY id").fetchall()
    else:
        # No updated_at on content_samples, sync all
        # Check what's already in Turso
        rows = conn.execute("SELECT * FROM content_samples ORDER BY id").fetchall()
    
    if not rows:
        print("  Content samples: nothing to sync")
        return 0
    
    print(f"  Content samples: syncing {len(rows)} rows...")
    synced = 0
    
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i+BATCH_SIZE]
        stmts = []
        for r in batch:
            stmts.append(make_stmt(
                """INSERT OR REPLACE INTO content_samples
                   (id, presence_id, url, views, likes, comments, shares, posted_at, caption)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [r['id'], r['presence_id'], r['url'] or '', r['views'] or 0,
                 r['likes'] or 0, r['comments'] or 0, r['shares'] or 0,
                 r['posted_at'] or '', r['caption'] or '']
            ))
        
        result = turso_execute(stmts)
        if result:
            synced += len(batch)
            print(f"    {synced}/{len(rows)} samples pushed")
    
    return synced


def main():
    full = '--full' in sys.argv
    
    print(f'{"="*60}')
    print(f'🔄 SYNC TO TURSO {"(FULL)" if full else "(INCREMENTAL)"}')
    print(f'   {datetime.now(timezone.utc).isoformat()}')
    print(f'{"="*60}')
    
    ensure_tables()
    
    conn = sqlite3.connect(LOCAL_DB)
    conn.row_factory = sqlite3.Row
    
    start = time.time()
    
    c = sync_creators(conn, full)
    p = sync_presences(conn, full)
    s = sync_content_samples(conn, full)
    
    save_sync_state()
    conn.close()
    
    elapsed = time.time() - start
    print(f'\n{"="*60}')
    print(f'DONE in {elapsed:.1f}s')
    print(f'  Creators: {c} | Presences: {p} | Samples: {s}')
    print(f'{"="*60}')


if __name__ == '__main__':
    main()
