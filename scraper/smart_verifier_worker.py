#!/usr/bin/env python3
"""
Smart Verifier Worker — Parallel version.
Usage: python3 smart_verifier_worker.py <worker_id> <num_workers>
  e.g. python3 smart_verifier_worker.py 0 4  (worker 0 of 4)

Each worker takes every Nth creator (round-robin by worker_id).
"""
import asyncio, json, sqlite3, random, re, sys, time
from datetime import datetime, timezone
from playwright.async_api import async_playwright

WORKER_ID = int(sys.argv[1])
NUM_WORKERS = int(sys.argv[2])

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'

# TikTok language → country mapping
LANG_TO_COUNTRY = {
    'id': 'ID', 'ms': 'MY', 'my': 'MY', 'tl': 'PH', 'fil': 'PH',
    'th': 'TH', 'vi': 'VN', 'ja': 'JP', 'ko': 'KR',
    'zh': 'CN', 'zh-Hans': 'CN', 'zh-Hant': 'TW',
    'es': 'LATAM', 'pt': 'BR', 'ru': 'RU', 'hi': 'IN',
    'ar': 'AE', 'fr': 'FR', 'de': 'DE', 'tr': 'TR',
    'uk': 'UA', 'pl': 'PL', 'it': 'IT', 'nl': 'NL',
    'sv': 'SE', 'da': 'DK', 'no': 'NO', 'fi': 'FI',
    'ro': 'RO', 'hu': 'HU', 'cs': 'CZ', 'el': 'GR',
    'he': 'IL', 'bn': 'BD', 'ta': 'IN', 'te': 'IN',
    'mr': 'IN', 'ur': 'PK', 'fa': 'IR', 'sw': 'KE',
}

REGION_TO_COUNTRY = {
    'MY': 'MY', 'ID': 'ID', 'SG': 'SG', 'TH': 'TH', 'PH': 'PH', 'VN': 'VN',
    'US': 'US', 'GB': 'GB', 'BR': 'BR', 'MX': 'MX', 'JP': 'JP', 'KR': 'KR',
    'IN': 'IN', 'AE': 'AE', 'SA': 'SA', 'AU': 'AU', 'CA': 'CA', 'DE': 'DE',
    'FR': 'FR', 'IT': 'IT', 'ES': 'ES', 'RU': 'RU', 'TR': 'TR', 'PK': 'PK',
    'BD': 'BD', 'NG': 'NG', 'EG': 'EG', 'TW': 'TW', 'HK': 'HK',
}

