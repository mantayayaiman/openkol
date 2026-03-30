#!/usr/bin/env python3
"""Bulk TikTok scraper using Playwright - extracts REAL data from hydration JSON."""

import asyncio
import json
import random
import sqlite3
import os
import sys
from datetime import datetime

# Try playwright import
try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Installing playwright...")
    os.system(f"{sys.executable} -m pip install playwright")
    os.system(f"{sys.executable} -m playwright install chromium")
    from playwright.async_api import async_playwright

# --- Creator lists by country ---
CREATORS = {
    "MY": [
        "khairulaming", "solikinh", "ameenizzul", "syahmisazli", "dfrntfaces",
        "cikmanggis", "alifcepmek", "msian.eats", "neelofa", "maborr",
        "kingshahx", "yonnyy", "soloz", "denaihati", "viloxyy",
        "fazleyakinmee", "squidgame.my", "afeyriel", "hairulazreen", "shawalein",
        "hannahhours"
    ],
    "ID": [
        "raborafael", "jfrprjkt", "fadiljaidi", "tanboykun", "tasyi.athasyia",
        "cifrfrhn", "yvfrhn", "arifrjt", "tifrfrhn", "jfrprjkt2",
        "gadiiing", "attahalilintar", "rikirhmdh", "jekfrn", "handfrn"
    ],
    "TH": ["maitjfcd", "zom.marie", "pearypie", "jaysbkk", "bambam1a", "ppkritt"],
    "PH": ["mimiyuuuh", "mannypacquiao", "alexagonzaga", "ivandragonn", "acbenavides"],
    "VN": ["quanglinhvlogs", "dovietnam", "tranghutt", "hienhoang.le"],
    "SG": ["jianhaotan", "naomineo", "munah_hirzi", "dee.kosh"],
}

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kreator.db")
JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "real_data.json")


def fmt_num(n):
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def compute_audit_scores(data):
    """Heuristic-based authenticity scoring."""
    followers = data.get("followers", 0)
    following = data.get("following", 0)
    likes = data.get("likes", 0)
    videos = data.get("videos", 0)

    # Engagement-to-follower ratio (likes per follower)
    if followers > 0:
        eng_ratio = likes / followers
    else:
        eng_ratio = 0

    # Following/follower ratio (lower = more authentic for big creators)
    if followers > 0:
        ff_ratio = following / followers
    else:
        ff_ratio = 1

    # Follower quality: penalize very high following/follower ratio
    if ff_ratio < 0.01:
        follower_quality = 90
    elif ff_ratio < 0.05:
        follower_quality = 80
    elif ff_ratio < 0.1:
        follower_quality = 70
    elif ff_ratio < 0.5:
        follower_quality = 60
    else:
        follower_quality = 40

    # Engagement authenticity: based on likes-per-follower
    if eng_ratio > 50:
        engagement_auth = 85
    elif eng_ratio > 20:
        engagement_auth = 80
    elif eng_ratio > 10:
        engagement_auth = 75
    elif eng_ratio > 5:
        engagement_auth = 70
    elif eng_ratio > 1:
        engagement_auth = 60
    else:
        engagement_auth = 45

    # Growth consistency (heuristic: more videos = more consistent)
    if videos > 500:
        growth = 85
    elif videos > 200:
        growth = 75
    elif videos > 50:
        growth = 65
    else:
        growth = 50

    # Comment quality placeholder (we don't scrape comments, use middle score)
    comment_quality = 65

    overall = int(0.3 * follower_quality + 0.3 * engagement_auth + 0.2 * growth + 0.2 * comment_quality)

    return {
        "overall": overall,
        "follower_quality": follower_quality,
        "engagement_authenticity": engagement_auth,
        "growth_consistency": growth,
        "comment_quality": comment_quality,
        "signals": {
            "engagement_ratio": round(eng_ratio, 2),
            "following_follower_ratio": round(ff_ratio, 4),
            "video_count": videos,
        }
    }


