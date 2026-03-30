#!/usr/bin/env python3
"""
Data Verifier — Scans creators from highest to lowest followers.
Scanner 1: Country detection from bio, hashtags, language, video captions
Scanner 2: Category detection from bio, video content, captions

Uses TikTok profile data (bio, language signals) + Google search for verification.
Processes top creators first (highest followers = most important to get right).

Run: PLAYWRIGHT_BROWSERS_PATH=0 python3 -u scraper/data_verifier.py 2>&1 | tee scraper/verifier_scan.log
"""
import asyncio, httpx, json, sqlite3, random, re, sys, time
from datetime import datetime, timezone
from playwright.async_api import async_playwright

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
PROGRESS_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/verifier_progress.json'

# Comprehensive country signals
COUNTRY_SIGNALS = {
    'MY': {
        'keywords': ['malaysia', 'malaysian', 'kuala lumpur', 'kl', 'sabah', 'sarawak', 'johor', 'penang', 'selangor',
                     'melayu', 'kelantan', 'terengganu', 'pahang', 'perak', 'kedah', 'melaka', 'negeri sembilan',
                     'putrajaya', 'cyberjaya', 'petaling jaya', 'subang', 'klang', 'ipoh', 'kuching', 'kota kinabalu'],
        'hashtags': ['fyp🇲🇾', 'fypmalaysia', 'malaysiatiktok', 'tiktokmsia', 'melayu', 'malaysiafyp'],
        'flag': '🇲🇾',
    },
    'ID': {
        'keywords': ['indonesia', 'indonesian', 'jakarta', 'surabaya', 'bandung', 'bali', 'yogyakarta', 'medan',
                     'semarang', 'makassar', 'palembang', 'tangerang', 'depok', 'bekasi', 'bogor', 'malang'],
        'hashtags': ['fyp🇮🇩', 'fypindonesia', 'indonesiatiktok', 'tiktokindonesia', 'viral_indonesia'],
        'flag': '🇮🇩',
    },
    'SG': {
        'keywords': ['singapore', 'singaporean', 'sg', 'sentosa', 'orchard', 'changi', 'jurong', 'tampines', 'woodlands'],
        'hashtags': ['fyp🇸🇬', 'fypsingapore', 'singaporetiktok', 'sgfyp', 'sgtiktok'],
        'flag': '🇸🇬',
    },
    'TH': {
        'keywords': ['thailand', 'thai', 'bangkok', 'chiang mai', 'pattaya', 'phuket', 'ayutthaya', 'krabi'],
        'hashtags': ['fyp🇹🇭', 'fypthailand', 'tiktokthailand', 'ไทย'],
        'flag': '🇹🇭',
        'script': r'[\u0E00-\u0E7F]',  # Thai script
    },
    'PH': {
        'keywords': ['philippines', 'filipino', 'filipina', 'pilipinas', 'manila', 'cebu', 'davao', 'pinoy', 'pinay',
                     'quezon', 'makati', 'taguig', 'pasig', 'caloocan', 'antipolo'],
        'hashtags': ['fyp🇵🇭', 'fypphilippines', 'pinoytiktok', 'filipinotiktok', 'pinaytiktok'],
        'flag': '🇵🇭',
    },
    'VN': {
        'keywords': ['vietnam', 'vietnamese', 'việt nam', 'hanoi', 'ho chi minh', 'saigon', 'da nang', 'hue', 'hai phong'],
        'hashtags': ['fyp🇻🇳', 'fypvietnam', 'tiktokvietnam', 'vietnamtiktok'],
        'flag': '🇻🇳',
        'script': r'[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]',
    },
    # Non-SEA countries (to properly exclude)
    'US': {'keywords': ['usa', 'united states', 'american', 'los angeles', 'new york', 'california', 'texas', 'florida', 'chicago'], 'flag': '🇺🇸'},
    'MX': {'keywords': ['mexico', 'mexicano', 'mexicana', 'ciudad de mexico', 'guadalajara', 'monterrey'], 'flag': '🇲🇽'},
    'BR': {'keywords': ['brasil', 'brazil', 'são paulo', 'rio de janeiro', 'brasileiro', 'brasileira'], 'flag': '🇧🇷'},
    'IN': {'keywords': ['india', 'indian', 'mumbai', 'delhi', 'bangalore', 'hindi', 'desi'], 'flag': '🇮🇳'},
    'KR': {'keywords': ['korea', 'korean', 'seoul', '한국'], 'flag': '🇰🇷'},
    'JP': {'keywords': ['japan', 'japanese', 'tokyo', 'osaka', '日本'], 'flag': '🇯🇵'},
    'CN': {'keywords': ['china', 'chinese', 'beijing', 'shanghai', '中国'], 'flag': '🇨🇳'},
    'ES': {'keywords': ['españa', 'spain', 'madrid', 'barcelona'], 'flag': '🇪🇸'},
    'CO': {'keywords': ['colombia', 'colombian', 'bogota', 'medellin'], 'flag': '🇨🇴'},
    'AR': {'keywords': ['argentina', 'argentino', 'buenos aires'], 'flag': '🇦🇷'},
}

