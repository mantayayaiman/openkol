#!/usr/bin/env python3
"""
Test: headed browser + API interception.
TikTok detects headless Chrome. Let's try headed mode.
Also: try using cookies from the browser session + XBogus for direct httpx calls.
"""
import asyncio
import json
import sys
import time
import httpx
import re

sys.path.insert(0, '/tmp/tiktok_api/crawlers/douyin/web')
from xbogus import XBogus

USERNAME = sys.argv[1] if len(sys.argv) > 1 else "tiktok"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

async def approach_xbogus_httpx():
    """
    Use Evil0ctal's approach: 
    1. Get cookies (ttwid, msToken) from httpx 
    2. Get secUid from profile SSR
    3. Sign with XBogus
    4. Make API call with httpx
    """
    print(f"\n=== XBogus + httpx approach ===")
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        # Step 1: Hit TikTok to get cookies
        print("  Getting cookies...")
        resp = await client.get('https://www.tiktok.com/', headers={
            'User-Agent': UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        
        cookies = dict(resp.cookies)
        print(f"  Initial cookies: {list(cookies.keys())}")
        
        # Step 2: Get ttwid
        ttwid_resp = await client.post(
            'https://ttwid.byteoversea.com/ttwid/union/register/',
            content='{"region":"us","aid":1988,"needFid":false,"service":"www.tiktok.com","migrate_info":{"ticket":"","source":"node"},"cbUrlProtocol":"https","union":true}',
            headers={
                'Content-Type': 'text/plain',
                'User-Agent': UA,
            }
        )
        ttwid = ttwid_resp.cookies.get('ttwid')
        if ttwid:
            cookies['ttwid'] = ttwid
            print(f"  Got ttwid: {ttwid[:30]}...")
        else:
            print(f"  ttwid status: {ttwid_resp.status_code}")
        
        # Step 3: Get profile data + secUid
        print(f"  Getting @{USERNAME} profile...")
        profile_resp = await client.get(
            f'https://www.tiktok.com/@{USERNAME}',
            headers={
                'User-Agent': UA,
                'Accept-Language': 'en-US,en;q=0.9',
                'Cookie': '; '.join(f'{k}={v}' for k, v in cookies.items()),
            }
        )
        
        # Update cookies from response
        cookies.update(dict(profile_resp.cookies))
        mstoken = cookies.get('msToken', '')
        print(f"  Profile cookies: {list(cookies.keys())}")
        
        # Extract secUid
        match = re.search(r'__UNIVERSAL_DATA_FOR_REHYDRATION__.*?type="application/json">(.*?)</script>', profile_resp.text, re.DOTALL)
        if not match:
            print("  ❌ No SSR data")
            return
        
        data = json.loads(match.group(1))
        ud = data.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {})
        
        if ud.get('statusCode') == 10221:
            print(f"  ❌ Captcha'd (10221)")
            # Try with different cookie approach
        
        user = ud.get('userInfo', {}).get('user', {})
        sec_uid = user.get('secUid')
        
        if not sec_uid:
            print("  ❌ No secUid from profile")
            return
        
        print(f"  ✅ secUid: {sec_uid[:40]}...")
        
        # Step 4: Build and sign the API URL
        device_id = str(int(time.time() * 1000))[:19]
        
        params = {
            'WebIdLastTime': str(int(time.time())),
            'aid': '1988',
            'app_language': 'en',
            'app_name': 'tiktok_web',
            'browser_language': 'en-US',
            'browser_name': 'Mozilla',
            'browser_online': 'true',
            'browser_platform': 'MacIntel',
            'browser_version': '5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'channel': 'tiktok_web',
            'cookie_enabled': 'true',
            'count': '30',
            'coverFormat': '2',
            'cursor': '0',
            'device_id': device_id,
            'device_platform': 'web_pc',
            'focus_state': 'true',
            'from_page': 'user',
            'history_len': '3',
            'is_fullscreen': 'false',
            'is_page_visible': 'true',
            'language': 'en',
            'os': 'mac',
            'priority_region': '',
            'referer': '',
            'region': 'US',
            'screen_height': '1080',
            'screen_width': '1920',
            'secUid': sec_uid,
            'tz_name': 'America/New_York',
            'webcast_language': 'en',
            'msToken': mstoken or 'fake_' + 'x' * 140,
        }
        
        param_str = '&'.join(f'{k}={v}' for k, v in params.items())
        
        # Sign with XBogus
        xb = XBogus(user_agent=UA)
        signed_params, xbogus_val, _ = xb.getXBogus(param_str)
        
        full_url = f'https://www.tiktok.com/api/post/item_list/?{signed_params}'
        
        print(f"  X-Bogus: {xbogus_val}")
        print(f"  Making signed API call...")
        
        cookie_str = '; '.join(f'{k}={v}' for k, v in cookies.items())
        
        api_resp = await client.get(full_url, headers={
            'User-Agent': UA,
            'Referer': f'https://www.tiktok.com/@{USERNAME}',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cookie': cookie_str,
            'Sec-Ch-Ua': '"Chromium";v="131", "Not_A Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        })
        
        print(f"  Status: {api_resp.status_code}")
        
        if api_resp.status_code == 200 and api_resp.text:
            try:
                result = api_resp.json()
                print(f"  Response keys: {list(result.keys())}")
                
                items = result.get('itemList', [])
                if items:
                    print(f"  ✅ Got {len(items)} videos!")
                    for v in items[:10]:
                        stats = v.get('stats', {})
                        from datetime import datetime
                        created = v.get('createTime', 0)
                        date_str = datetime.fromtimestamp(created).strftime('%Y-%m-%d') if created else '?'
                        print(f"    📹 {v['id']} | {stats.get('playCount',0):>10,} views | {stats.get('diggCount',0):>8,} likes | {date_str} | {v.get('desc','')[:40]}")
                    return True
                else:
                    print(f"  statusCode: {result.get('statusCode')}")
                    print(f"  statusMsg: {result.get('statusMsg')}")
                    print(f"  Full response: {json.dumps(result)[:500]}")
            except:
                print(f"  Not JSON: {api_resp.text[:300]}")
        else:
            print(f"  Response: {api_resp.text[:300]}")
    
    return False

async def approach_headed_browser():
    """Try headed browser (visible window) — harder for TikTok to detect."""
    print(f"\n=== Headed browser approach ===")
    from playwright.async_api import async_playwright
    
    captured = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # HEADED mode
            args=['--disable-blink-features=AutomationControlled']
        )
        ctx = await browser.new_context(
            user_agent=UA,
            viewport={'width': 1920, 'height': 1080},
        )
        await ctx.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
        
        page = await ctx.new_page()
        
        async def on_response(response):
            if '/api/post/item_list' in response.url:
                try:
                    data = await response.json()
                    items = data.get('itemList', [])
                    if items:
                        captured.extend(items)
                        print(f"  🎯 Captured {len(items)} videos!")
                except: pass
        
        page.on('response', on_response)
        
        print(f"  Loading @{USERNAME}...")
        await page.goto(f'https://www.tiktok.com/@{USERNAME}', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(5)
        
        # Scroll
        for i in range(3):
            await page.evaluate(f'window.scrollBy(0, {600})')
            await asyncio.sleep(2)
        
        dom = await page.evaluate('''() => {
            const items = document.querySelectorAll('[data-e2e="user-post-item"]');
            const links = document.querySelectorAll('a[href*="/video/"]');
            return {items: items.length, links: links.length};
        }''')
        print(f"  DOM: {dom}")
        
        if captured:
            print(f"\n  ✅ Got {len(captured)} videos from API!")
            for v in captured[:5]:
                stats = v.get('stats', {})
                print(f"    📹 {v['id']}: {stats.get('playCount',0):,} views")
        
        await browser.close()
    
    return len(captured) > 0

async def main():
    print(f"Testing TikTok video scraping for @{USERNAME}")
    print("=" * 60)
    
    # Try httpx approach first (faster, no browser)
    result = await approach_xbogus_httpx()
    
    if not result:
        # Try headed browser
        print("\n  httpx approach failed, trying headed browser...")
        result = await approach_headed_browser()
    
    print("\n" + "=" * 60)
    print(f"Final result: {'✅ SUCCESS' if result else '❌ FAILED'}")

if __name__ == '__main__':
    asyncio.run(main())
