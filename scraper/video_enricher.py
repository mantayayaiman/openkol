#!/usr/bin/env python3
"""
Video Enricher — Uses yt-dlp to fetch recent video stats for TikTok creators.
For each creator: get last 10 videos, store in content_samples, calculate avg_views.

This approach works because yt-dlp has its own anti-detection that bypasses
TikTok's empty-body response to headless browsers.

Run: python3 -u scraper/video_enricher.py 2>&1 | tee scraper/video_enricher.log
"""
import json
import sqlite3
import subprocess
import sys
import time
import random
from datetime import datetime, timezone

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
PROGRESS_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/video_enricher_progress.json'
VIDEOS_PER_CREATOR = 10
BATCH_SIZE = 50  # Save progress every N creators

def get_creators_needing_videos():
    """Get TikTok creators who don't have content samples yet, ordered by followers."""
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
        WHERE pp.platform = 'tiktok' 
        AND pp.followers >= 1000
        AND (cs.sample_count IS NULL OR cs.sample_count < 3)
        ORDER BY pp.followers DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def fetch_videos_ytdlp(username, count=VIDEOS_PER_CREATOR):
    """Use yt-dlp to get recent video stats for a TikTok user."""
    try:
        result = subprocess.run(
            [
                'yt-dlp',
                '--skip-download',
                '--dump-json',
                '--playlist-items', f'1:{count}',
                '--no-warnings',
                '--quiet',
                f'https://www.tiktok.com/@{username}'
            ],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        videos = []
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            try:
                d = json.loads(line)
                videos.append({
                    'url': d.get('webpage_url', f'https://www.tiktok.com/@{username}/video/{d.get("id","")}'),
                    'views': d.get('view_count', 0) or 0,
                    'likes': d.get('like_count', 0) or 0,
                    'comments': d.get('comment_count', 0) or 0,
                    'shares': d.get('repost_count', 0) or 0,
                    'posted_at': format_date(d.get('upload_date', '')),
                    'caption': (d.get('title', '') or d.get('description', '') or '')[:200],
                })
            except (json.JSONDecodeError, KeyError):
                continue
        
        return videos
    except subprocess.TimeoutExpired:
        return []
    except Exception as e:
        print(f"  ❌ Error fetching @{username}: {e}", file=sys.stderr)
        return []


def format_date(upload_date):
    """Convert YYYYMMDD to YYYY-MM-DD."""
    if upload_date and len(upload_date) == 8:
        return f'{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}'
    return upload_date or ''


def save_videos(presence_id, videos):
    """Insert videos into content_samples and update avg_views."""
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
            """, (presence_id, v['url'], v['views'], v['likes'], v['comments'], v['shares'], v['posted_at'], v['caption']))
            inserted += 1
        except Exception as e:
            print(f"  DB error: {e}", file=sys.stderr)
            continue
    
    # Update avg_views on platform_presences
    if inserted > 0:
        result = conn.execute(
            "SELECT AVG(views), COUNT(*) FROM content_samples WHERE presence_id=? AND views > 0",
            (presence_id,)
        ).fetchone()
        if result and result[0]:
            avg_views = int(result[0])
            total_views = conn.execute(
                "SELECT SUM(views) FROM content_samples WHERE presence_id=?",
                (presence_id,)
            ).fetchone()[0] or 0
            video_count = result[1]
            conn.execute(
                "UPDATE platform_presences SET avg_views=?, recent_videos=?, recent_views=? WHERE id=?",
                (avg_views, video_count, total_views, presence_id)
            )
    
    conn.commit()
    conn.close()
    return inserted


def main():
    creators = get_creators_needing_videos()
    total = len(creators)
    
    print(f'{"="*60}')
    print('🎬 VIDEO ENRICHER (yt-dlp)')
    print(f'   Creators needing video data: {total}')
    print(f'   Videos per creator: {VIDEOS_PER_CREATOR}')
    print(f'{"="*60}')
    sys.stdout.flush()
    
    if not creators:
        print('All creators have video data. Done.')
        return
    
    start_time = time.time()
    processed = 0
    total_videos = 0
    errors = 0
    
    for creator in creators:
        presence_id = creator['presence_id']
        username = creator['username']
        followers = creator['followers']
        
        videos = fetch_videos_ytdlp(username)
        processed += 1
        
        if videos:
            inserted = save_videos(presence_id, videos)
            total_videos += inserted
            
            avg_views = sum(v['views'] for v in videos) / len(videos) if videos else 0
            print(f'  ✅ @{username} ({followers:,}): {len(videos)} videos, avg {avg_views:,.0f} views')
            for v in videos[:3]:
                print(f'      {v["posted_at"]}: {v["views"]:>10,} views | {v["likes"]:>8,} likes | {v["caption"][:40]}')
            sys.stdout.flush()
        else:
            errors += 1
            if errors % 10 == 0:
                print(f'  ⚠️ {errors} errors so far')
        
        # Progress report
        if processed % BATCH_SIZE == 0 or processed == total:
            elapsed = (time.time() - start_time) / 3600
            rate = processed / max(elapsed, 0.001)
            eta_hours = (total - processed) / max(rate, 1)
            
            conn = sqlite3.connect(DB_PATH)
            total_samples = conn.execute("SELECT COUNT(*) FROM content_samples").fetchone()[0]
            with_avg = conn.execute("SELECT COUNT(*) FROM platform_presences WHERE avg_views > 0 AND platform='tiktok'").fetchone()[0]
            conn.close()
            
            print(f'\n  📊 [{processed}/{total}] {total_videos} videos | {total_samples} total samples | {with_avg} creators with avg_views')
            print(f'     Rate: {rate:.0f}/hr | ETA: {eta_hours:.1f}hr | Errors: {errors}')
            sys.stdout.flush()
            
            with open(PROGRESS_PATH, 'w') as f:
                json.dump({
                    'ts': datetime.now(timezone.utc).isoformat(),
                    'processed': processed,
                    'total': total,
                    'videos_inserted': total_videos,
                    'total_samples': total_samples,
                    'creators_with_avg': with_avg,
                    'errors': errors,
                    'rate_per_hour': round(rate, 1),
                    'eta_hours': round(eta_hours, 1),
                }, f)
        
        # Small delay to be nice
        time.sleep(random.uniform(1, 3))
    
    elapsed = (time.time() - start_time) / 3600
    print(f'\n{"="*60}')
    print(f'DONE — {elapsed:.1f}hr')
    print(f'Processed: {processed} | Videos: {total_videos} | Errors: {errors}')
    print(f'{"="*60}')


if __name__ == '__main__':
    main()
