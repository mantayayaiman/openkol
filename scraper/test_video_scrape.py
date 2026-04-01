#!/usr/bin/env python3
"""
Test TikTok video scraping approaches.
Goal: Get video list (IDs, views, likes, dates) for a creator.
"""
import asyncio
import json
import sys

# Test creator
USERNAME = sys.argv[1] if len(sys.argv) > 1 else "khaborstiktok"

async def approach_1_tiktokapi():
    """Use davidteather/TikTok-Api with Playwright backend."""
    print("\n=== Approach 1: TikTok-Api (Playwright) ===")
    try:
        from TikTokApi import TikTokApi
        async with TikTokApi() as api:
            await api.create_sessions(num_sessions=1, sleep_after=3, headless=True)
            user = api.user(USERNAME)
            videos = []
            async for video in user.videos(count=10):
                vd = video.as_dict
                videos.append({
                    'id': vd.get('id'),
                    'desc': vd.get('desc', '')[:50],
                    'views': vd.get('stats', {}).get('playCount'),
                    'likes': vd.get('stats', {}).get('diggCount'),
                    'created': vd.get('createTime'),
                })
            print(f"✅ Got {len(videos)} videos!")
            for v in videos[:3]:
                print(f"  - {v['id']}: {v['views']:,} views, {v['likes']:,} likes | {v['desc']}")
            return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

async def approach_2_playwright_ssr():
    """Load profile page with Playwright and extract video data from SSR JSON."""
    print("\n=== Approach 2: Playwright SSR extraction ===")
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080})
            page = await ctx.new_page()
            
            await page.goto(f'https://www.tiktok.com/@{USERNAME}', wait_until='domcontentloaded', timeout=15000)
            await asyncio.sleep(2)
            
            data = await page.evaluate('''() => {
                const e = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");
                return e ? e.textContent : null;
            }''')
            
            await browser.close()
            
            if not data:
                print("❌ No SSR data found")
                return False
            
            parsed = json.loads(data)
            scope = parsed.get('__DEFAULT_SCOPE__', {})
            
            # Check for user-detail (we already use this)
            user_detail = scope.get('webapp.user-detail', {})
            user_detail.get('userInfo', {})
            
            # Check for user-post (this is what we want!)
            user_post = scope.get('webapp.user-post', {})
            
            # Check all available keys
            print(f"  Available scopes: {list(scope.keys())}")
            
            if user_post:
                print(f"  webapp.user-post keys: {list(user_post.keys())}")
                item_list = user_post.get('itemList', [])
                if item_list:
                    print(f"  ✅ Got {len(item_list)} videos from SSR!")
                    for v in item_list[:3]:
                        stats = v.get('stats', {})
                        print(f"    - {v.get('id')}: {stats.get('playCount', 0):,} views, {stats.get('diggCount', 0):,} likes | {v.get('desc', '')[:50]}")
                    return True
                else:
                    print("  ❌ itemList is empty")
            else:
                print("  ❌ webapp.user-post not in SSR data")
            
            # Dump all keys for debugging
            for k, v in scope.items():
                if isinstance(v, dict):
                    print(f"  {k}: {list(v.keys())[:5]}")
                    
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback; traceback.print_exc()
        return False

async def approach_3_mobile_api():
    """Try TikTok's mobile API endpoints via httpx."""
    print("\n=== Approach 3: Mobile API (httpx) ===")
    try:
        import httpx
        
        # First, get secUid from profile page
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                viewport={'width': 1920, 'height': 1080})
            page = await ctx.new_page()
            await page.goto(f'https://www.tiktok.com/@{USERNAME}', wait_until='domcontentloaded', timeout=12000)
            await asyncio.sleep(1)
            data = await page.evaluate('()=>{const e=document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");return e?e.textContent:null}')
            await browser.close()
        
        if not data:
            print("  ❌ Can't get secUid")
            return False
            
        parsed = json.loads(data)
        user_info = parsed.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {}).get('userInfo', {}).get('user', {})
        sec_uid = user_info.get('secUid', '')
        print(f"  secUid: {sec_uid[:30]}...")
        
        # Try the webapp API with minimal params
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Referer': f'https://www.tiktok.com/@{USERNAME}',
            'Accept': 'application/json',
        }
        
        # Try oEmbed API for individual videos (if we know IDs)
        print("  Trying oEmbed API...")
        async with httpx.AsyncClient(headers=headers) as client:
            resp = await client.get(f'https://www.tiktok.com/oembed?url=https://www.tiktok.com/@{USERNAME}')
            if resp.status_code == 200:
                print(f"  oEmbed response: {json.dumps(resp.json(), indent=2)[:200]}")
            else:
                print(f"  oEmbed status: {resp.status_code}")
        
        return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback; traceback.print_exc()
        return False

async def approach_4_intercept_api():
    """Use Playwright to intercept the actual API calls TikTok makes when loading a profile."""
    print("\n=== Approach 4: Playwright API interception ===")
    try:
        from playwright.async_api import async_playwright
        
        captured_responses = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080})
            page = await ctx.new_page()
            
            async def handle_response(response):
                url = response.url
                if 'item_list' in url or 'post' in url or 'user-post' in url:
                    try:
                        body = await response.json()
                        captured_responses.append({'url': url[:100], 'data': body})
                        print(f"  🎯 Captured: {url[:100]}")
                    except:
                        pass
            
            page.on('response', handle_response)
            
            await page.goto(f'https://www.tiktok.com/@{USERNAME}', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)
            
            # Try scrolling to trigger lazy loading
            await page.evaluate('window.scrollBy(0, 1000)')
            await asyncio.sleep(3)
            
            await browser.close()
        
        if captured_responses:
            print(f"  ✅ Captured {len(captured_responses)} API responses!")
            for r in captured_responses[:2]:
                data = r['data']
                if isinstance(data, dict):
                    items = data.get('itemList', data.get('items', []))
                    if items:
                        print(f"  Got {len(items)} items from {r['url']}")
                        for v in items[:3]:
                            stats = v.get('stats', {})
                            print(f"    - {v.get('id')}: {stats.get('playCount', 0):,} views | {v.get('desc', '')[:40]}")
            return True
        else:
            print("  ❌ No API calls captured")
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback; traceback.print_exc()
        return False

async def main():
    print(f"Testing video scraping for @{USERNAME}")
    print("=" * 60)
    
    # Test approaches in order of simplicity
    r2 = await approach_2_playwright_ssr()
    r4 = await approach_4_intercept_api()
    
    # Only try TikTok-Api if others fail
    if not r2 and not r4:
        await approach_1_tiktokapi()
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    print(f"  SSR extraction:    {'✅' if r2 else '❌'}")
    print(f"  API interception:  {'✅' if r4 else '❌'}")

if __name__ == '__main__':
    asyncio.run(main())
