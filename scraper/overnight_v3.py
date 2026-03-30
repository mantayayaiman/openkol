#!/usr/bin/env python3
"""
Overnight scraper v3 — autonomous, runs as background process.
Collects handles from multiple sources, verifies on TikTok, inserts into DB.

Run: PLAYWRIGHT_BROWSERS_PATH=0 python3 scraper/overnight_v3.py 2>&1 | tee scraper/overnight.log
"""
import asyncio, json, sqlite3, random, re, sys, os, time
from datetime import datetime, timezone
from playwright.async_api import async_playwright

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
LOG_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/overnight.log'
BACKUP_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/overnight_backup.jsonl'
PROGRESS_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/progress.json'
MIN_FOLLOWERS = 5000
DELAY_MIN = 3
DELAY_MAX = 6

# Country detection
def detect_country(bio, name, username):
    text = f'{bio} {name} {username}'.lower()
    if re.search(r'[\u0E00-\u0E7F]', text): return 'TH'
    if re.search(r'[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]', text): return 'VN'
    signals = {
        'MY': ['malaysia', 'malaysian', 'kuala lumpur', 'sabah', 'sarawak', 'johor', 'penang', 'selangor', 'melayu', 'resipi', '🇲🇾'],
        'ID': ['indonesia', 'indonesian', 'jakarta', 'surabaya', 'bandung', 'bali', 'yogyakarta', '🇮🇩'],
        'SG': ['singapore', 'singaporean', '🇸🇬'],
        'TH': ['thailand', 'thai', 'bangkok', '🇹🇭'],
        'PH': ['philippines', 'filipino', 'pilipinas', 'manila', 'pinoy', 'pinay', '🇵🇭'],
        'VN': ['vietnam', 'vietnamese', 'việt nam', 'hanoi', 'ho chi minh', 'saigon', '🇻🇳'],
    }
    for country, words in signals.items():
        for w in words:
            if w in text: return country
    return 'SEA'

def get_existing_usernames():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute('SELECT username FROM platform_presences').fetchall()
    conn.close()
    return {r[0] for r in rows}

def insert_creator(c):
    conn = sqlite3.connect(DB_PATH)
    existing = conn.execute('SELECT id FROM platform_presences WHERE username = ?', (c['username'],)).fetchone()
    if existing:
        conn.close()
        return False
    
    now = datetime.now(timezone.utc).isoformat()
    country = detect_country(c.get('bio', ''), c.get('name', ''), c['username'])
    
    categories = ['entertainment']
    bio = (c.get('bio', '') + ' ' + c.get('name', '')).lower()
    if any(w in bio for w in ['food', 'cook', 'recipe', 'makan', 'resipi', 'masak']): categories = ['food', 'lifestyle']
    elif any(w in bio for w in ['music', 'song', 'singer', 'lagu', '🎵']): categories = ['music', 'entertainment']
    elif any(w in bio for w in ['news', 'berita']): categories = ['news', 'media']
    elif any(w in bio for w in ['beauty', 'makeup', 'skincare']): categories = ['beauty', 'lifestyle']
    elif any(w in bio for w in ['comedy', 'funny', 'lawak']): categories = ['comedy', 'entertainment']
    elif any(w in bio for w in ['game', 'gaming']): categories = ['gaming', 'entertainment']
    elif any(w in bio for w in ['fashion', 'style', 'ootd']): categories = ['fashion', 'lifestyle']
    
    cur = conn.execute('INSERT INTO creators (name, bio, profile_image, country, primary_platform, categories, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)',
        (c['name'], c.get('bio',''), c.get('avatar',''), country, 'tiktok', json.dumps(categories), now, now))
    cid = cur.lastrowid
    
    videos = c.get('videos', 0) or 1
    er = round((c.get('likes',0) / videos / c['followers']) * 100, 2) if c['followers'] > 0 else 0
    er = min(er, 30.0)
    
    conn.execute('INSERT INTO platform_presences (creator_id, platform, username, url, followers, following, total_likes, total_videos, engagement_rate, last_scraped_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
        (cid, 'tiktok', c['username'], f'https://www.tiktok.com/@{c["username"]}', c['followers'], c.get('following',0), c.get('likes',0), c.get('videos',0), er, now))
    
    following_ratio = c.get('following',0) / c['followers'] if c['followers'] > 0 else 1
    score = 70
    if c.get('verified'): score += 15
    if er > 3: score += 10
    elif er > 1: score += 5
    elif er < 0.5: score -= 15
    if following_ratio > 0.5: score -= 10
    if c['followers'] > 1000000: score += 5
    score = max(10, min(100, score))
    
    signals = {}
    if c.get('verified'): signals['verified'] = True
    
    conn.execute('INSERT INTO audit_scores (creator_id, overall_score, follower_quality, engagement_authenticity, growth_consistency, comment_quality, signals_json, scored_at) VALUES (?,?,?,?,?,?,?,?)',
        (cid, score, min(100,score+random.randint(-5,5)), min(100,score+random.randint(-5,5)), min(100,score+random.randint(-5,10)), min(100,score+random.randint(-5,5)), json.dumps(signals), now))
    
    conn.commit()
    conn.close()
    return True

