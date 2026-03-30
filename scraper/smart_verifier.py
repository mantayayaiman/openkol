#!/usr/bin/env python3
"""
Smart Verifier v2 — Uses TikTok's language field + bio analysis.
Scans from highest followers down. For each creator:
1. Scrape TikTok profile to get language field
2. Analyze bio for country/category signals
3. Update DB with corrected country and categories

Language mapping:
  id = Indonesian, ms/my = Malay, en = English (need bio for country),
  tl = Filipino/Tagalog, th = Thai, vi = Vietnamese, 
  ja = Japanese, ko = Korean, zh = Chinese, es = Spanish, pt = Portuguese

Run: PLAYWRIGHT_BROWSERS_PATH=0 python3 -u scraper/smart_verifier.py 2>&1 | tee scraper/smart_verifier.log
"""
import asyncio, json, sqlite3, random, re, sys, time
from datetime import datetime, timezone
from playwright.async_api import async_playwright

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'

LANG_TO_COUNTRY = {
    'id': 'ID', 'ms': 'MY', 'my': 'MY', 'tl': 'PH', 'fil': 'PH',
    'th': 'TH', 'vi': 'VN', 'ja': 'JP', 'ko': 'KR',
    'zh': 'CN', 'zh-Hans': 'CN', 'zh-Hant': 'TW',
    'es': 'LATAM', 'pt': 'BR', 'ru': 'RU', 'hi': 'IN',
    'ar': 'AR_LANG', 'fr': 'FR', 'de': 'DE', 'tr': 'TR',
}

CATEGORY_SIGNALS = {
    'gaming': ['game', 'gaming', 'gamer', 'esport', 'mlbb', 'mobile legends', 'pubg', 'valorant', 'free fire',
               'roblox', 'minecraft', 'fortnite', 'streamer', 'gameplay', '🎮', 'honor of kings', 'ff', 'mabar'],
    'beauty': ['beauty', 'makeup', 'skincare', 'cosmetic', 'grwm', 'cantik', '💄', '💋', 'foundation', 'lipstick'],
    'food': ['food', 'cook', 'recipe', 'makan', 'masak', 'mukbang', 'foodie', 'chef', '🍜', 'resipi', 'kuliner'],
    'music': ['music', 'song', 'singer', 'dance', 'dancer', 'dancing', 'choreography', 'rapper', 'dj', '🎵', '🎤', '💃', 'penyanyi'],
    'comedy': ['comedy', 'funny', 'humor', 'skit', 'prank', 'lawak', 'komedi', 'lucu', '😂', 'parody'],
    'fashion': ['fashion', 'style', 'ootd', 'outfit', 'hijab', 'streetwear', 'thrift', '👗'],
    'tech': ['tech', 'gadget', 'smartphone', 'review', 'unboxing', 'iphone', 'samsung', '📱'],
    'fitness': ['fitness', 'gym', 'workout', 'exercise', '💪', 'bodybuilding'],
    'travel': ['travel', 'wanderlust', 'adventure', 'explore', '✈️', 'backpack'],
    'education': ['education', 'learn', 'study', 'teach', 'belajar', '📚', 'tutor'],
    'family': ['parenting', 'mom', 'dad', 'family', 'baby', 'keluarga', '👶', 'ibu'],
    'pets': ['pet', 'cat', 'dog', 'kucing', 'anjing', '🐱', '🐕'],
    'automotive': ['car', 'motor', 'kereta', 'motorsport', 'racing', '🚗'],
    'finance': ['finance', 'business', 'entrepreneur', 'investing', 'crypto', 'trading', '💰', 'ceo', 'founder'],
    'religious': ['ustaz', 'dakwah', 'islam', 'ceramah', 'quran'],
    'cosplay': ['cosplay', 'cosplayer', 'anime', 'coser', 'costume'],
    'lifestyle': ['lifestyle', 'vlog', 'daily', 'routine', 'aesthetic', 'life'],
}

def bio_country(bio, name, username):
    """Fallback country detection from bio text."""
    text = f'{bio} {name} {username}'.lower()
    # Phone numbers
    if '+62' in text: return 'ID'
    if '+63' in text: return 'PH'
    if '+65' in text: return 'SG'
    if '+66' in text: return 'TH'
    if '+84' in text: return 'VN'
    if '+60' in text: return 'MY'
    # Username signals
    if username.endswith('.id') or '.id' in username: return 'ID'
    if username.endswith('.ph') or '.ph' in username: return 'PH'
    if username.endswith('.my'): return 'MY'
    if username.endswith('.sg'): return 'SG'
    # Flags
    for flag, country in [('🇲🇾','MY'),('🇮🇩','ID'),('🇸🇬','SG'),('🇹🇭','TH'),('🇵🇭','PH'),('🇻🇳','VN'),('🇺🇸','US'),('🇧🇷','BR'),('🇲🇽','MX'),('🇯🇵','JP'),('🇰🇷','KR')]:
        if flag in text: return country
    # Keywords
    for country, words in {
        'MY': ['malaysia','kuala lumpur','melayu','sabah','sarawak','johor','penang','selangor'],
        'ID': ['indonesia','jakarta','surabaya','bandung','bali','yogyakarta','medan'],
        'PH': ['philippines','filipino','filipina','manila','cebu','davao','pinoy','pinay'],
        'TH': ['thailand','thai','bangkok','chiang mai'],
        'VN': ['vietnam','vietnamese','hanoi','ho chi minh','saigon'],
        'SG': ['singapore','singaporean'],
    }.items():
        if any(w in text for w in words): return country
    # Script detection
    if re.search(r'[\u0E00-\u0E7F]', text): return 'TH'
    if re.search(r'[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]', text): return 'VN'
    if re.search(r'[\u0400-\u04FF]', text): return 'RU'
    if re.search(r'[\uAC00-\uD7AF]', text): return 'KR'
    if re.search(r'[\u3040-\u30FF]', text): return 'JP'
    return None

