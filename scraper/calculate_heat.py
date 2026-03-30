#!/usr/bin/env python3
"""
Calculate Heat Score (0-100) for all creators.

Heat Score formula:
  - Recent video frequency (posts in last 30 days)     — 20% weight
  - Recent view velocity (views_30d / followers)        — 30% weight
  - Recent engagement rate (likes+comments_30d / views) — 25% weight
  - Follower growth rate (new_followers_30d / followers) — 25% weight

Data source: platform_presences table
For creators without recent data, fall back to engagement_rate estimate.
"""

import sqlite3
import os
import math

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kreator.db")


def sigmoid_scale(value: float, midpoint: float, steepness: float = 1.0) -> float:
    """Scale a value 0-100 using sigmoid curve centered at midpoint."""
    if value <= 0:
        return 0.0
    x = steepness * (value - midpoint) / midpoint
    return 100.0 / (1.0 + math.exp(-x))


def clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def calc_frequency_score(recent_videos: int) -> float:
    """Score based on posting frequency in last 30 days.
    0 videos = 0, 1-2 = low, 5-10 = good, 15+ = great, 30+ = max."""
    if recent_videos <= 0:
        return 0.0
    if recent_videos >= 30:
        return 100.0
    # Linear scale: 1 video = ~3.3, 10 = 33, 20 = 67, 30 = 100
    return clamp((recent_videos / 30.0) * 100.0)


def calc_velocity_score(recent_views: int, followers: int) -> float:
    """Score based on view velocity = views_30d / followers.
    Ratio 0 = 0, 0.5 = decent, 1.0 = great, 5+ = viral."""
    if followers <= 0 or recent_views <= 0:
        return 0.0
    ratio = recent_views / followers
    # Use sigmoid: midpoint at ratio=1.0 (views = followers)
    return clamp(sigmoid_scale(ratio, midpoint=1.0, steepness=2.0))


def calc_engagement_score(engagement_rate: float) -> float:
    """Score based on engagement rate (already as percentage, e.g. 5.33 = 5.33%).
    0% = 0, 3% = decent, 8% = great, 20%+ = amazing."""
    if engagement_rate <= 0:
        return 0.0
    return clamp(sigmoid_scale(engagement_rate, midpoint=5.0, steepness=2.0))


def calc_growth_score(recent_new_followers: int, followers: int) -> float:
    """Score based on follower growth rate in 30 days.
    0% = 0, 2% = decent, 5% = great, 20%+ = explosive."""
    if followers <= 0 or recent_new_followers <= 0:
        return 0.0
    growth_pct = (recent_new_followers / followers) * 100.0
    return clamp(sigmoid_scale(growth_pct, midpoint=5.0, steepness=2.0))


def calc_reach_multiplier(followers: int) -> float:
    """Multiplier based on audience size. Prevents tiny accounts from dominating.
    <500 = 0.15, 1K = 0.3, 10K = 0.6, 100K = 0.85, 1M+ = 1.0"""
    if followers <= 0:
        return 0.0
    if followers >= 1_000_000:
        return 1.0
    # Log scale: log10(500)=2.7, log10(1M)=6
    log_f = math.log10(max(followers, 1))
    return clamp(0.15 + (log_f - 2.7) / (6.0 - 2.7) * 0.85, 0.15, 1.0)


def calc_video_engagement_score(avg_likes: float, avg_views: float) -> float:
    """Score based on actual video engagement (likes/views ratio from content_samples).
    1% = low, 5% = decent, 10% = great, 20%+ = amazing."""
    if avg_views <= 0 or avg_likes <= 0:
        return 0.0
    ratio_pct = (avg_likes / avg_views) * 100.0
    return clamp(sigmoid_scale(ratio_pct, midpoint=5.0, steepness=2.0))


def calc_views_to_followers_score(avg_views: float, followers: int) -> float:
    """Score based on avg video views relative to follower count.
    Higher ratio = more viral/discoverable content.
    0.1 = low, 0.5 = decent, 1.0+ = great (views match followers per video)."""
    if followers <= 0 or avg_views <= 0:
        return 0.0
    ratio = avg_views / followers
    return clamp(sigmoid_scale(ratio, midpoint=0.3, steepness=2.0))


