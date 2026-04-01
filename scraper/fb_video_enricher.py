#!/usr/bin/env python3
"""
Facebook Video Enricher — Playwright-based scraper for FB page video stats.
Loads page /videos/ tab and extracts view counts from rendered content.

Strategy:
1. Load https://www.facebook.com/{username}/videos/ in Playwright
2. Parse rendered HTML for video cards with view counts
3. Store in content_samples, update avg_views + engagement_rate

Facebook is the hardest platform — view counts are in localized text (e.g., "1.5J tontonan" in Malay).
Likes/comments are often hidden. We focus on views primarily.

Usage:
  python3 scraper/fb_video_enricher.py                # Single worker
  python3 scraper/fb_video_enricher.py 0 2            # Worker 0 of 2
"""
import asyncio
import sqlite3
import sys
import time
import random
import re
from playwright.async_api import async_playwright

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
BATCH_SIZE = 25

WORKER_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 0
TOTAL_WORKERS = int(sys.argv[2]) if len(sys.argv) > 2 else 1

# View count patterns (multi-locale)
VIEW_PATTERNS = [
    r'([\d,.]+[JKMBjt]*)\s*(?:views?|tontonan|paparan|tayangan|penayangan|lượt xem|ครั้ง|kali ditonton)',
    r'([\d,.]+[JKMBjt]*)\s*(?:plays?|plays)',
]

def parse_count(text):
    """Parse localized count: '1.9J' (Malay juta=million), '1.2M', '456K', '100rb', etc."""
    text = text.strip().replace(',', '.').replace(' ', '')
    multiplier = 1
    for suffix, mult in [('J', 1_000_000), ('jt', 1_000_000), ('juta', 1_000_000),
                         ('M', 1_000_000), ('m', 1_000_000),
                         ('K', 1_000), ('k', 1_000), ('rb', 1_000), ('ribu', 1_000),
                         ('B', 1_000_000_000), ('T', 1_000_000_000_000)]:
        if text.lower().endswith(suffix.lower()):
            text = text[:len(text)-len(suffix)]
            multiplier = mult
            break
    try:
        return int(float(text.replace(',', '.')) * multiplier)
    except:
        return 0