async def scrape_profile(page, username):
    """Scrape a single TikTok profile using hydration data."""
    try:
        await page.goto(
            f"https://www.tiktok.com/@{username}",
            wait_until="networkidle",
            timeout=30000
        )
        await asyncio.sleep(3)

        data = await page.evaluate('''() => {
            const el = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");
            return el ? el.textContent : null;
        }''')

        if not data:
            # Try SIGI_STATE as fallback
            data = await page.evaluate('''() => {
                const el = document.getElementById("SIGI_STATE");
                return el ? el.textContent : null;
            }''')

        if data:
            parsed = json.loads(data)

            # Try __UNIVERSAL_DATA_FOR_REHYDRATION__ format
            ds = parsed.get("__DEFAULT_SCOPE__", {})
            ud = ds.get("webapp.user-detail", {})

            if "userInfo" in ud:
                u = ud["userInfo"]["user"]
                s = ud["userInfo"]["stats"]
                return {
                    "username": username,
                    "name": u.get("nickname", username),
                    "bio": u.get("signature", ""),
                    "avatar": u.get("avatarLarger", ""),
                    "followers": s.get("followerCount", 0),
                    "following": s.get("followingCount", 0),
                    "likes": s.get("heartCount", 0),
                    "videos": s.get("videoCount", 0),
                    "verified": u.get("verified", False),
                }

            # Try SIGI_STATE format
            if "UserModule" in parsed:
                users = parsed["UserModule"].get("users", {})
                stats = parsed["UserModule"].get("stats", {})
                if username in users:
                    u = users[username]
                    s = stats.get(username, {})
                    return {
                        "username": username,
                        "name": u.get("nickname", username),
                        "bio": u.get("signature", ""),
                        "avatar": u.get("avatarLarger", ""),
                        "followers": s.get("followerCount", 0),
                        "following": s.get("followingCount", 0),
                        "likes": s.get("heartCount", 0),
                        "videos": s.get("videoCount", 0),
                        "verified": u.get("verified", False),
                    }

        return None
    except Exception as e:
        print(f"  Error scraping @{username}: {e}")
        return None


def insert_into_db(results, country_map):
    """Clear old data and insert fresh scraped data into SQLite."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Clear all existing data
    for table in ["content_samples", "metrics_history", "audit_scores", "platform_presences", "creators"]:
        cur.execute(f"DELETE FROM {table}")
    cur.execute("DELETE FROM sqlite_sequence")
    conn.commit()

    now = datetime.utcnow().isoformat()

    for r in results:
        country = country_map.get(r["username"], "XX")
        scores = compute_audit_scores(r)

        # Determine categories based on bio keywords
        categories = ["entertainment"]
        bio_lower = (r.get("bio") or "").lower()
        if any(w in bio_lower for w in ["food", "cook", "makan", "recipe", "eat"]):
            categories = ["food"]
        elif any(w in bio_lower for w in ["game", "gaming", "esport"]):
            categories = ["gaming"]
        elif any(w in bio_lower for w in ["beauty", "makeup", "skincare"]):
            categories = ["beauty"]
        elif any(w in bio_lower for w in ["music", "sing", "lagu"]):
            categories = ["music"]
        elif any(w in bio_lower for w in ["comedy", "funny", "lawak"]):
            categories = ["comedy"]
        elif any(w in bio_lower for w in ["travel", "jalan"]):
            categories = ["travel"]
        elif any(w in bio_lower for w in ["fashion", "style", "ootd"]):
            categories = ["fashion"]

        # Insert creator
        cur.execute("""
            INSERT INTO creators (name, bio, profile_image, country, primary_platform, categories, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r["name"], r.get("bio", ""), r.get("avatar", ""),
            country, "tiktok", json.dumps(categories), now, now
        ))
        creator_id = cur.lastrowid

        # Engagement rate heuristic: likes / (followers * videos) if available
        followers = r.get("followers", 0)
        videos = r.get("videos", 0)
        likes = r.get("likes", 0)
        eng_rate = 0
        if followers > 0 and videos > 0:
            avg_likes_per_video = likes / videos
            eng_rate = round((avg_likes_per_video / followers) * 100, 4)

        # Insert platform presence
        cur.execute("""
            INSERT INTO platform_presences (creator_id, platform, username, url, followers, following, total_likes, total_videos, avg_views, engagement_rate, last_scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            creator_id, "tiktok", r["username"],
            f"https://www.tiktok.com/@{r['username']}",
            followers, r.get("following", 0), likes, videos,
            0, eng_rate, now
        ))
        presence_id = cur.lastrowid

        # Insert initial metrics history
        cur.execute("""
            INSERT INTO metrics_history (presence_id, date, followers, avg_views, engagement_rate)
            VALUES (?, ?, ?, ?, ?)
        """, (presence_id, now[:10], followers, 0, eng_rate))

        # Insert audit scores
        cur.execute("""
            INSERT INTO audit_scores (creator_id, overall_score, follower_quality, engagement_authenticity, growth_consistency, comment_quality, scored_at, signals_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            creator_id, scores["overall"], scores["follower_quality"],
            scores["engagement_authenticity"], scores["growth_consistency"],
            scores["comment_quality"], now, json.dumps(scores["signals"])
        ))

    conn.commit()

    # Get count
    cur.execute("SELECT COUNT(*) FROM creators")
    count = cur.fetchone()[0]
    conn.close()
    return count


