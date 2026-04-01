#!/usr/bin/env python3
"""Backfill TikTok UIDs for existing creators. Scans from highest followers down."""
import asyncio
import json
import sqlite3
import random
import sys
from playwright.async_api import async_playwright

DB = "/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db"

async def main():
    conn = sqlite3.connect(DB)
    # Get TikTok creators without UIDs, ordered by followers
    creators = conn.execute("""
        SELECT pp.id, pp.username, pp.followers 
        FROM platform_presences pp
        WHERE pp.platform='tiktok' AND (pp.platform_uid IS NULL OR pp.platform_uid='')
        ORDER BY pp.followers DESC
    """).fetchall()
    conn.close()
    
    print(f"Backfilling UIDs for {len(creators)} TikTok creators")
    sys.stdout.flush()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            viewport={'width':1920,'height':1080})
        
        filled = 0
        for i, (pp_id, username, followers) in enumerate(creators):
            page = await ctx.new_page()
            try:
                await page.goto(f'https://www.tiktok.com/@{username}', wait_until='domcontentloaded', timeout=12000)
                await asyncio.sleep(1)
                data = await page.evaluate('()=>{const e=document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");return e?e.textContent:null}')
                if data:
                    parsed = json.loads(data)
                    u = parsed.get('__DEFAULT_SCOPE__',{}).get('webapp.user-detail',{}).get('userInfo',{}).get('user',{})
                    uid = u.get('id','')
                    if uid:
                        conn = sqlite3.connect(DB)
                        conn.execute("UPDATE platform_presences SET platform_uid=? WHERE id=?", (uid, pp_id))
                        conn.commit()
                        conn.close()
                        filled += 1
                        if filled <= 20 or filled % 50 == 0:
                            print(f"  ✅ @{username} ({followers:,}): UID={uid}")
                            sys.stdout.flush()
            except: pass
            await page.close()
            
            if (i+1) % 50 == 0:
                await ctx.close()
                ctx = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    viewport={'width':1920,'height':1080})
                print(f"  Progress: {i+1}/{len(creators)} | Filled: {filled}")
                sys.stdout.flush()
            
            await asyncio.sleep(random.uniform(1, 2))
        
        await browser.close()
    
    print(f"\nDone: {filled} UIDs backfilled out of {len(creators)}")
    sys.stdout.flush()

if __name__ == '__main__':
    asyncio.run(main())
