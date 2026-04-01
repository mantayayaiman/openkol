#!/usr/bin/env python3
"""
Crack video scraping: Use Playwright to intercept the actual API calls
TikTok makes when loading a user's video grid.
"""
import asyncio
import json
import sys
from playwright.async_api import async_playwright

USERNAME = sys.argv[1] if len(sys.argv) > 1 else 'soloz_official'

async def main():
    print(f'🎬 Intercepting video API calls for @{USERNAME}\n')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080})
        
        page = await ctx.new_page()
        
        video_data = []
        all_api_calls = []
        
        async def handle_response(response):
            url = response.url
            # Track ALL API calls
            if '/api/' in url or 'item_list' in url or 'post' in url.lower():
                try:
                    body = await response.text()
                    all_api_calls.append({'url': url, 'status': response.status, 'size': len(body)})
                    
                    if body:
                        try:
                            data = json.loads(body)
                            # Check if this has video items
                            if 'itemList' in data:
                                items = data['itemList']
                                print(f'  ✅ Found itemList with {len(items)} videos!')
                                for item in items[:5]:
                                    vid = {
                                        'id': item.get('id'),
                                        'desc': item.get('desc', '')[:80],
                                        'createTime': item.get('createTime'),
                                        'duration': item.get('video', {}).get('duration'),
                                        'cover': item.get('video', {}).get('cover', ''),
                                        'plays': item.get('stats', {}).get('playCount', 0),
                                        'likes': item.get('stats', {}).get('diggCount', 0),
                                        'comments': item.get('stats', {}).get('commentCount', 0),
                                        'shares': item.get('stats', {}).get('shareCount', 0),
                                    }
                                    video_data.append(vid)
                                    print(f'    📹 {vid["desc"][:60]}')
                                    print(f'       plays={vid["plays"]:,} likes={vid["likes"]:,} comments={vid["comments"]:,}')
                            elif 'items' in data:
                                print(f'  Found "items" key with {len(data["items"])} entries')
                        except json.JSONDecodeError:
                            pass
                except:
                    pass
        
        page.on('response', handle_response)
        
        print('Loading profile page...')
        await page.goto(f'https://www.tiktok.com/@{USERNAME}', wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(2)
        
        print('\nScrolling to trigger video load...')
        # Scroll down multiple times to trigger lazy loading
        for i in range(5):
            await page.evaluate('window.scrollBy(0, 800)')
            await asyncio.sleep(1)
        
        print('\nWaiting for any remaining API calls...')
        await asyncio.sleep(3)
        
        print(f'\n{"="*50}')
        print(f'All API calls intercepted ({len(all_api_calls)} total):')
        for call in all_api_calls:
            marker = '📹' if 'item_list' in call['url'] or 'post' in call['url'].lower() else '  '
            print(f'  {marker} [{call["status"]}] {call["url"][:120]} ({call["size"]} bytes)')
        
        print(f'\nVideo data collected: {len(video_data)} videos')
        for v in video_data:
            print(f'  📹 id={v["id"]} | {v["desc"][:50]} | plays={v["plays"]:,} | likes={v["likes"]:,} | dur={v["duration"]}s')
        
        if not video_data:
            print('\n⚠️ No video data intercepted. Trying alternative: evaluate page JS...')
            
            # Try to read the video grid directly from DOM
            videos_from_dom = await page.evaluate('''() => {
                const videos = [];
                // Look for video container elements
                const items = document.querySelectorAll('[data-e2e="user-post-item"]');
                items.forEach(item => {
                    const link = item.querySelector('a');
                    const desc = item.querySelector('[data-e2e="user-post-item-desc"]');
                    const views = item.querySelector('strong');
                    videos.push({
                        href: link?.href || '',
                        desc: desc?.textContent || '',
                        views: views?.textContent || '',
                    });
                });
                
                // Also try the newer selectors
                const items2 = document.querySelectorAll('[class*="DivItemContainerV2"]');
                items2.forEach(item => {
                    const link = item.querySelector('a');
                    videos.push({
                        href: link?.href || '',
                        text: item.textContent?.substring(0, 100) || '',
                    });
                });
                
                // Generic: any link with /video/ in href
                document.querySelectorAll('a[href*="/video/"]').forEach(a => {
                    videos.push({
                        href: a.href,
                        text: a.textContent?.substring(0, 50) || '',
                    });
                });
                
                return videos;
            }''')
            
            print(f'\nVideo links from DOM: {len(videos_from_dom)}')
            for v in videos_from_dom[:10]:
                print(f'  {v}')
            
            # Also try: use page.evaluate to call TikTok's internal JS API
            internal_data = await page.evaluate('''() => {
                // Check if TikTok stores video data in global state
                const win = window;
                const keys = Object.keys(win).filter(k => 
                    k.includes('SIGI') || k.includes('__NEXT') || k.includes('tiktok') || k.includes('webpackChunk')
                );
                
                // Check for React fiber tree data
                const rootEl = document.getElementById('app') || document.getElementById('__next');
                
                return {
                    globalKeys: keys,
                    hasApp: !!document.getElementById('app'),
                    hasNext: !!document.getElementById('__next'),
                    bodyClasses: document.body.className,
                };
            }''')
            print(f'\nInternal state: {internal_data}')
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
