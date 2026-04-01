import asyncio
import json
import sqlite3
import random
import time
from playwright.async_api import async_playwright

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'

async def verify_all():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    creators = conn.execute('''
        SELECT c.id, pp.username, c.name, c.country,
               pp.id as presence_id, pp.followers, pp.following, pp.total_likes
        FROM creators c
        JOIN platform_presences pp ON pp.creator_id = c.id
        WHERE pp.platform = 'tiktok'
        ORDER BY c.id
    ''').fetchall()
    
    print(f'Total TikTok creators to verify: {len(creators)}')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        verified = []
        fake = []
        failed = []
        mismatch_details = []
        context_refresh_count = 0
        consecutive_fails = 0
        
        for i, creator in enumerate(creators):
            username = creator['username']
            db_followers = creator['followers']
            
            # If too many consecutive fails, refresh browser context
            if consecutive_fails >= 5:
                print(f'  ⚠️  {consecutive_fails} consecutive failures — refreshing browser context...')
                await ctx.close()
                await asyncio.sleep(5)
                ctx = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080}
                )
                context_refresh_count += 1
                consecutive_fails = 0
            
            page = await ctx.new_page()
            try:
                await page.goto(f'https://www.tiktok.com/@{username}', wait_until='networkidle', timeout=30000)
                await asyncio.sleep(2)
                
                data = await page.evaluate('''() => {
                    const el = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");
                    return el ? el.textContent : null;
                }''')
                
                if data:
                    parsed = json.loads(data)
                    ds = parsed.get('__DEFAULT_SCOPE__', {})
                    ud = ds.get('webapp.user-detail', {})
                    if 'userInfo' in ud:
                        u = ud['userInfo']['user']
                        s = ud['userInfo']['stats']
                        real_followers = s.get('followerCount', 0)
                        real_following = s.get('followingCount', 0)
                        real_likes = s.get('heartCount', 0)
                        real_name = u.get('nickname', '')
                        
                        consecutive_fails = 0
                        
                        # Check if data is reasonable
                        if db_followers and real_followers:
                            ratio = real_followers / db_followers if db_followers > 0 else 0
                            if 0.5 <= ratio <= 2.0:
                                status = 'MATCH'
                                verified.append(creator['id'])
                            else:
                                status = f'MISMATCH (ratio={ratio:.2f})'
                                # Don't delete mismatches — they're real profiles with wrong DB data
                                # Just update with real data
                                verified.append(creator['id'])
                                mismatch_details.append({
                                    'username': username,
                                    'db_followers': db_followers,
                                    'real_followers': real_followers,
                                    'ratio': ratio
                                })
                        else:
                            if real_followers > 0:
                                status = 'VERIFIED'
                                verified.append(creator['id'])
                            else:
                                status = 'EMPTY_PROFILE'
                                fake.append(creator['id'])
                        
                        # Update DB with real data
                        conn.execute('''UPDATE platform_presences 
                            SET followers = ?, following = ?, total_likes = ?
                            WHERE id = ?''',
                            (real_followers, real_following, real_likes, creator['presence_id']))
                        conn.execute('''UPDATE creators SET name = ? WHERE id = ?''',
                            (real_name, creator['id']))
                        conn.commit()
                        
                        print(f'[{i+1}/{len(creators)}] @{username}: DB={db_followers:,} Real={real_followers:,} → {status}')
                    else:
                        # Check if statusCode indicates user doesn't exist
                        status_code = ud.get('statusCode', 0)
                        if status_code == 10221:
                            print(f'[{i+1}/{len(creators)}] @{username}: USER NOT FOUND (status 10221) → FAKE')
                            fake.append(creator['id'])
                            consecutive_fails = 0
                        elif status_code == 10222:
                            # Account banned/suspended
                            print(f'[{i+1}/{len(creators)}] @{username}: ACCOUNT BANNED (status 10222) → FAKE')
                            fake.append(creator['id'])
                            consecutive_fails = 0
                        else:
                            print(f'[{i+1}/{len(creators)}] @{username}: NO USER INFO (status={status_code}) → FAKE')
                            fake.append(creator['id'])
                            consecutive_fails = 0
                else:
                    print(f'[{i+1}/{len(creators)}] @{username}: NO HYDRATION DATA → SKIP')
                    failed.append(creator['id'])
                    consecutive_fails += 1
                    
            except Exception as e:
                err_msg = str(e)[:80]
                print(f'[{i+1}/{len(creators)}] @{username}: ERROR {err_msg} → SKIP')
                failed.append(creator['id'])
                consecutive_fails += 1
            finally:
                await page.close()
            
            # Rate limit: random 2-4 second delay, longer if we've had fails
            delay = random.uniform(3, 6) if consecutive_fails > 2 else random.uniform(2, 4)
            await asyncio.sleep(delay)
        
        await browser.close()
    
    # Delete fake entries
    if fake:
        print(f'\n--- DELETING {len(fake)} FAKE ENTRIES ---')
        for cid in fake:
            pids = [r[0] for r in conn.execute('SELECT id FROM platform_presences WHERE creator_id = ?', (cid,)).fetchall()]
            for pid in pids:
                conn.execute('DELETE FROM metrics_history WHERE presence_id = ?', (pid,))
            conn.execute('DELETE FROM content_samples WHERE creator_id = ?', (cid,))
            conn.execute('DELETE FROM audit_scores WHERE creator_id = ?', (cid,))
            conn.execute('DELETE FROM platform_presences WHERE creator_id = ?', (cid,))
            conn.execute('DELETE FROM creators WHERE id = ?', (cid,))
            uname = [c['username'] for c in creators if c['id'] == cid]
            print(f'  Deleted: @{uname[0] if uname else cid}')
        conn.commit()
    
    # Summary
    remaining = conn.execute('SELECT COUNT(*) FROM creators').fetchone()[0]
    print('\n=== VERIFICATION COMPLETE ===')
    print(f'Total checked: {len(creators)}')
    print(f'Verified REAL: {len(verified)}')
    print(f'FAKE (deleted): {len(fake)}')
    print(f'Errors (skipped): {len(failed)}')
    print(f'Remaining in DB: {remaining}')
    print(f'Context refreshes: {context_refresh_count}')
    
    if mismatch_details:
        print('\n--- DATA MISMATCHES (updated with real data) ---')
        for m in mismatch_details:
            print(f'  @{m["username"]}: DB={m["db_followers"]:,} → Real={m["real_followers"]:,} (ratio={m["ratio"]:.2f})')
    
    # Write report
    with open('/Users/aiman/.openclaw/workspace/projects/kreator/scraper/full_verification_report.md', 'w') as f:
        f.write('# Full Verification Report\n\n')
        f.write(f'**Date:** {time.strftime("%Y-%m-%d %H:%M:%S")}\n\n')
        f.write('## Summary\n\n')
        f.write(f'- Total checked: {len(creators)}\n')
        f.write(f'- Verified REAL: {len(verified)}\n')
        f.write(f'- FAKE (deleted): {len(fake)}\n')
        f.write(f'- Errors (skipped): {len(failed)}\n')
        f.write(f'- Remaining in DB: {remaining}\n')
        f.write(f'- Context refreshes: {context_refresh_count}\n\n')
        
        if fake:
            f.write('## Deleted Fake Entries\n\n')
            for cid in fake:
                uname = [c['username'] for c in creators if c['id'] == cid]
                f.write(f'- @{uname[0] if uname else cid}\n')
            f.write('\n')
        
        if mismatch_details:
            f.write('## Data Mismatches (corrected)\n\n')
            for m in mismatch_details:
                f.write(f'- @{m["username"]}: DB={m["db_followers"]:,} → Real={m["real_followers"]:,}\n')
            f.write('\n')
        
        if failed:
            f.write('## Failed to Verify (skipped)\n\n')
            for cid in failed:
                uname = [c['username'] for c in creators if c['id'] == cid]
                f.write(f'- @{uname[0] if uname else cid}\n')
    
    conn.close()
    print('\nReport saved to scraper/full_verification_report.md')

asyncio.run(verify_all())
