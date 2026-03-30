#!/usr/bin/env python3
"""YT priority worker — scrapes remaining YouTube handles from YuBin's data."""
import asyncio, json, sqlite3, random, re, sys, time
from datetime import datetime, timezone
from playwright.async_api import async_playwright

DB = "/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db"

def parse_count(t):
    t = t.strip().replace(",", ".")
    try:
        if re.search(r'[Jj](?:uta|t)?$', t):
            return int(float(re.sub(r'[^0-9.]', '', t)) * 1e6)
        if re.search(r'rb|ribu', t, re.I):
            return int(float(re.sub(r'[^0-9.]', '', t)) * 1e3)
        if 'M' in t:
            return int(float(re.sub(r'[^0-9.]', '', t)) * 1e6)
        if 'K' in t:
            return int(float(re.sub(r'[^0-9.]', '', t)) * 1e3)
        if 'B' in t:
            return int(float(re.sub(r'[^0-9.]', '', t)) * 1e9)
        return int(float(re.sub(r'[^0-9]', '', t)))
    except:
        return 0

async def main():
    handles = json.load(open("scraper/yt_remaining.json"))
    print(f"YT Priority: {len(handles)} handles")
    sys.stdout.flush()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        await ctx.add_cookies([
            {"name": "CONSENT", "value": "YES+cb.20210720-07-p0.en+FX+410", "domain": ".youtube.com", "path": "/"},
        ])

        inserted = 0
        failed = 0

        for i, h in enumerate(handles):
            page = await ctx.new_page()
            try:
                await page.goto(f"https://www.youtube.com/@{h}", wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(3)

                # Consent click
                try:
                    btn = await page.query_selector('button:has-text("Accept"), button:has-text("Terima")')
                    if btn:
                        await btn.click()
                        await asyncio.sleep(2)
                except:
                    pass

                text = await page.inner_text("body")
                subs = 0
                patterns = [
                    r'([\d,.]+[JKMBjt]*)\s*(?:pelanggan|subscribers?)',
                    r'([\d,.]+[JKMBjt]*)\s*(?:người đăng ký)',
                    r'([\d,.]+[JKMBjt]*)\s*(?:ผู้ติดตาม)',
                ]
                for pat in patterns:
                    m = re.search(pat, text, re.I)
                    if m:
                        subs = parse_count(m.group(1))
                        break

                if subs >= 1000:
                    content = await page.content()
                    title_pattern = r'"channelMetadataRenderer":\{"title":"([^"]*)"'
                    name_m = re.search(title_pattern, content)
                    name = name_m.group(1) if name_m else h

                    conn = sqlite3.connect(DB)
                    exists = conn.execute(
                        "SELECT 1 FROM platform_presences WHERE platform='youtube' AND LOWER(username)=LOWER(?)",
                        (h,),
                    ).fetchone()
                    if not exists:
                        now = datetime.now(timezone.utc).isoformat()
                        ex = conn.execute(
                            "SELECT c.id FROM creators c JOIN platform_presences pp ON pp.creator_id=c.id WHERE LOWER(pp.username)=LOWER(?) LIMIT 1",
                            (h,),
                        ).fetchone()
                        if ex:
                            cid = ex[0]
                        else:
                            cur = conn.execute(
                                "INSERT INTO creators (name,bio,profile_image,country,primary_platform,categories,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                                (name, "", "", "SEA", "youtube", '["entertainment"]', now, now),
                            )
                            cid = cur.lastrowid
                        conn.execute(
                            "INSERT INTO platform_presences (creator_id,platform,username,url,followers,following,total_likes,total_videos,engagement_rate,last_scraped_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (cid, "youtube", h, f"https://www.youtube.com/@{h}", subs, 0, 0, 0, 0, now),
                        )
                        conn.commit()
                        inserted += 1
                        print(f"  ✅ YT #{inserted} @{h} — {subs:,}")
                        sys.stdout.flush()
                    conn.close()
                else:
                    failed += 1
            except:
                failed += 1
            await page.close()

            if (i + 1) % 25 == 0:
                await ctx.close()
                ctx = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    viewport={"width": 1920, "height": 1080},
                )
                await ctx.add_cookies([
                    {"name": "CONSENT", "value": "YES+cb.20210720-07-p0.en+FX+410", "domain": ".youtube.com", "path": "/"},
                ])
                print(f"  Progress: {i+1}/{len(handles)} | Inserted: {inserted} | Failed: {failed}")
                sys.stdout.flush()

            await asyncio.sleep(random.uniform(2, 4))

        await browser.close()
        print(f"YT DONE: {inserted} inserted, {failed} failed out of {len(handles)}")
        sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(main())
