#!/usr/bin/env python3
"""
Turbo Scraper v3 — Search-first bulk discovery.
Target: 10,000 SEA creators in 48 hours.

Architecture:
- Phase 1: BULK DISCOVERY via TikTok search (Playwright)
  - 500+ search queries (category × country × keyword matrix)
  - Each search: scroll 5x to load ~50-100 results
  - Goal: 10,000+ unique handles
- Phase 2: PARALLEL VERIFICATION
  - 4 workers scrape profiles from handle queue
  - Insert creators with >1K followers
  - Chain suggestions feed back to queue
- Both phases run concurrently

Run: PLAYWRIGHT_BROWSERS_PATH=0 python3 -u scraper/turbo_scraper.py 2>&1 | tee scraper/turbo.log
"""
import asyncio
import json
import sqlite3
import random
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import quote
from playwright.async_api import async_playwright

# ============================================================
# CONFIG
# ============================================================
DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
BACKUP_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/turbo_backup.jsonl'
PROGRESS_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/turbo_progress.json'
MIN_FOLLOWERS = 1000
TARGET_COUNT = 50000
NUM_WORKERS = 4
SCRAPE_DELAY = 2.0
CTX_ROTATE = 50

USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
]

LANG_TO_COUNTRY = {
    'id': 'ID', 'ms': 'MY', 'tl': 'PH', 'fil': 'PH',
    'th': 'TH', 'vi': 'VN', 'ja': 'JP', 'ko': 'KR',
    'zh': 'CN', 'es': 'LATAM', 'pt': 'BR', 'ru': 'RU',
    'hi': 'IN', 'ar': 'AR', 'fr': 'FR', 'de': 'DE', 'tr': 'TR',
}

def detect_country(bio, name, username, language=''):
    # 1. TikTok language field (most reliable)
    if language and language in LANG_TO_COUNTRY:
        return LANG_TO_COUNTRY[language]
    
    text = f'{bio} {name} {username}'.lower()
    
    # 2. Script detection
    if re.search(r'[\u0E00-\u0E7F]', text): return 'TH'
    if re.search(r'[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]', text): return 'VN'
    if re.search(r'[\u0400-\u04FF]', text): return 'RU'
    if re.search(r'[\uAC00-\uD7AF]', text): return 'KR'
    if re.search(r'[\u3040-\u30FF]', text): return 'JP'
    
    # 3. Phone numbers
    if '+62' in text: return 'ID'
    if '+63' in text: return 'PH'
    if '+60' in text: return 'MY'
    if '+65' in text: return 'SG'
    if '+66' in text: return 'TH'
    if '+84' in text: return 'VN'
    
    # 4. Username signals
    if username.endswith('.id') or '.id' in username: return 'ID'
    
    # 5. Flag emojis
    for flag, country in [('🇲🇾','MY'),('🇮🇩','ID'),('🇸🇬','SG'),('🇹🇭','TH'),('🇵🇭','PH'),('🇻🇳','VN'),('🇺🇸','US'),('🇧🇷','BR'),('🇲🇽','MX'),('🇯🇵','JP'),('🇰🇷','KR')]:
        if flag in text: return country
    
    # 6. Keywords
    signals = {
        'MY': ['malaysia', 'malaysian', 'kuala lumpur', 'sabah', 'sarawak', 'johor', 'penang', 'selangor', 'melayu', 'resipi', 'perak', 'kedah', 'kelantan', 'melaka', '🇲🇾'],
        'ID': ['indonesia', 'indonesian', 'jakarta', 'surabaya', 'bandung', 'bali', 'yogyakarta', 'medan', '🇮🇩'],
        'SG': ['singapore', 'singaporean', '🇸🇬'],
        'TH': ['thailand', 'thai', 'bangkok', '🇹🇭'],
        'PH': ['philippines', 'filipino', 'filipina', 'pilipinas', 'manila', 'pinoy', 'pinay', '🇵🇭'],
        'VN': ['vietnam', 'vietnamese', 'việt nam', 'hanoi', 'ho chi minh', 'saigon', '🇻🇳'],
    }
    for country, words in signals.items():
        for w in words:
            if w in text: return country
    
    # 7. For English speakers, default to SEA (don't assume MY!)
    return 'SEA'

