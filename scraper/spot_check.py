#!/usr/bin/env python3
"""
Spot checker: runs every hour via cron.
1. Pick 5 random recently-added creators
2. Re-verify on TikTok
3. Delete fakes, update real ones with fresh data
4. Log accuracy rate
5. If accuracy < 80%, flag alert
"""
import asyncio, json, sqlite3, random, sys
from datetime import datetime, timezone
from playwright.async_api import async_playwright

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
SPOT_LOG = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/spot_check.jsonl'
SAMPLE_SIZE = 5

async def verify_on_tiktok(username):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = await ctx.new_page()
        try:
            await page.goto(f'https://www.tiktok.com/@{username}', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            data = await page.evaluate('() => { const el = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__"); return el ? el.textContent : null; }')
            if data:
                import re
                parsed = json.loads(data)
                ud = parsed.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {})
                if 'userInfo' in ud:
                    s = ud['userInfo']['stats']
                    return {
                        'followers': s.get('followerCount', 0),
                        'likes': s.get('heartCount', 0),
                        'videos': s.get('videoCount', 0),
                    }
            return None
        except:
            return None
        finally:
            await page.close()
            await ctx.close()
            await browser.close()

async def main():
    now = datetime.now(timezone.utc).isoformat()
    print(f'=== SPOT CHECK {now} ===')
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Get recent creators (prioritize recently added)
    creators = conn.execute('''
        SELECT c.id, c.name, pp.username, pp.followers, pp.total_likes
        FROM creators c
        JOIN platform_presences pp ON pp.creator_id = c.id
        ORDER BY c.created_at DESC
        LIMIT 20
    ''').fetchall()
    
    if len(creators) < SAMPLE_SIZE:
        sample = list(creators)
    else:
        sample = random.sample(list(creators), SAMPLE_SIZE)
    
    verified = 0
    fake = 0
    errors = 0
    deleted_ids = []
    
    for c in sample:
        real = await verify_on_tiktok(c['username'])
        
        if real is None:
            print(f'  @{c["username"]}: ⚠️ Could not verify (skip)')
            errors += 1
        elif real['followers'] == 0 and c['followers'] > 10000:
            print(f'  @{c["username"]}: ❌ FAKE — DB={c["followers"]:,} Real=0')
            fake += 1
            deleted_ids.append(c['id'])
        elif c['followers'] > 0 and real['followers'] > 0:
            ratio = real['followers'] / c['followers']
            if 0.3 <= ratio <= 3.0:
                print(f'  @{c["username"]}: ✅ MATCH — DB={c["followers"]:,} Real={real["followers"]:,}')
                verified += 1
                # Update with fresh data
                conn.execute('UPDATE platform_presences SET followers=?, total_likes=?, last_scraped_at=? WHERE creator_id=?',
                    (real['followers'], real['likes'], now, c['id']))
            else:
                print(f'  @{c["username"]}: ❌ MISMATCH — DB={c["followers"]:,} Real={real["followers"]:,} (ratio={ratio:.1f}x)')
                fake += 1
                deleted_ids.append(c['id'])
        else:
            print(f'  @{c["username"]}: ⚠️ Edge case')
            errors += 1
        
        await asyncio.sleep(random.uniform(3, 5))
    
    # Delete fakes
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
    
    checkable = verified + fake
    accuracy = round(verified / checkable * 100) if checkable > 0 else 0
    
    result = {
        'timestamp': now,
        'sampled': len(sample),
        'verified': verified,
        'fake_deleted': fake,
        'errors': errors,
        'accuracy': accuracy,
        'total_in_db': total,
    }
    
    with open(SPOT_LOG, 'a') as f:
        f.write(json.dumps(result) + '\n')
    
    print(f'\nRESULT: {accuracy}% accuracy ({verified}/{checkable}) | Deleted {fake} fakes | DB: {total}')
    
    if accuracy < 80 and checkable > 0:
        print('⚠️ ALERT: Accuracy below 80%! Scraper may be producing bad data.')

if __name__ == '__main__':
    asyncio.run(main())