async def main():
    print("=" * 60)
    print("🔍 TikTok Bulk Scraper — Real Data via Playwright")
    print("=" * 60)

    # Build flat list with country mapping
    all_creators = []
    country_map = {}
    for country, usernames in CREATORS.items():
        for u in usernames:
            all_creators.append(u)
            country_map[u] = country

    total = len(all_creators)
    print(f"\n📋 {total} creators to scrape across {len(CREATORS)} countries\n")

    results = []
    failed = []

    # Load any previously saved results to resume
    if os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH) as f:
                results = json.load(f)
            scraped_usernames = {r["username"] for r in results}
            print(f"📂 Loaded {len(results)} previously scraped results")
        except:
            scraped_usernames = set()
    else:
        scraped_usernames = set()

    remaining = [u for u in all_creators if u not in scraped_usernames]
    if not remaining:
        print("All creators already scraped!")
    else:
        print(f"🔄 {len(remaining)} remaining to scrape\n")

    if remaining:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            page = await ctx.new_page()

            for i, username in enumerate(remaining, 1):
                country = country_map[username]
                print(f"[{i}/{len(remaining)}] Scraping @{username} ({country})...", end=" ", flush=True)

                data = await scrape_profile(page, username)

                if data and data.get("followers", 0) > 0:
                    results.append(data)
                    f = fmt_num(data["followers"])
                    l = fmt_num(data["likes"])
                    print(f"{f} followers, {l} likes ✅")
                elif data and data.get("followers", 0) == 0:
                    # Got hydration but 0 followers — likely captcha/blocked, retry once
                    print("⚠️ Got 0 followers, retrying...", end=" ", flush=True)
                    await asyncio.sleep(5)
                    data = await scrape_profile(page, username)
                    if data and data.get("followers", 0) > 0:
                        results.append(data)
                        f = fmt_num(data["followers"])
                        l = fmt_num(data["likes"])
                        print(f"{f} followers, {l} likes ✅")
                    else:
                        # Accept whatever we got
                        if data:
                            results.append(data)
                            print(f"Accepted with 0 followers ⚠️")
                        else:
                            failed.append(username)
                            print("❌ Failed")
                else:
                    failed.append(username)
                    print("❌ Failed")

                # Save incrementally every 5 scraped
                if i % 5 == 0:
                    with open(JSON_PATH, "w") as f:
                        json.dump(results, f, indent=2, ensure_ascii=False)

                # Rate limit: random 3-5s delay
                if i < len(remaining):
                    delay = random.uniform(3, 5)
                    await asyncio.sleep(delay)

            await browser.close()

    # Save JSON
    print(f"\n💾 Saving {len(results)} results to {JSON_PATH}...")
    with open(JSON_PATH, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Insert into DB
    print(f"🗄️  Inserting into database at {DB_PATH}...")
    db_count = insert_into_db(results, country_map)

    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"  ✅ Scraped: {len(results)}/{total}")
    print(f"  ❌ Failed:  {len(failed)}/{total}")
    if failed:
        print(f"  Failed: {', '.join(failed)}")
    print(f"  🗄️  In DB:   {db_count} creators")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
