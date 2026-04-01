#!/usr/bin/env python3
"""
Instagram scraper v2: Discovers and scrapes SEA creator profiles from Instagram.
Uses Playwright with mobile UA rotation, exponential backoff, and proper resumption.

Run: PLAYWRIGHT_BROWSERS_PATH=0 python3 -u scraper/instagram_scraper.py >> scraper/ig_overnight.log 2>&1
"""
import asyncio
import json
import sqlite3
import random
import re
import sys
import time
import os
from datetime import datetime, timezone
from playwright.async_api import async_playwright

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
BACKUP_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/ig_backup.jsonl'
PROGRESS_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/ig_progress.json'
MIN_FOLLOWERS = 5000
DELAY_MIN = 8
DELAY_MAX = 15

# Mobile user agents for rotation
MOBILE_UAS = [
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/121.0.6167.171 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.64 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.64 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 13; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.178 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 14; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.64 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1',
]

def random_ua():
    return random.choice(MOBILE_UAS)

def detect_country(bio, name, username):
    text = f'{bio} {name} {username}'.lower()
    if re.search(r'[\u0E00-\u0E7F]', text): return 'TH'
    if re.search(r'[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]', text): return 'VN'
    signals = {
        'MY': ['malaysia', 'kuala lumpur', 'sabah', 'sarawak', 'johor', 'penang', 'selangor', 'melayu', '🇲🇾'],
        'ID': ['indonesia', 'jakarta', 'surabaya', 'bandung', 'bali', 'yogyakarta', '🇮🇩'],
        'SG': ['singapore', '🇸🇬'],
        'TH': ['thailand', 'thai', 'bangkok', '🇹🇭'],
        'PH': ['philippines', 'filipino', 'pilipinas', 'manila', 'pinoy', '🇵🇭'],
        'VN': ['vietnam', 'việt nam', 'hanoi', 'ho chi minh', 'saigon', '🇻🇳'],
    }
    for country, words in signals.items():
        for w in words:
            if w in text: return country
    return 'SEA'

def parse_count(s):
    if not s: return 0
    s = str(s).replace(',', '').strip()
    if 'K' in s or 'k' in s:
        return int(float(s.upper().replace('K','')) * 1000)
    if 'M' in s or 'm' in s:
        return int(float(s.upper().replace('M','')) * 1000000)
    if 'B' in s or 'b' in s:
        return int(float(s.upper().replace('B','')) * 1000000000)
    try:
        return int(float(s))
    except:
        return 0

def get_existing_ig_usernames():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT username FROM platform_presences WHERE platform = 'instagram'").fetchall()
    conn.close()
    return {r[0] for r in rows}

def get_existing_creator_names():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute('SELECT id, name, country FROM creators').fetchall()
    conn.close()
    return {r[1].lower(): (r[0], r[2]) for r in rows}

def load_progress():
    """Load scraping progress - which handles we've already attempted."""
    if os.path.exists(PROGRESS_PATH):
        try:
            with open(PROGRESS_PATH, 'r') as f:
                return json.load(f)
        except:
            pass
    return {'attempted': [], 'failed': [], 'succeeded': []}

def save_progress(progress):
    with open(PROGRESS_PATH, 'w') as f:
        json.dump(progress, f)