CATEGORY_SIGNALS = {
    'gaming': ['game', 'gaming', 'gamer', 'esport', 'mlbb', 'mobile legends', 'pubg', 'valorant', 'free fire',
               'roblox', 'minecraft', 'fortnite', 'streamer', 'gameplay', '🎮', 'honor of kings', 'ff', 'mabar',
               'codm', 'call of duty', 'apex', 'dota', 'league of legends', 'lol', 'twitch'],
    'beauty': ['beauty', 'makeup', 'skincare', 'cosmetic', 'grwm', 'cantik', '💄', '💋', 'foundation', 'lipstick',
               'tutorial makeup', 'kecantikan', 'concealer', 'mascara', 'beautytips'],
    'food': ['food', 'cook', 'recipe', 'makan', 'masak', 'mukbang', 'foodie', 'chef', '🍜', 'resipi', 'kuliner',
             'restaurant', 'baking', 'dapur', 'masakan', 'makanan', 'foodtiktok', 'asmr food'],
    'music': ['music', 'song', 'singer', 'rapper', 'dj', '🎵', '🎤', 'penyanyi', 'musician',
              'producer', 'beat', 'album', 'spotify', 'soundcloud', 'vocalist', 'band'],
    'dance': ['dance', 'dancer', 'dancing', 'choreography', '💃', 'kpop dance', 'hip hop dance',
              'ballet', 'contemporary', 'freestyle'],
    'comedy': ['comedy', 'funny', 'humor', 'skit', 'prank', 'lawak', 'komedi', 'lucu', '😂', 'parody',
               'meme', 'joke', 'stand up', 'comedian'],
    'fashion': ['fashion', 'style', 'ootd', 'outfit', 'hijab', 'streetwear', 'thrift', '👗',
                'fesyen', 'clothing', 'brand', 'model'],
    'tech': ['tech', 'gadget', 'smartphone', 'unboxing', 'iphone', 'samsung', '📱',
             'laptop', 'pc build', 'software', 'coding', 'programming', 'developer'],
    'fitness': ['fitness', 'gym', 'workout', 'exercise', '💪', 'bodybuilding', 'crossfit',
                'yoga', 'health', 'nutrition', 'diet', 'muscle'],
    'travel': ['travel', 'wanderlust', 'adventure', 'explore', '✈️', 'backpack', 'hotel',
               'tourism', 'trip', 'destination', 'vlog travel'],
    'education': ['education', 'learn', 'study', 'teach', 'belajar', '📚', 'tutor',
                  'university', 'school', 'knowledge', 'educational'],
    'family': ['parenting', 'mom', 'dad', 'family', 'baby', 'keluarga', '👶', 'ibu',
               'anak', 'wife', 'husband', 'pregnant', 'toddler'],
    'pets': ['pet', 'cat', 'dog', 'kucing', 'anjing', '🐱', '🐕', 'kitten', 'puppy', 'animal'],
    'automotive': ['car', 'motor', 'kereta', 'motorsport', 'racing', '🚗', 'bike', 'motorcycle',
                   'supercar', 'drift', 'modifikasi', 'otomotif'],
    'finance': ['finance', 'business', 'entrepreneur', 'investing', 'crypto', 'trading', '💰',
                'ceo', 'founder', 'startup', 'money', 'passive income', 'saham'],
    'religious': ['ustaz', 'dakwah', 'islam', 'ceramah', 'quran', 'sunnah', 'hijrah',
                  'christian', 'gospel', 'church', 'prayer'],
    'cosplay': ['cosplay', 'cosplayer', 'anime', 'coser', 'costume', 'manga', 'otaku'],
    'lifestyle': ['lifestyle', 'vlog', 'daily', 'routine', 'aesthetic', 'life', 'haul',
                  'minimalist', 'productivity', 'self care'],
    'sports': ['football', 'soccer', 'basketball', 'badminton', 'boxing', 'mma', 'ufc',
               'cricket', 'tennis', 'athlete', 'sukan', 'bola'],
    'art': ['artist', 'drawing', 'painting', 'illustration', 'digital art', 'sketch',
            'seni', 'illustrator', 'watercolor'],
}

def bio_country(bio, name, username):
    text = f'{bio} {name} {username}'.lower()
    for code, country in [('+62','ID'),('+63','PH'),('+65','SG'),('+66','TH'),('+84','VN'),('+60','MY')]:
        if code in text: return country
    for flag, country in [('🇲🇾','MY'),('🇮🇩','ID'),('🇸🇬','SG'),('🇹🇭','TH'),('🇵🇭','PH'),('🇻🇳','VN'),
                           ('🇺🇸','US'),('🇧🇷','BR'),('🇲🇽','MX'),('🇯🇵','JP'),('🇰🇷','KR'),('🇬🇧','GB'),
                           ('🇦🇺','AU'),('🇮🇳','IN'),('🇦🇪','AE'),('🇸🇦','SA'),('🇹🇼','TW'),('🇭🇰','HK'),
                           ('🇩🇪','DE'),('🇫🇷','FR'),('🇮🇹','IT'),('🇪🇸','ES'),('🇨🇦','CA'),('🇳🇬','NG'),
                           ('🇵🇰','PK'),('🇧🇩','BD'),('🇪🇬','EG'),('🇹🇷','TR'),('🇷🇺','RU')]:
        if flag in text: return country
    for country, words in {
        'MY': ['malaysia','kuala lumpur','kl','melayu','sabah','sarawak','johor','penang','selangor','melaka','perak','pahang','kedah','kelantan','terengganu','putrajaya'],
        'ID': ['indonesia','jakarta','surabaya','bandung','bali','yogyakarta','medan','semarang','makassar','palembang','malang'],
        'PH': ['philippines','filipino','filipina','manila','cebu','davao','pinoy','pinay','quezon','makati','taguig'],
        'TH': ['thailand','thai','bangkok','chiang mai','phuket','pattaya'],
        'VN': ['vietnam','vietnamese','hanoi','ho chi minh','saigon','hcmc','da nang'],
        'SG': ['singapore','singaporean'],
        'US': ['united states','usa','los angeles','new york','nyc','chicago','houston','miami','atlanta','california','texas','florida'],
        'GB': ['united kingdom','london','england','manchester','birmingham'],
        'BR': ['brasil','brazil','são paulo','rio de janeiro','recife'],
        'MX': ['mexico','ciudad de mexico','guadalajara','monterrey','cdmx'],
        'IN': ['india','mumbai','delhi','bangalore','kolkata','chennai','hyderabad'],
        'JP': ['japan','tokyo','osaka'],
        'KR': ['korea','seoul','busan'],
    }.items():
        if any(w in text for w in words): return country
    if re.search(r'[\u0E00-\u0E7F]', text): return 'TH'
    if re.search(r'[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]', text): return 'VN'
    if re.search(r'[\uAC00-\uD7AF]', text): return 'KR'
    if re.search(r'[\u3040-\u30FF]', text): return 'JP'
    return None

