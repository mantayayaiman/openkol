'use client';

import { useState } from 'react';
import { formatNumber, formatEngagement, getHeatColor } from '@/lib/types';
import { cn } from '@/lib/cn';
import { ScoreBadge } from './ScoreBadge';
import { Users, Eye, Heart, Video, ExternalLink, Clock, AlertTriangle } from 'lucide-react';
import Image from 'next/image';
import { ShortlistButton } from './ShortlistButton';

interface CreatorCardProps {
  creator: {
    id: number;
    name: string;
    bio: string;
    profile_image: string;
    country: string;
    primary_platform: string;
    platform: string;
    username: string;
    platform_url: string;
    followers: number;
    avg_views: number;
    engagement_rate: number;
    total_likes: number;
    total_videos: number;
    overall_score: number;
    heat_score: number;
    categories: string;
    last_scraped_at: string;
  };
}

const platformColors: Record<string, string> = {
  tiktok: 'bg-pink-500/10 text-pink-400 border-pink-500/20',
  instagram: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  youtube: 'bg-red-500/10 text-red-400 border-red-500/20',
  facebook: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
};

const countryFlags: Record<string, string> = {
  MY: '🇲🇾', ID: '🇮🇩', TH: '🇹🇭', PH: '🇵🇭', VN: '🇻🇳', SG: '🇸🇬',
};

function AvatarImage({ src, name }: { src: string; name: string }) {
  const [error, setError] = useState(false);
  if (!src || error) {
    return (
      <div className="h-14 w-14 rounded-full bg-card-hover flex items-center justify-center text-xl font-bold text-muted">
        {name?.charAt(0)?.toUpperCase() || '?'}
      </div>
    );
  }
  return (
    <Image
      src={src}
      alt={name}
      width={56}
      height={56}
      className="h-14 w-14 rounded-full bg-card-hover object-cover"
      unoptimized
      onError={() => setError(true)}
    />
  );
}

export function CreatorCard({ creator }: CreatorCardProps) {
  const heatScore = creator.heat_score || 0;
  let categories: string[] = [];
  try { categories = JSON.parse(creator.categories); } catch { /* */ }

  // Calculate days since last update
  const lastScraped = creator.last_scraped_at ? new Date(creator.last_scraped_at) : null;
  const daysSinceUpdate = lastScraped ? Math.floor((Date.now() - lastScraped.getTime()) / (1000 * 60 * 60 * 24)) : null;
  const freshnessColor = daysSinceUpdate === null ? 'text-gray-500' : 
                        daysSinceUpdate < 7 ? 'text-green-400' : 
                        daysSinceUpdate < 30 ? 'text-yellow-400' : 'text-red-400';

  return (
    <a
      href={`/creator/${creator.id}`}
      className={cn(
        'group block rounded-xl border bg-card/50 p-5 transition-all hover:bg-card hover:border-accent/30 hover:shadow-lg hover:shadow-accent/5',
        'border-border'
      )}
    >
      <div className="flex items-start gap-4">
        {/* Avatar */}
        <div className="relative shrink-0">
          <AvatarImage src={creator.profile_image} name={creator.name} />
          <span className="absolute -bottom-1 -right-1 text-lg">
            {countryFlags[creator.country] || '🌏'}
          </span>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="font-semibold truncate group-hover:text-accent transition-colors">
                {creator.name}
              </h3>
              <div className="flex items-center gap-2 mt-0.5">
                <span className={cn('inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium', platformColors[creator.platform])}>
                  {creator.platform === 'tiktok' ? '♪' : creator.platform === 'youtube' ? '▶' : '📷'}
                  {' @'}{creator.username}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <ShortlistButton
                creator={{
                  id: creator.id,
                  name: creator.name,
                  username: creator.username,
                  platform: creator.platform,
                  profile_image: creator.profile_image,
                  followers: creator.followers,
                  engagement_rate: creator.engagement_rate,
                  heat_score: heatScore,
                  country: creator.country,
                  addedAt: '',
                }}
                size="sm"
              />
              <ScoreBadge score={heatScore} size="sm" />
            </div>
          </div>

          <p className="mt-2 text-sm text-muted-foreground line-clamp-2">{creator.bio}</p>

          {/* Metrics grid */}
          <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="flex items-center gap-1.5">
              <Users className="h-3.5 w-3.5 text-muted" />
              <span className="text-sm font-medium">{formatNumber(creator.followers)}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Eye className="h-3.5 w-3.5 text-muted" />
              <span className="text-sm font-medium">{formatNumber(creator.avg_views)}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Heart className="h-3.5 w-3.5 text-muted" />
              <span className="text-sm font-medium">{formatEngagement(creator.engagement_rate)}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Video className="h-3.5 w-3.5 text-muted" />
              <span className="text-sm font-medium">{creator.total_videos}</span>
            </div>
          </div>

          {/* Categories and Last Updated */}
          <div className="mt-3 flex items-center justify-between gap-2">
            {categories.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {categories.slice(0, 3).map((cat) => (
                  <span key={cat} className="rounded-full bg-surface px-2 py-0.5 text-xs text-muted-foreground">
                    {cat}
                  </span>
                ))}
              </div>
            )}
            {lastScraped && (
              <div className={cn('text-xs flex items-center gap-1 ml-auto', freshnessColor)} title={`Last updated: ${lastScraped.toLocaleDateString()}`}>
                {daysSinceUpdate !== null && daysSinceUpdate > 30 ? (
                  <AlertTriangle className="h-3 w-3" />
                ) : (
                  <Clock className="h-3 w-3" />
                )}
                {daysSinceUpdate === 0 ? 'Today' :
                 daysSinceUpdate === 1 ? '1 day ago' :
                 daysSinceUpdate !== null && daysSinceUpdate < 7 ? `${daysSinceUpdate} days ago` :
                 daysSinceUpdate !== null && daysSinceUpdate < 30 ? `${Math.floor(daysSinceUpdate / 7)}w ago` :
                 daysSinceUpdate !== null && daysSinceUpdate < 365 ? `${Math.floor(daysSinceUpdate / 30)}mo ago` :
                 `${Math.floor((daysSinceUpdate || 0) / 365)}y ago`}
                {daysSinceUpdate !== null && daysSinceUpdate > 30 && (
                  <span className="text-red-400 font-medium">stale</span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </a>
  );
}
