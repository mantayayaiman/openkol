#!/usr/bin/env python3
"""
Seed discovery queue with fresh handles from TikTok discover pages.
"""
import asyncio
import json
import random
from playwright.async_api import async_playwright

DISCOVER_PAGES = [
    "https://www.tiktok.com/discover/malaysian-creator",
    "https://www.tiktok.com/discover/indonesian-creator",
    "https://www.tiktok.com/discover/singapore-influencer", 
    "https://www.tiktok.com/discover/thai-creator",
    "https://www.tiktok.com/discover/filipino-tiktok",
    "https://www.tiktok.com/discover/vietnamese-tiktok"
]

DISCOVERED_HANDLES_FILE = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/discovered_handles.json'

async def extract_handles_from_page(page, url):
    """Extract uniqueId values from a TikTok discover page"""
    print(f"\n🔍 Visiting: {url}")
    
    try:
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(random.uniform(3, 6))
        
        # Try to scroll a bit to load more content
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(2)
        
        # Extract handles from various selectors
        handles = []
        
        # Method 1: Look for uniqueId in hydration data
        hydration_data = await page.evaluate("""
            () => {
                const scripts = Array.from(document.querySelectorAll('script'));
                for (const script of scripts) {
                    if (script.textContent && script.textContent.includes('uniqueId')) {
                        try {
                            const matches = script.textContent.match(/"uniqueId":"([^"]+)"/g);
                            if (matches) return matches;
                        } catch (e) {}
                    }
                }
                return [];
            }
        """)
        
        if hydration_data:
            for match in hydration_data:
                username = match.split('"uniqueId":"')[1].split('"')[0]
                if username and len(username) > 1 and username != 'undefined':
                    handles.append(username)
                    
        # Method 2: Look for @usernames in links
        username_links = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[href*="/@"]'));
                return links.map(link => {
                    const match = link.href.match(/\/@([^\/\?]+)/);
                    return match ? match[1] : null;
                }).filter(Boolean);
            }
        """)
        
        handles.extend(username_links)
        
        # Remove duplicates
        handles = list(set(handles))
        print(f"  → Found {len(handles)} unique handles")
        
        return handles
        
    except Exception as e:
        print(f"  ❌ Error extracting from {url}: {e}")
        return []

async def main():
    print("🌱 Seeding discovery queue from TikTok discover pages...")
    
    # Load existing discovered handles
    try:
        with open(DISCOVERED_HANDLES_FILE, 'r') as f:
            existing = json.load(f)
    except:
        existing = {}
    
    print(f"📊 Currently have {len(existing)} discovered handles")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        
        page = await context.new_page()
        
        all_new_handles = []
        
        for url in DISCOVER_PAGES:
            handles = await extract_handles_from_page(page, url)
            all_new_handles.extend(handles)
            
            # Random delay between pages
            await asyncio.sleep(random.uniform(4, 8))
        
        await browser.close()
    
    # Filter new handles (not already in existing)
    new_handles = [h for h in all_new_handles if h not in existing]
    new_handles = list(set(new_handles))  # Remove duplicates
    
    print(f"\n📈 Found {len(new_handles)} NEW handles to add:")
    
    # Add new handles to discovered_handles.json with placeholder data
    for handle in new_handles[:50]:  # Limit to 50 new ones
        existing[handle] = {
            "name": "TBD",
            "followers": 0,
            "source": "discover-page-seed"
        }
        print(f"  + {handle}")
    
    # Save updated file
    with open(DISCOVERED_HANDLES_FILE, 'w') as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Discovery queue updated! Total handles: {len(existing)}")
    print(f"   New handles added: {len(new_handles[:50])}")

if __name__ == "__main__":
    asyncio.run(main())