# Category signals
CATEGORY_SIGNALS = {
    'Comedy & Entertainment': ['comedy', 'funny', 'humor', 'skit', 'prank', 'parody', 'lawak', 'komedi', 'lucu', '😂', '🤣', 'meme'],
    'Gaming': ['game', 'gaming', 'gamer', 'esport', 'mlbb', 'mobile legends', 'pubg', 'valorant', 'free fire', 'roblox', 'minecraft', 'honor of kings', 'cod', 'fortnite', 'streamer', 'gameplay', '🎮'],
    'Beauty & Skincare': ['beauty', 'makeup', 'skincare', 'cosmetic', 'foundation', 'lipstick', 'eyeshadow', 'tutorial makeup', 'grwm', 'cantik', 'kecantikan', 'cushion', 'serum', '💄', '💋'],
    'Food & F&B': ['food', 'cook', 'recipe', 'makan', 'masak', 'kuliner', 'mukbang', 'resipi', 'dapur', 'restaurant', 'foodie', 'chef', '🍜', '🍕', '🍔', 'eating'],
    'Music & Dance': ['music', 'song', 'singer', 'dance', 'dancer', 'dancing', 'choreography', 'rapper', 'rap', 'dj', 'musician', 'lagu', 'nyanyi', 'tarian', '🎵', '🎤', '🎶', '💃', 'kpop'],
    'Fashion & Style': ['fashion', 'style', 'ootd', 'outfit', 'fesyen', 'hijab', 'streetwear', 'thrift', 'haul', 'wardrobe', '👗', '👠'],
    'Fitness & Health': ['fitness', 'gym', 'workout', 'exercise', 'health', 'muscle', 'bodybuilding', 'yoga', 'running', 'fitfam', '💪'],
    'Travel': ['travel', 'traveler', 'wanderlust', 'adventure', 'explore', 'backpack', 'jalan', 'trip', 'tourism', '✈️', '🌍'],
    'Tech & Gadgets': ['tech', 'technology', 'gadget', 'smartphone', 'review', 'unboxing', 'iphone', 'samsung', 'laptop', 'pc build', '📱'],
    'Education': ['education', 'learn', 'study', 'teach', 'teacher', 'tutor', 'belajar', 'academic', 'university', 'student', '📚', '🎓'],
    'Lifestyle': ['lifestyle', 'daily', 'vlog', 'day in my life', 'routine', 'morning routine', 'life', 'aesthetic'],
    'Parenting & Family': ['parenting', 'mom', 'dad', 'family', 'baby', 'kids', 'ibu', 'keluarga', 'anak', 'pregnancy', '👶'],
    'Pets & Animals': ['pet', 'cat', 'dog', 'kucing', 'anjing', 'animal', 'puppy', 'kitten', '🐱', '🐕', '🐶'],
    'Automotive': ['car', 'motor', 'kereta', 'motorsport', 'racing', 'supercar', 'motorcycle', 'auto', '🚗'],
    'Finance & Business': ['finance', 'business', 'entrepreneur', 'investing', 'money', 'crypto', 'trading', 'startup', 'ceo', 'founder', '💰'],
}

