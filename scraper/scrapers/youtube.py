"""YouTube channel scraper using Playwright."""
from __future__ import annotations
import re
import json

from .base import BaseScraper
from ..models import PlatformProfile, ContentItem
from ..utils.anti_detect import random_delay


class YouTubeScraper(BaseScraper):
    """Scrape YouTube channel profiles and recent videos."""

    platform = "youtube"

    async def scrape_profile(self, username: str) -> PlatformProfile:
        """Scrape a YouTube channel page."""
        username = username.lstrip("@")
        url = f"https://www.youtube.com/@{username}"

        page = await self._context.new_page()

        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            if response and response.status == 404:
                return PlatformProfile(platform=self.platform, username=username)

            await random_delay(2, 4)

            # Accept cookies if prompted
            try:
                consent = await page.query_selector('button[aria-label*="Accept"]')
                if consent:
                    await consent.click()
                    await random_delay(1, 2)
            except Exception:
                pass

            # Extract from meta + DOM
            profile = await self._extract_profile(page, username, url)

            # Navigate to Videos tab for recent content
            videos = await self._scrape_recent_videos(page, username)
            if videos:
                profile.content_samples = videos
                total_views = sum(v.views for v in videos)
                profile.avg_views = total_views // len(videos) if videos else 0
                if profile.avg_views > 0 and profile.followers > 0:
                    total_eng = sum(v.likes + v.comments for v in videos)
                    profile.engagement_rate = total_eng / (profile.avg_views * len(videos))

            return profile

        finally:
            await page.close()

    async def _extract_profile(
        self, page, username: str, url: str
    ) -> PlatformProfile:
        """Extract channel info from the page."""
        display_name = username
        bio = ""
        subscribers = 0
        total_videos = 0
        profile_image = ""

        try:
            # Channel name
            name_el = await page.query_selector(
                '#channel-name yt-formatted-string, '
                'ytd-channel-name yt-formatted-string, '
                '[id="channel-header"] #text'
            )
            if name_el:
                display_name = (await name_el.text_content() or "").strip()

            # Subscriber count
            sub_el = await page.query_selector(
                '#subscriber-count, '
                '[id="subscriber-count"], '
                'yt-formatted-string#subscriber-count'
            )
            if sub_el:
                sub_text = (await sub_el.text_content() or "").strip()
                subscribers = self._parse_subscriber_count(sub_text)

            # Description from meta
            meta_desc = await page.evaluate("""
                () => {
                    const meta = document.querySelector('meta[name="description"]');
                    return meta ? meta.getAttribute('content') : '';
                }
            """)
            bio = meta_desc or ""

            # Video count from meta or about tab
            video_count_el = await page.query_selector(
                '[id="videos-count"], '
                'yt-formatted-string.style-scope.ytd-channel-about-metadata-renderer'
            )
            if video_count_el:
                vc_text = (await video_count_el.text_content() or "").strip()
                total_videos = self._parse_number(vc_text)

            # Profile image
            avatar_el = await page.query_selector(
                '#avatar img, '
                'yt-img-shadow#avatar img, '
                '[id="channel-header"] img'
            )
            if avatar_el:
                profile_image = await avatar_el.get_attribute("src") or ""

        except Exception:
            pass

        return PlatformProfile(
            platform=self.platform,
            username=username,
            url=url,
            display_name=display_name,
            bio=bio[:500],
            profile_image=profile_image,
            followers=subscribers,
            total_videos=total_videos,
            raw_data={"source": "dom"},
        )

    async def _scrape_recent_videos(self, page, username: str) -> list[ContentItem]:
        """Navigate to the Videos tab and scrape recent uploads."""
        videos = []
        try:
            # Go to videos tab
            videos_url = f"https://www.youtube.com/@{username}/videos"
            await page.goto(videos_url, wait_until="domcontentloaded", timeout=20000)
            await random_delay(2, 3)

            # Get video renderers
            video_els = await page.query_selector_all(
                "ytd-rich-item-renderer, ytd-grid-video-renderer"
            )

            for el in video_els[:20]:
                try:
                    # Title and URL
                    title_el = await el.query_selector("#video-title")
                    title = (await title_el.text_content() or "").strip() if title_el else ""
                    href = await title_el.get_attribute("href") if title_el else ""

                    # View count
                    view_el = await el.query_selector(
                        "#metadata-line span:first-child, "
                        ".inline-metadata-item:first-child"
                    )
                    view_text = (await view_el.text_content() or "").strip() if view_el else "0"
                    views = self._parse_view_count(view_text)

                    video_url = f"https://www.youtube.com{href}" if href else ""

                    videos.append(
                        ContentItem(
                            url=video_url,
                            views=views,
                            caption=title[:200],
                        )
                    )
                except Exception:
                    continue

        except Exception:
            pass

        return videos

    @staticmethod
    def _parse_subscriber_count(text: str) -> int:
        """Parse '1.2M subscribers' -> 1200000."""
        text = text.strip().upper()
        match = re.search(r'([\d,.]+)\s*([KMB])?', text)
        if not match:
            return 0
        num_str = match.group(1).replace(",", "")
        multiplier = match.group(2) or ""
        try:
            num = float(num_str)
            if multiplier == "B":
                return int(num * 1_000_000_000)
            if multiplier == "M":
                return int(num * 1_000_000)
            if multiplier == "K":
                return int(num * 1_000)
            return int(num)
        except ValueError:
            return 0

    @staticmethod
    def _parse_view_count(text: str) -> int:
        """Parse '1.2M views' or '456K views'."""
        text = text.strip().upper()
        match = re.search(r'([\d,.]+)\s*([KMB])?', text)
        if not match:
            return 0
        num_str = match.group(1).replace(",", "")
        multiplier = match.group(2) or ""
        try:
            num = float(num_str)
            if multiplier == "B":
                return int(num * 1_000_000_000)
            if multiplier == "M":
                return int(num * 1_000_000)
            if multiplier == "K":
                return int(num * 1_000)
            return int(num)
        except ValueError:
            return 0

    @staticmethod
    def _parse_number(text: str) -> int:
        """Parse generic number strings."""
        match = re.search(r'[\d,]+', text)
        if match:
            return int(match.group().replace(",", ""))
        return 0