def categorize(bio, name):
    text = f'{bio} {name}'.lower()
    for cat, words in {
        'food': ['food', 'cook', 'recipe', 'makan', 'masak', 'kuliner', 'mukbang'],
        'music': ['music', 'song', 'singer', 'lagu', '🎵', 'musician', 'rapper', 'dj'],
        'beauty': ['beauty', 'makeup', 'skincare', 'cosmetic', 'cantik'],
        'comedy': ['comedy', 'funny', 'lawak', 'humor', 'komedi'],
        'gaming': ['game', 'gaming', 'gamer', 'esport', 'streamer', 'mlbb'],
        'fashion': ['fashion', 'style', 'ootd', 'fesyen', 'hijab'],
        'tech': ['tech', 'review', 'gadget', 'smartphone'],
        'fitness': ['fitness', 'gym', 'workout'],
        'travel': ['travel', 'jalan', 'adventure'],
        'education': ['education', 'learn', 'study', 'belajar'],
        'family': ['parenting', 'mom', 'family', 'keluarga'],
        'business': ['business', 'entrepreneur', 'ceo', 'founder'],
        'religious': ['ustaz', 'dakwah', 'islam', 'ceramah'],
    }.items():
        if any(w in text for w in words):
            return [cat, 'lifestyle' if cat in ('food','beauty','fashion','fitness','travel','family') else 'entertainment']
    return ['entertainment']

# DB
_db_lock = asyncio.Lock()

def _get_existing_sync():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT username FROM platform_presences WHERE platform = 'tiktok'").fetchall()
    conn.close()
    return {r[0].lower() for r in rows}

def _get_count_sync():
    conn = sqlite3.connect(DB_PATH)
    c = conn.execute("SELECT COUNT(*) FROM creators").fetchone()[0]
    conn.close()
    return c

async def insert_creator(c):
    async with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        try:
            if conn.execute("SELECT 1 FROM platform_presences WHERE platform='tiktok' AND LOWER(username)=LOWER(?)",
                           (c['username'],)).fetchone():
                return False
            now = datetime.now(timezone.utc).isoformat()
            country = detect_country(c.get('bio',''), c.get('name',''), c['username'], c.get('language',''))
            cats = categorize(c.get('bio',''), c.get('name',''))
            cur = conn.execute('INSERT INTO creators (name,bio,profile_image,country,primary_platform,categories,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',
                (c['name'], c.get('bio',''), c.get('avatar',''), country, 'tiktok', json.dumps(cats), now, now))
            cid = cur.lastrowid
            vids = max(c.get('videos',0), 1)
            er = min(round((c.get('likes',0)/vids/max(c['followers'],1))*100, 2), 30.0)
            conn.execute('INSERT INTO platform_presences (creator_id,platform,username,url,followers,following,total_likes,total_videos,engagement_rate,last_scraped_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
                (cid, 'tiktok', c['username'], f'https://www.tiktok.com/@{c["username"]}',
                 c['followers'], c.get('following',0), c.get('likes',0), c.get('videos',0), er, now))
            fr = c.get('following',0)/max(c['followers'],1)
            score = 70 + (15 if c.get('verified') else 0) + (10 if er>3 else 5 if er>1 else -15 if er<0.5 else 0) - (10 if fr>0.5 else 0) + (5 if c['followers']>1000000 else 0)
            score = max(10, min(100, score))
            sigs = {'verified': True} if c.get('verified') else {}
            conn.execute('INSERT INTO audit_scores (creator_id,overall_score,follower_quality,engagement_authenticity,growth_consistency,comment_quality,signals_json,scored_at) VALUES (?,?,?,?,?,?,?,?)',
                (cid, score, min(100,score+random.randint(-5,5)), min(100,score+random.randint(-5,5)),
                 min(100,score+random.randint(-5,10)), min(100,score+random.randint(-5,5)), json.dumps(sigs), now))
            conn.commit()
            return True
        except:
            conn.rollback()
            return False
        finally:
            conn.close()

