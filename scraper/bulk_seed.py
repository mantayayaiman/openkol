#!/usr/bin/env python3
"""
Bulk seed script for OpenKOL/Kreator database.
Populates the database with real SEA creators across TikTok, Instagram, YouTube.
Uses hardcoded data based on real, well-known creators with realistic metrics.
"""

import sqlite3
import json
import random
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kreator.db")

def dicebear_avatar(username: str) -> str:
    return f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}"

def tiktok_url(username: str) -> str:
    return f"https://www.tiktok.com/@{username}"

def instagram_url(username: str) -> str:
    return f"https://www.instagram.com/{username}/"

def youtube_url(handle: str) -> str:
    return f"https://www.youtube.com/@{handle}"

def compute_audit_score(followers, engagement_rate, avg_views, followers_following_ratio=None):
    """Generate realistic audit scores based on metrics."""
    # Follower quality: penalize if engagement is very low relative to followers (bought followers signal)
    if followers > 1_000_000 and engagement_rate < 1.0:
        follower_quality = random.randint(25, 45)
    elif followers > 500_000 and engagement_rate < 1.5:
        follower_quality = random.randint(35, 55)
    elif engagement_rate > 5.0:
        follower_quality = random.randint(75, 95)
    elif engagement_rate > 3.0:
        follower_quality = random.randint(60, 85)
    else:
        follower_quality = random.randint(45, 75)

    # Engagement authenticity
    if engagement_rate > 8.0:
        engagement_authenticity = random.randint(80, 98)
    elif engagement_rate > 4.0:
        engagement_authenticity = random.randint(65, 90)
    elif engagement_rate > 2.0:
        engagement_authenticity = random.randint(50, 80)
    elif engagement_rate > 0.5:
        engagement_authenticity = random.randint(35, 65)
    else:
        engagement_authenticity = random.randint(15, 40)

    # Growth consistency (randomized but correlated with overall health)
    base_growth = (follower_quality + engagement_authenticity) // 2
    growth_consistency = max(10, min(99, base_growth + random.randint(-15, 15)))

    # Comment quality (higher for smaller, niche creators)
    if followers < 500_000:
        comment_quality = random.randint(60, 95)
    elif followers < 2_000_000:
        comment_quality = random.randint(45, 80)
    else:
        comment_quality = random.randint(30, 70)

    overall = int(
        follower_quality * 0.30 +
        engagement_authenticity * 0.30 +
        growth_consistency * 0.20 +
        comment_quality * 0.20
    )

    signals = {}
    if followers > 1_000_000 and engagement_rate < 1.0:
        signals["low_engagement_high_followers"] = True
        signals["possible_bought_followers"] = True
    if engagement_rate > 10.0:
        signals["unusually_high_engagement"] = True
    if avg_views > 0 and followers > 0 and (avg_views / followers) < 0.01:
        signals["very_low_view_ratio"] = True

    return {
        "overall": overall,
        "follower_quality": follower_quality,
        "engagement_authenticity": engagement_authenticity,
        "growth_consistency": growth_consistency,
        "comment_quality": comment_quality,
        "signals": signals,
    }

# ============================================================================
# CREATOR DATA - Real SEA creators with realistic metrics
# ============================================================================
# Format: (name, username, country, platform, categories, followers, following,
#           total_likes, total_videos, avg_views, engagement_rate, bio)
# ============================================================================

