#!/usr/bin/env python3
"""OpenKOL Scraper — CLI entry point for scraping creator profiles."""
from __future__ import annotations

import asyncio
import argparse
import json
import sys

from dotenv import load_dotenv

load_dotenv()

from .scrapers.tiktok import TikTokScraper
from .scrapers.instagram import InstagramScraper
from .scrapers.youtube import YouTubeScraper
from .utils.scoring import compute_audit_score


SCRAPERS = {
    "tiktok": TikTokScraper,
    "instagram": InstagramScraper,
    "youtube": YouTubeScraper,
}


def detect_platform(url: str) -> tuple[str, str] | None:
    """Detect platform and extract username from a URL."""
    import re

    if "tiktok.com" in url:
        match = re.search(r"tiktok\.com/@([^/?]+)", url)
        if match:
            return "tiktok", match.group(1)

    if "instagram.com" in url:
        match = re.search(r"instagram\.com/([^/?]+)", url)
        if match and match.group(1) not in ("p", "reel", "stories", "explore"):
            return "instagram", match.group(1)

    if "youtube.com" in url or "youtu.be" in url:
        match = re.search(r"youtube\.com/@([^/?]+)", url)
        if match:
            return "youtube", match.group(1)
        match = re.search(r"youtube\.com/channel/([^/?]+)", url)
        if match:
            return "youtube", match.group(1)

    return None


async def scrape_creator(
    platform: str, username: str, with_audit: bool = True
) -> dict:
    """Scrape a single creator and optionally compute audit score."""
    scraper_cls = SCRAPERS.get(platform)
    if not scraper_cls:
        raise ValueError(f"Unsupported platform: {platform}")

    scraper = scraper_cls()
    profile = await scraper.run(username)

    result = profile.model_dump()

    if with_audit and profile.followers > 0:
        audit = compute_audit_score(profile)
        result["audit"] = audit.model_dump()

    return result


async def main():
    parser = argparse.ArgumentParser(
        description="OpenKOL Scraper — Scrape creator profiles"
    )
    parser.add_argument(
        "target",
        help="Creator URL or platform:username (e.g., tiktok:username)",
    )
    parser.add_argument(
        "--no-audit",
        action="store_true",
        help="Skip authenticity scoring",
    )
    parser.add_argument(
        "--output", "-o",
        default="-",
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    args = parser.parse_args()

    # Parse target
    if "://" in args.target or "." in args.target:
        parsed = detect_platform(args.target)
        if not parsed:
            print(f"Error: Could not detect platform from URL: {args.target}", file=sys.stderr)
            sys.exit(1)
        platform, username = parsed
    elif ":" in args.target:
        platform, username = args.target.split(":", 1)
    else:
        print("Error: Invalid target format. Use a URL or platform:username", file=sys.stderr)
        sys.exit(1)

    print(f"Scraping {platform}/@{username}...", file=sys.stderr)

    result = await scrape_creator(platform, username, with_audit=not args.no_audit)

    indent = 2 if args.pretty else None
    output = json.dumps(result, indent=indent, default=str)

    if args.output == "-":
        print(output)
    else:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Saved to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
