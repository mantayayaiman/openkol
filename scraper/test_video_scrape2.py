#!/usr/bin/env python3
"""
Test TikTok video scraping — approach: intercept signed API calls from TikTok's own JS.
Also test: headed browser, stealth patches, and cookie-based auth.
"""
import asyncio
import json
import sys

USERNAME = sys.argv[1] if len(sys.argv) > 1 else "khaborstiktok"

async def approach_intercept_with_stealth():
    """Use Playwright with stealth to load profile and intercept the actual video list API call."""
    print(f"\n=== Intercepting TikTok API calls for @{USERNAME} ===")
    
    from playwright.async_api import async_playwright
    
    captured = []
    all_requests = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--no-sandbox',
            ]
        )
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
        )
        
        # Apply stealth patches
        await ctx.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            window.chrome = {runtime: {}};
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({state: Notification.permission}) :
                originalQuery(parameters)
            );
        """)
        
        page = await ctx.new_page()
        
        async def on_response(response):
            url = response.url
            if '/api/post/item_list' in url or '/api/recommend' in url:
                try:
                    body = await response.json()
                    captured.append({'url': url, 'status': response.status, 'data': body})
                    print(f"  🎯 Captured post API: status={response.status}")
                except:
                    captured.append({'url': url, 'status': response.status, 'data': None})
                    print(f"  🎯 Captured post API (no JSON): status={response.status}")
            
            # Track all tiktok API calls
            if 'tiktok.com/api/' in url:
                all_requests.append(url.split('?')[0])
        
        page.on('response', on_response)
        
        print(f"  Loading @{USERNAME} profile...")
        try:
            await page.goto(f'https://www.tiktok.com/@{USERNAME}', wait_until='networkidle', timeout=30000)
        except:
            print("  Timeout on networkidle, continuing...")
        
        await asyncio.sleep(3)
        
        # Check what SSR data is available
        ssr = await page.evaluate('''() => {
            const e = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");
            if (!e) return null;
            const d = JSON.parse(e.textContent);
            const scope = d.__DEFAULT_SCOPE__ || {};
            return {
                keys: Object.keys(scope),
                userDetail: scope['webapp.user-detail'] ? {
                    statusCode: scope['webapp.user-detail'].statusCode,
                    hasUserInfo: !!scope['webapp.user-detail'].userInfo,
                } : null,
                seoVidList: scope['seo.abtest'] ? scope['seo.abtest'].vidList : null,
            };
        }''')
        print(f"  SSR data: {json.dumps(ssr, indent=2)}")
        
        # Try scrolling to trigger video grid loading
        print("  Scrolling to load video grid...")
        for i in range(3):
            await page.evaluate(f'window.scrollBy(0, {800 + i * 400})')
            await asyncio.sleep(2)
        
        # Check page content for video elements
        video_count = await page.evaluate('''() => {
            const items = document.querySelectorAll('[data-e2e="user-post-item"]');
            const links = document.querySelectorAll('a[href*="/video/"]');
            return {postItems: items.length, videoLinks: links.length};
        }''')
        print(f"  DOM video elements: {video_count}")
        
        # Extract video links from the page if present
        if video_count.get('videoLinks', 0) > 0:
            video_links = await page.evaluate('''() => {
                const links = document.querySelectorAll('a[href*="/video/"]');
                return Array.from(links).map(a => a.href).slice(0, 20);
            }''')
            print(f"  ✅ Found {len(video_links)} video links in DOM!")
            for link in video_links[:5]:
                vid_id = link.split('/video/')[-1].split('?')[0]
                print(f"    - Video ID: {vid_id}")
        
        # Also try extracting from SIGI_STATE or next_data
        sigi = await page.evaluate('''() => {
            // Check for SIGI_STATE
            const scripts = document.querySelectorAll('script');
            for (const s of scripts) {
                const t = s.textContent;
                if (t.includes('SIGI_STATE') || t.includes('ItemModule')) {
                    return t.substring(0, 500);
                }
            }
            return null;
        }''')
        if sigi:
            print(f"  Found SIGI_STATE: {sigi[:200]}...")
        
        # Check seo.abtest vidList (some profiles include video IDs here)
        if ssr and ssr.get('seoVidList'):
            vid_list = ssr['seoVidList']
            print(f"  ✅ SEO vidList has {len(vid_list)} video IDs!")
            for vid in vid_list[:5]:
                print(f"    - {vid}")
        
        print("\n  All TikTok API endpoints called:")
        for ep in set(all_requests):
            print(f"    - {ep}")
        
        await browser.close()
    
    # Analyze captured responses
    if captured:
        print(f"\n  📦 Captured {len(captured)} post/recommend API responses")
        for c in captured:
            data = c['data']
            if data and isinstance(data, dict):
                items = data.get('itemList', [])
                if items:
                    print(f"  ✅ Got {len(items)} videos!")
                    for v in items[:5]:
                        stats = v.get('stats', {})
                        print(f"    - {v.get('id')}: {stats.get('playCount', 0):,} views, {stats.get('diggCount', 0):,} likes | {v.get('desc', '')[:40]}")
                    return True
                else:
                    print(f"    Keys: {list(data.keys())[:10]}")
                    if 'statusCode' in data:
                        print(f"    statusCode: {data['statusCode']}")
    
    return False

async def approach_seo_vidlist():
    """Extract video IDs from seo.abtest.vidList in SSR, then fetch individual video details via oEmbed."""
    print("\n=== Approach: SEO vidList + oEmbed ===")
    
    from playwright.async_api import async_playwright
    import httpx
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080})
        page = await ctx.new_page()
        await page.goto(f'https://www.tiktok.com/@{USERNAME}', wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(1)
        
        data = await page.evaluate('()=>{const e=document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");return e?e.textContent:null}')
        await browser.close()
    
    if not data:
        print("  ❌ No SSR data")
        return
    
    parsed = json.loads(data)
    scope = parsed.get('__DEFAULT_SCOPE__', {})
    seo = scope.get('seo.abtest', {})
    vid_list = seo.get('vidList', [])
    
    if not vid_list:
        print("  ❌ No vidList in SEO data")
        # Check what IS in seo.abtest
        print(f"  seo.abtest keys: {list(seo.keys())}")
        return
    
    print(f"  Got {len(vid_list)} video IDs from SEO data")
    
    # Fetch details via oEmbed for each video
    async with httpx.AsyncClient() as client:
        for vid_id in vid_list[:5]:
            url = f'https://www.tiktok.com/oembed?url=https://www.tiktok.com/@{USERNAME}/video/{vid_id}'
            resp = await client.get(url)
            if resp.status_code == 200:
                d = resp.json()
                print(f"  ✅ {vid_id}: {d.get('title', '')[:50]} | author: {d.get('author_name')}")
            else:
                print(f"  ❌ {vid_id}: status {resp.status_code}")
            await asyncio.sleep(0.5)

async def main():
    print(f"Testing video scraping approaches for @{USERNAME}")
    print("=" * 60)
    
    await approach_intercept_with_stealth()
    await approach_seo_vidlist()
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    asyncio.run(main())
