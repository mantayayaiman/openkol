#!/usr/bin/env python3
"""
OpenKOL QA Tests — Playwright browser-based testing
Tests every page: homepage, browse, rankings, creator profile, lookup
"""
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, ConsoleMessage

BASE_URL = "http://localhost:3000"
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

results = []
console_errors = []

def log(msg):
    print(f"  → {msg}")

def capture_console(msg: ConsoleMessage):
    if msg.type in ("error", "warning"):
        console_errors.append({
            "type": msg.type,
            "text": msg.text,
            "url": msg.location.get("url", "") if hasattr(msg, "location") else "",
        })

def screenshot(page: Page, name: str):
    path = SCREENSHOTS_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    log(f"Screenshot saved: {path.name}")
    return str(path)

def test_result(name, passed, details="", screenshot_path="", bugs=None):
    r = {
        "name": name,
        "passed": passed,
        "details": details,
        "screenshot": screenshot_path,
        "bugs": bugs or [],
    }
    results.append(r)
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n{status}: {name}")
    if details:
        log(details)
    if bugs:
        for b in bugs:
            log(f"BUG: {b}")
    return r


def test_homepage(page: Page):
    """Test 1: Homepage"""
    print("\n" + "="*60)
    print("TEST 1: Homepage (http://localhost:3000/)")
    print("="*60)
    
    console_errors.clear()
    page.on("console", capture_console)
    
    page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=30000)
    time.sleep(1)
    
    bugs = []
    
    # Check page title
    title = page.title()
    log(f"Page title: {title}")
    
    # Check search bar exists
    search_input = page.query_selector('input[placeholder*="Search"]')
    has_search = search_input is not None
    log(f"Search bar found: {has_search}")
    if not has_search:
        bugs.append("Search bar not found on homepage")
    
    # Check nav links
    nav_links = page.query_selector_all("nav a")
    nav_texts = [link.inner_text().strip() for link in nav_links]
    log(f"Nav links: {nav_texts}")
    
    expected_nav = ["OpenKOL", "Browse", "Rankings", "Lookup"]
    for expected in expected_nav:
        if not any(expected in t for t in nav_texts):
            bugs.append(f"Missing nav link: {expected}")
    
    # Check leaderboard cards render
    leaderboard_links = page.query_selector_all('section a[href*="/rankings"]')
    log(f"Leaderboard cards found: {len(leaderboard_links)}")
    if len(leaderboard_links) < 5:
        bugs.append(f"Expected at least 5 leaderboard cards, found {len(leaderboard_links)}")
    
    # Check hero text
    hero = page.query_selector("h1")
    hero_text = hero.inner_text() if hero else ""
    log(f"Hero text: {hero_text[:50]}...")
    
    # Check country quick filters
    country_btns = page.query_selector_all('button:has-text("Malaysia"), button:has-text("Indonesia"), button:has-text("Thailand")')
    log(f"Country quick filters found: {len(country_btns)}")
    
    # Check for console errors
    errors = [e for e in console_errors if e["type"] == "error"]
    if errors:
        bugs.append(f"Console errors: {len(errors)} - {errors[0]['text'][:100]}")
    
    ss = screenshot(page, "01_homepage")
    
    # Test search functionality
    if search_input:
        search_input.fill("test creator")
        page.keyboard.press("Enter")
        page.wait_for_url("**/browse**", timeout=5000)
        log(f"Search redirected to: {page.url}")
        page.go_back(wait_until="networkidle")
    
    test_result(
        "Homepage",
        len(bugs) == 0,
        f"Title: {title}, Search: {has_search}, Leaderboards: {len(leaderboard_links)}, Nav: {len(nav_links)}",
        ss,
        bugs,
    )


