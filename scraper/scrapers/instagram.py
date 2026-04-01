"""Instagram profile scraper using Playwright."""
from __future__ import annotations
import json

from .base import BaseScraper
from ..models import PlatformProfile
from ..utils.anti_detect import random_delay


class InstagramScraper(BaseScraper):
    """Scrape Instagram profiles and recent posts."""

    platform = "instagram"

    async def scrape_profile(self, username: str) -> PlatformProfile:
        """Scrape an Instagram profile page."""
        username = username.lstrip("@")
        url = f"https://www.instagram.com/{username}/"

        page = await self._context.new_page()

        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            if response and response.status == 404:
                return PlatformProfile(platform=self.platform, username=username)

            await random_delay(2, 5)

            # Try to extract from meta tags and structured data
            profile = await self._extract_from_meta(page, username, url)
            if profile and profile.followers > 0:
                return profile

            # Fallback: try __additionalDataLoaded or shared_data
            profile = await self._extract_from_shared_data(page, username, url)
            if profile:
                return profile

            # Last resort: DOM scraping
            return await self._extract_from_dom(page, username, url)

        finally:
            await page.close()

    async def _extract_from_meta(
        self, page, username: str, url: str
    ) -> PlatformProfile | None:
        """Extract data from meta tags."""
        try:
            meta_desc = await page.evaluate("""
                () => {
                    const meta = document.querySelector('meta[name="description"]');
                    return meta ? meta.getAttribute('content') : null;
                }
            """)

            if not meta_desc:
                return None

            # Parse: "1.2M Followers, 500 Following, 300 Posts - ..."
            import re
            followers = 0
            following = 0
            posts = 0

            followers_match = re.search(r'([\d,.]+[KMB]?)\s*Followers', meta_desc, re.IGNORECASE)
            following_match = re.search(r'([\d,.]+[KMB]?)\s*Following', meta_desc, re.IGNORECASE)
            posts_match = re.search(r'([\d,.]+[KMB]?)\s*Posts', meta_desc, re.IGNORECASE)

            if followers_match:
                followers = self._parse_number(followers_match.group(1))
            if following_match:
                following = self._parse_number(following_match.group(1))
            if posts_match:
                posts = self._parse_number(posts_match.group(1))

            # Get bio from page title or og:description
            title = await page.title() or ""
            bio_parts = meta_desc.split(" - ", 1)
            bio = bio_parts[1].strip() if len(bio_parts) > 1 else ""

            # Profile image from og:image
            profile_image = await page.evaluate("""
                () => {
                    const meta = document.querySelector('meta[property="og:image"]');
                    return meta ? meta.getAttribute('content') : '';
                }
            """) or ""

            display_name = title.split("(")[0].strip() if "(" in title else title.split("|")[0].strip()

            return PlatformProfile(
                platform=self.platform,
                username=username,
                url=url,
                display_name=display_name or username,
                bio=bio,
                profile_image=profile_image,
                followers=followers,
                following=following,
                total_videos=posts,
                raw_data={"source": "meta"},
            )

        except Exception:
            return None

    async def _extract_from_shared_data(
        self, page, username: str, url: str
    ) -> PlatformProfile | None:
        """Try extracting from window._sharedData or similar."""
        try:
            data = await page.evaluate("""
                () => {
                    if (window._sharedData) return JSON.stringify(window._sharedData);
                    // Try additional data
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    for (const s of scripts) {
                        try {
                            const d = JSON.parse(s.textContent);
                            if (d['@type'] === 'ProfilePage') return JSON.stringify(d);
                        } catch {}
                    }
                    return null;
                }
            """)
            if not data:
                return None

            parsed = json.loads(data)

            # Handle ld+json ProfilePage
            if parsed.get("@type") == "ProfilePage":
                main_entity = parsed.get("mainEntityofPage", parsed)
                interaction = {}
                for stat in main_entity.get("interactionStatistic", []):
                    stat_type = stat.get("interactionType", "")
                    if "Follow" in stat_type:
                        interaction["followers"] = stat.get("userInteractionCount", 0)

                return PlatformProfile(
                    platform=self.platform,
                    username=username,
                    url=url,
                    display_name=parsed.get("name", username),
                    bio=parsed.get("description", ""),
                    profile_image=parsed.get("image", ""),
                    followers=interaction.get("followers", 0),
                    raw_data={"source": "ld_json"},
                )

            return None
        except Exception:
            return None

    async def _extract_from_dom(
        self, page, username: str, url: str
    ) -> PlatformProfile:
        """Last resort: DOM-based extraction."""
        display_name = username
        bio = ""

        try:
            # Try to find the header/bio section
            header = await page.query_selector("header section")
            if header:
                name_el = await header.query_selector("h2, h1")
                if name_el:
                    display_name = (await name_el.text_content() or "").strip()

                bio_el = await header.query_selector('[class*="bio"], [class*="-note"]')
                if bio_el:
                    bio = (await bio_el.text_content() or "").strip()
        except Exception:
            pass

        return PlatformProfile(
            platform=self.platform,
            username=username,
            url=url,
            display_name=display_name,
            bio=bio,
            raw_data={"source": "dom_fallback"},
        )

    @staticmethod
    def _parse_number(text: str) -> int:
        """Parse Instagram-style numbers: 1.2M, 456K, 1,234."""
        text = text.strip().upper().replace(",", "")
        try:
            if "B" in text:
                return int(float(text.replace("B", "")) * 1_000_000_000)
            if "M" in text:
                return int(float(text.replace("M", "")) * 1_000_000)
            if "K" in text:
                return int(float(text.replace("K", "")) * 1_000)
            return int(float(text))
        except ValueError:
            return 0
