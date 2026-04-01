#!/usr/bin/env python3
"""
Content Assignment Workflow Monitor
Runs periodically (via heartbeat or cron) to enforce the content workflow:

1. First Draft Ready without Draft Link → nag editor, flag to requestor
2. First Draft Ready with Draft Link → notify requestor for approval
3. Pending to Post without Posting Link → daily reminder to requestor
4. Pending to Post with Posting Link → auto-move to Posted

Notifications go to the "content assignemnt lark" WhatsApp group.
"""
import subprocess
import json
import time
import os
from datetime import datetime, timezone, timedelta

BT = ["bash", os.path.expanduser("~/.openclaw/workspace/skills/feishu-bitable/scripts/feishu-bitable.sh")]
APP = "JWJ1bgcn1aS0qismE4PlwXv9gnb"
TBL = "tblIL3Pv5GuEWrw6"
STATE_FILE = os.path.expanduser("~/.openclaw/workspace/projects/kreator/scripts/workflow_state.json")

SGT = timezone(timedelta(hours=8))

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "notified_draft_ready": [],      # record_ids where requestor was notified
        "notified_draft_missing": [],    # record_ids where editor was nagged
        "last_pending_reminder": {},     # record_id -> last reminder timestamp
        "auto_posted": [],               # record_ids auto-moved to Posted
    }

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def search_by_status(status):
    """Fetch all records with given status."""
    all_records = []
    page_token = None
    while True:
        body = {
            "field_names": ["Content Title", "Final Status", "Draft Link", "Posting Link", 
                          "Requestor", "Editor (PIC)", "1st Draft Deadline", "Posting Deadline"],
            "filter": {"conjunction": "and", "conditions": [
                {"field_name": "Final Status", "operator": "is", "value": [status]}
            ]},
            "page_size": 200
        }
        if page_token:
            body["page_token"] = page_token
        result = subprocess.run(BT + ["search_records", APP, TBL, json.dumps(body)], 
                              capture_output=True, text=True)
        data = json.loads(result.stdout)
        items = data.get("items", [])
        all_records.extend(items)
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")
        time.sleep(0.3)
    return all_records

def update_record_status(record_id, new_status):
    """Update a single record's status."""
    body = json.dumps({"records": [{"record_id": record_id, "fields": {"Final Status": new_status}}]})
    result = subprocess.run(BT + ["update_records", APP, TBL, body], capture_output=True, text=True)
    return json.loads(result.stdout) if result.stdout else {}

def get_draft_link(fields):
    """Extract draft link from fields (URL type can be string or object)."""
    dl = fields.get("Draft Link")
    if not dl:
        return None
    if isinstance(dl, dict):
        return dl.get("link") or dl.get("text")
    return str(dl) if dl else None

def get_posting_link(fields):
    """Extract posting link from fields."""
    pl = fields.get("Posting Link")
    if not pl:
        return None
    if isinstance(pl, dict):
        return pl.get("link") or pl.get("text")
    return str(pl) if pl else None

def run_monitor():
    state = load_state()
    now = datetime.now(SGT)
    messages = []  # Collect messages to output
    
    # === 1. Check "First Draft Ready" ===
    draft_ready = search_by_status("First Draft Ready")
    time.sleep(0.5)
    
    for rec in draft_ready:
        rid = rec["record_id"]
        fields = rec.get("fields", {})
        title = fields.get("Content Title", "(untitled)")
        editor = fields.get("Editor (PIC)", "?")
        requestor = fields.get("Requestor", "?")
        draft_link = get_draft_link(fields)
        
        if not draft_link:
            # Draft link missing — nag
            if rid not in state["notified_draft_missing"]:
                messages.append(f"⚠️ *{editor}* marked \"{title}\" as First Draft Ready but didn't include a draft link. Please add the video link!")
                state["notified_draft_missing"].append(rid)
        else:
            # Draft link present — notify requestor for approval
            if rid not in state["notified_draft_ready"]:
                messages.append(f"📋 *{requestor}*, first draft ready for review:\n• *{title}* (by {editor})\n• Draft: {draft_link}\nPlease review and approve to move to Pending to Post.")
                state["notified_draft_ready"].append(rid)
    
    # === 2. Check "Pending to Post" ===
    pending_post = search_by_status("Pending to Post")
    time.sleep(0.5)
    
    for rec in pending_post:
        rid = rec["record_id"]
        fields = rec.get("fields", {})
        title = fields.get("Content Title", "(untitled)")
        requestor = fields.get("Requestor", "?")
        posting_link = get_posting_link(fields)
        
        if posting_link:
            # Has posting link → auto-move to Posted
            update_record_status(rid, "Posted")
            time.sleep(0.5)
            if rid not in state["auto_posted"]:
                messages.append(f"✅ \"{title}\" auto-moved to *Posted* (posting link added by {requestor})")
                state["auto_posted"].append(rid)
        else:
            # No posting link — send daily reminder
            last_reminder = state["last_pending_reminder"].get(rid)
            should_remind = True
            if last_reminder:
                last_dt = datetime.fromisoformat(last_reminder)
                if (now - last_dt).total_seconds() < 20 * 3600:  # ~20h cooldown
                    should_remind = False
            
            if should_remind:
                messages.append(f"🔔 *{requestor}*, \"{title}\" is approved and pending to post. Please add the posting link once it's live!")
                state["last_pending_reminder"][rid] = now.isoformat()
    
    # === 3. Cleanup old state entries ===
    # Keep state arrays from growing forever — prune entries older than 30 days
    # (Simple approach: keep last 500 entries)
    for key in ["notified_draft_ready", "notified_draft_missing", "auto_posted"]:
        if len(state[key]) > 500:
            state[key] = state[key][-200:]
    
    save_state(state)
    
    # Output results
    if messages:
        print("=== WORKFLOW NOTIFICATIONS ===")
        for msg in messages:
            print(msg)
            print()
        print(f"Total: {len(messages)} notifications")
    else:
        print("No workflow actions needed.")
    
    # Summary
    print("\n--- Summary ---")
    print(f"First Draft Ready: {len(draft_ready)} records")
    print(f"  - Missing draft link: {sum(1 for r in draft_ready if not get_draft_link(r.get('fields',{})))}")
    print(f"  - With draft link (awaiting approval): {sum(1 for r in draft_ready if get_draft_link(r.get('fields',{})))}")
    print(f"Pending to Post: {len(pending_post)} records")
    print(f"  - Auto-posted (link found): {sum(1 for r in pending_post if get_posting_link(r.get('fields',{})))}")
    print(f"  - Awaiting posting link: {sum(1 for r in pending_post if not get_posting_link(r.get('fields',{})))}")

if __name__ == "__main__":
    run_monitor()
