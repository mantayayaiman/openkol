#!/usr/bin/env python3
"""
YouTube scraper v2: Discovers and scrapes SEA creator channels.
Uses Playwright with consent handling, mobile UAs, and Google search discovery.

Run: PLAYWRIGHT_BROWSERS_PATH=0 python3 -u scraper/youtube_scraper.py >> scraper/yt_overnight.log 2>&1
"""
import asyncio, json, sqlite3, random, re, sys, time, os
from datetime import datetime, timezone
from playwright.async_api import async_playwright

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
BACKUP_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/yt_backup.jsonl'
PROGRESS_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/yt_progress.json'
MIN_SUBSCRIBERS = 10000
DELAY_MIN = 4
DELAY_MAX = 8

MOBILE_UAS = [
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.64 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.64 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/121.0.6167.171 Mobile/15E148 Safari/604.1',
]

# Desktop UAs (YouTube works better with desktop)
DESKTOP_UAS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
]

def detect_country(bio, name, username):
    text = f'{bio} {name} {username}'.lower()
    if re.search(r'[\u0E00-\u0E7F]', text): return 'TH'
    if re.search(r'[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]', text): return 'VN'
    signals = {
        'MY': ['malaysia', 'kuala lumpur', 'melayu', '🇲🇾'],
        'ID': ['indonesia', 'jakarta', 'bandung', 'bali', '🇮🇩'],
        'SG': ['singapore', '🇸🇬'],
        'TH': ['thailand', 'thai', 'bangkok', '🇹🇭'],
        'PH': ['philippines', 'filipino', 'manila', 'pinoy', '🇵🇭'],
        'VN': ['vietnam', 'việt nam', 'hanoi', '🇻🇳'],
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

def get_existing_yt_usernames():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT username FROM platform_presences WHERE platform = 'youtube'").fetchall()
    conn.close()
    return {r[0] for r in rows}

def load_progress():
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

def insert_yt_creator(c):
    conn = sqlite3.connect(DB_PATH)
    existing = conn.execute("SELECT id FROM platform_presences WHERE platform = 'youtube' AND username = ?", (c['username'],)).fetchone()
    if existing:
        conn.close()
        return False
    
    now = datetime.now(timezone.utc).isoformat()
    country = detect_country(c.get('bio', ''), c.get('name', ''), c['username'])
    
    existing_creator = conn.execute('SELECT id FROM creators WHERE LOWER(name) = LOWER(?)', (c.get('name', ''),)).fetchone()
    
    if existing_creator:
        creator_id = existing_creator[0]
    else:
        categories = ['entertainment']
        bio = (c.get('bio', '') + ' ' + c.get('name', '')).lower()
        if any(w in bio for w in ['food', 'cook', 'recipe', 'makan']): categories = ['food', 'lifestyle']
        elif any(w in bio for w in ['music', 'song', 'singer']): categories = ['music', 'entertainment']
        elif any(w in bio for w in ['beauty', 'makeup']): categories = ['beauty', 'lifestyle']
        elif any(w in bio for w in ['comedy', 'funny']): categories = ['comedy', 'entertainment']
        elif any(w in bio for w in ['gaming', 'game', 'esport']): categories = ['gaming', 'entertainment']
        elif any(w in bio for w in ['tech', 'review']): categories = ['tech', 'entertainment']
        
        cur = conn.execute('INSERT INTO creators (name, bio, profile_image, country, primary_platform, categories, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)',
            (c['name'], c.get('bio',''), c.get('avatar',''), country, 'youtube', json.dumps(categories), now, now))
        creator_id = cur.lastrowid
    
    conn.execute('INSERT INTO platform_presences (creator_id, platform, username, url, followers, following, total_likes, total_videos, engagement_rate, last_scraped_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
        (creator_id, 'youtube', c['username'], f'https://www.youtube.com/@{c["username"]}',
         c['subscribers'], 0, 0, c.get('videos', 0), 0, now))
    
    conn.commit()
    conn.close()
    return True

async def make_yt_context(browser):
    """Create browser context with consent cookies pre-set to bypass YouTube consent page."""
    ua = random.choice(DESKTOP_UAS)
    ctx = await browser.new_context(
        user_agent=ua,
        viewport={'width': 1920, 'height': 1080},
        locale='en-US',
    )
    # Set consent cookie to bypass GDPR/consent page
    await ctx.add_cookies([
        {
            'name': 'CONSENT',
            'value': 'PENDING+987',
            'domain': '.youtube.com',
            'path': '/',
        },
        {
            'name': 'CONSENT',
            'value': 'YES+cb.20210720-07-p0.en+FX+{}'.format(random.randint(100, 999)),
            'domain': '.youtube.com',
            'path': '/',
        },
        {
            'name': 'SOCS',
            'value': 'CAISHAgBEhJnd3NfMjAyMzA4MTUtMF9SQzIaAmVuIAEaBgiAo9CmBg',
            'domain': '.youtube.com',
            'path': '/',
        },
    ])
    return ctx

async def handle_consent_page(page):
    """Click through YouTube consent dialog if it appears."""
    try:
        # Look for consent buttons
        for selector in [
            'button[aria-label*="Accept"]',
            'button[aria-label*="Reject"]',
            'button:has-text("Accept all")',
            'button:has-text("Reject all")',
            'button:has-text("Accept")',
            'button:has-text("I agree")',
            'tp-yt-paper-button:has-text("Accept all")',
            'tp-yt-paper-button:has-text("Reject all")',
            '#content ytd-button-renderer:has-text("Accept")',
            'form[action*="consent"] button',
        ]:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    await btn.click()
                    await asyncio.sleep(2)
                    return True
            except:
                continue
    except:
        pass
    return False

async def scrape_yt_channel(ctx, handle):
    """Scrape a YouTube channel page with consent handling."""
    page = await ctx.new_page()
    try:
        url = f'https://www.youtube.com/@{handle}'
        resp = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        
        if resp and resp.status == 404:
            return 'not_found'
        
        # Wait for content
        await asyncio.sleep(random.uniform(2, 4))
        
        # Check for consent page and handle it
        page_url = page.url
        if 'consent' in page_url.lower():
            handled = await handle_consent_page(page)
            if handled:
                await asyncio.sleep(2)
                # Navigate again after consent
                resp = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(3)
        
        # Also try clicking consent on the page itself
        await handle_consent_page(page)
        await asyncio.sleep(1)
        
        content = await page.content()
        
        # Check if we actually got channel content
        if 'consent.youtube.com' in content or '"consentBumpRenderer"' in content:
            # Still on consent - try harder
            await handle_consent_page(page)
            await asyncio.sleep(2)
            content = await page.content()
        
        name = ''
        subs = 0
        desc = ''
        videos = 0
        avatar = ''
        
        # Strategy 1: channelMetadataRenderer (most reliable)
        meta_match = re.search(r'"channelMetadataRenderer":\{(.*?)\}', content)
        if meta_match:
            meta_block = meta_match.group(1)
            t = re.search(r'"title":"([^"]+)"', meta_block)
            d = re.search(r'"description":"([^"]*)"', meta_block)
            if t: name = t.group(1)
            if d: desc = d.group(1)[:200]
        
        # Strategy 2: subscriberCountText
        subs_patterns = [
            r'"subscriberCountText":\{"simpleText":"([^"]+)"\}',
            r'"subscriberCountText":\{"accessibility":\{"accessibilityData":\{"label":"([^"]+)"\}',
            r'"subscriberCountText":"([^"]+)"',
        ]
        for pat in subs_patterns:
            m = re.search(pat, content)
            if m:
                subs_text = m.group(1).strip()
                # Clean: "1.23M subscribers" or "456K subscribers" or "1,234,567 subscribers"
                subs_text = re.sub(r'\s*subscribers?', '', subs_text, flags=re.IGNORECASE).strip()
                subs = parse_count(subs_text)
                if subs > 0:
                    break
        
        # Strategy 3: from og:title or page title
        if not name:
            title = await page.title()
            # "Channel Name - YouTube"
            title_match = re.match(r'(.+?)\s*[-–—]\s*YouTube', title)
            if title_match:
                name = title_match.group(1).strip()
        
        # Strategy 4: extract from microformat
        if subs == 0:
            # Try "X subscribers" pattern anywhere
            sub_anywhere = re.findall(r'"([\d,.]+[KMB]?)\s*subscribers?"', content, re.IGNORECASE)
            for s in sub_anywhere:
                parsed = parse_count(s)
                if parsed > subs:
                    subs = parsed
        
        # Get video count
        vids_patterns = [
            r'"videosCountText":\{"runs":\[\{"text":"([\d,]+)"',
            r'"videosCountText":\{"simpleText":"([^"]+)"',
        ]
        for pat in vids_patterns:
            m = re.search(pat, content)
            if m:
                vids_text = m.group(1).replace(',', '').strip()
                # Might be "1,234 videos"
                vids_text = re.sub(r'\s*videos?', '', vids_text, flags=re.IGNORECASE)
                try:
                    videos = int(vids_text.replace(',', ''))
                except:
                    pass
                break
        
        # Get avatar
        avatar_match = re.search(r'"avatar":\{"thumbnails":\[(?:\{"url":"[^"]+"\},)*\{"url":"([^"]+)"', content)
        if not avatar_match:
            avatar_match = re.search(r'"avatar":\{"thumbnails":\[\{"url":"([^"]+)"', content)
        if avatar_match:
            avatar = avatar_match.group(1)
        
        if name and subs > 0:
            return {
                'username': handle,
                'name': name,
                'bio': desc,
                'avatar': avatar,
                'subscribers': subs,
                'videos': videos,
            }
        
        # If we got name but no subs, might be a real channel with hidden subs
        if name and not subs:
            print(f'    @{handle}: found name="{name}" but no sub count visible')
            sys.stdout.flush()
        
        return None
    except Exception as e:
        print(f'    Error scraping @{handle}: {type(e).__name__}: {e}', file=sys.stderr)
        sys.stderr.flush()
        return None
    finally:
        await page.close()

async def discover_yt_via_google(ctx):
    """Use Google to discover actual YouTube channel handles for our creators."""
    handles = set()
    
    # Search for our existing creators on YouTube
    conn = sqlite3.connect(DB_PATH)
    creator_names = [r[0] for r in conn.execute("SELECT DISTINCT name FROM creators LIMIT 100").fetchall()]
    conn.close()
    
    # Batch creator name searches (5 at a time in query)
    print(f'  Searching Google for YouTube channels of {len(creator_names)} creators...')
    sys.stdout.flush()
    
    # General SEA YouTuber discovery queries
    queries = [
        'top youtubers malaysia 2025 channel',
        'top youtubers indonesia 2025 channel',
        'popular youtubers singapore 2025',
        'popular youtubers thailand 2025',
        'popular youtubers philippines 2025',
        'popular youtubers vietnam 2025',
        'malaysia gaming youtubers',
        'indonesia beauty youtubers',
        'SEA content creators youtube channel',
        'malaysian tiktok creators youtube channel',
        'indonesian tiktok creators youtube channel',
    ]
    
    # Also search specific creator names
    batch_size = 3
    for i in range(0, min(len(creator_names), 30), batch_size):
        batch = creator_names[i:i+batch_size]
        names_str = ' OR '.join(f'"{n}"' for n in batch)
        queries.append(f'site:youtube.com/@* ({names_str})')
    
    for query in queries:
        page = await ctx.new_page()
        try:
            await page.goto(f'https://www.google.com/search?q={query}&num=30', wait_until='domcontentloaded', timeout=20000)
            await asyncio.sleep(random.uniform(2, 4))
            content = await page.content()
            yt_handles = re.findall(r'youtube\.com/@([a-zA-Z0-9_.-]+)', content)
            yt_handles = [h for h in set(yt_handles) if len(h) > 2 and h not in ('about', 'channel', 'feed', 'results')]
            new_h = [h for h in yt_handles if h not in handles]
            handles.update(new_h)
            if new_h:
                print(f'  Google [{query[:50]}]: +{len(new_h)} handles')
                sys.stdout.flush()
        except Exception as e:
            print(f'  Google [{query[:50]}]: error - {e}')
        finally:
            await page.close()
        await asyncio.sleep(random.uniform(5, 10))
    
    return handles

async def main():
    start = time.time()
    print(f'{"="*60}')
    print(f'YOUTUBE SCRAPER v2 — {datetime.now(timezone.utc).isoformat()}')
    print(f'{"="*60}')
    sys.stdout.flush()
    
    existing_yt = get_existing_yt_usernames()
    print(f'Existing YT in DB: {len(existing_yt)}')
    
    progress = load_progress()
    attempted_set = set(progress.get('attempted', []))
    print(f'Previously attempted: {len(attempted_set)}')
    sys.stdout.flush()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await make_yt_context(browser)
        
        # Phase 1: Discover handles
        print(f'\n--- Phase 1: Discovering YT handles ---')
        sys.stdout.flush()
        
        google_handles = await discover_yt_via_google(ctx)
        
        # Known clean SEA YouTube channels
        known_yt = [
            # MY
            'khairulaming', 'jinnyboy', 'namewee', 'danialhaqiem', 'msianfood',
            'lowyat', 'syedabdulkadir', 'luqmanpodolski', 'viralcham',
            'hairulazreen', 'shukshazwan', 'bellngasri',
            # ID
            'attahalilintar', 'jeromepolin', 'riaricis',
            'gadiiing', 'fadiljaidi', 'tanboykun', 'dedycorbuzier',
            'radityadika', 'araborrel', 'baimwong',
            # SG
            'jianhaotan', 'wahbanana', 'naomineo',
            'ryanaborrsylvia', 'thesmartlocal',
            # TH
            'pimrypie', 'iceababyoh',
            # PH
            'mimiyuuuh', 'cookinphill',
            # VN
            'sontungmtp',
        ]
        known_clean = [h for h in known_yt if 'aborr' not in h and len(h) > 2]
        
        # TikTok usernames as potential YT handles
        conn = sqlite3.connect(DB_PATH)
        tt_usernames = [r[0] for r in conn.execute("SELECT username FROM platform_presences WHERE platform = 'tiktok'").fetchall()]
        conn.close()
        
        all_handles = set()
        all_handles.update(google_handles)
        all_handles.update(known_clean)
        all_handles.update(tt_usernames)
        
        handle_queue = list(all_handles - existing_yt - attempted_set)
        random.shuffle(handle_queue)
        total_queue = len(handle_queue)
        print(f'\nTotal queue (after filtering attempted): {total_queue} handles')
        sys.stdout.flush()
        
        # Phase 2: Test consent handling first
        print(f'\n--- Phase 2: Testing YouTube access ---')
        sys.stdout.flush()
        test_page = await ctx.new_page()
        try:
            await test_page.goto('https://www.youtube.com/@YouTube', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            test_url = test_page.url
            if 'consent' in test_url.lower():
                print('  Consent page detected, handling...')
                await handle_consent_page(test_page)
                await asyncio.sleep(2)
            test_content = await test_page.content()
            if 'subscriberCountText' in test_content or 'channelMetadataRenderer' in test_content:
                print('  ✅ YouTube access working!')
            else:
                print('  ⚠️ YouTube access may be limited, but proceeding...')
            sys.stdout.flush()
        except Exception as e:
            print(f'  ⚠️ Test failed: {e}')
        finally:
            await test_page.close()
        
        # Phase 3: Scrape channels
        print(f'\n--- Phase 3: Scraping YT channels ---')
        sys.stdout.flush()
        new_inserted = 0
        failed = 0
        not_found = 0
        consecutive_failures = 0
        ctx_count = 0
        
        for i, handle in enumerate(handle_queue):
            ctx_count += 1
            if ctx_count >= random.randint(30, 50):
                try:
                    await ctx.close()
                except:
                    pass
                ctx = await make_yt_context(browser)
                ctx_count = 0
            
            result = await scrape_yt_channel(ctx, handle)
            progress['attempted'].append(handle)
            
            if result == 'not_found':
                not_found += 1
                consecutive_failures = 0
            elif result is None:
                failed += 1
                consecutive_failures += 1
                
                if consecutive_failures >= 5:
                    wait = min(60 * (consecutive_failures // 5), 300)
                    print(f'  ⚠️ {consecutive_failures} consecutive failures, waiting {wait}s')
                    sys.stdout.flush()
                    await asyncio.sleep(wait)
                    try:
                        await ctx.close()
                    except:
                        pass
                    ctx = await make_yt_context(browser)
                    ctx_count = 0
                
                if consecutive_failures >= 15:
                    print(f'  🛑 15 consecutive failures — long break (5 min)')
                    sys.stdout.flush()
                    await asyncio.sleep(300)
                    consecutive_failures = 0
                    try:
                        await ctx.close()
                    except:
                        pass
                    ctx = await make_yt_context(browser)
                    ctx_count = 0
                    
            elif result['subscribers'] < MIN_SUBSCRIBERS:
                consecutive_failures = 0
                print(f'  [{i+1}/{total_queue}] @{handle} — {result["subscribers"]:,} subs (below {MIN_SUBSCRIBERS:,} threshold)')
                sys.stdout.flush()
            else:
                consecutive_failures = 0
                with open(BACKUP_PATH, 'a') as f:
                    f.write(json.dumps(result, ensure_ascii=False) + '\n')
                
                inserted = insert_yt_creator(result)
                if inserted:
                    new_inserted += 1
                    country = detect_country(result.get('bio',''), result.get('name',''), result['username'])
                    print(f'  ✅ [{new_inserted}] @{result["username"]} ({country}): {result["name"]} — {result["subscribers"]:,} subs, {result.get("videos",0)} videos')
                    sys.stdout.flush()
            
            if (i + 1) % 10 == 0:
                save_progress(progress)
                print(f'  --- Progress: {i+1}/{total_queue} | inserted={new_inserted} | failed={failed} | 404={not_found} ---')
                sys.stdout.flush()
            
            await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
        
        save_progress(progress)
        
        try:
            await ctx.close()
        except:
            pass
        await browser.close()
    
    elapsed = round((time.time() - start) / 60, 1)
    conn = sqlite3.connect(DB_PATH)
    yt_total = conn.execute("SELECT COUNT(*) FROM platform_presences WHERE platform = 'youtube'").fetchone()[0]
    conn.close()
    
    print(f'\n{"="*60}')
    print(f'YT SCRAPE COMPLETE — {elapsed} min')
    print(f'{"="*60}')
    print(f'New YT channels: {new_inserted}')
    print(f'Failed: {failed}')
    print(f'Not found (404): {not_found}')
    print(f'Total YT in DB: {yt_total}')
    sys.stdout.flush()

if __name__ == '__main__':
    asyncio.run(main())
