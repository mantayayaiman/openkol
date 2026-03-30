#!/usr/bin/env python3
"""
KolBuff SEO Keyword Research Engine.

Strategy:
1. Programmatic SEO — auto-generate pages from DB data (e.g., "Top TikTok creators in Malaysia")
2. Editorial SEO — long-form articles targeting high-intent keywords
3. AI Search Optimization — structured content that AI search engines cite

Keyword categories:
- Creator discovery: "find tiktok influencers", "instagram creator search", "youtube influencer database"
- Platform-specific: "top tiktok creators [country]", "best instagram influencers [niche]"  
- Industry guides: "influencer marketing guide", "how to find micro influencers"
- Comparisons: "kolbuff vs [competitor]", "[competitor] alternatives"
- Niche + Country combos: "beauty influencers malaysia", "gaming creators indonesia"
"""

import json
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'kreator.db')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'keywords')
BLOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'content', 'blog')

# SEA countries we cover
COUNTRIES = {
    'MY': 'Malaysia',
    'ID': 'Indonesia', 
    'TH': 'Thailand',
    'PH': 'Philippines',
    'VN': 'Vietnam',
    'SG': 'Singapore',
}

# Our platform coverage
PLATFORMS = ['tiktok', 'instagram', 'youtube', 'facebook']

# Niche categories from our DB
CATEGORIES = [
    'beauty', 'fashion', 'food', 'gaming', 'tech', 'lifestyle',
    'fitness', 'travel', 'comedy', 'education', 'music', 'family',
    'automotive', 'finance', 'pets'
]

CATEGORY_DISPLAY = {
    'beauty': 'Beauty & Skincare',
    'fashion': 'Fashion & Style',
    'food': 'Food & F&B',
    'gaming': 'Gaming',
    'tech': 'Tech & Gadgets',
    'lifestyle': 'Lifestyle',
    'fitness': 'Fitness & Health',
    'travel': 'Travel',
    'comedy': 'Comedy & Entertainment',
    'education': 'Education',
    'music': 'Music & Dance',
    'family': 'Parenting & Family',
    'automotive': 'Automotive',
    'finance': 'Finance & Business',
    'pets': 'Pets & Animals',
}

