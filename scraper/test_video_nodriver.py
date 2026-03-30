#!/usr/bin/env python3
"""
Test nodriver (undetectable Chrome) for TikTok video scraping.
nodriver patches Chrome DevTools Protocol detection.
"""
import asyncio, json, sys

USERNAME = sys.argv[1] if len(sys.argv) > 1 else 'khaborinaldo'

async def main():
    import nodriver as uc
    
    print(f'🎬 nodriver (stealth Chrome) test for @{USERNAME}\n')
    
    browser = await uc.start(
        headless=True,
        lang='en-US',
    )
    
    page = await browser.get(f'https://www.tiktok.com/@{USERNAME}')
    
    print('Page loaded. Waiting for content...')
    await asyncio.sleep(5)
    
    # Try to extract __UNIVERSAL_DATA__
    result = await page.evaluate('''
        (() => {
            const el = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");
            if (!el) return { error: "No __UNIVERSAL_DATA__ element" };
            try {
                const data = JSON.parse(el.textContent);
                const scope = data.__DEFAULT_SCOPE__ || {};
                const keys = Object.keys(scope);
                const userDetail = scope["webapp.user-detail"] || {};
                const userPost = scope["webapp.user-post"] || {};
                
                let result = {
                    scopeKeys: keys,
                    hasUserInfo: !!userDetail.userInfo,
                    userPostKeys: Object.keys(userPost),
                };
                
                if (userDetail.userInfo) {
                    result.user = {
                        nickname: userDetail.userInfo.user.nickname,
                        followers: userDetail.userInfo.stats.followerCount,
                        videoCount: userDetail.userInfo.stats.videoCount,
                        secUid: userDetail.userInfo.user.secUid,
                    };
                }
                
                // Check for item list in various scopes
                for (const [key, val] of Object.entries(scope)) {
                    if (typeof val === 'object' && val !== null) {
                        const str = JSON.stringify(val);
                        if (str.includes('"itemList"') || str.includes('"desc"')) {
                            result[key + '_preview'] = str.substring(0, 500);
                        }
                    }
                }
                
                return result;
            } catch (e) {
                return { error: e.message, text: el.textContent.substring(0, 200) };
            }
        })()
    ''')
    
    print(f'Result: {json.dumps(result, indent=2, ensure_ascii=False)[:2000]}')
    
    if result.get('hasUserInfo'):
        print(f'\n✅ Got user data!')
        print(f'   {result["user"]["nickname"]} | {result["user"]["followers"]:,} followers | {result["user"]["videoCount"]} videos')
        
        # Now scroll down to load video grid
        print(f'\nScrolling to load videos...')
        for i in range(5):
            await page.evaluate('window.scrollBy(0, 800)')
            await asyncio.sleep(1)
        
        # Check for video elements in DOM
        videos = await page.evaluate('''
            (() => {
                const results = [];
                
                // Method 1: links with /video/
                document.querySelectorAll('a[href*="/video/"]').forEach(a => {
                    results.push({
                        href: a.href,
                        text: (a.textContent || '').substring(0, 50).trim(),
                    });
                });
                
                // Method 2: data-e2e selectors
                document.querySelectorAll('[data-e2e="user-post-item"]').forEach(el => {
                    const a = el.querySelector('a');
                    results.push({
                        href: a?.href || '',
                        type: 'user-post-item',
                    });
                });
                
                return { count: results.length, items: results.slice(0, 20) };
            })()
        ''')
        
        print(f'\nVideo elements in DOM: {videos["count"]}')
        for v in videos['items'][:10]:
            print(f'  {v}')
        
        # Try to intercept the post API directly
        if videos['count'] == 0:
            print(f'\nNo video elements in DOM. Trying API call...')
            sec_uid = result['user']['secUid']
            
            # Navigate to the API URL in the browser context (should have valid cookies + signatures)
            api_page = await browser.get(
                f'https://www.tiktok.com/api/post/item_list/?aid=1988&count=30&secUid={sec_uid}&cursor=0',
                new_tab=True
            )
            await asyncio.sleep(3)
            
            api_text = await api_page.evaluate('document.body.innerText')
            if api_text:
                try:
                    api_data = json.loads(api_text)
                    items = api_data.get('itemList', [])
                    print(f'  API returned {len(items)} videos!')
                    for item in items[:5]:
                        print(f'    📹 {item.get("desc", "")[:60]} | plays={item.get("stats", {}).get("playCount", "?")}')
                except:
                    print(f'  API response (not JSON): {api_text[:300]}')
    
    browser.stop()
    print('\nDone!')

asyncio.run(main())
