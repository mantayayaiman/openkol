#!/usr/bin/env python3
"""
Turbo YouTube Scraper v2 — Discovery-first with multiple sources.
Key insight: TikTok handles rarely match YT. Need YT-native discovery.

Sources:
1. SocialBlade top lists by country (Playwright — Cloudflare protected)
2. NoxInfluencer top lists by country
3. YouTube search (channel filter) via Playwright
4. Google "site:youtube.com/@*" queries
5. Cross-reference TikTok bios for YT links
6. YouTube's own "featured channels" from scraped profiles

Run: PLAYWRIGHT_BROWSERS_PATH=0 python3 -u scraper/turbo_yt.py 2>&1 | tee scraper/turbo_yt.log
"""
import asyncio, httpx, json, sqlite3, random, re, sys, time
from datetime import datetime, timezone
from urllib.parse import quote
from playwright.async_api import async_playwright

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
BACKUP_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/turbo_yt_backup.jsonl'
PROGRESS_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/turbo_yt_progress.json'
MIN_SUBS = 1000
NUM_WORKERS = 3
DELAY_MIN, DELAY_MAX = 2.0, 4.0
CTX_ROTATE = 40

UAS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
]

def detect_country(bio, name, username):
    text = f'{bio} {name} {username}'.lower()
    if re.search(r'[\u0E00-\u0E7F]', text): return 'TH'
    if re.search(r'[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]', text): return 'VN'
    for c, ws in {'MY':['malaysia','kuala lumpur','melayu'],'ID':['indonesia','jakarta','bandung','bali'],
                  'SG':['singapore'],'TH':['thailand','thai','bangkok'],'PH':['philippines','filipino','manila','pinoy'],
                  'VN':['vietnam','hanoi','ho chi minh']}.items():
        if any(w in text for w in ws): return c
    return 'SEA'

_db_lock = asyncio.Lock()
def _count(): 
    c = sqlite3.connect(DB_PATH); n = c.execute("SELECT COUNT(*) FROM platform_presences WHERE platform='youtube'").fetchone()[0]; c.close(); return n
def _existing():
    c = sqlite3.connect(DB_PATH); r = {x[0].lower() for x in c.execute("SELECT username FROM platform_presences WHERE platform='youtube'").fetchall()}; c.close(); return r

def parse_subs(text):
    text = re.sub(r'\s*(subscribers?|subs?).*', '', text, flags=re.IGNORECASE).strip().replace(',','')
    try:
        if 'B' in text: return int(float(text.replace('B','')) * 1e9)
        if 'M' in text: return int(float(text.replace('M','')) * 1e6)
        if 'K' in text: return int(float(text.replace('K','')) * 1e3)
        # Handle "1.48 million" format
        if 'million' in text.lower(): return int(float(re.sub(r'[^0-9.]','',text)) * 1e6)
        if 'billion' in text.lower(): return int(float(re.sub(r'[^0-9.]','',text)) * 1e9)
        return int(float(re.sub(r'[^0-9]','',text)))
    except: return 0

async def insert_yt(c):
    async with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        try:
            if conn.execute("SELECT 1 FROM platform_presences WHERE platform='youtube' AND LOWER(username)=LOWER(?)",(c['username'],)).fetchone(): return False
            now = datetime.now(timezone.utc).isoformat()
            country = detect_country(c.get('bio',''),c.get('name',''),c['username'])
            ex = conn.execute("SELECT c.id FROM creators c JOIN platform_presences pp ON pp.creator_id=c.id WHERE LOWER(c.name)=LOWER(?) OR LOWER(pp.username)=LOWER(?) LIMIT 1",
                             (c.get('name',''),c['username'])).fetchone()
            if ex: cid = ex[0]
            else:
                cats = ['entertainment']
                bio = (c.get('bio','')+' '+c.get('name','')).lower()
                for cat,ws in {'food':['food','cook','makan','mukbang'],'gaming':['game','gaming','gamer'],'beauty':['beauty','makeup'],
                               'comedy':['comedy','funny'],'music':['music','song','singer'],'tech':['tech','review','gadget'],
                               'education':['education','tutorial']}.items():
                    if any(w in bio for w in ws): cats=[cat,'entertainment']; break
                cur = conn.execute('INSERT INTO creators (name,bio,profile_image,country,primary_platform,categories,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',
                    (c['name'],c.get('bio',''),c.get('avatar',''),country,'youtube',json.dumps(cats),now,now))
                cid = cur.lastrowid
            conn.execute('INSERT INTO platform_presences (creator_id,platform,username,url,followers,following,total_likes,total_videos,engagement_rate,last_scraped_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
                (cid,'youtube',c['username'],f'https://www.youtube.com/@{c["username"]}',c['subscribers'],0,0,c.get('videos',0),0,now))
            conn.commit(); return True
        except: conn.rollback(); return False
        finally: conn.close()