def insert_ig_creator(c):
    conn = sqlite3.connect(DB_PATH)
    existing = conn.execute("SELECT id FROM platform_presences WHERE platform = 'instagram' AND username = ?", (c['username'],)).fetchone()
    if existing:
        conn.close()
        return False
    
    now = datetime.now(timezone.utc).isoformat()
    country = detect_country(c.get('bio', ''), c.get('name', ''), c['username'])
    
    existing_creators = get_existing_creator_names()
    name_lower = c.get('name', '').lower()
    
    creator_id = None
    if name_lower and name_lower in existing_creators:
        creator_id = existing_creators[name_lower][0]
        country = existing_creators[name_lower][1]
    
    if creator_id is None:
        categories = ['entertainment']
        bio = (c.get('bio', '') + ' ' + c.get('name', '')).lower()
        if any(w in bio for w in ['food', 'cook', 'recipe', 'makan']): categories = ['food', 'lifestyle']
        elif any(w in bio for w in ['music', 'song', 'singer']): categories = ['music', 'entertainment']
        elif any(w in bio for w in ['beauty', 'makeup']): categories = ['beauty', 'lifestyle']
        elif any(w in bio for w in ['comedy', 'funny']): categories = ['comedy', 'entertainment']
        elif any(w in bio for w in ['fashion', 'style']): categories = ['fashion', 'lifestyle']
        elif any(w in bio for w in ['gaming', 'game', 'esport']): categories = ['gaming', 'entertainment']
        
        cur = conn.execute('INSERT INTO creators (name, bio, profile_image, country, primary_platform, categories, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)',
            (c['name'], c.get('bio',''), c.get('avatar',''), country, 'instagram', json.dumps(categories), now, now))
        creator_id = cur.lastrowid
    
    er = round(c.get('engagement_rate', 0), 2)
    
    conn.execute('INSERT INTO platform_presences (creator_id, platform, username, url, followers, following, total_likes, total_videos, engagement_rate, last_scraped_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
        (creator_id, 'instagram', c['username'], f'https://www.instagram.com/{c["username"]}/',
         c['followers'], c.get('following', 0), 0, c.get('posts', 0), er, now))
    
    conn.commit()
    conn.close()
    return True

async def make_fresh_context(browser):
    """Create a fresh browser context with random mobile UA."""
    ua = random_ua()
    is_iphone = 'iPhone' in ua
    ctx = await browser.new_context(
        user_agent=ua,
        viewport={'width': 390, 'height': 844} if is_iphone else {'width': 412, 'height': 915},
        device_scale_factor=3 if is_iphone else 2.625,
        is_mobile=True,
        has_touch=True,
        locale='en-US',
    )
    return ctx

