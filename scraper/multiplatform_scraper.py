#!/usr/bin/env python3
"""
Multi-platform scraper: Collects IG/YT/FB handles from blog/list sites,
then verifies each handle exists and has real followers using platform-specific methods.

Run: PLAYWRIGHT_BROWSERS_PATH=0 python3 -u scraper/multiplatform_scraper.py 2>&1 | tee scraper/multi_overnight.log
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
BACKUP_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/multi_backup.jsonl'
MIN_FOLLOWERS = 5000
DELAY_MIN = 3
DELAY_MAX = 6

NOISE_IG = {'p', 'explore', 'reel', 'stories', 'accounts', 'about', 'developer', 'legal',
            'embed.js', 'feedspotdotcom', 'emplifi', 'brandwatch', 'vulcanpost',
            'thesmartlocalsg', 'hootsuite', 'sproutsocial', 'shopify'}
NOISE_YT = {'FeedSpotOfficial', 'BrandwatchVideos', 'Emplifi', 'TheSmartLocal', 'results', 'watch'}
NOISE_FB = {'sharer.php', 'sharer', 'share', 'dialog', 'plugins', 'tr', 'groups',
            'pages', 'events', 'watch', 'login', 'help', 'privacy', 'terms',
            'policies', 'photo', 'profile.php', 'Feedspot', 'Vulcanpost',
            'TheSmartLocal', 'Brandwatch', 'Emplifi'}

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

def get_existing(platform):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT username FROM platform_presences WHERE platform = ?", (platform,)).fetchall()
    conn.close()
    return {r[0] for r in rows}

def insert_profile(c, platform):
    conn = sqlite3.connect(DB_PATH)
    existing = conn.execute("SELECT id FROM platform_presences WHERE platform = ? AND username = ?", (platform, c['username'])).fetchone()
    if existing:
        conn.close()
        return False
    
    now = datetime.now(timezone.utc).isoformat()
    country = c.get('country', detect_country(c.get('bio',''), c.get('name',''), c['username']))
    
    # Check existing creator by name
    existing_creator = conn.execute('SELECT id FROM creators WHERE LOWER(name) = LOWER(?)', (c.get('name',''),)).fetchone()
    
    if existing_creator:
        creator_id = existing_creator[0]
    else:
        categories = ['entertainment']
        bio = (c.get('bio','') + ' ' + c.get('name','')).lower()
        if any(w in bio for w in ['food', 'cook', 'recipe', 'makan']): categories = ['food', 'lifestyle']
        elif any(w in bio for w in ['music', 'song', 'singer']): categories = ['music', 'entertainment']
        elif any(w in bio for w in ['beauty', 'makeup']): categories = ['beauty', 'lifestyle']
        elif any(w in bio for w in ['comedy', 'funny']): categories = ['comedy', 'entertainment']
        elif any(w in bio for w in ['fashion', 'style']): categories = ['fashion', 'lifestyle']
        
        cur = conn.execute('INSERT INTO creators (name, bio, profile_image, country, primary_platform, categories, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)',
            (c['name'], c.get('bio',''), c.get('avatar',''), country, platform, json.dumps(categories), now, now))
        creator_id = cur.lastrowid
    
    url_map = {
        'instagram': f'https://www.instagram.com/{c["username"]}/',
        'youtube': f'https://www.youtube.com/@{c["username"]}',
        'facebook': f'https://www.facebook.com/{c["username"]}',
    }
    
    conn.execute('INSERT INTO platform_presences (creator_id, platform, username, url, followers, following, total_likes, total_videos, engagement_rate, last_scraped_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
        (creator_id, platform, c['username'], url_map.get(platform, ''),
         c.get('followers', 0), c.get('following', 0), c.get('likes', 0), c.get('posts', 0), 0, now))
    
    conn.commit()
    conn.close()
    return True

# ======== HANDLE COLLECTION ========

LIST_URLS = {
    # Feedspot — confirmed working for IG
    'ig_my': 'https://blog.feedspot.com/malaysian_instagram_influencers/',
    'ig_id': 'https://blog.feedspot.com/indonesian_instagram_influencers/',
    'ig_sg': 'https://blog.feedspot.com/singapore_instagram_influencers/',
    'ig_th': 'https://blog.feedspot.com/thai_instagram_influencers/',
    'ig_ph': 'https://blog.feedspot.com/filipino_instagram_influencers/',
    'ig_vn': 'https://blog.feedspot.com/vietnamese_instagram_influencers/',
    # Feedspot YouTube
    'yt_my': 'https://blog.feedspot.com/malaysian_youtube_channels/',
    'yt_id': 'https://blog.feedspot.com/indonesian_youtube_channels/',
    'yt_sg': 'https://blog.feedspot.com/singapore_youtube_channels/',
    'yt_th': 'https://blog.feedspot.com/thai_youtube_channels/',
    'yt_ph': 'https://blog.feedspot.com/filipino_youtube_channels/',
    'yt_vn': 'https://blog.feedspot.com/vietnamese_youtube_channels/',
    # Feedspot Facebook
    'fb_my': 'https://blog.feedspot.com/malaysian_facebook_pages/',
    'fb_id': 'https://blog.feedspot.com/indonesian_facebook_pages/',
    'fb_sg': 'https://blog.feedspot.com/singapore_facebook_pages/',
    # Try alternate URL patterns
    'ig_my2': 'https://blog.feedspot.com/malaysia_instagram_influencers/',
    'ig_id2': 'https://blog.feedspot.com/indonesia_instagram_influencers/',
    'yt_my2': 'https://blog.feedspot.com/malaysia_youtube_channels/',
    'yt_id2': 'https://blog.feedspot.com/indonesia_youtube_channels/',
    'yt_sg2': 'https://blog.feedspot.com/singapore_youtube/',
    'yt_ph2': 'https://blog.feedspot.com/philippines_youtube_channels/',
}

COUNTRY_MAP = {
    'my': 'MY', 'id': 'ID', 'sg': 'SG', 'th': 'TH', 'ph': 'PH', 'vn': 'VN',
    'my2': 'MY', 'id2': 'ID', 'sg2': 'SG', 'ph2': 'PH',
}

async def collect_handles_from_url(ctx, url, label):
    """Scrape a list page for social media handles."""
    page = await ctx.new_page()
    result = {'ig': set(), 'yt': set(), 'fb': set()}
    try:
        await page.goto(url, wait_until='networkidle', timeout=20000)
        await asyncio.sleep(2)
        
        title = await page.title()
        if 'not found' in title.lower() or '404' in title:
            return result
        
        # Scroll extensively to load all content
        for _ in range(15):
            await page.evaluate('window.scrollBy(0, 800)')
            await asyncio.sleep(0.3)
        
        content = await page.content()
        
        ig = set(re.findall(r'instagram\.com/([a-zA-Z0-9_.]{2,30})', content)) - NOISE_IG
        yt_at = set(re.findall(r'youtube\.com/@([a-zA-Z0-9_.-]{2,30})', content))
        yt_c = set(re.findall(r'youtube\.com/c/([a-zA-Z0-9_.-]{2,30})', content))
        yt_user = set(re.findall(r'youtube\.com/user/([a-zA-Z0-9_.-]{2,30})', content))
        yt = (yt_at | yt_c | yt_user) - NOISE_YT
        fb = set(re.findall(r'facebook\.com/([a-zA-Z0-9_.]{2,30})', content)) - NOISE_FB
        
        result = {'ig': ig, 'yt': yt, 'fb': fb}
        
    except:
        pass
    finally:
        await page.close()
    return result

async def verify_ig_via_meta(ctx, username):
    """Try to get IG data from page meta tags (doesn't require login)."""
    page = await ctx.new_page()
    try:
        await page.goto(f'https://www.instagram.com/{username}/', wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(2)
        
        # Extract from meta description: "X Followers, Y Following, Z Posts"
        meta = await page.evaluate('''() => {
            const m = document.querySelector('meta[name="description"]');
            return m ? m.content : '';
        }''')
        
        title = await page.title()
        og_img = await page.evaluate('''() => {
            const m = document.querySelector('meta[property="og:image"]');
            return m ? m.content : '';
        }''')
        
        if meta and ('Followers' in meta or 'followers' in meta):
            def parse_count(s):
                if not s: return 0
                s = s.strip().replace(',', '')
                if 'K' in s or 'k' in s: return int(float(re.sub(r'[^\d.]','',s)) * 1000)
                if 'M' in s or 'm' in s: return int(float(re.sub(r'[^\d.]','',s)) * 1000000)
                if 'B' in s or 'b' in s: return int(float(re.sub(r'[^\d.]','',s)) * 1000000000)
                try: return int(re.sub(r'[^\d]','',s))
                except: return 0
            
            f_match = re.search(r'([\d,.]+[KMBkmb]?)\s*Followers', meta)
            fo_match = re.search(r'([\d,.]+[KMBkmb]?)\s*Following', meta)
            p_match = re.search(r'([\d,.]+[KMBkmb]?)\s*Posts', meta)
            
            name_match = re.match(r'(.+?)\s*[\(@]', title.replace(' • Instagram photos and videos',''))
            name = name_match.group(1).strip() if name_match else title.split('(')[0].split('@')[0].strip()
            name = name.replace(' • Instagram', '').strip()
            
            if f_match:
                followers = parse_count(f_match.group(1))
                return {
                    'username': username,
                    'name': name,
                    'bio': meta[:200] if meta else '',
                    'avatar': og_img,
                    'followers': followers,
                    'following': parse_count(fo_match.group(1)) if fo_match else 0,
                    'posts': parse_count(p_match.group(1)) if p_match else 0,
                }
        
        return None
    except:
        return None
    finally:
        await page.close()

async def verify_yt_channel(ctx, handle):
    """Verify YouTube channel exists and get subscriber count."""
    page = await ctx.new_page()
    try:
        # Try @handle first, then /c/handle, then /user/handle
        for url_fmt in [f'https://www.youtube.com/@{handle}', f'https://www.youtube.com/c/{handle}']:
            await page.goto(url_fmt, wait_until='networkidle', timeout=15000)
            await asyncio.sleep(2)
            
            content = await page.content()
            title = await page.title()
            
            if '404' in title or 'not found' in title.lower():
                continue
            
            subs_match = re.search(r'"subscriberCountText":\{"simpleText":"([^"]+)"', content)
            if not subs_match:
                subs_match = re.search(r'"subscriberCountText":"([^"]+)"', content)
            
            name_match = re.search(r'"channelMetadataRenderer":\{"title":"([^"]+)"', content)
            
            if subs_match:
                subs_text = subs_match.group(1).replace(' subscribers','').replace(' subscriber','').strip()
                subs = 0
                try:
                    if 'M' in subs_text: subs = int(float(subs_text.replace('M','').replace(',','')) * 1000000)
                    elif 'K' in subs_text: subs = int(float(subs_text.replace('K','').replace(',','')) * 1000)
                    else: subs = int(subs_text.replace(',',''))
                except: pass
                
                name = name_match.group(1) if name_match else handle
                
                if subs > 0:
                    return {
                        'username': handle,
                        'name': name,
                        'bio': '',
                        'avatar': '',
                        'followers': subs,
                    }
            break
        
        return None
    except:
        return None
    finally:
        await page.close()

async def main():
    start = time.time()
    print(f'{"="*60}')
    print(f'MULTI-PLATFORM SCRAPER — {datetime.now(timezone.utc).isoformat()}')
    print(f'{"="*60}')
    sys.stdout.flush()
    
    existing_ig = get_existing('instagram')
    existing_yt = get_existing('youtube')
    existing_fb = get_existing('facebook')
    
    all_ig = {}  # username -> country
    all_yt = {}
    all_fb = {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        # PHASE 1: Collect handles from list sites
        print('\n--- Phase 1: Collecting handles from list sites ---')
        sys.stdout.flush()
        
        for label, url in LIST_URLS.items():
            label.split('_')[0]
            country_key = label.split('_')[1]
            country = COUNTRY_MAP.get(country_key, 'SEA')
            
            result = await collect_handles_from_url(ctx, url, label)
            
            for h in result['ig']:
                if h not in existing_ig: all_ig[h] = country
            for h in result['yt']:
                if h not in existing_yt: all_yt[h] = country
            for h in result['fb']:
                if h not in existing_fb: all_fb[h] = country
            
            total = len(result['ig']) + len(result['yt']) + len(result['fb'])
            if total > 0:
                print(f'  {label}: IG={len(result["ig"])} YT={len(result["yt"])} FB={len(result["fb"])}')
            sys.stdout.flush()
            await asyncio.sleep(2)
        
        print(f'\n  Queue: IG={len(all_ig)} YT={len(all_yt)} FB={len(all_fb)}')
        sys.stdout.flush()
        
        # PHASE 2: Verify Instagram handles
        print(f'\n--- Phase 2: Verifying {len(all_ig)} IG handles ---')
        sys.stdout.flush()
        ig_inserted = 0
        ig_failed = 0
        empty_streak = 0
        ctx_count = 0
        
        for username in list(all_ig.keys()):
            ctx_count += 1
            if ctx_count >= 25:
                await ctx.close()
                ctx = await browser.new_context(
                    user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
                    viewport={'width': 390, 'height': 844}
                )
                ctx_count = 0
            
            result = await verify_ig_via_meta(ctx, username)
            
            if result and result['followers'] >= MIN_FOLLOWERS:
                result['country'] = all_ig[username]
                with open(BACKUP_PATH, 'a') as f:
                    f.write(json.dumps({'platform': 'instagram', **result}, ensure_ascii=False) + '\n')
                if insert_profile(result, 'instagram'):
                    ig_inserted += 1
                    country = result.get('country', 'SEA')
                    print(f'  IG [{ig_inserted}] @{username} ({country}): {result["name"]} — {result["followers"]:,}')
                    sys.stdout.flush()
                empty_streak = 0
            elif result is None:
                ig_failed += 1
                empty_streak += 1
                if empty_streak >= 8:
                    print('  ⚠️ IG blocked, pausing 120s...')
                    sys.stdout.flush()
                    await asyncio.sleep(120)
                    empty_streak = 0
                    await ctx.close()
                    ctx = await browser.new_context(
                        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                        viewport={'width': 1920, 'height': 1080}
                    )
                    ctx_count = 0
            else:
                empty_streak = 0
            
            await asyncio.sleep(random.uniform(4, 8))  # IG needs slower pace
        
        print(f'  IG done: {ig_inserted} inserted, {ig_failed} failed')
        
        # Reset context for YT
        await ctx.close()
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        # PHASE 3: Verify YouTube handles
        print(f'\n--- Phase 3: Verifying {len(all_yt)} YT handles ---')
        sys.stdout.flush()
        yt_inserted = 0
        ctx_count = 0
        
        for handle in list(all_yt.keys()):
            ctx_count += 1
            if ctx_count >= 50:
                await ctx.close()
                ctx = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    viewport={'width': 1920, 'height': 1080}
                )
                ctx_count = 0
            
            result = await verify_yt_channel(ctx, handle)
            
            if result and result['followers'] >= MIN_FOLLOWERS:
                result['country'] = all_yt[handle]
                with open(BACKUP_PATH, 'a') as f:
                    f.write(json.dumps({'platform': 'youtube', **result}, ensure_ascii=False) + '\n')
                if insert_profile(result, 'youtube'):
                    yt_inserted += 1
                    country = result.get('country', 'SEA')
                    print(f'  YT [{yt_inserted}] @{handle} ({country}): {result["name"]} — {result["followers"]:,}')
                    sys.stdout.flush()
            
            await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
        
        print(f'  YT done: {yt_inserted} inserted')
        
        await ctx.close()
        await browser.close()
    
    # Summary
    elapsed = round((time.time() - start) / 60, 1)
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute('SELECT COUNT(*) FROM creators').fetchone()[0]
    platforms = dict(conn.execute('SELECT platform, COUNT(*) FROM platform_presences GROUP BY platform').fetchall())
    conn.close()
    
    print(f'\n{"="*60}')
    print(f'MULTI-PLATFORM COMPLETE — {elapsed} min')
    print(f'{"="*60}')
    print(f'New IG: {ig_inserted} | New YT: {yt_inserted}')
    print(f'Total creators: {total}')
    print(f'Platforms: {platforms}')
    sys.stdout.flush()

if __name__ == '__main__':
    asyncio.run(main())
