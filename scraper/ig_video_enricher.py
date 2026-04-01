#!/usr/bin/env python3
"""
Instagram Video Enricher — Playwright-based scraper for IG video stats.
Loads profile pages and intercepts GraphQL API responses to get video data.

Strategy:
1. Load https://www.instagram.com/{username}/ in Playwright
2. Intercept XHR responses containing media data (graphql/query)
3. Extract video_view_count, edge_liked_by, edge_media_to_comment
4. Store in content_samples, update avg_views + engagement_rate

Usage:
  python3 scraper/ig_video_enricher.py                # Single worker
  python3 scraper/ig_video_enricher.py 0 2            # Worker 0 of 2
"""
import asyncio
import json
import sqlite3
import sys
import time
import random
import re
from datetime import datetime, timezone
from playwright.async_api import async_playwright

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
BATCH_SIZE = 25

WORKER_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 0
TOTAL_WORKERS = int(sys.argv[2]) if len(sys.argv) > 2 else 1


def get_creators_needing_videos():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT pp.id as presence_id, pp.username, pp.creator_id, pp.followers
        FROM platform_presences pp
        LEFT JOIN (
            SELECT presence_id, COUNT(*) as sample_count
            FROM content_samples
            GROUP BY presence_id
        ) cs ON cs.presence_id = pp.id
        WHERE pp.platform = 'instagram'
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


