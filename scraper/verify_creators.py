import asyncio
import json
from playwright.async_api import async_playwright

CREATORS = [
    {"id": 188, "username": "codyhong", "db_name": "Cody Hong", "db_followers": 2500000, "db_following": 198, "db_likes": 28000000},
    {"id": 92, "username": "blackink_th", "db_name": "Blackink", "db_followers": 5800000, "db_following": 290, "db_likes": 78000000},
    {"id": 172, "username": "zermattneo", "db_name": "Zermatt Neo", "db_followers": 2100000, "db_following": 210, "db_likes": 22000000},
    {"id": 249, "username": "jack97", "db_name": "Jack (J97)", "db_followers": 8200000, "db_following": 198, "db_likes": 95000000},
    {"id": 15, "username": "zommarie", "db_name": "Zom Marie", "db_followers": 1500000, "db_following": 280, "db_likes": 22000000},
    {"id": 240, "username": "lelepons_ph", "db_name": "Lele Pons PH", "db_followers": 2200000, "db_following": 178, "db_likes": 22000000},
    {"id": 18, "username": "mimiyuuuh", "db_name": "Mimiyuuuh", "db_followers": 7200000, "db_following": 380, "db_likes": 145000000},
    {"id": 122, "username": "raizacontawi", "db_name": "Raiza Contawi", "db_followers": 4200000, "db_following": 310, "db_likes": 48000000},
    {"id": 13, "username": "kristtps", "db_name": "Krist Perawat", "db_followers": 3400000, "db_following": 310, "db_likes": 55000000},
    {"id": 232, "username": "urboytj", "db_name": "UrboyTJ", "db_followers": 2800000, "db_following": 198, "db_likes": 28000000},
]

async def verify_profile(page, username):
    try:
        await page.goto(f'https://www.tiktok.com/@{username}', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        data = await page.evaluate('''() => {
            const el = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");
            return el ? el.textContent : null;
        }''')
        
        if data:
            parsed = json.loads(data)
            ds = parsed.get('__DEFAULT_SCOPE__', {})
            ud = ds.get('webapp.user-detail', {})
            if 'userInfo' in ud:
                u = ud['userInfo']['user']
                s = ud['userInfo']['stats']
                return {
                    'username': username,
                    'name': u.get('nickname'),
                    'followers': s.get('followerCount', 0),
                    'following': s.get('followingCount', 0),
                    'likes': s.get('heartCount', 0),
                    'videos': s.get('videoCount', 0),
                    'verified': u.get('verified', False),
                }
            # Check if user not found
            status_code = ud.get('statusCode', 0)
            if status_code == 10221:
                return {'username': username, 'error': 'USER_NOT_FOUND'}
        
        # Try alternate: check page title for "not found"
        title = await page.title()
        if 'not found' in title.lower() or "couldn't find" in title.lower():
            return {'username': username, 'error': 'USER_NOT_FOUND'}
        
        return {'username': username, 'error': 'PARSE_FAILED'}
    except Exception as e:
        return {'username': username, 'error': str(e)}

async def main():
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = await ctx.new_page()
        
        for i, creator in enumerate(CREATORS):
            print(f"[{i+1}/10] Verifying @{creator['username']}...", flush=True)
            result = await verify_profile(page, creator['username'])
            result['db'] = creator
            results.append(result)
            print(f"  Result: {json.dumps(result, default=str)}", flush=True)
            if i < len(CREATORS) - 1:
                await asyncio.sleep(4)
        
        await browser.close()
    
    # Output as JSON for processing
    print("\n===RESULTS_JSON===")
    print(json.dumps(results, indent=2, default=str))

asyncio.run(main())
