#!/usr/bin/env python3
"""
Video Content Scraper — Scrapes recent video performance data for existing creators.
Runs as a background enrichment process. For each creator in DB:
1. Visit their TikTok profile
2. Extract video URLs from the page
3. Visit each video to get views, likes, comments, shares
4. Store in content_samples table

Strategy: Use TikTok's mobile web which shows video thumbnails with view counts
on hover/tap. The mobile profile page is lighter and shows video previews.

Run: PLAYWRIGHT_BROWSERS_PATH=0 python3 -u scraper/video_scraper.py 2>&1 | tee scraper/video_scraper.log
"""
import asyncio, json, sqlite3, random, re, sys, time
from datetime import datetime, timezone
from playwright.async_api import async_playwright

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
PROGRESS_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/video_progress.json'
NUM_WORKERS = 2
DELAY = 3.0
VIDEOS_PER_CREATOR = 6

MOBILE_UAS = [
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
]

_db_lock = asyncio.Lock()

def get_creators_needing_videos():
    """Get TikTok creators who don't have content samples yet."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT pp.id, pp.username, pp.creator_id, pp.followers
        FROM platform_presences pp
        LEFT JOIN content_samples cs ON cs.presence_id = pp.id
        WHERE pp.platform = 'tiktok' 
        AND pp.followers >= 5000
        AND cs.id IS NULL
        ORDER BY pp.followers DESC
    """).fetchall()
    conn.close()
    return rows

async def insert_video(presence_id, video):
    async with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        try:
            # Check if already exists
            existing = conn.execute("SELECT 1 FROM content_samples WHERE presence_id=? AND url=?",
                                   (presence_id, video.get('url', ''))).fetchone()
            if existing:
                return False
            conn.execute("""
                INSERT INTO content_samples (presence_id, url, views, likes, comments, shares, posted_at, caption)
                VALUES (?,?,?,?,?,?,?,?)
            """, (presence_id, video.get('url',''), video.get('views',0), video.get('likes',0),
                  video.get('comments',0), video.get('shares',0), video.get('posted_at',''), video.get('caption','')))
            conn.commit()
            return True
        except:
            conn.rollback()
            return False
        finally:
            conn.close()

async def update_avg_views(presence_id):
    """Update the avg_views field from content_samples."""
    async with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        try:
            result = conn.execute("SELECT AVG(views) FROM content_samples WHERE presence_id=? AND views > 0",
                                 (presence_id,)).fetchone()
            if result and result[0]:
                conn.execute("UPDATE platform_presences SET avg_views=? WHERE id=?",
                            (int(result[0]), presence_id))
                conn.commit()
        except:
            pass
        finally:
            conn.close()

async def scrape_creator_videos(page, username):
    """Visit a TikTok profile, find video URLs, then scrape each video."""
    videos = []
    
    try:
        # Step 1: Visit profile to find video URLs
        await page.goto(f'https://www.tiktok.com/@{username}', wait_until='networkidle', timeout=20000)
        await asyncio.sleep(2)
        
        # Scroll to load video grid
        for _ in range(3):
            await page.evaluate('window.scrollBy(0, 800)')
            await asyncio.sleep(1)
        
        # Extract video URLs from page
        content = await page.content()
        video_ids = re.findall(r'/video/(\d{19,20})', content)
        video_ids = list(dict.fromkeys(video_ids))[:VIDEOS_PER_CREATOR]  # Dedupe, limit
        
        if not video_ids:
            # Try extracting from rehydration data
            match = re.search(r'__UNIVERSAL_DATA_FOR_REHYDRATION__[^>]*>(.+?)</script>', content, re.DOTALL)
            if match:
                vid_ids = re.findall(r'"id":"(\d{19,20})"', match.group(1))
                video_ids = list(dict.fromkeys(vid_ids))[:VIDEOS_PER_CREATOR]
        
        if not video_ids:
            return []
        
        # Step 2: Visit each video page to get stats
        for vid_id in video_ids:
            try:
                video_url = f'https://www.tiktok.com/@{username}/video/{vid_id}'
                await page.goto(video_url, wait_until='domcontentloaded', timeout=15000)
                await asyncio.sleep(1.5)
                
                data = await page.evaluate('() => { const el = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__"); return el ? el.textContent : null; }')
                
                if data:
                    parsed = json.loads(data)
                    vd = parsed.get('__DEFAULT_SCOPE__', {}).get('webapp.video-detail', {})
                    
                    if 'itemInfo' in vd:
                        item = vd['itemInfo']['itemStruct']
                        stats = item.get('stats', {})
                        create_time = item.get('createTime', 0)
                        posted_at = ''
                        if create_time:
                            posted_at = datetime.fromtimestamp(int(create_time), tz=timezone.utc).strftime('%Y-%m-%d')
                        
                        videos.append({
                            'url': video_url,
                            'views': stats.get('playCount', 0),
                            'likes': stats.get('diggCount', 0),
                            'comments': stats.get('commentCount', 0),
                            'shares': stats.get('shareCount', 0),
                            'posted_at': posted_at,
                            'caption': (item.get('desc', '') or '')[:200],
                        })
                
                await asyncio.sleep(random.uniform(1.5, 3))
            except:
                continue
        
    except:
        pass
    
    return videos

