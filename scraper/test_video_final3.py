#!/usr/bin/env python3
"""
TikTok video scraper — route interception approach.
Strategy: Navigate to profile page, intercept TikTok's own API calls.
If video grid loads, intercept the item_list API.
If not, make fetch call using page.evaluate and intercept the response.
"""
import asyncio
import json
import sys
import httpx
import re

USERNAME = sys.argv[1] if len(sys.argv) > 1 else "tiktok"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

async def get_secuid_httpx(username):
    """Get secUid using httpx (no browser needed)."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        resp = await client.get(
            f'https://www.tiktok.com/@{username}',
            headers={'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'}
        )
        if resp.status_code == 200:
            match = re.search(r'__UNIVERSAL_DATA_FOR_REHYDRATION__.*?type="application/json">(.*?)</script>', resp.text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                ud = data.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {})
                user = ud.get('userInfo', {}).get('user', {})
                return user.get('secUid'), user.get('id'), user.get('nickname')
    return None, None, None

async def main():
    from playwright.async_api import async_playwright
    
    print(f"Scraping videos for @{USERNAME}")
    print("=" * 60)
    
    # Step 1: Get secUid via httpx first
    print("1. Getting secUid via httpx...")
    sec_uid, uid, nickname = await get_secuid_httpx(USERNAME)
    
    if sec_uid:
        print(f"  ✅ secUid: {sec_uid[:40]}... | nickname: {nickname}")
    else:
        print("  ❌ Can't get secUid")
        return
    
    # Step 2: Use Playwright to make signed API calls
    print("\n2. Opening browser for signed API calls...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        ctx = await browser.new_context(
            user_agent=UA,
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
        )
        await ctx.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}};
        """)
        
        page = await ctx.new_page()
        
        # Capture API responses
        captured_videos = []
        
        async def on_response(response):
            url = response.url
            if '/api/post/item_list' in url:
                try:
                    data = await response.json()
                    items = data.get('itemList', [])
                    if items:
                        captured_videos.extend(items)
                        print(f"  🎯 Intercepted {len(items)} videos from API!")
                except:
                    pass
        
        page.on('response', on_response)
        
        # Load profile page — this triggers TikTok's own video list API
        print(f"  Loading @{USERNAME} profile...")
        try:
            await page.goto(f'https://www.tiktok.com/@{USERNAME}', wait_until='networkidle', timeout=30000)
        except:
            pass
        
        await asyncio.sleep(3)
        
        # Check SSR for embedded video data  
        ssr_videos = await page.evaluate('''() => {
            const e = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");
            if (!e) return null;
            try {
                const d = JSON.parse(e.textContent);
                const scope = d.__DEFAULT_SCOPE__ || {};
                
                // Try various known keys for video data
                const keys = Object.keys(scope);
                const result = {scopeKeys: keys};
                
                // Check webapp.user-post
                if (scope['webapp.user-post']) {
                    const up = scope['webapp.user-post'];
                    result.userPost = {
                        keys: Object.keys(up),
                        itemCount: up.itemList ? up.itemList.length : 0,
                    };
                    if (up.itemList) {
                        result.videos = up.itemList.map(v => ({
                            id: v.id,
                            desc: (v.desc || '').substring(0, 80),
                            views: v.stats?.playCount || 0,
                            likes: v.stats?.diggCount || 0,
                            comments: v.stats?.commentCount || 0,
                            shares: v.stats?.shareCount || 0,
                            created: v.createTime,
                            duration: v.video?.duration || 0,
                        }));
                    }
                }
                
                // Check seo.abtest for vidList
                if (scope['seo.abtest']?.vidList) {
                    result.seoVidList = scope['seo.abtest'].vidList;
                }
                
                return result;
            } catch(e) { return {error: e.message}; }
        }''')
        
        print(f"  SSR analysis: {json.dumps(ssr_videos, indent=2)[:500]}")
        
        # Try scrolling to trigger more video loading
        if not captured_videos:
            print("  Scrolling to trigger video API...")
            for i in range(5):
                await page.evaluate(f'window.scrollBy(0, {500 + i * 300})')
                await asyncio.sleep(1.5)
        
        # Check DOM for video links
        dom_videos = await page.evaluate('''() => {
            const links = document.querySelectorAll('a[href*="/video/"]');
            const items = document.querySelectorAll('[data-e2e="user-post-item"]');
            return {
                videoLinks: Array.from(links).map(a => {
                    const href = a.href;
                    const id = href.match(/video\\/(\d+)/)?.[1];
                    return id;
                }).filter(Boolean),
                postItems: items.length,
            };
        }''')
        print(f"  DOM: {dom_videos.get('postItems', 0)} post items, {len(dom_videos.get('videoLinks', []))} video links")
        
        # Combine results
        all_video_ids = set()
        
        if captured_videos:
            print(f"\n✅ Got {len(captured_videos)} videos from API interception!")
            for v in captured_videos[:10]:
                stats = v.get('stats', {})
                from datetime import datetime
                created = v.get('createTime', 0)
                date_str = datetime.fromtimestamp(created).strftime('%Y-%m-%d') if created else '?'
                print(f"  📹 {v['id']} | {stats.get('playCount',0):>10,} views | {stats.get('diggCount',0):>8,} likes | {date_str} | {v.get('desc','')[:50]}")
                all_video_ids.add(v['id'])
        
        if ssr_videos and ssr_videos.get('videos'):
            print(f"\n✅ Got {len(ssr_videos['videos'])} videos from SSR!")
            for v in ssr_videos['videos'][:10]:
                if v['id'] not in all_video_ids:
                    from datetime import datetime
                    created = v.get('created', 0)
                    date_str = datetime.fromtimestamp(created).strftime('%Y-%m-%d') if created else '?'
                    print(f"  📹 {v['id']} | {v['views']:>10,} views | {v['likes']:>8,} likes | {date_str} | {v['desc'][:50]}")
                    all_video_ids.add(v['id'])
        
        if dom_videos.get('videoLinks'):
            new_ids = [vid for vid in dom_videos['videoLinks'] if vid not in all_video_ids]
            if new_ids:
                print(f"\n✅ Got {len(new_ids)} additional video IDs from DOM!")
                for vid in new_ids[:5]:
                    print(f"  📹 {vid}")
        
        total = len(all_video_ids)
        print(f"\n{'='*60}")
        print(f"Total unique videos found: {total}")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