CREATORS = [
    # ========================================================================
    # MALAYSIA (MY) - 60+ creators
    # ========================================================================
    # Gaming
    ("Soloz", "solikiinn", "MY", "tiktok", ["Gaming", "Entertainment"], 5_200_000, 312, 89_000_000, 1420, 850_000, 4.8, "MPL MY pro player, Honor of Kings talent"),
    ("KingshahX", "kingshahx", "MY", "tiktok", ["Gaming", "Comedy"], 3_800_000, 245, 62_000_000, 980, 620_000, 5.1, "Gaming content creator, Team Vamos"),
    ("Yonnyboii", "yonnyboii", "MY", "tiktok", ["Gaming", "Music"], 2_100_000, 180, 31_000_000, 650, 380_000, 4.2, "Gamer and musician"),
    ("SultanRiq", "sultanriq", "MY", "tiktok", ["Gaming", "Comedy"], 1_500_000, 156, 18_000_000, 520, 250_000, 3.8, "Gaming entertainer"),
    ("Fredo", "fredoyt", "MY", "youtube", ["Gaming"], 2_800_000, 45, 0, 890, 450_000, 3.5, "Malaysian gaming YouTuber"),
    ("EjenAli Fan", "ejenali_fan", "MY", "tiktok", ["Gaming", "Entertainment"], 890_000, 210, 8_500_000, 340, 120_000, 4.1, "Gaming and anime content"),

    # Food
    ("Khairul Aming", "khairulaming", "MY", "tiktok", ["Food", "Lifestyle"], 11_500_000, 420, 195_000_000, 2100, 1_800_000, 6.2, "Malaysia's top food creator, Sambal Nyet founder"),
    ("Khairul Aming", "khaborneyyy", "MY", "instagram", ["Food", "Lifestyle"], 6_200_000, 890, 0, 3200, 0, 4.8, "Food creator and entrepreneur"),
    ("CikManggis", "cikmanggis", "MY", "tiktok", ["Food", "Comedy"], 4_100_000, 290, 55_000_000, 1100, 580_000, 5.5, "Food reviewer with comedic style"),
    ("Alif Cepmek", "alifcepmek", "MY", "tiktok", ["Food", "Comedy"], 3_500_000, 310, 48_000_000, 890, 420_000, 4.9, "Street food explorer"),
    ("Syahmi Sazli", "syahmisazli", "MY", "tiktok", ["Food", "Lifestyle"], 2_800_000, 198, 32_000_000, 720, 350_000, 4.3, "Food and lifestyle content"),
    ("Aisha Liyana", "aishaliyanaaa", "MY", "tiktok", ["Food", "Lifestyle"], 1_900_000, 245, 22_000_000, 580, 280_000, 5.1, "Home cooking and recipes"),
    ("Ceddy", "ceddyornot", "MY", "youtube", ["Food"], 1_200_000, 89, 0, 420, 380_000, 5.8, "Malaysian food reviewer YouTuber"),
    ("DennyChef", "dennychef", "MY", "tiktok", ["Food"], 950_000, 178, 9_800_000, 290, 150_000, 3.9, "Professional chef content"),

    # Beauty & Fashion
    ("Neelofa", "naborneyyy", "MY", "instagram", ["Beauty", "Fashion", "Lifestyle"], 8_900_000, 1200, 0, 4500, 0, 2.1, "Actress, entrepreneur, Naelofar Hijab founder"),
    ("Vivy Yusof", "vivyyusof", "MY", "instagram", ["Fashion", "Lifestyle", "Beauty"], 3_200_000, 980, 0, 2800, 0, 2.8, "FashionValet & dUCk founder"),
    ("Mira Filzah", "maborneyyy", "MY", "instagram", ["Beauty", "Lifestyle"], 7_500_000, 650, 0, 3100, 0, 1.9, "Actress and beauty influencer"),
    ("Ameenizzul", "ameenizzul", "MY", "tiktok", ["Beauty", "Comedy"], 2_900_000, 320, 38_000_000, 780, 420_000, 5.6, "Beauty tips with humor"),
    ("SabrinaAnais", "sabrinaanais", "MY", "tiktok", ["Beauty", "Fashion"], 1_600_000, 290, 19_000_000, 520, 250_000, 4.7, "Beauty and skincare reviews"),
    ("Hanis Zalikha", "haniszalikha", "MY", "instagram", ["Lifestyle", "Beauty"], 2_100_000, 780, 0, 1900, 0, 2.4, "OG Malaysian blogger"),

    # Comedy & Entertainment
    ("Asyraf Khalid", "asyrafkhalid_", "MY", "tiktok", ["Comedy", "Entertainment"], 3_200_000, 198, 42_000_000, 890, 520_000, 5.8, "Malaysian comedian"),
    ("Bell Ngasri", "bellngasri", "MY", "tiktok", ["Comedy", "Entertainment"], 2_600_000, 245, 35_000_000, 780, 380_000, 4.9, "Actor and comedian"),
    ("Khai Bahar", "khaibahar", "MY", "tiktok", ["Music", "Entertainment"], 4_800_000, 310, 68_000_000, 1200, 650_000, 4.5, "Singer and entertainer"),
    ("SyedHaiqal", "syedhaiqal_", "MY", "tiktok", ["Comedy"], 1_800_000, 178, 21_000_000, 560, 280_000, 5.2, "Sketch comedy creator"),

    # Lifestyle & Tech
    ("SoyaCincau", "soyacincau", "MY", "tiktok", ["Tech", "Lifestyle"], 580_000, 120, 4_200_000, 890, 45_000, 3.1, "Tech news and reviews"),
    ("Amanz", "amaborneyyy", "MY", "youtube", ["Tech"], 890_000, 56, 0, 1200, 120_000, 4.2, "Tech reviews in Bahasa Malaysia"),
    ("DanialRon", "danialron", "MY", "tiktok", ["Lifestyle", "Comedy"], 2_400_000, 267, 28_000_000, 650, 320_000, 4.6, "Lifestyle and comedy"),
    ("Iman Troye", "imantroye", "MY", "tiktok", ["Fitness", "Lifestyle"], 1_100_000, 198, 12_000_000, 420, 180_000, 5.3, "Fitness and motivation"),
    ("SharifahRose", "sharifahrose", "MY", "instagram", ["Lifestyle", "Fashion"], 1_500_000, 520, 0, 1600, 0, 2.6, "Lifestyle and fashion content"),

    # Suspicious/Low quality (for testing audit scores)
    ("BuyFollowersMY", "buyfollowersmy", "MY", "tiktok", ["Lifestyle"], 2_500_000, 12, 3_200_000, 45, 8_000, 0.3, "Suspicious account with bought followers"),
    ("ViralHacksMY", "viralhacksmy", "MY", "instagram", ["Lifestyle", "Tech"], 1_800_000, 3200, 0, 120, 0, 0.5, "Growth hacking account"),

    # ========================================================================
    # INDONESIA (ID) - 70+ creators
    # ========================================================================
    # Entertainment & Comedy
    ("Ria Ricis", "riaricis1795", "ID", "tiktok", ["Comedy", "Lifestyle", "Entertainment"], 32_000_000, 890, 520_000_000, 3200, 2_500_000, 3.8, "Indonesia's TikTok queen"),
    ("Ria Ricis", "riaricis1795", "ID", "youtube", ["Comedy", "Lifestyle"], 34_000_000, 120, 0, 4500, 1_800_000, 2.9, "Top Indonesian YouTuber"),
    ("Fadil Jaidi", "fadiljaidi", "ID", "tiktok", ["Comedy", "Entertainment"], 18_500_000, 456, 310_000_000, 2100, 1_200_000, 4.5, "King of Indonesian comedy skits"),
    ("Fadil Jaidi", "fadiljaidi", "ID", "instagram", ["Comedy", "Entertainment"], 9_800_000, 890, 0, 2800, 0, 3.2, "Comedy creator"),
    ("Bintang Emon", "baborneyyy", "ID", "tiktok", ["Comedy"], 12_000_000, 345, 180_000_000, 1800, 850_000, 4.1, "Stand-up comedian turned TikToker"),
    ("Arief Muhammad", "ariefmuhammad", "ID", "instagram", ["Lifestyle", "Comedy", "Entertainment"], 6_500_000, 1200, 0, 3500, 0, 3.5, "Content creator and entrepreneur"),
    ("Keanu Agl", "keanuagl", "ID", "tiktok", ["Comedy", "Entertainment"], 15_200_000, 310, 245_000_000, 1950, 1_100_000, 4.8, "Comedy and lifestyle"),
    ("Ria SW", "riasukmawijaya", "ID", "youtube", ["Comedy", "Lifestyle"], 12_500_000, 78, 0, 2200, 980_000, 3.6, "Vlogger and entertainer"),

    # Food
    ("Tanboy Kun", "tanaborneyyy", "ID", "youtube", ["Food", "Entertainment"], 25_000_000, 65, 0, 1800, 3_500_000, 4.2, "Mukbang and extreme food challenges"),
    ("Tanboy Kun", "tanboykun", "ID", "tiktok", ["Food", "Entertainment"], 18_000_000, 290, 280_000_000, 1500, 1_800_000, 3.9, "Food challenge content"),
    ("Tasyi Athasyia", "tasyiiathasyia", "ID", "tiktok", ["Food", "Lifestyle"], 8_200_000, 456, 95_000_000, 1400, 650_000, 4.3, "Food content creator"),
    ("Tasyi Athasyia", "tasyiiathasyia", "ID", "instagram", ["Food", "Lifestyle"], 4_500_000, 890, 0, 2100, 0, 3.1, "Food and lifestyle"),
    ("Magdalena", "magdalenaaf", "ID", "tiktok", ["Food", "Comedy"], 6_800_000, 234, 78_000_000, 980, 520_000, 4.6, "Indonesian food reviewer"),
    ("Nex Carlos", "nexcarlos", "ID", "youtube", ["Food"], 9_200_000, 45, 0, 1600, 1_200_000, 4.8, "Street food explorer across Indonesia"),
    ("Ade Koerniawan", "adekoerniawan", "ID", "tiktok", ["Food", "Comedy"], 4_500_000, 310, 52_000_000, 780, 380_000, 4.1, "Food with comedy twist"),

    # Education & Tech
    ("Jerome Polin", "jeromepolin", "ID", "youtube", ["Education", "Entertainment"], 16_500_000, 89, 0, 2800, 2_200_000, 5.1, "Math education from Japan, Nihongo Mantappu"),
    ("Jerome Polin", "jeromepolin", "ID", "tiktok", ["Education", "Entertainment"], 8_900_000, 234, 120_000_000, 1200, 850_000, 5.3, "Educational content creator"),
    ("Gita Savitri", "gitaborneyyy", "ID", "youtube", ["Education", "Lifestyle"], 1_200_000, 56, 0, 680, 250_000, 5.8, "Education and social commentary"),
    ("David Gadgetin", "davidgadgetin", "ID", "youtube", ["Tech"], 11_500_000, 34, 0, 3200, 1_500_000, 4.5, "Indonesia's top tech reviewer"),
    ("Deddy Corbuzier", "deddycorbuzier", "ID", "youtube", ["Entertainment", "Lifestyle"], 22_000_000, 45, 0, 3800, 2_800_000, 3.2, "Podcast and entertainment king"),
    ("Deddy Corbuzier", "mastercorbuzier", "ID", "tiktok", ["Entertainment", "Lifestyle"], 14_000_000, 189, 195_000_000, 1600, 1_200_000, 3.5, "Close Up podcast host"),

    # Beauty & Fashion
    ("Rachel Goddard", "rachelgoddard", "ID", "tiktok", ["Beauty", "Fashion"], 5_200_000, 310, 62_000_000, 890, 480_000, 5.2, "Beauty content creator"),
    ("Tasya Farasya", "tasyafarasya", "ID", "instagram", ["Beauty", "Fashion"], 5_800_000, 1100, 0, 2800, 0, 3.8, "Beauty guru and makeup artist"),
    ("Tasya Farasya", "tasyafarasya", "ID", "youtube", ["Beauty"], 4_200_000, 67, 0, 1200, 650_000, 4.1, "Beauty tutorials"),
    ("Abel Cantika", "abellyc", "ID", "tiktok", ["Beauty", "Lifestyle"], 3_800_000, 278, 42_000_000, 720, 350_000, 4.5, "Skincare and beauty"),
    ("Suhay Salim", "suhaysalim", "ID", "instagram", ["Beauty"], 2_900_000, 780, 0, 1800, 0, 3.2, "Makeup artist and beauty creator"),
    ("Molita Lin", "maborneyyy", "ID", "youtube", ["Beauty", "Fashion"], 1_800_000, 56, 0, 680, 320_000, 4.8, "Beauty and fashion vlogger"),

    # Gaming
    ("Jess No Limit", "jessnolimit", "ID", "youtube", ["Gaming"], 44_000_000, 34, 0, 5200, 3_200_000, 3.1, "Mobile Legends pro, top gaming channel"),
    ("Jess No Limit", "jessnolimit", "ID", "tiktok", ["Gaming", "Entertainment"], 12_000_000, 198, 165_000_000, 1400, 950_000, 3.5, "Gaming content"),
    ("Windah Basudara", "windahbasudara", "ID", "youtube", ["Gaming", "Entertainment"], 18_000_000, 56, 0, 3200, 2_800_000, 5.2, "GTA RP and gaming streamer"),
    ("Windah Basudara", "windahbasudara", "ID", "tiktok", ["Gaming", "Entertainment"], 8_500_000, 234, 98_000_000, 1100, 720_000, 4.8, "Gaming clips"),
    ("EVOS Legends", "evoslegends", "ID", "tiktok", ["Gaming"], 3_200_000, 178, 35_000_000, 620, 280_000, 3.9, "Esports team content"),
    ("Miawaug", "miaborneyyy", "ID", "youtube", ["Gaming"], 12_800_000, 45, 0, 4200, 1_500_000, 3.4, "Let's Play gaming channel"),

    # Fitness
    ("Oura Ring ID", "ouraid", "ID", "tiktok", ["Fitness", "Tech"], 450_000, 120, 3_200_000, 280, 35_000, 3.5, "Fitness tech reviews"),
    ("Dyland Pros", "dylandpros", "ID", "youtube", ["Gaming", "Fitness"], 2_800_000, 45, 0, 890, 450_000, 4.2, "Gaming and fitness content"),

    # Suspicious
    ("FakeInfluencerID", "fakeinfluencerid", "ID", "tiktok", ["Lifestyle"], 5_000_000, 8, 5_200_000, 30, 12_000, 0.2, "Suspicious bot-like account"),
    ("BotFarmJakarta", "botfarmjkt", "ID", "instagram", ["Fashion"], 3_200_000, 4500, 0, 80, 0, 0.4, "Suspected bot farm account"),

    # ========================================================================
    # THAILAND (TH) - 50+ creators
    # ========================================================================
    # Entertainment
    ("PP Krit", "ppkritt", "TH", "tiktok", ["Entertainment", "Lifestyle"], 8_500_000, 345, 125_000_000, 1800, 920_000, 5.1, "Thai actor and BL star"),
    ("PP Krit", "ppkritt", "TH", "instagram", ["Entertainment", "Lifestyle"], 11_200_000, 890, 0, 2800, 0, 3.8, "Actor, PPKRITT"),
    ("Bright Vachirawit", "baborneyyy", "TH", "instagram", ["Entertainment", "Fashion"], 14_500_000, 650, 0, 3200, 0, 3.2, "Thai actor, 2gether series"),
    ("Win Metawin", "winmetawin", "TH", "instagram", ["Entertainment", "Fashion"], 11_800_000, 780, 0, 2900, 0, 3.5, "Thai actor and model"),
    ("Gulf Kanawut", "gaborneyyy", "TH", "instagram", ["Entertainment"], 9_200_000, 560, 0, 2400, 0, 3.9, "Thai BL actor"),
    ("Blackink", "blackink_th", "TH", "tiktok", ["Entertainment", "Comedy"], 5_800_000, 290, 78_000_000, 1200, 580_000, 4.8, "Thai entertainment creator"),
    ("Kaykai Salaider", "kaykai", "TH", "youtube", ["Entertainment", "Comedy"], 9_800_000, 56, 0, 2100, 1_200_000, 4.1, "Top Thai YouTuber"),

    # Beauty
    ("Pearypie", "pearypie", "TH", "youtube", ["Beauty"], 2_100_000, 45, 0, 890, 450_000, 5.2, "Thai makeup artist, international acclaim"),
    ("Pearypie", "pearypie", "TH", "instagram", ["Beauty", "Fashion"], 1_800_000, 520, 0, 1200, 0, 4.1, "Celebrity makeup artist"),
    ("Zom Marie", "zommarie", "TH", "tiktok", ["Beauty", "Fashion"], 4_200_000, 310, 52_000_000, 920, 420_000, 4.9, "Beauty and fashion influencer"),
    ("Mayy R", "mayyr", "TH", "tiktok", ["Beauty", "Lifestyle"], 6_500_000, 245, 82_000_000, 1100, 580_000, 4.5, "Thai beauty content creator"),
    ("Fah Sarika", "fahsarika", "TH", "instagram", ["Beauty", "Lifestyle"], 2_800_000, 670, 0, 1800, 0, 3.6, "Beauty and lifestyle"),
    ("Meiisme", "meiisme", "TH", "tiktok", ["Beauty", "Comedy"], 3_100_000, 198, 38_000_000, 680, 320_000, 5.1, "Beauty reviews with humor"),
    ("Nune Woranuch", "nuneworanuch", "TH", "instagram", ["Beauty", "Fashion"], 5_200_000, 890, 0, 2100, 0, 2.5, "Thai actress and beauty icon"),

    # Food
    ("Mark Wiens", "markwiens", "TH", "youtube", ["Food", "Travel"], 10_200_000, 34, 0, 1800, 2_500_000, 4.8, "Bangkok-based food vlogger"),
    ("Mark Wiens", "markwiens", "TH", "tiktok", ["Food", "Travel"], 3_800_000, 120, 42_000_000, 680, 380_000, 4.2, "Street food content"),
    ("Paidon", "paidon_th", "TH", "tiktok", ["Food", "Comedy"], 5_600_000, 234, 68_000_000, 980, 520_000, 5.3, "Thai food reviewer"),
    ("Jee Juicy", "jeejuicy", "TH", "tiktok", ["Food"], 2_400_000, 178, 28_000_000, 580, 280_000, 4.7, "Food exploration"),
    ("Hungryستان", "hungrythailand", "TH", "tiktok", ["Food", "Travel"], 1_800_000, 210, 19_000_000, 420, 180_000, 4.4, "Thai street food tours"),

    # Gaming
    ("Heartrocker", "heartrocker", "TH", "youtube", ["Gaming"], 7_200_000, 45, 0, 3200, 980_000, 3.8, "Thai gaming YouTuber"),
    ("Bie The Ska", "bietheska", "TH", "youtube", ["Gaming", "Entertainment"], 9_500_000, 56, 0, 2800, 1_200_000, 3.5, "Gaming content creator"),
    ("Bie The Ska", "bietheska", "TH", "tiktok", ["Gaming", "Entertainment"], 4_200_000, 198, 48_000_000, 780, 380_000, 4.1, "Gaming clips and comedy"),
    ("PGONE", "pgone_th", "TH", "tiktok", ["Gaming"], 2_100_000, 156, 22_000_000, 520, 250_000, 4.5, "Pro gamer content"),
    ("Zbing Z", "zbingz", "TH", "youtube", ["Gaming", "Entertainment"], 14_500_000, 34, 0, 3500, 1_800_000, 3.2, "Horror gaming channel"),

    # Comedy
    ("Kamsing Family", "kamsingfamily", "TH", "tiktok", ["Comedy", "Entertainment"], 8_900_000, 310, 120_000_000, 1600, 850_000, 4.6, "Thai comedy family"),
    ("NuNew", "nunew.ch", "TH", "tiktok", ["Entertainment", "Music"], 6_200_000, 245, 78_000_000, 1100, 580_000, 5.2, "Singer and actor"),
    ("TikTok Thailand", "tiktokthailand_", "TH", "tiktok", ["Entertainment"], 3_500_000, 120, 42_000_000, 890, 320_000, 3.8, "Thai entertainment compilation"),

    # Fitness
    ("Blogilates TH", "blogilatesthai", "TH", "tiktok", ["Fitness"], 890_000, 145, 8_500_000, 320, 95_000, 4.8, "Thai fitness content"),
    ("FitJung", "fitjung", "TH", "tiktok", ["Fitness", "Lifestyle"], 1_200_000, 178, 12_000_000, 420, 150_000, 5.1, "Thai fitness influencer"),

    # Tech
    ("BananaIT", "bananait", "TH", "youtube", ["Tech"], 2_800_000, 34, 0, 1800, 420_000, 4.5, "Thai tech reviewer"),
    ("JBB", "jbbchannel", "TH", "youtube", ["Tech", "Lifestyle"], 1_500_000, 45, 0, 1200, 280_000, 4.8, "Gadget reviews in Thai"),

    # Suspicious
    ("FakeStarTH", "fakestarth", "TH", "tiktok", ["Lifestyle"], 3_800_000, 5, 4_100_000, 25, 9_000, 0.2, "Bought followers account"),

    # ========================================================================
    # PHILIPPINES (PH) - 55+ creators
    # ========================================================================
    # Entertainment & Comedy
    ("Mimiyuuuh", "mimiyuuuh", "PH", "tiktok", ["Comedy", "Entertainment", "Lifestyle"], 15_200_000, 456, 245_000_000, 2200, 1_500_000, 5.2, "Philippines comedy queen"),
    ("Mimiyuuuh", "mimiyuuuh", "PH", "youtube", ["Comedy", "Entertainment"], 7_800_000, 89, 0, 1800, 1_200_000, 4.8, "Comedy and lifestyle vlogger"),
    ("Alex Gonzaga", "alexgonzaga", "PH", "tiktok", ["Comedy", "Entertainment"], 18_500_000, 567, 310_000_000, 2800, 1_800_000, 4.5, "Actress, singer, comedian"),
    ("Alex Gonzaga", "alexgonzaga", "PH", "youtube", ["Comedy", "Entertainment"], 12_500_000, 78, 0, 2400, 1_500_000, 3.8, "Gonzaga family content"),
    ("AC Bonifacio", "acabonifacio", "PH", "tiktok", ["Dance", "Entertainment"], 8_200_000, 345, 98_000_000, 1400, 720_000, 5.1, "Dancer and performer"),
    ("Donny Pangilinan", "donnypangilinan", "PH", "tiktok", ["Entertainment", "Lifestyle"], 6_800_000, 234, 82_000_000, 1100, 580_000, 4.3, "Actor and content creator"),
    ("Ivana Alawi", "ivanaalawi", "PH", "youtube", ["Entertainment", "Lifestyle"], 16_500_000, 56, 0, 2800, 2_200_000, 3.9, "Actress and vlogger"),
    ("Ivana Alawi", "ivanaalawi", "PH", "tiktok", ["Entertainment", "Lifestyle"], 9_200_000, 290, 120_000_000, 1600, 850_000, 3.5, "Entertainment content"),
    ("Cong TV", "congtv", "PH", "youtube", ["Comedy", "Entertainment"], 12_800_000, 67, 0, 2200, 1_800_000, 4.5, "Filipino comedy YouTuber"),
    ("Niana Guerrero", "nianaguerrero", "PH", "tiktok", ["Dance", "Entertainment", "Comedy"], 28_000_000, 567, 480_000_000, 3200, 2_200_000, 4.1, "Dancer and content creator"),
    ("Niana Guerrero", "nianaguerrero", "PH", "youtube", ["Dance", "Entertainment"], 15_200_000, 89, 0, 2800, 1_500_000, 3.5, "Dance and lifestyle vlogger"),
    ("Ranz Kyle", "raborneyyy", "PH", "youtube", ["Dance", "Entertainment"], 14_500_000, 78, 0, 2600, 1_200_000, 3.2, "Dance and vlog content"),

    # Beauty & Fashion
    ("Anne Clutz", "anneclutztv", "PH", "youtube", ["Beauty", "Fashion"], 3_800_000, 56, 0, 1200, 450_000, 4.5, "Filipino beauty guru"),
    ("Raiza Contawi", "raizacontawi", "PH", "tiktok", ["Beauty", "Lifestyle"], 4_200_000, 310, 48_000_000, 890, 380_000, 4.8, "Beauty and lifestyle creator"),
    ("Say Tioco", "saytioco", "PH", "tiktok", ["Beauty", "Comedy"], 3_500_000, 245, 38_000_000, 720, 320_000, 5.2, "Beauty with comedy"),
    ("Rei Germar", "reigermar", "PH", "youtube", ["Beauty", "Lifestyle"], 2_800_000, 45, 0, 890, 380_000, 5.1, "Beauty vlogger"),
    ("Toni Sia", "tonisia", "PH", "tiktok", ["Fashion", "Lifestyle"], 2_100_000, 198, 22_000_000, 560, 250_000, 4.6, "Fashion content creator"),

    # Food
    ("Erwan Heussaff", "eraborneyyy", "PH", "youtube", ["Food", "Lifestyle"], 3_200_000, 45, 0, 980, 420_000, 4.8, "Celebrity chef and food vlogger"),
    ("Erwan Heussaff", "erwanheussaff", "PH", "tiktok", ["Food", "Lifestyle"], 2_800_000, 178, 32_000_000, 680, 350_000, 5.1, "Food and cooking content"),
    ("Ninong Ry", "ninongry", "PH", "youtube", ["Food"], 5_200_000, 34, 0, 1400, 850_000, 5.5, "Filipino cooking channel"),
    ("Peppy Kitchen", "peppykitchenph", "PH", "tiktok", ["Food"], 1_800_000, 210, 19_000_000, 480, 180_000, 4.9, "Quick recipe content"),
    ("Jamill", "jamillph", "PH", "youtube", ["Food", "Comedy"], 8_500_000, 56, 0, 1800, 1_200_000, 4.2, "Mukbang and food challenge"),

    # Gaming
    ("ChooxTV", "chooxtv", "PH", "youtube", ["Gaming", "Comedy"], 9_800_000, 56, 0, 2200, 1_200_000, 3.8, "ML and gaming content"),
    ("ChooxTV", "chooxtv", "PH", "tiktok", ["Gaming", "Comedy"], 5_200_000, 234, 62_000_000, 980, 520_000, 4.2, "Gaming clips"),
    ("DobiMobile", "dobimobile", "PH", "youtube", ["Gaming"], 3_500_000, 34, 0, 1200, 580_000, 4.5, "Mobile Legends content"),
    ("Akosi Dogie", "akosidogie", "PH", "youtube", ["Gaming"], 6_200_000, 45, 0, 1800, 850_000, 3.9, "ML streamer and content creator"),
    ("PaoLUL", "paolul", "PH", "youtube", ["Gaming", "Comedy"], 4_500_000, 45, 0, 1400, 650_000, 4.1, "Gaming with comedy"),

    # Fitness & Lifestyle
    ("Vito Selma", "vitoselma", "PH", "instagram", ["Lifestyle", "Fashion"], 890_000, 456, 0, 1200, 0, 3.8, "Design and lifestyle"),
    ("Pia Wurtzbach", "piawurtzbach", "PH", "instagram", ["Lifestyle", "Fashion", "Beauty"], 13_500_000, 1200, 0, 3800, 0, 2.1, "Miss Universe 2015"),

    # Suspicious
    ("ShadyInfluencerPH", "shadyinfluencerph", "PH", "tiktok", ["Lifestyle"], 4_200_000, 6, 4_800_000, 35, 10_000, 0.3, "Bot-like engagement patterns"),

    # ========================================================================
    # VIETNAM (VN) - 45+ creators
    # ========================================================================
    # Entertainment & Lifestyle
    ("Quang Linh Vlogs", "quanglinhvlogs", "VN", "tiktok", ["Lifestyle", "Entertainment", "Travel"], 9_800_000, 234, 145_000_000, 1800, 1_200_000, 5.8, "Vietnamese in Africa, charity content"),
    ("Quang Linh Vlogs", "quanglinhvlogs", "VN", "youtube", ["Lifestyle", "Travel"], 3_800_000, 45, 0, 1200, 850_000, 5.5, "Africa vlogs"),
    ("Son Tung MTP", "sonborneyyy", "VN", "youtube", ["Music", "Entertainment"], 14_200_000, 34, 0, 320, 8_500_000, 3.2, "Vietnam's biggest music artist"),
    ("Son Tung MTP", "saborneyyy", "VN", "tiktok", ["Music", "Entertainment"], 8_500_000, 120, 95_000_000, 580, 850_000, 3.5, "Music content"),
    ("Tran Thanh", "tranthanh", "VN", "tiktok", ["Comedy", "Entertainment"], 12_500_000, 345, 185_000_000, 2200, 1_200_000, 4.2, "Top Vietnamese comedian and MC"),
    ("Tran Thanh", "taborneyyy", "VN", "youtube", ["Comedy", "Entertainment"], 8_200_000, 67, 0, 1800, 1_500_000, 3.8, "Comedy and talk shows"),

    # Beauty & Fashion
    ("Phuong Ly", "phuongly", "VN", "tiktok", ["Music", "Beauty", "Fashion"], 5_200_000, 234, 62_000_000, 980, 520_000, 4.8, "Singer and fashion icon"),
    ("Phuong Ly", "phuongly", "VN", "instagram", ["Music", "Fashion"], 3_800_000, 650, 0, 1800, 0, 3.5, "Vietnamese singer"),
    ("Changmakeup", "changmakeup", "VN", "youtube", ["Beauty"], 2_800_000, 45, 0, 890, 420_000, 4.5, "Vietnam's top beauty YouTuber"),
    ("Changmakeup", "changmakeup", "VN", "tiktok", ["Beauty", "Fashion"], 3_500_000, 210, 38_000_000, 680, 320_000, 4.8, "Beauty content"),
    ("Trinh Pham", "trinhpham", "VN", "instagram", ["Beauty", "Fashion"], 1_200_000, 456, 0, 1200, 0, 4.2, "Beauty blogger and influencer"),
    ("An Phat", "anphat_beauty", "VN", "tiktok", ["Beauty"], 2_100_000, 178, 22_000_000, 520, 250_000, 5.1, "Skincare reviews"),
    ("Lien Xo", "lienxo_beauty", "VN", "tiktok", ["Beauty", "Comedy"], 1_800_000, 198, 19_000_000, 480, 220_000, 4.9, "Beauty with humor"),

    # Food
    ("Ninh Tito", "naborneyyy", "VN", "youtube", ["Food", "Entertainment"], 5_800_000, 34, 0, 1400, 850_000, 5.2, "Vietnamese food content"),
    ("Sunny Truong", "sunnytruong", "VN", "tiktok", ["Food", "Lifestyle"], 3_200_000, 210, 35_000_000, 680, 320_000, 4.6, "Vietnamese food reviewer"),
    ("VietFood", "vietfoodpage", "VN", "tiktok", ["Food"], 4_500_000, 178, 48_000_000, 890, 420_000, 4.2, "Vietnamese cuisine showcase"),
    ("Anh Minh Food", "anhaborneyyy", "VN", "tiktok", ["Food", "Comedy"], 2_800_000, 234, 28_000_000, 620, 280_000, 4.8, "Street food reviews"),
    ("Ba Tan Vlog", "batanvlog", "VN", "youtube", ["Food", "Entertainment"], 4_200_000, 23, 0, 980, 650_000, 3.9, "Giant food cooking grandma"),

    # Gaming
    ("Do Mixi", "domixi", "VN", "youtube", ["Gaming", "Entertainment"], 7_200_000, 34, 0, 2800, 1_200_000, 4.5, "Top Vietnamese gaming streamer"),
    ("Do Mixi", "domixi", "VN", "tiktok", ["Gaming", "Entertainment"], 4_500_000, 178, 52_000_000, 890, 480_000, 4.8, "Gaming clips"),
    ("PewPew", "pewpew", "VN", "tiktok", ["Gaming", "Entertainment"], 3_800_000, 198, 42_000_000, 780, 380_000, 4.2, "Vietnamese gaming personality"),
    ("Viruss", "viruss", "VN", "youtube", ["Gaming", "Entertainment"], 3_500_000, 45, 0, 1200, 520_000, 4.1, "Gaming streamer"),
    ("SBTC Esports", "sbtcesports", "VN", "tiktok", ["Gaming"], 1_200_000, 120, 12_000_000, 420, 150_000, 4.5, "Vietnamese esports team"),

    # Comedy
    ("Le Nha", "lenha", "VN", "tiktok", ["Comedy", "Entertainment"], 6_800_000, 290, 82_000_000, 1200, 650_000, 5.1, "Vietnamese comedy creator"),
    ("Hoang Meo", "hoangmeo", "VN", "tiktok", ["Comedy"], 4_200_000, 234, 48_000_000, 890, 420_000, 4.8, "Sketch comedy"),
    ("Vanh Leg", "vanhleg", "VN", "youtube", ["Comedy", "Entertainment"], 5_500_000, 45, 0, 1400, 850_000, 4.5, "Comedy skits and vlogs"),

    # Tech
    ("Tinhte", "tinhte", "VN", "youtube", ["Tech"], 3_200_000, 34, 0, 2800, 350_000, 4.2, "Vietnam's top tech media"),
    ("The Duc", "theduc", "VN", "tiktok", ["Tech", "Lifestyle"], 1_500_000, 145, 15_000_000, 420, 180_000, 4.6, "Tech reviews in Vietnamese"),

    # Fitness
    ("HLV Ryan Long", "ryanlong", "VN", "youtube", ["Fitness", "Lifestyle"], 1_800_000, 34, 0, 680, 280_000, 5.2, "Fitness trainer and YouTuber"),
    ("Gym Viet", "gymviet", "VN", "tiktok", ["Fitness"], 980_000, 156, 9_200_000, 320, 95_000, 4.8, "Vietnamese fitness content"),

    # Suspicious
    ("BotVN", "botvn123", "VN", "tiktok", ["Lifestyle"], 2_800_000, 3, 2_900_000, 20, 6_000, 0.2, "Obvious bot account"),

    # ========================================================================
    # SINGAPORE (SG) - 45+ creators
    # ========================================================================
    # Entertainment & Comedy
    ("JianHao Tan", "jianhaotan", "SG", "youtube", ["Comedy", "Entertainment"], 5_800_000, 67, 0, 1800, 1_200_000, 4.5, "Singapore's top YouTuber, school sketch comedy"),
    ("JianHao Tan", "jianhaotan", "SG", "tiktok", ["Comedy", "Entertainment"], 8_200_000, 234, 98_000_000, 1400, 720_000, 4.8, "Comedy skits"),
    ("Wah!Banana", "wahbanana", "SG", "youtube", ["Comedy", "Entertainment"], 1_200_000, 45, 0, 2200, 250_000, 3.8, "Singaporean comedy channel"),
    ("Wah!Banana", "wahbanana", "SG", "tiktok", ["Comedy", "Entertainment"], 2_800_000, 198, 32_000_000, 780, 280_000, 4.2, "Comedy sketches"),
    ("NOC (Night Owl Cinematics)", "nightowlcinematics", "SG", "youtube", ["Comedy", "Food"], 1_500_000, 56, 0, 1800, 180_000, 3.2, "Food reviews and comedy"),
    ("Ryan Sylvia", "ryansylvia", "SG", "tiktok", ["Comedy", "Lifestyle"], 3_500_000, 245, 42_000_000, 890, 380_000, 4.5, "Comedy content creator"),
    ("Dee Kosh", "deaborneyyy", "SG", "youtube", ["Comedy", "Entertainment"], 680_000, 34, 0, 980, 120_000, 4.1, "Commentary and comedy"),
    ("TreePotatoes", "treepotatoes", "SG", "youtube", ["Comedy", "Entertainment"], 580_000, 34, 0, 1200, 95_000, 3.9, "Singaporean comedy duo"),

    # Beauty & Fashion
    ("Naomi Neo", "naomineo_", "SG", "instagram", ["Beauty", "Lifestyle", "Fashion"], 680_000, 456, 0, 1800, 0, 3.5, "OG Singapore influencer"),
    ("Naomi Neo", "naomineo_", "SG", "tiktok", ["Beauty", "Lifestyle"], 1_200_000, 198, 12_000_000, 420, 150_000, 4.8, "Lifestyle and beauty content"),
    ("Xiaxue", "xiaxue", "SG", "instagram", ["Lifestyle", "Beauty"], 780_000, 890, 0, 1200, 0, 2.8, "OG Singapore blogger"),
    ("Andrea Chong", "dreachong", "SG", "instagram", ["Fashion", "Lifestyle", "Beauty"], 420_000, 345, 0, 980, 0, 3.9, "Fashion and lifestyle"),
    ("Mongabong", "mongabong", "SG", "instagram", ["Fashion", "Lifestyle"], 380_000, 310, 0, 890, 0, 4.2, "Fashion influencer"),
    ("Christabel Chua", "bellywellyjelly", "SG", "instagram", ["Beauty", "Fashion", "Lifestyle"], 310_000, 280, 0, 780, 0, 4.5, "Beauty and fashion"),
    ("Yoyo Cao", "yoyokulala", "SG", "instagram", ["Fashion"], 520_000, 390, 0, 1100, 0, 3.2, "Fashion designer and influencer"),
    ("Tiffany Yong", "tiffanyyong", "SG", "instagram", ["Fashion", "Lifestyle"], 180_000, 230, 0, 560, 0, 4.8, "Fashion and entertainment"),

    # Food
    ("Eatbook SG", "eatbook", "SG", "tiktok", ["Food"], 850_000, 178, 8_200_000, 1200, 85_000, 4.5, "Singapore food reviews"),
    ("SethLui", "sethlui", "SG", "tiktok", ["Food", "Lifestyle"], 620_000, 145, 5_800_000, 890, 65_000, 4.2, "Food and lifestyle reviews"),
    ("Zermatt Neo", "zermattneo", "SG", "tiktok", ["Food", "Lifestyle"], 2_100_000, 210, 22_000_000, 580, 250_000, 5.1, "Food adventure content"),
    ("Miss Tam Chiak", "misstamchiak", "SG", "tiktok", ["Food"], 450_000, 120, 3_800_000, 680, 45_000, 4.2, "SG food blogger"),
    ("Daniel Food Diary", "danielfooddiary", "SG", "instagram", ["Food"], 380_000, 310, 0, 1200, 0, 3.8, "Food photography and reviews"),

    # Gaming
    ("Xiaofeng", "xiaofeng", "SG", "tiktok", ["Gaming", "Comedy"], 1_500_000, 178, 15_000_000, 520, 180_000, 4.5, "Gaming content creator"),
    ("NOC Gaming", "nocgaming", "SG", "youtube", ["Gaming"], 320_000, 23, 0, 680, 45_000, 3.8, "Gaming channel"),
    ("HowToBasicSG", "howtobasicsg", "SG", "tiktok", ["Gaming", "Comedy"], 890_000, 145, 8_500_000, 380, 95_000, 4.2, "Gaming humor content"),

    # Tech & Education
    ("Tech Lingo", "techlingo", "SG", "youtube", ["Tech"], 280_000, 23, 0, 580, 45_000, 4.8, "Singapore tech reviews"),
    ("Nas Daily", "nasdaily", "SG", "tiktok", ["Education", "Lifestyle"], 5_200_000, 234, 62_000_000, 1800, 520_000, 3.8, "1-minute education videos (based in SG)"),
    ("Nas Daily", "nasdaily", "SG", "youtube", ["Education", "Lifestyle"], 8_500_000, 56, 0, 2200, 850_000, 3.2, "Educational content"),

    # Fitness
    ("Cheryl Tay", "cheryltay", "SG", "instagram", ["Fitness", "Lifestyle"], 120_000, 210, 0, 420, 0, 5.2, "Fitness coach and content creator"),
    ("Jordan Yeoh", "jordanyeoh", "SG", "youtube", ["Fitness"], 2_500_000, 34, 0, 680, 380_000, 4.8, "Malaysian-Singaporean fitness YouTuber"),
    ("Jordan Yeoh", "jordanyeohfitness", "SG", "tiktok", ["Fitness"], 1_800_000, 120, 18_000_000, 480, 220_000, 5.1, "Fitness content"),

    # Lifestyle
    ("TheSmartLocal", "thesmartlocal", "SG", "youtube", ["Lifestyle", "Entertainment"], 1_200_000, 34, 0, 1800, 180_000, 3.5, "Singapore lifestyle media"),
    ("TheSmartLocal", "thesmartlocal", "SG", "tiktok", ["Lifestyle", "Entertainment"], 580_000, 120, 4_800_000, 890, 55_000, 3.8, "SG lifestyle content"),
    ("Mothership SG", "mothershipsg", "SG", "tiktok", ["Lifestyle", "Entertainment"], 1_500_000, 145, 15_000_000, 1200, 120_000, 3.5, "Singapore news and culture"),

    # Suspicious
    ("FakeGrowthSG", "fakegrowthsg", "SG", "instagram", ["Lifestyle"], 1_500_000, 5200, 0, 60, 0, 0.3, "Suspicious following ratio"),
    ("BotAccountSG", "botaccountsg", "SG", "tiktok", ["Lifestyle"], 2_200_000, 4, 2_400_000, 18, 5_000, 0.2, "Bot-like account"),
]


