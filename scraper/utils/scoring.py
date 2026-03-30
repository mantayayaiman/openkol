"""Authenticity scoring engine — heuristic-based v0."""
from __future__ import annotations
from ..models import PlatformProfile, AuditResult, ContentItem


# Engagement rate benchmarks by follower tier
ENGAGEMENT_BENCHMARKS = {
    # (min_followers, max_followers): expected_engagement_rate
    (0, 10_000): 0.08,
    (10_000, 50_000): 0.05,
    (50_000, 500_000): 0.035,
    (500_000, 1_000_000): 0.025,
    (1_000_000, 10_000_000): 0.018,
    (10_000_000, float("inf")): 0.012,
}


def _get_benchmark_engagement(followers: int) -> float:
    for (lo, hi), rate in ENGAGEMENT_BENCHMARKS.items():
        if lo <= followers < hi:
            return rate
    return 0.012


def score_engagement_ratio(profile: PlatformProfile) -> int:
    """Score 0-100: engagement rate vs benchmark for this tier."""
    if profile.followers == 0:
        return 0
    benchmark = _get_benchmark_engagement(profile.followers)
    ratio = profile.engagement_rate / benchmark if benchmark > 0 else 0

    if ratio < 0.1:
        return 5  # Essentially dead account
    if ratio < 0.3:
        return 20
    if ratio < 0.5:
        return 40
    if ratio < 0.8:
        return 60
    if ratio <= 1.5:
        return 85  # Healthy range
    if ratio <= 2.5:
        return 70  # Slightly above average — could be good content
    # Suspiciously high engagement
    return max(30, 100 - int((ratio - 2.5) * 20))


def score_following_ratio(profile: PlatformProfile) -> int:
    """Score 0-100: following-to-follower ratio. High ratio is suspicious."""
    if profile.followers == 0:
        return 0
    ratio = profile.following / profile.followers

    if ratio < 0.01:
        return 90  # Very selective
    if ratio < 0.05:
        return 85
    if ratio < 0.1:
        return 75
    if ratio < 0.3:
        return 60
    if ratio < 0.5:
        return 40
    if ratio < 1.0:
        return 25
    return 10  # Following more than followers — very suspicious


def score_view_ratio(profile: PlatformProfile) -> int:
    """Score 0-100: average views vs follower count."""
    if profile.followers == 0:
        return 0
    ratio = profile.avg_views / profile.followers

    if ratio < 0.005:
        return 10  # Almost no one sees content
    if ratio < 0.02:
        return 30
    if ratio < 0.05:
        return 50
    if ratio < 0.15:
        return 70
    if ratio < 0.4:
        return 85  # Good organic reach
    if ratio < 1.0:
        return 90  # Great reach
    return 80  # Viral — slightly uncertain


def score_posting_consistency(profile: PlatformProfile) -> int:
    """Score 0-100: posting frequency and consistency."""
    if not profile.content_samples or len(profile.content_samples) < 2:
        return 50  # Not enough data

    # Check variance in posting dates
    dates = []
    for item in profile.content_samples:
        if item.posted_at:
            try:
                from datetime import datetime
                dates.append(datetime.fromisoformat(item.posted_at.replace("Z", "+00:00")))
            except (ValueError, TypeError):
                pass

    if len(dates) < 2:
        return 50

    dates.sort()
    gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
    avg_gap = sum(gaps) / len(gaps) if gaps else 0

    if avg_gap == 0:
        return 60  # Posting same day — bursty
    if avg_gap <= 2:
        return 90  # Very consistent
    if avg_gap <= 5:
        return 80
    if avg_gap <= 10:
        return 65
    if avg_gap <= 30:
        return 45
    return 25  # Very infrequent


def score_comment_quality(content_samples: list[ContentItem]) -> int:
    """Score 0-100: comment diversity and authenticity.
    For v0, we use a heuristic based on comment-to-like ratio."""
    if not content_samples:
        return 50

    ratios = []
    for item in content_samples:
        if item.likes > 0:
            ratios.append(item.comments / item.likes)

    if not ratios:
        return 50

    avg_ratio = sum(ratios) / len(ratios)

    # Healthy comment-to-like ratio is ~2-8%
    if avg_ratio < 0.005:
        return 20  # Almost no comments — possible bot likes
    if avg_ratio < 0.02:
        return 50
    if avg_ratio < 0.05:
        return 75
    if avg_ratio < 0.1:
        return 85
    if avg_ratio < 0.2:
        return 75  # Slightly high
    return 50  # Unusually high — could be spam


def compute_audit_score(profile: PlatformProfile) -> AuditResult:
    """Compute the full authenticity audit for a platform profile."""
    engagement_score = score_engagement_ratio(profile)
    growth_score = score_posting_consistency(profile)  # Proxy for growth in v0
    comment_score = score_comment_quality(profile.content_samples)
    following_score = score_following_ratio(profile)
    view_score = score_view_ratio(profile)

    # Weighted overall score
    overall = int(
        engagement_score * 0.30
        + growth_score * 0.20
        + comment_score * 0.20
        + following_score * 0.10
        + view_score * 0.10
        + score_posting_consistency(profile) * 0.10
    )
    overall = max(0, min(100, overall))

    # Build signals
    signals: dict = {"red_flags": [], "warnings": [], "positives": []}

    if profile.engagement_rate < 0.005 and profile.followers > 10_000:
        signals["red_flags"].append("Extremely low engagement rate for follower count")
    if profile.following / max(profile.followers, 1) > 0.5:
        signals["red_flags"].append("Suspicious following-to-follower ratio")
    if profile.avg_views < profile.followers * 0.005 and profile.followers > 50_000:
        signals["red_flags"].append("Views significantly below expected for follower count")

    if engagement_score >= 70:
        signals["positives"].append("Healthy engagement rate for follower tier")
    if following_score >= 80:
        signals["positives"].append("Good following-to-follower ratio")
    if view_score >= 70:
        signals["positives"].append("Strong organic reach")

    # Clean empty lists
    signals = {k: v for k, v in signals.items() if v}

    return AuditResult(
        overall_score=overall,
        follower_quality=following_score,
        engagement_authenticity=engagement_score,
        growth_consistency=growth_score,
        comment_quality=comment_score,
        signals=signals,
    )
