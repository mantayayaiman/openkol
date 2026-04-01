#!/usr/bin/env python3
"""
Sync editor workload from active tasks to Editors table.
Run periodically (cron or heartbeat) to keep utilization current.

Usage: python3 sync_editor_workload.py
"""
import subprocess
import json
import time

APP = "JWJ1bgcn1aS0qismE4PlwXv9gnb"
TBL = "tblIL3Pv5GuEWrw6"
EDITORS_TBL = "tblfq7UYjIkL3EnG"
BT = "/Users/aiman/.openclaw/workspace/skills/feishu-bitable/scripts/feishu-bitable.sh"

ACTIVE_STATUSES = [
    "Queue", "Shooting In Progress", "Editing In Progress", "First Draft Ready",
    "Pending to Post"
]

def bt(cmd, *args):
    result = subprocess.run(["bash", BT, cmd] + list(args), capture_output=True, text=True)
    return json.loads(result.stdout) if result.stdout.strip() else {}

def get_editor_load():
    """Calculate Edit Points per editor from active tasks."""
    editor_load = {}
    editor_tasks = {}
    
    for status in ACTIVE_STATUSES:
        page = None
        while True:
            query = {
                "filter": {"conjunction": "and", "conditions": [
                    {"field_name": "Final Status", "operator": "is", "value": [status]}
                ]},
                "field_names": ["Editor (PIC)", "Edit Points"],
                "page_size": 500
            }
            if page:
                query["page_token"] = page
            result = bt("search_records", APP, TBL, json.dumps(query))
            for item in result.get("items", []):
                editor = item["fields"].get("Editor (PIC)", "")
                ep = item["fields"].get("Edit Points", 0) or 0
                if editor:
                    editor_load[editor] = editor_load.get(editor, 0) + ep
                    editor_tasks[editor] = editor_tasks.get(editor, 0) + 1
            if result.get("has_more"):
                page = result.get("page_token")
            else:
                break
            time.sleep(0.2)
    
    return editor_load, editor_tasks

def update_editors(editor_load, editor_tasks):
    """Update Editors table with current load and utilization."""
    editors_result = bt("list_records", APP, EDITORS_TBL)
    editors = editors_result.get("items", [])
    
    updates = []
    for editor in editors:
        fields = editor.get("fields", {})
        name_raw = fields.get("Editor Name", "")
        if isinstance(name_raw, list):
            name = name_raw[0].get("text", "") if name_raw else ""
        else:
            name = str(name_raw)
        
        load = editor_load.get(name, 0)
        tasks = editor_tasks.get(name, 0)
        cap_raw = fields.get("Weekly Capacity (EP)", 15)
        capacity = float(cap_raw) if cap_raw else 15
        utilization = round((load / capacity) * 100) if capacity > 0 else 0
        
        # Set status based on utilization
        if load == 0:
            status = "Available"
        elif utilization >= 90:
            status = "Busy"
        else:
            status = "Available"
        
        # Don't override "On Leave" or "Inactive"
        current_status = fields.get("Status", "")
        if current_status in ("On Leave", "Inactive"):
            status = current_status
        
        updates.append({
            "record_id": editor["record_id"],
            "fields": {
                "Current Load (EP)": load,
                "Utilization %": utilization,
                "Status": status
            }
        })
        
        flag = "🔴" if utilization >= 90 else "🟡" if utilization >= 60 else "🟢"
        print(f"  {flag} {name:10} {load:3} EP ({tasks} tasks) = {utilization}%")
    
    bt("update_records", APP, EDITORS_TBL, json.dumps({"records": updates}))
    return len(updates)

if __name__ == "__main__":
    print("Calculating editor workload...")
    editor_load, editor_tasks = get_editor_load()
    print(f"\nActive editors: {len(editor_load)}")
    n = update_editors(editor_load, editor_tasks)
    print(f"\nUpdated {n} editors ✅")
