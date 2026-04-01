#!/usr/bin/env python3
"""
Kalodata Creator Scraper — Headed Playwright with API interception.

Logs in via headed browser (to pass Cloudflare), then intercepts API responses
to capture structured creator data. Iterates through all SEA regions.

Usage:
  PLAYWRIGHT_BROWSERS_PATH=0 \
  KALODATA_EMAIL=0124807277 KALODATA_PASSWORD='Rf00ng@123' \
  python3 -u scraper/kalodata_scraper.py

Optional: --region MY (scrape single region)
"""
import asyncio
import json
import os
import re
import sqlite3
import sys
import random
from datetime import datetime, timezone
from playwright.async_api import async_playwright

# ============================================================
# CONFIG
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, '..', 'kreator.db')
BACKUP_PATH = os.path.join(SCRIPT_DIR, 'kalodata_backup.jsonl')
PROGRESS_PATH = os.path.join(SCRIPT_DIR, 'kalodata_progress.json')
COOKIES_PATH = os.path.join(SCRIPT_DIR, 'kalodata_cookies.json')
BROWSER_DIR = os.environ.get('KALODATA_BROWSER_DIR', '/tmp/kalodata_scraper_browser')

BASE_URL = 'https://www.kalodata.com'
REGIONS = ['MY', 'ID', 'TH', 'VN', 'PH']  # Kalodata-supported SEA regions
SCRAPE_DELAY = (3.0, 6.0)
MAX_PAGES = 500  # safety cap per region
SCROLL_PAUSE = 2.0

USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
]

# ============================================================
# HELPERS
# ============================================================
def ts():
    return datetime.now().strftime('%H:%M:%S')

def parse_number(text):
    """Parse '1.2M', '500K', 'RM5.89m', '12,345' etc into int."""
    if not text:
        return 0
    text = str(text).strip().replace(',', '').replace(' ', '')
    # Remove currency prefixes
    for prefix in ['RM', 'Rp', '$', '¥', '₫', '฿', '₱', 'USD']:
        text = text.replace(prefix, '')
    text = text.strip()
    multipliers = {'K': 1_000, 'M': 1_000_000, 'B': 1_000_000_000, 'k': 1_000, 'm': 1_000_000, 'b': 1_000_000_000}
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
    return {'completed_regions': [], 'current_region': None, 'current_page': 0, 'total_scraped': 0, 'total_new': 0}

def save_progress(prog):
    with open(PROGRESS_PATH, 'w') as f:
        json.dump(prog, f, indent=2)

def backup_record(record):
    with open(BACKUP_PATH, 'a') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')

