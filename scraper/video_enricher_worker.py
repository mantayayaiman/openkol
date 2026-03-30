#!/usr/bin/env python3
"""
Video Enricher Worker — Parallel worker for video data enrichment.
Usage: python3 scraper/video_enricher_worker.py <worker_id> <total_workers>

Each worker handles creators where (creator_id % total_workers == worker_id).
Uses yt-dlp to fetch recent video stats from TikTok profiles.
"""
import json
import sqlite3
import subprocess
import sys
import time
import os
import random
from datetime import datetime, timezone

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
VIDEOS_PER_CREATOR = 10
BATCH_SIZE = 25

WORKER_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 0
TOTAL_WORKERS = int(sys.argv[2]) if len(sys.argv) > 2 else 1


def get_creators_needing_videos():
    """Get TikTok creators assigned to this worker who need video data."""
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
        AND pp.creator_id % ? = ?
        ORDER BY pp.followers DESC
    """, (TOTAL_WORKERS, WORKER_ID)).fetchall()
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
            timeout=90
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
        return []


def format_date(upload_date):
    if upload_date and len(upload_date) == 8:
        return f'{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}'
    return upload_date or ''


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
            """, (presence_id, v['url'], v['views'], v['likes'], v['comments'], v['shares'], v['posted_at'], v['caption']))
            inserted += 1
        except:
            continue
    
    if inserted > 0:
        result = conn.execute(
            "SELECT AVG(views), COUNT(*), SUM(views) FROM content_samples WHERE presence_id=? AND views > 0",
            (presence_id,)
        ).fetchone()
        if result and result[0]:
            conn.execute(
                "UPDATE platform_presences SET avg_views=?, recent_videos=?, recent_views=? WHERE id=?",
                (int(result[0]), result[1], result[2] or 0, presence_id)
            )
    
    conn.commit()
    conn.close()
    return inserted


def main():
    creators = get_creators_needing_videos()
    total = len(creators)
    
    print(f'🎬 VIDEO ENRICHER Worker {WORKER_ID}/{TOTAL_WORKERS}')
    print(f'   Creators to process: {total}')
    print(f'{"="*50}')
    sys.stdout.flush()
    
    if not creators:
        print('No creators need video data. Done.')
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
            print(f'  W{WORKER_ID} ✅ @{username} ({followers:,}): {len(videos)} vids, avg {avg_views:,.0f} views')
            sys.stdout.flush()
        else:
            errors += 1
        
        if processed % BATCH_SIZE == 0:
            elapsed = (time.time() - start_time) / 3600
            rate = processed / max(elapsed, 0.001)
            eta = (total - processed) / max(rate, 1)
            
            conn = sqlite3.connect(DB_PATH)
            total_samples = conn.execute("SELECT COUNT(*) FROM content_samples").fetchone()[0]
            with_avg = conn.execute("SELECT COUNT(*) FROM platform_presences WHERE avg_views > 0 AND platform='tiktok'").fetchone()[0]
            conn.close()
            
            print(f'\n  W{WORKER_ID} 📊 [{processed}/{total}] {total_videos} vids | {total_samples} total | {with_avg} enriched | {rate:.0f}/hr | ETA {eta:.1f}hr | err:{errors}')
            sys.stdout.flush()
            
            # Save progress
            progress_path = f'/Users/aiman/.openclaw/workspace/projects/kreator/scraper/video_w{WORKER_ID}_progress.json'
            with open(progress_path, 'w') as f:
                json.dump({
                    'ts': datetime.now(timezone.utc).isoformat(),
                    'worker': WORKER_ID,
                    'processed': processed,
                    'total': total,
                    'videos': total_videos,
                    'errors': errors,
                    'rate': round(rate, 1),
                }, f)
        
        # Delay between creators
        time.sleep(random.uniform(1.5, 3.5))
    
    elapsed = (time.time() - start_time) / 3600
    print(f'\nW{WORKER_ID} DONE — {elapsed:.1f}hr | {processed} creators | {total_videos} videos | {errors} errors')


if __name__ == '__main__':
    main()