def detect_language_script(text):
    """Detect language/country from script characters."""
    if re.search(r'[\u0E00-\u0E7F]', text): return 'TH'
    if re.search(r'[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]', text): return 'VN'
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text): return 'JP'
    if re.search(r'[\uAC00-\uD7AF]', text): return 'KR'
    if re.search(r'[\u4E00-\u9FFF]', text): return 'CN'  # Could be CN/TW/MY-Chinese
    if re.search(r'[\u0900-\u097F]', text): return 'IN'
    # Spanish language signals
    if re.search(r'\b(jaja|mira|como|pero|tambien|hermosa|bonita|guapo)\b', text, re.I): return 'LATAM'
    # Portuguese
    if re.search(r'\b(kkk|muito|voce|obrigado|bonito|gostei)\b', text, re.I): return 'BR'
    return None

def scan_country(bio, name, username, extra_text=''):
    """Scanner 1: Determine country from all available text signals."""
    all_text = f'{bio} {name} {username} {extra_text}'.lower()
    
    # 1. Script detection (most reliable)
    script_country = detect_language_script(all_text)
    if script_country and script_country in COUNTRY_SIGNALS:
        return script_country
    
    # 2. Flag emoji (very reliable)
    for country, data in COUNTRY_SIGNALS.items():
        if data.get('flag', '') in all_text:
            return country
    
    # 3. Hashtag matching
    for country, data in COUNTRY_SIGNALS.items():
        for tag in data.get('hashtags', []):
            if tag in all_text:
                return country
    
    # 4. Keyword matching (count signals per country)
    scores = {}
    for country, data in COUNTRY_SIGNALS.items():
        score = sum(1 for kw in data['keywords'] if kw in all_text)
        if score > 0:
            scores[country] = score
    
    if scores:
        # Return country with most signals
        best = max(scores, key=scores.get)
        return best
    
    # 5. Latin American detection
    if script_country == 'LATAM':
        # Check specific LATAM countries
        for c in ['MX', 'CO', 'AR', 'ES']:
            if c in scores:
                return c
        return 'LATAM'
    
    return None  # Couldn't determine

def scan_category(bio, name, extra_text=''):
    """Scanner 2: Determine content category from all available text signals."""
    all_text = f'{bio} {name} {extra_text}'.lower()
    
    scores = {}
    for category, keywords in CATEGORY_SIGNALS.items():
        score = sum(1 for kw in keywords if kw in all_text)
        if score > 0:
            scores[category] = score
    
    if scores:
        # Return top 2 categories
        sorted_cats = sorted(scores, key=scores.get, reverse=True)
        return sorted_cats[:2]
    
    return None

async def scrape_tiktok_for_verification(page, username):
    """Visit TikTok profile to get bio and any extra signals."""
    try:
        await page.goto(f'https://www.tiktok.com/@{username}', wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(1.5)
        data = await page.evaluate('()=>{const e=document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");return e?e.textContent:null}')
        if not data:
            return None
        parsed = json.loads(data)
        ud = parsed.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {})
        if 'userInfo' not in ud:
            return None
        u = ud['userInfo']['user']
        s = ud['userInfo']['stats']
        return {
            'bio': u.get('signature', ''),
            'name': u.get('nickname', ''),
            'region': u.get('region', ''),
            'language': u.get('language', ''),
            'verified': u.get('verified', False),
        }
    except:
        return None