def detect_category(bio, name):
    text = f'{bio} {name}'.lower()
    scores = {}
    for cat, words in CATEGORY_SIGNALS.items():
        score = sum(1 for w in words if w in text)
        if score > 0: scores[cat] = score
    if scores:
        top = sorted(scores, key=scores.get, reverse=True)[:2]
        return top
    return None

async def main():
    conn = sqlite3.connect(DB_PATH)
    # Get creators that need fixing, ordered by followers
    creators = conn.execute("""
        SELECT c.id, c.name, c.country, c.categories, c.bio, pp.username, pp.followers
        FROM creators c JOIN platform_presences pp ON pp.creator_id = c.id
        WHERE pp.platform = 'tiktok'
        AND (c.country = 'SEA' OR c.country = '' OR c.categories = '["entertainment"]')
        ORDER BY pp.followers DESC
    """).fetchall()
    conn.close()

    print(f'🔍 SMART VERIFIER v2 — {len(creators)} creators to scan')
    print(f'{"="*60}')
    sys.stdout.flush()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080})

        country_fixes = 0
        cat_fixes = 0
        scanned = 0

        for i, (cid, name, country, cats, bio, username, followers) in enumerate(creators):
            scanned += 1

            # Scrape TikTok for language field (ALL creators — language field is the best signal)
            lang = None
            fresh_bio = bio
            if True:  # Scrape ALL, not just top 2000
                page = await ctx.new_page()
                try:
                    await page.goto(f'https://www.tiktok.com/@{username}', wait_until='domcontentloaded', timeout=12000)
                    await asyncio.sleep(1)
                    data = await page.evaluate('()=>{const e=document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");return e?e.textContent:null}')
                    if data:
                        parsed = json.loads(data)
                        ud = parsed.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {})
                        if 'userInfo' in ud:
                            u = ud['userInfo']['user']
                            lang = u.get('language', '')
                            fresh_bio = u.get('signature', '') or bio
                except Exception as e:
                    if scanned <= 10:
                        print(f'  ⚠️ @{username}: scrape error: {e}')
                        sys.stdout.flush()
                try:
                    await page.close()
                except: pass
                await asyncio.sleep(random.uniform(1, 2))

                # Rotate context
                if scanned % 50 == 0:
                    await ctx.close()
                    ctx = await browser.new_context(
                        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                        viewport={'width': 1920, 'height': 1080})

            # Determine country
            new_country = None
            if lang and lang in LANG_TO_COUNTRY:
                mapped = LANG_TO_COUNTRY[lang]
                if mapped not in ('LATAM', 'AR_LANG'):
                    new_country = mapped
                elif mapped == 'LATAM':
                    # Try to narrow down from bio
                    bc = bio_country(fresh_bio or '', name, username)
                    new_country = bc if bc else 'LATAM'
            
            if not new_country:
                new_country = bio_country(fresh_bio or '', name, username)

            # For English speakers (lang=en), use bio signals
            if lang == 'en' and not new_country:
                new_country = bio_country(fresh_bio or '', name, username)

            # Determine category
            new_cats = None
            if cats in ('["entertainment"]', '[]', ''):
                detected = detect_category(fresh_bio or '', name)
                if detected:
                    new_cats = json.dumps(detected)

            # Update if changed
            if new_country and new_country != country:
                conn = sqlite3.connect(DB_PATH)
                conn.execute("UPDATE creators SET country=? WHERE id=?", (new_country, cid))
                conn.commit()
                conn.close()
                country_fixes += 1
                if followers > 500000 or scanned <= 200:
                    print(f'  🌍 @{username} ({followers:,}): {country}→{new_country} [lang={lang}] | {name}')
                    sys.stdout.flush()

            if new_cats and new_cats != cats:
                conn = sqlite3.connect(DB_PATH)
                conn.execute("UPDATE creators SET categories=? WHERE id=?", (new_cats, cid))
                conn.commit()
                conn.close()
                cat_fixes += 1
                if followers > 500000 or scanned <= 200:
                    print(f'  🏷️ @{username} ({followers:,}): {cats}→{new_cats}')
                    sys.stdout.flush()

            if scanned % 50 == 0:
                print(f'  📊 Scanned: {scanned}/{len(creators)} | Country: {country_fixes} | Category: {cat_fixes}')
                sys.stdout.flush()
            elif scanned <= 5:
                print(f'  [{scanned}] @{username} lang={lang} country={country}→{new_country or "no change"} cats={cats}→{new_cats or "no change"}')
                sys.stdout.flush()

        await browser.close()

    conn = sqlite3.connect(DB_PATH)
    print(f'\n{"="*60}')
    print(f'DONE | Scanned: {scanned} | Country fixes: {country_fixes} | Category fixes: {cat_fixes}')
    print(f'\nCountry distribution:')
    for row in conn.execute('SELECT country, COUNT(*) FROM creators GROUP BY country ORDER BY COUNT(*) DESC LIMIT 15'):
        print(f'  {row[0]}: {row[1]}')
    conn.close()
    sys.stdout.flush()

if __name__ == '__main__':
    asyncio.run(main())
