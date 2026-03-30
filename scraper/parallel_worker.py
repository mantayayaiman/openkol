#!/usr/bin/env python3
"""
Parallel worker — scrapes a chunk of handles for a specific platform.
Usage: python3 parallel_worker.py <platform> <chunk_file> <worker_id>
  platform: tt | ig
  chunk_file: path to JSON array of handles
  worker_id: 0, 1, 2...
"""
import asyncio, httpx, json, sqlite3, random, re, sys, time
from datetime import datetime, timezone

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
_db_lock = asyncio.Lock()

platform = sys.argv[1]  # 'tt' or 'ig'
chunk_file = sys.argv[2]
worker_id = sys.argv[3]

with open(chunk_file) as f:
    handles = json.load(f)

def detect_country(bio, name, username):
    text = f'{bio} {name} {username}'.lower()
    if re.search(r'[\u0E00-\u0E7F]', text): return 'TH'
    if re.search(r'[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]', text): return 'VN'
    for c, ws in {'MY':['malaysia','kuala lumpur','melayu','🇲🇾'],'ID':['indonesia','jakarta','🇮🇩'],
                  'SG':['singapore','🇸🇬'],'TH':['thailand','thai','🇹🇭'],
                  'PH':['philippines','filipino','pinoy','🇵🇭'],'VN':['vietnam','🇻🇳']}.items():
        if any(w in text for w in ws): return c
    return 'SEA'  # Don't assume MY — let smart_verifier fix with TikTok language field

UAS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
]

# ============ TikTok via Playwright ============
async def scrape_tt(handle):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=random.choice(UAS), viewport={'width':1920,'height':1080})
        inserted = 0; failed = 0; cc = 0
        
        for i, username in enumerate(handle):
            cc += 1
            if cc >= 50:
                await ctx.close()
                ctx = await browser.new_context(user_agent=random.choice(UAS), viewport={'width':1920,'height':1080})
                cc = 0
            
            page = await ctx.new_page()
            try:
                await page.goto(f'https://www.tiktok.com/@{username}', wait_until='domcontentloaded', timeout=15000)
                await asyncio.sleep(1)
                data = await page.evaluate('()=>{const e=document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");return e?e.textContent:null}')
                if data:
                    parsed = json.loads(data)
                    ud = parsed.get('__DEFAULT_SCOPE__',{}).get('webapp.user-detail',{})
                    if 'userInfo' in ud:
                        u = ud['userInfo']['user']; s = ud['userInfo']['stats']
                        c = {'username':u.get('uniqueId',username),'name':u.get('nickname',''),'bio':u.get('signature',''),
                             'avatar':u.get('avatarLarger',''),'followers':s.get('followerCount',0),
                             'following':s.get('followingCount',0),'likes':s.get('heartCount',0),
                             'videos':s.get('videoCount',0),'verified':u.get('verified',False)}
                        if c['followers'] >= 100:
                            async with _db_lock:
                                conn = sqlite3.connect(DB_PATH)
                                if not conn.execute("SELECT 1 FROM platform_presences WHERE platform='tiktok' AND LOWER(username)=LOWER(?)",(c['username'],)).fetchone():
                                    now = datetime.now(timezone.utc).isoformat()
                                    country = detect_country(c.get('bio',''),c.get('name',''),c['username'])
                                    cats = json.dumps(['entertainment'])
                                    cur = conn.execute('INSERT INTO creators (name,bio,profile_image,country,primary_platform,categories,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',
                                        (c['name'],c.get('bio',''),c.get('avatar',''),country,'tiktok',cats,now,now))
                                    cid = cur.lastrowid
                                    vids = max(c.get('videos',0),1)
                                    er = min(round((c.get('likes',0)/vids/max(c['followers'],1))*100,2),30.0)
                                    conn.execute('INSERT INTO platform_presences (creator_id,platform,username,url,followers,following,total_likes,total_videos,engagement_rate,last_scraped_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
                                        (cid,'tiktok',c['username'],f'https://www.tiktok.com/@{c["username"]}',c['followers'],c.get('following',0),c.get('likes',0),c.get('videos',0),er,now))
                                    score = 70+(15 if c.get('verified') else 0)+(10 if er>3 else 5 if er>1 else -15 if er<0.5 else 0)
                                    score = max(10,min(100,score))
                                    conn.execute('INSERT INTO audit_scores (creator_id,overall_score,follower_quality,engagement_authenticity,growth_consistency,comment_quality,signals_json,scored_at) VALUES (?,?,?,?,?,?,?,?)',
                                        (cid,score,score,score,score,score,'{}',now))
                                    conn.commit()
                                    inserted += 1
                                    if inserted % 10 == 0 or inserted <= 5:
                                        print(f'  [TT-W{worker_id}] ✅ #{inserted} @{c["username"]} — {c["followers"]:,}')
                                        sys.stdout.flush()
                                conn.close()
                    else: failed += 1
                else: failed += 1
            except: failed += 1
            await page.close()
            await asyncio.sleep(random.uniform(1.5, 2.5))
            
            if (i+1) % 50 == 0:
                print(f'  [TT-W{worker_id}] Progress: {i+1}/{len(handle)} | Inserted: {inserted} | Failed: {failed}')
                sys.stdout.flush()
        
        await ctx.close()
        await browser.close()
        print(f'  [TT-W{worker_id}] DONE: {inserted} inserted, {failed} failed out of {len(handle)}')
        sys.stdout.flush()

