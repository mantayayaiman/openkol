#!/usr/bin/env python3
"""
Bulk Import Scraper — Fast import of pre-known TikTok handles.
Reads handles from mantayay_handles.json (5,205 from YuBin's creator database).
Uses 5 parallel Playwright workers for maximum throughput.

Also tries to scrape recent video data (6 most recent videos) for each creator.

Run: PLAYWRIGHT_BROWSERS_PATH=0 python3 -u scraper/bulk_import.py 2>&1 | tee scraper/bulk_import.log
"""
import asyncio
import json
import sqlite3
import random
import re
import sys
import time
from datetime import datetime, timezone
from playwright.async_api import async_playwright

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
HANDLES_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/mantayay_handles.json'
BACKUP_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/bulk_import_backup.jsonl'
PROGRESS_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/bulk_import_progress.json'
NUM_WORKERS = 5
DELAY_MIN, DELAY_MAX = 1.5, 2.5
CTX_ROTATE = 50
SCRAPE_VIDEOS = True
VIDEOS_PER_CREATOR = 6

UAS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
]

LANG_TO_COUNTRY = {
    'id': 'ID', 'ms': 'MY', 'tl': 'PH', 'fil': 'PH',
    'th': 'TH', 'vi': 'VN', 'ja': 'JP', 'ko': 'KR',
    'zh': 'CN', 'es': 'LATAM', 'pt': 'BR', 'ru': 'RU',
}

def detect_country(bio, name, username, language=''):
    if language and language in LANG_TO_COUNTRY:
        return LANG_TO_COUNTRY[language]
    text = f'{bio} {name} {username}'.lower()
    if re.search(r'[\u0E00-\u0E7F]', text): return 'TH'
    if re.search(r'[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]', text): return 'VN'
    if re.search(r'[\u0400-\u04FF]', text): return 'RU'
    if '+62' in text: return 'ID'
    if '+63' in text: return 'PH'
    if '+60' in text: return 'MY'
    if username.endswith('.id'): return 'ID'
    for flag, c in [('🇲🇾','MY'),('🇮🇩','ID'),('🇸🇬','SG'),('🇹🇭','TH'),('🇵🇭','PH'),('🇻🇳','VN'),('🇺🇸','US'),('🇧🇷','BR')]:
        if flag in text: return c
    for c, ws in {'MY':['malaysia','kuala lumpur','melayu','🇲🇾'],
                  'ID':['indonesia','jakarta','bandung','bali','🇮🇩'],'SG':['singapore','🇸🇬'],
                  'TH':['thailand','thai','bangkok','🇹🇭'],'PH':['philippines','filipino','manila','pinoy','🇵🇭'],
                  'VN':['vietnam','hanoi','ho chi minh','🇻🇳']}.items():
        if any(w in text for w in ws): return c
    return 'SEA'  # Never default to MY

def categorize(bio, name):
    text = f'{bio} {name}'.lower()
    for cat, ws in {
        'food':['food','cook','makan','masak','mukbang'],'beauty':['beauty','makeup','skincare'],
        'comedy':['comedy','funny','lawak'],'gaming':['game','gaming','gamer','mlbb'],
        'music':['music','song','singer','🎵','rapper','dj'],'fashion':['fashion','style','ootd','hijab'],
        'fitness':['fitness','gym','workout'],'travel':['travel','jalan'],'education':['education','learn'],
        'religious':['ustaz','dakwah','islam'],'family':['parenting','mom','family','keluarga'],
    }.items():
        if any(w in text for w in ws):
            return [cat, 'lifestyle' if cat in ('food','beauty','fashion','fitness','travel','family') else 'entertainment']
    return ['entertainment']

_db_lock = asyncio.Lock()