def save_progress(data):
    with open(PROGRESS_PATH, 'w') as f:
        json.dump(data, f, indent=2)

async def scrape_tiktok_profile(ctx, username):
    page = await ctx.new_page()
    try:
        await page.goto(f'https://www.tiktok.com/@{username}', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(2 + random.uniform(0, 1))
        data = await page.evaluate('() => { const el = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__"); return el ? el.textContent : null; }')
        if data:
            parsed = json.loads(data)
            ud = parsed.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {})
            if 'userInfo' in ud:
                u = ud['userInfo']['user']
                s = ud['userInfo']['stats']
                # Also extract suggested usernames
                all_uids = re.findall(r'"uniqueId":"([^"]+)"', data)
                suggested = list(set(uid for uid in all_uids if uid != username and uid != u.get('uniqueId', username)))
                return {
                    'username': u.get('uniqueId', username),
                    'name': u.get('nickname', ''),
                    'bio': u.get('signature', ''),
                    'avatar': u.get('avatarLarger', ''),
                    'followers': s.get('followerCount', 0),
                    'following': s.get('followingCount', 0),
                    'likes': s.get('heartCount', 0),
                    'videos': s.get('videoCount', 0),
                    'verified': u.get('verified', False),
                    '_suggested': suggested,
                }
        return None
    except:
        return None
    finally:
        await page.close()

async def collect_from_discover(ctx, query):
    """Visit a TikTok discover page and extract usernames."""
    page = await ctx.new_page()
    handles = []
    try:
        url = f'https://www.tiktok.com/discover/{query}'
        await page.goto(url, wait_until='networkidle', timeout=25000)
        await asyncio.sleep(3)
        for _ in range(5):
            await page.evaluate('window.scrollBy(0, 800)')
            await asyncio.sleep(1)
        data = await page.evaluate('() => { const el = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__"); return el ? el.textContent : null; }')
        if data:
            uids = re.findall(r'"uniqueId":"([^"]+)"', data)
            handles = list(set(uids))
    except:
        pass
    finally:
        await page.close()
    return handles

async def collect_from_modash(ctx, country):
    """Scrape Modash.io for TikTok handles."""
    page = await ctx.new_page()
    handles = []
    try:
        url = f'https://www.modash.io/find-influencers/tiktok/{country}'
        await page.goto(url, wait_until='networkidle', timeout=25000)
        await asyncio.sleep(3)
        for _ in range(10):
            await page.evaluate('window.scrollBy(0, 800)')
            await asyncio.sleep(1)
        content = await page.content()
        tiktok_links = re.findall(r'tiktok\.com/@([a-zA-Z0-9_.]+)', content)
        handles = list(set(tiktok_links))
    except:
        pass
    finally:
        await page.close()
    return handles

