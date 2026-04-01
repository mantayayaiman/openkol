#!/usr/bin/env python3
"""
Turbo Facebook Scraper — Discovery-first FB page scraping.
FB is the hardest platform to scrape. Strategy:
1. Google discovery: "site:facebook.com [creator name]" for existing creators
2. Google: "facebook page [country] [category] influencer"
3. Cross-reference TikTok bios for FB links
4. Scrape public FB pages (no login needed for public pages)
5. Extract followers from page meta/about section

Key insight: FB public pages show follower count in meta tags.
We don't need to be logged in — just load the public page.

Run: PLAYWRIGHT_BROWSERS_PATH=0 python3 -u scraper/turbo_fb.py 2>&1 | tee scraper/turbo_fb.log
"""
import asyncio
import httpx
import json
import sqlite3
import random
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import quote
from playwright.async_api import async_playwright

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
BACKUP_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/turbo_fb_backup.jsonl'
PROGRESS_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/turbo_fb_progress.json'
MIN_FOLLOWERS = 1000
NUM_WORKERS = 2  # FB is strictest
DELAY_MIN, DELAY_MAX = 5.0, 8.0
CTX_ROTATE = 15

UAS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
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
    c = sqlite3.connect(DB_PATH); n = c.execute("SELECT COUNT(*) FROM platform_presences WHERE platform='facebook'").fetchone()[0]; c.close(); return n
def _existing():
    c = sqlite3.connect(DB_PATH); r = {x[0].lower() for x in c.execute("SELECT username FROM platform_presences WHERE platform='facebook'").fetchall()}; c.close(); return r

def parse_followers(text):
    """Parse '1.9J', '1.2M followers', '456K likes', '100rb' etc."""
    text = re.sub(r'\s*(followers?|likes?|people|pengikut|suka|mengikuti|orang).*','',text,flags=re.IGNORECASE).strip()
    text = text.replace(',', '.')
    try:
        # Malay: J = Juta (million), rb = ribu (thousand), jt = juta
        if re.search(r'[Jj](?:uta|t)?$', text): return int(float(re.sub(r'[^0-9.]','',text))*1e6)
        if re.search(r'rb|ribu', text, re.I): return int(float(re.sub(r'[^0-9.]','',text))*1e3)
        # Standard
        if 'B' in text.upper(): return int(float(re.sub(r'[^0-9.]','',text))*1e9)
        if 'M' in text.upper(): return int(float(re.sub(r'[^0-9.]','',text))*1e6)
        if 'K' in text.upper(): return int(float(re.sub(r'[^0-9.]','',text))*1e3)
        return int(float(re.sub(r'[^0-9]','',text)))
    except: return 0

async def insert_fb(c):
    async with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        try:
            if conn.execute("SELECT 1 FROM platform_presences WHERE platform='facebook' AND LOWER(username)=LOWER(?)",(c['username'],)).fetchone(): return False
            now = datetime.now(timezone.utc).isoformat()
            country = detect_country(c.get('bio',''),c.get('name',''),c['username'])
            
            # Link to existing creator
            ex = conn.execute("SELECT c.id FROM creators c JOIN platform_presences pp ON pp.creator_id=c.id WHERE LOWER(c.name)=LOWER(?) OR LOWER(pp.username)=LOWER(?) LIMIT 1",
                             (c.get('name',''),c['username'])).fetchone()
            if ex: cid = ex[0]
            else:
                cats = ['entertainment']
                bio = (c.get('bio','')+' '+c.get('name','')).lower()
                for cat,ws in {'food':['food','cook','makan'],'beauty':['beauty','makeup'],'comedy':['comedy','funny'],
                               'music':['music','song'],'gaming':['game','gaming']}.items():
                    if any(w in bio for w in ws): cats=[cat,'entertainment']; break
                cur = conn.execute('INSERT INTO creators (name,bio,profile_image,country,primary_platform,categories,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',
                    (c['name'],c.get('bio',''),c.get('avatar',''),country,'facebook',json.dumps(cats),now,now))
                cid = cur.lastrowid
            
            # ER will be populated by fb_video_enricher later
            er = 0
            conn.execute('INSERT INTO platform_presences (creator_id,platform,username,url,followers,following,total_likes,total_videos,engagement_rate,last_scraped_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
                (cid,'facebook',c['username'],f'https://www.facebook.com/{c["username"]}',c['followers'],0,c.get('likes',0),0,er,now))
            conn.commit(); return True
        except: conn.rollback(); return False
        finally: conn.close()