def upsert_creator(db, record):
    """Insert or update creator in our DB."""
    platform = 'tiktok'
    username = record.get('username', '').strip().lstrip('@')
    if not username or len(username) < 2:
        return False
    
    row = db.execute(
        "SELECT pp.id, pp.creator_id FROM platform_presences pp WHERE pp.platform = ? AND pp.username = ?",
        (platform, username)
    ).fetchone()
    
    country = record.get('country', 'SEA')
    name = record.get('name', username)
    categories = json.dumps(record.get('categories', ['entertainment']))
    followers = record.get('followers', 0)
    engagement_rate = record.get('engagement_rate', 0)
    avg_views = record.get('avg_views', 0)
    total_likes = record.get('total_likes', 0)
    total_videos = record.get('total_videos', 0)
    bio = record.get('bio', '')
    profile_image = record.get('avatar', '')
    
    now = datetime.now(timezone.utc).isoformat()
    
    if row:
        pp_id, creator_id = row
        db.execute("""
            UPDATE platform_presences SET
                followers = MAX(followers, ?), engagement_rate = COALESCE(NULLIF(?, 0), engagement_rate),
                avg_views = COALESCE(NULLIF(?, 0), avg_views), total_likes = COALESCE(NULLIF(?, 0), total_likes),
                total_videos = COALESCE(NULLIF(?, 0), total_videos), last_scraped_at = ?
            WHERE id = ?
        """, (followers, engagement_rate, avg_views, total_likes, total_videos, now, pp_id))
        if bio:
            db.execute("UPDATE creators SET bio = ? WHERE id = ? AND (bio = '' OR bio IS NULL)", (bio, creator_id))
        if profile_image:
            db.execute("UPDATE creators SET profile_image = ? WHERE id = ? AND (profile_image = '' OR profile_image IS NULL)", (profile_image, creator_id))
        return False
    else:
        cur = db.execute("""
            INSERT INTO creators (name, bio, profile_image, country, primary_platform, categories, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, bio, profile_image, country, platform, categories, now, now))
        creator_id = cur.lastrowid
        db.execute("""
            INSERT INTO platform_presences (creator_id, platform, username, url, followers, engagement_rate, avg_views, total_likes, total_videos, last_scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (creator_id, platform, username, f'https://www.tiktok.com/@{username}', followers, engagement_rate, avg_views, total_likes, total_videos, now))
        return True

# ============================================================
# SCRAPER
# ============================================================
class KalodataScraper:
    def __init__(self):
        self.phone = os.environ.get('KALODATA_EMAIL', '')
        self.password = os.environ.get('KALODATA_PASSWORD', '')
        if not self.phone or not self.password:
            print("❌ Set KALODATA_EMAIL and KALODATA_PASSWORD environment variables")
            sys.exit(1)
        
        # Parse region arg
        self.single_region = None
        if '--region' in sys.argv:
            idx = sys.argv.index('--region')
            if idx + 1 < len(sys.argv):
                self.single_region = sys.argv[idx + 1].upper()
        
        self.progress = load_progress()
        self.db = sqlite3.connect(DB_PATH)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.new_count = 0
        self.update_count = 0
        self.page_count = 0
        self.intercepted_creators = []
    
    async def login(self, page):
        """Login to Kalodata."""
        print(f"[{ts()}] Logging in...")
        await page.goto(f'{BASE_URL}/', wait_until='load', timeout=60000)
        await asyncio.sleep(3)
        
        await page.goto(f'{BASE_URL}/login', wait_until='load', timeout=60000)
        await asyncio.sleep(8)
        
        # Find and fill login form
        phone_input = await page.query_selector('input[placeholder="Phone Number"]')
        pwd_input = await page.query_selector('input[type="password"]')
        
        if not phone_input or not pwd_input:
            print(f"[{ts()}] ❌ Login form not found!")
            await page.screenshot(path=os.path.join(SCRIPT_DIR, 'kalodata_login_debug.png'))
            return False
        
        # Strip phone number formatting
        phone = self.phone
        if phone.startswith('+60'):
            phone = phone[3:]
        elif phone.startswith('60'):
            phone = phone[2:]
        if phone.startswith('0'):
            phone = phone[1:]
        
        await phone_input.fill(phone)
        await asyncio.sleep(0.5)
        await pwd_input.fill(self.password)
        await asyncio.sleep(0.5)
        
        # Checkbox
        cb = await page.query_selector('input[type="checkbox"]')
        if cb and not await cb.is_checked():
            await cb.click()
            await asyncio.sleep(0.3)
        
        # Click login
        await page.click('button:has-text("Log in")')
        await asyncio.sleep(8)
        
        if '/login' not in page.url:
            print(f"[{ts()}] ✅ Logged in → {page.url}")
            return True
        else:
            print(f"[{ts()}] ❌ Still on login page")
            await page.screenshot(path=os.path.join(SCRIPT_DIR, 'kalodata_login_debug.png'))
            return False
    
    def setup_api_interceptor(self, page):
        """Intercept API responses to get structured JSON data."""
        self.intercepted_creators = []
        
        async def on_response(response):
            url = response.url
            # Catch internal API calls for creator data
            if response.status == 200 and ('creator' in url.lower() or 'crator' in url.lower() or 'rank' in url.lower()):
                try:
                    ct = response.headers.get('content-type', '')
                    if 'json' in ct:
                        data = await response.json()
                        self._extract_from_api(data)
                except:
                    pass
        
        page.on('response', on_response)
    
    def _extract_from_api(self, data):
        """Extract creator records from API JSON."""
        if not isinstance(data, dict):
            return
        
        # Navigate common response structures
        items = None
        if 'data' in data:
            d = data['data']
            if isinstance(d, list):
                items = d
            elif isinstance(d, dict):
                for key in ['list', 'items', 'creators', 'records', 'rows', 'data']:
                    if key in d and isinstance(d[key], list):
                        items = d[key]
                        break
        
        if not items:
            return
        
        for item in items:
            if not isinstance(item, dict):
                continue
            username = (item.get('unique_id') or item.get('uniqueId') or 
                       item.get('tiktok_unique_id') or item.get('handle') or 
                       item.get('username') or '')
            if not username or len(username) < 2:
                continue
            
            creator = {
                'username': username.lstrip('@'),
                'name': item.get('nickname') or item.get('nick_name') or item.get('name') or username,
                'avatar': item.get('avatar') or item.get('avatar_url') or '',
                'followers': parse_number(item.get('follower_count', 0) or item.get('followers', 0)),
                'engagement_rate': float(item.get('engagement_rate', 0) or 0),
                'avg_views': parse_number(item.get('avg_video_views', 0) or item.get('avg_views', 0)),
                'total_likes': parse_number(item.get('like_count', 0) or item.get('digg_count', 0)),
                'total_videos': parse_number(item.get('video_count', 0)),
                'categories': [],
                'bio': item.get('signature', '') or item.get('bio', '') or '',
                'source': 'kalodata',
            }
            
            cat = item.get('category') or item.get('category_name') or ''
            if cat:
                creator['categories'] = [cat.lower()]
            
            self.intercepted_creators.append(creator)
    
    async def scrape_page_dom(self, page, region):
        """Extract creator data from DOM table."""
        creators = []
        try:
            rows = await page.query_selector_all('tbody tr')
            if not rows:
                return creators
            
            for row in rows:
                try:
                    # Get all cell text
                    cells = await row.query_selector_all('td')
                    if len(cells) < 3:
                        continue
                    
                    # First meaningful cell usually has creator info
                    # Look for @username pattern in the row
                    row_text = await row.inner_text()
                    
                    # Find @username
                    username_match = re.search(r'@(\w[\w.]+)', row_text)
                    if not username_match:
                        continue
                    username = username_match.group(1)
                    
                    # Get name (line before @username)
                    lines = [l.strip() for l in row_text.split('\n') if l.strip()]
                    name = username
                    for i, line in enumerate(lines):
                        if f'@{username}' in line and i > 0:
                            # Previous non-number line is likely the name
                            for j in range(i-1, -1, -1):
                                candidate = lines[j].strip()
                                if candidate and not candidate.isdigit() and not candidate.startswith(('RM', '$', 'Rp')):
                                    name = candidate
                                    break
                            break
                    
                    # Parse numbers from cells
                    followers = 0
                    
                    for cell in cells:
                        cell_text = (await cell.inner_text()).strip()
                        # Revenue (contains RM, $, etc)
                        if any(c in cell_text for c in ['RM', '$', 'Rp', '₫', '฿', '₱']):
                            parse_number(cell_text)
                        # Large numbers could be followers
                        elif parse_number(cell_text) > 1000 and followers == 0:
                            followers = parse_number(cell_text)
                    
                    # Try to get avatar
                    img = await row.query_selector('img')
                    avatar = ''
                    if img:
                        avatar = await img.get_attribute('src') or ''
                    
                    # Get engagement rate
                    engagement_rate = 0
                    er_match = re.search(r'(\d+\.?\d*)%', row_text)
                    if er_match:
                        engagement_rate = float(er_match.group(1))
                    
                    creator = {
                        'username': username,
                        'name': name,
                        'avatar': avatar,
                        'followers': followers,
                        'engagement_rate': engagement_rate,
                        'avg_views': 0,
                        'total_likes': 0,
                        'total_videos': 0,
                        'country': region,
                        'categories': ['entertainment'],
                        'bio': '',
                        'source': 'kalodata_dom',
                    }
                    creators.append(creator)
                except Exception:
                    continue
        except Exception as e:
            print(f"[{ts()}] ⚠️ DOM scrape error: {e}")
        
        return creators
    
    async def change_region(self, page, region):
        """Change the region/country filter on the creator page."""
        region_names = {
            'MY': 'Malaysia', 'ID': 'Indonesia', 'TH': 'Thailand',
            'VN': 'Vietnam', 'PH': 'Philippines',
        }
        region_name = region_names.get(region, region)
        
        # Look for region selector/dropdown
        # Try clicking the region button/dropdown
        try:
            # Kalodata has a region selector in the header or filter area
            region_btn = await page.query_selector(f'[class*="region"], button:has-text("{region_name}"), span:has-text("{region_name}")')
            if region_btn:
                await region_btn.click()
                await asyncio.sleep(2)
            
            # Or try the URL approach
            await page.goto(f'{BASE_URL}/creator?region={region.lower()}', wait_until='load', timeout=60000)
            await asyncio.sleep(5)
            return True
        except:
            return False
    
    async def next_page(self, page):
        """Click next page button (ant-design pagination)."""
        try:
            # Ant Design pagination: .ant-pagination-next
            next_btn = await page.query_selector('.ant-pagination-next')
            if next_btn:
                # Check if disabled
                cls = await next_btn.get_attribute('class') or ''
                aria = await next_btn.get_attribute('aria-disabled') or ''
                if 'disabled' in cls or aria == 'true':
                    return False
                await next_btn.click()
                await asyncio.sleep(4)
                return True
            
            # Fallback: click next numbered page
            active = await page.query_selector('.ant-pagination-item-active')
            if active:
                title = await active.get_attribute('title') or ''
                if title.isdigit():
                    current = int(title)
                    next_item = await page.query_selector(f'.ant-pagination-item[title="{current + 1}"]')
                    if next_item:
                        await next_item.click()
                        await asyncio.sleep(3)
                        return True
            
            return False
        except Exception as e:
            print(f"[{ts()}] ⚠️ Pagination error: {e}")
            return False
    
    async def dismiss_modals(self, page):
        """Close any popup modals (upgrade prompts, feature announcements)."""
        try:
            # Close ant-design modals
            close_btns = await page.query_selector_all('.ant-modal-close, .ant-modal-wrap button.ant-modal-close, [class*="Modal"] .ant-btn, [aria-label="Close"]')
            for btn in close_btns:
                if await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(0.5)
            
            # Also try clicking outside modal to dismiss
            modal_mask = await page.query_selector('.ant-modal-mask')
            if modal_mask and await modal_mask.is_visible():
                await page.keyboard.press('Escape')
                await asyncio.sleep(0.5)
            
            # Dismiss any overlay
            overlay = await page.query_selector('.ant-modal-wrap')
            if overlay and await overlay.is_visible():
                await page.keyboard.press('Escape')
                await asyncio.sleep(0.5)
        except:
            pass
    
    async def scroll_to_load(self, page):
        """Scroll down to trigger lazy loading."""
        for _ in range(3):
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(SCROLL_PAUSE)
    
    async def scrape_region(self, context, region):
        """Scrape all creators for a region."""
        print(f"\n[{ts()}] 🌍 Starting region: {region}")
        
        page = await context.new_page()
        region_total = 0
        page_num = self.progress.get('current_page', 0) if self.progress.get('current_region') == region else 0
        consecutive_empty = 0
        
        # Navigate to creator page with region
        url = f'{BASE_URL}/creator?country={region.lower()}'
        print(f"[{ts()}] Navigating to {url}")
        
        self.setup_api_interceptor(page)
        await page.goto(url, wait_until='load', timeout=60000)
        await asyncio.sleep(8)
        
        # Dismiss any popups
        await self.dismiss_modals(page)
        
        # Check if we're on the right page
        body = await page.inner_text('body')
        if 'Creator' not in body and 'creator' not in body.lower():
            print(f"[{ts()}] ⚠️ Not on creator page, trying alternative URL...")
            await page.goto(f'{BASE_URL}/creator', wait_until='load', timeout=60000)
            await asyncio.sleep(5)
        
        # Skip to resume page if needed
        if page_num > 0:
            print(f"[{ts()}] Resuming from page {page_num}")
            for _ in range(page_num):
                success = await self.next_page(page)
                if not success:
                    break
                await asyncio.sleep(1)
        
        while page_num < MAX_PAGES:
            page_num += 1
            
            try:
                # Reset intercepted data
                self.intercepted_creators = []
                
                # Scroll to trigger loading
                await self.scroll_to_load(page)
                await asyncio.sleep(random.uniform(*SCRAPE_DELAY))
                
                # Collect creators from API interception + DOM
                creators = self.intercepted_creators.copy()
                
                if not creators:
                    # Fallback to DOM scraping
                    creators = await self.scrape_page_dom(page, region)
                
                # Set country on all creators
                for c in creators:
                    c['country'] = region
                
                if not creators:
                    consecutive_empty += 1
                    print(f"[{ts()}] ⚠️ Page {page_num}: empty (consecutive: {consecutive_empty})")
                    if consecutive_empty >= 3:
                        print(f"[{ts()}] 🛑 3 consecutive empty pages, done with {region}")
                        break
                else:
                    consecutive_empty = 0
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
                    region_total += len(creators)
                    self.page_count += 1
                    
                    print(f"[{ts()}] ✅ Page {page_num}: {len(creators)} creators ({new_on_page} new) | Region: {region_total} | Total new: {self.new_count}")
                
                # Save progress
                self.progress['current_region'] = region
                self.progress['current_page'] = page_num
                self.progress['total_scraped'] = self.progress.get('total_scraped', 0) + len(creators)
                self.progress['total_new'] = self.new_count
                save_progress(self.progress)
                
                # Dismiss any modals before pagination
                await self.dismiss_modals(page)
                
                # Go to next page
                success = await self.next_page(page)
                if not success:
                    print(f"[{ts()}] 📄 No more pages for {region}")
                    break
                
                await asyncio.sleep(random.uniform(*SCRAPE_DELAY))
                
            except Exception as e:
                print(f"[{ts()}] ❌ Error page {page_num}: {e}")
                await asyncio.sleep(5)
                consecutive_empty += 1
                if consecutive_empty >= 5:
                    break
        
        await page.close()
        print(f"[{ts()}] ✅ Region {region} done: {region_total} creators scraped")
        if region not in self.progress['completed_regions']:
            self.progress['completed_regions'].append(region)
        self.progress['current_page'] = 0
        save_progress(self.progress)
    
    async def run(self):
        print(f"[{ts()}] 🚀 Kalodata Scraper starting")
        regions = [self.single_region] if self.single_region else REGIONS
        print(f"[{ts()}] Regions: {regions}")
        print(f"[{ts()}] DB: {DB_PATH}")
        
        async with async_playwright() as p:
            # Use headed mode with persistent context to pass Cloudflare
            context = await p.chromium.launch_persistent_context(
                user_data_dir=BROWSER_DIR,
                headless=False,
                args=['--disable-blink-features=AutomationControlled'],
                user_agent=USER_AGENTS[0],
                viewport={'width': 1440, 'height': 900},
            )
            
            # Login
            page = context.pages[0] if context.pages else await context.new_page()
            logged_in = await self.login(page)
            if not logged_in:
                print(f"[{ts()}] ❌ Login failed, aborting")
                await context.close()
                return
            await page.close()
            
            # Scrape each region
            for region in regions:
                if region in self.progress.get('completed_regions', []):
                    print(f"[{ts()}] ⏭️ Skipping {region} (already done)")
                    continue
                await self.scrape_region(context, region)
            
            await context.close()
        
        self.db.close()
        print(f"\n[{ts()}] 🏁 DONE!")
        print(f"[{ts()}] New: {self.new_count} | Updated: {self.update_count} | Pages: {self.page_count}")

if __name__ == '__main__':
    asyncio.run(KalodataScraper().run())
