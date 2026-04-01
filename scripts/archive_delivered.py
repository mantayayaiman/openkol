#!/usr/bin/env python3
"""
Archive old Delivered/Dropped records to a monthly archive table.
Moves records older than 60 days to keep the main table lean.

Usage:
  python3 archive_delivered.py              # Dry run (show what would move)
  python3 archive_delivered.py --execute    # Actually move records
"""
import subprocess
import json
import time
import sys
from datetime import datetime, timedelta

APP = "JWJ1bgcn1aS0qismE4PlwXv9gnb"
TBL = "tblIL3Pv5GuEWrw6"
BT = "/Users/aiman/.openclaw/workspace/skills/feishu-bitable/scripts/feishu-bitable.sh"
CUTOFF_DAYS = 60
DRY_RUN = "--execute" not in sys.argv

def bt(cmd, *args):
    result = subprocess.run(["bash", BT, cmd] + list(args), capture_output=True, text=True)
    return json.loads(result.stdout) if result.stdout.strip() else {}

def ensure_archive_table():
    """Create or find the Archive table."""
    tables = bt("list_tables", APP)
    for t in tables.get("items", []):
        if t["name"] == "Archive":
            return t["table_id"]
    
    # Create it
    result = bt("create_table", APP, "Archive")
    if result.get("success"):
        table_id = result["table_id"]
        print(f"Created Archive table: {table_id}")
        
        # It gets created with a default text field. We need to match the main table structure.
        # For simplicity, we'll store key summary fields only.
        fields = bt("list_fields", APP, table_id)
        default_field = fields["items"][0]["field_id"]
        
        # Rename default field
        bt("update_field", APP, table_id, default_field, '{"field_name":"Content Title","type":1}')
        time.sleep(0.3)
        
        # Add key fields
        for field_json in [
            '{"field_name":"Original Task #","type":1}',
            '{"field_name":"Editor","type":1}',
            '{"field_name":"Brand / Pillar","type":1}',
            '{"field_name":"Requestor","type":1}',
            '{"field_name":"Final Status","type":1}',
            '{"field_name":"Content Type","type":1}',
            '{"field_name":"Request Date","type":5,"property":{"date_formatter":"yyyy/MM/dd"}}',
            '{"field_name":"Posting Deadline","type":5,"property":{"date_formatter":"yyyy/MM/dd"}}',
            '{"field_name":"Views","type":2,"property":{"formatter":"0"}}',
            '{"field_name":"Likes","type":2,"property":{"formatter":"0"}}',
            '{"field_name":"Edit Points","type":2,"property":{"formatter":"0"}}',
            '{"field_name":"Archived Date","type":5,"property":{"date_formatter":"yyyy/MM/dd"}}',
        ]:
            bt("create_field", APP, table_id, field_json)
            time.sleep(0.3)
        
        return table_id
    
    print("ERROR: Failed to create Archive table")
    return None

def get_old_records():
    """Fetch Delivered/Dropped records older than CUTOFF_DAYS."""
    cutoff_ms = int((datetime.now() - timedelta(days=CUTOFF_DAYS)).timestamp() * 1000)
    
    all_records = []
    page = None
    
    while True:
        query = {
            "filter": {"conjunction": "and", "conditions": [
                {"field_name": "Final Status", "operator": "is", "value": ["Delivered"]},
                {"field_name": "Posting Deadline", "operator": "isLess", "value": ["ExactDate", str(cutoff_ms)]}
            ]},
            "field_names": ["Content Title", "Task #", "Editor (PIC)", "Brand / Pillar", "Requestor",
                          "Final Status", "Content Type", "Request Date", "Posting Deadline",
                          "Views", "Likes", "Edit Points"],
            "page_size": 500
        }
        if page:
            query["page_token"] = page
        
        result = bt("search_records", APP, TBL, json.dumps(query))
        items = result.get("items", [])
        all_records.extend(items)
        
        if result.get("has_more"):
            page = result.get("page_token")
            time.sleep(0.5)
        else:
            break
    
    # Also get old Dropped
    page = None
    while True:
        query = {
            "filter": {"conjunction": "and", "conditions": [
                {"field_name": "Final Status", "operator": "is", "value": ["Dropped"]}
            ]},
            "field_names": ["Content Title", "Task #", "Editor (PIC)", "Brand / Pillar", "Requestor",
                          "Final Status", "Content Type", "Request Date", "Posting Deadline",
                          "Views", "Likes", "Edit Points"],
            "page_size": 500
        }
        if page:
            query["page_token"] = page
        
        result = bt("search_records", APP, TBL, json.dumps(query))
        items = result.get("items", [])
        all_records.extend(items)
        
        if result.get("has_more"):
            page = result.get("page_token")
            time.sleep(0.5)
        else:
            break
    
    return all_records

