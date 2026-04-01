#!/usr/bin/env python3
"""
FastMoss Creator Scraper — Playwright browser scraping.

Extracts creator/KOL data from FastMoss's influencer search pages.
Logs in with credentials, iterates through SEA countries, paginates through results.

Usage:
  PLAYWRIGHT_BROWSERS_PATH=0 \
  FASTMOSS_EMAIL=xxx FASTMOSS_PASSWORD=xxx \
  python3 -u scraper/fastmoss_scraper.py

Env vars:
  FASTMOSS_EMAIL     — FastMoss login email
  FASTMOSS_PASSWORD  — FastMoss login password
"""
import asyncio
import json
import os
import sqlite3
import sys
import random
from datetime import datetime, timezone
from playwright.async_api import async_playwright

# ============================================================
# CONFIG
# ============================================================
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'kreator.db')
BACKUP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fastmoss_backup.jsonl')
PROGRESS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fastmoss_progress.json')

BASE_URL = 'https://www.fastmoss.com'
COUNTRIES = ['MY', 'ID', 'TH', 'PH', 'VN', 'SG']
SCRAPE_DELAY = (2.0, 4.0)  # random delay range
MAX_PAGES_PER_COUNTRY = 200  # safety cap
CTX_ROTATE = 40  # rotate context every N pages

USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
]

# ============================================================
# HELPERS
# ============================================================
def ts():
    return datetime.now().strftime('%H:%M:%S')

def parse_number(text):
    """Parse '1.2M', '500K', '12,345' etc into int."""
    if not text:
        return 0
    text = text.strip().replace(',', '').replace(' ', '')
    multipliers = {'K': 1_000, 'M': 1_000_000, 'B': 1_000_000_000, 'k': 1_000, 'm': 1_000_000}
    for suffix, mult in multipliers.items():
        if text.endswith(suffix):
            try:
                return int(float(text[:-1]) * mult)
            except:
                return 0
    try:
        return int(float(text))
    except:
        return 0

def load_progress():
    if os.path.exists(PROGRESS_PATH):
        with open(PROGRESS_PATH) as f:
            return json.load(f)
    return {'completed_countries': [], 'current_country': None, 'current_page': 0, 'total_scraped': 0}

def save_progress(prog):
    with open(PROGRESS_PATH, 'w') as f:
        json.dump(prog, f, indent=2)

def backup_record(record):
    with open(BACKUP_PATH, 'a') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')

