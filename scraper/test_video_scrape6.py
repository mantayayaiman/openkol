#!/usr/bin/env python3
"""
Video scraping approach: 
1. httpx gets secUid from profile page 
2. Playwright (stealth) navigates and intercepts the post API calls with valid signatures
3. Alternative: parse video data directly from SSR HTML
"""
import asyncio, json, sys, httpx, re
from playwright.async_api import async_playwright

USERNAME = sys.argv[1] if len(sys.argv) > 1 else 'khaborinaldo'

async def approach_httpx_ssr(username):
    """Extract all video data embedded in the SSR HTML."""
    print(f'\n{"="*50}')
    print(f'APPROACH A: httpx SSR extraction')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
    }
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        r = await client.get(f'https://www.tiktok.com/@{username}', timeout=15)
        text = r.text
        
        # Look for ALL script tags with JSON data
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', text, re.DOTALL)
        print(f'  Found {len(scripts)} script tags')
        
        for i, script in enumerate(scripts):
            if len(script) > 1000 and ('"video"' in script or '"itemList"' in script or '"desc"' in script):
                print(f'  Script #{i}: {len(script)} bytes — contains video-like data!')
                try:
                    data = json.loads(script)
                    print(f'    Type: {type(data).__name__}, keys: {list(data.keys())[:10] if isinstance(data, dict) else "N/A"}')
                except:
                    # Not pure JSON, maybe contains JSON
                    json_matches = re.findall(r'\{[^{}]*"desc"[^{}]*"video"[^{}]*\}', script)
                    if json_matches:
                        print(f'    Found {len(json_matches)} inline JSON objects with video data')
        
        # Method: extract __UNIVERSAL_DATA__ and dump EVERYTHING
        match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', text, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            scope = data.get('__DEFAULT_SCOPE__', {})
            
            # Dump ALL scopes recursively looking for video items
            def find_items(obj, path='', depth=0):
                if depth > 8: return
                if isinstance(obj, dict):
                    if 'desc' in obj and ('video' in obj or 'stats' in obj):
                        print(f'    📹 Found video at {path}')
                        print(f'       desc: {obj.get("desc", "")[:80]}')
                        print(f'       stats: {obj.get("stats", {})}')
                        return
                    for k, v in obj.items():
                        find_items(v, f'{path}.{k}', depth+1)
                elif isinstance(obj, list):
                    for i, v in enumerate(obj[:20]):
                        find_items(v, f'{path}[{i}]', depth+1)
            
            print(f'\n  Searching all scope data for video objects...')
            find_items(scope)
        
        # Also look for video thumbnails in the HTML
        thumbnails = re.findall(r'(https://p\d+-sign[^"]*tiktokcdn[^"]*)', text)
        if thumbnails:
            unique = list(set(thumbnails))
            print(f'\n  Found {len(unique)} unique CDN image URLs (possible video covers)')
            for t in unique[:5]:
                print(f'    {t[:100]}')
        
        # Look for video IDs in the page
        video_ids = re.findall(r'/video/(\d{18,20})', text)
        if video_ids:
            unique_ids = list(set(video_ids))
            print(f'\n  Found {len(unique_ids)} video IDs in page links')
            for vid in unique_ids[:10]:
                print(f'    Video ID: {vid}')
        
        return text, r.cookies

