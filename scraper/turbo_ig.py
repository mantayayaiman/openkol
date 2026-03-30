#!/usr/bin/env python3
"""
Turbo IG v3 — HTTP-based via /embed/ endpoint (no browser needed!)
Key insight: instagram.com/{username}/embed/ returns contextJSON with followers_count
No login, no Playwright, no anti-bot detection. Just needs 5-8s delay between requests.

Run: python3 -u scraper/turbo_ig.py 2>&1 | tee scraper/turbo_ig.log
"""
import asyncio, httpx, json, sqlite3, random, re, sys, time, os
from datetime import datetime, timezone

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
BACKUP_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/turbo_ig_backup.jsonl'
PROGRESS_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/turbo_ig_progress.json'
MIN_FOLLOWERS = 1000
DELAY_MIN, DELAY_MAX = 1.0, 2.0  # Embed endpoint handles 1s delay fine — tested 9/10 at 1s

UAS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
]

def detect_country(bio, name, username):
    text = f'{bio} {name} {username}'.lower()
    if re.search(r'[\u0E00-\u0E7F]', text): return 'TH'
    if re.search(r'[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]', text): return 'VN'
    for c, ws in {'MY':['malaysia','kuala lumpur','melayu','🇲🇾'],'ID':['indonesia','jakarta','🇮🇩'],
                  'SG':['singapore','🇸🇬'],'TH':['thailand','thai','bangkok','🇹🇭'],
                  'PH':['philippines','filipino','manila','pinoy','🇵🇭'],
                  'VN':['vietnam','hanoi','🇻🇳']}.items():
        if any(w in text for w in ws): return c
    return 'SEA'

_db_lock = asyncio.Lock()

async def insert_ig(c):
    async with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        try:
            if conn.execute("SELECT 1 FROM platform_presences WHERE platform='instagram' AND LOWER(username)=LOWER(?)",
                           (c['username'],)).fetchone(): return False
            now = datetime.now(timezone.utc).isoformat()
            country = detect_country(c.get('bio',''), c.get('name',''), c['username'])
            ex = conn.execute("SELECT c.id FROM creators c JOIN platform_presences pp ON pp.creator_id=c.id WHERE LOWER(pp.username)=LOWER(?) LIMIT 1",
                             (c['username'],)).fetchone()
            if ex: cid = ex[0]
            else:
                cats = ['entertainment']
                bio = (c.get('bio','')+' '+c.get('name','')).lower()
                for cat, ws in {'food':['food','cook','makan'],'beauty':['beauty','makeup','skincare'],
                               'comedy':['comedy','funny'],'fashion':['fashion','style','ootd','hijab'],
                               'gaming':['game','gaming'],'music':['music','singer','🎵']}.items():
                    if any(w in bio for w in ws): cats=[cat,'lifestyle' if cat in ('food','beauty','fashion') else 'entertainment']; break
                cur = conn.execute('INSERT INTO creators (name,bio,profile_image,country,primary_platform,categories,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',
                    (c['name'],c.get('bio',''),'',country,'instagram',json.dumps(cats),now,now))
                cid = cur.lastrowid
            conn.execute('INSERT INTO platform_presences (creator_id,platform,username,url,followers,following,total_likes,total_videos,engagement_rate,last_scraped_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
                (cid,'instagram',c['username'],f'https://www.instagram.com/{c["username"]}/',c['followers'],0,0,c.get('posts',0),0,now))
            conn.commit(); return True
        except: conn.rollback(); return False
        finally: conn.close()

def scrape_ig_embed(client, username):
    """Scrape IG profile via /embed/ endpoint — pure HTTP, no browser."""
    try:
        resp = client.get(f'https://www.instagram.com/{username}/embed/',
            headers={'User-Agent': random.choice(UAS)}, follow_redirects=True, timeout=15)
        if resp.status_code != 200: return None
        ctx = re.search(r'contextJSON":"(.*?)(?:"[,}])', resp.text)
        if not ctx: return None
        ctx_str = ctx.group(1).replace('\\"', '"').replace('\\\\', '\\')
        fc = re.search(r'followers_count"?\s*[:\s]\s*(\d+)', ctx_str)
        if not fc: return None
        followers = int(fc.group(1))
        if followers < MIN_FOLLOWERS: return None
        name_m = re.search(r'full_name"?\s*[:\s]\s*"?([^"\\,}]+)', ctx_str)
        bio_m = re.search(r'biography"?\s*[:\s]\s*"?([^"\\]{0,200})', ctx_str)
        media_m = re.search(r'media_count"?\s*[:\s]\s*(\d+)', ctx_str)
        return {
            'username': username,
            'name': (name_m.group(1).strip() if name_m else username).rstrip('\\'),
            'bio': (bio_m.group(1).strip() if bio_m else '').rstrip('\\'),
            'followers': followers,
            'posts': int(media_m.group(1)) if media_m else 0,
        }
    except: return None