def extract_text(val):
    """Extract text from Lark field value."""
    if isinstance(val, list):
        return "".join(v.get("text", "") for v in val if isinstance(v, dict))
    if isinstance(val, dict):
        return val.get("text", str(val))
    return str(val) if val else ""

def archive_records(records, archive_table_id):
    """Copy records to archive table and delete from main."""
    now_ms = int(datetime.now().timestamp() * 1000)
    
    # Build archive records
    archive_batch = []
    delete_ids = []
    
    for r in records:
        f = r["fields"]
        archive_batch.append({
            "fields": {
                "Content Title": extract_text(f.get("Content Title", "")),
                "Original Task #": extract_text(f.get("Task #", "")),
                "Editor": f.get("Editor (PIC)", ""),
                "Brand / Pillar": f.get("Brand / Pillar", ""),
                "Requestor": f.get("Requestor", ""),
                "Final Status": f.get("Final Status", ""),
                "Content Type": f.get("Content Type", ""),
                "Request Date": f.get("Request Date"),
                "Posting Deadline": f.get("Posting Deadline"),
                "Views": f.get("Views", 0) or 0,
                "Likes": f.get("Likes", 0) or 0,
                "Edit Points": f.get("Edit Points", 0) or 0,
                "Archived Date": now_ms
            }
        })
        delete_ids.append(r["record_id"])
    
    # Create in archive (batches of 500)
    created = 0
    for i in range(0, len(archive_batch), 500):
        chunk = archive_batch[i:i+500]
        result = bt("create_records", APP, archive_table_id, json.dumps({"records": chunk}))
        if result.get("success"):
            created += len(chunk)
            print(f"  Archived {created}/{len(archive_batch)} records")
        else:
            print(f"  ERROR archiving: {result.get('error', 'unknown')}")
            return created, 0
        time.sleep(1)
    
    # Delete from main (batches of 500)
    deleted = 0
    for i in range(0, len(delete_ids), 500):
        chunk = delete_ids[i:i+500]
        result = bt("delete_records", APP, TBL, json.dumps({"records": chunk}))
        if result.get("success"):
            deleted += len(chunk)
            print(f"  Deleted {deleted}/{len(delete_ids)} from main table")
        else:
            print(f"  ERROR deleting: {result.get('error', 'unknown')}")
            return created, deleted
        time.sleep(1)
    
    return created, deleted

if __name__ == "__main__":
    print(f"Content Tasks Archiver — {'DRY RUN' if DRY_RUN else 'EXECUTING'}")
    print(f"Cutoff: {CUTOFF_DAYS} days ({(datetime.now() - timedelta(days=CUTOFF_DAYS)).strftime('%Y-%m-%d')})")
    print()
    
    records = get_old_records()
    print(f"Found {len(records)} records to archive")
    
    if not records:
        print("Nothing to archive ✅")
        sys.exit(0)
    
    # Show breakdown
    by_status = {}
    for r in records:
        s = r["fields"].get("Final Status", "(none)")
        by_status[s] = by_status.get(s, 0) + 1
    for s, n in by_status.items():
        print(f"  {s}: {n}")
    
    if DRY_RUN:
        print("\nDry run — no changes made. Use --execute to archive.")
    else:
        archive_id = ensure_archive_table()
        if archive_id:
            created, deleted = archive_records(records, archive_id)
            print(f"\n✅ Archived: {created} | Deleted from main: {deleted}")