def upsert_creator(db, record):
    """Insert or update creator in our DB."""
    platform = 'tiktok'  # FastMoss is TikTok-focused
    username = record.get('username', '').strip().lstrip('@')
    if not username:
        return False
    
    # Check if presence exists
    row = db.execute(
        "SELECT pp.id, pp.creator_id FROM platform_presences pp WHERE pp.platform = ? AND pp.username = ?",
        (platform, username)
    ).fetchone()
    
    country = record.get('country', 'SEA')
    name = record.get('name', username)
    categories = json.dumps(record.get('categories', ['entertainment']))
    followers = record.get('followers', 0)
    engagement_rate = record.get('engagement_rate', 0)
    bio = record.get('bio', '')
    profile_image = record.get('avatar', '')
    avg_views = record.get('avg_views', 0)
    total_likes = record.get('total_likes', 0)
    total_videos = record.get('total_videos', 0)
    
    now = datetime.now(timezone.utc).isoformat()
    
    if row:
        # Update existing
        pp_id, creator_id = row
        db.execute("""
            UPDATE platform_presences SET
                followers = MAX(followers, ?), engagement_rate = COALESCE(NULLIF(?, 0), engagement_rate),
                avg_views = COALESCE(NULLIF(?, 0), avg_views), total_likes = COALESCE(NULLIF(?, 0), total_likes),
                total_videos = COALESCE(NULLIF(?, 0), total_videos), last_scraped_at = ?
            WHERE id = ?
        """, (followers, engagement_rate, avg_views, total_likes, total_videos, now, pp_id))
        # Update creator if we have better data
        if bio:
            db.execute("UPDATE creators SET bio = ? WHERE id = ? AND (bio = '' OR bio IS NULL)", (bio, creator_id))
        if profile_image:
            db.execute("UPDATE creators SET profile_image = ? WHERE id = ? AND (profile_image = '' OR profile_image IS NULL)", (profile_image, creator_id))
        return False  # not new
    else:
        # Insert new creator
        cur = db.execute("""
            INSERT INTO creators (name, bio, profile_image, country, primary_platform, categories, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, bio, profile_image, country, platform, categories, now, now))
        creator_id = cur.lastrowid
        db.execute("""
            INSERT INTO platform_presences (creator_id, platform, username, url, followers, engagement_rate, avg_views, total_likes, total_videos, last_scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (creator_id, platform, username, f'https://www.tiktok.com/@{username}', followers, engagement_rate, avg_views, total_likes, total_videos, now))
        return True  # new

# ============================================================
# SCRAPER
# ============================================================
class FastMossScraper:
    def __init__(self):
        self.email = os.environ.get('FASTMOSS_EMAIL')
        self.password = os.environ.get('FASTMOSS_PASSWORD')
        if not self.email or not self.password:
            print("❌ Set FASTMOSS_EMAIL and FASTMOSS_PASSWORD environment variables")
            sys.exit(1)
        self.progress = load_progress()
        self.db = sqlite3.connect(DB_PATH)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.new_count = 0
        self.update_count = 0
        self.page_count = 0
        self.cookies = None
    
    async def login(self, page):
        """Login to FastMoss."""
        print(f"[{ts()}] Logging in as {self.email}...")
        await page.goto(f'{BASE_URL}/login', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(2)
        
        # Try to find login form
        # FastMoss uses various login methods - email/password or Google
        # Look for email input
        email_sel = 'input[type="email"], input[name="email"], input[placeholder*="email" i], input[placeholder*="Email"]'
        pwd_sel = 'input[type="password"], input[name="password"]'
        
        try:
            await page.wait_for_selector(email_sel, timeout=10000)
            await page.fill(email_sel, self.email)
            await asyncio.sleep(0.5)
            await page.fill(pwd_sel, self.password)
            await asyncio.sleep(0.5)
            
            # Click login button
            btn_sel = 'button[type="submit"], button:has-text("Log in"), button:has-text("Sign in"), button:has-text("Login")'
            await page.click(btn_sel)
            await asyncio.sleep(3)
            await page.wait_for_load_state('networkidle', timeout=15000)
            print(f"[{ts()}] ✅ Logged in successfully")
        except Exception as e:
            print(f"[{ts()}] ⚠️ Login form issue: {e}")
            print(f"[{ts()}] Current URL: {page.url}")
            # Maybe already logged in or different login flow
            # Save screenshot for debugging
            await page.screenshot(path=os.path.join(os.path.dirname(PROGRESS_PATH), 'fastmoss_login_debug.png'))
            
    async def save_cookies(self, context):
        """Save cookies for session reuse."""
        self.cookies = await context.cookies()
        
    async def intercept_api(self, page, country):
        """Intercept XHR responses to capture API data directly."""
        creators = []
        
        async def handle_response(response):
            url = response.url
            if '/influencer/' in url and response.status == 200:
                try:
                    data = await response.json()
                    if isinstance(data, dict) and 'data' in data:
                        items = data['data']
                        if isinstance(items, dict) and 'list' in items:
                            items = items['list']
                        if isinstance(items, list):
                            for item in items:
                                creator = self.parse_api_item(item, country)
                                if creator:
                                    creators.append(creator)
                except:
                    pass
        
        page.on('response', handle_response)
        return creators
    
    def parse_api_item(self, item, country):
        """Parse a creator from FastMoss API response."""
        try:
            username = item.get('nickname', '') or item.get('unique_id', '') or item.get('uniqueId', '')
            unique_id = item.get('unique_id', '') or item.get('uniqueId', '') or username
            if not unique_id:
                return None
            return {
                'username': unique_id.lstrip('@'),
                'name': item.get('nickname', '') or item.get('nick_name', '') or unique_id,
                'avatar': item.get('avatar', '') or item.get('avatar_url', ''),
                'followers': parse_number(str(item.get('follower_count', 0) or item.get('follower_count_show', '0'))),
                'engagement_rate': float(item.get('engagement_rate', 0) or 0),
                'avg_views': parse_number(str(item.get('avg_video_views', 0) or item.get('avg_views', 0) or 0)),
                'total_likes': parse_number(str(item.get('like_count', 0) or item.get('heart_count', 0) or 0)),
                'total_videos': parse_number(str(item.get('video_count', 0) or 0)),
                'country': country,
                'categories': [item.get('category', 'entertainment')] if item.get('category') else ['entertainment'],
                'bio': item.get('signature', '') or item.get('bio', ''),
                'source': 'fastmoss',
            }
        except:
            return None
    
    async def scrape_page_dom(self, page, country):
        """Fallback: scrape creator data from DOM."""
        creators = []
        try:
            # Wait for creator cards/rows to appear
            await page.wait_for_selector('[class*="creator"], [class*="influencer"], tr[class*="row"], [class*="table"] tr', timeout=10000)
            
            # Try to extract from table rows or cards
            rows = await page.query_selector_all('tr[data-key], [class*="creator-item"], [class*="influencer-card"]')
            if not rows:
                rows = await page.query_selector_all('tbody tr')
            
            for row in rows:
                try:
                    text = await row.inner_text()
                    lines = [l.strip() for l in text.split('\n') if l.strip()]
                    if len(lines) < 2:
                        continue
                    
                    # Try to find username (starts with @)
                    username = ''
                    name = ''
                    for line in lines:
                        if line.startswith('@'):
                            username = line.lstrip('@')
                        elif not name and not line.replace(',', '').replace('.', '').replace('K', '').replace('M', '').isdigit():
                            name = line
                    
                    # Also try links
                    if not username:
                        links = await row.query_selector_all('a[href*="tiktok.com/@"], a[href*="/influencer/detail/"]')
                        for link in links:
                            href = await link.get_attribute('href') or ''
                            if '@' in href:
                                username = href.split('@')[-1].split('?')[0].split('/')[0]
                            elif '/detail/' in href:
                                inner = await link.inner_text()
                                if inner.startswith('@'):
                                    username = inner.lstrip('@')
                    
                    if not username:
                        continue
                    
                    # Parse numbers from text
                    numbers = []
                    for line in lines:
                        n = parse_number(line)
                        if n > 0:
                            numbers.append(n)
                    
                    # Try to get avatar
                    img = await row.query_selector('img')
                    avatar = ''
                    if img:
                        avatar = await img.get_attribute('src') or ''
                    
                    creator = {
                        'username': username,
                        'name': name or username,
                        'avatar': avatar,
                        'followers': numbers[0] if numbers else 0,
                        'engagement_rate': 0,
                        'avg_views': numbers[1] if len(numbers) > 1 else 0,
                        'total_likes': numbers[2] if len(numbers) > 2 else 0,
                        'total_videos': 0,
                        'country': country,
                        'categories': ['entertainment'],
                        'bio': '',
                        'source': 'fastmoss',
                    }
                    
                    # Try to parse engagement rate (looks like "X.XX%")
                    for line in lines:
                        if '%' in line:
                            try:
                                er = float(line.replace('%', '').strip())
                                creator['engagement_rate'] = er
                                break
                            except:
                                pass
                    
                    creators.append(creator)
                except:
                    continue
        except Exception as e:
            print(f"[{ts()}] ⚠️ DOM scrape error: {e}")
        
        return creators
    
    async def scrape_country(self, browser, country):
        """Scrape all creators for a given country."""
        print(f"\n[{ts()}] 🌍 Starting country: {country}")
        
        ua = random.choice(USER_AGENTS)
        context = await browser.new_context(
            user_agent=ua,
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
        )
        
        if self.cookies:
            await context.add_cookies(self.cookies)
        
        page = await context.new_page()
        country_total = 0
        page_num = self.progress.get('current_page', 0) if self.progress.get('current_country') == country else 0
        consecutive_empty = 0
        
        while page_num < MAX_PAGES_PER_COUNTRY:
            page_num += 1
            
            # Rotate context periodically
            if page_num > 1 and page_num % CTX_ROTATE == 0:
                print(f"[{ts()}] 🔄 Rotating context at page {page_num}")
                await self.save_cookies(context)
                await context.close()
                ua = random.choice(USER_AGENTS)
                context = await browser.new_context(user_agent=ua, viewport={'width': 1920, 'height': 1080})
                if self.cookies:
                    await context.add_cookies(self.cookies)
                page = await context.new_page()
            
            try:
                # Navigate to search page with country filter
                url = f'{BASE_URL}/influencer/search?country={country}&page={page_num}'
                print(f"[{ts()}] 📄 Page {page_num} — {url}")
                
                # Set up API interception
                api_creators = await self.intercept_api(page, country)
                
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(random.uniform(*SCRAPE_DELAY))
                
                # Check if we need to login
                if '/login' in page.url:
                    await self.login(page)
                    await page.goto(url, wait_until='networkidle', timeout=30000)
                    await asyncio.sleep(2)
                
                # First check intercepted API data
                creators = api_creators
                
                # If no API data, try DOM scraping
                if not creators:
                    creators = await self.scrape_page_dom(page, country)
                
                if not creators:
                    consecutive_empty += 1
                    print(f"[{ts()}] ⚠️ Empty page (consecutive: {consecutive_empty})")
                    if consecutive_empty >= 3:
                        print(f"[{ts()}] 🛑 3 consecutive empty pages, moving to next country")
                        break
                    continue
                
                consecutive_empty = 0
                
                # Save to DB
                new_on_page = 0
                for creator in creators:
                    backup_record(creator)
                    is_new = upsert_creator(self.db, creator)
                    if is_new:
                        self.new_count += 1
                        new_on_page += 1
                    else:
                        self.update_count += 1
                
                self.db.commit()
                country_total += len(creators)
                self.page_count += 1
                
                print(f"[{ts()}] ✅ {len(creators)} creators ({new_on_page} new) | Country total: {country_total} | DB new: {self.new_count}")
                
                # Save progress
                self.progress['current_country'] = country
                self.progress['current_page'] = page_num
                self.progress['total_scraped'] = self.progress.get('total_scraped', 0) + len(creators)
                save_progress(self.progress)
                
                # Random delay
                await asyncio.sleep(random.uniform(*SCRAPE_DELAY))
                
            except Exception as e:
                print(f"[{ts()}] ❌ Error on page {page_num}: {e}")
                await asyncio.sleep(5)
                consecutive_empty += 1
                if consecutive_empty >= 5:
                    break
        
        await context.close()
        print(f"[{ts()}] ✅ Country {country} done: {country_total} creators scraped")
        self.progress['completed_countries'].append(country)
        save_progress(self.progress)
    
    async def run(self):
        print(f"[{ts()}] 🚀 FastMoss Scraper starting")
        print(f"[{ts()}] Countries: {COUNTRIES}")
        print(f"[{ts()}] DB: {DB_PATH}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            # Login first
            context = await browser.new_context(user_agent=random.choice(USER_AGENTS))
            page = await context.new_page()
            await self.login(page)
            await self.save_cookies(context)
            await context.close()
            
            # Scrape each country
            for country in COUNTRIES:
                if country in self.progress.get('completed_countries', []):
                    print(f"[{ts()}] ⏭️ Skipping {country} (already completed)")
                    continue
                await self.scrape_country(browser, country)
            
            await browser.close()
        
        self.db.close()
        print(f"\n[{ts()}] 🏁 DONE!")
        print(f"[{ts()}] New creators: {self.new_count}")
        print(f"[{ts()}] Updated creators: {self.update_count}")
        print(f"[{ts()}] Pages scraped: {self.page_count}")

if __name__ == '__main__':
    asyncio.run(FastMossScraper().run())
