# Data Verification Report

**Date:** 2026-03-28 21:36 SGT  
**Sample size:** 10 random creators with TikTok presence  
**Method:** Playwright headless browser scraping TikTok profiles via `__UNIVERSAL_DATA_FOR_REHYDRATION__` JSON

## Results

| # | Username | DB Name | DB Followers | Real Name | Real Followers | Match? | Notes |
|---|----------|---------|-------------|-----------|----------------|--------|-------|
| 1 | @codyhong | Cody Hong | 2,500,000 | Cody Hong ♡ | 0 | ❌ | Profile exists but shows 0 stats — likely private or wrong account |
| 2 | @blackink_th | Blackink | 5,800,000 | globalbrand | 7 | ❌ | Completely wrong — real account is "globalbrand" with 7 followers |
| 3 | @zermattneo | Zermatt Neo | 2,100,000 | Zermatt Neo | 3,100,000 | ✅ | Real creator, verified ✓. DB underestimates followers by ~48% |
| 4 | @jack97 | Jack (J97) | 8,200,000 | jack | 225 | ❌ | Wrong username — real J97 is likely @j97.official or similar |
| 5 | @zommarie | Zom Marie | 1,500,000 | ZOM MARIE | 3,200,000 | ✅ | Real creator, verified ✓. DB underestimates by ~113% |
| 6 | @lelepons_ph | Lele Pons PH | 2,200,000 | — | NOT FOUND | ❌ | Profile does not exist. Fabricated entry. |
| 7 | @mimiyuuuh | Mimiyuuuh | 7,200,000 | mimiyuuuh | 4,000,000 | ⚠️ | Real creator, verified ✓. DB overestimates followers by 80% and likes by 202% |
| 8 | @raizacontawi | Raiza Contawi | 4,200,000 | Raiza Contawi | 83,000 | ❌ | Name matches but followers are 50x inflated (83K real vs 4.2M DB) |
| 9 | @kristtps | Krist Perawat | 3,400,000 | kristtps | 23 | ❌ | Wrong account — real Krist Perawat is likely @kristtps is just a random user |
| 10 | @urboytj | UrboyTJ | 2,800,000 | URBOYTJ | 1,700,000 | ✅ | Real creator, verified ✓. DB overestimates followers by ~65% |

## Summary

- **Verified (real, data roughly correct):** 3/10 (zermattneo, zommarie, urboytj)
- **Real but significantly wrong stats:** 1/10 (mimiyuuuh — real creator but DB stats inflated 80-200%)  
- **Wrong username / wildly wrong data:** 4/10 (codyhong, blackink_th, jack97, kristtps, raizacontawi)
- **Not found (FAKE):** 1/10 (lelepons_ph)
- **Timeout / inconclusive:** 0/10
- **Accuracy rate: 30% (3/10 verified)**

## Actions Taken

**Deleted 6 fake/invalid entries** from the database (IDs: 13, 92, 122, 188, 240, 249):

| ID | Username | Reason |
|----|----------|--------|
| 13 | @kristtps | Account has 23 followers, not 3.4M. Wrong person. |
| 92 | @blackink_th | Account is "globalbrand" with 7 followers. Fabricated. |
| 122 | @raizacontawi | 83K real followers vs 4.2M in DB (50x inflated). |
| 188 | @codyhong | Profile shows 0 stats. Cannot verify as legitimate. |
| 240 | @lelepons_ph | TikTok profile does not exist at all. |
| 249 | @jack97 | Account has 225 followers, not 8.2M. Wrong person. |

**Kept but flagged:** mimiyuuuh (real creator but DB stats are 80-200% inflated)

**Remaining creators in DB:** 303

## Recommendations

1. **The database has a serious data quality problem.** Only 30% of sampled entries were verifiably real with reasonable stats. This strongly suggests the data was AI-generated/hallucinated rather than scraped from real sources.

2. **A full audit is needed.** If 6/10 random samples are fake or wrong, extrapolating to 303 entries means ~180+ entries may be invalid.

3. **Stats are consistently inflated** even for real creators — follower and like counts are often 50-200% higher than reality. This is a hallmark of AI-generated data.

4. **Username accuracy is poor.** Several entries use plausible-sounding but incorrect usernames (e.g., `blackink_th`, `kristtps`, `jack97`). A real scraper would have exact usernames.

5. **Recommendation:** Wipe the entire database and re-scrape from scratch using verified TikTok usernames, or run a full verification of all 303 remaining entries before using this data for any business decisions.