def detect_category(bio, name, nickname=''):
    text = f'{bio} {name} {nickname}'.lower()
    scores = {}
    for cat, words in CATEGORY_SIGNALS.items():
        score = sum(1 for w in words if w in text)
        if score > 0: scores[cat] = score
    strong_cats = {cat: s for cat, s in scores.items() if s >= 2}
    if strong_cats:
        top = sorted(strong_cats, key=strong_cats.get, reverse=True)[:2]
        return top
    if scores:
        top_cat = max(scores, key=scores.get)
        if scores[top_cat] == 1:
            specific_cats = {'gaming', 'cosplay', 'automotive', 'religious', 'pets'}
            if top_cat in specific_cats:
                return [top_cat]
    return None

async def scrape_tiktok(page, username):
    try:
        await page.goto(f'https://www.tiktok.com/@{username}', wait_until='domcontentloaded', timeout=12000)
        await asyncio.sleep(1)
        data = await page.evaluate('()=>{const e=document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");return e?e.textContent:null}')
        if not data:
            return {'status': 'no_data'}
        parsed = json.loads(data)
        ud = parsed.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {})
        if 'userInfo' not in ud:
            code = ud.get('statusCode', 0)
            return {'status': 'captcha' if code == 10221 else 'not_found'}
        u = ud['userInfo']['user']
        s = ud['userInfo']['stats']
        return {
            'status': 'found',
            'language': u.get('language', ''),
            'region': u.get('region', ''),
            'bio': u.get('signature', ''),
            'nickname': u.get('nickname', ''),
            'username': u.get('uniqueId', username),
            'followers': s.get('followerCount', 0),
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

async def main():
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    
    all_creators = conn.execute("""
        SELECT c.id, c.name, c.country, c.categories, c.bio, pp.username, pp.followers
        FROM creators c JOIN platform_presences pp ON pp.creator_id = c.id
        WHERE pp.platform = 'tiktok'
        ORDER BY 
            CASE WHEN c.country = 'SEA' THEN 0 
                 WHEN c.categories = '["entertainment"]' THEN 1 
                 ELSE 2 END,
            pp.followers DESC
    """).fetchall()
    conn.close()

    # Round-robin: this worker takes every Nth row
    creators = [c for i, c in enumerate(all_creators) if i % NUM_WORKERS == WORKER_ID]

    print(f'{"="*60}')
    print(f'WORKER {WORKER_ID}/{NUM_WORKERS} — {now}')
    print(f'{len(creators)} creators to scan (of {len(all_creators)} total)')
    print(f'{"="*60}')
    sys.stdout.flush()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080})

        country_fixes = 0
        cat_fixes = 0
        bio_updates = 0
        scanned = 0
        captchas = 0
        consecutive_captchas = 0
        errors = 0

        for i, (cid, name, country, cats, bio, username, followers) in enumerate(creators):
            scanned += 1
            
            page = await ctx.new_page()
            result = await scrape_tiktok(page, username)
            try:
                await page.close()
            except: pass
            await asyncio.sleep(random.uniform(0.8, 1.5))

            if result['status'] == 'captcha':
                captchas += 1
                consecutive_captchas += 1
                if consecutive_captchas > 5:
                    print(f'  ⚠️ W{WORKER_ID}: {consecutive_captchas} consecutive captchas, rotating + cooling...')
                    sys.stdout.flush()
                    await ctx.close()
                    await asyncio.sleep(random.uniform(8, 15))
                    ctx = await browser.new_context(
                        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                        viewport={'width': 1920, 'height': 1080})
                    consecutive_captchas = 0
                continue
            
            consecutive_captchas = 0
            
            if result['status'] in ('error', 'no_data', 'not_found'):
                errors += 1
                continue

            lang = result.get('language', '')
            region = result.get('region', '')
            fresh_bio = result.get('bio', '') or bio
            nickname = result.get('nickname', '')

            # === COUNTRY ===
            new_country = None
            if region and region in REGION_TO_COUNTRY:
                new_country = REGION_TO_COUNTRY[region]
            if not new_country and lang and lang != 'en' and lang in LANG_TO_COUNTRY:
                mapped = LANG_TO_COUNTRY[lang]
                if mapped not in ('LATAM', 'AE'):
                    new_country = mapped
                else:
                    bc = bio_country(fresh_bio, name, username)
                    new_country = bc if bc else mapped
            if not new_country:
                new_country = bio_country(fresh_bio, name, username)

            # === CATEGORY ===
            new_cats = None
            current_cats = cats or '[]'
            if current_cats in ('["entertainment"]', '[]', ''):
                detected = detect_category(fresh_bio, name, nickname)
                if detected:
                    new_cats = json.dumps(detected)

            # === BIO ===
            new_bio = None
            if fresh_bio and fresh_bio != bio and len(fresh_bio) > len(bio or ''):
                new_bio = fresh_bio

            # === APPLY ===
            updates = []
            params = []
            
            if new_country and new_country != country:
                updates.append("country=?")
                params.append(new_country)
                country_fixes += 1
                print(f'  🌍 W{WORKER_ID} @{username} ({followers:,}): {country}→{new_country} [lang={lang}, region={region}]')
                sys.stdout.flush()
            
            if new_cats and new_cats != current_cats:
                updates.append("categories=?")
                params.append(new_cats)
                cat_fixes += 1
                print(f'  🏷️ W{WORKER_ID} @{username} ({followers:,}): {current_cats}→{new_cats}')
                sys.stdout.flush()
            
            if new_bio:
                updates.append("bio=?")
                params.append(new_bio)
                bio_updates += 1

            if updates:
                updates.append("updated_at=datetime('now')")
                params.append(cid)
                conn = sqlite3.connect(DB_PATH)
                conn.execute(f"UPDATE creators SET {', '.join(updates)} WHERE id=?", params)
                conn.commit()
                conn.close()

            if scanned % 25 == 0:
                print(f'  📊 W{WORKER_ID} [{scanned}/{len(creators)}] country:{country_fixes} cat:{cat_fixes} bio:{bio_updates} captcha:{captchas} err:{errors}')
                sys.stdout.flush()

            if scanned % 40 == 0:
                await ctx.close()
                await asyncio.sleep(random.uniform(1, 3))
                ctx = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    viewport={'width': 1920, 'height': 1080})

        await browser.close()

    print(f'\n{"="*60}')
    print(f'WORKER {WORKER_ID} DONE | Scanned: {scanned} | Country: {country_fixes} | Category: {cat_fixes} | Bio: {bio_updates}')
    print(f'Errors: {errors} | Captchas: {captchas}')
    print(f'{"="*60}')
    sys.stdout.flush()

if __name__ == '__main__':
    asyncio.run(main())