PLATFORM_DISPLAY = {
    'tiktok': 'TikTok',
    'instagram': 'Instagram',
    'youtube': 'YouTube',
    'facebook': 'Facebook',
}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def generate_keyword_matrix():
    """Generate the full keyword matrix for programmatic + editorial SEO."""
    
    keywords = []
    
    # === PROGRAMMATIC SEO (auto-generated from data) ===
    
    # Pattern 1: "Top [platform] creators in [country]"
    for platform in PLATFORMS:
        for code, country in COUNTRIES.items():
            keywords.append({
                'pattern': 'top_creators_country',
                'keyword': f'top {PLATFORM_DISPLAY[platform]} creators in {country}',
                'slug': f'top-{platform}-creators-{country.lower()}-2026',
                'title': f'Top {PLATFORM_DISPLAY[platform]} Creators in {country} (2026) — Rankings & Analytics',
                'intent': 'informational',
                'priority': 'high',
                'type': 'programmatic',
                'platform': platform,
                'country': code,
                'category': None,
                'estimated_volume': 'medium-high',
            })
    
    # Pattern 2: "Best [niche] influencers [country]"
    for cat in CATEGORIES:
        for code, country in COUNTRIES.items():
            keywords.append({
                'pattern': 'niche_country',
                'keyword': f'best {CATEGORY_DISPLAY[cat].lower()} influencers {country}',
                'slug': f'best-{cat}-influencers-{country.lower()}-2026',
                'title': f'Best {CATEGORY_DISPLAY[cat]} Influencers in {country} (2026)',
                'intent': 'informational',
                'priority': 'medium',
                'type': 'programmatic',
                'platform': None,
                'country': code,
                'category': cat,
                'estimated_volume': 'medium',
            })
    
    # Pattern 3: "Top [niche] [platform] creators"
    for cat in ['gaming', 'beauty', 'food', 'tech', 'fitness', 'comedy']:
        for platform in ['tiktok', 'instagram', 'youtube']:
            keywords.append({
                'pattern': 'niche_platform',
                'keyword': f'top {cat} {PLATFORM_DISPLAY[platform]} creators',
                'slug': f'top-{cat}-{platform}-creators-2026',
                'title': f'Top {CATEGORY_DISPLAY[cat]} {PLATFORM_DISPLAY[platform]} Creators (2026)',
                'intent': 'informational',
                'priority': 'medium',
                'type': 'programmatic',
                'platform': platform,
                'country': None,
                'category': cat,
                'estimated_volume': 'medium',
            })
    
    # === EDITORIAL SEO (manual/AI-written long-form) ===
    
    editorial_keywords = [
        # High-volume head terms
        {
            'keyword': 'influencer marketing platform',
            'slug': 'best-influencer-marketing-platforms-2026',
            'title': 'Best Influencer Marketing Platforms in 2026 — Complete Comparison',
            'priority': 'high',
            'estimated_volume': 'high',
        },
        {
            'keyword': 'how to find micro influencers',
            'slug': 'how-to-find-micro-influencers',
            'title': 'How to Find Micro-Influencers for Your Brand (2026 Guide)',
            'priority': 'high',
            'estimated_volume': 'high',
        },
        {
            'keyword': 'tiktok influencer marketing guide',
            'slug': 'tiktok-influencer-marketing-complete-guide',
            'title': 'TikTok Influencer Marketing: The Complete Guide for Brands',
            'priority': 'high',
            'estimated_volume': 'high',
        },
        {
            'keyword': 'influencer marketing roi',
            'slug': 'influencer-marketing-roi-how-to-measure',
            'title': 'How to Measure Influencer Marketing ROI (With Real Data)',
            'priority': 'high',
            'estimated_volume': 'high',
        },
        {
            'keyword': 'fake followers check',
            'slug': 'how-to-spot-fake-followers-influencer-audit',
            'title': 'How to Spot Fake Followers: The Ultimate Influencer Audit Guide',
            'priority': 'high',
            'estimated_volume': 'high',
        },
        {
            'keyword': 'tiktok engagement rate calculator',
            'slug': 'tiktok-engagement-rate-calculator',
            'title': 'TikTok Engagement Rate Calculator — Free Tool + Benchmarks',
            'priority': 'high',
            'estimated_volume': 'high',
        },
        {
            'keyword': 'instagram influencer pricing',
            'slug': 'instagram-influencer-pricing-guide',
            'title': 'Instagram Influencer Pricing: What Brands Really Pay in 2026',
            'priority': 'medium',
            'estimated_volume': 'medium-high',
        },
        {
            'keyword': 'southeast asia influencer market',
            'slug': 'southeast-asia-influencer-marketing-landscape',
            'title': 'Southeast Asia Influencer Marketing: The $4B Opportunity',
            'priority': 'high',
            'estimated_volume': 'medium',
        },
        {
            'keyword': 'kol marketing malaysia',
            'slug': 'kol-marketing-malaysia-guide',
            'title': 'KOL Marketing in Malaysia: Finding the Right Creators for Your Brand',
            'priority': 'high',
            'estimated_volume': 'medium',
        },
        {
            'keyword': 'tiktok live selling tips',
            'slug': 'tiktok-live-selling-tips-beginners',
            'title': 'TikTok Live Selling: 15 Tips That Actually Work (From Data)',
            'priority': 'medium',
            'estimated_volume': 'medium',
        },
        {
            'keyword': 'creator economy statistics',
            'slug': 'creator-economy-statistics-2026',
            'title': 'Creator Economy Statistics 2026: 50+ Key Data Points',
            'priority': 'medium',
            'estimated_volume': 'medium',
        },
        {
            'keyword': 'influencer marketing for small business',
            'slug': 'influencer-marketing-small-business-guide',
            'title': 'Influencer Marketing for Small Businesses: Budget-Friendly Strategies',
            'priority': 'medium',
            'estimated_volume': 'medium-high',
        },
    ]
    
    for ek in editorial_keywords:
        ek['pattern'] = 'editorial'
        ek['type'] = 'editorial'
        ek['intent'] = 'informational'
        ek['platform'] = None
        ek['country'] = None
        ek['category'] = None
        keywords.append(ek)
    
    # === AI SEARCH OPTIMIZATION (question-based, FAQ-style) ===
    
    ai_questions = [
        'What is the best influencer marketing platform for Southeast Asia?',
        'How do I find authentic TikTok creators for my brand?',
        'What is a good engagement rate on TikTok?',
        'How much do Malaysian influencers charge?',
        'What are the top creator discovery tools?',
        'How to verify if an influencer has fake followers?',
        'What is KOL marketing?',
        'Best platforms for micro-influencer campaigns in 2026',
    ]
    
    for q in ai_questions:
        slug = q.lower().replace('?', '').replace("'", '').replace(' ', '-')[:60]
        keywords.append({
            'pattern': 'ai_question',
            'keyword': q,
            'slug': slug,
            'title': q,
            'intent': 'informational',
            'priority': 'medium',
            'type': 'faq',
            'platform': None,
            'country': None,
            'category': None,
            'estimated_volume': 'emerging',
        })
    
    return keywords