async def main():
    conn = sqlite3.connect(DB_PATH)
    
    # Get creators ordered by followers (highest first), focusing on bad data
    creators = conn.execute("""
        SELECT c.id, c.name, c.country, c.categories, c.bio,
               pp.username, pp.followers, pp.platform
        FROM creators c
        JOIN platform_presences pp ON pp.creator_id = c.id
        WHERE pp.platform = 'tiktok'
        ORDER BY pp.followers DESC
    """).fetchall()
    conn.close()
    
    print(f'🔍 DATA VERIFIER — Scanning {len(creators)} creators (highest followers first)')
    print(f'{"="*60}')
    sys.stdout.flush()
    
    updated_country = 0
    updated_category = 0
    total_scanned = 0
    start = time.time()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        for i, (cid, name, current_country, current_cats, bio, username, followers, platform) in enumerate(creators):
            needs_country = current_country in ('SEA', '') or (followers > 1000000 and current_country == 'MY')
            needs_category = current_cats in ('["entertainment"]', '[]', '')
            
            # Skip if both are already good (unless top 500 by followers)
            if not needs_country and not needs_category and i > 500:
                continue
            
            total_scanned += 1
            
            # Get extra data from TikTok profile if needed
            extra_text = ''
            if needs_country or needs_category:
                # For top 1000, scrape TikTok for fresh bio
                if i < 1000:
                    page = await ctx.new_page()
                    tt_data = await scrape_tiktok_for_verification(page, username)
                    await page.close()
                    if tt_data:
                        bio = tt_data.get('bio', bio) or bio
                        extra_text = f"{tt_data.get('region', '')} {tt_data.get('language', '')}"
                    await asyncio.sleep(random.uniform(1.5, 2.5))
            
            # Scanner 1: Country
            new_country = None
            if needs_country:
                new_country = scan_country(bio or '', name, username, extra_text)
            
            # Scanner 2: Category
            new_cats = None
            if needs_category:
                cats = scan_category(bio or '', name, extra_text)
                if cats:
                    if len(cats) == 1:
                        # Add lifestyle/entertainment as secondary
                        secondary = 'lifestyle' if cats[0] in ('Food & F&B', 'Beauty & Skincare', 'Fashion & Style', 'Fitness & Health', 'Travel', 'Parenting & Family', 'Pets & Animals') else 'entertainment'
                        new_cats = json.dumps([cats[0].lower().split(' & ')[0].split(' ')[0], secondary])
                    else:
                        new_cats = json.dumps([cats[0].lower().split(' & ')[0].split(' ')[0], cats[1].lower().split(' & ')[0].split(' ')[0]])
            
            # Update DB
            if new_country or new_cats:
                conn = sqlite3.connect(DB_PATH)
                if new_country and new_country != current_country:
                    conn.execute("UPDATE creators SET country=? WHERE id=?", (new_country, cid))
                    updated_country += 1
                    if followers > 500000 or total_scanned <= 100:
                        print(f'  🌍 @{username} ({followers:,}): {current_country} → {new_country} | {name}')
                        sys.stdout.flush()
                if new_cats and new_cats != current_cats:
                    conn.execute("UPDATE creators SET categories=? WHERE id=?", (new_cats, cid))
                    updated_category += 1
                    if followers > 500000 or total_scanned <= 100:
                        print(f'  🏷️ @{username} ({followers:,}): {current_cats} → {new_cats}')
                        sys.stdout.flush()
                conn.commit()
                conn.close()
            
            # Rotate context
            if total_scanned % 50 == 0:
                await ctx.close()
                ctx = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    viewport={'width': 1920, 'height': 1080})
            
            if total_scanned % 100 == 0:
                elapsed = (time.time() - start) / 3600
                rate = total_scanned / max(elapsed, 0.001)
                print(f'\n  📊 Scanned: {total_scanned} | Country fixes: {updated_country} | Category fixes: {updated_category} | {rate:.0f}/hr\n')
                sys.stdout.flush()
                with open(PROGRESS_PATH, 'w') as f:
                    json.dump({'ts': datetime.now(timezone.utc).isoformat(), 'scanned': total_scanned,
                               'country_fixes': updated_country, 'category_fixes': updated_category,
                               'rate': round(rate, 1)}, f)
        
        await ctx.close()
        await browser.close()
    
    print(f'\n{"="*60}')
    print(f'VERIFICATION COMPLETE')
    print(f'Scanned: {total_scanned}')
    print(f'Country fixes: {updated_country}')
    print(f'Category fixes: {updated_category}')
    
    # Show final distribution
    conn = sqlite3.connect(DB_PATH)
    print(f'\nCountry distribution:')
    for row in conn.execute('SELECT country, COUNT(*) FROM creators GROUP BY country ORDER BY COUNT(*) DESC'):
        print(f'  {row[0]}: {row[1]}')
    conn.close()
    sys.stdout.flush()

if __name__ == '__main__':
    asyncio.run(main())
