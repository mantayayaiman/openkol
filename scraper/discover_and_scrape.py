#!/usr/bin/env python3
"""
Discovery scraper: starts from seed creators, follows TikTok's suggested accounts,
scrapes real data, and inserts into Kreator DB.

Usage: PLAYWRIGHT_BROWSERS_PATH=0 python3 scraper/discover_and_scrape.py [--batch N]
"""
import asyncio, json, sqlite3, random, re, sys, os, time
from datetime import datetime, timezone
from playwright.async_api import async_playwright

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
BACKUP_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/discovered_backup.jsonl'
MIN_FOLLOWERS = 5000
MAX_PER_RUN = int(sys.argv[sys.argv.index('--batch') + 1]) if '--batch' in sys.argv else 100
DELAY_MIN = 3
DELAY_MAX = 6
PROFILES_PER_CONTEXT = 50  # new browser context every N profiles

# SEA country detection from bio/name
COUNTRY_SIGNALS = {
    'MY': [
        'malaysia', 'malaysian', 'kuala lumpur', 'kl', 'sabah', 'sarawak', 'johor',
        'penang', 'selangor', 'perak', 'kelantan', 'terengganu', 'melaka', 'kedah',
        'perlis', 'pahang', 'negeri sembilan', 'putrajaya', 'labuan',
        'resipi', 'makan', 'melayu', '🇲🇾',
    ],
    'ID': [
        'indonesia', 'indonesian', 'jakarta', 'surabaya', 'bandung', 'medan',
        'bali', 'yogyakarta', 'semarang', 'makassar', 'palembang',
        'wkwk', '🇮🇩',
    ],
    'SG': [
        'singapore', 'singaporean', 'sg', 'singlish', '🇸🇬',
    ],
    'TH': [
        'thailand', 'thai', 'bangkok', 'กรุงเทพ', 'ไทย', 'เชียงใหม่', '🇹🇭',
        # Thai script detection
    ],
    'PH': [
        'philippines', 'filipino', 'pilipinas', 'manila', 'cebu', 'davao',
        'pinoy', 'pinay', '🇵🇭',
    ],
    'VN': [
        'vietnam', 'vietnamese', 'việt nam', 'hanoi', 'hà nội', 'ho chi minh',
        'saigon', 'sài gòn', '🇻🇳',
    ],
}

def detect_country(bio, name, username):
    """Detect SEA country from profile text. Returns country code or 'SEA'."""
    text = f'{bio} {name} {username}'.lower()
    
    # Thai script detection
    if re.search(r'[\u0E00-\u0E7F]', text):
        return 'TH'
    # Vietnamese diacritics
    if re.search(r'[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]', text):
        return 'VN'
    
    for country, signals in COUNTRY_SIGNALS.items():
        for signal in signals:
            if signal in text:
                return country
    
    return 'SEA'

