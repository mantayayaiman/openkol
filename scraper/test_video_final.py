#!/usr/bin/env python3
"""
TikTok video scraper — uses TikTok's own JS signing.
Strategy: Load TikTok in Playwright, use byted_acrawler.frontierSign to sign,
then make API calls from within the browser context (same-origin, no CORS).
"""
import asyncio
import json
import sys
import time
import random

USERNAME = sys.argv[1] if len(sys.argv) > 1 else "khaborstiktok"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

async def main():
    from playwright.async_api import async_playwright
    
    print(f"Scraping videos for @{USERNAME}")
    print("=" * 60)
    
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
        
        # Step 1: Load TikTok homepage to initialize JS environment (avoid profile captcha)
        print("1. Loading TikTok homepage to initialize JS environment...")
        await page.goto('https://www.tiktok.com/explore', wait_until='domcontentloaded', timeout=20000)
        await asyncio.sleep(3)
        
        # Verify signing JS is loaded
        has_signer = await page.evaluate('() => typeof window.byted_acrawler !== "undefined" && typeof window.byted_acrawler.frontierSign === "function"')
        print(f"  Signing JS loaded: {has_signer}")
        
        sec_uid = None
        
        if not sec_uid:
            print("  ❌ No secUid from SSR. Will try API approach...")
        
        if not sec_uid:
            # Try fetching from the web API using username
            print("  Trying user detail API via browser fetch...")
            user_data = await page.evaluate('''async (username) => {
                try {
                    const params = new URLSearchParams({
                        uniqueId: username,
                        secUid: '',
                    });
                    const url = `/api/user/detail/?${params.toString()}`;
                    
                    // Sign the URL
                    let signedParams = {};
                    if (window.byted_acrawler && window.byted_acrawler.frontierSign) {
                        signedParams = window.byted_acrawler.frontierSign(url);
                    }
                    
                    const finalUrl = signedParams['X-Bogus'] ? 
                        `${url}&X-Bogus=${signedParams['X-Bogus']}` : url;
                    
                    const resp = await fetch(finalUrl, {credentials: 'include'});
                    const data = await resp.json();
                    return data;
                } catch(e) {
                    return {error: e.message};
                }
            }''', USERNAME)
            print(f"  User detail API: {json.dumps(user_data, indent=2)[:500] if user_data else 'null'}")
            
            if user_data and user_data.get('userInfo'):
                sec_uid = user_data['userInfo']['user']['secUid']
                print(f"  ✅ Got secUid from API: {sec_uid[:40]}...")
        
        if not sec_uid:
            print("\n❌ Cannot get secUid. Aborting.")
            await browser.close()
            return
        
        # Step 3: Fetch videos using signed API call from within the browser
        print(f"\n2. Fetching videos via signed API call...")
        
        videos = await page.evaluate('''async (secUid) => {
            try {
                const params = new URLSearchParams({
                    secUid: secUid,
                    count: '30',
                    cursor: '0',
                    coverFormat: '2',
                    from_page: 'user',
                    device_platform: 'web_pc',
                    aid: '1988',
                    app_language: 'en',
                    app_name: 'tiktok_web',
                    browser_language: 'en-US',
                    browser_name: 'Mozilla',
                    browser_online: 'true',
                    browser_platform: 'MacIntel',
                    channel: 'tiktok_web',
                    cookie_enabled: 'true',
                    focus_state: 'true',
                    history_len: '3',
                    is_fullscreen: 'false',
                    is_page_visible: 'true',
                    language: 'en',
                    os: 'mac',
                    priority_region: '',
                    referer: '',
                    region: 'US',
                    screen_height: '1080',
                    screen_width: '1920',
                    tz_name: 'America/New_York',
                    webcast_language: 'en',
                });
                
                const baseUrl = '/api/post/item_list/';
                const queryStr = params.toString();
                const url = `${baseUrl}?${queryStr}`;
                
                // Sign with TikTok's own signer
                let signedParams = {};
                if (window.byted_acrawler && window.byted_acrawler.frontierSign) {
                    signedParams = window.byted_acrawler.frontierSign(url);
                }
                
                let finalUrl = url;
                if (signedParams['X-Bogus']) {
                    finalUrl += '&X-Bogus=' + signedParams['X-Bogus'];
                }
                
                const resp = await fetch(finalUrl, {
                    credentials: 'include',
                    headers: {
                        'Accept': 'application/json',
                    }
                });
                
                const data = await resp.json();
                return {
                    status: resp.status,
                    statusCode: data.statusCode,
                    hasItems: !!(data.itemList && data.itemList.length),
                    itemCount: data.itemList ? data.itemList.length : 0,
                    items: (data.itemList || []).slice(0, 10).map(v => ({
                        id: v.id,
                        desc: (v.desc || '').substring(0, 60),
                        views: v.stats?.playCount || 0,
                        likes: v.stats?.diggCount || 0,
                        comments: v.stats?.commentCount || 0,
                        shares: v.stats?.shareCount || 0,
                        created: v.createTime,
                        duration: v.video?.duration || 0,
                    })),
                    cursor: data.cursor,
                    hasMore: data.hasMore,
                    keys: Object.keys(data),
                };
            } catch(e) {
                return {error: e.message, stack: e.stack};
            }
        }''', sec_uid)
        
        print(f"  Result: {json.dumps(videos, indent=2)}")
        
        if videos and videos.get('hasItems'):
            print(f"\n✅ SUCCESS! Got {videos['itemCount']} videos!")
            print(f"  Has more: {videos.get('hasMore')}")
            print(f"  Cursor: {videos.get('cursor')}")
            for v in videos.get('items', []):
                print(f"  - {v['id']}: {v['views']:,} views, {v['likes']:,} likes, {v['duration']}s | {v['desc']}")
        elif videos and videos.get('statusCode'):
            print(f"\n❌ API returned status: {videos['statusCode']}")
            print(f"  Response keys: {videos.get('keys')}")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
