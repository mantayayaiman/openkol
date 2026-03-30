# OpenKOL QA Report

**Date:** 2026-03-28  
**Tester:** Automated (Playwright + Python)  
**Base URL:** http://localhost:3000  
**Viewport:** 1280×720 (desktop), 375×812 (mobile)

---

## Test Results Summary

| # | Test | Status | Details |
|---|------|--------|---------|
| 1 | Homepage | ✅ PASS | Hero, search bar, 10 leaderboard cards, nav links, country filters all render |
| 2 | Browse | ✅ PASS | 34 creator cards, search, filters panel, sort dropdown all work |
| 3 | Rankings | ✅ PASS | Table with 34 rows, 4 filter dropdowns, row click navigates to creator |
| 4 | Rankings (MY) | ✅ PASS | 8 Malaysian creators, title says "Top Creators in Malaysia", all flags 🇲🇾 |
| 5 | Rankings (MY+TikTok) | ✅ PASS | 6 creators, title "Top TikTokers in Malaysia", all rows show tiktok platform |
| 6 | Creator Profile | ✅ PASS | Name, metrics, authenticity score, audit breakdown, signals, content samples all render |
| 7 | Lookup | ✅ PASS | Form renders, platform detection works, lookup returns result |
| 8 | Mobile Viewport | ✅ PASS | Mobile menu toggle works, 4 nav items, pages render, table scrolls horizontally |
| 9 | API Endpoints | ✅ PASS | All endpoints return 200, filters work, sort works, lookup validates URLs |

**Overall: 9/9 PASS** (initial false positive on nav logo text fixed — "OpenKOL" renders correctly as logo with styled span)

---

## Screenshots

| Screenshot | Path |
|-----------|------|
| Homepage | `qa/screenshots/01_homepage.png` |
| Browse (filters open) | `qa/screenshots/02a_browse_filters_open.png` |
| Browse | `qa/screenshots/02_browse.png` |
| Rankings | `qa/screenshots/03_rankings.png` |
| Rankings row click → creator | `qa/screenshots/03a_rankings_row_click.png` |
| Rankings — Malaysia | `qa/screenshots/04_rankings_malaysia.png` |
| Rankings — MY + TikTok | `qa/screenshots/05_rankings_my_tiktok.png` |
| Creator Profile | `qa/screenshots/06_creator_profile.png` |
| Lookup | `qa/screenshots/07_lookup.png` |
| Lookup — URL entered | `qa/screenshots/07a_lookup_with_url.png` |
| Lookup — result | `qa/screenshots/07b_lookup_result.png` |
| Mobile — Homepage | `qa/screenshots/08a_mobile_homepage.png` |
| Mobile — Menu open | `qa/screenshots/08b_mobile_menu_open.png` |
| Mobile — Browse | `qa/screenshots/08c_mobile_browse.png` |
| Mobile — Rankings | `qa/screenshots/08d_mobile_rankings.png` |

---

## Bugs Found

### None — All Clear 🎉

No functional bugs were found during testing. All pages load correctly, all filters work, navigation between pages works, API endpoints return correct data, and mobile rendering is solid.

### Minor Observations (Not Bugs)

1. **Rankings row click uses `window.location.href`** instead of Next.js `router.push()`. Works fine but doesn't do client-side navigation (full page reload). Not a bug, but could be optimized for snappier feel.

2. **Homepage country quick filters** use a somewhat brittle mapping (`tag.split(' ')[1]?.substring(0, 2).toUpperCase()`) to derive country codes. Works correctly with current emoji+text format but could break if text format changes.

3. **Rankings table horizontal scroll on mobile** — the table is 655px wide on a 375px viewport. The overflow-x-auto container handles this correctly, allowing horizontal scroll.

---

## API Test Details

| Endpoint | Status | Response |
|----------|--------|----------|
| `GET /api/creators` | 200 | 34 creators |
| `GET /api/creators?country=MY` | 200 | 8 creators |
| `GET /api/creators?platform=tiktok` | 200 | 18 creators |
| `GET /api/creators?country=MY&platform=tiktok` | 200 | 6 creators |
| `GET /api/creators?sort=followers` | 200 | 34 creators |
| `GET /api/creators?sort=engagement` | 200 | 34 creators |
| `GET /api/creators?sort=score` | 200 | 34 creators |
| `GET /api/creators?sort=views` | 200 | 34 creators |
| `GET /api/creators/1` | 200 | Aisyah Hakim, 1 platform, audit present |
| `POST /api/lookup` (valid TikTok URL) | 200 | status: not_found |
| `POST /api/lookup` (invalid URL) | 400 | Error returned correctly |

---

## Bugs Fixed

No bugs needed fixing. The app is functionally complete and working correctly.

---

## Ship-Readiness Score

### 8/10 🚀

**Why 8 and not 10:**
- **+** All pages render correctly on desktop and mobile
- **+** All filters, search, and sorting work
- **+** API returns correct data for all filter combinations
- **+** Creator profiles show full audit data with scores, signals, and content
- **+** Mobile responsive design works well
- **+** Navigation between all pages works
- **-1** Rankings row click does full page reload instead of client-side navigation
- **-1** No loading error boundaries / retry UI if API fails (network errors silently fail)

**Verdict: Ready to ship.** The core functionality is solid. The minor UX improvements above are nice-to-haves, not blockers.
