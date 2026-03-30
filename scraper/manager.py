#!/usr/bin/env python3
"""
Scraper Manager — Autonomous health monitor and auto-restarter.
Runs every 30 minutes via cron. Checks all scrapers, restarts dead ones.

Scrapers managed:
1. turbo_scraper.py (TikTok — main volume driver)
2. instagram_scraper.py (IG cross-platform)
3. youtube_scraper.py (YT cross-platform)

For each scraper:
- Check if process is alive (ps aux)
- Check if it's actually producing (DB count change in last 30 min)
- If dead or stalled: kill and restart
- Log everything to health.jsonl

Run: python3 scraper/manager.py
"""
import subprocess
import sqlite3
import json
import time
import os
import sys
from datetime import datetime, timezone

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
SCRAPER_DIR = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper'
PROJECT_DIR = '/Users/aiman/.openclaw/workspace/projects/kreator'
HEALTH_LOG = os.path.join(SCRAPER_DIR, 'health.jsonl')
STATE_FILE = os.path.join(SCRAPER_DIR, 'manager_state.json')

# Scraper definitions
SCRAPERS = [
    {
        'name': 'tiktok_turbo',
        'process_match': 'turbo_scraper.py',
        'cmd': f'cd {PROJECT_DIR} && PLAYWRIGHT_BROWSERS_PATH=0 nohup python3 -u scraper/turbo_scraper.py >> scraper/turbo.log 2>&1 &',
        'log': 'turbo.log',
        'platform': 'tiktok',
        'critical': True,
    },
    {
        'name': 'instagram_turbo',
        'process_match': 'turbo_ig.py',
        'cmd': f'cd {PROJECT_DIR} && PLAYWRIGHT_BROWSERS_PATH=0 nohup python3 -u scraper/turbo_ig.py >> scraper/turbo_ig.log 2>&1 &',
        'log': 'turbo_ig.log',
        'platform': 'instagram',
        'critical': True,
    },
    {
        'name': 'youtube_turbo',
        'process_match': 'turbo_yt.py',
        'cmd': f'cd {PROJECT_DIR} && PLAYWRIGHT_BROWSERS_PATH=0 nohup python3 -u scraper/turbo_yt.py >> scraper/turbo_yt.log 2>&1 &',
        'log': 'turbo_yt.log',
        'platform': 'youtube',
        'critical': True,
    },
    {
        'name': 'facebook_turbo',
        'process_match': 'turbo_fb.py',
        'cmd': f'cd {PROJECT_DIR} && PLAYWRIGHT_BROWSERS_PATH=0 nohup python3 -u scraper/turbo_fb.py >> scraper/turbo_fb.log 2>&1 &',
        'log': 'turbo_fb.log',
        'platform': 'facebook',
        'critical': True,
    },
]

def is_process_alive(match_str):
    """Check if a process matching the string is running."""
    try:
        result = subprocess.run(['pgrep', '-f', match_str], capture_output=True, text=True)
        pids = result.stdout.strip().split('\n')
        pids = [p for p in pids if p]
        return len(pids) > 0, pids
    except:
        return False, []

def get_platform_count(platform):
    """Get count of presences for a platform."""
    try:
        conn = sqlite3.connect(DB_PATH)
        count = conn.execute("SELECT COUNT(*) FROM platform_presences WHERE platform = ?", (platform,)).fetchone()[0]
        conn.close()
        return count
    except:
        return -1

def get_total_creators():
    try:
        conn = sqlite3.connect(DB_PATH)
        count = conn.execute("SELECT COUNT(*) FROM creators").fetchone()[0]
        conn.close()
        return count
    except:
        return -1

def load_state():
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def log_health(entry):
    with open(HEALTH_LOG, 'a') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

def kill_process(match_str):
    """Kill all processes matching the string."""
    try:
        subprocess.run(['pkill', '-f', match_str], capture_output=True)
        time.sleep(2)
        # Force kill if still alive
        alive, _ = is_process_alive(match_str)
        if alive:
            subprocess.run(['pkill', '-9', '-f', match_str], capture_output=True)
            time.sleep(1)
    except:
        pass

def restart_scraper(scraper):
    """Kill and restart a scraper."""
    print(f'  🔄 Restarting {scraper["name"]}...')
    kill_process(scraper['process_match'])
    time.sleep(3)
    # Start new process
    subprocess.Popen(scraper['cmd'], shell=True, cwd=PROJECT_DIR)
    time.sleep(5)
    alive, pids = is_process_alive(scraper['process_match'])
    if alive:
        print(f'  ✅ {scraper["name"]} restarted (PID: {",".join(pids)})')
    else:
        print(f'  ❌ {scraper["name"]} FAILED to restart!')
    return alive

def main():
    now = datetime.now(timezone.utc).isoformat()
    state = load_state()
    
    print(f'\n{"="*60}')
    print(f'SCRAPER MANAGER — {now}')
    print(f'{"="*60}')
    
    total_creators = get_total_creators()
    print(f'Total creators in DB: {total_creators}')
    
    health_entry = {
        'timestamp': now,
        'total_creators': total_creators,
        'scrapers': {},
    }
    
    any_restarted = False
    
    for scraper in SCRAPERS:
        name = scraper['name']
        alive, pids = is_process_alive(scraper['process_match'])
        platform_count = get_platform_count(scraper['platform']) if scraper['platform'] else -1
        
        # Check if stalled (count hasn't changed in 30+ min)
        prev_count = state.get(f'{name}_count', 0)
        prev_time = state.get(f'{name}_time', 0)
        time_since = time.time() - prev_time if prev_time else 999
        count_change = platform_count - prev_count if prev_count else platform_count
        
        stalled = alive and time_since > 1800 and count_change == 0 and prev_time > 0
        
        status = 'alive' if alive and not stalled else 'stalled' if stalled else 'dead'
        
        print(f'\n  [{name}] Status: {status} | PID: {",".join(pids) if pids else "none"} | {scraper["platform"]}: {platform_count} | Δ: +{count_change}')
        
        health_entry['scrapers'][name] = {
            'alive': alive,
            'stalled': stalled,
            'pids': pids,
            'count': platform_count,
            'count_change': count_change,
        }
        
        # Auto-restart if dead or stalled
        if not alive or stalled:
            reason = 'stalled (no new data in 30min)' if stalled else 'dead'
            print(f'  ⚠️ {name} is {reason} — auto-restarting...')
            restarted = restart_scraper(scraper)
            health_entry['scrapers'][name]['restarted'] = restarted
            health_entry['scrapers'][name]['restart_reason'] = reason
            any_restarted = True
        
        # Update state
        state[f'{name}_count'] = platform_count
        state[f'{name}_time'] = time.time()
    
    # Country breakdown
    try:
        conn = sqlite3.connect(DB_PATH)
        countries = conn.execute('SELECT country, COUNT(*) FROM creators GROUP BY country ORDER BY COUNT(*) DESC').fetchall()
        conn.close()
        print(f'\n  Country breakdown:')
        for c, n in countries:
            print(f'    {c}: {n}')
        health_entry['countries'] = {c: n for c, n in countries}
    except:
        pass
    
    save_state(state)
    log_health(health_entry)
    
    if any_restarted:
        print(f'\n  ⚡ Scrapers were restarted. Manager will check again in 30 min.')
    else:
        print(f'\n  ✅ All scrapers healthy.')
    
    print(f'{"="*60}\n')
    sys.stdout.flush()

if __name__ == '__main__':
    main()
