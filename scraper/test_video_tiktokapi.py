#!/usr/bin/env python3
"""Test TikTokApi library for getting user videos."""
import asyncio, json, sys

USERNAME = sys.argv[1] if len(sys.argv) > 1 else 'khaborinaldo'

async def main():
    from TikTokApi import TikTokApi
    
    print(f'🎬 TikTokApi test for @{USERNAME}\n')
    
    async with TikTokApi() as api:
        # Create sessions
        await api.create_sessions(
            ms_tokens=[None],
            num_sessions=1,
            sleep_after=3,
            headless=False,  # non-headless sometimes works better
        )
        
        # Get user info
        user = api.user(USERNAME)
        user_data = await user.info()
        print(f'User: {user_data}')
        
        # Get user videos
        print(f'\nFetching videos...')
        videos = []
        async for video in user.videos(count=10):
            vid = video.as_dict
            videos.append({
                'id': vid.get('id'),
                'desc': vid.get('desc', '')[:80],
                'plays': vid.get('stats', {}).get('playCount', 0),
                'likes': vid.get('stats', {}).get('diggCount', 0),
                'comments': vid.get('stats', {}).get('commentCount', 0),
                'shares': vid.get('stats', {}).get('shareCount', 0),
                'duration': vid.get('video', {}).get('duration', 0),
                'cover': vid.get('video', {}).get('cover', ''),
                'createTime': vid.get('createTime'),
            })
            print(f'  📹 {vid.get("desc", "")[:60]} | plays={vid.get("stats", {}).get("playCount", "?")}')
        
        print(f'\nTotal videos: {len(videos)}')
        if videos:
            print(f'\nFirst video full dump:')
            print(json.dumps(videos[0], indent=2, ensure_ascii=False))

asyncio.run(main())
