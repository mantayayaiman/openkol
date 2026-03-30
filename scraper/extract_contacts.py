#!/usr/bin/env python3
"""
Extract contact info (email, phone) from creator bios and update the database.
Also scrapes link-in-bio pages (Linktree, Beacons, etc.) for contact info.
"""

import sqlite3
import re
import os
import time
import requests
from urllib.parse import urlparse

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kreator.db")

# Email regex
EMAIL_RE = re.compile(
    r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE
)

# Phone regex (international formats)
PHONE_RE = re.compile(
    r'(?:\+?\d{1,4}[\s\-.]?)?\(?\d{2,4}\)?[\s\-.]?\d{3,4}[\s\-.]?\d{3,4}(?:\d{0,4})?'
)

# Link-in-bio URL patterns in bios
LINKINBIO_RE = re.compile(
    r'https?://(?:linktr\.ee|beacons\.ai|bio\.link|lnk\.bio|tap\.bio|lynk\.id|msha\.ke|hoo\.be|campsite\.bio|snipfeed\.co|solo\.to|withkoji\.com|carrd\.co|bit\.ly|tinyurl\.com)/[^\s\)\"\']+',
    re.IGNORECASE
)

# Common non-email @ patterns to skip
SKIP_PATTERNS = {'@gmail', '@yahoo', '@hotmail', '@outlook', '@live', '@icloud', '@proton', '@mail', '@aol', '@msn', '@ymail'}

def extract_email(text: str) -> str | None:
    """Extract the first valid email from text."""
    if not text:
        return None
    matches = EMAIL_RE.findall(text)
    for m in matches:
        # Skip obviously fake ones
        if any(skip in m.lower() for skip in ['example.com', 'test.com', 'email.com']):
            continue
        return m.lower()
    return None


def extract_phone(text: str) -> str | None:
    """Extract phone number from text."""
    if not text:
        return None
    # Look for explicit phone indicators
    phone_indicators = ['phone', 'call', 'whatsapp', 'wa', 'tel', 'hp', 'contact', '📱', '📞', '☎']
    text_lower = text.lower()
    
    # If there's a phone indicator, be more aggressive with extraction
    has_indicator = any(ind in text_lower for ind in phone_indicators)
    
    matches = PHONE_RE.findall(text)
    for m in matches:
        digits = re.sub(r'[^\d]', '', m)
        # Valid phone: 8-15 digits
        if 8 <= len(digits) <= 15:
            if has_indicator or m.startswith('+'):
                return m.strip()
    return None


def extract_linkinbio_urls(text: str) -> list[str]:
    """Extract link-in-bio URLs from text."""
    if not text:
        return []
    return LINKINBIO_RE.findall(text)


def scrape_linkinbio(url: str) -> dict:
    """Scrape a link-in-bio page for contact info."""
    result = {'email': None, 'phone': None, 'links': []}
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        }
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        if resp.status_code != 200:
            return result
        
        text = resp.text
        
        # Extract emails from page
        email = extract_email(text)
        if email:
            result['email'] = email
        
        # Extract phone from page  
        phone = extract_phone(text)
        if phone:
            result['phone'] = phone
            
    except Exception as e:
        pass
    
    return result


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Phase 1: Extract from bios
    print("Phase 1: Extracting contacts from bios...")
    rows = cur.execute("""
        SELECT id, name, bio, contact_email 
        FROM creators 
        WHERE bio IS NOT NULL AND bio != ''
    """).fetchall()
    
    bio_updates = 0
    phone_updates = 0
    
    for row in rows:
        existing = row['contact_email'] or ''
        bio = row['bio'] or ''
        
        email = extract_email(bio)
        phone = extract_phone(bio)
        
        new_contact = existing
        
        # Add email if we found one and don't already have one
        if email and '@' not in existing:
            new_contact = email
            bio_updates += 1
        
        # Add phone if we found one and don't already have contact
        if phone and not new_contact:
            new_contact = f"Phone: {phone}"
            phone_updates += 1
        
        if new_contact != existing:
            cur.execute("UPDATE creators SET contact_email = ? WHERE id = ?", (new_contact, row['id']))
    
    conn.commit()
    print(f"  Extracted {bio_updates} emails + {phone_updates} phones from bios")
    
    # Phase 2: Scrape link-in-bio URLs
    print("\nPhase 2: Scraping link-in-bio pages...")
    rows = cur.execute("""
        SELECT id, name, bio
        FROM creators 
        WHERE (contact_email IS NULL OR contact_email = '')
        AND bio IS NOT NULL AND bio != ''
    """).fetchall()
    
    linkinbio_found = 0
    linkinbio_scraped = 0
    
    for row in rows:
        urls = extract_linkinbio_urls(row['bio'])
        if not urls:
            continue
        
        linkinbio_found += 1
        
        for url in urls[:1]:  # Only first link
            result = scrape_linkinbio(url)
            linkinbio_scraped += 1
            
            if result['email']:
                cur.execute("UPDATE creators SET contact_email = ? WHERE id = ?", (result['email'], row['id']))
                print(f"  ✓ {row['name']}: {result['email']} (from {url})")
            elif result['phone']:
                cur.execute("UPDATE creators SET contact_email = ? WHERE id = ?", (f"Phone: {result['phone']}", row['id']))
                print(f"  ✓ {row['name']}: Phone from {url}")
            
            time.sleep(0.5)  # Rate limit
            
            if linkinbio_scraped >= 200:  # Cap per run
                break
        
        if linkinbio_scraped >= 200:
            break
    
    conn.commit()
    
    # Final stats
    stats = cur.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN contact_email != '' AND contact_email IS NOT NULL THEN 1 ELSE 0 END) as with_contact,
            SUM(CASE WHEN contact_email LIKE '%@%' AND contact_email NOT LIKE 'Phone:%' THEN 1 ELSE 0 END) as with_email,
            SUM(CASE WHEN contact_email LIKE 'Phone:%' THEN 1 ELSE 0 END) as with_phone
        FROM creators
    """).fetchone()
    
    print(f"\n=== Contact Coverage ===")
    print(f"  Total creators: {stats['total']}")
    print(f"  With contact info: {stats['with_contact']} ({stats['with_contact']*100//stats['total']}%)")
    print(f"    Emails: {stats['with_email']}")
    print(f"    Phones: {stats['with_phone']}")
    print(f"  No contact: {stats['total'] - stats['with_contact']}")
    print(f"\n  Link-in-bio pages found: {linkinbio_found}, scraped: {linkinbio_scraped}")
    
    conn.close()


if __name__ == "__main__":
    main()