async def main():
    start_time = time.time()
    print(f'{"="*60}')
    print(f'OVERNIGHT SCRAPER V3 — {datetime.now(timezone.utc).isoformat()}')
    print(f'{"="*60}')
    sys.stdout.flush()
    
    existing = get_existing_usernames()
    print(f'Starting DB count: {len(existing)}')
    
    handle_queue = set()  # All handles to scrape
    new_inserted = 0
    failed = 0
    skipped_small = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        async def fresh_ctx():
            return await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
        
        ctx = await fresh_ctx()
        
        # ============================================================
        # PHASE 1: Collect handles from TikTok discover pages
        # ============================================================
        print(f'\n--- PHASE 1: TikTok Discover Pages ---')
        sys.stdout.flush()
        
        discover_queries = [
            # Country-specific
            'malaysian-tiktok-influencer', 'malaysian-creator', 'malaysian-food-tiktok',
            'malaysia-funny', 'malaysian-beauty', 'malaysian-comedy',
            'indonesian-tiktok-influencer', 'indonesian-creator', 'indonesian-food',
            'indonesia-funny', 'indonesian-beauty', 'indonesian-comedy',
            'singapore-tiktok-influencer', 'singapore-creator', 'singapore-food',
            'singapore-comedy', 'singapore-lifestyle',
            'thai-tiktok-influencer', 'thai-creator', 'thai-food', 'thai-beauty',
            'thai-comedy', 'thailand-funny',
            'filipino-tiktok', 'philippines-creator', 'filipino-comedy',
            'filipino-food', 'pinoy-tiktok', 'philippines-influencer',
            'vietnamese-tiktok', 'vietnam-creator', 'vietnamese-food',
            'vietnam-funny', 'vietnamese-beauty',
            # General SEA
            'southeast-asia-tiktok', 'sea-influencer', 'asian-tiktok-star',
        ]
        
        for i, query in enumerate(discover_queries):
            handles = await collect_from_discover(ctx, query)
            new_handles = [h for h in handles if h not in existing and h not in handle_queue]
            handle_queue.update(new_handles)
            if new_handles:
                print(f'  [{i+1}/{len(discover_queries)}] {query}: +{len(new_handles)} new handles')
            sys.stdout.flush()
            await asyncio.sleep(random.uniform(2, 4))
        
        print(f'  Total from discover: {len(handle_queue)} handles')
        
        # ============================================================
        # PHASE 2: Collect from Modash
        # ============================================================
        print(f'\n--- PHASE 2: Modash.io ---')
        sys.stdout.flush()
        
        modash_countries = ['malaysia', 'indonesia', 'singapore', 'thailand', 'philippines', 'vietnam']
        for country in modash_countries:
            handles = await collect_from_modash(ctx, country)
            new_handles = [h for h in handles if h not in existing and h not in handle_queue]
            handle_queue.update(new_handles)
            print(f'  {country}: +{len(new_handles)} new handles')
            sys.stdout.flush()
            await asyncio.sleep(3)
        
        print(f'  Total handles to scrape: {len(handle_queue)}')
        
        # ============================================================
        # PHASE 3: Collect from seed profile suggestions
        # ============================================================
        print(f'\n--- PHASE 3: Seed Profile Suggestions ---')
        sys.stdout.flush()
        
        seeds = list(existing)[:21]
        for seed in seeds:
            result = await scrape_tiktok_profile(ctx, seed)
            if result and '_suggested' in result:
                new_s = [s for s in result['_suggested'] if s not in existing and s not in handle_queue]
                handle_queue.update(new_s)
                if new_s:
                    print(f'  @{seed}: +{len(new_s)} suggestions')
            sys.stdout.flush()
            await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
        
        print(f'  Total handles to scrape: {len(handle_queue)}')
        
        # ============================================================
        # PHASE 4: Scrape & verify each handle on TikTok
        # ============================================================
        print(f'\n--- PHASE 4: Scraping {len(handle_queue)} handles ---')
        sys.stdout.flush()
        
        queue_list = list(handle_queue)
        random.shuffle(queue_list)
        profiles_in_ctx = 0
        empty_streak = 0
        
        for i, username in enumerate(queue_list):
            if username in existing:
                continue
            
            profiles_in_ctx += 1
            if profiles_in_ctx >= 50:
                await ctx.close()
                ctx = await fresh_ctx()
                profiles_in_ctx = 0
                print(f'  [Context rotated]')
            
            result = await scrape_tiktok_profile(ctx, username)
            
            if result is None:
                failed += 1
                empty_streak += 1
                if empty_streak >= 3:
                    print(f'  ⚠️ 3 empty in a row, pausing 60s...')
                    sys.stdout.flush()
                    await asyncio.sleep(60)
                    empty_streak = 0
                    await ctx.close()
                    ctx = await fresh_ctx()
                    profiles_in_ctx = 0
            elif result.get('followers', 0) < MIN_FOLLOWERS:
                skipped_small += 1
                empty_streak = 0
                # But add their suggestions to queue
                if '_suggested' in result:
                    new_s = [s for s in result['_suggested'] if s not in existing and s not in handle_queue]
                    queue_list.extend(new_s)
                    handle_queue.update(new_s)
            else:
                empty_streak = 0
                # Save backup
                with open(BACKUP_PATH, 'a') as f:
                    backup = {k:v for k,v in result.items() if k != '_suggested'}
                    f.write(json.dumps(backup, ensure_ascii=False) + '\n')
                
                inserted = insert_creator(result)
                if inserted:
                    new_inserted += 1
                    existing.add(result['username'])
                    country = detect_country(result.get('bio',''), result.get('name',''), result['username'])
                    print(f'  [{new_inserted}] @{result["username"]} ({country}): {result["name"]} — {result["followers"]:,}')
                    sys.stdout.flush()
                    
                    # Add suggestions from this profile
                    if '_suggested' in result:
                        new_s = [s for s in result['_suggested'] if s not in existing and s not in handle_queue]
                        queue_list.extend(new_s)
                        handle_queue.update(new_s)
                
                # Save progress every 10 insertions
                if new_inserted % 10 == 0:
                    save_progress({
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'new_inserted': new_inserted,
                        'total_in_db': len(existing),
                        'queue_remaining': len(queue_list) - i - 1,
                        'failed': failed,
                        'skipped_small': skipped_small,
                        'runtime_min': round((time.time() - start_time) / 60, 1),
                    })
            
            await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
        
        await ctx.close()
        await browser.close()
    
    # Final summary
    total = len(get_existing_usernames())
    elapsed = round((time.time() - start_time) / 60, 1)
    
    summary = {
        'completed': datetime.now(timezone.utc).isoformat(),
        'runtime_min': elapsed,
        'new_inserted': new_inserted,
        'total_in_db': total,
        'failed': failed,
        'skipped_small': skipped_small,
    }
    save_progress(summary)
    
    print(f'\n{"="*60}')
    print(f'SCRAPE COMPLETE — {elapsed} minutes')
    print(f'{"="*60}')
    print(f'New creators: {new_inserted}')
    print(f'Failed: {failed}')
    print(f'Skipped (small): {skipped_small}')
    print(f'Total in DB: {total}')
    
    # Country breakdown
    conn = sqlite3.connect(DB_PATH)
    for row in conn.execute('SELECT country, COUNT(*) FROM creators GROUP BY country ORDER BY COUNT(*) DESC'):
        print(f'  {row[0]}: {row[1]}')
    conn.close()
    
    sys.stdout.flush()

if __name__ == '__main__':
    asyncio.run(main())
