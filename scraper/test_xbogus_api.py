#!/usr/bin/env python3
"""
Test TikTok video scraping using X-Bogus signature generation.
Directly calls /api/post/item_list/ with proper signing.
"""
import asyncio
import json
import sys
import time
import random
import string

# Import the X-Bogus implementation
sys.path.insert(0, '/tmp/tiktok_api/crawlers/douyin/web')
from xbogus import XBogus

import httpx

USERNAME = sys.argv[1] if len(sys.argv) > 1 else "khaborstiktok"

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

def gen_random_str(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

async def get_sec_uid(username):
    """Get secUid from profile page SSR data."""
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA, viewport={'width': 1920, 'height': 1080})
        page = await ctx.new_page()
        await page.goto(f'https://www.tiktok.com/@{username}', wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(1.5)
        data = await page.evaluate('()=>{const e=document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");return e?e.textContent:null}')
        
        # Also grab cookies
        cookies = await ctx.cookies()
        await browser.close()
    
    if not data:
        return None, None, {}
    
    parsed = json.loads(data)
    ud = parsed.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {})
    user_info = ud.get('userInfo', {}).get('user', {})
    sec_uid = user_info.get('secUid')
    uid = user_info.get('id')
    
    cookie_dict = {c['name']: c['value'] for c in cookies}
    return sec_uid, uid, cookie_dict

async def fetch_user_videos(sec_uid, cookies):
    """Fetch user videos using the signed API."""
    
    # Build the parameter string matching TikTok's web client format
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
        'device_id': str(random.randint(7000000000000000000, 7999999999999999999)),
        'device_platform': 'web_pc',
        'focus_state': 'true',
        'from_page': 'user',
        'history_len': str(random.randint(1, 10)),
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
    }
    
    # Add msToken (fake one — TikTok sometimes accepts it)
    params['msToken'] = gen_random_str(146) + '=='
    
    # Build query string
    param_str = '&'.join(f'{k}={v}' for k, v in params.items())
    
    # Generate X-Bogus signature
    xb = XBogus(user_agent=UA)
    signed_url, xbogus_val, _ = xb.getXBogus(param_str)
    
    full_url = f'https://www.tiktok.com/api/post/item_list/?{signed_url}'
    
    # Build cookie string
    cookie_str = '; '.join(f'{k}={v}' for k, v in cookies.items())
    
    headers = {
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
    }
    
    print(f"  Requesting: /api/post/item_list/ with X-Bogus={xbogus_val[:20]}...")
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(full_url, headers=headers, timeout=15)
        print(f"  Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"  Response keys: {list(data.keys())}")
            
            if 'itemList' in data:
                items = data['itemList']
                print(f"  ✅ Got {len(items)} videos!")
                for v in items[:5]:
                    stats = v.get('stats', {})
                    print(f"    - {v.get('id')}: {stats.get('playCount', 0):,} views, {stats.get('diggCount', 0):,} likes | {v.get('desc', '')[:40]}")
                return items
            elif 'statusCode' in data:
                print(f"  ❌ Status code: {data['statusCode']}, msg: {data.get('statusMsg', '')}")
            else:
                print(f"  Response: {json.dumps(data)[:500]}")
        else:
            print(f"  Response: {resp.text[:300]}")
    
    return None

async def approach_playwright_signed():
    """Use Playwright to execute TikTok's own signing JS, then make API calls."""
    print("\n=== Approach: Use Playwright to sign via TikTok's own JS ===")
    
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        ctx = await browser.new_context(
            user_agent=UA,
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Apply stealth
        await ctx.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
        
        page = await ctx.new_page()
        
        # Load TikTok to get the signing JS loaded
        print("  Loading TikTok homepage to initialize signing JS...")
        await page.goto('https://www.tiktok.com/', wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(3)
        
        # Check if byted_acrawler exists (this is the signing function)
        has_signer = await page.evaluate('''() => {
            return {
                byted_acrawler: typeof window.byted_acrawler !== 'undefined',
                _signature: typeof window._signature !== 'undefined',
                webmssdk: typeof window.webmssdk !== 'undefined',
            };
        }''')
        print(f"  Signing functions available: {has_signer}")
        
        # Try to generate signature using TikTok's own JS
        if has_signer.get('byted_acrawler'):
            print("  ✅ byted_acrawler available! Trying to sign...")
            try:
                result = await page.evaluate('''(url) => {
                    return window.byted_acrawler.frontierSign(url);
                }''', '/api/post/item_list/?secUid=test&count=30&cursor=0')
                print(f"  Signature result: {result}")
            except Exception as e:
                print(f"  ❌ Signing failed: {e}")
        
        await browser.close()

async def main():
    print(f"Testing TikTok video API for @{USERNAME}")
    print("=" * 60)
    
    # Step 1: Get secUid and cookies
    print(f"\n1. Getting secUid for @{USERNAME}...")
    sec_uid, uid, cookies = await get_sec_uid(USERNAME)
    
    if sec_uid:
        print(f"  secUid: {sec_uid[:40]}...")
        print(f"  uid: {uid}")
        print(f"  Cookies: {list(cookies.keys())}")
    else:
        print("  ❌ Couldn't get secUid (captcha?). Trying with known secUid...")
        # We can still try if we have a secUid from our DB
    
    # Step 2: Try X-Bogus signed API call
    if sec_uid:
        print("\n2. Fetching videos with X-Bogus signature...")
        await fetch_user_videos(sec_uid, cookies)
    
    # Step 3: Try Playwright signing approach
    await approach_playwright_signed()
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    asyncio.run(main())
