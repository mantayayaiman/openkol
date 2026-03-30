# OpenKOL Product Plan — Post-MVP Roadmap

## Context
OpenKOL is an AI-powered creator discovery and analytics platform for Southeast Asia. We built the MVP in 48 hours. Now we need to go from demo to product.

**Current state:** 20,000+ creators, 4 platforms (TikTok/IG/YT/FB), 6 SEA countries, authenticity scoring, interactive filter UI.

**Parent company:** MantaYaY — Malaysia's leading TikTok MCN with 4,000+ managed creators, RM40M revenue.

**Competitive landscape:** HypeAuditor ($300+/mo, global, best fraud detection), Kalodata (TikTok Shop focused), FastMoss (TikTok analytics), NoxInfluencer (YouTube focused), SocialBlade (free stats).

## Problem Statement
Brands and agencies in SEA need to find and vet creators for campaigns. Current tools are either too expensive (HypeAuditor), not SEA-focused (SocialBlade), or TikTok-Shop-only (Kalodata). OpenKOL aims to be the affordable, SEA-first creator intelligence platform.

## Target Users
1. **Primary:** Brand marketers in SEA running influencer campaigns
2. **Secondary:** Agencies managing creator campaigns for brands
3. **Internal:** MantaYaY's own sales team (pitch creators to brands)

## Phase 0: Foundation (Week 1-2) — BLOCKING ADOPTION

### 0.1 Export & Shortlist System
- [ ] "Add to shortlist" button on creator cards and profiles
- [ ] Shortlist management page (view, remove, reorder)
- [ ] Export shortlist to CSV (name, handle, followers, ER, country, category, profile URL)
- [ ] Export shortlist to PDF (branded report with creator cards)
- **Why:** Brands work in spreadsheets. If they can't export data, they won't use the product.

### 0.2 Search & Discovery Improvements
- [ ] Full-text search across creator names, bios, usernames
- [ ] Multi-select filters (e.g., select MY + ID + SG at once)
- [ ] Follower range slider (not just tier pills)
- [ ] Engagement rate range filter
- [ ] Sort by multiple criteria
- **Why:** Current discovery is too basic. Brands need precise filtering.

### 0.3 Data Freshness & Quality
- [ ] "Last updated" timestamp on every creator profile
- [ ] Fix remaining country misclassifications (9,000+ "SEA" tagged creators)
- [ ] Store TikTok UIDs for all creators (username changes break tracking)
- [ ] Automated weekly re-scrape of top 5,000 creators
- [ ] Data staleness warning if >30 days old
- **Why:** Stale data = zero trust. A creator showing 500K followers who now has 2M is useless.

### 0.4 Creator Profile Enrichment
- [ ] Contact info section (email from bio, management contact)
- [ ] Cross-platform linked profiles (show all platforms on one page)
- [ ] Recent videos with views/likes/comments (need video scraping solution)
- [ ] "Similar creators" recommendations
- **Why:** Profile page is the conversion point. If it's thin, users bounce.

## Phase 1: Competitive Parity (Week 3-6)

### 1.1 Audience Demographics (Estimated)
- [ ] Gender split estimate (from bio keywords, content type, engagement patterns)
- [ ] Age range estimate (from content style, language, topics)
- [ ] Geographic audience distribution (from comment language analysis)
- [ ] "Audience quality" indicator (bot detection via follower analysis)
- **Why:** THE #1 thing brands ask for. "What % of this creator's audience is female, 18-34, in Malaysia?"

### 1.2 Growth & Trend Analytics
- [ ] Historical follower chart (track daily/weekly snapshots)
- [ ] Follower growth rate (30-day, 90-day)
- [ ] "Breakout" score — creators growing fastest relative to their size
- [ ] Engagement trend (is ER going up or down?)
- **Why:** Static snapshots are useless for campaign planning. Brands want trajectory.

### 1.3 Content Analytics
- [ ] Recent 20 videos with individual performance metrics
- [ ] Best-performing content identification
- [ ] Content frequency analysis (posts per week)
- [ ] Hashtag analysis (what topics they cover)
- [ ] Posting time patterns
- **Why:** Brands evaluate creators by their content, not just numbers.

### 1.4 Campaign Pricing Estimates
- [ ] Estimated cost per post (based on follower count + ER + category)
- [ ] CPM estimates (cost per thousand views)
- [ ] Rate card suggestions (video, livestream, story, bundle)
- [ ] MantaYaY insider pricing for managed creators
- **Why:** Budget planning is critical. "Is this creator worth $5K or $500?"

## Phase 2: Differentiation (Week 7-12)

### 2.1 Campaign Management
- [ ] Create campaign with brief, budget, timeline
- [ ] Add creators to campaign
- [ ] Track campaign status (contacted, confirmed, posted, completed)
- [ ] Campaign analytics (total reach, engagement, cost)
- **Why:** End-to-end workflow keeps users in our platform.

### 2.2 API Access
- [ ] REST API for creator search
- [ ] Webhook for creator data updates
- [ ] Integration with popular marketing tools
- **Why:** Agencies with custom workflows need programmatic access.

### 2.3 Brand Collaboration Detection
- [ ] Detect sponsored content in recent posts (hashtag analysis)
- [ ] Show which brands a creator has worked with
- [ ] Competitor campaign tracking
- **Why:** "Has this creator worked with our competitor?" is a key brand question.

### 2.4 AI-Powered Features
- [ ] AI creator recommendation engine ("find me 10 food creators in MY with 50K-200K followers")
- [ ] Natural language search ("show me rising gaming creators in Indonesia")
- [ ] Automated campaign brief matching
- **Why:** AI differentiator that pure data tools can't replicate easily.