# ============ Instagram via HTTP embed ============
async def scrape_ig(handles_list):
    client = httpx.Client(follow_redirects=True, timeout=10)
    inserted = 0; failed = 0
    
    conn_check = sqlite3.connect(DB_PATH)
    existing = set(r[0].lower() for r in conn_check.execute("SELECT username FROM platform_presences WHERE platform='instagram'").fetchall())
    conn_check.close()
    
    for i, username in enumerate(handles_list):
        if username.lower() in existing: continue
        
        try:
            resp = client.get(f'https://www.instagram.com/{username}/embed/',
                headers={'User-Agent': random.choice(UAS)}, follow_redirects=True, timeout=10)
            if resp.status_code != 200: failed += 1; continue
            ctx = re.search(r'contextJSON":"(.*?)(?:"[,}])', resp.text)
            if not ctx: failed += 1; continue
            s = ctx.group(1).replace('\\"', '"')
            fc = re.search(r'followers_count"?\s*[:\s]\s*(\d+)', s)
            if not fc or int(fc.group(1)) < 1000: failed += 1; continue
            
            name_m = re.search(r'full_name"?\s*[:\s]\s*"?([^"\\,}]+)', s)
            followers = int(fc.group(1))
            name = (name_m.group(1).strip().rstrip('\\') if name_m else username)
            
            async with _db_lock:
                conn = sqlite3.connect(DB_PATH)
                if not conn.execute("SELECT 1 FROM platform_presences WHERE platform='instagram' AND LOWER(username)=LOWER(?)",(username,)).fetchone():
                    now = datetime.now(timezone.utc).isoformat()
                    country = detect_country('', name, username)
                    ex = conn.execute("SELECT c.id FROM creators c JOIN platform_presences pp ON pp.creator_id=c.id WHERE LOWER(pp.username)=LOWER(?) LIMIT 1",(username,)).fetchone()
                    if ex: cid = ex[0]
                    else:
                        cur = conn.execute('INSERT INTO creators (name,bio,profile_image,country,primary_platform,categories,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',
                            (name,'','',country,'instagram','["entertainment"]',now,now))
                        cid = cur.lastrowid
                    conn.execute('INSERT INTO platform_presences (creator_id,platform,username,url,followers,following,total_likes,total_videos,engagement_rate,last_scraped_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
                        (cid,'instagram',username,f'https://www.instagram.com/{username}/',followers,0,0,0,0,now))
                    conn.commit()
                    inserted += 1
                    existing.add(username.lower())
                    if inserted % 10 == 0 or inserted <= 5:
                        print(f'  [IG-W{worker_id}] ✅ #{inserted} @{username} — {followers:,}')
                        sys.stdout.flush()
                conn.close()
        except: failed += 1
        
        await asyncio.sleep(random.uniform(1.0, 2.0))
        
        if (i+1) % 100 == 0:
            print(f'  [IG-W{worker_id}] Progress: {i+1}/{len(handles_list)} | Inserted: {inserted} | Failed: {failed}')
            sys.stdout.flush()
    
    client.close()
    print(f'  [IG-W{worker_id}] DONE: {inserted} inserted, {failed} failed out of {len(handles_list)}')
    sys.stdout.flush()

async def main():
    print(f'[Worker {worker_id}] Starting {platform.upper()} with {len(handles)} handles')
    sys.stdout.flush()
    if platform == 'tt':
        await scrape_tt(handles)
    elif platform == 'ig':
        await scrape_ig(handles)

if __name__ == '__main__':
    asyncio.run(main())
