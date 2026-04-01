#!/usr/bin/env python3
"""
Content Assignment Dashboard — generates KPI summary.
Can be run on demand or via cron. Outputs to stdout and optionally sends to Feishu.

Usage: 
  python3 content_dashboard.py           # Print to stdout
  python3 content_dashboard.py --send    # Print + send to YuBin via Feishu
"""
import subprocess
import json
import time
import sys
import urllib.request
from datetime import datetime, timedelta

APP = "JWJ1bgcn1aS0qismE4PlwXv9gnb"
TBL = "tblIL3Pv5GuEWrw6"
EDITORS_TBL = "tblfq7UYjIkL3EnG"
BT = "/Users/aiman/.openclaw/workspace/skills/feishu-bitable/scripts/feishu-bitable.sh"
YUBIN_OPEN_ID = "ou_8036042a4fd01cc7f08ad04cda4d531f"

def bt(cmd, *args):
    result = subprocess.run(["bash", BT, cmd] + list(args), capture_output=True, text=True)
    return json.loads(result.stdout) if result.stdout.strip() else {}

def count_status(status):
    r = bt("search_records", APP, TBL, json.dumps({
        "filter": {"conjunction": "and", "conditions": [
            {"field_name": "Final Status", "operator": "is", "value": [status]}
        ]}, "page_size": 1
    }))
    return r.get("total", 0)

def count_by_filter(conditions):
    r = bt("search_records", APP, TBL, json.dumps({
        "filter": {"conjunction": "and", "conditions": conditions},
        "page_size": 1
    }))
    return r.get("total", 0)

def get_recent_deliveries(days=7):
    """Count records that moved to Delivered in the last N days (by Posting Deadline)."""
    cutoff = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    r = bt("search_records", APP, TBL, json.dumps({
        "filter": {"conjunction": "and", "conditions": [
            {"field_name": "Final Status", "operator": "is", "value": ["Delivered"]},
            {"field_name": "Posting Deadline", "operator": "isGreater", "value": ["ExactDate", str(cutoff)]}
        ]}, "page_size": 1
    }))
    return r.get("total", 0)

def get_editor_workload():
    """Get editor workload summary."""
    r = bt("search_records", APP, EDITORS_TBL, json.dumps({
        "field_names": ["Editor Name", "Current Load (EP)", "Utilization %", "Status", "Weekly Capacity (EP)"],
        "page_size": 25,
        "sort": [{"field_name": "Utilization %", "desc": True}]
    }))
    editors = []
    for item in r.get("items", []):
        f = item["fields"]
        name = f.get("Editor Name", "")
        if isinstance(name, list): name = name[0].get("text", "") if name else ""
        editors.append({
            "name": name,
            "load": f.get("Current Load (EP)", 0) or 0,
            "util": f.get("Utilization %", 0) or 0,
            "cap": f.get("Weekly Capacity (EP)", 15) or 15,
            "status": f.get("Status", "")
        })
    return editors

def get_content_type_breakdown():
    """Get active tasks by content type."""
    types = {}
    for ct in ["TikTok Clip", "Brand Content", "Drama Episode", "Gaming Content", "Other"]:
        # Count active (non-delivered/dropped) by content type
        r = bt("search_records", APP, TBL, json.dumps({
            "filter": {"conjunction": "and", "conditions": [
                {"field_name": "Content Type", "operator": "is", "value": [ct]},
                {"field_name": "Final Status", "operator": "isNot", "value": ["Delivered"]},
                {"field_name": "Final Status", "operator": "isNot", "value": ["Dropped"]}
            ]}, "page_size": 1
        }))
        n = r.get("total", 0)
        if n > 0: types[ct] = n
        time.sleep(0.15)
    return types

def get_brand_breakdown_active():
    """Get top brands by active task count."""
    r = bt("search_records", APP, TBL, json.dumps({
        "filter": {"conjunction": "and", "conditions": [
            {"field_name": "Final Status", "operator": "isNot", "value": ["Delivered"]},
            {"field_name": "Final Status", "operator": "isNot", "value": ["Dropped"]}
        ]},
        "field_names": ["Brand / Pillar"],
        "page_size": 500
    }))
    brands = {}
    for item in r.get("items", []):
        b = item["fields"].get("Brand / Pillar", "(none)")
        brands[b] = brands.get(b, 0) + 1
    # Sort by count desc
    return dict(sorted(brands.items(), key=lambda x: -x[1])[:10])