## Technical Debt
- [ ] Migrate from SQLite to PostgreSQL (scaling)
- [ ] Add Redis caching for API responses
- [ ] CDN for creator avatar images (currently hotlinking TikTok CDN)
- [ ] User authentication system (currently no login)
- [ ] Rate limiting on API endpoints
- [ ] Proper error handling and monitoring

## Success Metrics
- Phase 0: 10 beta users (MantaYaY sales team) actively using daily
- Phase 1: 50 external users, 5 paying customers
- Phase 2: 200 users, $5K MRR

## Unfair Advantages
1. **MantaYaY network** — 4,000 managed creators = ground truth data + captive first customer
2. **SEA focus** — competitors are global/diluted, we go deep on 6 countries
3. **Aiman (AI cofounder)** — 24/7 autonomous development, scraping, data enrichment
4. **Pricing** — free tier + affordable paid vs $300+/mo incumbents

---

## GSTACK AUTOPLAN REVIEW REPORT

**Reviewed:** 2026-03-29T22:31:00+08:00
**Mode:** SELECTIVE EXPANSION (autoplan, auto-decided)
**Reviewer:** Aiman (AI cofounder) via /autoplan pipeline
**Plan file:** .gstack/plan.md
**Codebase examined:** 18 TypeScript files, 40+ Python scrapers, kreator.db (21,426 creators)

---

### PHASE 1: CEO REVIEW (Strategy & Scope)

#### 0A. Premise Challenge

**Premise 1: "Brands and agencies in SEA need an affordable creator discovery tool."**
Status: VALID but incomplete. The competitive analysis confirms HypeAuditor at $300+/mo prices out most SEA agencies. But the premise skips a step. Brands don't just need *discovery*, they need *workflow*. Discovery without export/shortlist/outreach is a Wikipedia article about creators, not a tool. The plan's Phase 0 recognizes this (export, shortlists), which is good instinct.

**Premise 2: "SEA focus is a differentiator."**
Status: PARTIALLY VALID. HypeAuditor and NoxInfluencer already cover SEA. "SEA focus" alone is not a moat. But "SEA focus + MCN ground truth + affordable pricing + authenticity scoring" as a bundle IS differentiated. The plan doesn't articulate this bundle clearly enough. The positioning should be: "Built by an MCN that runs 4,000 creators in SEA. We don't just have data, we have campaign results to calibrate against."

**Premise 3: "We can compete with 21K creators vs HypeAuditor's 223M."**
Status: RISKY. The gap is 10,000x. But the plan's implicit strategy is correct: go deep on SEA, not wide on the world. 50K deeply profiled SEA creators with audience estimates beats 223M global entries with surface metrics. The plan should explicitly state a target: **50K SEA creators by end of Phase 1, 100K by end of Phase 2.**

**Premise 4: "SQLite is sufficient for now."**
Status: VALID for Phase 0-1, RISKY for Phase 2. At 21K creators, SQLite is fine. At 100K with concurrent API users, WAL mode handles reads well. The plan correctly defers PostgreSQL migration to tech debt, but should set a trigger: "Migrate when concurrent users > 20 or DB > 2GB."

**Premise 5: "MVP built in 48 hours means we can iterate fast."**
Status: TRUE. The codebase is clean, small (18 .ts/.tsx files), and well-structured. No test debt because there are no tests. No framework lock-in. This is actually a strength, not just a claim.

#### 0B. Existing Code Leverage

```
SUB-PROBLEM                    → EXISTING CODE
─────────────────────────────────────────────────────────
Creator search/filter          → /api/creators route.ts (working, has tier/country/platform/category/search)
Creator profiles               → /creator/[id]/page.tsx (working, shows metrics + audit scores)
Authenticity scoring           → audit_scores table + ScoreBadge component (11,202 scored)
Multi-platform presence        → platform_presences table (22,873 entries)
Content samples schema         → content_samples table (EXISTS but 0 rows)
Metrics history schema         → metrics_history table (EXISTS but 0 rows)
Category filtering             → categoryMap in route.ts (15 categories mapped)
Python scraping infra          → 40+ scraper files (TikTok, IG, YT, FB)
```

Key finding: content_samples and metrics_history tables already exist in the schema but have 0 rows. The plan's Phase 0.3 and Phase 1.2 can leverage existing schema, just need data pipeline work.

#### 0C. Dream State Mapping

```
CURRENT STATE                    THIS PLAN                    12-MONTH IDEAL
─────────────────────────────    ──────────────────────        ──────────────────
21K creators                     50K+ SEA creators            200K+ SEA creators
0 content samples                Recent 20 videos/creator     Full content library
0 metrics history                30/90-day growth charts      2-year time series
No export                        CSV + PDF export             White-label reports
No auth                          Basic auth system            SSO + team workspaces
No audience data                 Estimated demographics       ML-calibrated demographics
No campaign tools                Basic campaign tracking       Full campaign CRM
SQLite                           SQLite (fine)                PostgreSQL + Redis
No API                           REST API                     GraphQL + webhooks
No pricing data                  Estimated pricing            MantaYaY-calibrated rates
```

The plan covers roughly 60% of the gap between current state and 12-month ideal. That's appropriate for a 12-week roadmap.

#### 0C-bis. Implementation Alternatives

**APPROACH A: Feature-First (Current Plan)**
  Summary: Build features in order of user workflow (export → search → data → analytics)
  Effort: L (12 weeks)
  Risk: Medium, data freshness could block adoption even with features
  Pros: Follows user journey, each phase delivers usable value
  Cons: Data quality debt compounds while building features

