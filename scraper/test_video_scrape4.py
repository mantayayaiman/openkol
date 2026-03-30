#!/usr/bin/env python3
"""Dump full vidList and explore all video data from TikTok profiles."""
import asyncio, json, sys, httpx, re

USERNAME = sys.argv[1] if len(sys.argv) > 1 else 'kingshahx'

async def main():
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        r = await client.get(f'https://www.tiktok.com/@{USERNAME}', timeout=15)
        text = r.text
        
        match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', text, re.DOTALL)
        if not match:
            print('No data found')
            return
        
        data = json.loads(match.group(1))
        scope = data.get('__DEFAULT_SCOPE__', {})
        
        # Full dump of seo.abtest
        seo = scope.get('seo.abtest', {})
        vid_list = seo.get('vidList', [])
        print(f'vidList has {len(vid_list)} items')
        print(f'\nFull vidList dump:')
        print(json.dumps(vid_list, indent=2, ensure_ascii=False)[:3000])
        
        # Also check: is there a SIGI_STATE?
        sigi = re.search(r'<script id="SIGI_STATE"[^>]*>(.*?)</script>', text, re.DOTALL)
        if sigi:
            sigi_data = json.loads(sigi.group(1))
            print(f'\nSIGI_STATE keys: {list(sigi_data.keys())}')
        
        # Check for __NEXT_DATA__
        next_data = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.DOTALL)
        if next_data:
            nd = json.loads(next_data.group(1))
            print(f'\n__NEXT_DATA__ found! keys: {list(nd.keys())}')
        
        # Full dump of webapp.user-detail
        ud = scope.get('webapp.user-detail', {})
        print(f'\nwebapp.user-detail full dump:')
        print(json.dumps(ud, indent=2, ensure_ascii=False)[:2000])
        
        # Now try: fetch videos via the post/item_list API using cookies from this session
        print(f'\n{"="*50}')
        print(f'Trying post API with session cookies...')
        
        if 'userInfo' in ud:
            sec_uid = ud['userInfo']['user'].get('secUid', '')
            
            # Get msToken from cookies
            cookies = dict(r.cookies)
            print(f'Cookies: {list(cookies.keys())}')
            
            api_headers = {
                'User-Agent': headers['User-Agent'],
                'Referer': f'https://www.tiktok.com/@{USERNAME}',
                'Accept': 'application/json',
            }
            
            # Try the post list endpoint
            api_url = f'https://www.tiktok.com/api/post/item_list/?aid=1988&app_language=en&app_name=tiktok_web&count=30&secUid={sec_uid}&cursor=0'
            r2 = await client.get(api_url, headers=api_headers, timeout=15)
            print(f'Post API status: {r2.status_code}')
            # print headers
            
            body = r2.text
            if body:
                try:
                    api_data = json.loads(body)
                    print(f'Post API keys: {list(api_data.keys())}')
                    items = api_data.get('itemList', [])
                    print(f'Items: {len(items)}')
                    for item in items[:3]:
                        print(f'\n  📹 {item.get("desc", "")[:80]}')
                        print(f'     id: {item.get("id")}')
                        print(f'     createTime: {item.get("createTime")}')
                        stats = item.get('stats', {})
                        print(f'     plays: {stats.get("playCount"):,}' if stats.get("playCount") else '')
                        print(f'     likes: {stats.get("diggCount"):,}' if stats.get("diggCount") else '')
                        print(f'     comments: {stats.get("commentCount"):,}' if stats.get("commentCount") else '')
                        print(f'     shares: {stats.get("shareCount"):,}' if stats.get("shareCount") else '')
                        video = item.get('video', {})
                        if video:
                            print(f'     duration: {video.get("duration")}s')
                            print(f'     cover: {video.get("cover", "")[:80]}')
                except json.JSONDecodeError:
                    print(f'Not JSON. Body: {body[:500]}')
            else:
                print('Empty response body')

if __name__ == '__main__':
    asyncio.run(main())
