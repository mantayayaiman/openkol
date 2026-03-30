"""Base scraper class — platform-agnostic interface."""
from __future__ import annotations
from abc import ABC, abstractmethod
import os

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from ..models import PlatformProfile
from ..utils.anti_detect import (
    get_random_user_agent,
    get_random_viewport,
    get_random_timezone,
    get_random_locale,
    get_random_proxy,
    random_delay,
)


class BaseScraper(ABC):
    """Abstract base class for all platform scrapers."""

    platform: str = ""  # Override in subclass

    def __init__(self):
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def _launch_browser(self) -> BrowserContext:
        """Launch a browser with anti-detection settings."""
        pw = await async_playwright().start()

        proxy = get_random_proxy()
        viewport = get_random_viewport()
        headless = os.getenv("HEADLESS", "true").lower() == "true"

        launch_args = {
            "headless": headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ],
        }
        if proxy:
            launch_args["proxy"] = {"server": proxy}

        self._browser = await pw.chromium.launch(**launch_args)
        self._context = await self._browser.new_context(
            user_agent=get_random_user_agent(),
            viewport=viewport,
            timezone_id=get_random_timezone(),
            locale=get_random_locale(),
            java_script_enabled=True,
        )

        # Stealth: override navigator.webdriver
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            window.chrome = { runtime: {} };
        """)

        return self._context

    async def _close_browser(self):
        """Close browser and clean up."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()

    @abstractmethod
    async def scrape_profile(self, username: str) -> PlatformProfile:
        """Scrape a creator's profile. Must be implemented by subclass."""
        ...

    async def run(self, username: str) -> PlatformProfile:
        """Main entry point: launch browser, scrape, close."""
        try:
            await self._launch_browser()
            await random_delay(1, 3)  # Initial delay
            profile = await self.scrape_profile(username)
            return profile
        finally:
            await self._close_browser()
