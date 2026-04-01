#!/usr/bin/env python3
"""
THE CRACK: Mobile UA + httpx gets user data. 
Now extend it to get video data via individual video page scraping.
"""
import asyncio
import json
import sys
import httpx
import re

USERNAME = sys.argv[1] if len(sys.argv) > 1 else 'khaborinaldo'

async def get_user_info(client, username):
    """Get user info using mobile UA."""
    r = await client.get(f'https://www.tiktok.com/@{username}', timeout=15)
    text = r.text
    
    match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', text, re.DOTALL)
    if not match:
        return None, None
    
    data = json.loads(match.group(1))
    scope = data.get('__DEFAULT_SCOPE__', {})
    ud = scope.get('webapp.user-detail', {})
    
    if 'userInfo' not in ud:
        return None, None
    
    return ud['userInfo'], text

async def get_video_stats(client, username, video_id):
    """Get video stats from individual video page."""
    try:
        r = await client.get(f'https://www.tiktok.com/@{username}/video/{video_id}', timeout=15)
        text = r.text
        
        match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', text, re.DOTALL)
        if not match:
            return None
        
        data = json.loads(match.group(1))
        scope = data.get('__DEFAULT_SCOPE__', {})
        
        # Try all possible video detail scope keys
        for key in ['webapp.video-detail', 'webapp.video.detail', 'webapp.videoDetail']:
            detail = scope.get(key, {})
            if detail and 'itemInfo' in detail:
                item = detail['itemInfo'].get('itemStruct', {})
                if item:
                    stats = item.get('stats', {})
                    video = item.get('video', {})
                    return {
                        'id': video_id,
                        'desc': item.get('desc', ''),
                        'createTime': item.get('createTime'),
                        'plays': stats.get('playCount', 0),
                        'likes': stats.get('diggCount', 0),
                        'comments': stats.get('commentCount', 0),
                        'shares': stats.get('shareCount', 0),
                        'duration': video.get('duration', 0),
                        'cover': video.get('cover', ''),
                        'dynamicCover': video.get('dynamicCover', ''),
                    }
        
        # Debug: what scopes exist?
        video_scopes = [k for k in scope.keys() if 'video' in k.lower()]
        print(f'    ⚠️ No video-detail for {video_id}. Video scopes: {video_scopes}')
        for vs in video_scopes:
            print(f'       {vs}: {list(scope[vs].keys())[:5]}')
        
        return None
    except Exception as e:
        print(f'    ❌ Error fetching video {video_id}: {e}')
        return None

async def get_video_oembed(client, username, video_id):
    """Get basic video info from oEmbed."""
    try:
        r = await client.get(
            f'https://www.tiktok.com/oembed?url=https://www.tiktok.com/@{username}/video/{video_id}',
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            return {
                'id': video_id,
                'title': data.get('title', ''),
                'thumbnail': data.get('thumbnail_url', ''),
            }
    except:
        pass
    return None

async def main():
    print(f'🎬 Video crack for @{USERNAME}\n')
    
    # Mobile UA client
    mobile_headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    # Desktop UA client  
    desktop_headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
    }
    
    async with httpx.AsyncClient(headers=mobile_headers, follow_redirects=True) as mobile_client:
        # Step 1: Get user info
        user_info, page_text = await get_user_info(mobile_client, USERNAME)
        if not user_info:
            print('❌ Failed to get user info')
            
            # Try desktop
            async with httpx.AsyncClient(headers=desktop_headers, follow_redirects=True) as desktop_client:
                user_info, page_text = await get_user_info(desktop_client, USERNAME)
                if not user_info:
                    print('❌ Desktop also failed')
                    return
        
        user = user_info['user']
        stats = user_info['stats']
        print(f'✅ User: {user.get("nickname")} (@{user.get("uniqueId")})')
        print(f'   Followers: {stats.get("followerCount"):,}')
        print(f'   Videos: {stats.get("videoCount")}')
        print(f'   Region: {user.get("region")}')
        
        # Step 2: Find video IDs
        # From page links
        video_ids = list(set(re.findall(r'/video/(\d{18,20})', page_text or '')))
        
        # From vidList  
        match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', page_text, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            seo = data.get('__DEFAULT_SCOPE__', {}).get('seo.abtest', {})
            for v in seo.get('vidList', []):
                if isinstance(v, str):
                    video_ids.append(v)
        
        # From 19-digit numbers in page 
        if not video_ids:
            possible = re.findall(r'"(\d{19})"', page_text or '')
            video_ids = list(set(possible))[:20]
        
        print(f'\n📋 Found {len(video_ids)} video IDs: {video_ids[:5]}')
        
        if not video_ids:
            print('\n⚠️ No video IDs found in profile page. TikTok may not include them in SSR.')
            print('   Trying oEmbed with constructed video IDs...')
            return
        
        # Step 3: Get video details
        print('\n🔍 Fetching video details...')
        videos = []
        
        for i, vid_id in enumerate(video_ids[:10]):
            # Try oEmbed first (faster, more reliable)
            oembed = await get_video_oembed(mobile_client, USERNAME, vid_id)
            if oembed:
                print(f'  📹 oEmbed: {oembed["title"][:60]}')
            
            # Then try full page for stats
            await asyncio.sleep(0.5)  # Rate limit
            full = await get_video_stats(mobile_client, USERNAME, vid_id)
            if full:
                if oembed:
                    full['thumbnail'] = oembed.get('thumbnail', '')
                videos.append(full)
                print(f'  ✅ {full["desc"][:50]} | plays={full["plays"]:,} likes={full["likes"]:,} dur={full["duration"]}s')
            elif oembed:
                videos.append(oembed)
        
        # Summary
        print(f'\n{"="*50}')
        print(f'RESULTS: {len(videos)} videos with data')
        
        has_stats = sum(1 for v in videos if 'plays' in v)
        print(f'  With full stats: {has_stats}')
        print(f'  oEmbed only: {len(videos) - has_stats}')
        
        for v in videos:
            if 'plays' in v:
                print(f'\n  📹 {v["desc"][:60]}')
                print(f'     id={v["id"]} | plays={v["plays"]:,} | likes={v["likes"]:,} | comments={v["comments"]:,} | dur={v["duration"]}s')
                print(f'     cover: {v["cover"][:60]}')
            else:
                print(f'\n  📹 {v.get("title", "")[:60]} (oEmbed only)')
                print(f'     id={v["id"]} | thumbnail: {v.get("thumbnail", "")[:60]}')
        
        if videos:
            with open('scraper/video_crack_output.json', 'w') as f:
                json.dump(videos, f, indent=2, ensure_ascii=False)
            print('\n💾 Saved to scraper/video_crack_output.json')

asyncio.run(main())