async def scrape_ig_profile(ctx, username):
    """Scrape an Instagram profile using mobile web (i.instagram.com is lighter)."""
    page = await ctx.new_page()
    try:
        # Go directly to the mobile profile page
        url = f'https://www.instagram.com/{username}/'
        resp = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        
        if resp and resp.status == 404:
            return 'not_found'
        
        # Wait a bit for content to load
        await asyncio.sleep(random.uniform(2, 4))
        
        # Check if we got a login wall / challenge
        page_text = await page.text_content('body') or ''
        if 'Log in' in page_text and len(page_text) < 500:
            # Likely a login wall
            return None
        
        content = await page.content()
        
        # Strategy 1: Extract from meta description tag
        # Format: "X Followers, Y Following, Z Posts - See Instagram photos and videos from Name (@username)"
        meta_desc = ''
        meta_el = await page.query_selector('meta[name="description"]')
        if meta_el:
            meta_desc = await meta_el.get_attribute('content') or ''
        
        if not meta_desc:
            # Try og:description
            og_el = await page.query_selector('meta[property="og:description"]')
            if og_el:
                meta_desc = await og_el.get_attribute('content') or ''
        
        followers = 0
        following = 0
        posts = 0
        name = ''
        bio = ''
        avatar = ''
        
        if meta_desc:
            # Parse: "1.2M Followers, 500 Following, 200 Posts - ..."
            f_match = re.search(r'([\d,.]+[KMBkmb]?)\s*Followers', meta_desc)
            fw_match = re.search(r'([\d,.]+[KMBkmb]?)\s*Following', meta_desc)
            p_match = re.search(r'([\d,.]+[KMBkmb]?)\s*Posts', meta_desc)
            
            if f_match:
                followers = parse_count(f_match.group(1))
            if fw_match:
                following = parse_count(fw_match.group(1))
            if p_match:
                posts = parse_count(p_match.group(1))
            
            # Name from meta: "... from Name (@username)"
            name_match = re.search(r'from\s+(.+?)\s*\(@', meta_desc)
            if name_match:
                name = name_match.group(1).strip()
        
        # Strategy 2: Extract from JSON in page (shared data, additional data)
        if followers == 0:
            json_matches = re.findall(r'"edge_followed_by":\{"count":(\d+)\}', content)
            if json_matches:
                followers = int(json_matches[0])
            
            json_matches2 = re.findall(r'"edge_follow":\{"count":(\d+)\}', content)
            if json_matches2:
                following = int(json_matches2[0])
        
        # Strategy 3: Try to get from og:title
        if not name:
            title = await page.title()
            # Title format: "Name (@username) • Instagram photos and videos"
            title_match = re.match(r'(.+?)\s*[\(@•]', title)
            if title_match:
                name = title_match.group(1).strip()
        
        # Strategy 4: Look for JSON-LD or embedded data
        if followers == 0:
            # Try to find follower count in any JSON blob
            fc_matches = re.findall(r'"follower_count"\s*:\s*(\d+)', content)
            if fc_matches:
                followers = int(fc_matches[0])
            fc_matches2 = re.findall(r'"following_count"\s*:\s*(\d+)', content)
            if fc_matches2:
                following = int(fc_matches2[0])
            fc_matches3 = re.findall(r'"media_count"\s*:\s*(\d+)', content)
            if fc_matches3:
                posts = int(fc_matches3[0])
        
        # Get bio from page content
        if not bio:
            bio_match = re.search(r'"biography"\s*:\s*"([^"]*)"', content)
            if bio_match:
                bio = bio_match.group(1)[:300]
        
        # Get full name from JSON if not found
        if not name:
            name_match = re.search(r'"full_name"\s*:\s*"([^"]*)"', content)
            if name_match:
                name = name_match.group(1)
        
        # Avatar
        avatar_match = re.search(r'"profile_pic_url(?:_hd)?"\s*:\s*"([^"]+)"', content)
        if avatar_match:
            avatar = avatar_match.group(1).replace('\\u0026', '&')
        
        if not name:
            name = username
        
        if followers > 0:
            return {
                'username': username,
                'name': name,
                'bio': bio,
                'avatar': avatar,
                'followers': followers,
                'following': following,
                'posts': posts,
                'verified': False,
            }
        
        return None
    except Exception as e:
        print(f'    Error scraping @{username}: {type(e).__name__}: {e}', file=sys.stderr)
        sys.stderr.flush()
        return None
    finally:
        await page.close()

async def collect_ig_handles_from_google(ctx):
    """Use Google to find IG handles for SEA influencers."""
    handles = set()
    queries = [
        'site:instagram.com malaysia influencer',
        'site:instagram.com indonesia influencer',
        'site:instagram.com singapore influencer',
        'site:instagram.com thailand influencer',
        'site:instagram.com philippines influencer',
        'site:instagram.com vietnam influencer',
        'top instagram influencers malaysia 2025',
        'top instagram influencers indonesia 2025',
        'top instagram influencers singapore 2025',
        'instagram malaysia content creator',
        'instagram indonesia content creator popular',
    ]
    
    for query in queries:
        page = await ctx.new_page()
        try:
            await page.goto(f'https://www.google.com/search?q={query}&num=30', wait_until='domcontentloaded', timeout=20000)
            await asyncio.sleep(random.uniform(2, 4))
            content = await page.content()
            ig_handles = re.findall(r'instagram\.com/([a-zA-Z0-9_.]+)', content)
            ig_handles = [h for h in set(ig_handles) if h not in ('p', 'explore', 'reel', 'reels', 'stories', 'accounts', 'about', 'directory', 'tv', 'accounts')]
            new_h = [h for h in ig_handles if h not in handles]
            handles.update(new_h)
            if new_h:
                print(f'  Google [{query[:45]}]: +{len(new_h)} handles')
        except Exception as e:
            print(f'  Google [{query[:45]}]: error - {e}')
        finally:
            await page.close()
        await asyncio.sleep(random.uniform(5, 10))
    
    return handles

