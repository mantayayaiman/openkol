#!/usr/bin/env python3
"""
Periodic verifier: picks N random creators from DB, re-scrapes TikTok,
compares data, deletes fakes, logs results.

Usage: PLAYWRIGHT_BROWSERS_PATH=0 python3 scraper/periodic_verify.py [--sample 10]
"""
import asyncio, json, sqlite3, random, sys
from datetime import datetime, timezone
from playwright.async_api import async_playwright

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
LOG_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/verify_log.jsonl'
SAMPLE_SIZE = int(sys.argv[sys.argv.index('--sample') + 1]) if '--sample' in sys.argv else 10

async def verify_profile(ctx, username):
    """Scrape real TikTok data for verification."""
    page = await ctx.new_page()
    try:
        await page.goto(f'https://www.tiktok.com/@{username}', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(2 + random.uniform(0, 1))
        
        data = await page.evaluate('''() => {
            const el = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");
            return el ? el.textContent : null;
        }''')
        
        if data:
            parsed = json.loads(data)
            ds = parsed.get('__DEFAULT_SCOPE__', {})
            ud = ds.get('webapp.user-detail', {})
            if 'userInfo' in ud:
                u = ud['userInfo']['user']
                s = ud['userInfo']['stats']
                return {
                    'username': u.get('uniqueId', username),
                    'name': u.get('nickname', ''),
                    'followers': s.get('followerCount', 0),
                    'following': s.get('followingCount', 0),
                    'likes': s.get('heartCount', 0),
                    'videos': s.get('videoCount', 0),
                    'verified': u.get('verified', False),
                }
        return None
    except:
        return None
    finally:
        await page.close()

async def main():
    print(f'=== PERIODIC VERIFICATION ({SAMPLE_SIZE} samples) ===')
    print(f'Time: {datetime.now(timezone.utc).isoformat()}')
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Get random sample
    creators = conn.execute('''
        SELECT c.id, c.name, pp.username, pp.followers, pp.following, pp.total_likes, pp.total_videos
        FROM creators c
        JOIN platform_presences pp ON pp.creator_id = c.id
        ORDER BY RANDOM()
        LIMIT ?
    ''', (SAMPLE_SIZE,)).fetchall()
    
    print(f'Sampled {len(creators)} creators to verify\n')
    
    verified = 0
    mismatched = 0
    not_found = 0
    updated = 0
    deleted_ids = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        for i, c in enumerate(creators):
            username = c['username']
            db_followers = c['followers']
            
            real = await verify_profile(ctx, username)
            
            if real is None:
                print(f'  [{i+1}] @{username}: ⚠️ Could not scrape (skip)')
                not_found += 1
            elif real['followers'] == 0 and db_followers > 10000:
                print(f'  [{i+1}] @{username}: ❌ FAKE — DB={db_followers:,}, Real=0 → DELETE')
                deleted_ids.append(c['id'])
            elif db_followers > 0 and real['followers'] > 0:
                ratio = real['followers'] / db_followers
                if 0.3 <= ratio <= 3.0:
                    print(f'  [{i+1}] @{username}: ✅ MATCH — DB={db_followers:,}, Real={real["followers"]:,} (ratio={ratio:.2f})')
                    verified += 1
                    # Update with fresh data
                    conn.execute('UPDATE platform_presences SET followers=?, following=?, total_likes=?, total_videos=?, last_scraped_at=? WHERE creator_id=?',
                        (real['followers'], real['following'], real['likes'], real['videos'],
                         datetime.now(timezone.utc).isoformat(), c['id']))
                    updated += 1
                else:
                    print(f'  [{i+1}] @{username}: ❌ MISMATCH — DB={db_followers:,}, Real={real["followers"]:,} (ratio={ratio:.2f}) → DELETE')
                    deleted_ids.append(c['id'])
                    mismatched += 1
            else:
                print(f'  [{i+1}] @{username}: ⚠️ Edge case — DB={db_followers:,}, Real={real["followers"]:,}')
            
            await asyncio.sleep(random.uniform(3, 5))
        
        await ctx.close()
        await browser.close()
    
    # Delete fakes
    if deleted_ids:
        print(f'\n🗑️ Deleting {len(deleted_ids)} fake entries...')
        for cid in deleted_ids:
            pids = [r[0] for r in conn.execute('SELECT id FROM platform_presences WHERE creator_id=?', (cid,)).fetchall()]
            for pid in pids:
                conn.execute('DELETE FROM metrics_history WHERE presence_id=?', (pid,))
            conn.execute('DELETE FROM content_samples WHERE creator_id=?', (cid,))
            conn.execute('DELETE FROM audit_scores WHERE creator_id=?', (cid,))
            conn.execute('DELETE FROM platform_presences WHERE creator_id=?', (cid,))
            conn.execute('DELETE FROM creators WHERE id=?', (cid,))
    
    conn.commit()
    
    total = conn.execute('SELECT COUNT(*) FROM creators').fetchone()[0]
    conn.close()
    
    # Log results
    result = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'sampled': len(creators),
        'verified': verified,
        'mismatched': mismatched,
        'not_found': not_found,
        'deleted': len(deleted_ids),
        'updated': updated,
        'total_in_db': total,
        'accuracy': f'{verified/max(1,len(creators)-not_found)*100:.0f}%'
    }
    
    with open(LOG_PATH, 'a') as f:
        f.write(json.dumps(result) + '\n')
    
    print(f'\n=== RESULTS ===')
    print(f'Verified: {verified}/{len(creators)}')
    print(f'Mismatched (deleted): {mismatched}')
    print(f'Not found (skipped): {not_found}')
    print(f'Data updated: {updated}')
    print(f'Accuracy: {result["accuracy"]}')
    print(f'Total in DB: {total}')

asyncio.run(main())