def parse_localized_count(text):
    """Parse subscriber counts in any locale: '20.7J' (Malay), '1.5M', '456K', '100rb' (Indo), etc."""
    text = text.strip().replace(',', '.').replace(' ', '')
    try:
        # Malay/Indo: J/jt = juta (million), rb = ribu (thousand)
        if re.search(r'[Jj](?:uta)?$', text): return int(float(re.sub(r'[^0-9.]', '', text)) * 1e6)
        if re.search(r'rb|ribu', text, re.I): return int(float(re.sub(r'[^0-9.]', '', text)) * 1e3)
        # Standard: M/B/K
        if 'B' in text.upper(): return int(float(re.sub(r'[^0-9.]', '', text)) * 1e9)
        if 'M' in text.upper(): return int(float(re.sub(r'[^0-9.]', '', text)) * 1e6)
        if 'K' in text.upper(): return int(float(re.sub(r'[^0-9.]', '', text)) * 1e3)
        # Thai: ล (lan = million), พัน (phan = thousand)
        if 'ล' in text: return int(float(re.sub(r'[^0-9.]', '', text)) * 1e6)
        # Vietnamese: Tr (triệu = million), N (nghìn = thousand)
        if 'Tr' in text: return int(float(re.sub(r'[^0-9.]', '', text)) * 1e6)
        if 'N' in text and text[0].isdigit(): return int(float(re.sub(r'[^0-9.]', '', text)) * 1e3)
        return int(float(re.sub(r'[^0-9]', '', text)))
    except: return 0