def test_browse(page: Page):
    """Test 2: Browse page"""
    print("\n" + "="*60)
    print("TEST 2: Browse (http://localhost:3000/browse)")
    print("="*60)
    
    console_errors.clear()
    
    page.goto(f"{BASE_URL}/browse", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)  # Wait for API call
    
    bugs = []
    
    # Check heading
    heading = page.query_selector("h1")
    heading_text = heading.inner_text() if heading else ""
    log(f"Heading: {heading_text}")
    
    # Check search input
    search = page.query_selector('input[placeholder*="Search"]')
    log(f"Search input: {search is not None}")
    
    # Check filters button
    filters_btn = page.query_selector('button:has-text("Filters")')
    log(f"Filters button: {filters_btn is not None}")
    
    # Check creator cards loaded
    cards = page.query_selector_all('a[href*="/creator/"]')
    log(f"Creator cards found: {len(cards)}")
    if len(cards) == 0:
        bugs.append("No creator cards rendered on browse page")
    
    # Check results count
    results_text = page.query_selector('div:has-text("found")')
    if results_text:
        log("Results text visible")
    
    # Click filters button to open panel
    if filters_btn:
        filters_btn.click()
        page.wait_for_timeout(500)
        
        # Check filter options exist
        country_filters = page.query_selector_all('button:has-text("Malaysia")')
        platform_filters = page.query_selector_all('button:has-text("TikTok")')
        log(f"Country filters visible: {len(country_filters) > 0}")
        log(f"Platform filters visible: {len(platform_filters) > 0}")
        
        screenshot(page, "02a_browse_filters_open")
    
    # Sort dropdown
    sort_select = page.query_selector('select')
    log(f"Sort dropdown: {sort_select is not None}")
    
    ss = screenshot(page, "02_browse")
    
    # Test clicking a creator card
    if cards:
        first_card = cards[0]
        href = first_card.get_attribute("href")
        log(f"First card href: {href}")
        if href and "/creator/" in href:
            log("Creator card link looks correct")
        else:
            bugs.append(f"Creator card has unexpected href: {href}")
    
    test_result(
        "Browse Page",
        len(bugs) == 0,
        f"Cards: {len(cards)}, Search: {search is not None}, Filters: {filters_btn is not None}",
        ss,
        bugs,
    )