def get_content_stats():
    """Get stats from our DB to power data-driven articles."""
    conn = get_db()
    
    stats = {}
    
    # Total creators
    stats['total_creators'] = conn.execute('SELECT COUNT(*) FROM creators').fetchone()[0]
    
    # By country
    stats['by_country'] = {}
    for row in conn.execute('SELECT country, COUNT(*) as cnt FROM creators GROUP BY country ORDER BY cnt DESC'):
        stats['by_country'][row['country']] = row['cnt']
    
    # By platform
    stats['by_platform'] = {}
    for row in conn.execute('SELECT platform, COUNT(*) as cnt FROM platform_presences GROUP BY platform ORDER BY cnt DESC'):
        stats['by_platform'][row['platform']] = row['cnt']
    
    # Top creators per country per platform (for programmatic pages)
    stats['top_creators'] = {}
    for code in COUNTRIES:
        for platform in PLATFORMS:
            rows = conn.execute('''
                SELECT c.id, c.name, c.country, c.categories, c.heat_score,
                       pp.username, pp.followers, pp.engagement_rate, pp.avg_views, pp.total_likes
                FROM creators c
                JOIN platform_presences pp ON pp.creator_id = c.id
                WHERE c.country = ? AND pp.platform = ?
                ORDER BY pp.followers DESC
                LIMIT 50
            ''', (code, platform)).fetchall()
            
            key = f'{code}_{platform}'
            stats['top_creators'][key] = [dict(r) for r in rows]
    
    # Top creators per niche per country
    stats['top_niche'] = {}
    for cat in CATEGORIES:
        for code in COUNTRIES:
            rows = conn.execute('''
                SELECT c.id, c.name, c.country, c.categories, c.heat_score,
                       pp.platform, pp.username, pp.followers, pp.engagement_rate
                FROM creators c
                JOIN platform_presences pp ON pp.creator_id = c.id AND pp.platform = c.primary_platform
                WHERE c.country = ? AND c.categories LIKE ?
                ORDER BY pp.followers DESC
                LIMIT 30
            ''', (code, f'%{cat}%')).fetchall()
            
            key = f'{cat}_{code}'
            stats['top_niche'][key] = [dict(r) for r in rows]
    
    conn.close()
    return stats