**APPROACH B: Data-First**
  Summary: Spend weeks 1-4 entirely on data pipeline (scraping, demographics, content), then build features on rich data
  Effort: L (12 weeks)
  Risk: Low technical, high business (no user-facing progress for 4 weeks)
  Pros: Every feature built on solid data from day 1
  Cons: Internal stakeholders (MantaYaY sales team) waiting longer

**APPROACH C: Hybrid (RECOMMENDED)**
  Summary: Week 1-2 ship export + shortlist (immediate value). Parallel: aggressive data enrichment pipeline. Week 3-6 build features on enriched data.
  Effort: L (12 weeks)
  Risk: Low, parallel tracks maximize throughput
  Pros: Immediate user value AND data quality improves simultaneously
  Cons: Requires managing two parallel workstreams

Auto-decision (P1 completeness + P3 pragmatic): **APPROACH C**. The plan already roughly follows this, but should explicitly call out the parallel data enrichment track.

#### CEO Review Sections Summary

**Section 1 (Architecture):** Current architecture is clean but missing auth, caching, and rate limiting. No single point of failure (SQLite WAL handles concurrent reads). The scraper → DB → API → UI pipeline is straightforward. **1 issue: no auth system means anyone can hit the API.**

**Section 2 (Error/Rescue Map):** 
```
METHOD/CODEPATH              | WHAT CAN GO WRONG           | RESCUED?
────────────────────────────|───────────────────────────── |──────────
/api/creators GET            | SQLite locked                | N ← GAP
                             | Invalid params               | Partial (no validation)
                             | Too many results             | Y (LIMIT 100)
/api/creators/[id] GET       | Creator not found            | Y (returns null)
                             | SQLite locked                | N ← GAP
fetch() in browse page       | Network error                | Y (catch block, console.error)
                             | API returns 500              | N ← GAP (no user message)
Image loading (profile pics) | TikTok CDN blocks hotlink    | N ← GAP (broken images)
Python scrapers              | Rate limiting/bans           | Partial (anti_detect.py)
                             | Invalid/changed HTML         | N ← GAP
```
**3 CRITICAL GAPS:** No error boundaries in the React app. No input validation on API params. No CDN for creator images (hotlinking TikTok CDN will break).

**Section 3 (Security):** No auth = no authorization = anyone can scrape your entire DB via the API. This is fine for internal MVP but MUST be in Phase 0 for external launch. SQL injection risk is LOW (using parameterized queries via better-sqlite3). No rate limiting. No CORS restrictions.

**Section 4 (Data Flow):** Happy path works. Nil path: creator with no platform_presences shows empty metrics (handled). Error path: API failures show nothing to user (console.error only). Empty path: zero results shows... nothing. No empty state component.

**Section 5 (Code Quality):** Clean code. Good use of TypeScript. Some `any` types in page components (browse, home, creator detail). CountryFlags and platformColors are duplicated across 3+ files. No shared constants file for these.

**Section 6 (Tests):** Zero tests. No test framework. No CI. This is the biggest gap.

**Section 7 (Performance):** Main query in /api/creators does a 3-way JOIN (creators + platform_presences + audit_scores) with LIKE queries on search. At 21K rows, this is fine. At 100K+ it'll be slow without full-text search. The LIKE '%search%' pattern can't use indexes.

**Section 8 (Observability):** Zero logging, zero metrics, zero alerts. console.error is the entire observability story.

**Section 9 (Deployment):** Plan doesn't specify deployment strategy at all. Where does this run? Vercel? VPS? The SQLite dependency means it can't run on serverless without changes.

**Section 10 (Long-Term):** Good trajectory. The schema is forward-compatible. The scraper infra is solid. The main risk is data staleness if scraping isn't automated.

**Section 11 (Design/UX):** UI scope detected. Dark theme, responsive, clean. But: no empty states, no loading skeletons on browse page (just missing), no error states visible to users. The homepage has a nice hero but the browse → profile flow is the real product. Profile page is the strongest page (authenticity breakdown with progress bars is excellent). Info hierarchy is reasonable: filters → cards → detail. Missing: mobile nav behavior, no skip nav for accessibility.

#### CEO Phase Decision Log

| # | Decision | Principle | Rationale |
|---|----------|-----------|-----------|
| 1 | Mode: SELECTIVE EXPANSION | P6 bias toward action | Plan is well-scoped, just needs gaps filled |
| 2 | Approach C (Hybrid) | P1 completeness + P3 pragmatic | Parallel data + features maximizes throughput |
| 3 | Add auth to Phase 0 | P1 completeness | Can't launch externally without auth |
| 4 | Add CDN for images | P3 pragmatic | Hotlinking will break, cheap to fix |
| 5 | Add empty states | P5 explicit | Users need to see something when results = 0 |
| 6 | Keep SQLite for now | P3 pragmatic | 21K rows, no need to migrate yet |

---

### PHASE 2: DESIGN REVIEW (UI Scope Detected)

#### Step 0: Design Scope Assessment

**Initial rating: 5/10.** The plan describes features but not experiences. It says "shortlist management page" but never specifies: what does the empty shortlist look like? What's the interaction when you add a creator? Is there a limit? What does the export PDF look like? Every feature in the plan is described as a backend capability, not a user experience.

No DESIGN.md exists. No design system documented. The codebase has an implicit design system (dark theme, rounded-xl cards, border-border, accent color, muted-foreground text) but it's not written down.

#### Pass 1: Information Architecture — 4/10

