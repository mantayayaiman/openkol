"""Anti-detection utilities for web scraping."""
import random
import asyncio
import os
from fake_useragent import UserAgent

ua = UserAgent()

# Common screen resolutions
VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1280, "height": 720},
]

# Common timezones
TIMEZONES = [
    "Asia/Kuala_Lumpur",
    "Asia/Jakarta",
    "Asia/Bangkok",
    "Asia/Manila",
    "Asia/Ho_Chi_Minh",
    "Asia/Singapore",
]

# Common locales
LOCALES = ["en-US", "en-GB", "id-ID", "th-TH", "vi-VN", "ms-MY", "fil-PH"]


def get_random_user_agent() -> str:
    """Return a random, recent user agent string."""
    return ua.random


def get_random_viewport() -> dict:
    """Return a random viewport size."""
    return random.choice(VIEWPORTS)


def get_random_timezone() -> str:
    """Return a random SEA timezone."""
    return random.choice(TIMEZONES)


def get_random_locale() -> str:
    """Return a random locale."""
    return random.choice(LOCALES)


async def random_delay(min_s: float | None = None, max_s: float | None = None):
    """Sleep for a random duration to mimic human behavior."""
    min_delay = min_s or float(os.getenv("MIN_DELAY_SECONDS", "2"))
    max_delay = max_s or float(os.getenv("MAX_DELAY_SECONDS", "5"))
    delay = random.uniform(min_delay, max_delay)
    await asyncio.sleep(delay)


def get_proxy_list() -> list[str]:
    """Load proxy list from environment variable."""
    proxies_str = os.getenv("PROXY_LIST", "")
    if not proxies_str:
        return []
    return [p.strip() for p in proxies_str.replace("\n", ",").split(",") if p.strip()]


def get_random_proxy() -> str | None:
    """Return a random proxy from the configured list, or None."""
    proxies = get_proxy_list()
    return random.choice(proxies) if proxies else None