async def main():
    # Load priority handles
    handles = []
    pf = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/kol_full_ig.json'
    if os.path.exists(pf):
        with open(pf) as f: handles.extend(json.load(f))
    # Add TikTok bio handles
    conn = sqlite3.connect(DB_PATH)
    bios = conn.execute('SELECT bio FROM creators WHERE bio IS NOT NULL').fetchall()
    for (bio,) in bios:
        if not bio: continue
        for m in re.finditer(r'(?:ig|instagram|insta)[:\s@/]*([a-zA-Z0-9_.]{3,30})', (bio or '').lower()):
            h = m.group(1)
            if h not in ('p','explore','reel','stories','reels'): handles.append(h)
    # Add TikTok usernames
    tt_users = [r[0] for r in conn.execute("SELECT username FROM platform_presences WHERE platform='tiktok'").fetchall()]
    existing_ig = set(r[0].lower() for r in conn.execute("SELECT username FROM platform_presences WHERE platform='instagram'").fetchall())
    conn.close()
    handles.extend(tt_users[:2000])
    # Dedupe and filter existing
    seen = set()
    queue = []
    for h in handles:
        h_low = h.lower().strip()
        if h_low and h_low not in seen and h_low not in existing_ig and len(h_low) > 1:
            seen.add(h_low); queue.append(h)
    random.shuffle(queue)
    
    print(f'🚀 TURBO IG v3 — HTTP Embed Scraper')
    print(f'   Queue: {len(queue)} handles')
    print(f'   Existing IG: {len(existing_ig)}')
    print(f'{"="*50}'); sys.stdout.flush()
    
    new_inserted = 0; failed = 0; total = 0
    start = time.time()
    
    client = httpx.Client(follow_redirects=True, timeout=15)
    
    for i, username in enumerate(queue):
        result = scrape_ig_embed(client, username)
        total += 1
        
        if result:
            inserted = await insert_ig(result)
            if inserted:
                new_inserted += 1
                country = detect_country(result.get('bio',''), result.get('name',''), result['username'])
                print(f'  ✅ IG #{new_inserted} @{result["username"]} ({country}) — {result["followers"]:,}')
                sys.stdout.flush()
                with open(BACKUP_PATH, 'a') as f:
                    f.write(json.dumps(result, ensure_ascii=False) + '\n')
        else:
            failed += 1
            # Only cooldown if we get HTTP errors, not just missing embed data
            # Most "fails" are profiles without embed data (not rate limits)
            if failed > 0 and failed % 200 == 0:
                pause = random.uniform(15, 30)
                print(f'  ⚠️ {failed} fails total, brief cooldown {pause:.0f}s')
                sys.stdout.flush()
                await asyncio.sleep(pause)
                client.close()
                client = httpx.Client(follow_redirects=True, timeout=15)
        
        if total % 50 == 0:
            elapsed = (time.time() - start) / 3600
            rate = new_inserted / max(elapsed, 0.001)
            ig_count = sqlite3.connect(DB_PATH).execute("SELECT COUNT(*) FROM platform_presences WHERE platform='instagram'").fetchone()[0]
            print(f'  📊 IG: {ig_count} total | New: {new_inserted} | Scraped: {total}/{len(queue)} | {rate:.0f}/hr | Fail: {failed}')
            sys.stdout.flush()
            with open(PROGRESS_PATH, 'w') as f:
                json.dump({'ts': datetime.now(timezone.utc).isoformat(), 'ig': ig_count,
                           'new': new_inserted, 'scraped': total, 'queue': len(queue)-i,
                           'rate': round(rate,1), 'fail': failed}, f)
        
        await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
    
    client.close()
    print(f'\n{"="*50}')
    print(f'IG DONE | New: {new_inserted} | Failed: {failed} | Total scraped: {total}')
    sys.stdout.flush()

if __name__ == '__main__':
    asyncio.run(main())