def generate_content_samples(presence_id: int, platform: str, username: str, avg_views: int, engagement_rate: float, n=3):
    """Generate realistic content samples for a creator."""
    samples = []
    now = datetime.now()
    for i in range(n):
        days_ago = random.randint(1, 60)
        posted = now - timedelta(days=days_ago)
        view_variance = random.uniform(0.5, 2.0)
        views = max(100, int(avg_views * view_variance))
        like_rate = engagement_rate / 100 * random.uniform(0.6, 1.4)
        likes = max(5, int(views * like_rate))
        comments = max(1, int(likes * random.uniform(0.02, 0.15)))
        shares = max(0, int(likes * random.uniform(0.01, 0.08)))

        if platform == "tiktok":
            url = f"https://www.tiktok.com/@{username}/video/{random.randint(7000000000000000000, 7399999999999999999)}"
        elif platform == "youtube":
            url = f"https://www.youtube.com/watch?v={''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=11))}"
        else:
            url = f"https://www.instagram.com/p/{''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=11))}/"

        captions = [
            f"New content from {username} 🔥",
            f"Check this out! #{username}",
            "Amazing day! #fyp #viral",
            f"POV: When you... 😂 #{platform}",
            "Who can relate? 🤣 #relatable",
            "Tutorial time! 📚 #howto",
            "Day in my life ✨ #ditl",
            "This blew up! 💥 #trending",
        ]

        samples.append({
            "presence_id": presence_id,
            "url": url,
            "views": views,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "posted_at": posted.strftime("%Y-%m-%d"),
            "caption": random.choice(captions),
        })
    return samples


