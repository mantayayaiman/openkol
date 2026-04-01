#!/usr/bin/env python3
"""
Extra batch of real SEA creators to reach 350+ total.
Run after bulk_seed.py.
"""

import sqlite3
import json
import random
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kreator.db")

def dicebear_avatar(username): return f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}"
def tiktok_url(username): return f"https://www.tiktok.com/@{username}"
def instagram_url(username): return f"https://www.instagram.com/{username}/"
def youtube_url(handle): return f"https://www.youtube.com/@{handle}"

def compute_audit_score(followers, engagement_rate, avg_views):
    if followers > 1_000_000 and engagement_rate < 1.0:
        fq = random.randint(25, 45)
    elif engagement_rate > 5.0: fq = random.randint(75, 95)
    elif engagement_rate > 3.0: fq = random.randint(60, 85)
    else: fq = random.randint(45, 75)

    if engagement_rate > 8.0: ea = random.randint(80, 98)
    elif engagement_rate > 4.0: ea = random.randint(65, 90)
    elif engagement_rate > 2.0: ea = random.randint(50, 80)
    elif engagement_rate > 0.5: ea = random.randint(35, 65)
    else: ea = random.randint(15, 40)

    gc = max(10, min(99, (fq + ea) // 2 + random.randint(-15, 15)))
    cq = random.randint(60, 95) if followers < 500_000 else random.randint(45, 80) if followers < 2_000_000 else random.randint(30, 70)
    overall = int(fq * 0.30 + ea * 0.30 + gc * 0.20 + cq * 0.20)
    signals = {}
    if followers > 1_000_000 and engagement_rate < 1.0:
        signals["low_engagement_high_followers"] = True
        signals["possible_bought_followers"] = True
    return overall, fq, ea, gc, cq, signals

EXTRA_CREATORS = [
    # MALAYSIA extras
    ("Dato' Aliff Syukri", "aaborneyyy", "MY", "tiktok", ["Lifestyle", "Comedy", "Beauty"], 6_800_000, 420, 92_000_000, 1800, 780_000, 3.8, "Controversial entrepreneur and beauty mogul"),
    ("Luqman Podolski", "luqmanpodolski", "MY", "tiktok", ["Comedy", "Entertainment"], 3_900_000, 278, 48_000_000, 920, 420_000, 4.6, "Malaysian comedy creator"),
    ("Cody Hong", "codyhong", "MY", "tiktok", ["Comedy", "Lifestyle"], 2_500_000, 198, 28_000_000, 620, 280_000, 4.8, "Comedy and lifestyle"),
    ("Sajat", "sajat_official", "MY", "tiktok", ["Entertainment", "Lifestyle"], 4_200_000, 310, 52_000_000, 890, 480_000, 4.2, "Controversial entertainment personality"),
    ("MK K-Clique", "mkofkclique", "MY", "tiktok", ["Music", "Entertainment"], 1_800_000, 145, 19_000_000, 480, 220_000, 5.1, "Malaysian hip-hop artist"),
    ("Fattah Amin", "fattahamin", "MY", "instagram", ["Entertainment", "Lifestyle"], 5_200_000, 890, 0, 2800, 0, 2.5, "Actor and celebrity"),
    ("Siti Nurhaliza", "ctdk", "MY", "instagram", ["Music", "Lifestyle"], 8_500_000, 650, 0, 3200, 0, 1.8, "Malaysian music icon"),
    ("Hannah Delisha", "hannahdelisha", "MY", "tiktok", ["Beauty", "Entertainment"], 2_200_000, 245, 24_000_000, 560, 280_000, 4.9, "Actress and content creator"),
    ("Sean Lee", "seanleee", "MY", "tiktok", ["Comedy", "Lifestyle"], 1_500_000, 178, 15_000_000, 420, 180_000, 5.2, "Malaysian comedian"),
    ("Ismail Izzani", "ismailizzani", "MY", "tiktok", ["Music", "Lifestyle"], 2_800_000, 210, 32_000_000, 680, 350_000, 4.5, "Singer and content creator"),
    ("Wak Doyok", "wakdoyok", "MY", "instagram", ["Lifestyle", "Fashion"], 1_900_000, 520, 0, 1600, 0, 3.2, "Grooming and fashion icon"),
    ("Sugu Pavithra", "sugupavithra", "MY", "youtube", ["Food"], 980_000, 34, 0, 420, 180_000, 4.8, "Indian-Malaysian cooking channel"),
    ("Daiyan Trisha", "daiyantrisha", "MY", "tiktok", ["Beauty", "Lifestyle"], 1_300_000, 198, 12_000_000, 380, 150_000, 4.6, "Actress and beauty creator"),
    ("Azfar Heri", "azfarheri", "MY", "tiktok", ["Comedy"], 2_100_000, 210, 22_000_000, 520, 250_000, 5.0, "Comedy sketch creator"),
    ("Hunny Madu", "hunnymadu", "MY", "tiktok", ["Comedy", "Entertainment"], 4_500_000, 290, 55_000_000, 980, 520_000, 4.8, "Malaysian comedy duo"),
    ("Baby Shima", "babyshima", "MY", "tiktok", ["Music", "Entertainment"], 3_200_000, 245, 38_000_000, 720, 350_000, 4.1, "Singer and entertainer"),
    ("Mat Kilau Gamer", "matkilaugamer", "MY", "tiktok", ["Gaming"], 890_000, 156, 8_200_000, 320, 95_000, 4.5, "Malaysian gaming content"),

    # INDONESIA extras
    ("Raffi Ahmad", "rafaborneyyy", "ID", "instagram", ["Entertainment", "Lifestyle"], 72_000_000, 2200, 0, 8500, 0, 1.2, "Indonesia's biggest celebrity"),
    ("Nagita Slavina", "nagitaslavina", "ID", "instagram", ["Lifestyle", "Entertainment"], 65_000_000, 1800, 0, 7200, 0, 1.3, "Celebrity and entrepreneur"),
    ("Atta Halilintar", "attahalilintar", "ID", "youtube", ["Entertainment", "Lifestyle"], 31_000_000, 89, 0, 4200, 1_800_000, 2.5, "YouTuber entrepreneur"),
    ("Atta Halilintar", "attahalilintar", "ID", "tiktok", ["Entertainment", "Lifestyle"], 22_000_000, 345, 350_000_000, 2800, 1_500_000, 3.2, "Entertainment content"),
    ("Baim Wong", "baimwong", "ID", "youtube", ["Entertainment", "Comedy"], 20_500_000, 67, 0, 3200, 2_200_000, 3.5, "Social experiment vlogger"),
    ("Raditya Dika", "raaborneyyy", "ID", "youtube", ["Comedy", "Entertainment"], 11_200_000, 45, 0, 1800, 850_000, 3.8, "Comedian and filmmaker"),
    ("Awkarin", "awkarin", "ID", "tiktok", ["Lifestyle", "Fashion"], 6_500_000, 310, 78_000_000, 1200, 580_000, 4.2, "Influencer and music artist"),
    ("Aurelie Hermansyah", "aureaborneyyy", "ID", "instagram", ["Music", "Lifestyle"], 9_200_000, 980, 0, 3200, 0, 2.8, "Singer and celebrity"),
    ("Rachel Vennya", "rachelvennya", "ID", "instagram", ["Lifestyle", "Fashion"], 7_500_000, 890, 0, 2800, 0, 2.2, "Lifestyle influencer"),
    ("Ria SW", "riaaborneyyy", "ID", "tiktok", ["Comedy", "Lifestyle"], 5_800_000, 245, 68_000_000, 980, 520_000, 4.1, "Entertainment content"),
    ("Saaih Halilintar", "saaihalilintar", "ID", "youtube", ["Entertainment"], 8_500_000, 56, 0, 2200, 980_000, 3.5, "Halilintar family content"),
    ("Sisca Kohl", "siscakohl", "ID", "tiktok", ["Food", "Lifestyle"], 18_500_000, 345, 280_000_000, 1800, 1_500_000, 4.5, "Luxury food content"),
    ("Ayu Ting Ting", "ayutingting92", "ID", "tiktok", ["Music", "Entertainment"], 14_000_000, 290, 195_000_000, 1600, 950_000, 3.5, "Dangdut singer and entertainer"),
    ("Ziva Magnolya", "zivamagnolya", "ID", "tiktok", ["Music"], 4_200_000, 198, 48_000_000, 680, 380_000, 4.8, "Indonesian Idol singer"),
    ("Ivan Gunawan", "ivan_gunawan", "ID", "instagram", ["Fashion", "Entertainment"], 8_800_000, 1200, 0, 3500, 0, 2.1, "Fashion designer and TV personality"),
    ("Prilly Latuconsina", "prillylatuconsina", "ID", "instagram", ["Entertainment", "Beauty"], 7_200_000, 890, 0, 2800, 0, 2.5, "Actress and beauty influencer"),
    ("Chef Arnold", "chefaborneyyy", "ID", "instagram", ["Food"], 5_200_000, 780, 0, 2200, 0, 3.2, "Celebrity chef"),
    ("Hansol TikTok", "hansoltiktok", "ID", "tiktok", ["Comedy", "Entertainment"], 8_200_000, 234, 95_000_000, 1200, 650_000, 4.5, "Korean-Indonesian comedy creator"),
    ("Fiersa Besari", "fiersabesari", "ID", "instagram", ["Music", "Lifestyle"], 3_500_000, 567, 0, 1800, 0, 3.8, "Musician and writer"),

    # THAILAND extras
    ("Lisa Blackpink TH", "lalalalisa_m", "TH", "instagram", ["Music", "Fashion", "Beauty"], 102_000_000, 450, 0, 5200, 0, 1.5, "Thai member of BLACKPINK"),
    ("Bambam GOT7", "bambam1a", "TH", "instagram", ["Music", "Entertainment"], 21_000_000, 780, 0, 3200, 0, 3.2, "Thai K-pop star"),
    ("Ice Paris", "ice.paris", "TH", "tiktok", ["Entertainment", "Comedy"], 7_200_000, 310, 88_000_000, 1400, 720_000, 4.5, "Thai actor and TikToker"),
    ("Milli", "maborneyyy_th", "TH", "tiktok", ["Music", "Entertainment"], 3_800_000, 198, 42_000_000, 680, 380_000, 5.1, "Thai rapper, Coachella performer"),
    ("Engfa Waraha", "engfa_waraha", "TH", "tiktok", ["Entertainment", "Fashion"], 5_200_000, 245, 62_000_000, 980, 520_000, 4.8, "Miss Grand International"),
    ("Engfa Waraha", "engfa_waraha", "TH", "instagram", ["Entertainment", "Fashion"], 8_500_000, 650, 0, 2800, 0, 3.5, "Beauty queen and entertainer"),
    ("Ohm Pawat", "ohaborneyyy", "TH", "instagram", ["Entertainment"], 6_200_000, 520, 0, 2200, 0, 3.8, "Thai BL actor"),
    ("Pimrypie", "pimrypie", "TH", "youtube", ["Comedy", "Entertainment"], 12_800_000, 56, 0, 2800, 1_500_000, 3.8, "Thailand's comedy queen"),
    ("Pimrypie", "pimrypie", "TH", "tiktok", ["Comedy", "Entertainment"], 8_500_000, 290, 98_000_000, 1400, 850_000, 4.2, "Comedy and challenge content"),
    ("Stamp Apiwat", "stampaborneyyy", "TH", "instagram", ["Music", "Lifestyle"], 2_200_000, 456, 0, 1200, 0, 3.5, "Thai musician"),
    ("Atom Chanakan", "atomchanakan", "TH", "tiktok", ["Comedy", "Entertainment"], 3_500_000, 210, 38_000_000, 720, 350_000, 4.6, "Comedy creator"),
    ("Earth Pirapat", "earth_pirapat", "TH", "instagram", ["Entertainment", "Lifestyle"], 4_800_000, 560, 0, 1800, 0, 3.2, "Thai actor"),
    ("Minnie (G)I-DLE", "minnie_th", "TH", "instagram", ["Music", "Fashion"], 15_200_000, 450, 0, 3200, 0, 3.0, "Thai K-pop idol"),
    ("UrboyTJ", "urboytj", "TH", "tiktok", ["Music", "Entertainment"], 2_800_000, 198, 28_000_000, 580, 280_000, 4.5, "Thai rapper and producer"),
    ("Mook Worranit", "maborneyyy_wrn", "TH", "tiktok", ["Entertainment", "Fashion"], 1_800_000, 178, 18_000_000, 450, 200_000, 4.8, "Actress and fashion"),

    # PHILIPPINES extras
    ("Vice Ganda", "viceganda", "PH", "tiktok", ["Comedy", "Entertainment"], 12_500_000, 345, 180_000_000, 1800, 1_200_000, 4.5, "Philippines comedy king"),
    ("Vice Ganda", "viceganda", "PH", "instagram", ["Comedy", "Entertainment"], 14_800_000, 890, 0, 3500, 0, 2.8, "TV host and comedian"),
    ("Kathryn Bernardo", "kathrynbernardo", "PH", "instagram", ["Entertainment", "Fashion"], 18_500_000, 1200, 0, 4200, 0, 2.2, "Top Filipina actress"),
    ("Daniel Padilla", "daborneyyy_jp", "PH", "instagram", ["Entertainment", "Lifestyle"], 9_800_000, 780, 0, 2800, 0, 2.5, "Filipino actor"),
    ("Kim Chiu", "chiukim", "PH", "tiktok", ["Entertainment", "Dance"], 8_200_000, 290, 95_000_000, 1400, 720_000, 4.2, "Actress and dancer"),
    ("Liza Soberano", "lizaborneyyy", "PH", "instagram", ["Entertainment", "Fashion", "Beauty"], 22_000_000, 1100, 0, 4500, 0, 2.0, "Filipina actress"),
    ("Maine Mendoza", "mainedcm", "PH", "tiktok", ["Comedy", "Lifestyle"], 5_800_000, 245, 68_000_000, 1100, 580_000, 4.8, "Comedian and actress, Yaya Dub"),
    ("Lele Pons PH", "lelepons_ph", "PH", "tiktok", ["Comedy"], 2_200_000, 178, 22_000_000, 520, 250_000, 4.5, "Comedy content"),
    ("Zeinab Harake", "zeinabharake", "PH", "youtube", ["Lifestyle", "Entertainment"], 12_200_000, 56, 0, 2200, 1_200_000, 3.5, "Filipina vlogger"),
    ("Andrea Brillantes", "blythe", "PH", "tiktok", ["Entertainment", "Beauty"], 18_000_000, 345, 280_000_000, 2200, 1_500_000, 4.1, "Young actress and creator"),
    ("Donnalyn Bartolome", "donnalynbartolome", "PH", "youtube", ["Music", "Entertainment"], 8_500_000, 45, 0, 1800, 950_000, 3.8, "Singer and YouTuber"),
    ("Lloyd Cadena Legacy", "lloydcadena", "PH", "youtube", ["Comedy"], 5_800_000, 34, 0, 1200, 320_000, 3.2, "Legacy comedy channel"),
    ("Alodia Gosiengfiao", "alodia", "PH", "instagram", ["Gaming", "Cosplay", "Entertainment"], 6_500_000, 890, 0, 2200, 0, 2.5, "Cosplay and gaming personality"),
    ("Ham Vlog", "hamvlog", "PH", "tiktok", ["Food", "Comedy"], 3_200_000, 210, 35_000_000, 680, 320_000, 4.8, "Food content creator"),
    ("Kimpoy Feliciano", "kimpoyfeliciano", "PH", "tiktok", ["Comedy", "Lifestyle"], 4_500_000, 267, 52_000_000, 890, 420_000, 4.5, "Filipino comedy creator"),
    ("Jessica Soho", "jessicasoho", "PH", "youtube", ["Lifestyle", "Entertainment"], 5_200_000, 23, 0, 2800, 650_000, 4.2, "Veteran journalist and vlogger"),

    # VIETNAM extras
    ("Jack (J97)", "jack97", "VN", "tiktok", ["Music", "Entertainment"], 8_200_000, 198, 95_000_000, 980, 720_000, 4.5, "Vietnamese pop singer"),
    ("Jack (J97)", "jack97", "VN", "youtube", ["Music"], 5_800_000, 34, 0, 280, 5_200_000, 3.8, "Music videos"),
    ("Thuy Tien", "thuytiencf", "VN", "tiktok", ["Music", "Lifestyle"], 6_500_000, 245, 78_000_000, 1100, 580_000, 4.2, "Singer and charity activist"),
    ("Duc Anh", "ducanh_comedy", "VN", "tiktok", ["Comedy"], 3_800_000, 210, 42_000_000, 780, 380_000, 4.8, "Vietnamese comedian"),
    ("Hau Hoang", "hauhoang", "VN", "youtube", ["Comedy", "Entertainment"], 6_200_000, 45, 0, 1800, 950_000, 4.5, "Vietnamese comedy YouTuber"),
    ("Chi Pu", "chipu_official", "VN", "tiktok", ["Music", "Fashion", "Beauty"], 4_500_000, 234, 48_000_000, 780, 420_000, 4.2, "Vietnamese singer and actress"),
    ("Chi Pu", "chipu_official", "VN", "instagram", ["Music", "Fashion"], 5_200_000, 890, 0, 2200, 0, 2.8, "Actress and singer"),
    ("Min (Singer)", "min.official", "VN", "tiktok", ["Music"], 2_800_000, 178, 28_000_000, 520, 280_000, 4.8, "Vietnamese pop artist"),
    ("Huynh Phuong", "huynhphuong", "VN", "tiktok", ["Comedy", "Entertainment"], 5_200_000, 267, 62_000_000, 980, 520_000, 4.5, "Vietnamese comedian"),
    ("Bui Xuan Huong", "xuanhuong_fitness", "VN", "tiktok", ["Fitness", "Lifestyle"], 1_200_000, 156, 12_000_000, 420, 150_000, 5.2, "Vietnamese fitness influencer"),
    ("Linh Ngoc Dam", "lingocdam", "VN", "tiktok", ["Lifestyle", "Beauty"], 3_500_000, 210, 38_000_000, 680, 350_000, 4.6, "Streamer and beauty creator"),
    ("Lam Vlog", "lamvlog", "VN", "youtube", ["Entertainment", "Comedy"], 4_800_000, 45, 0, 1400, 720_000, 4.2, "Vietnamese vlogger"),
    ("Duy Thahh", "duythanh_vn", "VN", "tiktok", ["Comedy"], 2_200_000, 178, 22_000_000, 520, 250_000, 5.0, "Comedy skits"),
    ("KhaSu", "khasu_review", "VN", "tiktok", ["Food", "Lifestyle"], 1_800_000, 145, 18_000_000, 450, 200_000, 4.8, "Food reviews"),
    ("Cris Devil Gamer", "crisdevilgamer", "VN", "youtube", ["Gaming"], 9_500_000, 34, 0, 3200, 1_200_000, 3.8, "Top Vietnamese gaming channel"),

    # SINGAPORE extras
    ("Tabitha Nauser", "tabithanauser", "SG", "tiktok", ["Music", "Lifestyle"], 580_000, 145, 4_800_000, 420, 55_000, 4.5, "Singaporean singer"),
    ("Benjamin Kheng", "benjaminkheng", "SG", "instagram", ["Music", "Comedy", "Lifestyle"], 280_000, 310, 0, 890, 0, 4.8, "Musician and content creator"),
    ("Tosh Zhang", "toshaborneyyy", "SG", "instagram", ["Comedy", "Lifestyle"], 220_000, 267, 0, 780, 0, 4.5, "Actor and comedian"),
    ("Sheena Liam", "sheenaliam", "SG", "instagram", ["Fashion", "Art"], 350_000, 310, 0, 980, 0, 4.2, "Model and artist"),
    ("Hirzi Zulkiflie", "hirzi", "SG", "tiktok", ["Comedy"], 1_800_000, 198, 18_000_000, 520, 180_000, 4.8, "Singapore comedy creator"),
    ("Nicole Changmin", "nicolechangmin", "SG", "tiktok", ["Lifestyle", "Fashion"], 890_000, 178, 8_200_000, 380, 85_000, 4.5, "Fashion and lifestyle"),
    ("NOC Aiken", "aikenbaborneyyy", "SG", "tiktok", ["Comedy", "Entertainment"], 1_200_000, 198, 12_000_000, 420, 120_000, 4.2, "Comedy content"),
    ("Sylvia Chan", "sylvia.chan", "SG", "instagram", ["Lifestyle", "Food"], 280_000, 245, 0, 780, 0, 4.5, "Food and lifestyle"),
    ("Tosh Rock", "toshrock_sg", "SG", "tiktok", ["Comedy"], 450_000, 120, 3_500_000, 280, 35_000, 4.8, "Sketch comedy"),
    ("Munah & Hirzi", "munahhirzi", "SG", "youtube", ["Comedy"], 320_000, 23, 0, 680, 55_000, 4.5, "Singaporean comedy duo"),
    ("MrBrown", "mrbrown", "SG", "tiktok", ["Comedy", "Lifestyle"], 450_000, 120, 3_800_000, 890, 35_000, 3.8, "OG Singapore internet personality"),
    ("Preetipls", "preetipls", "SG", "tiktok", ["Comedy", "Lifestyle"], 280_000, 145, 2_500_000, 320, 25_000, 4.5, "Singaporean comedian and rapper"),
    ("Yan Kay Kay", "yankaykay", "SG", "instagram", ["Fashion", "Beauty"], 180_000, 210, 0, 560, 0, 4.8, "Fashion influencer"),
    ("Drea Chong", "dreachong_", "SG", "tiktok", ["Fashion", "Lifestyle"], 650_000, 178, 5_800_000, 380, 55_000, 4.2, "Fashion content creator"),
    ("Aarika Lee", "aarikalee", "SG", "tiktok", ["Beauty", "Lifestyle"], 520_000, 156, 4_500_000, 320, 45_000, 4.5, "Beauty reviews"),
    ("Jade Rasif", "jaderasif", "SG", "instagram", ["Lifestyle", "Fitness"], 520_000, 345, 0, 1100, 0, 3.5, "DJ and fitness influencer"),
]


def generate_content_samples(presence_id, platform, username, avg_views, engagement_rate, n=3):
    samples = []
    now = datetime.now()
    for i in range(n):
        days_ago = random.randint(1, 60)
        posted = now - timedelta(days=days_ago)
        views = max(100, int(avg_views * random.uniform(0.5, 2.0)))
        likes = max(5, int(views * engagement_rate / 100 * random.uniform(0.6, 1.4)))
        comments = max(1, int(likes * random.uniform(0.02, 0.15)))
        shares = max(0, int(likes * random.uniform(0.01, 0.08)))
        vid_id = random.randint(7000000000000000000, 7399999999999999999)
        rand_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=11))
        url = f"https://www.tiktok.com/@{username}/video/{vid_id}" if platform == "tiktok" else f"https://www.youtube.com/watch?v={rand_str}" if platform == "youtube" else f"https://www.instagram.com/p/{rand_str}/"
        captions = ["New content 🔥", f"#{username} #fyp", "Who can relate? 🤣", "POV: 😂", "Check this! ✨", "Day in my life 📚", "This blew up 💥", "Tutorial time 🎯"]
        samples.append((presence_id, url, views, likes, comments, shares, posted.strftime("%Y-%m-%d"), random.choice(captions)))
    return samples