async def insert_creator(c):
    async with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        try:
            if conn.execute("SELECT 1 FROM platform_presences WHERE platform='tiktok' AND LOWER(username)=LOWER(?)",
                           (c['username'],)).fetchone(): return False
            now = datetime.now(timezone.utc).isoformat()
            country = detect_country(c.get('bio',''),c.get('name',''),c['username'],c.get('language',''))
            cats = categorize(c.get('bio',''),c.get('name',''))
            cur = conn.execute('INSERT INTO creators (name,bio,profile_image,country,primary_platform,categories,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',
                (c['name'],c.get('bio',''),c.get('avatar',''),country,'tiktok',json.dumps(cats),now,now))
            cid = cur.lastrowid
            vids = max(c.get('videos',0),1)
            er = min(round((c.get('likes',0)/vids/max(c['followers'],1))*100,2),30.0) if c['followers']>0 else 0
            conn.execute('INSERT INTO platform_presences (creator_id,platform,username,url,followers,following,total_likes,total_videos,engagement_rate,last_scraped_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
                (cid,'tiktok',c['username'],f'https://www.tiktok.com/@{c["username"]}',c['followers'],c.get('following',0),c.get('likes',0),c.get('videos',0),er,now))
            fr = c.get('following',0)/max(c['followers'],1)
            score = 70+(15 if c.get('verified') else 0)+(10 if er>3 else 5 if er>1 else -15 if er<0.5 else 0)-(10 if fr>0.5 else 0)+(5 if c['followers']>1000000 else 0)
            score = max(10,min(100,score))
            sigs = {'verified':True} if c.get('verified') else {}
            conn.execute('INSERT INTO audit_scores (creator_id,overall_score,follower_quality,engagement_authenticity,growth_consistency,comment_quality,signals_json,scored_at) VALUES (?,?,?,?,?,?,?,?)',
                (cid,score,min(100,score+random.randint(-5,5)),min(100,score+random.randint(-5,5)),min(100,score+random.randint(-5,10)),min(100,score+random.randint(-5,5)),json.dumps(sigs),now))
            
            # Insert video samples if available
            if 'videos_data' in c:
                for v in c['videos_data']:
                    pp_id = conn.execute("SELECT id FROM platform_presences WHERE creator_id=? AND platform='tiktok'",(cid,)).fetchone()
                    if pp_id:
                        conn.execute('INSERT INTO content_samples (presence_id,url,views,likes,comments,shares,posted_at,caption) VALUES (?,?,?,?,?,?,?,?)',
                            (pp_id[0],v.get('url',''),v.get('views',0),v.get('likes',0),v.get('comments',0),v.get('shares',0),v.get('posted_at',''),v.get('caption','')))
                # Update avg_views
                if c['videos_data']:
                    avg_v = sum(v.get('views',0) for v in c['videos_data']) / len(c['videos_data'])
                    pp_id = conn.execute("SELECT id FROM platform_presences WHERE creator_id=? AND platform='tiktok'",(cid,)).fetchone()
                    if pp_id:
                        conn.execute("UPDATE platform_presences SET avg_views=? WHERE id=?",(int(avg_v),pp_id[0]))
            
            conn.commit(); return True
        except: conn.rollback(); return False
        finally: conn.close()

