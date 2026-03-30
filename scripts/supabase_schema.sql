-- KolBuff Supabase Schema
-- Paste this into Supabase Dashboard → SQL Editor → New Query → Run

CREATE TABLE IF NOT EXISTS creators (
    id BIGINT PRIMARY KEY,
    name TEXT NOT NULL,
    bio TEXT DEFAULT '',
    profile_image TEXT DEFAULT '',
    country TEXT NOT NULL,
    primary_platform TEXT NOT NULL,
    categories TEXT DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    heat_score REAL DEFAULT 0,
    audience_demographics TEXT DEFAULT '',
    contact_email TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS platform_presences (
    id BIGINT PRIMARY KEY,
    creator_id BIGINT NOT NULL REFERENCES creators(id),
    platform TEXT NOT NULL,
    username TEXT NOT NULL,
    url TEXT DEFAULT '',
    followers BIGINT DEFAULT 0,
    following BIGINT DEFAULT 0,
    total_likes BIGINT DEFAULT 0,
    total_videos BIGINT DEFAULT 0,
    avg_views BIGINT DEFAULT 0,
    engagement_rate REAL DEFAULT 0,
    last_scraped_at TEXT DEFAULT '',
    recent_videos INTEGER DEFAULT 0,
    recent_views BIGINT DEFAULT 0,
    recent_new_followers BIGINT DEFAULT 0,
    impressions BIGINT DEFAULT 0,
    platform_uid TEXT DEFAULT '',
    top_content TEXT DEFAULT ''
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_creators_country ON creators(country);
CREATE INDEX IF NOT EXISTS idx_creators_name ON creators(name);
CREATE INDEX IF NOT EXISTS idx_creators_heat ON creators(heat_score DESC);
CREATE INDEX IF NOT EXISTS idx_pp_creator ON platform_presences(creator_id);
CREATE INDEX IF NOT EXISTS idx_pp_platform ON platform_presences(platform);
CREATE INDEX IF NOT EXISTS idx_pp_followers ON platform_presences(followers DESC);
CREATE INDEX IF NOT EXISTS idx_pp_username ON platform_presences(username);
CREATE INDEX IF NOT EXISTS idx_pp_creator_platform ON platform_presences(creator_id, platform);

-- Enable Row Level Security but allow public read
ALTER TABLE creators ENABLE ROW LEVEL SECURITY;
ALTER TABLE platform_presences ENABLE ROW LEVEL SECURITY;

-- Allow public read access (anyone can view creators)
CREATE POLICY "Public read creators" ON creators FOR SELECT USING (true);
CREATE POLICY "Public read presences" ON platform_presences FOR SELECT USING (true);

-- Allow service role full access (for data sync)
CREATE POLICY "Service write creators" ON creators FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service write presences" ON platform_presences FOR ALL USING (true) WITH CHECK (true);