def build_dashboard():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Status counts
    statuses = {}
    active_total = 0
    for s in ["Queue", "In Progress", "Review", "Need to Amend", "Pending Approval", 
              "Pending to Post", "Pending Details", "Delivered", "Dropped", "On Hold"]:
        n = count_status(s)
        statuses[s] = n
        if s not in ("Delivered", "Dropped"):
            active_total += n
        time.sleep(0.15)
    
    # Recent deliveries
    delivered_7d = get_recent_deliveries(7)
    delivered_30d = get_recent_deliveries(30)
    
    # Editor workload
    editors = get_editor_workload()
    overloaded = [e for e in editors if e["util"] >= 90]
    idle = [e for e in editors if e["load"] == 0]
    
    # Content type breakdown (active only)
    ct_active = get_content_type_breakdown()
    
    # Top brands by active work
    top_brands = get_brand_breakdown_active()
    
    # Build output
    lines = []
    lines.append(f"📊 Content Dashboard — {now}")
    lines.append("")
    
    # Pipeline
    lines.append("━━━ Pipeline ━━━")
    lines.append(f"📥 Queue: {statuses['Queue']}  |  🔨 In Progress: {statuses['In Progress']}  |  👁 Review: {statuses['Review']}")
    lines.append(f"🔴 Amend: {statuses['Need to Amend']}  |  ⏳ Approval: {statuses['Pending Approval']}  |  📤 Ready to Post: {statuses['Pending to Post']}")
    lines.append(f"❓ Pending Details: {statuses['Pending Details']}  |  ⏸ On Hold: {statuses['On Hold']}")
    lines.append(f"Active: {active_total}  |  Total: {sum(statuses.values())}")
    lines.append("")
    
    # Throughput
    lines.append("━━━ Throughput ━━━")
    lines.append(f"✅ Delivered (7d): {delivered_7d}  |  (30d): {delivered_30d}")
    weekly_rate = delivered_7d
    monthly_est = round(weekly_rate * 4.3)
    lines.append(f"📈 Run rate: ~{weekly_rate}/week → ~{monthly_est}/month")
    lines.append("")
    
    # Editor workload
    lines.append("━━━ Team Load ━━━")
    if overloaded:
        lines.append(f"🔴 Overloaded ({len(overloaded)}):")
        for e in overloaded:
            lines.append(f"   {e['name']}: {e['load']}/{e['cap']:.0f} EP = {e['util']}%")
    
    active_editors = [e for e in editors if e["load"] > 0 and e["util"] < 90]
    if active_editors:
        lines.append(f"🟡🟢 Active ({len(active_editors)}):")
        for e in active_editors:
            flag = "🟡" if e["util"] >= 60 else "🟢"
            lines.append(f"   {flag} {e['name']}: {e['load']}/{e['cap']:.0f} EP = {e['util']}%")
    
    lines.append(f"💤 Idle: {len(idle)} editors")
    lines.append("")
    
    # Content mix (active)
    if ct_active:
        lines.append("━━━ Active Content Mix ━━━")
        for ct, n in sorted(ct_active.items(), key=lambda x: -x[1]):
            lines.append(f"   {ct}: {n}")
        lines.append("")
    
    # Top brands
    if top_brands:
        lines.append("━━━ Top Active Brands ━━━")
        for b, n in list(top_brands.items())[:5]:
            lines.append(f"   {b}: {n}")
        lines.append("")
    
    return "\n".join(lines)

def send_to_feishu(text):
    config = json.load(open('/Users/aiman/.openclaw/openclaw.json'))
    app_id = config['channels']['feishu']['appId']
    app_secret = config['channels']['feishu']['appSecret']
    
    # Get token
    data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
    req = urllib.request.Request('https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal',
        data=data, headers={'Content-Type': 'application/json'})
    token = json.loads(urllib.request.urlopen(req).read())['tenant_access_token']
    
    # Send
    msg = json.dumps({
        "receive_id": YUBIN_OPEN_ID,
        "msg_type": "text",
        "content": json.dumps({"text": text})
    }).encode()
    req = urllib.request.Request(
        'https://open.larksuite.com/open-apis/im/v1/messages?receive_id_type=open_id',
        data=msg,
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    return resp.get('code') == 0

if __name__ == "__main__":
    dashboard = build_dashboard()
    print(dashboard)
    
    if "--send" in sys.argv:
        ok = send_to_feishu(dashboard)
        print(f"\n{'✅ Sent to Feishu' if ok else '❌ Failed to send'}")