def generate_metrics_history(presence_id, followers, avg_views, engagement_rate, n=5):
    history = []
    now = datetime.now()
    for i in range(n):
        days_ago = (i + 1) * 30
        date = now - timedelta(days=days_ago)
        gf = 1 - (i * random.uniform(0.03, 0.08))
        history.append((presence_id, date.strftime("%Y-%m-%d"), max(1000, int(followers * gf)), max(100, int(avg_views * gf * random.uniform(0.8, 1.2))), round(max(0.1, engagement_rate * random.uniform(0.85, 1.15)), 2)))
    return history

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username FROM platform_presences")
    existing = {r[0] for r in c.fetchall()}
    inserted_creators = {}
    stats = {"creators": 0, "presences": 0, "samples": 0, "history": 0, "scores": 0, "skipped": 0}

    for name, username, country, platform, categories, followers, following, total_likes, total_videos, avg_views, engagement_rate, bio in EXTRA_CREATORS:
        if username in existing:
            stats["skipped"] += 1
            continue
        
        creator_key = f"{name}_{country}"
        if creator_key in inserted_creators:
            creator_id = inserted_creators[creator_key]
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO creators (name, bio, profile_image, country, primary_platform, categories, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (name, bio, dicebear_avatar(username), country, platform, json.dumps(categories), now, now))
            creator_id = c.lastrowid
            inserted_creators[creator_key] = creator_id
            stats["creators"] += 1

        url = tiktok_url(username) if platform == "tiktok" else instagram_url(username) if platform == "instagram" else youtube_url(username)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO platform_presences (creator_id, platform, username, url, followers, following, total_likes, total_videos, avg_views, engagement_rate, last_scraped_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (creator_id, platform, username, url, followers, following, total_likes, total_videos, avg_views, engagement_rate, now))
        pid = c.lastrowid
        stats["presences"] += 1
        existing.add(username)

        for s in generate_content_samples(pid, platform, username, avg_views, engagement_rate):
            c.execute("INSERT INTO content_samples (presence_id, url, views, likes, comments, shares, posted_at, caption) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", s)
            stats["samples"] += 1

        for h in generate_metrics_history(pid, followers, avg_views, engagement_rate):
            c.execute("INSERT INTO metrics_history (presence_id, date, followers, avg_views, engagement_rate) VALUES (?, ?, ?, ?, ?)", h)
            stats["history"] += 1

        overall, fq, ea, gc, cq, signals = compute_audit_score(followers, engagement_rate, avg_views)
        try:
            c.execute("INSERT OR REPLACE INTO audit_scores (creator_id, overall_score, follower_quality, engagement_authenticity, growth_consistency, comment_quality, scored_at, signals_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (creator_id, overall, fq, ea, gc, cq, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), json.dumps(signals)))
            stats["scores"] += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    print("✅ Extra batch complete!")
    for k, v in stats.items():
        print(f"   {k}: {v}")

if __name__ == "__main__":
    main()