async def scrape_fb_page(page, handle):
    """Scrape a public Facebook page/profile. Uses networkidle + visible text (Malay locale)."""
    try:
        await page.goto(f'https://www.facebook.com/{handle}', wait_until='networkidle', timeout=25000)
        await asyncio.sleep(4 + random.uniform(0,1))
        
        # Dismiss popups (login, cookies, etc)
        for sel in ['[aria-label="Close"]', 'button:has-text("Not Now")', 'button:has-text("Decline")', 
                    'button:has-text("Decline optional cookies")', '[aria-label="Tutup"]']:
            try:
                btn = await page.query_selector(sel)
                if btn: await btn.click(); await asyncio.sleep(0.5)
            except: pass
        
        content = await page.content()
        
        # Check for 404
        if 'page_not_found' in content.lower() or 'this content isn' in content.lower():
            return None
        
        followers = 0; likes = 0; name = handle; bio = ''; avatar = ''
        
        # Get name from og:title
        og_title = re.search(r'<meta\s+property="og:title"\s+content="([^"]*)"', content)
        if og_title: name = og_title.group(1)
        og_desc = re.search(r'<meta\s+property="og:description"\s+content="([^"]*)"', content)
        if og_desc: bio = og_desc.group(1)[:200]
        og_img = re.search(r'<meta\s+property="og:image"\s+content="([^"]*)"', content)
        if og_img: avatar = og_img.group(1)
        
        # Method 1: Visible text (works with Malay locale)
        text = await page.inner_text('body')
        
        # Multi-locale patterns: English, Malay, Indonesian, Thai, Vietnamese
        fol_patterns = [
            r'([\d,.]+[JKMBjt]*)\s*(?:pengikut|followers?|people follow)',  # Malay/English
            r'([\d,.]+[JKMBjt]*)\s*(?:orang mengikuti|mengikuti)',  # Indonesian
            r'([\d,.]+[JKMBjt]*)\s*(?:suka|likes?|people like)',  # Malay/English likes
            r'([\d,.]+[JKMBjt]*)\s*(?:ผู้ติดตาม)',  # Thai
            r'([\d,.]+[JKMBjt]*)\s*(?:người theo dõi)',  # Vietnamese
        ]
        for pat in fol_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                val = parse_followers(m.group(1))
                if val > followers: followers = val
        
        # Method 2: JSON in page source
        for pat in [r'"follower_count":(\d+)', r'"followers_count":(\d+)', r'"page_likers":\{"global_likers_count":(\d+)']:
            matches = re.findall(pat, content)
            for m in matches:
                val = int(m)
                if val > followers: followers = val
        
        if followers == 0: return None
        
        return {
            'username': handle, 'name': name, 'bio': bio,
            'avatar': avatar, 'followers': followers, 'likes': likes,
        }
    except:
        return None