class VideoScraper:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.scraped = 0
        self.videos_inserted = 0
        self.start_time = time.time()
        self.running = True

    async def make_ctx(self, browser):
        ua = random.choice(MOBILE_UAS)
        return await browser.new_context(
            user_agent=ua,
            viewport={'width': 390, 'height': 844},
            is_mobile=True,
            has_touch=True,
        )

    async def worker(self, wid, browser):
        ctx = await self.make_ctx(browser)
        cc = 0
        
        while self.running:
            try:
                presence_id, username, creator_id, followers = await asyncio.wait_for(self.queue.get(), timeout=300)
            except asyncio.TimeoutError:
                break
            
            cc += 1
            if cc >= 20:
                await ctx.close()
                ctx = await self.make_ctx(browser)
                cc = 0
            
            page = await ctx.new_page()
            videos = await scrape_creator_videos(page, username)
            await page.close()
            self.scraped += 1
            
            for v in videos:
                inserted = await insert_video(presence_id, v)
                if inserted:
                    self.videos_inserted += 1
            
            if videos:
                await update_avg_views(presence_id)
                print(f'  ✅ @{username} ({followers:,} followers): {len(videos)} videos scraped')
                for v in videos[:3]:
                    print(f'      {v["posted_at"]}: {v["views"]:>10,} views | {v["likes"]:>8,} likes | {v["caption"][:40]}')
            
            if self.scraped % 10 == 0:
                elapsed = (time.time() - self.start_time) / 3600
                rate = self.scraped / max(elapsed, 0.001)
                conn = sqlite3.connect(DB_PATH)
                total_samples = conn.execute("SELECT COUNT(*) FROM content_samples").fetchone()[0]
                conn.close()
                print(f'  📊 Video scraper: {self.scraped} creators done | {total_samples} total samples | {self.videos_inserted} new | {rate:.0f} creators/hr')
                sys.stdout.flush()
                with open(PROGRESS_PATH, 'w') as f:
                    json.dump({'ts': datetime.now(timezone.utc).isoformat(), 'creators_done': self.scraped,
                               'videos': self.videos_inserted, 'total_samples': total_samples,
                               'rate': round(rate, 1)}, f)
            
            await asyncio.sleep(random.uniform(DELAY, DELAY + 2))
        
        await ctx.close()

    async def run(self):
        creators = get_creators_needing_videos()
        print(f'🎬 VIDEO SCRAPER')
        print(f'   Creators needing videos: {len(creators)}')
        print(f'   Workers: {NUM_WORKERS}')
        print(f'{"="*50}')
        sys.stdout.flush()
        
        if not creators:
            print('No creators need video data. Done.')
            return
        
        # Queue up creators (prioritize by followers)
        for c in creators:
            self.queue.put_nowait(c)
        
        async with async_playwright() as p:
            browsers = [await p.chromium.launch(headless=True) for _ in range(NUM_WORKERS)]
            print(f'  {NUM_WORKERS} browsers launched')
            
            tasks = [asyncio.create_task(self.worker(i, browsers[i])) for i in range(NUM_WORKERS)]
            
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except KeyboardInterrupt:
                self.running = False
            
            for b in browsers:
                await b.close()
        
        conn = sqlite3.connect(DB_PATH)
        total = conn.execute("SELECT COUNT(*) FROM content_samples").fetchone()[0]
        conn.close()
        elapsed = (time.time() - self.start_time) / 3600
        print(f'\n{"="*50}')
        print(f'VIDEO SCRAPER DONE — {elapsed:.1f}hr')
        print(f'Creators processed: {self.scraped}')
        print(f'Videos inserted: {self.videos_inserted}')
        print(f'Total in content_samples: {total}')
        sys.stdout.flush()

if __name__ == '__main__':
    asyncio.run(VideoScraper().run())
