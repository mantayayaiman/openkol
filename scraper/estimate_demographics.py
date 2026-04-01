#!/usr/bin/env python3
"""
Audience Demographics Estimator — Estimates gender, age, and location splits.
Uses heuristic models based on:
1. Content category (gaming=male 70%, beauty=female 80%, etc.)
2. Creator's country/language
3. Creator's bio signals (pronouns, keywords)
4. Name-based gender inference
5. Category-based age distribution

This is an ESTIMATION — not real data. Clearly labeled as estimated in the UI.
Real data requires creators to connect their business accounts (Phase 2).

Run: python3 scraper/estimate_demographics.py
"""
import sqlite3
import json

DB_PATH = '/Users/aiman/.openclaw/workspace/projects/kreator/kreator.db'

# Category → typical audience demographics (industry benchmarks)
CATEGORY_DEMOGRAPHICS = {
    'gaming': {'male': 72, 'female': 28, 'age_primary': '18-24', 'age_dist': {'13-17': 15, '18-24': 40, '25-34': 30, '35-44': 10, '45+': 5}},
    'beauty': {'male': 15, 'female': 85, 'age_primary': '18-34', 'age_dist': {'13-17': 10, '18-24': 35, '25-34': 35, '35-44': 15, '45+': 5}},
    'food': {'male': 35, 'female': 65, 'age_primary': '25-34', 'age_dist': {'13-17': 5, '18-24': 25, '25-34': 35, '35-44': 25, '45+': 10}},
    'fashion': {'male': 20, 'female': 80, 'age_primary': '18-34', 'age_dist': {'13-17': 12, '18-24': 38, '25-34': 30, '35-44': 15, '45+': 5}},
    'music': {'male': 45, 'female': 55, 'age_primary': '18-24', 'age_dist': {'13-17': 20, '18-24': 35, '25-34': 25, '35-44': 12, '45+': 8}},
    'comedy': {'male': 55, 'female': 45, 'age_primary': '18-24', 'age_dist': {'13-17': 15, '18-24': 35, '25-34': 30, '35-44': 15, '45+': 5}},
    'tech': {'male': 75, 'female': 25, 'age_primary': '25-34', 'age_dist': {'13-17': 5, '18-24': 25, '25-34': 40, '35-44': 20, '45+': 10}},
    'fitness': {'male': 55, 'female': 45, 'age_primary': '25-34', 'age_dist': {'13-17': 5, '18-24': 30, '25-34': 40, '35-44': 18, '45+': 7}},
    'travel': {'male': 40, 'female': 60, 'age_primary': '25-34', 'age_dist': {'13-17': 5, '18-24': 25, '25-34': 35, '35-44': 25, '45+': 10}},
    'education': {'male': 50, 'female': 50, 'age_primary': '18-24', 'age_dist': {'13-17': 15, '18-24': 35, '25-34': 30, '35-44': 15, '45+': 5}},
    'family': {'male': 25, 'female': 75, 'age_primary': '25-34', 'age_dist': {'13-17': 3, '18-24': 15, '25-34': 40, '35-44': 30, '45+': 12}},
    'finance': {'male': 65, 'female': 35, 'age_primary': '25-34', 'age_dist': {'13-17': 2, '18-24': 20, '25-34': 40, '35-44': 25, '45+': 13}},
    'automotive': {'male': 80, 'female': 20, 'age_primary': '25-34', 'age_dist': {'13-17': 5, '18-24': 20, '25-34': 35, '35-44': 28, '45+': 12}},
    'pets': {'male': 35, 'female': 65, 'age_primary': '25-34', 'age_dist': {'13-17': 8, '18-24': 25, '25-34': 32, '35-44': 25, '45+': 10}},
    'religious': {'male': 45, 'female': 55, 'age_primary': '25-44', 'age_dist': {'13-17': 5, '18-24': 15, '25-34': 30, '35-44': 30, '45+': 20}},
    'cosplay': {'male': 60, 'female': 40, 'age_primary': '18-24', 'age_dist': {'13-17': 15, '18-24': 40, '25-34': 30, '35-44': 10, '45+': 5}},
    'lifestyle': {'male': 40, 'female': 60, 'age_primary': '18-34', 'age_dist': {'13-17': 10, '18-24': 30, '25-34': 35, '35-44': 18, '45+': 7}},
    'entertainment': {'male': 50, 'female': 50, 'age_primary': '18-24', 'age_dist': {'13-17': 15, '18-24': 35, '25-34': 28, '35-44': 15, '45+': 7}},
}

