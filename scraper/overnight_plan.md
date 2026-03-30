# Overnight Scraping Plan (Mar 28 10PM → Mar 29 10AM)

## Strategy: Slow, accurate, expanding network

### Phase 1: Discovery Scraper (single agent)
- Start from 21 seed creators
- Visit each profile via Playwright
- Extract "suggested accounts" / related creators from TikTok's page
- For each discovered handle:
  1. Scrape full profile data
  2. Filter: must have 5k+ followers
  3. Detect SEA country from bio/language/profile signals
  4. Insert into DB
- Rate: ~1 profile per 5-6 seconds (safe, no blocking)
- Expected: ~500-700 profiles per hour

### Phase 2: Parallel scrapers (if Phase 1 stable after 1hr)
- Spawn 2nd scraper agent with different seed pool
- Each scraper works independently, checks DB before inserting (no dupes)
- Max 3 parallel scrapers to stay under TikTok's radar

### Phase 3: Periodic verifier
- Every 2 hours, spot-check 10 random DB entries
- Re-scrape those 10 profiles and compare
- Delete any that don't match
- Write verification log

### Country Detection Heuristic
Since TikTok doesn't expose country:
- Check bio language (Malay, Indonesian, Thai, Vietnamese, Tagalog)
- Check if handle appears in TikTok discover pages for specific countries
- Default to "SEA" if unclear, can be fixed later

### Safety
- 3-5 sec delay between scrapes
- New browser context every 100 profiles (avoid fingerprint bans)
- If blocked (empty responses 3x in a row), pause 5 min then retry
- All data saved to JSON backup before DB insert

### Targets
- By 10AM: 200+ verified real creators across SEA
- Country coverage: MY, ID, SG, TH, PH, VN
