#!/usr/bin/env python3
"""Take screenshot to see what TikTok is actually rendering."""
import asyncio
import os
from playwright.async_api import async_playwright

PROFILE_DIR = os.path.expanduser('~/.tiktok-scraper-profile')

async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            PROFILE_DIR, headless=False,
            args=['--disable-blink-features=AutomationControlled'],
            viewport={'width': 1440, 'height': 900}, locale='en-US',
        )
        await ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
        
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto('https://www.tiktok.com/@charlidamelio', wait_until='domcontentloaded', timeout=20000)
        await asyncio.sleep(5)
        
        # Screenshot initial state
        await page.screenshot(path='scraper/tt_screenshot_1.png', full_page=False)
        print('Screenshot 1 saved')
        
        # Scroll down
        for i in range(5):
            await page.evaluate('window.scrollBy(0, 500)')
            await asyncio.sleep(2)
        
        await page.screenshot(path='scraper/tt_screenshot_2.png', full_page=False)
        print('Screenshot 2 saved')
        
        # Check page content
        html = await page.content()
        print(f'Page HTML length: {len(html)}')
        print(f'Contains "video": {"video" in html.lower()}')
        print(f'Contains "captcha": {"captcha" in html.lower()}')
        print(f'Contains "login": {"login" in html.lower()}')
        
        # Get all visible text
        text = await page.evaluate('() => document.body.innerText.substring(0, 2000)')
        print(f'\nVisible text:\n{text[:1000]}')
        
        await ctx.close()

asyncio.run(main())
