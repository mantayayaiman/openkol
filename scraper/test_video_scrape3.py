#!/usr/bin/env python3
"""
Deep dive: Mobile web UA + httpx — extract video list from TikTok profiles.
"""
import asyncio, json, sys, httpx, re

USERNAME = sys.argv[1] if len(sys.argv) > 1 else 'soloz'

async def main():
    print(f'🎬 Deep dive on @{USERNAME} video data\n')
    
    # Approach A: Mobile web user-agent with httpx (NO browser needed)
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        r = await client.get(f'https://www.tiktok.com/@{USERNAME}', timeout=15)
        print(f'Status: {r.status_code}')
        
        text = r.text
        
        match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', text, re.DOTALL)
        if not match:
            print('❌ No __UNIVERSAL_DATA__ found')
            return
        
        data = json.loads(match.group(1))
        scope = data.get('__DEFAULT_SCOPE__', {})
        
        # Print ALL scope keys and sizes
        print(f'\nAll scopes:')
        for k, v in scope.items():
            print(f'  {k}: {len(json.dumps(v))} bytes')
        
        # Check user-detail
        ud = scope.get('webapp.user-detail', {})
        if 'userInfo' in ud:
            user = ud['userInfo']['user']
            stats = ud['userInfo']['stats']
            print(f'\n✅ User: {user.get("nickname")} (@{user.get("uniqueId")})')
            print(f'   Followers: {stats.get("followerCount"):,}')
            print(f'   Following: {stats.get("followingCount"):,}')
            print(f'   Likes: {stats.get("heartCount"):,}')
            print(f'   Videos: {stats.get("videoCount"):,}')
            print(f'   Language: {user.get("language")}')
            print(f'   SecUid: {user.get("secUid", "")[:40]}...')
        
        # Check seo.abtest for vidList
        seo = scope.get('seo.abtest', {})
        if seo:
            print(f'\nseo.abtest keys: {list(seo.keys())}')
            vid_list = seo.get('vidList', [])
            if vid_list:
                print(f'\n🎬 vidList: {len(vid_list)} videos!')
                for v in vid_list:
                    if isinstance(v, dict):
                        print(f'  Video keys: {list(v.keys())[:20]}')
                        print(f'  desc: {v.get("desc", "")[:100]}')
                        print(f'  id: {v.get("id")}')
                        stats = v.get('stats', v.get('statsV2', {}))
                        print(f'  stats: {stats}')
                        video = v.get('video', {})
                        if video:
                            print(f'  video.duration: {video.get("duration")}s')
                            print(f'  video.cover: {video.get("cover", "")[:100]}')
                            print(f'  video.playAddr: {str(video.get("playAddr", ""))[:100]}')
                        print()
        
        # Check ALL scope data for anything video-related
        print(f'\n🔍 Scanning all scopes for video/item data...')
        for scope_key, scope_val in scope.items():
            if not isinstance(scope_val, dict):
                continue
            scope_str = json.dumps(scope_val)
            if '"desc"' in scope_str and ('"video"' in scope_str or '"playAddr"' in scope_str):
                print(f'  📹 {scope_key} contains video-like data!')
                # Try to find the video list
                def find_video_lists(obj, path=''):
                    if isinstance(obj, list):
                        for item in obj:
                            if isinstance(item, dict) and ('desc' in item or 'video' in item):
                                return path, obj
                    elif isinstance(obj, dict):
                        for k, v in obj.items():
                            result = find_video_lists(v, f'{path}.{k}')
                            if result:
                                return result
                    return None
                
                result = find_video_lists(scope_val)
                if result:
                    path, items = result
                    print(f'  Found at {path}: {len(items)} items')
    
    # Approach B: Try with desktop UA but different Accept header  
    print(f'\n{"="*50}')
    print(f'Approach B: Desktop UA with cookies')
    headers2 = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    async with httpx.AsyncClient(headers=headers2, follow_redirects=True) as client:
        r = await client.get(f'https://www.tiktok.com/@{USERNAME}', timeout=15)
        text = r.text
        
        match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', text, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            scope = data.get('__DEFAULT_SCOPE__', {})
            ud = scope.get('webapp.user-detail', {})
            seo = scope.get('seo.abtest', {})
            
            has_user = 'userInfo' in ud
            vid_list = seo.get('vidList', [])
            
            print(f'  Has userInfo: {has_user}')
            print(f'  vidList count: {len(vid_list)}')
            
            if vid_list:
                for v in vid_list[:2]:
                    if isinstance(v, dict):
                        print(f'  Video: {v.get("desc", "")[:80]} | stats: {v.get("stats", {})}')

if __name__ == '__main__':
    asyncio.run(main())
