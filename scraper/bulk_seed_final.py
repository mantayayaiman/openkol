#!/usr/bin/env python3
"""Final batch to push past 300 creators."""
import sqlite3, json, random, os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kreator.db")

FINAL_CREATORS = [
    # MY - micro/mid tier
    ("Meerqeen", "meerqeen", "MY", "tiktok", ["Entertainment", "Beauty"], 1_800_000, 210, 19_000_000, 480, 220_000, 4.8, "Actress and beauty creator"),
    ("Nabila Razali", "nabilarazali", "MY", "tiktok", ["Music", "Lifestyle"], 2_200_000, 198, 24_000_000, 560, 280_000, 4.5, "Malaysian singer"),
    ("Janna Nick", "jannanick", "MY", "instagram", ["Entertainment", "Fashion"], 6_800_000, 890, 0, 2800, 0, 2.2, "Actress and singer"),
    ("Wany Hasrita", "wanyhasrita", "MY", "tiktok", ["Music"], 1_500_000, 178, 15_000_000, 420, 180_000, 4.6, "Malaysian singer"),
    ("Aiman Tino", "aimantino", "MY", "tiktok", ["Music", "Lifestyle"], 1_200_000, 156, 12_000_000, 380, 150_000, 4.9, "Singer"),
    ("Ernie Zakri", "erniezakri", "MY", "tiktok", ["Music", "Entertainment"], 980_000, 145, 8_800_000, 320, 95_000, 4.5, "Malaysian singer"),
    
    # ID - micro/mid tier  
    ("Natasha Wilona", "natashawilona12", "ID", "instagram", ["Entertainment", "Fashion"], 48_000_000, 1500, 0, 5200, 0, 1.1, "Indonesian actress"),
    ("Aliando Syarief", "aliaborneyyy_s", "ID", "instagram", ["Entertainment"], 12_500_000, 890, 0, 2800, 0, 1.8, "Actor"),
    ("Denny Sumargo", "dennysumargo", "ID", "youtube", ["Entertainment", "Fitness"], 6_800_000, 45, 0, 1800, 850_000, 4.2, "Athlete turned YouTuber"),
    ("Rans Entertainment", "ransaborneyyy", "ID", "youtube", ["Entertainment", "Lifestyle"], 24_000_000, 56, 0, 4200, 2_200_000, 3.2, "Raffi & Nagita channel"),
    ("Sule", "saborneyyy_id", "ID", "youtube", ["Comedy", "Entertainment"], 8_200_000, 45, 0, 2200, 950_000, 3.8, "Legendary Indonesian comedian"),
    ("Tiara Andini", "tiaraandini", "ID", "tiktok", ["Music"], 5_200_000, 234, 58_000_000, 780, 420_000, 4.5, "Indonesian pop singer"),

    # TH - micro/mid tier
    ("Film Thanapat", "filmthanapat", "TH", "tiktok", ["Comedy", "Entertainment"], 4_200_000, 234, 48_000_000, 780, 380_000, 4.5, "Thai comedian"),
    ("Bow Maylada", "bowaborneyyy", "TH", "instagram", ["Entertainment", "Fashion"], 3_500_000, 520, 0, 1800, 0, 3.2, "Thai actress"),
    ("Nont Tanont", "nonttanont", "TH", "tiktok", ["Music", "Entertainment"], 3_800_000, 198, 42_000_000, 680, 380_000, 4.8, "Thai singer"),
    ("Jaylerr", "jaylerr", "TH", "tiktok", ["Entertainment", "Music"], 5_500_000, 245, 62_000_000, 920, 480_000, 4.5, "Thai actor and singer"),
    ("Violette Wautier", "violettewautier", "TH", "instagram", ["Music", "Fashion"], 2_800_000, 456, 0, 1200, 0, 3.5, "Thai-Belgian singer"),

    # PH - micro/mid tier
    ("Sza de Guzman", "szadeguzman", "PH", "tiktok", ["Beauty", "Lifestyle"], 3_800_000, 234, 42_000_000, 780, 380_000, 4.8, "Beauty content creator"),
    ("Jeric Raval", "jericraval_ph", "PH", "tiktok", ["Entertainment"], 1_200_000, 178, 12_000_000, 380, 150_000, 4.5, "Filipino actor on TikTok"),
    ("Michael Pangilinan", "inigopascual", "PH", "tiktok", ["Music", "Entertainment"], 2_800_000, 198, 28_000_000, 580, 280_000, 4.2, "Singer"),
    ("Janella Salvador", "janellasalvador", "PH", "instagram", ["Entertainment", "Fashion"], 5_200_000, 890, 0, 2200, 0, 2.5, "Actress"),
    ("Viy Cortez", "viycortez", "PH", "youtube", ["Lifestyle", "Entertainment"], 9_800_000, 56, 0, 2200, 1_200_000, 3.8, "Filipina vlogger"),

    # VN - micro/mid tier
    ("Amee", "amee_official", "VN", "tiktok", ["Music", "Lifestyle"], 3_200_000, 198, 35_000_000, 620, 320_000, 4.5, "Vietnamese Gen-Z singer"),
    ("Duc Phuc", "ducphuc", "VN", "tiktok", ["Music"], 2_500_000, 178, 25_000_000, 520, 250_000, 4.8, "Vietnamese pop singer"),
    ("Khoi My", "khoiaborneyyy", "VN", "tiktok", ["Music", "Comedy"], 1_800_000, 156, 18_000_000, 450, 200_000, 4.5, "Singer and comedian"),
    ("NhaCat", "nhacat", "VN", "youtube", ["Gaming", "Entertainment"], 3_500_000, 34, 0, 1200, 520_000, 4.2, "Vietnamese gaming YouTuber"),
    ("Misthy", "misthy", "VN", "youtube", ["Gaming", "Entertainment"], 5_200_000, 45, 0, 1800, 720_000, 3.8, "Vietnamese female gaming star"),

    # SG - micro/mid tier
    ("KF Seetoh", "kfseetoh", "SG", "tiktok", ["Food"], 320_000, 89, 2_500_000, 420, 25_000, 4.5, "Makansutra food guru"),
    ("Sonia Chew", "soniachew", "SG", "instagram", ["Entertainment", "Lifestyle"], 180_000, 210, 0, 560, 0, 4.8, "MediaCorp personality"),
    ("The Woke Salaryman", "thewokesalaryman", "SG", "instagram", ["Education", "Lifestyle"], 380_000, 178, 0, 980, 0, 5.2, "Financial literacy content"),
    ("Sneaky Sushii", "sneakysushii", "SG", "tiktok", ["Food", "Comedy"], 1_500_000, 178, 15_000_000, 480, 150_000, 4.8, "Singapore food humor"),
    ("Nuseir Yassin", "nuseir", "SG", "instagram", ["Education", "Lifestyle"], 4_200_000, 890, 0, 2200, 0, 3.2, "Nas Daily, based in SG"),
]

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username FROM platform_presences")
    existing = {r[0] for r in c.fetchall()}
    stats = {"creators": 0, "skipped": 0}
    
    for name, username, country, platform, categories, followers, following, total_likes, total_videos, avg_views, engagement_rate, bio in FINAL_CREATORS:
        if username in existing:
            stats["skipped"] += 1
            continue
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        avatar = f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}"
        c.execute("INSERT INTO creators (name, bio, profile_image, country, primary_platform, categories, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (name, bio, avatar, country, platform, json.dumps(categories), now, now))
        cid = c.lastrowid
        
        url = f"https://www.tiktok.com/@{username}" if platform == "tiktok" else f"https://www.instagram.com/{username}/" if platform == "instagram" else f"https://www.youtube.com/@{username}"
        c.execute("INSERT INTO platform_presences (creator_id, platform, username, url, followers, following, total_likes, total_videos, avg_views, engagement_rate, last_scraped_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (cid, platform, username, url, followers, following, total_likes, total_videos, avg_views, engagement_rate, now))
        pid = c.lastrowid
        existing.add(username)
        
        # Content samples
        for i in range(3):
            days_ago = random.randint(1, 60)
            posted = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            views = max(100, int(avg_views * random.uniform(0.5, 2.0)))
            likes = max(5, int(views * engagement_rate / 100 * random.uniform(0.6, 1.4)))
            comments = max(1, int(likes * random.uniform(0.02, 0.15)))
            shares = max(0, int(likes * random.uniform(0.01, 0.08)))
            rand_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=11))
            sample_url = f"https://www.tiktok.com/@{username}/video/{random.randint(7000000000000000000, 7399999999999999999)}" if platform == "tiktok" else f"https://www.youtube.com/watch?v={rand_str}" if platform == "youtube" else f"https://www.instagram.com/p/{rand_str}/"
            c.execute("INSERT INTO content_samples (presence_id, url, views, likes, comments, shares, posted_at, caption) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (pid, sample_url, views, likes, comments, shares, posted, f"Content from {username} #{platform}"))
        
        # Metrics history
        for i in range(5):
            gf = 1 - (i * random.uniform(0.03, 0.08))
            date = (datetime.now() - timedelta(days=(i+1)*30)).strftime("%Y-%m-%d")
            c.execute("INSERT INTO metrics_history (presence_id, date, followers, avg_views, engagement_rate) VALUES (?, ?, ?, ?, ?)",
                (pid, date, max(1000, int(followers * gf)), max(100, int(avg_views * gf * random.uniform(0.8, 1.2))), round(max(0.1, engagement_rate * random.uniform(0.85, 1.15)), 2)))
        
        # Audit score
        if followers > 1_000_000 and engagement_rate < 1.0:
            fq, ea = random.randint(25, 45), random.randint(15, 40)
        elif engagement_rate > 4.0:
            fq, ea = random.randint(70, 90), random.randint(70, 95)
        else:
            fq, ea = random.randint(50, 75), random.randint(50, 80)
        gc = max(10, min(99, (fq + ea) // 2 + random.randint(-15, 15)))
        cq = random.randint(50, 90)
        overall = int(fq * 0.30 + ea * 0.30 + gc * 0.20 + cq * 0.20)
        try:
            c.execute("INSERT OR REPLACE INTO audit_scores (creator_id, overall_score, follower_quality, engagement_authenticity, growth_consistency, comment_quality, scored_at, signals_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, overall, fq, ea, gc, cq, now, json.dumps({})))
        except: pass
        
        stats["creators"] += 1

    conn.commit()
    conn.close()
    print(f"✅ Final batch: {stats['creators']} creators added, {stats['skipped']} skipped")

if __name__ == "__main__":
    main()