def test_rankings(page: Page):
    """Test 3: Rankings page"""
    print("\n" + "="*60)
    print("TEST 3: Rankings (http://localhost:3000/rankings)")
    print("="*60)
    
    console_errors.clear()
    
    page.goto(f"{BASE_URL}/rankings", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    
    bugs = []
    
    # Check heading
    heading = page.query_selector("h1")
    heading_text = heading.inner_text() if heading else ""
    log(f"Heading: {heading_text}")
    
    # Check table renders with actual data (NOT just skeleton)
    table = page.query_selector("table")
    has_table = table is not None
    log(f"Table found: {has_table}")
    
    if has_table:
        rows = page.query_selector_all("table tbody tr")
        log(f"Table rows: {len(rows)}")
        if len(rows) == 0:
            bugs.append("Rankings table is empty (no data rows)")
        else:
            # Check first row has actual content
            first_row = rows[0]
            cells = first_row.query_selector_all("td")
            log(f"First row cells: {len(cells)}")
            if cells:
                name_cell = cells[1].inner_text() if len(cells) > 1 else ""
                log(f"First creator: {name_cell[:30]}")
    else:
        # Check if still showing skeleton
        skeletons = page.query_selector_all(".animate-pulse")
        if skeletons:
            bugs.append("Rankings showing skeleton loading, not actual data")
        else:
            bugs.append("No table found on rankings page")
    
    # Check filter dropdowns
    selects = page.query_selector_all("select")
    log(f"Filter dropdowns: {len(selects)}")
    if len(selects) < 3:
        bugs.append(f"Expected at least 3 filter dropdowns, found {len(selects)}")
    
    # Check for trophy icon
    page.query_selector("svg")  # Trophy icon should be in heading
    
    ss = screenshot(page, "03_rankings")
    
    # Test clicking a row navigates to creator page
    if has_table:
        rows = page.query_selector_all("table tbody tr")
        if rows:
            # Click first row
            rows[0].click()
            page.wait_for_timeout(1000)
            current_url = page.url
            log(f"After clicking row, URL: {current_url}")
            if "/creator/" not in current_url:
                bugs.append(f"Clicking ranking row did not navigate to creator page (URL: {current_url})")
            else:
                screenshot(page, "03a_rankings_row_click")
            page.go_back(wait_until="networkidle")
            page.wait_for_timeout(1000)
    
    test_result(
        "Rankings Page",
        len(bugs) == 0,
        f"Table: {has_table}, Rows: {len(rows) if has_table else 0}, Filters: {len(selects)}",
        ss,
        bugs,
    )


def test_rankings_malaysia(page: Page):
    """Test 4: Rankings filtered by Malaysia"""
    print("\n" + "="*60)
    print("TEST 4: Rankings - Malaysia (country=MY)")
    print("="*60)
    
    console_errors.clear()
    
    page.goto(f"{BASE_URL}/rankings?country=MY", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    
    bugs = []
    
    # Check title says Malaysia
    heading = page.query_selector("h1")
    heading_text = heading.inner_text() if heading else ""
    log(f"Heading: {heading_text}")
    
    if "Malaysia" not in heading_text:
        bugs.append(f"Title does not mention Malaysia: '{heading_text}'")
    
    # Check table has data
    rows = page.query_selector_all("table tbody tr")
    log(f"Malaysian creators: {len(rows)}")
    if len(rows) == 0:
        bugs.append("No Malaysian creators found")
    
    # Check country flags are all MY
    flags = page.query_selector_all("table tbody td:last-child")
    for flag in flags[:3]:
        flag_text = flag.inner_text().strip()
        log(f"Flag: {flag_text}")
    
    # Check country filter dropdown shows MY selected
    country_select = page.query_selector("select")
    if country_select:
        selected_value = country_select.input_value()
        log(f"Country filter value: {selected_value}")
    
    ss = screenshot(page, "04_rankings_malaysia")
    
    test_result(
        "Rankings - Malaysia Filter",
        len(bugs) == 0,
        f"Title: {heading_text}, Rows: {len(rows)}",
        ss,
        bugs,
    )


def test_rankings_malaysia_tiktok(page: Page):
    """Test 5: Rankings filtered by Malaysia + TikTok"""
    print("\n" + "="*60)
    print("TEST 5: Rankings - MY + TikTok")
    print("="*60)
    
    console_errors.clear()
    
    page.goto(f"{BASE_URL}/rankings?country=MY&platform=tiktok", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    
    bugs = []
    
    heading = page.query_selector("h1")
    heading_text = heading.inner_text() if heading else ""
    log(f"Heading: {heading_text}")
    
    # Should mention TikTokers and Malaysia
    if "Malaysia" not in heading_text:
        bugs.append(f"Title missing Malaysia: '{heading_text}'")
    if "TikTok" not in heading_text:
        bugs.append(f"Title missing TikTok reference: '{heading_text}'")
    
    rows = page.query_selector_all("table tbody tr")
    log(f"MY TikTok creators: {len(rows)}")
    
    # Check all rows show tiktok platform
    for row in rows[:3]:
        cells = row.query_selector_all("td")
        if len(cells) > 1:
            platform_text = cells[1].inner_text()
            log(f"Row platform info: {platform_text[:40]}")
            if "tiktok" not in platform_text.lower():
                bugs.append(f"Non-TikTok creator in filtered results: {platform_text[:40]}")
    
    ss = screenshot(page, "05_rankings_my_tiktok")
    
    test_result(
        "Rankings - MY + TikTok Filter",
        len(bugs) == 0,
        f"Title: {heading_text}, Rows: {len(rows)}",
        ss,
        bugs,
    )


def test_creator_profile(page: Page):
    """Test 6: Creator profile page"""
    print("\n" + "="*60)
    print("TEST 6: Creator Profile (/creator/1)")
    print("="*60)
    
    console_errors.clear()
    
    page.goto(f"{BASE_URL}/creator/1", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    
    bugs = []
    
    # Check if "Creator not found" is showing
    not_found = page.query_selector('h2:has-text("Creator not found")')
    if not_found:
        bugs.append("Creator 1 not found - API returned no data")
        ss = screenshot(page, "06_creator_not_found")
        test_result("Creator Profile", False, "Creator not found", ss, bugs)
        return
    
    # Check creator name
    name = page.query_selector("h1")
    name_text = name.inner_text() if name else ""
    log(f"Creator name: {name_text}")
    if not name_text:
        bugs.append("Creator name not displayed")
    
    # Check metrics cards
    metric_cards = page.query_selector_all('div:has-text("Followers"), div:has-text("Avg Views"), div:has-text("Engagement")')
    log(f"Metric sections found: {len(metric_cards)}")
    
    # Check authenticity score badge
    score_badge = page.query_selector('div:has-text("Authenticity Score")')
    has_score = score_badge is not None
    log(f"Authenticity score visible: {has_score}")
    if not has_score:
        bugs.append("Authenticity score not visible on creator profile")
    
    # Check audit breakdown section
    audit_section = page.query_selector('h2:has-text("Authenticity Breakdown")')
    has_audit = audit_section is not None
    log(f"Audit breakdown section: {has_audit}")
    
    # Check signals/red flags section
    signals_section = page.query_selector('h2:has-text("Signals")')
    has_signals = signals_section is not None
    log(f"Signals section: {has_signals}")
    
    # Check platform links
    platform_links = page.query_selector_all('a[target="_blank"]')
    log(f"External platform links: {len(platform_links)}")
    
    # Check back button
    back_link = page.query_selector('a:has-text("Back")')
    log(f"Back button: {back_link is not None}")
    
    # Check profile image
    profile_img = page.query_selector("img")
    log(f"Profile image: {profile_img is not None}")
    
    ss = screenshot(page, "06_creator_profile")
    
    # Check content samples table
    content_table = page.query_selector('h2:has-text("Recent Content")')
    log(f"Recent content section: {content_table is not None}")
    
    test_result(
        "Creator Profile",
        len(bugs) == 0,
        f"Name: {name_text}, Score: {has_score}, Audit: {has_audit}, Signals: {has_signals}",
        ss,
        bugs,
    )


def test_lookup(page: Page):
    """Test 7: Lookup page"""
    print("\n" + "="*60)
    print("TEST 7: Lookup (http://localhost:3000/lookup)")
    print("="*60)
    
    console_errors.clear()
    
    page.goto(f"{BASE_URL}/lookup", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(1000)
    
    bugs = []
    
    # Check heading
    heading = page.query_selector("h1")
    heading_text = heading.inner_text() if heading else ""
    log(f"Heading: {heading_text}")
    if "Lookup" not in heading_text:
        bugs.append(f"Heading doesn't mention Lookup: {heading_text}")
    
    # Check input form
    input_field = page.query_selector('input[placeholder*="tiktok"]')
    has_input = input_field is not None
    log(f"URL input field: {has_input}")
    if not has_input:
        bugs.append("Lookup URL input not found")
    
    # Check lookup button
    lookup_btn = page.query_selector('button:has-text("Lookup")')
    has_btn = lookup_btn is not None
    log(f"Lookup button: {has_btn}")
    
    # Check supported formats section
    formats = page.query_selector('h3:has-text("Supported formats")')
    log(f"Supported formats section: {formats is not None}")
    
    ss = screenshot(page, "07_lookup")
    
    # Test lookup with a URL
    if input_field:
        input_field.fill("https://tiktok.com/@testuser")
        page.wait_for_timeout(500)
        
        # Check platform detection
        detected = page.query_selector('span:has-text("detected")')
        if detected:
            log(f"Platform detection: {detected.inner_text()}")
        
        screenshot(page, "07a_lookup_with_url")
        
        # Submit the form
        if lookup_btn:
            lookup_btn.click()
            page.wait_for_timeout(2000)
            
            # Check for result (either found or not found)
            result = page.query_selector('h2:has-text("Lookup Result")')
            error = page.query_selector('h3:has-text("Lookup failed")')
            
            if result:
                log("Lookup returned a result")
                screenshot(page, "07b_lookup_result")
            elif error:
                log("Lookup returned an error")
            else:
                log("No visible result after lookup")
    
    test_result(
        "Lookup Page",
        len(bugs) == 0,
        f"Heading: {heading_text}, Input: {has_input}, Button: {has_btn}",
        ss,
        bugs,
    )


def test_mobile_viewport(page: Page):
    """Test 8: Mobile viewport rendering"""
    print("\n" + "="*60)
    print("TEST 8: Mobile Viewport (375x812)")
    print("="*60)
    
    page.set_viewport_size({"width": 375, "height": 812})
    
    bugs = []
    
    # Homepage mobile
    page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(1000)
    
    # Check mobile menu toggle
    mobile_toggle = page.query_selector('button:has(svg)')
    log(f"Mobile menu toggle: {mobile_toggle is not None}")
    
    # Check hero is visible
    hero = page.query_selector("h1")
    hero_visible = hero.is_visible() if hero else False
    log(f"Hero visible on mobile: {hero_visible}")
    
    ss1 = screenshot(page, "08a_mobile_homepage")
    
    # Check mobile menu works
    if mobile_toggle:
        mobile_toggle.click()
        page.wait_for_timeout(500)
        mobile_nav = page.query_selector_all('div.sm\\:hidden a')
        log(f"Mobile nav items: {len(mobile_nav)}")
        screenshot(page, "08b_mobile_menu_open")
    
    # Browse on mobile
    page.goto(f"{BASE_URL}/browse", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    screenshot(page, "08c_mobile_browse")
    
    # Rankings on mobile
    page.goto(f"{BASE_URL}/rankings", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    screenshot(page, "08d_mobile_rankings")
    
    # Check horizontal scroll on rankings table
    table = page.query_selector("table")
    if table:
        table_width = table.evaluate("el => el.scrollWidth")
        viewport_width = 375
        log(f"Table scroll width: {table_width}, viewport: {viewport_width}")
        if table_width > viewport_width + 50:
            log("Table is horizontally scrollable (good)")
    
    # Reset viewport
    page.set_viewport_size({"width": 1280, "height": 720})
    
    test_result(
        "Mobile Viewport",
        len(bugs) == 0,
        "Mobile menu: OK, Pages render on mobile",
        ss1,
        bugs,
    )


def test_api_endpoints(page: Page):
    """Test 9: API endpoints directly"""
    print("\n" + "="*60)
    print("TEST 9: API Endpoints")
    print("="*60)
    
    bugs = []
    
    # Test /api/creators
    resp = page.request.get(f"{BASE_URL}/api/creators")
    data = resp.json()
    log(f"GET /api/creators — status: {resp.status}, creators: {len(data.get('creators', []))}, total: {data.get('total', 0)}")
    if resp.status != 200:
        bugs.append(f"/api/creators returned {resp.status}")
    if len(data.get("creators", [])) == 0:
        bugs.append("/api/creators returned no creators")
    
    # Test with country filter
    resp = page.request.get(f"{BASE_URL}/api/creators?country=MY")
    data = resp.json()
    log(f"GET /api/creators?country=MY — creators: {len(data.get('creators', []))}")
    
    # Test with platform filter
    resp = page.request.get(f"{BASE_URL}/api/creators?platform=tiktok")
    data = resp.json()
    log(f"GET /api/creators?platform=tiktok — creators: {len(data.get('creators', []))}")
    
    # Test with combined filters
    resp = page.request.get(f"{BASE_URL}/api/creators?country=MY&platform=tiktok")
    data = resp.json()
    log(f"GET /api/creators?country=MY&platform=tiktok — creators: {len(data.get('creators', []))}")
    
    # Test /api/creators/1
    resp = page.request.get(f"{BASE_URL}/api/creators/1")
    log(f"GET /api/creators/1 — status: {resp.status}")
    if resp.status == 200:
        creator = resp.json()
        log(f"Creator 1: {creator.get('name', 'N/A')}, platforms: {len(creator.get('platforms', []))}")
        has_audit = creator.get("audit") is not None
        log(f"Has audit: {has_audit}")
    elif resp.status == 404:
        bugs.append("Creator ID 1 not found in database")
    
    # Test /api/lookup
    resp = page.request.post(f"{BASE_URL}/api/lookup", data=json.dumps({"url": "https://tiktok.com/@testuser"}), headers={"Content-Type": "application/json"})
    lookup_data = resp.json()
    log(f"POST /api/lookup — status: {resp.status}, result: {lookup_data.get('status', 'N/A')}")
    
    # Test invalid lookup
    resp = page.request.post(f"{BASE_URL}/api/lookup", data=json.dumps({"url": "not-a-url"}), headers={"Content-Type": "application/json"})
    log(f"POST /api/lookup (invalid) — status: {resp.status}")
    
    # Test sort options
    for sort_by in ["followers", "engagement", "score", "views"]:
        resp = page.request.get(f"{BASE_URL}/api/creators?sort={sort_by}")
        data = resp.json()
        log(f"GET /api/creators?sort={sort_by} — creators: {len(data.get('creators', []))}")
    
    test_result(
        "API Endpoints",
        len(bugs) == 0,
        "All API endpoints responding correctly",
        "",
        bugs,
    )


def run_all_tests():
    print("🧪 OpenKOL QA Test Suite")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True,
        )
        page = context.new_page()
        
        try:
            test_homepage(page)
            test_browse(page)
            test_rankings(page)
            test_rankings_malaysia(page)
            test_rankings_malaysia_tiktok(page)
            test_creator_profile(page)
            test_lookup(page)
            test_mobile_viewport(page)
            test_api_endpoints(page)
        except Exception as e:
            print(f"\n💥 FATAL ERROR: {e}")
            screenshot(page, "fatal_error")
            raise
        finally:
            browser.close()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])
    total = len(results)
    
    for r in results:
        status = "✅" if r["passed"] else "❌"
        print(f"  {status} {r['name']}")
        for bug in r.get("bugs", []):
            print(f"     🐛 {bug}")
    
    print(f"\n  Results: {passed}/{total} passed, {failed} failed")
    
    # Write JSON results
    results_path = SCREENSHOTS_DIR.parent / "test_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to: {results_path}")
    
    return results


if __name__ == "__main__":
    run_all_tests()
