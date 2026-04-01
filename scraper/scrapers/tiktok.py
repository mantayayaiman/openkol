"""TikTok profile scraper using Playwright."""
from __future__ import annotations
import json

from .base import BaseScraper
from ..models import PlatformProfile, ContentItem
from ..utils.anti_detect import random_delay


class TikTokScraper(BaseScraper):
    """Scrape TikTok profiles and recent videos."""

    platform = "tiktok"

    async def scrape_profile(self, username: str) -> PlatformProfile:
        """Scrape a TikTok profile page for stats and recent videos."""
        username = username.lstrip("@")
        url = f"https://www.tiktok.com/@{username}"

        page = await self._context.new_page()

        try:
            # Navigate to profile
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            if response and response.status == 404:
                return PlatformProfile(platform=self.platform, username=username)

            # Wait for profile data to load
            try:
                await page.wait_for_selector('[data-e2e="user-bio"]', timeout=15000)
            except Exception:
                pass
            await random_delay(2, 4)

            # Try to extract data from __UNIVERSAL_DATA_FOR_REHYDRATION__ script
            profile_data = await self._extract_from_hydration(page, username)
            if profile_data:
                return profile_data

            # Fallback: scrape from DOM
            return await self._extract_from_dom(page, username, url)

        finally:
            await page.close()

    async def _extract_from_hydration(
        self, page, username: str
    ) -> PlatformProfile | None:
        """Try to extract profile data from TikTok's hydration JSON."""
        try:
            script_content = await page.evaluate("""
                () => {
                    const el = document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__');
                    return el ? el.textContent : null;
                }
            """)
            if not script_content:
                return None

            data = json.loads(script_content)
            # Navigate TikTok's data structure (this changes frequently)
            default_scope = data.get("__DEFAULT_SCOPE__", {})
            user_detail = default_scope.get("webapp.user-detail", {})
            user_info = user_detail.get("userInfo", {})

            user = user_info.get("user", {})
            stats = user_info.get("stats", {})

            if not user:
                return None

            followers = stats.get("followerCount", 0)
            following = stats.get("followingCount", 0)
            total_likes = stats.get("heartCount", 0)
            total_videos = stats.get("videoCount", 0)

            return PlatformProfile(
                platform=self.platform,
                username=username,
                url=f"https://www.tiktok.com/@{username}",
                display_name=user.get("nickname", username),
                bio=user.get("signature", ""),
                profile_image=user.get("avatarLarger", ""),
                followers=followers,
                following=following,
                total_likes=total_likes,
                total_videos=total_videos,
                raw_data={"source": "hydration"},
            )

        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    async def _extract_from_dom(
        self, page, username: str, url: str
    ) -> PlatformProfile:
        """Fallback: extract profile data from the DOM."""

        async def _get_text(selector: str) -> str:
            try:
                el = await page.query_selector(selector)
                return (await el.text_content()).strip() if el else ""
            except Exception:
                return ""

        async def _parse_count(selector: str) -> int:
            text = await _get_text(selector)
            return self._parse_stat_number(text)

        display_name = await _get_text('h1[data-e2e="user-subtitle"]') or username
        bio = await _get_text('[data-e2e="user-bio"]')

        followers = await _parse_count('[data-e2e="followers-count"]')
        following = await _parse_count('[data-e2e="following-count"]')
        total_likes = await _parse_count('[data-e2e="likes-count"]')

        # Try to get video items
        content_samples = await self._scrape_recent_videos(page)

        avg_views = 0
        engagement_rate = 0.0
        if content_samples:
            total_views = sum(v.views for v in content_samples)
            avg_views = total_views // len(content_samples)
            if avg_views > 0:
                total_engagement = sum(v.likes + v.comments for v in content_samples)
                engagement_rate = total_engagement / (avg_views * len(content_samples))

        return PlatformProfile(
            platform=self.platform,
            username=username,
            url=url,
            display_name=display_name,
            bio=bio,
            followers=followers,
            following=following,
            total_likes=total_likes,
            avg_views=avg_views,
            engagement_rate=engagement_rate,
            content_samples=content_samples,
            raw_data={"source": "dom"},
        )

    async def _scrape_recent_videos(self, page) -> list[ContentItem]:
        """Scrape recent video items from the profile page."""
        videos = []
        try:
            # Get video cards
            video_elements = await page.query_selector_all(
                '[data-e2e="user-post-item"]'
            )

            for el in video_elements[:20]:  # Max 20 videos
                try:
                    # Get view count from the overlay
                    view_text = ""
                    view_el = await el.query_selector('[data-e2e="video-views"]')
                    if view_el:
                        view_text = await view_el.text_content()

                    link_el = await el.query_selector("a")
                    href = await link_el.get_attribute("href") if link_el else ""

                    views = self._parse_stat_number(view_text or "0")
                    videos.append(
                        ContentItem(
                            url=f"https://www.tiktok.com{href}" if href else "",
                            views=views,
                        )
                    )
                except Exception:
                    continue

        except Exception:
            pass

        return videos

    @staticmethod
    def _parse_stat_number(text: str) -> int:
        """Parse TikTok stat numbers like '1.2M', '456K', '789'."""
        text = text.strip().upper().replace(",", "")
        if not text:
            return 0
        try:
            if "M" in text:
                return int(float(text.replace("M", "")) * 1_000_000)
            if "K" in text:
                return int(float(text.replace("K", "")) * 1_000)
            return int(float(text))
        except ValueError:
            return 0
