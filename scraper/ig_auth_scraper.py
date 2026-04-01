#!/usr/bin/env python3
"""
Authenticated IG scraper — uses burner account session to scrape remaining profiles.
Combines: API endpoint (for profiles that need auth) + embed endpoint (for public profiles)
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

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
PROGRESS_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/ig_auth_progress.json'

COOKIES = {
    'sessionid': '37017113104%3AlxyRYR8kIll9Tp%3A13%3AAYifO1H7d_ED1_8zEq5IEn5f9xJz0VgofQTW-W7Aqg',
    'csrftoken': '21t5nte7DxsCLKualrvdf9slBKGtksC0',
    'ds_user_id': '37017113104',
    'mid': 'ackOCwAEAAGo8w7M_dCdXfMkMrHS',
    'ig_did': '6E421E4A-FC89-41EE-AF7C-C84C8EEE6D45',
    'datr': 'Cw7JaZy1Se7LlyGqrbc4XrjU',
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'X-IG-App-ID': '936619743392459',
    'X-CSRFToken': '21t5nte7DxsCLKualrvdf9slBKGtksC0',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://www.instagram.com/',
}

def detect_country(bio, name, username):
    text = f'{bio} {name} {username}'.lower()
    if re.search(r'[\u0E00-\u0E7F]', text): return 'TH'
    if re.search(r'[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]', text): return 'VN'
    for c, ws in {'MY':['malaysia','kuala lumpur','melayu','🇲🇾'],'ID':['indonesia','jakarta','🇮🇩'],
                  'SG':['singapore','🇸🇬'],'TH':['thailand','thai','🇹🇭'],
                  'PH':['philippines','filipino','pinoy','🇵🇭'],'VN':['vietnam','🇻🇳']}.items():
        if any(w in text for w in ws): return c
    return 'SEA'

_db_lock = asyncio.Lock()

async def insert_ig(c):
    async with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        try:
            if conn.execute("SELECT 1 FROM platform_presences WHERE platform='instagram' AND LOWER(username)=LOWER(?)",(c['username'],)).fetchone(): return False
            now = datetime.now(timezone.utc).isoformat()
            country = detect_country(c.get('bio',''), c.get('name',''), c['username'])
            ex = conn.execute("SELECT c.id FROM creators c JOIN platform_presences pp ON pp.creator_id=c.id WHERE LOWER(pp.username)=LOWER(?) LIMIT 1",(c['username'],)).fetchone()
            if ex: cid = ex[0]
            else:
                cur = conn.execute('INSERT INTO creators (name,bio,profile_image,country,primary_platform,categories,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',
                    (c['name'],c.get('bio',''),c.get('avatar',''),country,'instagram','["entertainment"]',now,now))
                cid = cur.lastrowid
            conn.execute('INSERT INTO platform_presences (creator_id,platform,username,url,followers,following,total_likes,total_videos,engagement_rate,last_scraped_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
                (cid,'instagram',c['username'],f'https://www.instagram.com/{c["username"]}/',c['followers'],c.get('following',0),0,c.get('posts',0),0,now))
            conn.commit(); return True
        except: conn.rollback(); return False
        finally: conn.close()

def scrape_api(client, username):
    """Scrape via authenticated API — full data."""
    try:
        resp = client.get(f'https://www.instagram.com/api/v1/users/web_profile_info/?username={username}', headers=HEADERS)
        if resp.status_code != 200: return None
        data = resp.json()
        if data.get('status') == 'fail': return None
        user = data.get('data', {}).get('user', {})
        fc = user.get('edge_followed_by', {}).get('count', 0)
        if fc < 1000: return None
        return {
            'username': user.get('username', username),
            'name': user.get('full_name', ''),
            'bio': (user.get('biography', '') or '')[:200],
            'avatar': user.get('profile_pic_url_hd', ''),
            'followers': fc,
            'following': user.get('edge_follow', {}).get('count', 0),
            'posts': user.get('edge_owner_to_timeline_media', {}).get('count', 0),
        }
    except: return None

def scrape_embed(client_noauth, username):
    """Fallback: embed endpoint (no auth needed)."""
    try:
        resp = client_noauth.get(f'https://www.instagram.com/{username}/embed/',
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'},
            follow_redirects=True, timeout=10)
        if resp.status_code != 200: return None
        ctx = re.search(r'contextJSON":"(.*?)(?:"[,}])', resp.text)
        if not ctx: return None
        s = ctx.group(1).replace('\\"', '"')
        fc = re.search(r'followers_count"?\s*[:\s]\s*(\d+)', s)
        if not fc or int(fc.group(1)) < 1000: return None
        name_m = re.search(r'full_name"?\s*[:\s]\s*"?([^"\\,}]+)', s)
        return {
            'username': username,
            'name': (name_m.group(1).strip().rstrip('\\') if name_m else username),
            'bio': '', 'avatar': '',
            'followers': int(fc.group(1)), 'following': 0, 'posts': 0,
        }
    except: return None

async def main():
    # Load remaining handles
    conn = sqlite3.connect(DB_PATH)
    existing = set(r[0].lower() for r in conn.execute("SELECT username FROM platform_presences WHERE platform='instagram'").fetchall())
    conn.close()
    
    with open('/Users/aiman/.openclaw/workspace/projects/kreator/scraper/kol_full_ig.json') as f:
        all_ig = json.load(f)
    remaining = [h for h in all_ig if h.lower() not in existing]
    
    print('🚀 AUTHENTICATED IG SCRAPER')
    print(f'   Remaining: {len(remaining)} handles')
    print('   Method: API (auth) + embed (fallback)')
    print(f'{"="*50}'); sys.stdout.flush()
    
    client_auth = httpx.Client(follow_redirects=True, timeout=15, cookies=COOKIES)
    client_noauth = httpx.Client(follow_redirects=True, timeout=10)
    
    inserted = 0; api_ok = 0; embed_ok = 0; failed = 0
    start = time.time()
    
    for i, username in enumerate(remaining):
        # Try API first (richer data)
        result = scrape_api(client_auth, username)
        if result:
            api_ok += 1
        else:
            # Fallback to embed
            result = scrape_embed(client_noauth, username)
            if result: embed_ok += 1
        
        if result:
            ok = await insert_ig(result)
            if ok:
                inserted += 1
                print(f'  ✅ #{inserted} @{result["username"]} — {result["followers"]:,} ({"API" if result.get("posts",0) > 0 else "embed"})')
                sys.stdout.flush()
        else:
            failed += 1
        
        if (i+1) % 50 == 0:
            elapsed = (time.time() - start) / 3600
            rate = inserted / max(elapsed, 0.001)
            ig_total = sqlite3.connect(DB_PATH).execute("SELECT COUNT(*) FROM platform_presences WHERE platform='instagram'").fetchone()[0]
            print(f'  📊 [{i+1}/{len(remaining)}] IG total: {ig_total} | New: {inserted} | API: {api_ok} | Embed: {embed_ok} | Failed: {failed} | {rate:.0f}/hr')
            sys.stdout.flush()
            with open(PROGRESS_PATH, 'w') as f:
                json.dump({'ts': datetime.now(timezone.utc).isoformat(), 'ig': ig_total, 'new': inserted,
                           'api': api_ok, 'embed': embed_ok, 'fail': failed, 'remaining': len(remaining)-i-1}, f)
        
        # Rate limit: 3s for API, 1s for embed
        await asyncio.sleep(random.uniform(2.0, 4.0))
    
    client_auth.close()
    client_noauth.close()
    
    ig_total = sqlite3.connect(DB_PATH).execute("SELECT COUNT(*) FROM platform_presences WHERE platform='instagram'").fetchone()[0]
    print(f'\n{"="*50}')
    print(f'DONE | IG total: {ig_total} | New: {inserted} | API: {api_ok} | Embed: {embed_ok} | Failed: {failed}')
    sys.stdout.flush()

if __name__ == '__main__':
    asyncio.run(main())