# Country → typical audience location distribution
# For a MY creator, most audience is from MY but some from ID, SG etc.
COUNTRY_AUDIENCE = {
    'MY': {'MY': 75, 'SG': 8, 'ID': 5, 'BN': 3, 'Other': 9},
    'ID': {'ID': 80, 'MY': 5, 'SG': 3, 'Other': 12},
    'PH': {'PH': 78, 'US': 8, 'SG': 3, 'Other': 11},
    'TH': {'TH': 82, 'Other': 18},
    'VN': {'VN': 80, 'Other': 20},
    'SG': {'SG': 55, 'MY': 15, 'ID': 8, 'PH': 5, 'Other': 17},
    'SEA': {'MY': 25, 'ID': 25, 'PH': 15, 'TH': 10, 'VN': 10, 'SG': 5, 'Other': 10},
}

def estimate_demographics(categories_json, country, bio='', name=''):
    """Estimate audience demographics for a creator."""
    # Parse categories
    try:
        cats = json.loads(categories_json) if isinstance(categories_json, str) else categories_json
    except:
        cats = ['entertainment']
    
    primary_cat = cats[0] if cats else 'entertainment'
    
    # Get category-based demographics
    demo = CATEGORY_DEMOGRAPHICS.get(primary_cat, CATEGORY_DEMOGRAPHICS['entertainment'])
    
    # Adjust gender based on bio signals
    bio_lower = (bio or '').lower() + ' ' + (name or '').lower()
    female_signals = sum(1 for w in ['she/her', 'woman', 'girl', 'queen', 'mom', 'mama', 'wife', 'wanita', 'perempuan', 'ibu', '💄', '👗', '💅'] if w in bio_lower)
    male_signals = sum(1 for w in ['he/him', 'man', 'boy', 'king', 'dad', 'papa', 'husband', 'lelaki', 'abang', '💪'] if w in bio_lower)
    
    gender_male = demo['male']
    gender_female = demo['female']
    
    if female_signals > male_signals:
        gender_female = min(90, gender_female + 10)
        gender_male = 100 - gender_female
    elif male_signals > female_signals:
        gender_male = min(90, gender_male + 10)
        gender_female = 100 - gender_male
    
    # Get location distribution
    location = COUNTRY_AUDIENCE.get(country, COUNTRY_AUDIENCE.get('SEA', {'Other': 100}))
    
    return {
        'gender': {'male': gender_male, 'female': gender_female},
        'age_primary': demo['age_primary'],
        'age_distribution': demo['age_dist'],
        'audience_location': location,
        'estimation_method': 'category_heuristic',
        'confidence': 'estimated',
    }

def main():
    conn = sqlite3.connect(DB_PATH)
    
    # Add demographics column if not exists
    try:
        conn.execute("ALTER TABLE creators ADD COLUMN audience_demographics TEXT DEFAULT ''")
    except:
        pass
    
    # Get all creators
    creators = conn.execute("SELECT id, categories, country, bio, name FROM creators").fetchall()
    
    updated = 0
    for cid, cats, country, bio, name in creators:
        demo = estimate_demographics(cats, country, bio, name)
        conn.execute("UPDATE creators SET audience_demographics=? WHERE id=?", 
                     (json.dumps(demo), cid))
        updated += 1
    
    conn.commit()
    conn.close()
    
    print(f'Estimated demographics for {updated} creators')
    
    # Verify
    conn = sqlite3.connect(DB_PATH)
    sample = conn.execute("""
        SELECT c.name, c.categories, c.country, c.audience_demographics 
        FROM creators c JOIN platform_presences pp ON pp.creator_id=c.id
        WHERE pp.platform='tiktok' ORDER BY pp.followers DESC LIMIT 5
    """).fetchall()
    conn.close()
    
    print('\nSample:')
    for name, cats, country, demo in sample:
        d = json.loads(demo) if demo else {}
        print(f'  {name} ({country}, {cats}): {d.get("gender",{})} | Age: {d.get("age_primary","")} | Location: {d.get("audience_location",{})}')

if __name__ == '__main__':
    main()