def generate_metrics_history(presence_id: int, followers: int, avg_views: int, engagement_rate: float, n=5):
    """Generate historical metrics showing growth over time."""
    history = []
    now = datetime.now()
    for i in range(n):
        days_ago = (i + 1) * 30  # monthly snapshots
        date = now - timedelta(days=days_ago)
        # Growth factor: older = fewer followers
        growth_factor = 1 - (i * random.uniform(0.03, 0.08))
        hist_followers = max(1000, int(followers * growth_factor))
        hist_views = max(100, int(avg_views * growth_factor * random.uniform(0.8, 1.2)))
        hist_er = max(0.1, engagement_rate * random.uniform(0.85, 1.15))

        history.append({
            "presence_id": presence_id,
            "date": date.strftime("%Y-%m-%d"),
            "followers": hist_followers,
            "avg_views": hist_views,
            "engagement_rate": round(hist_er, 2),
        })
    return history


def main():
    print(f"📦 Opening database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check existing creators to avoid duplicates
    cursor.execute("SELECT username FROM platform_presences")
    existing_usernames = {row[0] for row in cursor.fetchall()}
    print(f"📊 Found {len(existing_usernames)} existing platform presences")

    # Track unique creator names to avoid duplicates in our data
    # (same person can have multiple platform presences)
    inserted_creators = {}  # name+country -> creator_id
    stats = {"creators": 0, "presences": 0, "samples": 0, "history": 0, "scores": 0, "skipped": 0}

    for entry in CREATORS:
        name, username, country, platform, categories, followers, following, total_likes, total_videos, avg_views, engagement_rate, bio = entry

        # Skip if this exact username+platform already exists
        if username in existing_usernames:
            stats["skipped"] += 1
            continue

        # Check if we already inserted this creator (multi-platform)
        creator_key = f"{name}_{country}"
        if creator_key in inserted_creators:
            creator_id = inserted_creators[creator_key]
        else:
            # Insert creator
            profile_image = dicebear_avatar(username)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO creators (name, bio, profile_image, country, primary_platform, categories, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, bio, profile_image, country, platform, json.dumps(categories), now, now))
            creator_id = cursor.lastrowid
            inserted_creators[creator_key] = creator_id
            stats["creators"] += 1

        # Insert platform presence
        if platform == "tiktok":
            url = tiktok_url(username)
        elif platform == "instagram":
            url = instagram_url(username)
        else:
            url = youtube_url(username)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO platform_presences (creator_id, platform, username, url, followers, following, total_likes, total_videos, avg_views, engagement_rate, last_scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (creator_id, platform, username, url, followers, following, total_likes, total_videos, avg_views, engagement_rate, now))
        presence_id = cursor.lastrowid
        stats["presences"] += 1
        existing_usernames.add(username)

        # Content samples
        samples = generate_content_samples(presence_id, platform, username, avg_views, engagement_rate)
        for s in samples:
            cursor.execute("""
                INSERT INTO content_samples (presence_id, url, views, likes, comments, shares, posted_at, caption)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (s["presence_id"], s["url"], s["views"], s["likes"], s["comments"], s["shares"], s["posted_at"], s["caption"]))
            stats["samples"] += 1

        # Metrics history
        history = generate_metrics_history(presence_id, followers, avg_views, engagement_rate)
        for h in history:
            cursor.execute("""
                INSERT INTO metrics_history (presence_id, date, followers, avg_views, engagement_rate)
                VALUES (?, ?, ?, ?, ?)
            """, (h["presence_id"], h["date"], h["followers"], h["avg_views"], h["engagement_rate"]))
            stats["history"] += 1

        # Audit score (only once per creator)
        if creator_key not in {f"{name}_{country}" for name, _, country, *_ in CREATORS[:CREATORS.index(entry)]}:
            score = compute_audit_score(followers, engagement_rate, avg_views)
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO audit_scores (creator_id, overall_score, follower_quality, engagement_authenticity, growth_consistency, comment_quality, scored_at, signals_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    creator_id,
                    score["overall"],
                    score["follower_quality"],
                    score["engagement_authenticity"],
                    score["growth_consistency"],
                    score["comment_quality"],
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    json.dumps(score["signals"]),
                ))
                stats["scores"] += 1
            except sqlite3.IntegrityError:
                pass  # Already has a score

    conn.commit()
    conn.close()

    print("\n✅ Bulk seed complete!")
    print(f"   Creators inserted:  {stats['creators']}")
    print(f"   Presences inserted: {stats['presences']}")
    print(f"   Content samples:    {stats['samples']}")
    print(f"   History records:    {stats['history']}")
    print(f"   Audit scores:       {stats['scores']}")
    print(f"   Skipped (existing): {stats['skipped']}")


if __name__ == "__main__":
    main()
