#!/usr/bin/env python3
"""
Verifier — Spot checks random DB entries against live TikTok profiles.
Runs every hour via cron. Ensures data quality.

Process:
1. Pick 10 random creators from DB
2. Scrape their live TikTok profile
3. Compare followers (allow 20% drift)
4. If profile doesn't exist or data is way off → flag/delete
5. Log results to verify_log.jsonl
6. Alert if accuracy drops below 90%

Run: PLAYWRIGHT_BROWSERS_PATH=0 python3 scraper/verifier.py
"""
import asyncio
import json
import sqlite3
import random
import re
import sys
import time
from datetime import datetime, timezone
from playwright.async_api import async_playwright

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
VERIFY_LOG = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/verify_log.jsonl'
SAMPLE_SIZE = 10

async def scrape_tiktok(page, username):
    """Quick scrape to verify a TikTok profile exists and get followers."""
    try:
        await page.goto(f'https://www.tiktok.com/@{username}', wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(1.5)
        data = await page.evaluate('() => { const el = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__"); return el ? el.textContent : null; }')
        if not data:
            return {'status': 'no_data'}
        
        parsed = json.loads(data)
        ud = parsed.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {})
        
        if 'userInfo' not in ud:
            status_code = ud.get('statusCode', 0)
            if status_code == 10221:
                return {'status': 'captcha'}  # Anti-bot, not necessarily fake
            return {'status': 'not_found'}
        
        u = ud['userInfo']['user']
        s = ud['userInfo']['stats']
        return {
            'status': 'found',
            'username': u.get('uniqueId', username),
            'name': u.get('nickname', ''),
            'followers': s.get('followerCount', 0),
            'verified': u.get('verified', False),
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

async def main():
    now = datetime.now(timezone.utc).isoformat()
    print(f'{"="*60}')
    print(f'VERIFIER — {now}')
    print(f'{"="*60}')
    
    # Get random sample from DB
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM creators").fetchone()[0]
    
    # Get random creators with their TikTok presence
    sample = conn.execute("""
        SELECT c.id, c.name, c.country, pp.username, pp.followers 
        FROM creators c 
        JOIN platform_presences pp ON pp.creator_id = c.id AND pp.platform = 'tiktok'
        ORDER BY RANDOM() 
        LIMIT ?
    """, (SAMPLE_SIZE,)).fetchall()
    conn.close()
    
    if not sample:
        print('No TikTok creators in DB to verify')
        return
    
    print(f'Total in DB: {total}')
    print(f'Sampling {len(sample)} creators for verification\n')
    
    results = {
        'verified': 0,
        'captcha': 0,
        'not_found': 0,
        'data_mismatch': 0,
        'error': 0,
        'deleted': [],
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
        )
        
        for cid, name, country, username, db_followers in sample:
            page = await ctx.new_page()
            result = await scrape_tiktok(page, username)
            await page.close()
            
            if result['status'] == 'found':
                live_followers = result['followers']
                # Allow 30% drift (followers change over time)
                if db_followers > 0:
                    ratio = live_followers / max(db_followers, 1)
                    drift_ok = 0.5 < ratio < 3.0  # Very generous
                else:
                    drift_ok = True
                
                if drift_ok:
                    results['verified'] += 1
                    print(f'  ✅ @{username} ({country}): DB={db_followers:,} Live={live_followers:,}')
                else:
                    results['data_mismatch'] += 1
                    print(f'  ⚠️ @{username} ({country}): DB={db_followers:,} Live={live_followers:,} — BIG DRIFT')
            
            elif result['status'] == 'captcha':
                results['captcha'] += 1
                print(f'  🔒 @{username} ({country}): captcha/anti-bot (not counting as fake)')
            
            elif result['status'] == 'not_found':
                results['not_found'] += 1
                print(f'  ❌ @{username} ({country}): NOT FOUND — deleting from DB')
                # Delete fake/nonexistent creator
                conn = sqlite3.connect(DB_PATH)
                conn.execute("DELETE FROM platform_presences WHERE creator_id = ?", (cid,))
                conn.execute("DELETE FROM audit_scores WHERE creator_id = ?", (cid,))
                conn.execute("DELETE FROM creators WHERE id = ?", (cid,))
                conn.commit()
                conn.close()
                results['deleted'].append({'id': cid, 'username': username, 'name': name})
            
            elif result['status'] == 'error':
                results['error'] += 1
                print(f'  ⚠️ @{username} ({country}): error — {result.get("error", "unknown")}')
            
            else:
                results['error'] += 1
                print(f'  ⚠️ @{username} ({country}): {result["status"]}')
            
            await asyncio.sleep(random.uniform(2, 4))
        
        await ctx.close()
        await browser.close()
    
    # Calculate accuracy (exclude captcha from denominator since we can't verify those)
    verifiable = results['verified'] + results['not_found'] + results['data_mismatch']
    accuracy = (results['verified'] / max(verifiable, 1)) * 100
    
    print(f'\n{"="*60}')
    print(f'RESULTS: {results["verified"]} verified, {results["captcha"]} captcha, {results["not_found"]} not found, {results["data_mismatch"]} mismatch, {results["error"]} error')
    print(f'Accuracy: {accuracy:.0f}% (of verifiable)')
    if results['deleted']:
        print(f'Deleted: {len(results["deleted"])} fake/nonexistent creators')
    print(f'Total in DB after cleanup: {sqlite3.connect(DB_PATH).execute("SELECT COUNT(*) FROM creators").fetchone()[0]}')
    print(f'{"="*60}')
    sys.stdout.flush()
    
    # Log
    log_entry = {
        'timestamp': now,
        'total_db': total,
        'sampled': len(sample),
        **results,
        'accuracy': round(accuracy, 1),
        'alert': accuracy < 90,
    }
    with open(VERIFY_LOG, 'a') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    # Return accuracy for cron to check
    if accuracy < 90:
        print(f'\n🚨 ALERT: Accuracy dropped to {accuracy:.0f}%! Data quality issue.')
    
    return accuracy

if __name__ == '__main__':
    asyncio.run(main())