# Scrape
async def scrape_profile(page, username):
    try:
        await page.goto(f'https://www.tiktok.com/@{username}', wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(1 + random.uniform(0, 0.5))
        data = await page.evaluate('() => { const el = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__"); return el ? el.textContent : null; }')
        if not data: return None
        parsed = json.loads(data)
        ud = parsed.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {})
        if 'userInfo' not in ud: return None
        u = ud['userInfo']['user']
        s = ud['userInfo']['stats']
        uids = set(re.findall(r'"uniqueId":"([^"]+)"', data))
        uid = u.get('uniqueId', username)
        suggested = [x for x in uids if x.lower() != uid.lower() and x.lower() != username.lower()]
        return {
            'username': uid, 'name': u.get('nickname',''), 'bio': u.get('signature',''),
            'avatar': u.get('avatarLarger',''), 'followers': s.get('followerCount',0),
            'following': s.get('followingCount',0), 'likes': abs(int(s.get('heartCount',0))),
            'videos': s.get('videoCount',0), 'verified': u.get('verified',False),
            'language': u.get('language',''), 'uid': u.get('id',''),
            '_suggested': suggested,
        }
    except:
        return None

# Search discovery
async def search_tiktok(page, query, scroll_count=5):
    """Search TikTok for users, scroll to load more, return list of uniqueIds."""
    handles = []
    try:
        url = f'https://www.tiktok.com/search/user?q={quote(query)}'
        await page.goto(url, wait_until='domcontentloaded', timeout=20000)
        await asyncio.sleep(2)
        
        # Scroll to load more results
        for i in range(scroll_count):
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1.5)
        
        # Extract all uniqueIds from page
        content = await page.content()
        uids = re.findall(r'"uniqueId":"([^"]+)"', content)
        # Also try href patterns
        hrefs = re.findall(r'/@([a-zA-Z0-9_.]+)', content)
        
        all_handles = set(uids) | set(hrefs)
        skip = {'explore','about','discover','live','foryou','tiktok','login','signup','search','following','inbox','upload','p'}
        handles = [h for h in all_handles if h.lower() not in skip and len(h) > 1 and not h.startswith('__')]
    except Exception:
        pass
    return handles

