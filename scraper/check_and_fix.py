#!/usr/bin/env python3
"""
Health checker: runs every 30 min via cron.
1. Is scraper process alive?
2. Is it making progress (new entries in last 30 min)?
3. If not, restart it.
4. Report status.
"""
import subprocess
import sqlite3
import json
import os
import time
from datetime import datetime, timezone

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
LOG_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/overnight.log'
PROGRESS_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/progress.json'
HEALTH_LOG = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/health.jsonl'
SCRAPER_SCRIPT = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/overnight_v3.py'
PROJECT_DIR = '/Users/aiman/.openclaw/workspace/projects/kreator'

def get_db_count():
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute('SELECT COUNT(*) FROM creators').fetchone()[0]
    # Get count added in last 30 min
    recent = conn.execute("SELECT COUNT(*) FROM creators WHERE created_at > datetime('now', '-30 minutes')").fetchone()[0]
    countries = dict(conn.execute('SELECT country, COUNT(*) FROM creators GROUP BY country ORDER BY COUNT(*) DESC').fetchall())
    conn.close()
    return total, recent, countries

def is_scraper_running():
    """Check if overnight_v3.py is running."""
    result = subprocess.run(['pgrep', '-f', 'overnight_v3.py'], capture_output=True, text=True)
    pids = result.stdout.strip().split('\n') if result.stdout.strip() else []
    return len(pids) > 0, pids

def check_all_scrapers():
    """Check status of all 3 scrapers."""
    scrapers = {
        'tiktok': ('overnight_v3.py', '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/overnight_v3.py'),
        'facebook': ('facebook_scraper.py', '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/facebook_scraper.py'),
    }
    # Note: IG and YT scrapers disabled for now
    # IG: blocked without login, all requests fail
    # YT: page parsing needs rework, subscriberCountText extraction unreliable
    status = {}
    for name, (pattern, script) in scrapers.items():
        result = subprocess.run(['pgrep', '-f', pattern], capture_output=True, text=True)
        running = bool(result.stdout.strip())
        status[name] = {'running': running, 'script': script}
    return status

def get_last_log_lines(n=10):
    try:
        result = subprocess.run(['tail', f'-{n}', LOG_PATH], capture_output=True, text=True)
        return result.stdout
    except:
        return ''

def restart_scraper():
    """Kill any existing scraper and start fresh."""
    subprocess.run(['pkill', '-f', 'overnight_v3.py'], capture_output=True)
    time.sleep(2)
    
    # Start new scraper
    env = os.environ.copy()
    env['PLAYWRIGHT_BROWSERS_PATH'] = '0'
    subprocess.Popen(
        ['python3', '-u', SCRAPER_SCRIPT],
        cwd=PROJECT_DIR,
        env=env,
        stdout=open(LOG_PATH, 'a'),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    return True

def main():
    now = datetime.now(timezone.utc).isoformat()
    total, recent, countries = get_db_count()
    running, pids = is_scraper_running()
    last_log = get_last_log_lines(5)
    
    all_scrapers = check_all_scrapers()
    
    # Platform counts
    conn2 = sqlite3.connect(DB_PATH)
    platform_counts = dict(conn2.execute("SELECT platform, COUNT(*) FROM platform_presences GROUP BY platform").fetchall())
    conn2.close()
    
    status = {
        'timestamp': now,
        'db_total': total,
        'added_last_30min': recent,
        'countries': countries,
        'platforms': platform_counts,
        'scraper_running': running,
        'scraper_pids': pids,
        'all_scrapers': {k: v['running'] for k, v in all_scrapers.items()},
        'action': 'none',
    }
    
    print(f'=== HEALTH CHECK {now} ===')
    print(f'DB: {total} creators ({recent} added in last 30min)')
    print(f'Platforms: {platform_counts}')
    print(f'Countries: {countries}')
    print(f'Scrapers: TT={all_scrapers["tiktok"]["running"]} IG={all_scrapers["instagram"]["running"]} YT={all_scrapers["youtube"]["running"]}')
    print(f'Last TT log: {last_log[-200:]}')
    
    # Decision logic — restart any dead scrapers
    actions = []
    for name, info in all_scrapers.items():
        if not info['running']:
            print(f'⚠️ {name} scraper not running! Restarting...')
            env = os.environ.copy()
            env['PLAYWRIGHT_BROWSERS_PATH'] = '0'
            log_file = os.path.join(PROJECT_DIR, 'scraper', f'{name}_overnight.log' if name != 'tiktok' else 'overnight.log')
            subprocess.Popen(
                ['python3', '-u', info['script']],
                cwd=PROJECT_DIR, env=env,
                stdout=open(log_file, 'a'), stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            actions.append(f'restarted {name}')
    
    if not running and 'restarted tiktok' not in actions:
        restart_scraper()
        actions.append('restarted tiktok')
    
    if recent == 0 and total < 200 and running:
        print('⚠️ TikTok scraper running but no progress. Restarting...')
        restart_scraper()
        actions.append('restarted tiktok (stuck)')
    
    if total >= 200:
        print('✅ Target reached (200+)!')
    
    status['action'] = ', '.join(actions) if actions else 'all healthy'
    print(f'\nSTATUS: {status["action"]}')
    
    # Log
    with open(HEALTH_LOG, 'a') as f:
        f.write(json.dumps(status) + '\n')
    
    # Print summary for cron output
    print(f'\nSTATUS: {status["action"]} | DB: {total} | +{recent}/30min')

if __name__ == '__main__':
    main()