def generate_priority_queue(keywords):
    """Sort keywords by priority and generate a publishing queue."""
    
    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    
    # Separate by type
    programmatic = [k for k in keywords if k['type'] == 'programmatic']
    editorial = [k for k in keywords if k['type'] == 'editorial']
    faq = [k for k in keywords if k['type'] == 'faq']
    
    # Programmatic: prioritize high-volume combos
    # Malaysia + TikTok first (our strongest data), then expand
    country_priority = ['MY', 'ID', 'SG', 'PH', 'TH', 'VN']
    platform_priority = ['tiktok', 'instagram', 'youtube', 'facebook']
    
    def prog_sort_key(k):
        cp = country_priority.index(k['country']) if k['country'] in country_priority else 99
        pp = platform_priority.index(k['platform']) if k['platform'] in platform_priority else 99
        return (priority_order.get(k['priority'], 99), cp, pp)
    
    programmatic.sort(key=prog_sort_key)
    editorial.sort(key=lambda k: priority_order.get(k['priority'], 99))
    
    # Publishing queue: alternate between editorial (higher value) and programmatic (volume)
    queue = []
    
    # Week 1: 3 high-priority editorial + 6 programmatic (MY focus)
    queue.extend(editorial[:3])
    queue.extend(programmatic[:6])
    
    # Week 2+: continue mix
    queue.extend(editorial[3:])
    queue.extend(programmatic[6:])
    queue.extend(faq)
    
    return queue


def check_existing_posts():
    """Check which articles already exist."""
    existing = set()
    if os.path.exists(BLOG_DIR):
        for f in os.listdir(BLOG_DIR):
            if f.endswith('.mdx'):
                existing.add(f.replace('.mdx', ''))
    return existing


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("🔍 Generating keyword matrix...")
    keywords = generate_keyword_matrix()
    
    print(f"📊 Total keywords: {len(keywords)}")
    print(f"  - Programmatic: {len([k for k in keywords if k['type'] == 'programmatic'])}")
    print(f"  - Editorial: {len([k for k in keywords if k['type'] == 'editorial'])}")
    print(f"  - FAQ/AI: {len([k for k in keywords if k['type'] == 'faq'])}")
    
    # Check existing
    existing = check_existing_posts()
    pending = [k for k in keywords if k['slug'] not in existing]
    print(f"  - Already published: {len(keywords) - len(pending)}")
    print(f"  - Pending: {len(pending)}")
    
    # Generate priority queue
    queue = generate_priority_queue(pending)
    
    # Save full keyword matrix
    with open(os.path.join(OUTPUT_DIR, 'keyword_matrix.json'), 'w') as f:
        json.dump(keywords, f, indent=2)
    
    # Save priority queue
    with open(os.path.join(OUTPUT_DIR, 'publishing_queue.json'), 'w') as f:
        json.dump(queue, f, indent=2)
    
    # Get content stats for data-driven articles
    print("\n📈 Pulling content stats from DB...")
    stats = get_content_stats()
    
    with open(os.path.join(OUTPUT_DIR, 'content_stats.json'), 'w') as f:
        json.dump(stats, f, indent=2, default=str)
    
    print(f"  - {stats['total_creators']} creators in DB")
    print(f"  - {len(stats['by_country'])} countries")
    print(f"  - {len(stats['by_platform'])} platforms")
    
    # Print first 10 items in queue
    print("\n📋 Publishing Queue (first 10):")
    for i, item in enumerate(queue[:10]):
        status = '✅' if item['slug'] in existing else '📝'
        print(f"  {i+1}. {status} [{item['type']}] {item['title']}")
    
    print(f"\n✅ Saved to {OUTPUT_DIR}/")
    print(f"  - keyword_matrix.json ({len(keywords)} keywords)")
    print(f"  - publishing_queue.json ({len(queue)} articles to write)")
    print(f"  - content_stats.json (DB stats for data-driven content)")


if __name__ == '__main__':
    main()
