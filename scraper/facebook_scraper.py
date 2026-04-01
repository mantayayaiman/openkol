#!/usr/bin/env python3
"""
Facebook scraper: Discovers and scrapes SEA creator pages/profiles.
Uses Playwright to load public Facebook pages and extract follower data.

Facebook is the hardest to scrape — heavily protected.
Strategy: Use existing creator names to find their FB pages via Google,
then scrape the public page info.

Run: PLAYWRIGHT_BROWSERS_PATH=0 python3 -u scraper/facebook_scraper.py 2>&1 | tee scraper/fb_overnight.log
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
BACKUP_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/fb_backup.jsonl'
MIN_FOLLOWERS = 5000
DELAY_MIN = 5
DELAY_MAX = 10  # FB is very strict

def detect_country(bio, name, username):
    text = f'{bio} {name} {username}'.lower()
    if re.search(r'[\u0E00-\u0E7F]', text): return 'TH'
    if re.search(r'[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]', text): return 'VN'
    signals = {
        'MY': ['malaysia', 'kuala lumpur', 'sabah', 'sarawak', 'johor', 'penang', 'selangor', 'melayu', '🇲🇾'],
        'ID': ['indonesia', 'jakarta', 'surabaya', 'bandung', 'bali', '🇮🇩'],
        'SG': ['singapore', '🇸🇬'],
        'TH': ['thailand', 'thai', 'bangkok', '🇹🇭'],
        'PH': ['philippines', 'filipino', 'manila', 'pinoy', '🇵🇭'],
        'VN': ['vietnam', 'việt nam', 'hanoi', 'ho chi minh', '🇻🇳'],
    }
    for country, words in signals.items():
        for w in words:
            if w in text: return country
    return 'SEA'

def get_existing_fb():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT username FROM platform_presences WHERE platform = 'facebook'").fetchall()
    conn.close()
    return {r[0] for r in rows}

def insert_fb_creator(c):
    conn = sqlite3.connect(DB_PATH)
    existing = conn.execute("SELECT id FROM platform_presences WHERE platform = 'facebook' AND username = ?", (c['username'],)).fetchone()
    if existing:
        conn.close()
        return False
    
    now = datetime.now(timezone.utc).isoformat()
    country = detect_country(c.get('bio', ''), c.get('name', ''), c['username'])
    
    # Check if creator already exists (from other platforms)
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
        elif any(w in bio for w in ['fashion', 'style']): categories = ['fashion', 'lifestyle']
        
        cur = conn.execute('INSERT INTO creators (name, bio, profile_image, country, primary_platform, categories, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)',
            (c['name'], c.get('bio', ''), c.get('avatar', ''), country, 'facebook', json.dumps(categories), now, now))
        creator_id = cur.lastrowid
    
    conn.execute('INSERT INTO platform_presences (creator_id, platform, username, url, followers, following, total_likes, total_videos, engagement_rate, last_scraped_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
        (creator_id, 'facebook', c['username'], f'https://www.facebook.com/{c["username"]}',
         c['followers'], 0, c.get('likes', 0), 0, 0, now))
    
    conn.commit()
    conn.close()
    return True

def parse_fb_count(text):
    """Parse Facebook follower/like counts like '1.2M', '456K', '1,234,567'."""
    if not text:
        return 0
    text = text.strip().replace(',', '').replace(' ', '')
    try:
        if 'M' in text or 'm' in text:
            return int(float(re.sub(r'[^\d.]', '', text)) * 1_000_000)
        elif 'K' in text or 'k' in text:
            return int(float(re.sub(r'[^\d.]', '', text)) * 1_000)
        elif 'B' in text or 'b' in text:
            return int(float(re.sub(r'[^\d.]', '', text)) * 1_000_000_000)
        else:
            return int(re.sub(r'[^\d]', '', text))
    except:
        return 0

async def scrape_fb_page(ctx, page_id):
    """Scrape a Facebook page for public follower data."""
    page = await ctx.new_page()
    try:
        url = f'https://www.facebook.com/{page_id}'
        await page.goto(url, wait_until='networkidle', timeout=25000)
        await asyncio.sleep(3)
        
        # Check if we hit login wall
        content = await page.content()
        page_text = await page.evaluate('document.body.innerText')
        
        if 'log in' in page_text[:500].lower() and 'followers' not in page_text[:2000].lower():
            # Try mobile version which sometimes shows more
            await page.close()
            page = await ctx.new_page()
            await page.goto(f'https://m.facebook.com/{page_id}', wait_until='networkidle', timeout=25000)
            await asyncio.sleep(3)
            content = await page.content()
            page_text = await page.evaluate('document.body.innerText')
        
        # Extract name from title or og:title
        title = await page.title()
        name = title.replace(' | Facebook', '').replace(' - Facebook', '').strip()
        if not name or name == 'Facebook':
            og_title = await page.evaluate('() => { const m = document.querySelector("meta[property=\\"og:title\\"]"); return m ? m.content : ""; }')
            if og_title:
                name = og_title
        
        # Extract follower/like counts from page text
        followers = 0
        likes = 0
        bio = ''
        avatar = ''
        
        # Try meta description
        meta_desc = await page.evaluate('() => { const m = document.querySelector("meta[name=\\"description\\"]"); return m ? m.content : ""; }')
        if meta_desc:
            bio = meta_desc[:200]
        
        # Try og:image for avatar
        og_img = await page.evaluate('() => { const m = document.querySelector("meta[property=\\"og:image\\"]"); return m ? m.content : ""; }')
        if og_img:
            avatar = og_img
        
        # Parse follower count from various patterns
        # Pattern: "1.2M followers" or "1,234,567 followers"
        follower_patterns = [
            r'([\d,.]+[KMBkmb]?)\s*(?:followers|people follow this)',
            r'([\d,.]+[KMBkmb]?)\s*follower',
            r'Followed by\s*([\d,.]+[KMBkmb]?)',
        ]
        
        for pattern in follower_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                followers = parse_fb_count(match.group(1))
                break
        
        # Also try from structured data in HTML
        if followers == 0:
            struct_followers = re.findall(r'"follower_count":(\d+)', content)
            if struct_followers:
                followers = int(struct_followers[0])
        
        # Like count
        like_patterns = [
            r'([\d,.]+[KMBkmb]?)\s*(?:people like this|likes)',
            r'([\d,.]+[KMBkmb]?)\s*like',
        ]
        for pattern in like_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                likes = parse_fb_count(match.group(1))
                break
        
        if name and (followers > 0 or likes > 0):
            return {
                'username': page_id,
                'name': name,
                'bio': bio,
                'avatar': avatar,
                'followers': max(followers, likes),  # Use whichever is available
                'likes': likes,
            }
        
        return None
    except Exception:
        return None
    finally:
        await page.close()

async def discover_fb_pages(ctx):
    """Find Facebook page handles for SEA creators."""
    handles = set()
    
    # Source 1: Use existing creator names to find their FB pages via Google
    conn = sqlite3.connect(DB_PATH)
    conn.execute('SELECT name, country FROM creators').fetchall()
    conn.close()
    
    # Source 2: Google search for FB pages of known creators
    print('  Searching Google for FB pages...')
    sys.stdout.flush()
    
    search_queries = [
        'site:facebook.com malaysia influencer page',
        'site:facebook.com indonesia influencer page',
        'site:facebook.com singapore influencer page',
        'site:facebook.com thailand influencer page',
        'site:facebook.com philippines influencer page',
        'site:facebook.com vietnam influencer page',
        'top facebook influencers malaysia 2025',
        'top facebook influencers indonesia 2025',
        'top facebook pages southeast asia creators',
    ]
    
    for query in search_queries:
        page = await ctx.new_page()
        try:
            await page.goto(f'https://www.google.com/search?q={query}&num=30', wait_until='networkidle', timeout=20000)
            await asyncio.sleep(2)
            content = await page.content()
            fb_pages = re.findall(r'facebook\.com/([a-zA-Z0-9_.]+)', content)
            fb_pages = [p for p in set(fb_pages) if p not in (
                'login', 'help', 'pages', 'groups', 'events', 'marketplace',
                'watch', 'gaming', 'photo', 'photos', 'videos', 'posts',
                'about', 'reviews', 'community', 'ads', 'business',
                'privacy', 'terms', 'policies', 'settings', 'profile.php',
                'share', 'sharer', 'dialog', 'plugins', 'tr', 'flx',
            ) and len(p) > 2 and not p.startswith('share')]
            new_p = [p for p in fb_pages if p not in handles]
            handles.update(new_p)
            if new_p:
                print(f'    [{query[:40]}]: +{len(new_p)} pages')
                sys.stdout.flush()
        except:
            pass
        finally:
            await page.close()
        await asyncio.sleep(random.uniform(3, 6))
    
    # Source 3: Known SEA Facebook pages
    known_fb = [
        # MY
        'khairulaming', 'naborrelofasharip', 'JinnyboyTV', 'NamAborrew',
        'AfieqShazwan', 'HairulAzreen', 'BellNgasri',
        # ID  
        'AttaHalilintar', 'RaffiNaborrgitaSlavina', 'RiaRicis',
        'GadingMarten', 'FadilJaidi',
        # SG
        'JianHaoTan', 'TheSmartLocal', 'ZermattNeo',
        # TH
        'pimrypie', 'BamBam1A',
        # PH
        'mimiyuuuh', 'AlexGonzagaOfficial', 'IvanaAlawi',
        # VN
        'QuangLinhVlogs', 'SonTungMTP',
    ]
    known_clean = [h for h in known_fb if 'aborr' not in h.lower()]
    handles.update(known_clean)
    
    # Source 4: Try existing creator TikTok usernames as FB page IDs
    conn = sqlite3.connect(DB_PATH)
    tt_usernames = [r[0] for r in conn.execute("SELECT username FROM platform_presences WHERE platform = 'tiktok'").fetchall()]
    conn.close()
    handles.update(tt_usernames)
    
    return handles

async def main():
    start = time.time()
    print(f'{"="*60}')
    print(f'FACEBOOK SCRAPER — {datetime.now(timezone.utc).isoformat()}')
    print(f'{"="*60}')
    sys.stdout.flush()
    
    existing_fb = get_existing_fb()
    print(f'Existing FB in DB: {len(existing_fb)}')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Discover handles
        print('\n--- Discovering FB pages ---')
        sys.stdout.flush()
        all_handles = await discover_fb_pages(ctx)
        handle_queue = list(all_handles - existing_fb)
        random.shuffle(handle_queue)
        print(f'Total queue: {len(handle_queue)} pages to check')
        sys.stdout.flush()
        
        # Scrape each
        print('\n--- Scraping FB pages ---')
        sys.stdout.flush()
        new_inserted = 0
        failed = 0
        ctx_count = 0
        empty_streak = 0
        
        for i, page_id in enumerate(handle_queue):
            ctx_count += 1
            if ctx_count >= 20:  # FB is very strict, rotate often
                await ctx.close()
                # Alternate between desktop and mobile UA
                if ctx_count % 2 == 0:
                    ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
                    vp = {'width': 390, 'height': 844}
                else:
                    ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
                    vp = {'width': 1920, 'height': 1080}
                ctx = await browser.new_context(user_agent=ua, viewport=vp)
                ctx_count = 0
            
            result = await scrape_fb_page(ctx, page_id)
            
            if result is None:
                failed += 1
                empty_streak += 1
                if empty_streak >= 5:
                    print('  ⚠️ 5 failures in a row, pausing 180s (FB is very strict)...')
                    sys.stdout.flush()
                    await asyncio.sleep(180)
                    empty_streak = 0
                    await ctx.close()
                    ctx = await browser.new_context(
                        user_agent='Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                        viewport={'width': 412, 'height': 915}
                    )
                    ctx_count = 0
            elif result['followers'] < MIN_FOLLOWERS:
                empty_streak = 0
            else:
                empty_streak = 0
                with open(BACKUP_PATH, 'a') as f:
                    f.write(json.dumps(result, ensure_ascii=False) + '\n')
                
                inserted = insert_fb_creator(result)
                if inserted:
                    new_inserted += 1
                    existing_fb.add(result['username'])
                    country = detect_country(result.get('bio', ''), result.get('name', ''), result['username'])
                    print(f'  [{new_inserted}] {result["username"]} ({country}): {result["name"]} — {result["followers"]:,} followers')
                    sys.stdout.flush()
            
            await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
        
        await ctx.close()
        await browser.close()
    
    elapsed = round((time.time() - start) / 60, 1)
    conn = sqlite3.connect(DB_PATH)
    fb_total = conn.execute("SELECT COUNT(*) FROM platform_presences WHERE platform = 'facebook'").fetchone()[0]
    conn.close()
    
    print(f'\n{"="*60}')
    print(f'FB SCRAPE COMPLETE — {elapsed} min')
    print(f'{"="*60}')
    print(f'New FB pages: {new_inserted}')
    print(f'Failed: {failed}')
    print(f'Total FB in DB: {fb_total}')
    sys.stdout.flush()

if __name__ == '__main__':
    asyncio.run(main())