async def scrape_yt(page, handle):
    try:
        await page.goto(f'https://www.youtube.com/@{handle}', wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(3)
        # Consent click
        try:
            btn = await page.query_selector('button[aria-label*="Accept"], button:has-text("Accept all"), button:has-text("Terima")')
            if btn: await btn.click(); await asyncio.sleep(2)
        except: pass
        
        content = await page.content()
        if 'This page isn' in content or '404' in content[:500] or 'not available' in content[:500]: return None
        
        subs = 0; videos = 0; name = handle; bio = ''; avatar = ''
        
        # Method 1: JSON in page (works for some locales)
        subs_m = re.search(r'"subscriberCountText":\{"simpleText":"([^"]+)"', content)
        if subs_m: subs = parse_subs(subs_m.group(1))
        
        # Method 2: Extract from visible text (works in ALL locales)
        if subs == 0:
            visible = await page.inner_text('body')
            # Pattern: "@handle • XY subscribers/pelanggan/etc • Z videos"
            # The subscriber line typically follows the @handle
            sub_patterns = [
                r'([\d,.]+[JKMB]?)\s*(?:pelanggan|subscribers?|subs?|người đăng ký|ผู้ติดตาม|subscriber)',
                r'([\d,.]+\s*(?:juta|ribu|Jt|rb))\s*(?:pelanggan|subscriber)',
                r'@\w+\s*•?\s*([\d,.]+[JKMB]?)\s*(?:pelanggan|subscriber)',
            ]
            for pat in sub_patterns:
                m = re.search(pat, visible, re.IGNORECASE)
                if m:
                    subs = parse_localized_count(m.group(1))
                    if subs > 0: break
            
            # Video count
            vid_patterns = [
                r'([\d,.]+[KM]?)\s*(?:video|วิดีโอ)',
            ]
            for pat in vid_patterns:
                m = re.search(pat, visible, re.IGNORECASE)
                if m:
                    videos = parse_localized_count(m.group(1))
                    break
        
        # Method 3: channelMetadataRenderer (for name/bio)
        name_m = re.search(r'"channelMetadataRenderer":\{"title":"([^"]+)"', content)
        if name_m: name = name_m.group(1)
        desc_m = re.search(r'"description":"([^"]{0,300})"', content)
        if desc_m: bio = desc_m.group(1)[:200]
        avatar_m = re.search(r'"avatar":\{"thumbnails":\[\{"url":"([^"]+)"', content)
        if avatar_m: avatar = avatar_m.group(1)
        vids_m = re.search(r'"videosCountText":\{"runs":\[\{"text":"([\d,]+)"', content)
        if vids_m and videos == 0: videos = int(vids_m.group(1).replace(',',''))
        
        if subs == 0: return None
        
        # Extract featured/related channels
        featured = list(set(re.findall(r'"canonicalBaseUrl":"/@([^"]+)"', content)))
        
        return {
            'username': handle, 'name': name, 'bio': bio, 'avatar': avatar,
            'subscribers': subs, 'videos': videos,
            '_featured': [f for f in featured if f.lower() != handle.lower()],
        }
    except: return None

class TurboYT:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.seen = set()
        self.existing = set()
        self.new_inserted = 0
        self.failed = 0
        self.skipped = 0
        self.total_scraped = 0
        self.start_time = time.time()
        self.running = True

    def enqueue(self, handles):
        added = 0
        for h in handles:
            h = h.lower().strip().lstrip('@').rstrip('/')
            if h and h not in self.seen and len(h) > 1:
                self.seen.add(h); self.queue.put_nowait(h); added += 1
        return added

    async def make_ctx(self, browser):
        ctx = await browser.new_context(user_agent=random.choice(UAS), viewport={'width':1920,'height':1080}, locale='en-US')
        await ctx.add_cookies([
            {'name':'CONSENT','value':'YES+cb.20210720-07-p0.en+FX+410','domain':'.youtube.com','path':'/'},
            {'name':'SOCS','value':'CAISHAgBEhJnd3NfMjAyMTA3MjAtMF9SQzIaAmVuIAEaBgiA_LyGBg','domain':'.youtube.com','path':'/'},
        ])
        return ctx

    async def worker(self, wid, browser):
        ctx = await self.make_ctx(browser); cc = 0; fails = 0
        while self.running:
            try: handle = await asyncio.wait_for(self.queue.get(), timeout=300)
            except asyncio.TimeoutError: await asyncio.sleep(30); continue
            if handle in self.existing: continue
            cc += 1
            if cc >= CTX_ROTATE: await ctx.close(); ctx = await self.make_ctx(browser); cc = 0
            page = await ctx.new_page()
            result = await scrape_yt(page, handle)
            await page.close(); self.total_scraped += 1
            if result is None:
                self.failed += 1; fails += 1
                if fails >= 8: await asyncio.sleep(30); await ctx.close(); ctx = await self.make_ctx(browser); cc=0; fails=0
            elif result['subscribers'] < MIN_SUBS:
                self.skipped += 1; fails = 0
                if '_featured' in result: self.enqueue(result['_featured'])
            else:
                fails = 0
                with open(BACKUP_PATH,'a') as f: f.write(json.dumps({k:v for k,v in result.items() if k!='_featured'},ensure_ascii=False)+'\n')
                inserted = await insert_yt(result)
                if inserted:
                    self.new_inserted += 1; self.existing.add(result['username'].lower())
                    country = detect_country(result.get('bio',''),result.get('name',''),result['username'])
                    print(f'  ✅ YT #{self.new_inserted} @{result["username"]} ({country}) — {result["subscribers"]:,} subs')
                    sys.stdout.flush()
                # Chain featured channels
                if '_featured' in result: self.enqueue(result['_featured'])
            
            if self.total_scraped % 20 == 0:
                elapsed = (time.time()-self.start_time)/3600; rate = self.new_inserted/max(elapsed,0.001)
                print(f'  📊 YT: {_count()} | New: {self.new_inserted} | Q: {self.queue.qsize()} | {rate:.0f}/hr | Fail: {self.failed}')
                sys.stdout.flush()
                with open(PROGRESS_PATH,'w') as f: json.dump({'ts':datetime.now(timezone.utc).isoformat(),'yt':_count(),'new':self.new_inserted,'q':self.queue.qsize(),'rate':round(rate,1),'fail':self.failed},f)
            await asyncio.sleep(random.uniform(DELAY_MIN,DELAY_MAX))
        await ctx.close()

    async def discoverer(self, browser):
        round_num = 0
        while self.running:
            round_num += 1
            print(f'\n{"="*50}\nYT DISCOVERY R{round_num} | Total: {_count()} | Q: {self.queue.qsize()}\n{"="*50}'); sys.stdout.flush()

            # Source 0: Priority handles from YuBin's KOL data (first round only)
            if round_num == 1:
                import os
                pf = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/yt_priority_handles.json'
                if os.path.exists(pf):
                    with open(pf) as f:
                        priority = json.load(f)
                    added = self.enqueue(priority)
                    print(f'  [KOL Priority] +{added} YT handles from YuBin data')
                    sys.stdout.flush()

            # Source 1: SocialBlade top lists (Playwright needed — Cloudflare)
            if round_num <= 2:
                print('  [SocialBlade] Scraping top lists...')
                ctx = await self.make_ctx(browser)
                sb_countries = [('my','Malaysia'),('id','Indonesia'),('sg','Singapore'),('th','Thailand'),('ph','Philippines'),('vn','Vietnam')]
                for code, name in sb_countries:
                    for metric in ['mostsubscribed','mostviewed']:
                        page = await ctx.new_page()
                        try:
                            await page.goto(f'https://socialblade.com/youtube/top/country/{code}/{metric}', wait_until='domcontentloaded', timeout=20000)
                            await asyncio.sleep(3)
                            content = await page.content()
                            handles = re.findall(r'youtube\.com/@([a-zA-Z0-9_.]+)', content)
                            # Also look for channel links
                            handles2 = re.findall(r'/youtube/user/([a-zA-Z0-9_.]+)', content)
                            handles3 = re.findall(r'href="/youtube/c/([a-zA-Z0-9_.]+)"', content)
                            all_h = set(handles) | set(handles2) | set(handles3)
                            added = self.enqueue(list(all_h))
                            if added > 0: print(f'    {name} {metric}: +{added}')
                        except: pass
                        finally: await page.close()
                        await asyncio.sleep(random.uniform(2,4))
                await ctx.close()

            # Source 2: NoxInfluencer top lists
            if round_num <= 2:
                print('  [NoxInfluencer] Scraping...')
                ctx = await self.make_ctx(browser)
                nox_countries = ['my','id','sg','th','ph','vn']
                for code in nox_countries:
                    page = await ctx.new_page()
                    try:
                        await page.goto(f'https://www.noxinfluencer.com/youtube-channel-rank/top-100-{code}-all-youtuber-sorted-by-subs-weekly',
                                       wait_until='domcontentloaded', timeout=20000)
                        await asyncio.sleep(3)
                        content = await page.content()
                        handles = re.findall(r'youtube\.com/@([a-zA-Z0-9_.]+)', content)
                        handles2 = re.findall(r'youtube\.com/channel/([a-zA-Z0-9_-]+)', content)
                        added = self.enqueue(handles)
                        if added > 0: print(f'    Nox {code.upper()}: +{added}')
                    except: pass
                    finally: await page.close()
                    await asyncio.sleep(random.uniform(2,4))
                await ctx.close()

            # Source 3: YouTube search (channel filter) — most reliable
            print('  [YT Search] Searching...')
            ctx = await self.make_ctx(browser)
            yt_queries = [
                'malaysia vlogger','indonesia vlogger','singapore vlogger','thai vlogger','filipino vlogger','vietnam vlogger',
                'malaysian food','indonesian food','thai food','singapore food','filipino food','vietnamese food',
                'malaysia gaming','indonesia gaming','philippines gaming','thai gaming',
                'malaysia beauty','indonesia beauty','thai beauty',
                'malaysia comedy','indonesia comedy','pinoy comedy','thai comedy',
                'malaysia music','indonesia music','kpop indonesia','malaysia rap',
                'malaysia tech review','indonesia tech','singapore tech',
                'malaysia education','indonesia education',
                'malaysia mukbang','indonesia mukbang',
                'malaysia travel','indonesia travel','thailand travel',
                'malaysia fitness','indonesia fitness',
                'malaysia motivasi','indonesia motivasi',
                'melayu youtuber','youtuber indonesia terkenal','youtuber malaysia popular',
                'youtuber filipina famous','thai youtuber popular',
                'malaysia horror','indonesia horror',
                'malaysia daily vlog','indonesia daily vlog',
                'malaysia car review','indonesia otomotif',
                'malaysia hijab tutorial','indonesia hijab',
                'SEA youtuber','southeast asia youtube',
            ]
            random.shuffle(yt_queries)
            for q in yt_queries[:25]:
                page = await ctx.new_page()
                try:
                    # sp=EgIQAg%3D%3D = channel filter
                    await page.goto(f'https://www.youtube.com/results?search_query={quote(q)}&sp=EgIQAg%3D%3D',
                                   wait_until='domcontentloaded', timeout=15000)
                    await asyncio.sleep(3)
                    # Scroll for more results
                    for _ in range(3):
                        await page.evaluate('window.scrollBy(0,1000)')
                        await asyncio.sleep(1)
                    content = await page.content()
                    channels = re.findall(r'"canonicalBaseUrl":"/@([^"]+)"', content)
                    added = self.enqueue(channels)
                    if added > 0: print(f'    "{q}": +{added}')
                except: pass
                finally: await page.close()
                await asyncio.sleep(random.uniform(2,4))
                if not self.running: break
            await ctx.close()

            # Source 4: Extract YT links from TikTok bios
            if round_num == 1:
                conn = sqlite3.connect(DB_PATH)
                bios = conn.execute('SELECT bio FROM creators WHERE bio IS NOT NULL').fetchall()
                conn.close()
                yt_handles = set()
                for (bio,) in bios:
                    if not bio: continue
                    for m in re.finditer(r'(?:youtube\.com/@|youtu\.be/|yt[:\s]+@?)([a-zA-Z0-9_.]{3,30})', bio.lower()):
                        yt_handles.add(m.group(1))
                added = self.enqueue(list(yt_handles))
                if added > 0: print(f'  [Bios→YT] +{added}')

            # Source 5: Google discovery
            print('  [Google] Searching...')
            async with httpx.AsyncClient(http2=True, follow_redirects=True, timeout=15) as client:
                gqs = [
                    'site:youtube.com/@* malaysia youtuber',
                    'site:youtube.com/@* indonesia youtuber',
                    'site:youtube.com/@* singapore youtuber',
                    'site:youtube.com/@* thailand youtuber',
                    'site:youtube.com/@* philippines youtuber',
                    'site:youtube.com/@* vietnam youtuber',
                    'top youtubers malaysia 2025 list',
                    'top youtubers indonesia 2025 list',
                    'youtuber terkenal malaysia senarai',
                    'youtuber terkenal indonesia daftar',
                    'famous filipino youtubers list 2025',
                    'best youtube channels southeast asia',
                    'top 50 youtubers malaysia',
                    'top 50 youtubers indonesia',
                ]
                random.shuffle(gqs)
                for gq in gqs[:8]:
                    try:
                        resp = await client.get(f'https://www.google.com/search?q={quote(gq)}&num=50',
                            headers={'User-Agent':random.choice(UAS)}, timeout=15)
                        if resp.status_code == 200:
                            h = re.findall(r'youtube\.com/@([a-zA-Z0-9_.]+)', resp.text)
                            added = self.enqueue(h)
                            if added > 0: print(f'    "{gq[:40]}": +{added}')
                    except: pass
                    await asyncio.sleep(random.uniform(3,6))

            elapsed = (time.time()-self.start_time)/3600; rate = self.new_inserted/max(elapsed,0.001)
            print(f'\n📊 YT R{round_num}: Total={_count()} | Q={self.queue.qsize()} | Seen={len(self.seen)} | {rate:.0f}/hr')
            sys.stdout.flush()
            await asyncio.sleep(60 if self.queue.qsize() < 100 else 180)

    async def run(self):
        self.existing = _existing(); self.seen = set(self.existing)
        print(f'🚀 TURBO YOUTUBE v2\n   Workers: {NUM_WORKERS}+1 | Existing: {len(self.existing)}\n{"="*50}'); sys.stdout.flush()
        async with async_playwright() as p:
            browsers = [await p.chromium.launch(headless=True) for _ in range(NUM_WORKERS+1)]
            print(f'  {len(browsers)} browsers launched')
            tasks = [asyncio.create_task(self.discoverer(browsers[0]))]
            await asyncio.sleep(15)
            for i in range(NUM_WORKERS):
                tasks.append(asyncio.create_task(self.worker(i, browsers[i+1]))); await asyncio.sleep(1)
            try: await asyncio.gather(*tasks, return_exceptions=True)
            except KeyboardInterrupt: self.running = False
            for b in browsers: await b.close()
        print(f'\nYT DONE | {_count()} total | {self.new_inserted} new'); sys.stdout.flush()

if __name__ == '__main__':
    asyncio.run(TurboYT().run())
