#!/usr/bin/env python3
"""
KolBuff SEO Article Generator.

Generates MDX blog posts from the keyword queue using real data from our DB.
Two modes:
1. Programmatic — data-driven pages from templates (top creators lists, niche roundups)
2. Editorial — AI-written long-form articles with real data points

Usage:
  python3 seo/article_generator.py                  # Generate next 5 from queue
  python3 seo/article_generator.py --count 10       # Generate next 10
  python3 seo/article_generator.py --slug <slug>    # Generate specific article
  python3 seo/article_generator.py --type editorial  # Only editorial articles
"""

import json
import os
import sys
import sqlite3
import subprocess
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, '..')
DB_PATH = os.path.join(PROJECT_DIR, 'kreator.db')
BLOG_DIR = os.path.join(PROJECT_DIR, 'content', 'blog')
KEYWORDS_DIR = os.path.join(SCRIPT_DIR, 'keywords')
QUEUE_PATH = os.path.join(KEYWORDS_DIR, 'publishing_queue.json')
STATS_PATH = os.path.join(KEYWORDS_DIR, 'content_stats.json')

COUNTRIES = {
    'MY': 'Malaysia', 'ID': 'Indonesia', 'TH': 'Thailand',
    'PH': 'Philippines', 'VN': 'Vietnam', 'SG': 'Singapore',
}

PLATFORM_DISPLAY = {
    'tiktok': 'TikTok', 'instagram': 'Instagram',
    'youtube': 'YouTube', 'facebook': 'Facebook',
}

