#!/usr/bin/env python3
"""
KolBuff QA Suite — Automated blackbox + whitebox testing for the live website.
Tests API endpoints, data integrity, page rendering, and feature correctness.

Usage:
  python3 qa/test_live.py                    # Test production (kolbuff.com)
  python3 qa/test_live.py --base http://localhost:3000  # Test local dev

Exit codes: 0 = all pass, 1 = failures found
"""

import json
import sys
import time
import urllib.request
import urllib.error
import sqlite3
import os
import argparse
from datetime import datetime, timezone

# ─── Config ─────────────────────────────────────────────────────────────────
DEFAULT_BASE = "https://kreator-mu.vercel.app"
LOCAL_DB = "/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db"
REPORT_PATH = "/Users/aiman/.openclaw/workspace/projects/kreator/qa/qa_report.json"

# Known test creators (must exist in DB)
TEST_CREATORS = [
    {"name": "Khairulaming", "id": 35, "country": "MY", "min_followers": 1_000_000},
]

# ─── Test infrastructure ────────────────────────────────────────────────────
class QAResult:
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.start_time = time.time()
    
    def ok(self, name, detail=""):
        self.tests.append({"name": name, "status": "PASS", "detail": detail})
        self.passed += 1
        print(f"  ✅ {name}")
    
    def fail(self, name, detail=""):
        self.tests.append({"name": name, "status": "FAIL", "detail": detail})
        self.failed += 1
        print(f"  ❌ {name}: {detail}")
    
    def warn(self, name, detail=""):
        self.tests.append({"name": name, "status": "WARN", "detail": detail})
        self.warnings += 1
        print(f"  ⚠️  {name}: {detail}")
    
    def summary(self):
        elapsed = time.time() - self.start_time
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "total": len(self.tests),
            "tests": self.tests,
        }