async def scrape_ig_profile(page, username):
    """Load IG profile and extract media data from page source / intercepted responses."""
    media_data = []

    async def handle_response(response):
        """Intercept graphql responses containing media data."""
        try:
            url = response.url
            if 'graphql' in url or 'api/v1/users' in url or 'web_profile_info' in url:
                if response.status == 200:
                    try:
                        body = await response.json()
                        extract_media_from_json(body, media_data, username)
                    except:
                        pass
        except:
            pass

    page.on('response', handle_response)

    try:
        await page.goto(f'https://www.instagram.com/{username}/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3 + random.uniform(0, 2))

        # Also try to extract from page source (shared_data / additional_data)
        html = await page.content()
        extract_media_from_html(html, media_data, username)

        # Scroll down to trigger lazy loading of more posts
        await page.evaluate('window.scrollBy(0, 1000)')
        await asyncio.sleep(2)

    except Exception:
        pass
    finally:
        page.remove_listener('response', handle_response)

    return media_data[:10]


def extract_media_from_json(data, media_data, username):
    """Recursively extract media nodes from JSON response."""
    if isinstance(data, dict):
        # Check for edge_owner_to_timeline_media
        if 'edge_owner_to_timeline_media' in data:
            edges = data['edge_owner_to_timeline_media'].get('edges', [])
            for edge in edges:
                node = edge.get('node', {})
                process_media_node(node, media_data, username)
        # Check for items array (v1 API)
        if 'items' in data and isinstance(data['items'], list):
            for item in data['items']:
                process_media_item_v1(item, media_data, username)
        # Recurse
        for v in data.values():
            if isinstance(v, (dict, list)):
                extract_media_from_json(v, media_data, username)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                extract_media_from_json(item, media_data, username)


def process_media_node(node, media_data, username):
    """Process a GraphQL media node."""
    if not node.get('shortcode'):
        return
    shortcode = node['shortcode']
    url = f'https://www.instagram.com/p/{shortcode}/'

    # Skip if already collected
    if any(m['url'] == url for m in media_data):
        return

    is_video = node.get('is_video', False)
    views = node.get('video_view_count', 0) or 0
    likes = (node.get('edge_liked_by') or node.get('edge_media_preview_like') or {}).get('count', 0) or 0
    comments = (node.get('edge_media_to_comment') or node.get('edge_media_preview_comment') or {}).get('count', 0) or 0
    timestamp = node.get('taken_at_timestamp', 0)

    caption_edges = (node.get('edge_media_to_caption') or {}).get('edges', [])
    caption = caption_edges[0].get('node', {}).get('text', '')[:200] if caption_edges else ''

    posted_at = ''
    if timestamp:
        posted_at = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime('%Y-%m-%d')

    # For images, use likes as proxy for "views" (IG doesn't show image views)
    if not is_video and views == 0:
        views = likes * 10  # Rough estimate: likes are ~10% of impressions

    media_data.append({
        'url': url, 'views': views, 'likes': likes, 'comments': comments,
        'shares': 0, 'posted_at': posted_at, 'caption': caption,
    })


def process_media_item_v1(item, media_data, username):
    """Process a v1 API media item."""
    code = item.get('code') or item.get('shortcode')
    if not code:
        return
    url = f'https://www.instagram.com/p/{code}/'
    if any(m['url'] == url for m in media_data):
        return

    views = item.get('play_count') or item.get('video_view_count') or 0
    likes = item.get('like_count', 0) or 0
    comments = item.get('comment_count', 0) or 0
    timestamp = item.get('taken_at', 0)

    caption_obj = item.get('caption') or {}
    caption = (caption_obj.get('text', '') if isinstance(caption_obj, dict) else str(caption_obj))[:200]

    posted_at = ''
    if timestamp:
        posted_at = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime('%Y-%m-%d')

    if views == 0:
        views = likes * 10

    media_data.append({
        'url': url, 'views': views, 'likes': likes, 'comments': comments,
        'shares': 0, 'posted_at': posted_at, 'caption': caption,
    })


def extract_media_from_html(html, media_data, username):
    """Extract media data from page HTML (shared_data, additional_data)."""
    patterns = [
        r'window\._sharedData\s*=\s*({.*?});</script>',
        r'window\.__additionalDataLoaded\s*\([^,]+,\s*({.*?})\s*\)',
        r'"edge_owner_to_timeline_media":\s*({.*?"edges":\s*\[.*?\]})',
    ]
    for pat in patterns:
        matches = re.findall(pat, html, re.DOTALL)
        for match in matches:
            try:
                data = json.loads(match)
                extract_media_from_json(data, media_data, username)
            except:
                continue


async def main():
    creators = get_creators_needing_videos()
    total = len(creators)

    print(f'📸 IG VIDEO ENRICHER Worker {WORKER_ID}/{TOTAL_WORKERS}')
    print(f'   Creators to process: {total}')
    print(f'{"="*50}')
    sys.stdout.flush()

    if not creators:
        print('No Instagram creators need video data. Done.')
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
            locale='en-US',
        )
        page = await context.new_page()

        for creator in creators:
            presence_id = creator['presence_id']
            username = creator['username']
            followers = creator['followers']

            videos = await scrape_ig_profile(page, username)
            processed += 1

            if videos:
                inserted = save_videos(presence_id, videos)
                total_videos += inserted
                avg_views = sum(v['views'] for v in videos) / len(videos) if videos else 0
                print(f'  W{WORKER_ID} ✅ @{username} ({followers:,}): {len(videos)} posts, avg {avg_views:,.0f} views')
                sys.stdout.flush()
            else:
                errors += 1
                if errors % 5 == 0:
                    print(f'  W{WORKER_ID} ⚠️  {errors} errors so far (last: @{username})')

            if processed % BATCH_SIZE == 0:
                elapsed = (time.time() - start_time) / 3600
                rate = processed / max(elapsed, 0.001)
                eta = (total - processed) / max(rate, 1)

                conn = sqlite3.connect(DB_PATH)
                with_avg = conn.execute("SELECT COUNT(*) FROM platform_presences WHERE avg_views > 0 AND platform='instagram'").fetchone()[0]
                total_ig = conn.execute("SELECT COUNT(*) FROM platform_presences WHERE platform='instagram'").fetchone()[0]
                conn.close()

                print(f'\n  W{WORKER_ID} 📊 [{processed}/{total}] {total_videos} posts | {with_avg}/{total_ig} enriched | {rate:.0f}/hr | ETA {eta:.1f}hr | err:{errors}')
                sys.stdout.flush()

            # Rate limiting — IG is aggressive
            await asyncio.sleep(random.uniform(3, 6))

            # Rotate context every 100 profiles to avoid session tracking
            if processed % 100 == 0:
                await context.close()
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1280, 'height': 720},
                    locale='en-US',
                )
                page = await context.new_page()

        await browser.close()

    elapsed = (time.time() - start_time) / 3600
    print(f'\nW{WORKER_ID} DONE — {elapsed:.1f}hr | {processed} creators | {total_videos} posts | {errors} errors')


if __name__ == '__main__':
    asyncio.run(main())
