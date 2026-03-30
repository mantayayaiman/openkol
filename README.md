# OpenKOL — Open Creator Intelligence

> Discover. Audit. Trust.

AI-powered creator discovery and authenticity scoring platform for Southeast Asia. Analyze creators across TikTok, Instagram, and YouTube with proprietary authenticity scoring.

## Stack

- **Frontend:** Next.js 15 (App Router) + Tailwind CSS v4
- **Database:** SQLite via better-sqlite3
- **Scraper:** Python + Playwright (modular, platform-agnostic)
- **Scoring:** Heuristic-based authenticity engine (v0)

## Quick Start

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The database is auto-seeded with 30+ sample creators on first API call.

## Features

- **Browse** — Filter creators by country (MY, ID, TH, PH, VN, SG), platform, and category
- **Rankings** — Top creators ranked by authenticity score, engagement, or reach
- **Creator Profiles** — Deep metrics, authenticity breakdown, red flags, recent content
- **Lookup** — Paste a TikTok/IG/YT URL to find or analyze a creator
- **Authenticity Score** — 0-100 score based on engagement patterns, follower quality, growth consistency

## Scraper

```bash
cd scraper
pip install -r requirements.txt
playwright install chromium

# Scrape a profile
python -m scraper.main https://tiktok.com/@username --pretty
python -m scraper.main tiktok:username --pretty
python -m scraper.main instagram:username -o output.json
```

## Project Structure

```
├── src/
│   ├── app/
│   │   ├── page.tsx          # Landing page
│   │   ├── browse/           # Browse & filter creators
│   │   ├── rankings/         # Creator rankings
│   │   ├── lookup/           # URL lookup
│   │   ├── creator/[id]/     # Creator detail page
│   │   └── api/              # API routes
│   ├── components/           # Shared components
│   └── lib/                  # DB, types, utilities
├── scraper/
│   ├── scrapers/             # Platform scrapers (TikTok, IG, YT)
│   ├── utils/                # Anti-detection, scoring engine
│   ├── models.py             # Pydantic data models
│   └── main.py               # CLI entry point
└── kreator.db                # SQLite database (auto-created)
```

## Authenticity Score (v0)

| Component | Weight | What it measures |
|-----------|--------|-----------------|
| Engagement-to-follower ratio | 30% | Engagement vs category/tier benchmark |
| Growth consistency | 20% | Posting frequency and regularity |
| Comment quality | 20% | Comment-to-like ratio as proxy |
| Following-to-follower ratio | 10% | High ratio = suspicious |
| Posting consistency | 10% | Regular posting schedule |
| View-to-follower ratio | 10% | Organic reach indicator |

**Score ranges:** 🟢 70-100 (Authentic) · 🟡 40-69 (Review) · 🔴 0-39 (Suspicious)
