#!/usr/bin/env python3
"""
TikTok video scraper — final approach.
1. Load TikTok profile page to get secUid from SSR
2. Navigate to explore page to get signing JS
3. Use byted_acrawler.frontierSign to sign video list API calls
4. Fetch videos from within browser context
"""
import asyncio
import json
import sys

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
        
        # Step 1: Load profile page (even if captcha'd, we sometimes get secUid from SSR)
        print("1. Loading profile page for secUid...")
        await page.goto(f'https://www.tiktok.com/@{USERNAME}', wait_until='domcontentloaded', timeout=20000)
        await asyncio.sleep(2)
        
        # Try to get secUid from SSR
        sec_uid = await page.evaluate('''() => {
            const e = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");
            if (!e) return null;
            try {
                const d = JSON.parse(e.textContent);
                const ud = d.__DEFAULT_SCOPE__?.['webapp.user-detail'] || {};
                return ud.userInfo?.user?.secUid || null;
            } catch(e) { return null; }
        }''')
        
        if sec_uid:
            print(f"  ✅ Got secUid: {sec_uid[:40]}...")
        else:
            print("  ❌ No secUid from SSR (captcha'd)")
            
            # Try httpx approach to get secUid
            print("  Trying httpx with mobile UA for secUid...")
            import httpx
            mobile_ua = 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36'
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                resp = await client.get(
                    f'https://www.tiktok.com/@{USERNAME}',
                    headers={'User-Agent': mobile_ua, 'Accept-Language': 'en-US,en;q=0.9'}
                )
                if resp.status_code == 200:
                    import re
                    match = re.search(r'"secUid":"([^"]+)"', resp.text)
                    if match:
                        sec_uid = match.group(1)
                        print(f"  ✅ Got secUid via httpx: {sec_uid[:40]}...")
                    else:
                        # Try finding it in the UNIVERSAL_DATA
                        match2 = re.search(r'__UNIVERSAL_DATA_FOR_REHYDRATION__.*?<\/script>', resp.text, re.DOTALL)
                        if match2:
                            script_text = match2.group(0)
                            json_match = re.search(r'>(\{.*?\})<', script_text, re.DOTALL)
                            if json_match:
                                try:
                                    data = json.loads(json_match.group(1))
                                    ud = data.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {})
                                    sec_uid = ud.get('userInfo', {}).get('user', {}).get('secUid')
                                    if sec_uid:
                                        print(f"  ✅ Got secUid from httpx SSR: {sec_uid[:40]}...")
                                except:
                                    pass
                        if not sec_uid:
                            print(f"  httpx status: {resp.status_code}, no secUid found")
                else:
                    print(f"  httpx status: {resp.status_code}")
        
        if not sec_uid:
            print("\n❌ Cannot get secUid. Aborting.")
            await browser.close()
            return
        
        # Step 2: Check if signing JS is available
        has_signer = await page.evaluate('() => typeof window.byted_acrawler?.frontierSign === "function"')
        print(f"\n2. Signing JS available: {has_signer}")
        
        if not has_signer:
            # Navigate to a simpler page to try loading it
            print("  Navigating to explore page...")
            await page.goto('https://www.tiktok.com/explore', wait_until='domcontentloaded', timeout=15000)
            await asyncio.sleep(3)
            has_signer = await page.evaluate('() => typeof window.byted_acrawler?.frontierSign === "function"')
            print(f"  After explore: {has_signer}")
        
        # Step 3: Make the signed API call from within the browser
        print("\n3. Fetching videos...")
        
        result = await page.evaluate('''async (secUid) => {
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
                    browser_language: navigator.language,
                    browser_name: 'Mozilla',
                    browser_online: String(navigator.onLine),
                    browser_platform: navigator.platform,
                    channel: 'tiktok_web',
                    cookie_enabled: String(navigator.cookieEnabled),
                    focus_state: 'true',
                    history_len: String(history.length),
                    is_fullscreen: 'false',
                    is_page_visible: String(!document.hidden),
                    language: 'en',
                    os: 'mac',
                    priority_region: '',
                    referer: '',
                    region: 'US',
                    screen_height: String(screen.height),
                    screen_width: String(screen.width),
                    tz_name: Intl.DateTimeFormat().resolvedOptions().timeZone,
                    webcast_language: 'en',
                });
                
                const baseUrl = '/api/post/item_list/';
                let url = `${baseUrl}?${params.toString()}`;
                
                // Sign the request
                if (window.byted_acrawler?.frontierSign) {
                    const sig = window.byted_acrawler.frontierSign(url);
                    if (sig['X-Bogus']) {
                        url += '&X-Bogus=' + sig['X-Bogus'];
                    }
                }
                
                const resp = await fetch(url, {
                    credentials: 'include',
                    headers: { 'Accept': 'application/json, text/plain, */*' }
                });
                
                const text = await resp.text();
                let data;
                try { data = JSON.parse(text); } catch(e) { 
                    return {error: 'Not JSON', status: resp.status, body: text.substring(0, 500)}; 
                }
                
                if (data.itemList && data.itemList.length > 0) {
                    return {
                        success: true,
                        count: data.itemList.length,
                        hasMore: data.hasMore,
                        cursor: data.cursor,
                        videos: data.itemList.map(v => ({
                            id: v.id,
                            desc: (v.desc || '').substring(0, 80),
                            views: v.stats?.playCount || 0,
                            likes: v.stats?.diggCount || 0,
                            comments: v.stats?.commentCount || 0,
                            shares: v.stats?.shareCount || 0,
                            created: v.createTime,
                            duration: v.video?.duration || 0,
                        })),
                    };
                }
                
                return {
                    success: false,
                    status: resp.status,
                    statusCode: data.statusCode,
                    statusMsg: data.statusMsg,
                    keys: Object.keys(data),
                };
            } catch(e) {
                return {error: e.message};
            }
        }''', sec_uid)
        
        print(f"  Result: {json.dumps(result, indent=2)[:2000]}")
        
        if result and result.get('success'):
            print(f"\n🎉 SUCCESS! Got {result['count']} videos!")
            for v in result.get('videos', [])[:10]:
                created = v.get('created', 0)
                from datetime import datetime
                date_str = datetime.fromtimestamp(created).strftime('%Y-%m-%d') if created else '?'
                print(f"  📹 {v['id']} | {v['views']:>10,} views | {v['likes']:>8,} likes | {v['duration']:>3}s | {date_str} | {v['desc'][:50]}")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