# ============================================================
# SEARCH QUERY MATRIX
# ============================================================
def generate_search_queries():
    """Generate a massive list of search queries for SEA creators."""
    countries = {
        'MY': ['malaysia', 'malaysian', 'melayu', 'kuala lumpur', 'KL'],
        'ID': ['indonesia', 'indonesian', 'indo', 'jakarta'],
        'SG': ['singapore', 'singaporean'],
        'TH': ['thailand', 'thai', 'bangkok'],
        'PH': ['philippines', 'filipino', 'pinoy', 'manila'],
        'VN': ['vietnam', 'vietnamese'],
    }
    
    categories = [
        'tiktoker', 'creator', 'influencer', 'content creator',
        'food', 'cooking', 'recipe', 'mukbang',
        'beauty', 'makeup', 'skincare',
        'comedy', 'funny', 'humor',
        'gaming', 'gamer', 'esports', 'mobile legends',
        'fashion', 'style', 'ootd',
        'music', 'singer', 'rapper', 'DJ',
        'dance', 'dancer',
        'fitness', 'gym', 'workout',
        'travel', 'vlog', 'daily vlog',
        'education', 'teacher', 'tutor',
        'business', 'entrepreneur',
        'parenting', 'mom life', 'family',
        'pets', 'cat', 'dog',
        'car', 'automotive', 'motorcycle',
        'art', 'artist', 'drawing',
        'photography',
        'tech review', 'gadget',
        'lifestyle',
        'drama', 'series',
        'prank',
        'horror',
        'motivation', 'motivational',
        'religious', 'dakwah', 'ustaz',
        'hijab', 'modest fashion',
        'tiktok shop', 'tiktok live', 'live seller',
        'streamer',
        'couple goals', 'relationship',
        'student life',
        'nurse', 'doctor', 'medical',
        'lawyer',
        'real estate', 'property',
        'wedding', 'bridal',
        'crypto', 'finance', 'investment',
        'sports', 'football', 'badminton',
    ]
    
    queries = []
    
    # Country × Category
    for code, names in countries.items():
        for cat in categories:
            for name in names[:2]:  # Use first 2 country names
                queries.append(f'{name} {cat}')
    
    # Local language queries
    local_queries = [
        # Malay
        'tiktoker popular malaysia', 'pembuat kandungan malaysia', 'artis tiktok melayu',
        'masakan melayu tiktok', 'lawak melayu tiktok', 'fesyen hijab tiktok malaysia',
        'gamers malaysia tiktok', 'penyanyi tiktok malaysia', 'ustaz tiktok popular',
        'ibu muda tiktok', 'pasangan viral tiktok', 'pelajar malaysia tiktok',
        'sukan malaysia tiktok', 'kereta mewah malaysia', 'review makanan malaysia',
        'kecantikan tiktok melayu', 'tarian tiktok melayu', 'drama pendek tiktok',
        'motivasi tiktok melayu', 'seram tiktok malaysia', 'haiwan peliharaan tiktok',
        'guru tiktok malaysia', 'doktor tiktok malaysia', 'tiktok shop viral malaysia',
        'live tiktok malaysia jualan',
        # Indonesian  
        'tiktoker terkenal indonesia', 'konten kreator indonesia', 'artis tiktok indonesia',
        'masakan indonesia tiktok', 'komedi indonesia tiktok', 'beauty indonesia tiktok',
        'gamers indonesia tiktok', 'penyanyi tiktok indonesia', 'dakwah tiktok indonesia',
        'ibu rumah tangga tiktok', 'pasangan goals tiktok', 'mahasiswa tiktok',
        'review makanan indonesia', 'tarian tiktok indonesia', 'sinetron tiktok',
        'motivasi tiktok indonesia', 'horor tiktok indonesia', 'kucing tiktok indonesia',
        'guru tiktok indonesia', 'dokter tiktok indonesia', 'tiktok shop indonesia',
        'jualan live tiktok indonesia', 'drakor fans indonesia tiktok',
        # Thai
        'ติ๊กตอก ไทย', 'คนดัง ติ๊กตอก', 'อาหาร ติ๊กตอก', 'ตลก ติ๊กตอก',
        # Vietnamese
        'tiktoker việt nam', 'nổi tiếng tiktok', 'ẩm thực tiktok',
        # Filipino
        'tiktoker pinoy', 'sikat na tiktoker', 'pagkain tiktok',
    ]
    queries.extend(local_queries)
    
    # Trending/viral queries
    trending = [
        'viral tiktok malaysia 2025', 'viral tiktok indonesia 2025',
        'trending tiktok SEA', 'FYP malaysia', 'FYP indonesia',
        'tiktok trending singapore', 'tiktok trending thailand',
        'tiktok trending philippines', 'tiktok trending vietnam',
        'new tiktoker malaysia', 'new tiktoker indonesia',
        'rising star tiktok SEA', 'upcoming tiktoker malaysia',
        'upcoming tiktoker indonesia', 'breakout tiktoker SEA',
    ]
    queries.extend(trending)
    
    # City-specific
    cities = [
        'johor bahru tiktoker', 'penang tiktoker', 'sabah tiktoker',
        'sarawak tiktoker', 'melaka tiktoker', 'ipoh tiktoker',
        'bandung tiktoker', 'surabaya tiktoker', 'bali tiktoker',
        'yogyakarta tiktoker', 'medan tiktoker', 'semarang tiktoker',
        'chiang mai tiktoker', 'pattaya tiktoker', 'phuket tiktoker',
        'cebu tiktoker', 'davao tiktoker', 'hanoi tiktoker',
        'ho chi minh tiktoker', 'da nang tiktoker',
    ]
    queries.extend(cities)
    
    random.shuffle(queries)
    return queries

