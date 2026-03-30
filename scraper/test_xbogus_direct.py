#!/usr/bin/env python3
"""
Minimal test: XBogus signing + httpx for TikTok video list.
"""
import asyncio
import json
import sys
import time
import re
import httpx
import urllib.parse

sys.path.insert(0, '/tmp/tiktok_api/crawlers/douyin/web')
from xbogus import XBogus

USERNAME = sys.argv[1] if len(sys.argv) > 1 else "tiktok"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

async def main():
    print(f"Testing XBogus-signed API for @{USERNAME}")
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        # Step 1: Get profile page for secUid + cookies
        print("1. Getting profile page...")
        resp = await client.get(f'https://www.tiktok.com/@{USERNAME}', headers={
            'User-Agent': UA,
            'Accept-Language': 'en-US,en;q=0.9',
        })
        
        cookies = dict(resp.cookies)
        print(f"  Cookies: {list(cookies.keys())}")
        
        match = re.search(r'"application/json">(.*?)</script>', resp.text, re.DOTALL)
        if not match:
            print("  ❌ No SSR data")
            return
        
        data = json.loads(match.group(1))
        ud = data.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {})
        user = ud.get('userInfo', {}).get('user', {})
        sec_uid = user.get('secUid')
        
        print(f"  statusCode: {ud.get('statusCode')}")
        print(f"  secUid: {(sec_uid or 'N/A')[:40]}...")
        
        if not sec_uid:
            print("  ❌ No secUid")
            return
        
        # Step 2: Build params and sign
        print("\n2. Building signed API request...")
        
        params = (
            f"WebIdLastTime={int(time.time())}"
            f"&aid=1988"
            f"&app_language=en"
            f"&app_name=tiktok_web"
            f"&browser_language=en-US"
            f"&browser_name=Mozilla"
            f"&browser_online=true"
            f"&browser_platform=MacIntel"
            f"&browser_version={urllib.parse.quote(UA.split(')')[-1].strip())}"
            f"&channel=tiktok_web"
            f"&cookie_enabled=true"
            f"&count=30"
            f"&coverFormat=2"
            f"&cursor=0"
            f"&device_id={int(time.time()*1000)}"
            f"&device_platform=web_pc"
            f"&focus_state=true"
            f"&from_page=user"
            f"&history_len=3"
            f"&is_fullscreen=false"
            f"&is_page_visible=true"
            f"&language=en"
            f"&os=mac"
            f"&priority_region="
            f"&referer="
            f"&region=US"
            f"&screen_height=1080"
            f"&screen_width=1920"
            f"&secUid={urllib.parse.quote(sec_uid)}"
            f"&tz_name={urllib.parse.quote('America/New_York')}"
            f"&webcast_language=en"
            f"&msToken={cookies.get('msToken', 'x' * 148)}"
        )
        
        xb = XBogus(user_agent=UA)
        signed, xb_val, _ = xb.getXBogus(params)
        
        url = f"https://www.tiktok.com/api/post/item_list/?{signed}"
        print(f"  X-Bogus: {xb_val}")
        
        # Step 3: Make the request
        print("\n3. Calling API...")
        cookie_str = '; '.join(f'{k}={v}' for k, v in cookies.items())
        
        api_resp = await client.get(url, headers={
            'User-Agent': UA,
            'Referer': f'https://www.tiktok.com/@{USERNAME}',
            'Accept': 'application/json, text/plain, */*',
            'Cookie': cookie_str,
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        })
        
        print(f"  Status: {api_resp.status_code}")
        print(f"  Response length: {len(api_resp.text)}")
        
        if api_resp.text:
            try:
                result = api_resp.json()
                print(f"  Keys: {list(result.keys())}")
                
                items = result.get('itemList', [])
                if items:
                    print(f"\n  ✅ SUCCESS! {len(items)} videos!")
                    for v in items[:10]:
                        stats = v.get('stats', {})
                        from datetime import datetime
                        ct = v.get('createTime', 0)
                        dt = datetime.fromtimestamp(ct).strftime('%Y-%m-%d') if ct else '?'
                        print(f"    📹 {v['id']} | {stats.get('playCount',0):>10,} views | {stats.get('diggCount',0):>8,} likes | {dt} | {v.get('desc','')[:40]}")
                else:
                    print(f"  statusCode: {result.get('statusCode')}")
                    print(f"  statusMsg: {result.get('statusMsg')}")
                    print(f"  Full: {json.dumps(result)[:500]}")
            except Exception as e:
                print(f"  Not JSON: {api_resp.text[:500]}")
        else:
            print("  Empty response!")
        
        # Also try: pure httpx getting secUid from a DIFFERENT URL approach
        print("\n4. Bonus: trying oembed for video details...")
        oembed = await client.get(
            f'https://www.tiktok.com/oembed?url=https://www.tiktok.com/@{USERNAME}',
            headers={'User-Agent': UA}
        )
        if oembed.status_code == 200:
            print(f"  oembed: {json.dumps(oembed.json(), indent=2)[:300]}")

if __name__ == '__main__':
    asyncio.run(main())