def fetch_json(url, timeout=15):
    """Fetch URL and parse JSON response."""
    req = urllib.request.Request(url, headers={"User-Agent": "KolBuff-QA/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = resp.status
        body = json.loads(resp.read())
        return status, body


def fetch_status(url, timeout=10):
    """Fetch URL and return HTTP status code."""
    req = urllib.request.Request(url, headers={"User-Agent": "KolBuff-QA/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


# ─── Test suites ────────────────────────────────────────────────────────────

def test_api_health(base, r):
    """Test all API endpoints return 200 and valid JSON."""
    print("\n📡 API Health")
    
    endpoints = [
        ("/api/stats", "Stats API"),
        ("/api/creators?country=MY&limit=3", "Creators API (MY)"),
        ("/api/creators?country=ID&limit=3", "Creators API (ID)"),
        ("/api/suggest?q=khairul", "Suggest API"),
        (f"/api/creators/{TEST_CREATORS[0]['id']}", "Creator Detail API"),
    ]
    
    for path, name in endpoints:
        try:
            status, body = fetch_json(f"{base}{path}")
            if status == 200:
                if "error" in body and not body.get("creators"):
                    r.fail(name, f"200 but error in body: {body['error'][:100]}")
                else:
                    r.ok(name)
            else:
                r.fail(name, f"HTTP {status}")
        except Exception as e:
            r.fail(name, str(e)[:100])


def test_stats_integrity(base, r):
    """Test /api/stats returns sensible numbers."""
    print("\n📊 Stats Integrity")
    
    try:
        _, data = fetch_json(f"{base}/api/stats")
        
        creators = data.get("creators", 0)
        countries = data.get("countries", 0)
        platforms = data.get("platforms", 0)
        
        if creators > 1000:
            r.ok(f"Creator count: {creators:,}")
        elif creators > 0:
            r.warn(f"Creator count low: {creators}", "Expected 1000+")
        else:
            r.fail("Creator count", f"Got {creators}, expected > 0")
        
        if 5 <= countries <= 200:
            r.ok(f"Country count: {countries}")
        else:
            r.fail("Country count", f"Got {countries}, expected 5-200")
        
        if 1 <= platforms <= 10:
            r.ok(f"Platform count: {platforms}")
        else:
            r.fail("Platform count", f"Got {platforms}, expected 1-10")
    
    except Exception as e:
        r.fail("Stats fetch", str(e)[:100])


def test_creator_data(base, r):
    """Test creator detail API returns complete data."""
    print("\n👤 Creator Data Quality")
    
    for tc in TEST_CREATORS:
        try:
            _, data = fetch_json(f"{base}/api/creators/{tc['id']}")
            
            # Basic fields
            if data.get("name") == tc["name"]:
                r.ok(f"{tc['name']}: name correct")
            else:
                r.fail(f"{tc['name']}: name", f"Got '{data.get('name')}', expected '{tc['name']}'")
            
            if data.get("country") == tc["country"]:
                r.ok(f"{tc['name']}: country correct ({tc['country']})")
            else:
                r.fail(f"{tc['name']}: country", f"Got '{data.get('country')}', expected '{tc['country']}'")
            
            # Platforms should not be empty
            platforms = data.get("platforms", [])
            if len(platforms) > 0:
                r.ok(f"{tc['name']}: has {len(platforms)} platform(s)")
            else:
                r.fail(f"{tc['name']}: platforms", "Empty — sync may be broken")
            
            # Check follower count on best platform
            if platforms:
                best = max(platforms, key=lambda p: p.get("followers", 0))
                followers = best.get("followers", 0)
                if followers >= tc["min_followers"]:
                    r.ok(f"{tc['name']}: followers {followers:,}")
                else:
                    r.fail(f"{tc['name']}: followers", f"Got {followers:,}, expected >= {tc['min_followers']:,}")
                
                # Check avg_views is populated
                avg_views = best.get("avg_views", 0)
                if avg_views > 0:
                    r.ok(f"{tc['name']}: avg_views {avg_views:,}")
                else:
                    r.warn(f"{tc['name']}: avg_views is 0", "Video enrichment may not have synced")
            
            # Content samples (top videos)
            samples = data.get("content_samples", [])
            if len(samples) > 0:
                r.ok(f"{tc['name']}: {len(samples)} top videos")
                # Validate sample structure
                s = samples[0]
                for field in ["url", "views", "likes", "caption"]:
                    if not s.get(field) and s.get(field) != 0:
                        r.fail(f"{tc['name']}: video missing '{field}'", str(s)[:100])
                        break
                else:
                    r.ok(f"{tc['name']}: video data structure valid")
            else:
                r.warn(f"{tc['name']}: no top videos", "top_content may not have synced")
            
            # Heat score should be > 0 for known big creators
            heat = data.get("heat_score", 0)
            if heat > 10:
                r.ok(f"{tc['name']}: heat score {heat}")
            elif heat > 0:
                r.warn(f"{tc['name']}: heat score low ({heat})", "May need recalculation")
            else:
                r.fail(f"{tc['name']}: heat score is 0", "Heat calculation may be broken")
            
            # Categories should be parsed
            cats = data.get("categories", [])
            if isinstance(cats, list) and len(cats) > 0:
                r.ok(f"{tc['name']}: categories {cats}")
            else:
                r.warn(f"{tc['name']}: no categories", f"Got: {cats}")
            
            # Negative number check (integer overflow bug)
            for p in platforms:
                if (p.get("total_likes", 0) or 0) < 0:
                    r.fail(f"{tc['name']}: negative total_likes on {p['platform']}", f"{p['total_likes']}")
                if (p.get("followers", 0) or 0) < 0:
                    r.fail(f"{tc['name']}: negative followers on {p['platform']}", f"{p['followers']}")
                if (p.get("engagement_rate", 0) or 0) < 0:
                    r.fail(f"{tc['name']}: negative engagement_rate on {p['platform']}", f"{p['engagement_rate']}")
        
        except Exception as e:
            r.fail(f"{tc['name']}: fetch error", str(e)[:100])


def test_search(base, r):
    """Test search/suggest functionality."""
    print("\n🔍 Search & Suggest")
    
    queries = [
        ("khairul", "Khairulaming"),
        ("soloz", None),  # Just check it returns results
    ]
    
    for q, expected_name in queries:
        try:
            _, data = fetch_json(f"{base}/api/suggest?q={q}")
            suggestions = data.get("suggestions", [])
            
            if len(suggestions) > 0:
                r.ok(f"suggest?q={q}: {len(suggestions)} results")
                if expected_name:
                    names = [s.get("name", "") for s in suggestions]
                    if expected_name in names:
                        r.ok(f"suggest?q={q}: found {expected_name}")
                    else:
                        r.fail(f"suggest?q={q}: missing {expected_name}", f"Got: {names[:5]}")
            else:
                r.fail(f"suggest?q={q}: no results", "Search index may be empty")
        except Exception as e:
            r.fail(f"suggest?q={q}", str(e)[:100])
    
    # Test minimum length requirement
    try:
        _, data = fetch_json(f"{base}/api/suggest?q=a")
        suggestions = data.get("suggestions", [])
        if len(suggestions) == 0:
            r.ok("suggest: rejects single-char queries")
        else:
            r.warn("suggest: returns results for single char", "May cause performance issues")
    except:
        pass


def test_creators_list(base, r):
    """Test creator list API with various filters."""
    print("\n📋 Creator List & Filters")
    
    # Country filter
    for country in ["MY", "ID", "SG"]:
        try:
            _, data = fetch_json(f"{base}/api/creators?country={country}&limit=5")
            creators = data.get("creators", [])
            total = data.get("total", 0)
            
            if total > 0 and len(creators) > 0:
                r.ok(f"country={country}: {total} total, {len(creators)} returned")
                # Verify all results match the country
                mismatched = [c for c in creators if c.get("country") != country]
                if mismatched:
                    r.fail(f"country={country}: wrong countries in results", 
                           f"{len(mismatched)} creators have wrong country")
            else:
                r.warn(f"country={country}: no results", f"total={total}")
        except Exception as e:
            r.fail(f"country={country}", str(e)[:100])
    
    # Sort order
    try:
        _, data = fetch_json(f"{base}/api/creators?country=MY&sort=followers&limit=10")
        creators = data.get("creators", [])
        if len(creators) >= 2:
            followers = [c.get("followers", 0) for c in creators]
            if followers == sorted(followers, reverse=True):
                r.ok("sort=followers: correctly ordered DESC")
            else:
                r.fail("sort=followers: wrong order", f"Got: {followers[:5]}")
    except Exception as e:
        r.fail("sort=followers", str(e)[:100])
    
    # Tier filter
    try:
        _, data = fetch_json(f"{base}/api/creators?country=MY&tier=mega&limit=5")
        creators = data.get("creators", [])
        if creators:
            under_10m = [c for c in creators if (c.get("followers") or 0) < 10_000_000]
            if not under_10m:
                r.ok(f"tier=mega: all have 10M+ followers")
            else:
                r.fail("tier=mega: creators under 10M", f"{len(under_10m)} incorrect")
    except Exception as e:
        r.fail("tier=mega", str(e)[:100])


def test_data_integrity(base, r):
    """Test data makes sense (no negative numbers, no absurd values)."""
    print("\n🔢 Data Integrity")
    
    try:
        _, data = fetch_json(f"{base}/api/creators?country=MY&sort=followers&limit=50")
        creators = data.get("creators", [])
        
        neg_likes = 0
        neg_followers = 0
        neg_engagement = 0
        absurd_engagement = 0
        zero_names = 0
        
        for c in creators:
            if (c.get("total_likes") or 0) < 0: neg_likes += 1
            if (c.get("followers") or 0) < 0: neg_followers += 1
            if (c.get("engagement_rate") or 0) < 0: neg_engagement += 1
            if (c.get("engagement_rate") or 0) > 100: absurd_engagement += 1
            if not c.get("name"): zero_names += 1
        
        if neg_likes == 0:
            r.ok("No negative total_likes")
        else:
            r.fail(f"Negative total_likes", f"{neg_likes}/{len(creators)} creators")
        
        if neg_followers == 0:
            r.ok("No negative followers")
        else:
            r.fail(f"Negative followers", f"{neg_followers}/{len(creators)} creators")
        
        if neg_engagement == 0:
            r.ok("No negative engagement_rate")
        else:
            r.fail(f"Negative engagement_rate", f"{neg_engagement}/{len(creators)} creators")
        
        if absurd_engagement == 0:
            r.ok("No engagement_rate > 100%")
        else:
            r.fail(f"Absurd engagement_rate (>100%)", f"{absurd_engagement}/{len(creators)} creators")
        
        if zero_names == 0:
            r.ok("All creators have names")
        else:
            r.fail(f"Missing names", f"{zero_names}/{len(creators)} creators")
    
    except Exception as e:
        r.fail("Data integrity check", str(e)[:100])


def test_pages(base, r):
    """Test static pages return 200."""
    print("\n📄 Page Loading")
    
    pages = [
        ("/", "Homepage"),
        ("/browse", "Browse"),
        ("/rankings", "Rankings"),
        ("/lookup", "Lookup"),
        ("/shortlist", "Shortlist"),
        ("/changelog", "Changelog"),
        (f"/creator/{TEST_CREATORS[0]['id']}", "Creator Profile"),
    ]
    
    for path, name in pages:
        try:
            status = fetch_status(f"{base}{path}")
            if status == 200:
                r.ok(f"{name} ({path})")
            else:
                r.fail(f"{name} ({path})", f"HTTP {status}")
        except Exception as e:
            r.fail(f"{name} ({path})", str(e)[:100])


def test_local_vs_cloud(base, r):
    """Compare local SQLite data with cloud Turso data (whitebox test)."""
    print("\n🔄 Local vs Cloud Sync")
    
    if not os.path.exists(LOCAL_DB):
        r.warn("Local DB not found", "Skipping sync comparison")
        return
    
    conn = sqlite3.connect(LOCAL_DB)
    
    # Compare creator counts
    local_count = conn.execute("SELECT COUNT(*) FROM creators").fetchone()[0]
    try:
        _, stats = fetch_json(f"{base}/api/stats")
        cloud_count = stats.get("creators", 0)
        
        diff = abs(local_count - cloud_count)
        pct = diff / max(local_count, 1) * 100
        
        if pct < 5:
            r.ok(f"Creator count sync: local={local_count:,} cloud={cloud_count:,} (diff {pct:.1f}%)")
        elif pct < 20:
            r.warn(f"Creator count drift: local={local_count:,} cloud={cloud_count:,} (diff {pct:.1f}%)")
        else:
            r.fail(f"Creator count out of sync", f"local={local_count:,} cloud={cloud_count:,} (diff {pct:.1f}%)")
    except Exception as e:
        r.fail("Sync comparison", str(e)[:100])
    
    # Check if platform_presences are synced (by checking a known creator)
    for tc in TEST_CREATORS:
        local_presences = conn.execute(
            "SELECT COUNT(*) FROM platform_presences WHERE creator_id = ?", (tc["id"],)
        ).fetchone()[0]
        
        try:
            _, data = fetch_json(f"{base}/api/creators/{tc['id']}")
            cloud_presences = len(data.get("platforms", []))
            
            if local_presences == cloud_presences:
                r.ok(f"{tc['name']}: presences synced ({local_presences})")
            elif cloud_presences > 0:
                r.warn(f"{tc['name']}: presence count differs", f"local={local_presences} cloud={cloud_presences}")
            else:
                r.fail(f"{tc['name']}: presences not synced", f"local={local_presences} cloud=0")
        except Exception as e:
            r.fail(f"{tc['name']}: sync check", str(e)[:100])
    
    # Check video enrichment progress
    local_with_videos = conn.execute(
        "SELECT COUNT(*) FROM platform_presences WHERE avg_views > 0 AND platform='tiktok'"
    ).fetchone()[0]
    local_total_tt = conn.execute(
        "SELECT COUNT(*) FROM platform_presences WHERE platform='tiktok'"
    ).fetchone()[0]
    
    if local_total_tt > 0:
        video_pct = local_with_videos / local_total_tt * 100
        r.ok(f"Video enrichment: {local_with_videos:,}/{local_total_tt:,} TikTok creators ({video_pct:.0f}%)")
    
    # Check top_content is populated
    local_with_top = conn.execute(
        "SELECT COUNT(*) FROM platform_presences WHERE top_content IS NOT NULL AND top_content != ''"
    ).fetchone()[0]
    if local_with_top > 0:
        r.ok(f"top_content populated: {local_with_top:,} presences")
    else:
        r.warn("top_content not populated", "Run top_content packer")
    
    conn.close()


def test_performance(base, r):
    """Test API response times."""
    print("\n⚡ Performance")
    
    endpoints = [
        ("/api/stats", "Stats", 3.0),
        ("/api/creators?country=MY&limit=20", "Creators list", 5.0),
        ("/api/suggest?q=khairul", "Suggest", 3.0),
        (f"/api/creators/{TEST_CREATORS[0]['id']}", "Creator detail", 5.0),
    ]
    
    for path, name, max_seconds in endpoints:
        try:
            start = time.time()
            fetch_json(f"{base}{path}")
            elapsed = time.time() - start
            
            if elapsed < max_seconds:
                r.ok(f"{name}: {elapsed:.2f}s")
            elif elapsed < max_seconds * 2:
                r.warn(f"{name}: slow ({elapsed:.2f}s)", f"Expected < {max_seconds}s")
            else:
                r.fail(f"{name}: too slow ({elapsed:.2f}s)", f"Expected < {max_seconds}s")
        except Exception as e:
            r.fail(f"{name}: timeout/error", str(e)[:100])


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="KolBuff QA Suite")
    parser.add_argument("--base", default=DEFAULT_BASE, help="Base URL to test")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()
    
    base = args.base.rstrip("/")
    
    print(f"{'='*60}")
    print(f"🧪 KOLBUFF QA SUITE")
    print(f"   Target: {base}")
    print(f"   Time: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}")
    
    r = QAResult()
    
    test_api_health(base, r)
    test_stats_integrity(base, r)
    test_creator_data(base, r)
    test_search(base, r)
    test_creators_list(base, r)
    test_data_integrity(base, r)
    test_pages(base, r)
    test_local_vs_cloud(base, r)
    test_performance(base, r)
    
    summary = r.summary()
    
    print(f"\n{'='*60}")
    print(f"📊 RESULTS: {r.passed} passed | {r.failed} failed | {r.warnings} warnings | {summary['elapsed_seconds']}s")
    if r.failed > 0:
        print(f"\n❌ FAILURES:")
        for t in summary["tests"]:
            if t["status"] == "FAIL":
                print(f"   • {t['name']}: {t['detail']}")
    if r.warnings > 0:
        print(f"\n⚠️  WARNINGS:")
        for t in summary["tests"]:
            if t["status"] == "WARN":
                print(f"   • {t['name']}: {t['detail']}")
    print(f"{'='*60}")
    
    # Save report
    try:
        os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
        with open(REPORT_PATH, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\nReport saved: {REPORT_PATH}")
    except:
        pass
    
    if args.json:
        print(json.dumps(summary, indent=2))
    
    sys.exit(1 if r.failed > 0 else 0)


if __name__ == "__main__":
    main()