class TurboFB:
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
            h = h.lower().strip().rstrip('/').split('?')[0]
            if h and h not in self.seen and len(h) > 1 and h not in ('facebook','pages','groups','watch','marketplace','gaming','events','profile.php'):
                self.seen.add(h); self.queue.put_nowait(h); added += 1
        return added

    async def make_ctx(self, browser):
        return await browser.new_context(user_agent=random.choice(UAS), viewport={'width':1920,'height':1080}, locale='en-US')

    async def worker(self, wid, browser):
        ctx = await self.make_ctx(browser); cc = 0; fails = 0
        while self.running:
            try: handle = await asyncio.wait_for(self.queue.get(), timeout=300)
            except asyncio.TimeoutError: await asyncio.sleep(30); continue
            if handle in self.existing: continue
            cc += 1
            if cc >= CTX_ROTATE: await ctx.close(); ctx = await self.make_ctx(browser); cc = 0
            page = await ctx.new_page()
            result = await scrape_fb_page(page, handle)
            await page.close(); self.total_scraped += 1
            if result is None:
                self.failed += 1; fails += 1
                if fails >= 5:
                    pause = random.uniform(60,120)
                    print(f'  [FB-W{wid}] ⚠️ {fails} fails, pause {pause:.0f}s'); sys.stdout.flush()
                    await asyncio.sleep(pause)
                    await ctx.close(); ctx = await self.make_ctx(browser); cc=0; fails=0
            elif result['followers'] < MIN_FOLLOWERS:
                self.skipped += 1; fails = 0
            else:
                fails = 0
                with open(BACKUP_PATH,'a') as f: f.write(json.dumps(result,ensure_ascii=False)+'\n')
                inserted = await insert_fb(result)
                if inserted:
                    self.new_inserted += 1; self.existing.add(result['username'].lower())
                    country = detect_country(result.get('bio',''),result.get('name',''),result['username'])
                    print(f'  ✅ FB #{self.new_inserted} @{result["username"]} ({country}) — {result["followers"]:,}')
                    sys.stdout.flush()
            if self.total_scraped % 10 == 0:
                elapsed = (time.time()-self.start_time)/3600; rate = self.new_inserted/max(elapsed,0.001)
                print(f'  📊 FB: {_count()} | New: {self.new_inserted} | Q: {self.queue.qsize()} | {rate:.0f}/hr | Fail: {self.failed}')
                sys.stdout.flush()
                with open(PROGRESS_PATH,'w') as f: json.dump({'ts':datetime.now(timezone.utc).isoformat(),'fb':_count(),'new':self.new_inserted,'q':self.queue.qsize(),'rate':round(rate,1),'fail':self.failed},f)
            await asyncio.sleep(random.uniform(DELAY_MIN,DELAY_MAX))
        await ctx.close()

    async def discoverer(self, browser):
        round_num = 0
        while self.running:
            round_num += 1
            print(f'\n{"="*50}\nFB DISCOVERY R{round_num} | Total: {_count()} | Q: {self.queue.qsize()}\n{"="*50}'); sys.stdout.flush()

            # Source 0: Priority handles from YuBin's KOL data
            if round_num == 1:
                import os
                pf = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/kol_full_fb.json'
                if os.path.exists(pf):
                    with open(pf) as f:
                        priority = json.load(f)
                    added = self.enqueue(priority)
                    print(f'  [KOL Priority] +{added} FB handles from YuBin data')
                    sys.stdout.flush()

            # Source 1: TikTok bios with FB links
            if round_num == 1:
                conn = sqlite3.connect(DB_PATH)
                bios = conn.execute('SELECT bio FROM creators WHERE bio IS NOT NULL').fetchall()
                conn.close()
                fb_handles = set()
                for (bio,) in bios:
                    if not bio: continue
                    for m in re.finditer(r'(?:facebook\.com/|fb\.com/|fb[:\s]+@?)([a-zA-Z0-9_.]{3,50})', bio.lower()):
                        h = m.group(1)
                        if h not in ('profile.php','pages','groups','watch'):
                            fb_handles.add(h)
                added = self.enqueue(list(fb_handles))
                print(f'  [Bios→FB] +{added}')

            # Source 2: TikTok usernames as FB candidates  
            if round_num == 1:
                conn = sqlite3.connect(DB_PATH)
                tt = [r[0] for r in conn.execute("SELECT username FROM platform_presences WHERE platform='tiktok'").fetchall()]
                conn.close()
                random.shuffle(tt)
                added = self.enqueue(tt[:500])  # Only try first 500 — FB match rate is low
                print(f'  [TikTok→FB] +{added}')

            # Source 3: Google discovery — most important for FB
            print('  [Google] Searching...')
            async with httpx.AsyncClient(http2=True, follow_redirects=True, timeout=15) as client:
                gqs = [
                    'site:facebook.com malaysia influencer',
                    'site:facebook.com indonesia influencer',
                    'site:facebook.com singapore influencer',
                    'site:facebook.com thailand influencer',
                    'site:facebook.com philippines influencer',
                    'site:facebook.com vietnam influencer',
                    'facebook page malaysia popular creator',
                    'facebook page indonesia popular creator',
                    'top facebook pages malaysia',
                    'top facebook pages indonesia',
                    'facebook influencer malaysia list',
                    'facebook influencer indonesia list',
                    'malaysia facebook content creator',
                    'indonesia facebook content creator',
                    'facebook page malaysia food',
                    'facebook page indonesia comedy',
                    'facebook gaming malaysia',
                    'facebook beauty influencer SEA',
                    'senarai facebook popular malaysia',
                    'daftar facebook terkenal indonesia',
                ]
                random.shuffle(gqs)
                for gq in gqs[:10]:
                    try:
                        resp = await client.get(f'https://www.google.com/search?q={quote(gq)}&num=50',
                            headers={'User-Agent':random.choice(UAS)}, timeout=15)
                        if resp.status_code == 200:
                            fb = re.findall(r'facebook\.com/([a-zA-Z0-9_.]+)', resp.text)
                            skip = {'profile.php','pages','groups','watch','marketplace','gaming','events','login','sharer','dialog','share','help'}
                            handles = [h for h in set(fb) if h.lower() not in skip and len(h) > 2]
                            added = self.enqueue(handles)
                            if added > 0: print(f'    "{gq[:40]}": +{added}')
                    except: pass
                    await asyncio.sleep(random.uniform(3,6))

            # Source 4: Creator names → Google "site:facebook.com [name]"
            if round_num <= 3:
                print('  [Name→FB] Searching by creator names...')
                conn = sqlite3.connect(DB_PATH)
                creators = conn.execute("SELECT name FROM creators WHERE name != '' ORDER BY RANDOM() LIMIT 50").fetchall()
                conn.close()
                async with httpx.AsyncClient(http2=True, follow_redirects=True, timeout=15) as client:
                    for (name,) in creators[:20]:
                        try:
                            resp = await client.get(f'https://www.google.com/search?q={quote(f"site:facebook.com {name}")}&num=10',
                                headers={'User-Agent':random.choice(UAS)}, timeout=15)
                            if resp.status_code == 200:
                                fb = re.findall(r'facebook\.com/([a-zA-Z0-9_.]+)', resp.text)
                                skip = {'profile.php','pages','groups','watch','marketplace','login','sharer','dialog','share','help'}
                                handles = [h for h in set(fb) if h.lower() not in skip and len(h) > 2]
                                self.enqueue(handles)
                        except: pass
                        await asyncio.sleep(random.uniform(3,6))
                        if not self.running: break

            elapsed = (time.time()-self.start_time)/3600; rate = self.new_inserted/max(elapsed,0.001)
            print(f'\n📊 FB R{round_num}: Total={_count()} | Q={self.queue.qsize()} | Seen={len(self.seen)} | {rate:.0f}/hr')
            sys.stdout.flush()
            await asyncio.sleep(120 if self.queue.qsize() > 50 else 30)

    async def run(self):
        self.existing = _existing(); self.seen = set(self.existing)
        print(f'🚀 TURBO FACEBOOK SCRAPER\n   Workers: {NUM_WORKERS}+1 | Existing: {len(self.existing)}\n{"="*50}'); sys.stdout.flush()
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
        print(f'\nFB DONE | {_count()} total | {self.new_inserted} new'); sys.stdout.flush()

if __name__ == '__main__':
    asyncio.run(TurboFB().run())