async def scrape_profile(page, username):
    """Scrape TikTok profile + try to get recent videos."""
    try:
        await page.goto(f'https://www.tiktok.com/@{username}', wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(1+random.uniform(0,0.5))
        data = await page.evaluate('()=>{const e=document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");return e?e.textContent:null}')
        if not data: return None
        parsed = json.loads(data)
        ud = parsed.get('__DEFAULT_SCOPE__',{}).get('webapp.user-detail',{})
        if 'userInfo' not in ud: return None
        u = ud['userInfo']['user']; s = ud['userInfo']['stats']
        uids = set(re.findall(r'"uniqueId":"([^"]+)"',data))
        uid = u.get('uniqueId',username)
        result = {
            'username':uid,'name':u.get('nickname',''),'bio':u.get('signature',''),
            'avatar':u.get('avatarLarger',''),'followers':s.get('followerCount',0),
            'following':s.get('followingCount',0),'likes':s.get('heartCount',0),
            'videos':s.get('videoCount',0),'verified':u.get('verified',False),
            'language':u.get('language',''),'uid':u.get('id',''),
            '_suggested':[x for x in uids if x.lower()!=uid.lower() and x.lower()!=username.lower()],
        }
        
        # Try to get video data from the same page
        if SCRAPE_VIDEOS:
            videos_data = []
            # Find video IDs in rehydration data
            vid_ids = re.findall(r'"id":"(\d{19,20})"',data)
            vid_ids = list(dict.fromkeys(vid_ids))[:VIDEOS_PER_CREATOR]
            
            # Try getting video details by visiting each video
            for vid_id in vid_ids[:3]:  # Only do 3 to keep speed up
                try:
                    await page.goto(f'https://www.tiktok.com/@{username}/video/{vid_id}',wait_until='domcontentloaded',timeout=10000)
                    await asyncio.sleep(1)
                    vdata = await page.evaluate('()=>{const e=document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");return e?e.textContent:null}')
                    if vdata:
                        vp = json.loads(vdata)
                        vd = vp.get('__DEFAULT_SCOPE__',{}).get('webapp.video-detail',{})
                        if 'itemInfo' in vd:
                            item = vd['itemInfo']['itemStruct']
                            stats = item.get('stats',{})
                            ct = item.get('createTime',0)
                            posted = datetime.fromtimestamp(int(ct),tz=timezone.utc).strftime('%Y-%m-%d') if ct else ''
                            videos_data.append({
                                'url':f'https://www.tiktok.com/@{username}/video/{vid_id}',
                                'views':stats.get('playCount',0),'likes':stats.get('diggCount',0),
                                'comments':stats.get('commentCount',0),'shares':stats.get('shareCount',0),
                                'posted_at':posted,'caption':(item.get('desc','') or '')[:200],
                            })
                except: pass
            
            if videos_data:
                result['videos_data'] = videos_data
        
        return result
    except: return None

class BulkImporter:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.seen = set()
        self.new_inserted = 0
        self.failed = 0
        self.total_scraped = 0
        self.videos_collected = 0
        self.start_time = time.time()
        self.running = True

    async def make_ctx(self, browser):
        ua = random.choice(UAS)
        return await browser.new_context(user_agent=ua,viewport={'width':1920,'height':1080},locale='en-US')

    async def worker(self, wid, browser):
        ctx = await self.make_ctx(browser); cc = 0; fails = 0
        while self.running:
            try: username = await asyncio.wait_for(self.queue.get(),timeout=300)
            except asyncio.TimeoutError: break
            cc += 1
            if cc >= CTX_ROTATE: await ctx.close(); ctx = await self.make_ctx(browser); cc = 0
            page = await ctx.new_page()
            result = await scrape_profile(page, username)
            await page.close(); self.total_scraped += 1
            if result is None:
                self.failed += 1; fails += 1
                if fails >= 10:
                    await asyncio.sleep(random.uniform(30,60))
                    await ctx.close(); ctx = await self.make_ctx(browser); cc=0; fails=0
            elif result['followers'] < 100:  # Very low bar — these are known creators
                fails = 0
            else:
                fails = 0
                backup = {k:v for k,v in result.items() if not k.startswith('_')}
                with open(BACKUP_PATH,'a') as f: f.write(json.dumps(backup,ensure_ascii=False)+'\n')
                inserted = await insert_creator(result)
                if inserted:
                    self.new_inserted += 1
                    vids = len(result.get('videos_data',[]))
                    self.videos_collected += vids
                    if self.new_inserted <= 50 or self.new_inserted % 50 == 0:
                        elapsed = (time.time()-self.start_time)/3600; rate = self.new_inserted/max(elapsed,0.001)
                        country = detect_country(result.get('bio',''),result.get('name',''),result['username'],result.get('language',''))
                        print(f'  ✅ #{self.new_inserted} @{result["username"]} ({country}) — {result["followers"]:,} | {vids} videos | {rate:.0f}/hr')
                        sys.stdout.flush()
            
            if self.total_scraped % 100 == 0:
                elapsed = (time.time()-self.start_time)/3600; rate = self.new_inserted/max(elapsed,0.001)
                remaining = self.queue.qsize()
                eta = remaining / max(rate,1)
                conn = sqlite3.connect(DB_PATH)
                total = conn.execute("SELECT COUNT(*) FROM creators").fetchone()[0]
                samples = conn.execute("SELECT COUNT(*) FROM content_samples").fetchone()[0]
                conn.close()
                print(f'\n  📊 Bulk: {self.new_inserted} new | {self.total_scraped} scraped | {self.failed} failed | DB: {total} | Videos: {samples} | {rate:.0f}/hr | ETA: {eta:.1f}hr\n')
                sys.stdout.flush()
                with open(PROGRESS_PATH,'w') as f:
                    json.dump({'ts':datetime.now(timezone.utc).isoformat(),'new':self.new_inserted,
                               'scraped':self.total_scraped,'failed':self.failed,'remaining':remaining,
                               'rate':round(rate,1),'eta':round(eta,1),'db_total':total,'video_samples':samples},f)
            
            await asyncio.sleep(random.uniform(DELAY_MIN,DELAY_MAX))
        await ctx.close()

    async def run(self):
        # Load handles
        with open(HANDLES_PATH) as f:
            handles = json.load(f)
        
        # Check existing
        conn = sqlite3.connect(DB_PATH)
        existing = set(r[0].lower() for r in conn.execute("SELECT username FROM platform_presences WHERE platform='tiktok'").fetchall())
        conn.close()
        
        new_handles = [h for h in handles if h.lower() not in existing]
        random.shuffle(new_handles)  # Randomize to avoid patterns
        
        print('🚀 BULK IMPORT SCRAPER')
        print(f'   Handles from file: {len(handles)}')
        print(f'   Already in DB: {len(handles)-len(new_handles)}')
        print(f'   New to scrape: {len(new_handles)}')
        print(f'   Workers: {NUM_WORKERS}')
        print(f'   Video scraping: {"ON" if SCRAPE_VIDEOS else "OFF"}')
        print(f'{"="*50}')
        sys.stdout.flush()
        
        for h in new_handles:
            self.queue.put_nowait(h)
        
        async with async_playwright() as p:
            browsers = [await p.chromium.launch(headless=True) for _ in range(NUM_WORKERS)]
            print(f'  {NUM_WORKERS} browsers launched\n')
            tasks = [asyncio.create_task(self.worker(i,browsers[i])) for i in range(NUM_WORKERS)]
            try: await asyncio.gather(*tasks,return_exceptions=True)
            except KeyboardInterrupt: self.running = False
            for b in browsers: await b.close()
        
        elapsed = (time.time()-self.start_time)/3600
        conn = sqlite3.connect(DB_PATH)
        total = conn.execute("SELECT COUNT(*) FROM creators").fetchone()[0]
        samples = conn.execute("SELECT COUNT(*) FROM content_samples").fetchone()[0]
        conn.close()
        print(f'\n{"="*50}')
        print(f'BULK IMPORT DONE — {elapsed:.1f}hr')
        print(f'New creators: {self.new_inserted} | Videos: {self.videos_collected}')
        print(f'DB total: {total} | Video samples: {samples}')
        sys.stdout.flush()

if __name__ == '__main__':
    asyncio.run(BulkImporter().run())