CATEGORY_DISPLAY = {
    'beauty': 'Beauty & Skincare', 'fashion': 'Fashion & Style',
    'food': 'Food & F&B', 'gaming': 'Gaming', 'tech': 'Tech & Gadgets',
    'lifestyle': 'Lifestyle', 'fitness': 'Fitness & Health', 'travel': 'Travel',
    'comedy': 'Comedy & Entertainment', 'education': 'Education',
    'music': 'Music & Dance', 'family': 'Parenting & Family',
    'automotive': 'Automotive', 'finance': 'Finance & Business', 'pets': 'Pets & Animals',
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def format_number(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def get_top_creators(country=None, platform=None, category=None, limit=50):
    """Pull top creators from DB for article content."""
    conn = get_db()
    
    where_clauses = []
    params = []
    
    if country:
        where_clauses.append('c.country = ?')
        params.append(country)
    if platform:
        where_clauses.append('pp.platform = ?')
        params.append(platform)
    if category:
        where_clauses.append('c.categories LIKE ?')
        params.append(f'%{category}%')
    
    where = ' AND '.join(where_clauses) if where_clauses else '1=1'
    
    rows = conn.execute(f'''
        SELECT c.id, c.name, c.country, c.categories, c.bio, c.heat_score, c.profile_image,
               pp.platform, pp.username, pp.followers, pp.following,
               pp.engagement_rate, pp.avg_views, pp.total_likes, pp.total_videos
        FROM creators c
        JOIN platform_presences pp ON pp.creator_id = c.id
        WHERE {where}
        ORDER BY pp.followers DESC
        LIMIT ?
    ''', params + [limit]).fetchall()
    
    conn.close()
    return [dict(r) for r in rows]


def get_category_stats(country=None):
    """Get category distribution stats."""
    conn = get_db()
    where = f"WHERE country = '{country}'" if country else ""
    
    rows = conn.execute(f'''
        SELECT categories, COUNT(*) as cnt
        FROM creators {where}
        GROUP BY categories
        ORDER BY cnt DESC
        LIMIT 20
    ''').fetchall()
    
    conn.close()
    
    # Parse and aggregate
    cat_counts = {}
    for row in rows:
        try:
            cats = json.loads(row['categories'])
            for cat in cats:
                cat_counts[cat] = cat_counts.get(cat, 0) + row['cnt']
        except:
            pass
    
    return dict(sorted(cat_counts.items(), key=lambda x: -x[1]))


def generate_programmatic_top_creators(keyword):
    """Generate a 'Top [platform] creators in [country]' article from real data."""
    
    country = keyword.get('country')
    platform = keyword.get('platform')
    category = keyword.get('category')
    
    country_name = COUNTRIES.get(country, country) if country else 'Southeast Asia'
    platform_name = PLATFORM_DISPLAY.get(platform, platform) if platform else 'Social Media'
    category_name = CATEGORY_DISPLAY.get(category, category) if category else ''
    
    creators = get_top_creators(country=country, platform=platform, category=category, limit=50)
    
    if not creators:
        print(f"  ⚠️ No creators found for {keyword['slug']}, skipping")
        return None
    
    # Build the MDX content
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Determine article focus
    if platform and country:
        focus = f'{platform_name} creators in {country_name}'
        description = f"Discover the top {len(creators)} {platform_name} creators in {country_name} for 2026. Real follower counts, engagement rates, and analytics from KolBuff's database of {format_number(get_total_creators())}+ verified creators."
        tags = [platform_name.lower(), country_name.lower(), 'creators', 'rankings', 'influencer marketing']
    elif category and country:
        focus = f'{category_name} influencers in {country_name}'
        description = f"The best {category_name.lower()} influencers in {country_name} for 2026. Verified analytics, engagement rates, and audience data for {len(creators)} top creators."
        tags = [category.lower(), country_name.lower(), 'influencers', 'rankings', category_name.lower()]
    elif category and platform:
        focus = f'{category_name} {platform_name} creators'
        description = f"Top {category_name.lower()} {platform_name} creators ranked by followers and engagement. Real data from KolBuff."
        tags = [category.lower(), platform_name.lower(), 'creators', 'rankings']
    else:
        focus = 'top creators'
        description = f"Top social media creators ranked by KolBuff."
        tags = ['creators', 'rankings']
    
    # Calculate aggregate stats
    total_followers = sum(c['followers'] for c in creators)
    avg_er = sum(c['engagement_rate'] for c in creators if c['engagement_rate']) / max(len([c for c in creators if c['engagement_rate']]), 1)
    top_10 = creators[:10]
    
    # Build creator table rows
    table_rows = []
    for i, c in enumerate(creators[:50]):
        er_display = f"{c['engagement_rate']:.2f}%" if c['engagement_rate'] else 'N/A'
        views_display = format_number(c['avg_views']) if c['avg_views'] else 'N/A'
        table_rows.append(
            f"| {i+1} | [{c['name']}](https://kolbuff.com/creator/{c['id']}) | @{c['username']} | {format_number(c['followers'])} | {er_display} | {views_display} |"
        )
    
    table = '\n'.join(table_rows)
    
    # Category breakdown
    cat_stats = get_category_stats(country)
    cat_section = ''
    if cat_stats:
        cat_items = '\n'.join([f"- **{CATEGORY_DISPLAY.get(k, k)}**: {v} creators" for k, v in list(cat_stats.items())[:8]])
        cat_section = f"""
## Content Categories

The {focus} scene breaks down across these niches:

{cat_items}
"""
    
    # Engagement insights
    high_er = [c for c in creators if c['engagement_rate'] and c['engagement_rate'] > 5]
    mega = [c for c in creators if c['followers'] >= 1_000_000]
    micro = [c for c in creators if 10_000 <= c['followers'] <= 100_000]
    
    mdx = f"""---
title: "{keyword['title']}"
description: "{description}"
date: "{today}"
author: "KolBuff Team"
tags: {json.dumps(tags)}
category: "Rankings"
slug: "{keyword['slug']}"
featured: false
---

# {keyword['title']}

Looking for the top {focus}? We've ranked **{len(creators)} creators** using real data from KolBuff's verified database of **{format_number(get_total_creators())}+ creators** across Southeast Asia.

Every number on this page is pulled directly from live platform data — no guesswork, no estimates.

## Quick Stats

- **Total creators ranked**: {len(creators)}
- **Combined followers**: {format_number(total_followers)}
- **Average engagement rate**: {avg_er:.2f}%
- **Mega creators (1M+)**: {len(mega)}
- **Micro creators (10K-100K)**: {len(micro)}
- **High engagement (>5%)**: {len(high_er)}

## Top 10 {focus.title()}

Here are the top 10 by follower count:

| Rank | Creator | Handle | Followers | Engagement | Avg Views |
|------|---------|--------|-----------|------------|-----------|
{chr(10).join(table_rows[:10])}

## Full Rankings (Top {min(len(creators), 50)})

| Rank | Creator | Handle | Followers | Engagement | Avg Views |
|------|---------|--------|-----------|------------|-----------|
{table}

{cat_section}

## How We Rank Creators

KolBuff's rankings are based on verified, real-time data:

1. **Follower count** — scraped directly from platform profiles
2. **Engagement rate** — calculated from likes, comments, and shares relative to followers
3. **Average views** — mean views across recent content
4. **Heat score** — our proprietary metric combining recency, growth velocity, and engagement trends

We don't accept paid placements. Every creator on this list earned their spot through real performance.

## Methodology

- Data sourced from KolBuff's database of {format_number(get_total_creators())}+ creators
- Updated weekly via automated scrapers
- Engagement rates calculated using the standard formula: (likes + comments) / followers × 100
- Rankings refresh automatically as new data comes in

## Find Your Perfect Creator

Use [KolBuff's free search](https://kolbuff.com/browse) to filter creators by country, platform, niche, follower range, and engagement rate. Every creator profile includes detailed analytics, audience insights, and contact information.

---

*Data last updated: {today}. Rankings refresh weekly.*
"""
    
    return mdx


def get_total_creators():
    conn = get_db()
    count = conn.execute('SELECT COUNT(*) FROM creators').fetchone()[0]
    conn.close()
    return count


def generate_editorial_article(keyword):
    """Generate an editorial article using Claude for high-quality content."""
    
    # Get relevant stats from our DB
    total = get_total_creators()
    cat_stats = get_category_stats()
    
    # Build context for the AI writer
    context = f"""
KolBuff (kolbuff.com) is a free creator discovery and analytics platform covering {format_number(total)}+ creators across TikTok, Instagram, YouTube, and Facebook in Southeast Asia (Malaysia, Indonesia, Thailand, Philippines, Vietnam, Singapore).

Key features:
- Real-time follower counts, engagement rates, and view analytics
- Authenticity audit scores (detects fake followers)
- Heat score tracking (trending creators)
- Free search and filtering
- Creator profiles with contact info

The article should:
1. Be genuinely helpful and authoritative (not salesy)
2. Include real data points and statistics
3. Link to KolBuff features where natural (creator search, specific creator profiles)
4. Target the keyword: "{keyword['keyword']}"
5. Be 1500-2500 words
6. Include an FAQ section at the end (for AI search optimization)
7. Use natural language, avoid keyword stuffing
8. Include internal links to kolbuff.com/browse and relevant creator profiles
"""
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    prompt = f"""Write a complete MDX blog post for the following:

Title: {keyword['title']}
Target keyword: {keyword['keyword']}
Context: {context}

The output should be a complete MDX file with frontmatter. Format:

---
title: "{keyword['title']}"
description: "..."  (150 chars max, include keyword naturally)
date: "{today}"
author: "KolBuff Team"
tags: ["relevant", "tags", "here"]
category: "Guides"
slug: "{keyword['slug']}"
featured: false
---

[Article content in MDX/Markdown]

Write the full article now. Make it genuinely useful, data-rich, and authoritative. Include:
- A compelling intro that hooks the reader
- Clear H2/H3 structure
- Real statistics and data points
- Practical actionable advice
- Internal links to kolbuff.com features
- An FAQ section with 4-5 common questions
- A conclusion with CTA

Do NOT include any meta-commentary or instructions in the output. Just the raw MDX file."""

    # Use Claude to write the article
    try:
        result = subprocess.run(
            ['claude', '--permission-mode', 'bypassPermissions', '--print', '-p', prompt],
            capture_output=True, text=True, timeout=120,
            cwd=PROJECT_DIR
        )
        
        if result.returncode == 0 and result.stdout.strip():
            content = result.stdout.strip()
            # Clean up — remove any markdown code fences if Claude wrapped it
            if content.startswith('```mdx'):
                content = content[6:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            return content.strip()
        else:
            print(f"  ❌ Claude failed: {result.stderr[:200]}")
            return None
    except subprocess.TimeoutExpired:
        print(f"  ❌ Claude timed out")
        return None
    except FileNotFoundError:
        print(f"  ❌ Claude CLI not found, skipping editorial article")
        return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Generate SEO articles for KolBuff')
    parser.add_argument('--count', type=int, default=5, help='Number of articles to generate')
    parser.add_argument('--slug', type=str, help='Generate specific article by slug')
    parser.add_argument('--type', type=str, choices=['programmatic', 'editorial', 'faq'], help='Only generate this type')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be generated without writing')
    args = parser.parse_args()
    
    os.makedirs(BLOG_DIR, exist_ok=True)
    
    # Load queue
    if not os.path.exists(QUEUE_PATH):
        print("❌ No publishing queue found. Run keyword_research.py first.")
        sys.exit(1)
    
    with open(QUEUE_PATH) as f:
        queue = json.load(f)
    
    # Check existing
    existing = set()
    for f_name in os.listdir(BLOG_DIR):
        if f_name.endswith('.mdx'):
            existing.add(f_name.replace('.mdx', ''))
    
    # Filter
    if args.slug:
        queue = [k for k in queue if k['slug'] == args.slug]
    elif args.type:
        queue = [k for k in queue if k['type'] == args.type]
    
    pending = [k for k in queue if k['slug'] not in existing]
    
    if not pending:
        print("✅ All articles in queue have been generated!")
        return
    
    to_generate = pending[:args.count]
    
    print(f"📝 Generating {len(to_generate)} articles...")
    
    generated = 0
    for i, keyword in enumerate(to_generate):
        print(f"\n[{i+1}/{len(to_generate)}] {keyword['title']}")
        print(f"  Type: {keyword['type']} | Slug: {keyword['slug']}")
        
        if args.dry_run:
            print(f"  (dry run — skipping)")
            continue
        
        content = None
        
        if keyword['type'] == 'programmatic':
            content = generate_programmatic_top_creators(keyword)
        elif keyword['type'] in ('editorial', 'faq'):
            content = generate_editorial_article(keyword)
        
        if content:
            filepath = os.path.join(BLOG_DIR, f"{keyword['slug']}.mdx")
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"  ✅ Written: {filepath}")
            generated += 1
        else:
            print(f"  ⚠️ Skipped (no content generated)")
    
    print(f"\n🎉 Generated {generated}/{len(to_generate)} articles")
    print(f"📁 Blog directory: {BLOG_DIR}")


if __name__ == '__main__':
    main()
