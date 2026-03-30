#!/usr/bin/env python3
"""
Use a persistent browser profile to maintain TikTok session state.
First run: creates profile and loads TikTok (needs one manual interaction).
Subsequent runs: reuses cookies and should bypass anti-bot.
"""
import asyncio, json, sys, os, random
from playwright.async_api import async_playwright

USERNAME = sys.argv[1] if len(sys.argv) > 1 else 'charlidamelio'
PROFILE_DIR = os.path.expanduser('~/.tiktok-scraper-profile')

async def main():
    print(f'🎬 Persistent profile approach for @{USERNAME}\n')
    
    async with async_playwright() as p:
        # Use persistent context — stores cookies, localStorage, etc.
        ctx = await p.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=False,
            args=['--disable-blink-features=AutomationControlled'],
            viewport={'width': 1440, 'height': 900},
            locale='en-US',
        )
        
        # Anti-detection
        await ctx.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        video_items = []
        
        async def handle_response(response):
            url = response.url
            if '/api/post/item_list/' in url:
                try:
                    body = await response.text()
                    if body:
                        data = json.loads(body)
                        items = data.get('itemList', [])
                        if items:
                            print(f'  ✅ POST API → {len(items)} videos!')
                            video_items.extend(items)
                except: pass
        
        page.on('response', handle_response)
        
        print('Loading profile...')
        await page.goto(f'https://www.tiktok.com/@{USERNAME}', wait_until='domcontentloaded', timeout=20000)
        await asyncio.sleep(5)
        
        # Check for captcha/login prompt
        title = await page.title()
        print(f'Page title: {title}')
        
        # Check SSR data
        ssr = await page.evaluate('''() => {
            const el = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");
            if (!el) return null;
            try {
                const data = JSON.parse(el.textContent);
                const ud = data.__DEFAULT_SCOPE__?.["webapp.user-detail"];
                if (ud?.userInfo) {
                    return {
                        name: ud.userInfo.user.nickname,
                        followers: ud.userInfo.stats.followerCount,
                        videos: ud.userInfo.stats.videoCount,
                    };
                }
                return { status: ud?.statusCode || 'unknown' };
            } catch(e) { return { error: e.message }; }
        }''')
        print(f'SSR: {ssr}')
        
        # Scroll
        print('\nScrolling to load videos...')
        for i in range(15):
            await page.evaluate('window.scrollBy(0, 500)')
            await asyncio.sleep(random.uniform(1.5, 2.5))
            
            dom_count = await page.evaluate('() => document.querySelectorAll(\'a[href*="/video/"]\').length')
            if dom_count > 0 or video_items:
                print(f'  Scroll {i+1}: DOM={dom_count} links, API={len(video_items)} videos')
        
        await asyncio.sleep(3)
        
        # Get DOM video links
        dom_links = await page.evaluate('''() => {
            const links = new Set();
            document.querySelectorAll('a[href*="/video/"]').forEach(a => links.add(a.href));
            return [...links];
        }''')
        
        print(f'\n{"="*50}')
        print(f'API videos: {len(video_items)}')
        print(f'DOM links: {len(dom_links)}')
        
        if video_items:
            for item in video_items[:5]:
                stats = item.get('stats', {})
                print(f'  📹 {item.get("desc", "")[:50]} | plays={stats.get("playCount", "?"):,}')
            
            with open('scraper/video_persistent_output.json', 'w') as f:
                json.dump(video_items[:30], f, indent=2, ensure_ascii=False)
        
        if dom_links:
            print(f'\nFirst 5 DOM links:')
            for link in dom_links[:5]:
                print(f'  {link}')
        
        await ctx.close()

asyncio.run(main())
