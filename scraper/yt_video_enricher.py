#!/usr/bin/env python3
"""
YouTube Video Enricher — Uses yt-dlp to fetch recent video stats for YouTube creators.
For each creator: get last 10 videos via --flat-playlist, store in content_samples, calculate avg_views + engagement_rate.

flat-playlist gives us view_count per video (fast, no full extraction needed).
For likes/comments, we do a second pass on top 3 videos with full extraction.

Usage:
  python3 scraper/yt_video_enricher.py                # Single worker
  python3 scraper/yt_video_enricher.py 0 4            # Worker 0 of 4
"""
import json
import sqlite3
import subprocess
import sys
import time
import random
from datetime import datetime, timezone

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
VIDEOS_PER_CREATOR = 10
BATCH_SIZE = 25

WORKER_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 0
TOTAL_WORKERS = int(sys.argv[2]) if len(sys.argv) > 2 else 1


def get_creators_needing_videos():
    """Get YouTube creators assigned to this worker who need video data."""
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
        WHERE pp.platform = 'youtube'
        AND pp.followers >= 1000
        AND (cs.sample_count IS NULL OR cs.sample_count < 3)
        AND pp.creator_id % ? = ?
        ORDER BY pp.followers DESC
    """, (TOTAL_WORKERS, WORKER_ID)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def fetch_videos_flat(username, count=VIDEOS_PER_CREATOR):
    """Use yt-dlp --flat-playlist to get video list with view counts (fast)."""
    url = f'https://www.youtube.com/@{username}/videos'
    try:
        result = subprocess.run(
            ['yt-dlp', '--flat-playlist', '--dump-json', '--playlist-items', f'1:{count}',
             '--no-warnings', '--quiet', url],
            capture_output=True, text=True, timeout=60
        )
        videos = []
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            try:
                d = json.loads(line)
                vid_id = d.get('id', '')
                videos.append({
                    'id': vid_id,
                    'url': d.get('webpage_url') or d.get('url') or f'https://www.youtube.com/watch?v={vid_id}',
                    'views': d.get('view_count', 0) or 0,
                    'likes': d.get('like_count', 0) or 0,
                    'comments': d.get('comment_count', 0) or 0,
                    'shares': 0,
                    'posted_at': format_date(d.get('upload_date', '')),
                    'caption': (d.get('title', '') or '')[:200],
                    'duration': d.get('duration', 0) or 0,
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return videos
    except subprocess.TimeoutExpired:
        return []
    except Exception:
        return []


def fetch_video_details(video_url):
    """Full extraction for a single video to get likes/comments."""
    try:
        result = subprocess.run(
            ['yt-dlp', '--skip-download', '--dump-json', '--no-warnings', '--quiet', video_url],
            capture_output=True, text=True, timeout=30
        )
        if result.stdout.strip():
            d = json.loads(result.stdout.strip().split('\n')[0])
            return {
                'likes': d.get('like_count', 0) or 0,
                'comments': d.get('comment_count', 0) or 0,
                'posted_at': format_date(d.get('upload_date', '')),
            }
    except:
        pass
    return None


def format_date(upload_date):
    if upload_date and len(upload_date) == 8:
        return f'{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}'
    return upload_date or ''


def save_videos(presence_id, videos, followers):
    """Save videos to content_samples and update avg_views + engagement_rate."""
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
        except:
            continue

    # Update avg_views and engagement_rate from all content_samples
    if inserted > 0:
        result = conn.execute(
            "SELECT AVG(views), COUNT(*), SUM(views), SUM(likes), SUM(comments) "
            "FROM content_samples WHERE presence_id=? AND views > 0",
            (presence_id,)
        ).fetchone()
        if result and result[0]:
            avg_views = int(result[0])
            total_vids = result[1]
            total_views = result[2] or 0
            total_likes = result[3] or 0
            total_comments = result[4] or 0

            # Engagement rate = (likes + comments) / views * 100
            if total_views > 0:
                er = round((total_likes + total_comments) / total_views * 100, 2)
                er = min(er, 30.0)  # Cap at 30%
            else:
                er = 0

            conn.execute(
                "UPDATE platform_presences SET avg_views=?, recent_videos=?, recent_views=?, engagement_rate=? WHERE id=?",
                (avg_views, total_vids, total_views, er, presence_id)
            )

    conn.commit()
    conn.close()
    return inserted


def main():
    creators = get_creators_needing_videos()
    total = len(creators)

    print(f'📺 YT VIDEO ENRICHER Worker {WORKER_ID}/{TOTAL_WORKERS}')
    print(f'   Creators to process: {total}')
    print(f'{"="*50}')
    sys.stdout.flush()

    if not creators:
        print('No YouTube creators need video data. Done.')
        return

    start_time = time.time()
    processed = 0
    total_videos = 0
    errors = 0

    for creator in creators:
        presence_id = creator['presence_id']
        username = creator['username']
        followers = creator['followers']

        # Step 1: Get video list with views (fast)
        videos = fetch_videos_flat(username)
        processed += 1

        if videos:
            # Step 2: For top 3 by views, get likes/comments via full extraction
            top3 = sorted(videos, key=lambda v: v['views'], reverse=True)[:3]
            for v in top3:
                details = fetch_video_details(v['url'])
                if details:
                    v['likes'] = details['likes']
                    v['comments'] = details['comments']
                    if details['posted_at']:
                        v['posted_at'] = details['posted_at']
                time.sleep(random.uniform(0.5, 1.5))

            inserted = save_videos(presence_id, videos, followers)
            total_videos += inserted

            avg_views = sum(v['views'] for v in videos) / len(videos) if videos else 0
            print(f'  W{WORKER_ID} ✅ @{username} ({followers:,}): {len(videos)} vids, avg {avg_views:,.0f} views')
            sys.stdout.flush()
        else:
            errors += 1

        if processed % BATCH_SIZE == 0:
            elapsed = (time.time() - start_time) / 3600
            rate = processed / max(elapsed, 0.001)
            eta = (total - processed) / max(rate, 1)

            conn = sqlite3.connect(DB_PATH)
            with_avg = conn.execute("SELECT COUNT(*) FROM platform_presences WHERE avg_views > 0 AND platform='youtube'").fetchone()[0]
            total_yt = conn.execute("SELECT COUNT(*) FROM platform_presences WHERE platform='youtube'").fetchone()[0]
            conn.close()

            print(f'\n  W{WORKER_ID} 📊 [{processed}/{total}] {total_videos} vids | {with_avg}/{total_yt} enriched | {rate:.0f}/hr | ETA {eta:.1f}hr | err:{errors}')
            sys.stdout.flush()

            progress_path = f'/Users/aiman/.openclaw/workspace/projects/kreator/scraper/yt_video_w{WORKER_ID}_progress.json'
            with open(progress_path, 'w') as f:
                json.dump({
                    'ts': datetime.now(timezone.utc).isoformat(),
                    'worker': WORKER_ID, 'processed': processed, 'total': total,
                    'videos': total_videos, 'errors': errors, 'rate': round(rate, 1),
                }, f)

        # Delay between creators
        time.sleep(random.uniform(1.0, 2.5))

    elapsed = (time.time() - start_time) / 3600
    print(f'\nW{WORKER_ID} DONE — {elapsed:.1f}hr | {processed} creators | {total_videos} videos | {errors} errors')


if __name__ == '__main__':
    main()
