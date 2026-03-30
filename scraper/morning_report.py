#!/usr/bin/env python3
"""Generate morning summary of overnight scraping."""
import sqlite3, json, os
from datetime import datetime, timezone

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'
HEALTH_LOG = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/health.jsonl'
SPOT_LOG = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/spot_check.jsonl'
REPORT_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/scraper/morning_report.txt'

conn = sqlite3.connect(DB_PATH)
total = conn.execute('SELECT COUNT(*) FROM creators').fetchone()[0]
countries = dict(conn.execute('SELECT country, COUNT(*) FROM creators GROUP BY country ORDER BY COUNT(*) DESC').fetchall())
top5 = conn.execute('''
    SELECT c.name, c.country, pp.username, pp.followers
    FROM creators c JOIN platform_presences pp ON pp.creator_id = c.id
    ORDER BY pp.followers DESC LIMIT 5
''').fetchall()
conn.close()

# Read health logs
health_entries = []
if os.path.exists(HEALTH_LOG):
    with open(HEALTH_LOG) as f:
        for line in f:
            if line.strip():
                health_entries.append(json.loads(line))

# Read spot check logs
spot_entries = []
if os.path.exists(SPOT_LOG):
    with open(SPOT_LOG) as f:
        for line in f:
            if line.strip():
                spot_entries.append(json.loads(line))

avg_accuracy = 0
if spot_entries:
    accuracies = [e['accuracy'] for e in spot_entries if e.get('accuracy', 0) > 0]
    avg_accuracy = round(sum(accuracies) / len(accuracies)) if accuracies else 0

report = f"""🌅 OpenKOL Overnight Report

DB: {total} creators
Countries: {', '.join(f'{k}: {v}' for k, v in countries.items())}

Top 5:
"""
for name, country, username, followers in top5:
    report += f"  {country} @{username} — {followers:,} ({name})\n"

report += f"""
Health checks: {len(health_entries)} runs
Spot checks: {len(spot_entries)} runs
Avg accuracy: {avg_accuracy}%
"""

with open(REPORT_PATH, 'w') as f:
    f.write(report)

print(report)