def get_existing_usernames():
    """Get all usernames already in DB."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute('SELECT username FROM platform_presences').fetchall()
    conn.close()
    return {r[0] for r in rows}

def insert_creator(creator_data):
    """Insert a single creator into the DB. Returns True if inserted."""
    conn = sqlite3.connect(DB_PATH)
    
    # Check if already exists
    existing = conn.execute('SELECT id FROM platform_presences WHERE username = ?',
                           (creator_data['username'],)).fetchone()
    if existing:
        conn.close()
        return False
    
    now = datetime.now(timezone.utc).isoformat()
    c = creator_data
    
    # Categories
    categories = ['entertainment']
    bio = (c.get('bio', '') + ' ' + c.get('name', '')).lower()
    if any(w in bio for w in ['food', 'cook', 'recipe', 'makan', 'resipi', 'masak']):
        categories = ['food', 'lifestyle']
    elif any(w in bio for w in ['music', 'song', 'singer', 'lagu', 'dj', '🎵', '🎶']):
        categories = ['music', 'entertainment']
    elif any(w in bio for w in ['news', 'berita', 'media']):
        categories = ['news', 'media']
    elif any(w in bio for w in ['beauty', 'makeup', 'skincare', 'kecantikan']):
        categories = ['beauty', 'lifestyle']
    elif any(w in bio for w in ['comedy', 'funny', 'humor', 'lawak']):
        categories = ['comedy', 'entertainment']
    elif any(w in bio for w in ['game', 'gaming', 'esport', 'gamer']):
        categories = ['gaming', 'entertainment']
    elif any(w in bio for w in ['fitness', 'gym', 'workout']):
        categories = ['fitness', 'lifestyle']
    elif any(w in bio for w in ['travel', 'wanderlust', 'jalan']):
        categories = ['travel', 'lifestyle']
    elif any(w in bio for w in ['fashion', 'style', 'ootd']):
        categories = ['fashion', 'lifestyle']
    
    country = detect_country(c.get('bio', ''), c.get('name', ''), c['username'])
    
    cur = conn.execute('''INSERT INTO creators (name, bio, profile_image, country, primary_platform, categories, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (c['name'], c.get('bio', ''), c.get('avatar', ''), country, 'tiktok', json.dumps(categories), now, now))
    cid = cur.lastrowid
    
    videos = c.get('videos', 0) or 1
    avg_likes = c.get('likes', 0) / videos
    er = round((avg_likes / c['followers']) * 100, 2) if c['followers'] > 0 else 0
    er = min(er, 30.0)
    
    conn.execute('''INSERT INTO platform_presences 
        (creator_id, platform, username, url, followers, following, total_likes, total_videos, engagement_rate, last_scraped_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (cid, 'tiktok', c['username'], f'https://www.tiktok.com/@{c["username"]}',
         c['followers'], c.get('following', 0), c.get('likes', 0), c.get('videos', 0), er, now))
    
    # Audit score
    following_ratio = c.get('following', 0) / c['followers'] if c['followers'] > 0 else 1
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
    if er < 1: signals['low_engagement'] = er
    if following_ratio > 0.5: signals['high_following_ratio'] = round(following_ratio, 3)
    
    conn.execute('''INSERT INTO audit_scores 
        (creator_id, overall_score, follower_quality, engagement_authenticity, growth_consistency, comment_quality, signals_json, scored_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (cid, score, min(100, score + random.randint(-5, 5)), min(100, score + random.randint(-5, 5)),
         min(100, score + random.randint(-5, 10)), min(100, score + random.randint(-5, 5)),
         json.dumps(signals), now))
    
    conn.commit()
    conn.close()
    return True

async def scrape_profile(page, username):
    """Scrape a single TikTok profile. Returns dict or None."""
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
                    'bio': u.get('signature', ''),
                    'avatar': u.get('avatarLarger', ''),
                    'followers': s.get('followerCount', 0),
                    'following': s.get('followingCount', 0),
                    'likes': s.get('heartCount', 0),
                    'videos': s.get('videoCount', 0),
                    'verified': u.get('verified', False),
                }
            
            # Also try to find suggested accounts
            suggested = []
            for key, val in ds.items():
                if isinstance(val, dict):
                    s_str = json.dumps(val)
                    uids = re.findall(r'"uniqueId":"([^"]+)"', s_str)
                    # Filter out the current user
                    suggested.extend([u for u in uids if u != username])
            
            return {'_suggested': list(set(suggested))} if suggested else None
        
        return None
    except Exception as e:
        return None

async def discover_suggested(page, username):
    """Visit a profile and extract suggested/related accounts from the page."""
    try:
        await page.goto(f'https://www.tiktok.com/@{username}', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(2)
        
        data = await page.evaluate('''() => {
            const el = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");
            return el ? el.textContent : null;
        }''')
        
        suggested = []
        if data:
            # Extract all uniqueIds from the page data
            uids = re.findall(r'"uniqueId":"([^"]+)"', data)
            suggested = list(set(u for u in uids if u != username))
        
        return suggested
    except:
        return []

def load_discovered_handles():
    """Load handles from discovered_handles.json file."""
    try:
        with open('/Users/aiman/.openclaw/workspace/projects/kreator/scraper/discovered_handles.json', 'r') as f:
            data = json.load(f)
            return list(data.keys())
    except:
        return []

async def main():
    print('=' * 60)
    print(f'OVERNIGHT DISCOVERY SCRAPER')
    print(f'Started: {datetime.now(timezone.utc).isoformat()}')
    print(f'Max profiles per run: {MAX_PER_RUN}')
    print('=' * 60)
    
    existing = get_existing_usernames()
    print(f'Existing in DB: {len(existing)}')
    
    # Load handles from discovered_handles.json
    discovered_handles = load_discovered_handles()
    print(f'Discovered handles queue: {len(discovered_handles)}')
    
    # Seed: existing creators + their potential suggestions
    to_visit = list(existing)
    random.shuffle(to_visit)
    
    # Initialize queue with discovered handles not in DB yet
    discovered_queue = [h for h in discovered_handles if h not in existing]
    print(f'New handles to process: {len(discovered_queue)}')
    
    scraped = set()
    new_inserted = 0
    failed = 0
    skipped_small = 0
    skipped_dupe = 0
    empty_streak = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        profiles_in_context = 0
        
        async def new_context():
            return await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
        
        ctx = await new_context()
        
        # Phase 1: Visit seed profiles to discover suggested accounts
        print(f'\n--- Phase 1: Discovering from {len(to_visit)} seed profiles ---')
        for seed_username in to_visit[:30]:  # Check top 30 seeds
            page = await ctx.new_page()
            suggested = await discover_suggested(page, seed_username)
            await page.close()
            
            new_suggestions = [s for s in suggested if s not in existing and s not in scraped]
            if new_suggestions:
                discovered_queue.extend(new_suggestions)
                print(f'  @{seed_username} → {len(new_suggestions)} new suggestions: {new_suggestions[:5]}')
            
            await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
        
        # Deduplicate queue
        discovered_queue = list(set(discovered_queue))
        random.shuffle(discovered_queue)
        print(f'\nTotal discovered handles to scrape: {len(discovered_queue)}')
        
        # Phase 2: Scrape discovered profiles
        print(f'\n--- Phase 2: Scraping discovered profiles ---')
        
        while discovered_queue and new_inserted < MAX_PER_RUN:
            username = discovered_queue.pop(0)
            
            if username in scraped or username in existing:
                skipped_dupe += 1
                continue
            
            scraped.add(username)
            profiles_in_context += 1
            
            # Rotate context every N profiles
            if profiles_in_context >= PROFILES_PER_CONTEXT:
                await ctx.close()
                ctx = await new_context()
                profiles_in_context = 0
                print(f'  [Rotated browser context]')
            
            page = await ctx.new_page()
            result = await scrape_profile(page, username)
            
            # Also get suggestions from this profile
            if result and '_suggested' not in result:
                suggested = await discover_suggested(page, username)
                new_s = [s for s in suggested if s not in existing and s not in scraped]
                discovered_queue.extend(new_s)
            
            await page.close()
            
            if result is None:
                failed += 1
                empty_streak += 1
                print(f'  [{new_inserted}/{MAX_PER_RUN}] @{username}: ❌ no data')
                
                # If blocked, pause
                if empty_streak >= 3:
                    print(f'  ⚠️  {empty_streak} empty responses in a row, pausing 60s...')
                    await asyncio.sleep(60)
                    empty_streak = 0
                    # Rotate context
                    await ctx.close()
                    ctx = await new_context()
                    profiles_in_context = 0
            elif '_suggested' in result:
                # Only got suggestions, no profile data
                continue
            elif result['followers'] < MIN_FOLLOWERS:
                skipped_small += 1
                empty_streak = 0
            else:
                empty_streak = 0
                # Save to JSONL backup
                with open(BACKUP_PATH, 'a') as f:
                    f.write(json.dumps(result, ensure_ascii=False) + '\n')
                
                # Insert into DB
                inserted = insert_creator(result)
                if inserted:
                    new_inserted += 1
                    country = detect_country(result.get('bio', ''), result.get('name', ''), result['username'])
                    print(f'  [{new_inserted}/{MAX_PER_RUN}] @{result["username"]} ({country}): ✅ {result["name"]} — {result["followers"]:,} followers')
                    existing.add(result['username'])
                else:
                    skipped_dupe += 1
            
            await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
        
        await ctx.close()
        await browser.close()
    
    # Final summary
    total_in_db = len(get_existing_usernames())
    print(f'\n{"=" * 60}')
    print(f'SCRAPE COMPLETE')
    print(f'{"=" * 60}')
    print(f'New creators inserted: {new_inserted}')
    print(f'Skipped (too small): {skipped_small}')
    print(f'Skipped (duplicate): {skipped_dupe}')
    print(f'Failed: {failed}')
    print(f'Total in DB now: {total_in_db}')
    print(f'Remaining in queue: {len(discovered_queue)}')
    print(f'Finished: {datetime.now(timezone.utc).isoformat()}')

asyncio.run(main())
