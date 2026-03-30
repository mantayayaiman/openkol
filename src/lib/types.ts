export interface Creator {
  id: number;
  name: string;
  bio: string;
  profile_image: string;
  country: CountryCode;
  primary_platform: Platform;
  categories: string[];
  created_at: string;
  updated_at: string;
}

export interface PlatformPresence {
  id: number;
  creator_id: number;
  platform: Platform;
  username: string;
  url: string;
  followers: number;
  following: number;
  total_likes: number;
  total_videos: number;
  avg_views: number;
  engagement_rate: number;
  last_scraped_at: string;
}

export interface MetricsHistory {
  id: number;
  presence_id: number;
  date: string;
  followers: number;
  avg_views: number;
  engagement_rate: number;
}

export interface ContentSample {
  id: number;
  presence_id: number;
  url: string;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  posted_at: string;
  caption: string;
}

export interface AuditScore {
  id: number;
  creator_id: number;
  overall_score: number;
  follower_quality: number;
  engagement_authenticity: number;
  growth_consistency: number;
  comment_quality: number;
  scored_at: string;
  signals_json: string;
}

export interface CreatorWithDetails extends Creator {
  platforms: PlatformPresence[];
  audit: AuditScore | null;
  content_samples: ContentSample[];
}

export type Platform = 'tiktok' | 'instagram' | 'youtube' | 'facebook';
export type CountryCode = 'MY' | 'ID' | 'TH' | 'PH' | 'VN' | 'SG';

export const PLATFORMS: { value: Platform; label: string }[] = [
  { value: 'tiktok', label: 'TikTok' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'youtube', label: 'YouTube' },
];

export const COUNTRIES: { value: CountryCode; label: string; flag: string }[] = [
  { value: 'MY', label: 'Malaysia', flag: '🇲🇾' },
  { value: 'ID', label: 'Indonesia', flag: '🇮🇩' },
  { value: 'TH', label: 'Thailand', flag: '🇹🇭' },
  { value: 'PH', label: 'Philippines', flag: '🇵🇭' },
  { value: 'VN', label: 'Vietnam', flag: '🇻🇳' },
  { value: 'SG', label: 'Singapore', flag: '🇸🇬' },
];

export const CATEGORIES = [
  'Beauty & Skincare',
  'Fashion & Style',
  'Food & F&B',
  'Gaming',
  'Tech & Gadgets',
  'Lifestyle',
  'Fitness & Health',
  'Travel',
  'Comedy & Entertainment',
  'Education',
  'Music & Dance',
  'Parenting & Family',
  'Automotive',
  'Finance & Business',
  'Pets & Animals',
] as const;

export type Category = (typeof CATEGORIES)[number];

export function getScoreColor(score: number): 'green' | 'yellow' | 'red' {
  if (score >= 70) return 'green';
  if (score >= 40) return 'yellow';
  return 'red';
}

export function getScoreLabel(score: number): string {
  if (score >= 70) return 'Authentic';
  if (score >= 40) return 'Review';
  return 'Suspicious';
}

// Heat Score helpers
export type HeatLevel = 'fire' | 'hot' | 'warm' | 'cool';

export function getHeatLevel(score: number): HeatLevel {
  if (score >= 80) return 'fire';
  if (score >= 60) return 'hot';
  if (score >= 40) return 'warm';
  return 'cool';
}

export function getHeatLabel(score: number): string {
  if (score >= 80) return 'On Fire';
  if (score >= 60) return 'Hot';
  if (score >= 40) return 'Warm';
  return 'Cool';
}

export function getHeatEmoji(score: number): string {
  if (score >= 80) return '🔴';
  if (score >= 60) return '🟠';
  if (score >= 40) return '🟡';
  return '⬜';
}

export function getHeatColor(score: number): { text: string; bg: string; border: string } {
  if (score >= 80) return { text: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/40' };
  if (score >= 60) return { text: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/40' };
  if (score >= 40) return { text: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/40' };
  return { text: 'text-gray-400', bg: 'bg-gray-500/10', border: 'border-gray-500/40' };
}

export function formatNumber(n: number | null | undefined): string {
  if (n == null || isNaN(n)) return '0';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K';
  return n.toString();
}

export function formatEngagement(rate: number | null | undefined): string {
  if (rate == null || isNaN(rate)) return '0.00%';
  // DB stores engagement_rate already as percentage (e.g. 5.33 = 5.33%)
  return rate.toFixed(2) + '%';
}