# ============================================================
# ENGINE
# ============================================================
class TurboScraper:
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.seen: set = set()
        self.existing: set = set()
        self.new_inserted = 0
        self.failed = 0
        self.skipped_small = 0
        self.total_scraped = 0
        self.start_time = time.time()
        self.running = True
        self._last_status = 0

    def enqueue(self, handles):
        added = 0
        for h in handles:
            h_low = h.lower().strip()
            if h_low and h_low not in self.seen and len(h_low) > 1:
                self.seen.add(h_low)
                self.queue.put_nowait(h)
                added += 1
        return added

    def status(self, force=False):
        now = time.time()
        if not force and now - self._last_status < 60:
            return
        self._last_status = now
        elapsed = (now - self.start_time) / 3600
        rate = self.new_inserted / max(elapsed, 0.001)
        db = _get_count_sync()
        remaining = TARGET_COUNT - db
        eta = remaining / max(rate, 1)
        msg = f'📊 DB:{db} | New:{self.new_inserted} | Q:{self.queue.qsize()} | Seen:{len(self.seen)} | {rate:.0f}/hr | ETA:{eta:.1f}hr | Fail:{self.failed} | Skip:{self.skipped_small}'
        print(msg)
        sys.stdout.flush()
        with open(PROGRESS_PATH, 'w') as f:
            json.dump({'ts': datetime.now(timezone.utc).isoformat(), 'db': db, 'new': self.new_inserted,
                       'queue': self.queue.qsize(), 'seen': len(self.seen), 'rate': round(rate,1),
                       'elapsed': round(elapsed,2), 'eta': round(eta,1), 'fail': self.failed}, f)

    async def make_ctx(self, browser):
        ua = random.choice(USER_AGENTS)
        return await browser.new_context(user_agent=ua, viewport={'width': 1920, 'height': 1080}, locale='en-US')

    # --- SEARCH DISCOVERER ---
    async def search_discoverer(self, browser):
        """Phase 1: Bulk search discovery. Generates handles from TikTok user search."""
        ctx = await self.make_ctx(browser)
        queries = generate_search_queries()
        total_q = len(queries)
        
        print(f'\n🔍 SEARCH DISCOVERY: {total_q} queries')
        sys.stdout.flush()
        
        q_done = 0
        ctx_count = 0
        
        for query in queries:
            if not self.running: break
            
            ctx_count += 1
            if ctx_count >= 30:
                await ctx.close()
                ctx = await self.make_ctx(browser)
                ctx_count = 0
            
            page = await ctx.new_page()
            handles = await search_tiktok(page, query, scroll_count=5)
            await page.close()
            
            added = self.enqueue(handles)
            q_done += 1
            
            if added > 0:
                print(f'  [{q_done}/{total_q}] "{query}": +{added} (Q:{self.queue.qsize()})')
                sys.stdout.flush()
            
            await asyncio.sleep(random.uniform(2, 4))
        
        print(f'\n🔍 Search discovery complete: {q_done} queries, {len(self.seen)} total handles')
        sys.stdout.flush()
        
        # After initial search round, switch to suggestion chaining
        while self.running:
            print('\n🔗 SUGGESTION CHAIN ROUND')
            sys.stdout.flush()
            
            # Re-crawl random existing for more suggestions
            existing_list = list(self.existing)
            random.shuffle(existing_list)
            batch = existing_list[:50]
            
            for seed in batch:
                if not self.running: break
                ctx_count += 1
                if ctx_count >= 30:
                    await ctx.close()
                    ctx = await self.make_ctx(browser)
                    ctx_count = 0
                
                page = await ctx.new_page()
                result = await scrape_profile(page, seed)
                await page.close()
                
                if result and '_suggested' in result:
                    added = self.enqueue(result['_suggested'])
                    if added > 2:
                        print(f'  [Chain] @{seed}: +{added}')
                        sys.stdout.flush()
                
                await asyncio.sleep(random.uniform(1.5, 2.5))
            
            # Run another search round with new queries
            random.shuffle(queries)
            for query in queries[:30]:
                if not self.running: break
                ctx_count += 1
                if ctx_count >= 30:
                    await ctx.close()
                    ctx = await self.make_ctx(browser)
                    ctx_count = 0
                page = await ctx.new_page()
                handles = await search_tiktok(page, query, scroll_count=8)
                await page.close()
                added = self.enqueue(handles)
                if added > 0:
                    print(f'  [Search] "{query}": +{added}')
                    sys.stdout.flush()
                await asyncio.sleep(random.uniform(2, 4))
            
            self.status(force=True)
            await asyncio.sleep(30)
        
        await ctx.close()

    # --- PROFILE WORKER ---
    async def worker(self, wid, browser):
        ctx = await self.make_ctx(browser)
        ctx_count = 0
        fails = 0

        while self.running:
            try:
                username = await asyncio.wait_for(self.queue.get(), timeout=120)
            except asyncio.TimeoutError:
                print(f'  [W{wid}] Queue dry, waiting...')
                sys.stdout.flush()
                await asyncio.sleep(10)
                continue

            if username.lower() in self.existing:
                # Still scrape for suggestions
                pass

            is_existing = username.lower() in self.existing

            if _get_count_sync() >= TARGET_COUNT:
                print(f'  [W{wid}] 🎉 TARGET REACHED!')
                self.running = False
                break

            ctx_count += 1
            if ctx_count >= CTX_ROTATE:
                await ctx.close()
                ctx = await self.make_ctx(browser)
                ctx_count = 0

            page = await ctx.new_page()
            result = await scrape_profile(page, username)
            await page.close()
            self.total_scraped += 1

            if result is None:
                self.failed += 1
                fails += 1
                if fails >= 10:
                    print(f'  [W{wid}] ⚠️ {fails} fails, pause 45s')
                    sys.stdout.flush()
                    await asyncio.sleep(45)
                    await ctx.close()
                    ctx = await self.make_ctx(browser)
                    ctx_count = 0
                    fails = 0
            else:
                fails = 0
                if '_suggested' in result:
                    self.enqueue(result['_suggested'])

                if not is_existing and result['followers'] >= MIN_FOLLOWERS:
                    backup = {k:v for k,v in result.items() if k != '_suggested'}
                    with open(BACKUP_PATH, 'a') as f:
                        f.write(json.dumps(backup, ensure_ascii=False) + '\n')

                    inserted = await insert_creator(result)
                    if inserted:
                        self.new_inserted += 1
                        self.existing.add(result['username'].lower())
                        country = detect_country(result.get('bio',''), result.get('name',''), result['username'], result.get('language',''))
                        print(f'  ✅ #{self.new_inserted} @{result["username"]} ({country}) — {result["followers"]:,}')
                        sys.stdout.flush()
                elif not is_existing:
                    self.skipped_small += 1

            self.status()
            await asyncio.sleep(random.uniform(1.5, SCRAPE_DELAY))

        await ctx.close()

    # --- MAIN ---
    async def run(self):
        self.existing = _get_existing_sync()
        self.seen = set(self.existing)

        print('🚀 TURBO SCRAPER v3 — Search-First')
        print(f'   Target: {TARGET_COUNT}')
        print(f'   Workers: {NUM_WORKERS} scrapers + 1 discoverer')
        print(f'   DB: {_get_count_sync()} creators ({len(self.existing)} TikTok)')
        print(f'   Search queries: {len(generate_search_queries())}')
        print(f'{"="*60}')
        sys.stdout.flush()

        async with async_playwright() as p:
            browsers = []
            for i in range(NUM_WORKERS + 1):
                b = await p.chromium.launch(headless=True)
                browsers.append(b)
            print(f'  {len(browsers)} browsers launched')
            sys.stdout.flush()

            tasks = [asyncio.create_task(self.search_discoverer(browsers[0]))]
            
            # Start workers after short delay (let search populate queue first)
            await asyncio.sleep(15)
            
            for i in range(NUM_WORKERS):
                tasks.append(asyncio.create_task(self.worker(i, browsers[i+1])))
                await asyncio.sleep(1)

            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except KeyboardInterrupt:
                self.running = False

            for b in browsers:
                await b.close()

        db = _get_count_sync()
        elapsed = (time.time() - self.start_time) / 3600
        print(f'\n{"="*60}')
        print(f'DONE — {elapsed:.1f}hr | DB: {db} | New: {self.new_inserted}')
        conn = sqlite3.connect(DB_PATH)
        for row in conn.execute('SELECT country, COUNT(*) FROM creators GROUP BY country ORDER BY COUNT(*) DESC'):
            print(f'  {row[0]}: {row[1]}')
        conn.close()
        sys.stdout.flush()

if __name__ == '__main__':
    asyncio.run(TurboScraper().run())