def calculate_heat_score(row: dict) -> float:
    """Calculate heat score for a creator's platform presence.
    
    With video samples (content_samples data):
      - View/follower ratio     30%  (are videos reaching beyond followers?)
      - Video engagement        25%  (likes+comments per view)  
      - Posting frequency       20%  (how active?)
      - Follower growth         10%  (growing audience?)
      - Profile engagement      15%  (engagement_rate from profile)
    
    Without video samples: fallback to engagement_rate only.
    """
    recent_videos = row.get("recent_videos") or 0
    recent_views = row.get("recent_views") or 0
    recent_new_followers = row.get("recent_new_followers") or 0
    followers = row.get("followers") or 0
    engagement_rate = row.get("engagement_rate") or 0.0
    avg_views = row.get("avg_views") or row.get("avg_sample_views") or 0
    avg_likes = row.get("avg_sample_likes") or 0
    sample_count = row.get("sample_count") or 0

    has_video_samples = sample_count > 0 and avg_views > 0
    has_recent_data = recent_videos > 0 or recent_views > 0
    reach_mult = calc_reach_multiplier(followers)

    if has_video_samples:
        # Best data: actual video performance from yt-dlp
        views_ratio = calc_views_to_followers_score(avg_views, followers)
        video_eng = calc_video_engagement_score(avg_likes, avg_views)
        freq = calc_frequency_score(recent_videos if recent_videos > 0 else sample_count)
        growth = calc_growth_score(recent_new_followers, followers)
        profile_eng = calc_engagement_score(engagement_rate)

        raw_heat = (
            views_ratio * 0.30
            + video_eng * 0.25
            + freq * 0.20
            + growth * 0.10
            + profile_eng * 0.15
        )
        heat = raw_heat * reach_mult
    elif has_recent_data:
        # Has 30-day stats but no individual video samples
        freq = calc_frequency_score(recent_videos)
        velocity = calc_velocity_score(recent_views, followers)
        engagement = calc_engagement_score(engagement_rate)
        growth = calc_growth_score(recent_new_followers, followers)

        raw_heat = (
            freq * 0.20
            + velocity * 0.30
            + engagement * 0.25
            + growth * 0.25
        )
        heat = raw_heat * reach_mult
    else:
        # Fallback: use engagement rate alone, scaled down
        heat = calc_engagement_score(engagement_rate) * 0.40 * reach_mult

    return round(clamp(heat), 1)


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get all creators with their best platform presence + content sample stats
    rows = cur.execute("""
        SELECT c.id as creator_id,
               pp.followers, pp.engagement_rate,
               pp.recent_videos, pp.recent_views,
               pp.recent_new_followers, pp.impressions,
               pp.avg_views,
               cs.sample_count, cs.avg_sample_views, cs.avg_sample_likes, cs.avg_sample_comments
        FROM creators c
        LEFT JOIN platform_presences pp ON pp.creator_id = c.id
        LEFT JOIN (
            SELECT presence_id,
                   COUNT(*) as sample_count,
                   AVG(views) as avg_sample_views,
                   AVG(likes) as avg_sample_likes,
                   AVG(comments) as avg_sample_comments
            FROM content_samples
            WHERE views > 0
            GROUP BY presence_id
        ) cs ON cs.presence_id = pp.id
        WHERE pp.id IS NOT NULL
        ORDER BY c.id, pp.followers DESC
    """).fetchall()

    # Group by creator, take best (highest followers) platform
    creator_scores: dict[int, float] = {}
    for row in rows:
        cid = row["creator_id"]
        if cid in creator_scores:
            continue  # Already have best platform
        score = calculate_heat_score(dict(row))
        creator_scores[cid] = score

    # Batch update
    print(f"Calculating heat scores for {len(creator_scores)} creators...")
    cur.executemany(
        "UPDATE creators SET heat_score = ? WHERE id = ?",
        [(score, cid) for cid, score in creator_scores.items()],
    )
    conn.commit()

    # Stats
    scores = list(creator_scores.values())
    on_fire = sum(1 for s in scores if s >= 80)
    hot = sum(1 for s in scores if 60 <= s < 80)
    warm = sum(1 for s in scores if 40 <= s < 60)
    cool = sum(1 for s in scores if s < 40)

    print(f"\nHeat Score Distribution:")
    print(f"  🔴 On Fire (80-100): {on_fire}")
    print(f"  🟠 Hot     (60-79):  {hot}")
    print(f"  🟡 Warm    (40-59):  {warm}")
    print(f"  ⬜ Cool    (0-39):   {cool}")
    print(f"\n  Total: {len(scores)}")
    print(f"  Average: {sum(scores)/len(scores):.1f}")

    conn.close()


if __name__ == "__main__":
    main()