async def main():
    start = time.time()
    print(f'{"="*60}')
    print(f'INSTAGRAM SCRAPER v2 — {datetime.now(timezone.utc).isoformat()}')
    print(f'{"="*60}')
    sys.stdout.flush()
    
    existing_ig = get_existing_ig_usernames()
    print(f'Existing IG profiles in DB: {len(existing_ig)}')
    
    progress = load_progress()
    attempted_set = set(progress.get('attempted', []))
    print(f'Previously attempted: {len(attempted_set)}')
    sys.stdout.flush()
    
    handle_queue = set()
    new_inserted = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await make_fresh_context(browser)
        
        # Phase 1: Get handles from TikTok creator bios
        print('\n--- Phase 1: Extract IG handles from TikTok bios ---')
        conn = sqlite3.connect(DB_PATH)
        creators = conn.execute('SELECT name, bio FROM creators').fetchall()
        conn.close()
        bio_handles = set()
        for name, bio_text in creators:
            ig_matches = re.findall(r'(?:ig|instagram|insta)[:\s@]*([a-zA-Z0-9_.]+)', (bio_text or '').lower())
            for h in ig_matches:
                if len(h) > 2:
                    bio_handles.add(h)
        handle_queue.update(bio_handles - existing_ig - attempted_set)
        print(f'  From bios: {len(bio_handles)} handles ({len(bio_handles - existing_ig - attempted_set)} new)')
        sys.stdout.flush()
        
        # Phase 2: Google search for IG handles
        print('\n--- Phase 2: Google Search ---')
        google_handles = await collect_ig_handles_from_google(ctx)
        handle_queue.update(google_handles - existing_ig - attempted_set)
        print(f'  From Google: {len(google_handles)} handles ({len(google_handles - existing_ig - attempted_set)} new)')
        sys.stdout.flush()
        
        # Phase 3: Known SEA IG handles (verified famous accounts)
        known_ig = [
            # MY
            'vivy_yusof', 'elfira_loy', 'neelofa', 'jinnyboytv', 'dfrntfaces',
            'hairulazreen', 'bellngasri', 'afieqshazwan', 'shaheizy', 'mirafihzah',
            'wanyhaserita', 'fazleyakinmee', 'shukshazwan', 'luqmanpodolski',
            'khaborr_aming', 'khairulaming', 'syedabdulkadir',
            # ID
            'riaricis1795', 'gadiiing', 'fadiljaidi', 'jessica.iskandar',
            'gisel_la', 'raikiertakelmulya', 'attahalilintar', 'nagitaslavina',
            'rafaborrahmad1717', 'raffi_nagita1717',
            # SG
            'jianhaotan', 'naomineo_', 'xiaxue', 'sylvia_channel', 'wahbanana_jian',
            'andreadechocolate', 'mongabong',
            # TH
            'bambam1a', 'davikah', 'pimrypie', 'lalisa', 'maborrlalisa',
            # PH
            'mimiyuuuh', 'andreabrillantes', 'bellemariano02', 'donny',
            'ivanaalawi', 'alexagonzaga',
            # VN
            'sontungmtp', 'chi.pu',
        ]
        # Filter any remaining corrupted entries
        known_ig_clean = [h for h in known_ig if 'aborr' not in h and len(h) > 2]
        for h in known_ig_clean:
            if h not in existing_ig and h not in attempted_set:
                handle_queue.add(h)
        
        # Also use TikTok usernames as potential IG handles
        conn = sqlite3.connect(DB_PATH)
        tt_usernames = [r[0] for r in conn.execute("SELECT username FROM platform_presences WHERE platform = 'tiktok'").fetchall()]
        conn.close()
        for h in tt_usernames:
            if h not in existing_ig and h not in attempted_set:
                handle_queue.add(h)
        
        total_queue = len(handle_queue)
        print(f'\n  Total queue (after filtering attempted): {total_queue}')
        sys.stdout.flush()
        
        # Phase 4: Scrape each handle
        print('\n--- Phase 4: Scraping IG profiles ---')
        sys.stdout.flush()
        
        queue_list = list(handle_queue)
        random.shuffle(queue_list)
        failed = 0
        consecutive_failures = 0
        backoff_multiplier = 1
        ctx_count = 0
        not_found_count = 0
        
        for i, username in enumerate(queue_list):
            if username in existing_ig:
                continue
            
            # Rotate context every 15-25 requests (randomized)
            ctx_count += 1
            if ctx_count >= random.randint(15, 25):
                try:
                    await ctx.close()
                except:
                    pass
                ctx = await make_fresh_context(browser)
                ctx_count = 0
            
            result = await scrape_ig_profile(ctx, username)
            
            # Track attempt
            progress['attempted'].append(username)
            
            if result == 'not_found':
                not_found_count += 1
                consecutive_failures = 0
                backoff_multiplier = max(1, backoff_multiplier - 0.5)
                print(f'  [{i+1}/{total_queue}] @{username} — not found (404)')
                sys.stdout.flush()
            elif result is None:
                failed += 1
                consecutive_failures += 1
                progress['failed'].append(username)
                
                # Exponential backoff
                if consecutive_failures >= 3:
                    backoff_multiplier = min(backoff_multiplier * 1.5, 8)
                    wait_time = 30 * backoff_multiplier
                    print(f'  ⚠️ {consecutive_failures} consecutive failures, backing off {wait_time:.0f}s (multiplier: {backoff_multiplier:.1f}x)')
                    sys.stdout.flush()
                    await asyncio.sleep(wait_time)
                    
                    # Fresh context after backoff
                    try:
                        await ctx.close()
                    except:
                        pass
                    ctx = await make_fresh_context(browser)
                    ctx_count = 0
                
                if consecutive_failures >= 10:
                    print('  🛑 10 consecutive failures — taking a long break (5 min)')
                    sys.stdout.flush()
                    await asyncio.sleep(300)
                    consecutive_failures = 0
                    backoff_multiplier = 2
                    try:
                        await ctx.close()
                    except:
                        pass
                    ctx = await make_fresh_context(browser)
                    ctx_count = 0
                    
            elif result['followers'] < MIN_FOLLOWERS:
                consecutive_failures = 0
                backoff_multiplier = max(1, backoff_multiplier - 0.5)
                print(f'  [{i+1}/{total_queue}] @{username} — {result["followers"]:,} followers (below {MIN_FOLLOWERS:,} threshold)')
                sys.stdout.flush()
            else:
                consecutive_failures = 0
                backoff_multiplier = max(1, backoff_multiplier - 0.5)
                
                with open(BACKUP_PATH, 'a') as f:
                    f.write(json.dumps(result, ensure_ascii=False) + '\n')
                
                inserted = insert_ig_creator(result)
                if inserted:
                    new_inserted += 1
                    existing_ig.add(result['username'])
                    progress['succeeded'].append(username)
                    country = detect_country(result.get('bio',''), result.get('name',''), result['username'])
                    print(f'  ✅ [{new_inserted}] @{result["username"]} ({country}): {result["name"]} — {result["followers"]:,} followers, {result.get("posts",0):,} posts')
                    sys.stdout.flush()
            
            # Save progress periodically
            if (i + 1) % 10 == 0:
                save_progress(progress)
            
            # Variable delay with backoff
            delay = random.uniform(DELAY_MIN, DELAY_MAX) * backoff_multiplier
            await asyncio.sleep(delay)
        
        save_progress(progress)
        
        try:
            await ctx.close()
        except:
            pass
        await browser.close()
    
    elapsed = round((time.time() - start) / 60, 1)
    conn = sqlite3.connect(DB_PATH)
    ig_total = conn.execute("SELECT COUNT(*) FROM platform_presences WHERE platform = 'instagram'").fetchone()[0]
    conn.close()
    
    print(f'\n{"="*60}')
    print(f'IG SCRAPE COMPLETE — {elapsed} min')
    print(f'{"="*60}')
    print(f'New IG profiles inserted: {new_inserted}')
    print(f'Failed (blocked/error): {failed}')
    print(f'Not found (404): {not_found_count}')
    print(f'Total IG in DB: {ig_total}')
    sys.stdout.flush()

if __name__ == '__main__':
    asyncio.run(main())