The plan doesn't define navigation structure for new pages. Current nav: Home, Browse, Lookup, Rankings. The plan adds: Shortlist page, Campaign page, API docs. But WHERE in the nav? What's the hierarchy?

```
CURRENT NAV:
  Home → Browse → Creator Profile
  Lookup (standalone)
  Rankings (standalone)

PROPOSED NAV (after plan):
  Dashboard (new, replace Home?)
  ├── Browse → Creator Profile
  ├── Shortlists → Shortlist Detail → Export
  ├── Campaigns → Campaign Detail → Analytics
  ├── Lookup
  └── Settings / API Keys
```

Auto-decision (P5 explicit): The plan should specify the navigation structure. Added to plan recommendations.

#### Pass 2: Interaction State Coverage — 3/10

```
FEATURE              | LOADING | EMPTY  | ERROR  | SUCCESS | PARTIAL
─────────────────────|---------|--------|--------|---------|--------
Browse page          | ✅      | ❌     | ❌     | ✅      | ❌
Creator profile      | ✅      | ✅     | ❌     | ✅      | ❌
Shortlist (planned)  | ❌      | ❌     | ❌     | ❌      | ❌
Export (planned)      | ❌      | ❌     | ❌     | ❌      | ❌
Search (planned)     | ❌      | ❌     | ❌     | ❌      | ❌
Growth charts (plan) | ❌      | ❌     | ❌     | ❌      | ❌
Campaign (planned)   | ❌      | ❌     | ❌     | ❌      | ❌
```

The plan doesn't specify ANY interaction states for ANY planned feature. This is the biggest design gap. Every new feature needs loading, empty, and error states specified BEFORE implementation, or the engineer will ship "No items found." for every empty state.

Auto-decision (P1 completeness): Plan must include interaction state specs for every new feature.

#### Pass 3: User Journey & Emotional Arc — 5/10

The plan knows the user journey (from COMPETITIVE_ANALYSIS.md Journey A/B/C), but doesn't translate it into experience specs. The critical journey:

```
STEP | USER DOES                | USER FEELS          | PLAN SPECIFIES?
─────|─────────────────────────|────────────────────|─────────────────
1    | Lands on OpenKOL        | Curious, skeptical  | Partial (homepage exists)
2    | Searches for creators   | Focused, purposeful | Yes (search + filters)
3    | Browses results         | Evaluating           | Yes (cards with metrics)
4    | Opens creator profile   | Deep-diving          | Yes (detailed page)
5    | Checks authenticity     | Trust-building       | YES (best moment, audit breakdown)
6    | Adds to shortlist       | Collecting           | Feature planned, no UX spec
7    | Compares shortlisted    | Deciding             | Not specified
8    | Exports shortlist       | Delivering           | Feature planned, no UX spec
9    | Shares with team        | Collaborating        | Not specified at all
```

Step 5 (authenticity check) is where OpenKOL wins. The current creator profile page with the authenticity breakdown, progress bars, and red flag alerts is the hero moment. The plan should lean INTO this, not just add features around it.

Auto-decision (P5 explicit): Step 5 is the product's soul. Step 6-8 are the revenue path. Both need experience specs.

#### Pass 4: AI Slop Risk — 6/10

Current UI avoids most AI slop. Dark theme, clean cards, no 3-column icon grids. The homepage has some generic patterns (stat counters, filter pills) but the browse page and creator profiles feel intentional. The authenticity breakdown with colored progress bars is genuinely well-designed.

Risk areas in planned features:
- "Dashboard with widgets" (Section 2.1 Campaign Management) — classic AI slop territory
- "Settings page" — don't make it a generic card grid
- Export PDF — avoid generic report templates

Auto-decision (P5 explicit): Flag specific anti-patterns to avoid in implementation.

#### Pass 5: Design System Alignment — 3/10