async def approach_playwright_stealth(username):
    """Use Playwright with stealth settings to intercept real API calls."""
    print(f'\n{"="*50}')
    print(f'APPROACH B: Playwright stealth + API interception')
    
    async with async_playwright() as p:
        # Launch with stealth settings
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-dev-shm-usage',
            ]
        )
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
        )
        
        # Remove webdriver flag
        await ctx.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        """)
        
        page = await ctx.new_page()
        
        video_api_data = []
        
        async def handle_response(response):
            url = response.url
            if 'item_list' in url or 'post/list' in url or '/api/post/' in url:
                try:
                    body = await response.text()
                    if body:
                        data = json.loads(body)
                        items = data.get('itemList', data.get('items', []))
                        if items:
                            print(f'  ✅ Intercepted video API! {len(items)} videos')
                            video_api_data.extend(items)
                except: pass
            # Also check the big user/list response
            elif '/api/user/list' in url:
                try:
                    body = await response.text()
                    if body:
                        data = json.loads(body)
                        print(f'  /api/user/list keys: {list(data.keys())[:10]}')
                        # Check for recommended users with video data
                        if isinstance(data, dict):
                            for k, v in data.items():
                                if isinstance(v, list) and len(v) > 0:
                                    print(f'    {k}: list of {len(v)}')
                                    if isinstance(v[0], dict):
                                        print(f'    First item keys: {list(v[0].keys())[:10]}')
                except: pass
        
        page.on('response', handle_response)
        
        await page.goto(f'https://www.tiktok.com/@{username}', wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(3)
        
        # Scroll aggressively
        for i in range(8):
            await page.evaluate('window.scrollBy(0, 600)')
            await asyncio.sleep(0.8)
        
        await asyncio.sleep(3)
        
        # Check the DOM for video elements
        videos_dom = await page.evaluate('''() => {
            const results = [];
            
            // Method 1: data-e2e selectors
            document.querySelectorAll('[data-e2e="user-post-item"], [data-e2e="user-post-item-list"] a').forEach(el => {
                const link = el.tagName === 'A' ? el : el.querySelector('a');
                if (link) results.push({ href: link.href, type: 'data-e2e' });
            });
            
            // Method 2: any link to /video/
            document.querySelectorAll('a[href*="/video/"]').forEach(a => {
                results.push({ href: a.href, type: 'video-link' });
            });
            
            // Method 3: check for video grid containers
            const containers = document.querySelectorAll('[class*="DivVideoFeed"], [class*="DivThreeColumnContainer"], [class*="DivItemContainer"]');
            results.push({ containers: containers.length, type: 'containers' });
            
            // Method 4: check page text for video count
            const h2s = document.querySelectorAll('h2, span, strong');
            h2s.forEach(el => {
                if (el.textContent && /\d+\s*(videos?|posts?)/i.test(el.textContent)) {
                    results.push({ text: el.textContent.trim(), type: 'video-count' });
                }
            });
            
            return results;
        }''')
        
        print(f'\n  DOM analysis: {len(videos_dom)} items found')
        for v in videos_dom[:15]:
            print(f'    {v}')
        
        if video_api_data:
            print(f'\n  📹 Total videos from API: {len(video_api_data)}')
            for item in video_api_data[:5]:
                print(f'    {item.get("desc", "")[:60]} | plays={item.get("stats", {}).get("playCount", "?")}')
        
        await browser.close()

async def approach_video_page(username):
    """Get video data by fetching individual video pages (if we have IDs)."""
    print(f'\n{"="*50}')
    print(f'APPROACH C: Individual video page scraping')
    
    # First get video IDs from the profile page
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html',
    }
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        r = await client.get(f'https://www.tiktok.com/@{username}', timeout=15)
        text = r.text
        
        # Look for video IDs
        video_ids = list(set(re.findall(r'/video/(\d{18,20})', text)))
        
        # Also check __UNIVERSAL_DATA__ for secUid to build URL
        match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', text, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            seo = data.get('__DEFAULT_SCOPE__', {}).get('seo.abtest', {})
            vid_list = seo.get('vidList', [])
            # These might be video IDs
            for v in vid_list:
                if isinstance(v, str) and v.isdigit():
                    video_ids.append(v)
        
        video_ids = list(set(video_ids))
        print(f'  Found {len(video_ids)} video IDs: {video_ids[:5]}')
        
        if not video_ids:
            print('  No video IDs found, cannot proceed')
            return
        
        # Now fetch individual video pages to get data
        for vid_id in video_ids[:3]:
            try:
                # Try oembed for this specific video
                oembed_url = f'https://www.tiktok.com/oembed?url=https://www.tiktok.com/@{username}/video/{vid_id}'
                r2 = await client.get(oembed_url, timeout=10)
                if r2.status_code == 200:
                    oembed = r2.json()
                    print(f'\n  📹 Video {vid_id} (oEmbed):')
                    print(f'     Title: {oembed.get("title", "")[:80]}')
                    print(f'     Author: {oembed.get("author_name")}')
                    print(f'     Thumbnail: {oembed.get("thumbnail_url", "")[:80]}')
                    print(f'     Width: {oembed.get("thumbnail_width")} Height: {oembed.get("thumbnail_height")}')
                
                # Try the actual video page
                r3 = await client.get(f'https://www.tiktok.com/@{username}/video/{vid_id}', timeout=10)
                text3 = r3.text
                
                vmatch = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', text3, re.DOTALL)
                if vmatch:
                    vdata = json.loads(vmatch.group(1))
                    item_detail = vdata.get('__DEFAULT_SCOPE__', {}).get('webapp.video-detail', {})
                    if not item_detail:
                        item_detail = vdata.get('__DEFAULT_SCOPE__', {}).get('webapp.video.detail', {})
                    
                    if item_detail:
                        print(f'\n  📹 Video {vid_id} (page):')
                        print(f'     video-detail keys: {list(item_detail.keys())[:10]}')
                        item = item_detail.get('itemInfo', {}).get('itemStruct', {})
                        if item:
                            print(f'     desc: {item.get("desc", "")[:80]}')
                            stats = item.get('stats', {})
                            print(f'     plays: {stats.get("playCount", "?")}')
                            print(f'     likes: {stats.get("diggCount", "?")}')
                            print(f'     comments: {stats.get("commentCount", "?")}')
                            print(f'     shares: {stats.get("shareCount", "?")}')
                            video = item.get('video', {})
                            print(f'     duration: {video.get("duration", "?")}s')
                            print(f'     cover: {video.get("cover", "")[:80]}')
                    else:
                        # Check all scopes
                        for sk, sv in vdata.get('__DEFAULT_SCOPE__', {}).items():
                            if 'video' in sk.lower() or 'detail' in sk.lower():
                                print(f'     {sk}: {list(sv.keys())[:5] if isinstance(sv, dict) else type(sv)}')
            except Exception as e:
                print(f'  Error on {vid_id}: {e}')

async def main():
    print(f'🎬 Testing all video scraping approaches for @{USERNAME}')
    
    await approach_httpx_ssr(USERNAME)
    await approach_playwright_stealth(USERNAME)
    await approach_video_page(USERNAME)
    
    print(f'\n{"="*50}')
    print('DONE')

if __name__ == '__main__':
    asyncio.run(main())
