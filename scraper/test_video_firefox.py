#!/usr/bin/env python3
"""
Video scraping: Try Firefox + webkit with various stealth approaches.
Also try: fetching individual video pages via httpx (bypass video list API).
"""
import asyncio, json, sys, httpx, re

USERNAME = sys.argv[1] if len(sys.argv) > 1 else 'khaborinaldo'

async def approach_httpx_video_pages(username):
    """
    Strategy: Instead of getting the video LIST, 
    get individual video pages directly.
    
    Step 1: Get the user page via httpx to find video IDs (from seo.abtest.vidList or links)
    Step 2: Use oEmbed for each video to get metadata
    Step 3: Fetch individual video pages for full stats
    """
    print(f'APPROACH: Individual video pages via httpx + oEmbed\n')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
    }
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, http2=True) as client:
        # Step 1: Get profile page
        r = await client.get(f'https://www.tiktok.com/@{username}', timeout=15)
        text = r.text
        
        match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', text, re.DOTALL)
        if not match:
            print('  No __UNIVERSAL_DATA__ found')
            return
        
        data = json.loads(match.group(1))
        scope = data.get('__DEFAULT_SCOPE__', {})
        ud = scope.get('webapp.user-detail', {})
        
        if 'userInfo' not in ud:
            print(f'  No userInfo! Keys: {list(ud.keys())}')
            print(f'  statusCode: {ud.get("statusCode")}')
            
            # Try with http2 enabled explicitly
            r2 = await client.get(f'https://www.tiktok.com/@{username}', timeout=15, 
                                   headers={**headers, 'Sec-Fetch-Dest': 'document', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'none', 'Sec-Fetch-User': '?1', 'Upgrade-Insecure-Requests': '1'})
            text2 = r2.text
            match2 = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', text2, re.DOTALL)
            if match2:
                data2 = json.loads(match2.group(1))
                ud2 = data2.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {})
                if 'userInfo' in ud2:
                    print(f'  ✅ Got userInfo with Sec-Fetch headers!')
                    ud = ud2
                else:
                    print(f'  Still no userInfo: {list(ud2.keys())}')
                    return
            else:
                return
        
        user = ud['userInfo']['user']
        stats = ud['userInfo']['stats']
        sec_uid = user.get('secUid', '')
        print(f'  ✅ User: {user.get("nickname")} (@{user.get("uniqueId")})')
        print(f'     Followers: {stats.get("followerCount"):,}')
        print(f'     Videos: {stats.get("videoCount")}')
        print(f'     Region: {user.get("region")}')
        
        # Step 2: Find video IDs from page
        video_ids = list(set(re.findall(r'/video/(\d{18,20})', text)))
        
        # Also check vidList
        seo = scope.get('seo.abtest', {})
        for v in seo.get('vidList', []):
            if isinstance(v, str) and v.isdigit():
                video_ids.append(v)
        video_ids = list(set(video_ids))
        print(f'\n  Video IDs from page: {len(video_ids)}')
        
        if not video_ids:
            # Try to construct video URLs by scraping the page for data-src or cover images
            # that contain video IDs
            possible_ids = re.findall(r'(\d{19,20})', text)
            # Filter: TikTok video IDs are typically 19 digits
            video_ids = [vid for vid in set(possible_ids) if len(vid) >= 19][:20]
            print(f'  Found {len(video_ids)} potential video IDs from page content')
        
        # Step 3: Get video details via oEmbed (fast, reliable, no auth needed)
        videos = []
        for vid_id in video_ids[:20]:
            try:
                oembed_url = f'https://www.tiktok.com/oembed?url=https://www.tiktok.com/@{username}/video/{vid_id}'
                r3 = await client.get(oembed_url, timeout=10)
                if r3.status_code == 200:
                    oembed = r3.json()
                    videos.append({
                        'id': vid_id,
                        'title': oembed.get('title', ''),
                        'thumbnail': oembed.get('thumbnail_url', ''),
                        'thumbnail_width': oembed.get('thumbnail_width'),
                        'thumbnail_height': oembed.get('thumbnail_height'),
                        'author': oembed.get('author_name', ''),
                    })
                    print(f'    📹 {oembed.get("title", "")[:60]}')
            except Exception as e:
                print(f'    Error for {vid_id}: {e}')
        
        # Step 4: For richer stats, fetch individual video pages
        print(f'\n  Fetching video pages for stats...')
        for vid in videos[:5]:
            try:
                r4 = await client.get(f'https://www.tiktok.com/@{username}/video/{vid["id"]}', timeout=15)
                match4 = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', r4.text, re.DOTALL)
                if match4:
                    vdata = json.loads(match4.group(1))
                    # Try both possible scope keys
                    for key in ['webapp.video-detail', 'webapp.video.detail']:
                        detail = vdata.get('__DEFAULT_SCOPE__', {}).get(key, {})
                        if detail:
                            item = detail.get('itemInfo', {}).get('itemStruct', {})
                            if item:
                                stats = item.get('stats', {})
                                video = item.get('video', {})
                                vid.update({
                                    'desc': item.get('desc', ''),
                                    'createTime': item.get('createTime'),
                                    'plays': stats.get('playCount', 0),
                                    'likes': stats.get('diggCount', 0),
                                    'comments': stats.get('commentCount', 0),
                                    'shares': stats.get('shareCount', 0),
                                    'duration': video.get('duration', 0),
                                    'cover': video.get('cover', ''),
                                })
                                print(f'    ✅ {vid["id"]}: plays={vid["plays"]:,} likes={vid["likes"]:,} dur={vid["duration"]}s')
                                break
                            else:
                                print(f'    {key} has no itemStruct. Keys: {list(detail.keys())[:5]}')
                    else:
                        # Check what scopes exist
                        scopes = list(vdata.get('__DEFAULT_SCOPE__', {}).keys())
                        video_scopes = [s for s in scopes if 'video' in s.lower() or 'detail' in s.lower()]
                        print(f'    No video-detail scope. Available: {video_scopes}')
            except Exception as e:
                print(f'    Error fetching {vid["id"]}: {e}')
        
        print(f'\n{"="*50}')
        print(f'Final results: {len(videos)} videos')
        for v in videos[:10]:
            plays = v.get('plays', '?')
            likes = v.get('likes', '?')
            dur = v.get('duration', '?')
            print(f'  📹 {v.get("desc", v.get("title", ""))[:60]}')
            if isinstance(plays, int):
                print(f'     plays={plays:,} likes={likes:,} dur={dur}s')
            print(f'     thumbnail: {v.get("thumbnail", "")[:60]}')
        
        return videos

async def main():
    print(f'🎬 Video scraping deep dive for @{USERNAME}\n')
    await approach_httpx_video_pages(USERNAME)

asyncio.run(main())