def get_creators_needing_videos():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT pp.id as presence_id, pp.username, pp.creator_id, pp.followers, pp.url
        FROM platform_presences pp
        LEFT JOIN (
            SELECT presence_id, COUNT(*) as sample_count
            FROM content_samples
            GROUP BY presence_id
        ) cs ON cs.presence_id = pp.id
        WHERE pp.platform = 'facebook'
        AND pp.followers >= 1000
        AND (cs.sample_count IS NULL OR cs.sample_count < 3)
        AND pp.creator_id % ? = ?
        ORDER BY pp.followers DESC
    """, (TOTAL_WORKERS, WORKER_ID)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_videos(presence_id, videos):
    conn = sqlite3.connect(DB_PATH)
    inserted = 0

    for v in videos:
        try:
            existing = conn.execute(
                "SELECT 1 FROM content_samples WHERE presence_id=? AND url=?",
                (presence_id, v['url'])
            ).fetchone()
            if existing:
                continue
            conn.execute("""
                INSERT INTO content_samples (presence_id, url, views, likes, comments, shares, posted_at, caption)
                VALUES (?,?,?,?,?,?,?,?)
            """, (presence_id, v['url'], v['views'], v['likes'], v['comments'], v.get('shares', 0),
                  v.get('posted_at', ''), v.get('caption', '')))
            inserted += 1
        except:
            continue

    if inserted > 0:
        result = conn.execute(
            "SELECT AVG(views), COUNT(*), SUM(views), SUM(likes), SUM(comments) "
            "FROM content_samples WHERE presence_id=? AND views > 0",
            (presence_id,)
        ).fetchone()
        if result and result[0]:
            avg_views = int(result[0])
            total_views = result[2] or 0
            total_likes = result[3] or 0
            total_comments = result[4] or 0
            er = round((total_likes + total_comments) / max(total_views, 1) * 100, 2)
            er = min(er, 30.0)
            conn.execute(
                "UPDATE platform_presences SET avg_views=?, recent_videos=?, recent_views=?, engagement_rate=? WHERE id=?",
                (avg_views, result[1], total_views, er, presence_id)
            )

    conn.commit()
    conn.close()
    return inserted


async def scrape_fb_videos(page, username):
    """Load FB page videos tab and extract video data from rendered content."""
    videos = []

    try:
        url = f'https://www.facebook.com/{username}/videos/'
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(4 + random.uniform(0, 2))

        # Dismiss cookie/login popups
        for selector in ['[data-testid="cookie-policy-manage-dialog-accept-button"]',
                         '[aria-label="Close"]', '[aria-label="Decline optional cookies"]']:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible(timeout=1000):
                    await btn.click()
                    await asyncio.sleep(0.5)
            except:
                pass

        # Scroll to load more videos
        for _ in range(3):
            await page.evaluate('window.scrollBy(0, 1500)')
            await asyncio.sleep(1.5)

        # Get all text content and look for video links + view counts
        content = await page.content()

        # Extract video IDs from hrefs
        video_ids = re.findall(r'facebook\.com/(?:[^/]+/)?videos/(\d+)', content)
        video_ids = list(dict.fromkeys(video_ids))[:10]  # Dedupe, max 10

        # Try to extract view counts from nearby text
        # FB renders video cards with view counts as text spans
        all_text = await page.evaluate('''() => {
            const items = [];
            document.querySelectorAll('a[href*="/videos/"]').forEach(a => {
                const card = a.closest('[class]') || a.parentElement;
                if (card) {
                    items.push({
                        href: a.href,
                        text: card.innerText.substring(0, 500)
                    });
                }
            });
            return items;
        }''')

        seen_urls = set()
        for item in all_text:
            href = item.get('href', '')
            text = item.get('text', '')

            # Extract video ID from href
            vid_match = re.search(r'videos/(\d+)', href)
            if not vid_match:
                continue
            vid_id = vid_match.group(1)
            video_url = f'https://www.facebook.com/{username}/videos/{vid_id}/'
            if video_url in seen_urls:
                continue
            seen_urls.add(video_url)

            # Parse view count from card text
            views = 0
            for pat in VIEW_PATTERNS:
                m = re.search(pat, text, re.I)
                if m:
                    views = parse_count(m.group(1))
                    break

            # Parse likes
            likes = 0
            likes_m = re.search(r'([\d,.]+[JKMBjt]*)\s*(?:likes?|suka|thích)', text, re.I)
            if likes_m:
                likes = parse_count(likes_m.group(1))

            # Parse comments
            comments = 0
            comments_m = re.search(r'([\d,.]+[JKMBjt]*)\s*(?:comments?|komen|bình luận)', text, re.I)
            if comments_m:
                comments = parse_count(comments_m.group(1))

            # Extract caption (first line of card text, skip view/like counts)
            caption_lines = [l.strip() for l in text.split('\n') if l.strip() and not re.search(r'views?|tontonan|likes?|suka|comments?|komen|share|ago|hari|jam|menit', l, re.I)]
            caption = caption_lines[0][:200] if caption_lines else ''

            videos.append({
                'url': video_url, 'views': views, 'likes': likes,
                'comments': comments, 'shares': 0, 'posted_at': '', 'caption': caption,
            })

            if len(videos) >= 10:
                break

        # If we found video IDs but no view data from text, still record them
        if not videos and video_ids:
            for vid_id in video_ids[:10]:
                video_url = f'https://www.facebook.com/{username}/videos/{vid_id}/'
                if video_url not in seen_urls:
                    videos.append({
                        'url': video_url, 'views': 0, 'likes': 0,
                        'comments': 0, 'shares': 0, 'posted_at': '', 'caption': '',
                    })

    except Exception:
        pass

    return videos


async def main():
    creators = get_creators_needing_videos()
    total = len(creators)

    print(f'📘 FB VIDEO ENRICHER Worker {WORKER_ID}/{TOTAL_WORKERS}')
    print(f'   Creators to process: {total}')
    print(f'{"="*50}')
    sys.stdout.flush()

    if not creators:
        print('No Facebook creators need video data. Done.')
        return

    start_time = time.time()
    processed = 0
    total_videos = 0
    errors = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 720},
            locale='ms-MY',  # Malay locale to match our audience
        )
        page = await context.new_page()

        for creator in creators:
            presence_id = creator['presence_id']
            username = creator['username']
            followers = creator['followers']

            videos = await scrape_fb_videos(page, username)
            processed += 1

            if videos:
                # Filter out zero-view entries if we have some with views
                with_views = [v for v in videos if v['views'] > 0]
                to_save = with_views if with_views else videos

                inserted = save_videos(presence_id, to_save)
                total_videos += inserted
                avg_views = sum(v['views'] for v in with_views) / len(with_views) if with_views else 0
                print(f'  W{WORKER_ID} ✅ @{username} ({followers:,}): {len(videos)} vids ({len(with_views)} w/ views), avg {avg_views:,.0f}')
                sys.stdout.flush()
            else:
                errors += 1

            if processed % BATCH_SIZE == 0:
                elapsed = (time.time() - start_time) / 3600
                rate = processed / max(elapsed, 0.001)
                eta = (total - processed) / max(rate, 1)

                conn = sqlite3.connect(DB_PATH)
                with_avg = conn.execute("SELECT COUNT(*) FROM platform_presences WHERE avg_views > 0 AND platform='facebook'").fetchone()[0]
                total_fb = conn.execute("SELECT COUNT(*) FROM platform_presences WHERE platform='facebook'").fetchone()[0]
                conn.close()

                print(f'\n  W{WORKER_ID} 📊 [{processed}/{total}] {total_videos} vids | {with_avg}/{total_fb} enriched | {rate:.0f}/hr | ETA {eta:.1f}hr | err:{errors}')
                sys.stdout.flush()

            # FB rate limiting — be cautious
            await asyncio.sleep(random.uniform(4, 8))

            # Rotate context every 50 profiles
            if processed % 50 == 0:
                await context.close()
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1280, 'height': 720},
                    locale='ms-MY',
                )
                page = await context.new_page()

        await browser.close()

    elapsed = (time.time() - start_time) / 3600
    print(f'\nW{WORKER_ID} DONE — {elapsed:.1f}hr | {processed} creators | {total_videos} videos | {errors} errors')


if __name__ == '__main__':
    asyncio.run(main())