No DESIGN.md. The implicit system:
- Colors: dark bg (#0a0a0a-ish), card bg with border, accent (appears to be a blue/indigo), green/yellow/red for scores
- Typography: system fonts, font-bold for headers, text-sm for labels
- Spacing: p-4 to p-8, gap-3 to gap-6, rounded-xl for cards
- Components: CreatorCard, ScoreBadge, NavBar

Duplicated across files: platformColors (3 files), countryFlags (3 files), countryNames (1 file). This should be a shared constants module.

Auto-decision (P4 DRY): Create shared design tokens and constants.

#### Pass 6: Responsive & Accessibility — 2/10

Current: Some responsive classes (sm:, lg: breakpoints), grid-cols-2 sm:grid-cols-3 patterns. No keyboard navigation specs. No ARIA landmarks. No skip-nav. No touch target size specs. The filter panel on browse uses small clickable areas.

Planned features: Zero responsive or a11y specs. "Shortlist page" doesn't specify mobile behavior. "Campaign management" on mobile?

Auto-decision (P1 completeness): Minimum a11y specs needed for every new page.

#### Pass 7: Unresolved Design Decisions — 6 decisions needed

```
DECISION NEEDED                         | IF DEFERRED, WHAT HAPPENS
──────────────────────────────────────|───────────────────────────────
1. Shortlist: drawer vs. separate page? | Engineer picks randomly
2. Export: inline generation or email?   | Probably inline, but PDF takes time
3. Search: instant or debounced?         | Currently keydown Enter only
4. Growth chart: sparkline or full chart?| Generic chart.js default
5. "Similar creators": where shown?      | Probably bottom of profile page
6. Mobile nav: hamburger or bottom tabs? | Desktop nav squished on mobile
```

Auto-decision (P5 explicit): All 6 should be specified in the plan. Recommendations:
1. Separate page (easier to build, clearer mental model) — TASTE DECISION
2. Inline with loading indicator (immediate feedback)
3. Debounced 300ms (standard UX pattern)
4. Sparkline on cards, full chart on profile page
5. Bottom of profile page, horizontal scroll cards
6. Bottom tabs for core nav (Browse, Shortlists, Profile) — TASTE DECISION

#### Design Phase Summary

| Dimension | Initial | After Review |
|-----------|---------|-------------|
| Information Architecture | 4/10 | 7/10 (with nav spec added) |
| Interaction States | 3/10 | 7/10 (with state table added) |
| User Journey | 5/10 | 7/10 (with experience specs) |
| AI Slop Risk | 6/10 | 8/10 (anti-patterns flagged) |
| Design System | 3/10 | 5/10 (needs DESIGN.md) |
| Responsive/A11y | 2/10 | 5/10 (needs specs per feature) |
| Unresolved Decisions | 6 needed | 4 resolved, 2 taste |
| **Overall** | **3/10** | **6/10** |

---

### PHASE 3: ENGINEERING REVIEW

#### Step 0: Scope Challenge

**Complexity check:** The plan touches approximately 12-15 new files and introduces 3+ new "services" (export, campaign management, API layer). This triggers the complexity smell. But for a 12-week roadmap split into 3 phases, this is reasonable. Each phase is 4-5 files, which is manageable.

**What already exists that the plan can reuse:**
```
PLANNED FEATURE          → EXISTING CODE TO LEVERAGE
─────────────────────────────────────────────────────
Full-text search          → Already has LIKE queries in route.ts, but need FTS5
Multi-select filters      → Filter UI exists in browse/page.tsx, extend it
Follower range slider     → tier filtering exists, extend to continuous range
"Last updated" timestamp  → last_scraped_at column already in platform_presences
TikTok UIDs              → backfill_uids.py already exists in scrapers
Content samples           → content_samples TABLE already exists, 0 rows
Metrics history           → metrics_history TABLE already exists, 0 rows
Audience demographics     → Would need new table + estimation logic
Campaign management       → Entirely new
API access               → API routes exist, need auth + documentation
```

**Existing code that partially solves sub-problems:**
- `backfill_uids.py` exists but needs to be integrated into the auto-scrape pipeline
- Scraper infrastructure is mature (anti-detect, parallel workers, progress tracking)
- The scoring engine in `utils/scoring.py` could be extended for audience estimation

#### Section 1: Architecture Review

```
SYSTEM ARCHITECTURE (Current + Planned)
═══════════════════════════════════════

┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│  Next.js App  │────▶│  API Routes      │────▶│  SQLite DB   │
│  (React UI)   │     │  /api/creators   │     │  kreator.db  │
│               │     │  /api/stats      │     │  WAL mode    │
│  Pages:       │     │  /api/lookup     │     │              │
│  - Home       │     │                  │     │  Tables:     │
│  - Browse     │     │  PLANNED:        │     │  - creators  │
│  - Creator    │     │  /api/shortlist  │     │  - platforms │
│  - Lookup     │     │  /api/export     │     │  - audit     │
│  - Rankings   │     │  /api/campaigns  │     │  - content   │
│               │     │  /api/auth       │     │  - metrics   │
│  PLANNED:     │     │                  │     │  - shortlist │
│  - Shortlists │     │                  │     │  - campaigns │
│  - Campaigns  │     │                  │     │  - users     │
│  - Settings   │     │                  │     │              │
└──────────────┘     └──────────────────┘     └──────────────┘
                                                      ▲
                                                      │
                                               ┌──────┴──────┐
                                               │  Python      │
                                               │  Scrapers    │
                                               │  (cron/manual)│
                                               │              │
                                               │  TikTok      │
                                               │  Instagram   │
                                               │  YouTube     │
                                               │  Facebook    │
                                               └──────────────┘
```

**Coupling concerns:** API routes directly construct SQL. No service layer. This works at current scale but means every new feature adds SQL to route handlers. For Phase 0, this is fine. For Phase 1+, consider extracting a thin service layer (src/lib/services/).

**Scaling concern:** SQLite + Next.js API routes means this must run on a single server process. You can't deploy to Vercel serverless (SQLite file system requirement). Plan should specify: deploy on VPS (Railway, Fly.io, or bare VPS).

**Security:** No auth. The plan lists "User authentication system" under Tech Debt. This is NOT tech debt, it's a Phase 0 blocker for external launch. You cannot have an external product without login.

**Production failure scenarios:**
1. TikTok changes their page structure → scrapers break silently → data goes stale → users see outdated info with no warning
2. SQLite file gets corrupted → entire app down, no backup strategy
3. Creator profile images hotlinked from TikTok CDN → TikTok blocks the referrer → all profile images break

Auto-decided issues:
| # | Issue | Decision | Principle |
|---|-------|----------|-----------|
| 7 | Move auth from Tech Debt to Phase 0 | Yes, required | P1 completeness |
| 8 | Add SQLite backup strategy | Yes, daily backup script | P1 completeness |
| 9 | Proxy/cache creator images | Yes, via Next.js Image or CDN | P3 pragmatic |
| 10 | Deploy target: VPS | Fly.io or Railway | P5 explicit |
| 11 | Add service layer | Defer to Phase 1 | P3 pragmatic |

#### Section 2: Code Quality Review

**DRY violations (found in codebase):**
- `platformColors` defined in CreatorCard.tsx, creator/[id]/page.tsx (identical)
- `countryFlags` defined in CreatorCard.tsx, creator/[id]/page.tsx, page.tsx (3 places)
- `platformIcons` defined in creator/[id]/page.tsx and page.tsx
- Fix: create `src/lib/constants.ts` with shared platform/country constants

**TypeScript quality:**
- Browse page uses `any[]` for creators state. Should use `CreatorWithDetails[]` or a specific list type.
- Creator detail page uses `any` for creator state and `any` for platform/content mapping.
- Fix: type all component state properly.

**Error handling patterns:**
- All fetch calls use `.catch(console.error)` or `.catch(() => {})`. No user-facing error states.
- No error boundaries in the React component tree.
- API routes don't validate input params (e.g., `parseInt` on a non-numeric string returns NaN, which gets passed to SQL).

Auto-decided: All DRY fixes and type improvements are mechanical (P4 DRY, P5 explicit). Error boundaries should be added to Phase 0.

#### Section 3: Test Review

**Current state: ZERO tests. No test framework. No CI/CD.**

```
CODE PATH COVERAGE
═══════════════════
[+] src/app/api/creators/route.ts
    ├── [GAP] GET with no params
    ├── [GAP] GET with country filter
    ├── [GAP] GET with search query
    ├── [GAP] GET with tier filter
    ├── [GAP] GET with invalid params
    ├── [GAP] GET with SQL injection attempt
    └── [GAP] GET with limit=0 or negative offset

[+] src/app/api/creators/[id]/route.ts
    ├── [GAP] GET with valid ID
    ├── [GAP] GET with non-existent ID
    └── [GAP] GET with non-numeric ID

[+] src/app/browse/page.tsx
    ├── [GAP] Initial load
    ├── [GAP] Filter interaction
    ├── [GAP] Search submission
    ├── [GAP] Empty results
    └── [GAP] Error state

[+] src/app/creator/[id]/page.tsx
    ├── [GAP] Load with full data
    ├── [GAP] Load with missing audit scores
    ├── [GAP] Load with no platform presences
    └── [GAP] Division by zero (avg views calc when total_videos=0)

[+] Python scrapers
    ├── [GAP] All scraper modules untested
    └── [GAP] No integration tests for DB writes

COVERAGE: 0/20+ paths tested (0%)
GAPS: Everything
```

**Test plan for Phase 0 (minimum viable test suite):**
1. API route tests (Vitest + supertest pattern): test each route with valid/invalid/edge inputs
2. Component tests (Vitest + React Testing Library): test CreatorCard, ScoreBadge, Browse page
3. Python scraper tests (pytest): test data parsing and DB write functions
4. E2E smoke test: browse → filter → click creator → verify data loads

Auto-decided (P1 completeness): Add Vitest + React Testing Library setup and minimum test suite to Phase 0. This is non-negotiable for any external product.

#### Section 4: Performance Review

**N+1 queries:** The /api/creators route does a single JOIN query covering creators + platform_presences + audit_scores. Good. No N+1.

**LIKE '%search%' problem:** The search query uses `LIKE '%term%'` which can't use indexes. At 21K rows, query time is ~5-10ms. At 100K rows, it'll be ~50-100ms. At 500K, it'll be slow. Plan should include SQLite FTS5 for full-text search in Phase 1.

**Missing indexes:** No index on `platform_presences.username` (needed for search). No composite index on `creators.country + platform_presences.platform` (needed for filtered queries).

**Memory:** SQLite loads the entire result set into memory. LIMIT 100 caps this, but the count query (`COUNT(*)`) still scans all matching rows. For filtered queries with LIKE, this could be slow.

**Image performance:** Currently hotlinking TikTok CDN for profile images. Each creator card loads an external image. On browse page with 100 cards, that's 100 cross-origin image requests. Slow, unreliable, and CDN might block.

Auto-decided:
| # | Issue | Decision | Principle |
|---|-------|----------|-----------|
| 12 | Add FTS5 for search | Phase 1 scope | P1 completeness |
| 13 | Add composite indexes | Phase 0 scope (cheap) | P3 pragmatic |
| 14 | Cache/proxy images | Phase 0 scope | P3 pragmatic |

---

### FAILURE MODES REGISTRY

```
CODEPATH                 | FAILURE MODE              | RESCUED? | TEST? | USER SEES?     | LOGGED?
────────────────────────|──────────────────────────|─────────|──────|───────────────|────────
/api/creators           | SQLite BUSY              | N        | N    | 500 error      | N      ← CRITICAL
/api/creators           | Invalid search params    | N        | N    | Malformed query | N      ← CRITICAL
browse page fetch       | Network timeout          | Y*       | N    | Nothing (catch) | Console
browse page             | Zero results             | N        | N    | Empty page      | N      ← CRITICAL
creator profile         | Division by zero (ratios)| N        | N    | NaN displayed   | N      ← CRITICAL
creator profile images  | CDN blocks hotlink       | N        | N    | Broken image    | N
python scrapers         | Platform rate limit      | Partial  | N    | Stale data      | File
python scrapers         | HTML structure change    | N        | N    | Stale data      | N      ← CRITICAL
data freshness          | No auto-refresh          | N        | N    | Outdated info   | N
```

**5 CRITICAL GAPS** where failures are silent or produce bad UX with no logging.

---

### ERROR & RESCUE REGISTRY

```
METHOD                      | EXCEPTION           | RESCUED? | RESCUE ACTION        | USER SEES
───────────────────────────|────────────────────|─────────|────────────────────|──────────────
db.prepare().all()          | SQLITE_BUSY        | N ← GAP | —                   | 500 error
db.prepare().all()          | SQLITE_CORRUPT     | N ← GAP | —                   | 500 error
parseInt(searchParams)      | Returns NaN        | N ← GAP | —                   | Undefined behavior
JSON.parse(categories)      | Invalid JSON       | Y       | Empty catch, []     | No categories shown
fetch() in components       | Network error      | Y       | console.error       | Nothing visible
Image src hotlink          | 403/404 from CDN   | N ← GAP | —                   | Broken image
primaryPlatform.followers  | Undefined (no plat) | N ← GAP | —                   | NaN or crash
```

---

### "NOT IN SCOPE" (Deferred Items)

1. **PostgreSQL migration** — Not needed until 100K+ creators or 20+ concurrent users. Trigger documented.
2. **Redis caching** — Premature at current scale. Add when API p99 > 200ms.
3. **TikTok Shop data integration** — High effort, different data source. Defer to Phase 3+.
4. **Outreach/DM automation** — Compliance risk, platform TOS concerns. Not for MVP.
5. **White-label reports** — Premium feature, build after base export works.
6. **Real-time trend alerts** — Requires streaming infrastructure. Defer to post-Phase 2.
7. **GraphQL API** — REST first, GraphQL if demand emerges.
8. **Multi-language support** — English first for SEA agencies/brands. Bahasa later.

### "WHAT ALREADY EXISTS"

1. `content_samples` table with full schema, including views/likes/comments/shares/caption — just needs data
2. `metrics_history` table with followers/avg_views/engagement_rate per date — just needs data
3. `backfill_uids.py` for TikTok UID storage
4. `utils/scoring.py` for authenticity scoring algorithms
5. Full scraper suite for 4 platforms with anti-detection
6. `last_scraped_at` column on platform_presences (data freshness is already tracked in DB)
7. Tier-based filtering (mega/macro/mid/micro/nano) already in API

### CROSS-PHASE THEMES

**Theme 1: Data quality is the real product, features are just the interface.**
Appeared in: CEO (Premise 3), Eng (Performance), Design (empty states for no data).
Every phase of the plan adds features, but data freshness, completeness, and accuracy determine whether those features are useful. Recommendation: add "Data Quality Dashboard" as an internal tool in Phase 0. Know your own data health.

**Theme 2: Auth is not tech debt, it's a launch blocker.**
Appeared in: CEO (Section 3), Eng (Security). The plan lists auth under "Technical Debt." It should be in Phase 0. You cannot invite beta users without login.

**Theme 3: Zero observability means blind operation.**
Appeared in: CEO (Section 8), Eng (Failure Modes). No logging, no metrics, no alerts. When scrapers break (they will), you won't know until a user complains about stale data. Minimum: structured logging + scraper health dashboard.

---

### DECISION AUDIT TRAIL

| # | Phase | Decision | Principle | Rationale | Rejected Alt |
|---|-------|----------|-----------|-----------|--------------|
| 1 | CEO | Mode: SELECTIVE EXPANSION | P6 action | Plan is well-scoped, needs gap filling not reimagining | SCOPE EXPANSION (too ambitious for 12 weeks) |
| 2 | CEO | Approach C (Hybrid) | P1+P3 | Parallel data+features maximizes throughput | Data-first (delays user value) |
| 3 | CEO | Add auth to Phase 0 | P1 completeness | Can't launch externally without auth | Keep in tech debt (blocks launch) |
| 4 | CEO | Add CDN/proxy for images | P3 pragmatic | Hotlinking TikTok CDN will break | Do nothing (broken images) |
| 5 | CEO | Keep SQLite | P3 pragmatic | 21K rows, WAL mode, no need to migrate | Migrate now (premature) |
| 6 | CEO | Add empty states to plan | P5 explicit | Users see blank pages otherwise | Defer (bad UX on day 1) |
| 7 | Design | Nav structure: add to plan | P5 explicit | Engineer will improvise otherwise | Let engineer decide (inconsistency) |
| 8 | Design | Interaction states: specify all | P1 completeness | Empty/error states are features | Defer (ship "No items") |
| 9 | Design | Shortlist as separate page | TASTE | Clearer mental model, easier to build | Drawer (more fluid but complex) |
| 10 | Design | Mobile nav: bottom tabs | TASTE | Better for mobile creator browsing | Hamburger (standard but less discoverable) |
| 11 | Design | Search: debounced 300ms | P5 explicit | Standard UX, avoids excessive API calls | Enter-only (current behavior) |
| 12 | Eng | Add Vitest + RTL to Phase 0 | P1 completeness | Zero tests is unacceptable for external product | Defer tests (guaranteed debt) |
| 13 | Eng | Add composite indexes | P3 pragmatic | Cheap, prevents slow queries at scale | Defer (works fine now) |
| 14 | Eng | Add FTS5 for search in Phase 1 | P1 completeness | LIKE %% can't scale | LIKE only (breaks at 100K) |
| 15 | Eng | Deploy target: Fly.io/Railway | P5 explicit | SQLite needs persistent disk | Vercel (won't work with SQLite) |
| 16 | Eng | DRY fix: shared constants | P4 DRY | platformColors/countryFlags duplicated 3x | Leave as-is (technical debt) |
| 17 | Eng | Error boundaries in React | P1 completeness | Unhandled errors show blank page | Defer (bad UX) |
| 18 | Eng | Input validation on API routes | P1+P5 | NaN propagation, potential injection | Defer (security risk) |

---

### TASTE DECISIONS (for human review)

**Taste Decision 1: Shortlist as separate page vs. drawer/sidebar**
I recommend: **Separate page**. Clearer mental model, easier to implement, works better on mobile. But a drawer is more fluid for power users who want to add/view shortlist while browsing.
Impact if you pick drawer: More complex state management, needs to work across pages, but feels more "modern."

**Taste Decision 2: Mobile navigation, hamburger vs. bottom tabs**
I recommend: **Bottom tabs** (Browse, Shortlists, Profile). Creator browsing is a mobile-heavy use case in SEA. Bottom tabs keep core actions one tap away.
Impact if you pick hamburger: Standard pattern, simpler to build, but hides navigation behind an extra tap.

**Taste Decision 3: Phase 0 scope, include "Similar creators" or defer?**
I recommend: **Defer to Phase 1**. Phase 0 already has 4 major features (export, search, data freshness, profile enrichment) plus the newly recommended auth, tests, and error handling. Similar creators requires a recommendation algorithm.
Impact if you include: Phase 0 becomes 4-5 weeks instead of 2, but the feature drives discovery.

---

### RECOMMENDED PLAN AMENDMENTS

Based on this review, the plan should be updated:

**Phase 0 additions (required for external launch):**
1. ☐ Basic auth system (email/password or OAuth, session-based)
2. ☐ Vitest + React Testing Library setup + minimum test suite (API routes + key components)
3. ☐ Error boundaries in React app
4. ☐ Empty state components (browse zero results, shortlist empty, profile missing data)
5. ☐ Input validation on all API route params
6. ☐ Image proxy/caching (stop hotlinking TikTok CDN)
7. ☐ Composite database indexes for common query patterns
8. ☐ Deploy strategy (Fly.io/Railway with persistent SQLite volume)
9. ☐ DRY fix: shared constants for platform colors, country flags, etc.

**Phase 1 additions:**
1. ☐ SQLite FTS5 for full-text search (replace LIKE %%)
2. ☐ Structured logging (at minimum for scrapers and API errors)
3. ☐ Scraper health dashboard (internal: when did each scraper last run? How many failures?)

**Phase 0 resequencing:**
```
Week 1: Auth + Export + Shortlist + Error handling + Tests setup
Week 2: Search improvements + Data freshness + Image proxy + Deploy
```

### COMPLETION SUMMARY

```
+====================================================================+
|            AUTOPLAN REVIEW — COMPLETION SUMMARY                     |
+====================================================================+
| Mode selected        | SELECTIVE EXPANSION (auto-decided)           |
| Implementation       | Approach C: Hybrid (features + data parallel)|
+--------------------------------------------------------------------+
| CEO REVIEW                                                          |
|   Premises           | 5 evaluated, 4 valid, 1 partially valid     |
|   Architecture       | 1 issue (no auth)                           |
|   Error/Rescue       | 7 methods mapped, 5 GAPS                    |
|   Security           | 2 issues (no auth, no rate limiting)         |
|   Data/Edge Cases    | 4 edge cases mapped, 3 unhandled             |
|   Code Quality       | 3 DRY violations, 4 type issues              |
|   Tests              | 0% coverage, 20+ gaps                        |
|   Performance        | 3 issues (LIKE, indexes, images)             |
|   Observability      | 0 logging, 0 metrics, 0 alerts               |
|   Deployment         | Not specified (blocker)                       |
|   Long-Term          | Good trajectory, reversibility 4/5           |
|   Design (CEO-level) | 4 issues (empty states, nav, responsive)     |
+--------------------------------------------------------------------+
| DESIGN REVIEW                                                       |
|   Info Architecture  | 4/10 → 7/10                                 |
|   Interaction States | 3/10 → 7/10                                 |
|   User Journey       | 5/10 → 7/10                                 |
|   AI Slop Risk       | 6/10 → 8/10                                 |
|   Design System      | 3/10 → 5/10                                 |
|   Responsive/A11y    | 2/10 → 5/10                                 |
|   Unresolved         | 4 resolved, 2 taste decisions                |
|   Overall Design     | 3/10 → 6/10                                 |
+--------------------------------------------------------------------+
| ENG REVIEW                                                          |
|   Scope Challenge    | Complexity OK (phased approach)              |
|   Architecture       | 5 issues, 5 auto-decided                     |
|   Code Quality       | 7 issues (DRY, types, error handling)        |
|   Test Review        | 0% coverage, 20+ gaps, test plan written     |
|   Performance        | 3 issues (search, indexes, images)           |
+--------------------------------------------------------------------+
| CROSS-PHASE                                                         |
|   Themes             | 3 (data quality, auth, observability)        |
|   Failure Modes      | 9 total, 5 CRITICAL GAPS                     |
|   NOT in scope       | 8 items deferred with rationale              |
|   What exists        | 7 reusable assets identified                 |
+--------------------------------------------------------------------+
| DECISIONS                                                           |
|   Auto-decided       | 18 (using 6 decision principles)             |
|   Taste decisions    | 3 (for human review)                         |
|   Lake Score         | 15/18 chose complete option                  |
+--------------------------------------------------------------------+
| OUTSIDE VOICES                                                      |
|   Codex              | Unavailable (subagent environment)           |
|   Claude subagent    | Unavailable (subagent environment)           |
|   Mode               | Single-reviewer                              |
+====================================================================+

VERDICT: Plan is SOLID FOUNDATION with GAPS that need filling before
external launch. The product instinct is strong (authenticity scoring
as hero feature, SEA focus, MantaYaY data advantage). The main risks
are all fixable: auth, tests, error handling, data freshness, deploy
strategy. 3 taste decisions surfaced for human review.
```
