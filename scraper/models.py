"""Standardized data models for creator profiles."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ContentItem(BaseModel):
    """A single piece of content (video/post/reel)."""
    url: str = ""
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    posted_at: Optional[str] = None
    caption: str = ""


class PlatformProfile(BaseModel):
    """Standardized profile data from a single platform."""
    platform: str  # tiktok | instagram | youtube
    username: str
    url: str = ""
    display_name: str = ""
    bio: str = ""
    profile_image: str = ""
    followers: int = 0
    following: int = 0
    total_likes: int = 0
    total_videos: int = 0
    avg_views: int = 0
    engagement_rate: float = 0.0
    content_samples: list[ContentItem] = Field(default_factory=list)
    scraped_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    raw_data: dict = Field(default_factory=dict)


class AuditResult(BaseModel):
    """Authenticity audit result."""
    overall_score: int = 0  # 0-100
    follower_quality: int = 0
    engagement_authenticity: int = 0
    growth_consistency: int = 0
    comment_quality: int = 0
    signals: dict = Field(default_factory=dict)


class CreatorProfile(BaseModel):
    """Complete creator profile across platforms."""
    name: str
    bio: str = ""
    profile_image: str = ""
    country: str = ""
    primary_platform: str = ""
    categories: list[str] = Field(default_factory=list)
    platforms: list[PlatformProfile] = Field(default_factory=list)
    audit: Optional[AuditResult] = None
