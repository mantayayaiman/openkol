'use client';

import { useState, useEffect, use } from 'react';
import { ScoreBadge } from '@/components/ScoreBadge';
import { formatNumber, formatEngagement, getScoreColor, getHeatLabel, getHeatEmoji, getHeatColor } from '@/lib/types';
import { cn } from '@/lib/cn';
import {
  Users, Eye, Heart, Video, ExternalLink, ArrowLeft,
  TrendingUp, MessageCircle, Share2, AlertTriangle, CheckCircle, Shield,
  Flame, BarChart3, Globe, Mail, Clock
} from 'lucide-react';
import Image from 'next/image';
import { ShortlistButton } from '@/components/ShortlistButton';

const platformColors: Record<string, string> = {
  tiktok: 'bg-pink-500/10 text-pink-400 border-pink-500/20',
  instagram: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  youtube: 'bg-red-500/10 text-red-400 border-red-500/20',
  facebook: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
};

const platformIcons: Record<string, string> = {
  tiktok: '♪', instagram: '📷', youtube: '▶', facebook: '📘',
};

const countryFlags: Record<string, string> = {
  MY: '🇲🇾', ID: '🇮🇩', TH: '🇹🇭', PH: '🇵🇭', VN: '🇻🇳', SG: '🇸🇬',
};

const countryNames: Record<string, string> = {
  MY: 'Malaysia', ID: 'Indonesia', TH: 'Thailand', PH: 'Philippines', VN: 'Vietnam', SG: 'Singapore',
};

function ProfileImageWithFallback({ src, name, size = 80 }: { src: string; name: string; size?: number }) {
  const [error, setError] = useState(false);
  if (!src || error) {
    return (
      <div
        className="rounded-full bg-card-hover flex items-center justify-center text-2xl font-bold text-muted shrink-0"
        style={{ width: size, height: size }}
      >
        {name?.charAt(0)?.toUpperCase() || '?'}
      </div>
    );
  }
  return (
    <Image
      src={src}
      alt={name}
      width={size}
      height={size}
      className="rounded-full bg-card-hover object-cover shrink-0"
      style={{ width: size, height: size }}
      unoptimized
      onError={() => setError(true)}
    />
  );
}

export default function CreatorPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [creator, setCreator] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [similarCreators, setSimilarCreators] = useState<any[]>([]);
  const [loadingSimilar, setLoadingSimilar] = useState(false);

  useEffect(() => {
    fetch(`/api/creators/${id}`)
      .then(res => res.json())
      .then(data => {
        setCreator(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (creator && creator.country && creator.categories) {
      setLoadingSimilar(true);
      const primaryPlatform = creator.platforms?.[0];
      const followersRange = primaryPlatform?.followers || 0;
      const minFollowers = followersRange * 0.5;
      const maxFollowers = followersRange * 2;
      
      fetch(`/api/creators/similar?id=${creator.id}&country=${creator.country}&category=${encodeURIComponent(creator.categories[0] || '')}&minFollowers=${minFollowers}&maxFollowers=${maxFollowers}`)
        .then(res => res.json())
        .then(data => {
          setSimilarCreators(data.creators || []);
          setLoadingSimilar(false);
        })
        .catch(() => {
          setLoadingSimilar(false);
        });
    }
  }, [creator]);

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 w-48 bg-card rounded" />
          <div className="h-64 bg-card rounded-xl" />
          <div className="grid grid-cols-2 gap-4">
            <div className="h-32 bg-card rounded-xl" />
            <div className="h-32 bg-card rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  if (!creator) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-20 text-center">
        <div className="mb-4">
          <h2 className="text-2xl font-bold mb-2">Creator not found</h2>
          <p className="text-muted-foreground mb-4">This creator may have been removed or doesn&apos;t exist.</p>
        </div>
        <a href="/browse" className="text-accent hover:underline">← Back to browse</a>
      </div>
    );
  }

  const primaryPlatform = creator.platforms?.[0];
  const audit = creator.audit;
  const heatScore = creator.heat_score || 0;
  const heatColors = getHeatColor(heatScore);
  const heatLabel = getHeatLabel(heatScore);
  const heatEmoji = getHeatEmoji(heatScore);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* Back button */}
      <a href="/browse" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors">
        <ArrowLeft className="h-4 w-4" />
        Back to browse
      </a>

      {/* Profile header */}
      <div className="rounded-xl border border-border bg-card/50 p-6 sm:p-8 mb-6">
        <div className="flex flex-col sm:flex-row gap-6">
          {/* Avatar & basic info */}
          <div className="flex items-start gap-5 flex-1">
            <ProfileImageWithFallback src={creator.profile_image} name={creator.name} size={80} />
            <div className="min-w-0">
              <h1 className="text-2xl sm:text-3xl font-bold">{creator.name}</h1>
              <div className="flex flex-wrap items-center gap-2 mt-2">
                <span className="text-sm text-muted-foreground">
                  {countryFlags[creator.country]} {countryNames[creator.country]}
                </span>
                {creator.categories?.map((cat: string) => (
                  <span key={cat} className="rounded-full bg-surface border border-border-subtle px-2.5 py-0.5 text-xs text-muted-foreground">
                    {cat}
                  </span>
                ))}
              </div>
              <p className="mt-3 text-muted-foreground max-w-lg">{creator.bio}</p>
              
              {/* Contact Information */}
              <div className="mt-4 flex flex-wrap gap-2">
                {creator.contact_email && creator.contact_email.includes('@') && !creator.contact_email.startsWith('Phone:') && (
                  <a
                    href={`mailto:${creator.contact_email}`}
                    className="inline-flex items-center gap-2 rounded-lg bg-accent/10 border border-accent/20 px-3 py-1.5 text-sm font-medium text-accent hover:bg-accent/20 transition-colors"
                  >
                    <Mail className="h-4 w-4" />
                    {creator.contact_email}
                  </a>
                )}
                {creator.contact_email && creator.contact_email.startsWith('Phone:') && (
                  <a
                    href={`tel:${creator.contact_email.replace('Phone: ', '').replace('Phone:', '').trim()}`}
                    className="inline-flex items-center gap-2 rounded-lg bg-green-500/10 border border-green-500/20 px-3 py-1.5 text-sm font-medium text-green-400 hover:bg-green-500/20 transition-colors"
                  >
                    📞 {creator.contact_email.replace('Phone: ', '').replace('Phone:', '').trim()}
                  </a>
                )}
                {/* DM buttons for each platform */}
                {creator.platforms?.map((p: any) => {
                  let dmUrl = '';
                  let dmLabel = '';
                  if (p.platform === 'tiktok' && p.username) {
                    dmUrl = `https://www.tiktok.com/@${p.username}`;
                    dmLabel = 'Message on TikTok';
                  } else if (p.platform === 'instagram' && p.username) {
                    dmUrl = `https://ig.me/m/${p.username}`;
                    dmLabel = 'DM on Instagram';
                  } else if (p.platform === 'youtube' && p.url) {
                    dmUrl = p.url;
                    dmLabel = 'Contact on YouTube';
                  } else if (p.platform === 'facebook' && p.url) {
                    dmUrl = `https://m.me/${p.username || ''}`;
                    dmLabel = 'Message on Facebook';
                  }
                  if (!dmUrl) return null;
                  const colors: Record<string, string> = {
                    tiktok: 'bg-pink-500/10 border-pink-500/20 text-pink-400 hover:bg-pink-500/20',
                    instagram: 'bg-purple-500/10 border-purple-500/20 text-purple-400 hover:bg-purple-500/20',
                    youtube: 'bg-red-500/10 border-red-500/20 text-red-400 hover:bg-red-500/20',
                    facebook: 'bg-blue-500/10 border-blue-500/20 text-blue-400 hover:bg-blue-500/20',
                  };
                  return (
                    <a
                      key={p.platform}
                      href={dmUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={cn(
                        'inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors',
                        colors[p.platform] || 'bg-surface border-border text-muted-foreground'
                      )}
                    >
                      <MessageCircle className="h-4 w-4" />
                      {dmLabel}
                    </a>
                  );
                })}
                {!creator.contact_email && (!creator.platforms || creator.platforms.length === 0) && (
                  <div className="inline-flex items-center gap-2 rounded-lg bg-surface border border-border px-3 py-1.5">
                    <Mail className="h-4 w-4 text-muted" />
                    <span className="text-sm text-muted-foreground">No contact info available</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Heat Score Badge + Shortlist */}
          <div className="sm:ml-auto flex flex-col items-center gap-3 shrink-0">
            <ScoreBadge score={heatScore} size="lg" />
            {primaryPlatform && (
              <ShortlistButton
                creator={{
                  id: creator.id,
                  name: creator.name,
                  username: primaryPlatform.username,
                  platform: primaryPlatform.platform,
                  profile_image: creator.profile_image,
                  followers: primaryPlatform.followers,
                  engagement_rate: primaryPlatform.engagement_rate,
                  heat_score: heatScore,
                  country: creator.country,
                  addedAt: '',
                }}
                size="md"
              />
            )}
          </div>
        </div>

        {/* Platform links - all cross-platform profiles */}
        {creator.platforms?.length > 0 && (
          <div className="flex flex-wrap gap-3 mt-6 pt-6 border-t border-border">
            {creator.platforms.map((p: any) => {
              // Calculate days since last update
              const lastScraped = p.last_scraped_at ? new Date(p.last_scraped_at) : null;
              const daysSinceUpdate = lastScraped ? Math.floor((Date.now() - lastScraped.getTime()) / (1000 * 60 * 60 * 24)) : null;
              const freshnessColor = daysSinceUpdate === null ? 'text-gray-500' : 
                                   daysSinceUpdate < 7 ? 'text-green-400' : 
                                   daysSinceUpdate < 30 ? 'text-yellow-400' : 'text-red-400';
              
              return (
                <div key={p.id} className="flex flex-col gap-1">
                  <a
                    href={p.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={cn(
                      'inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:opacity-80',
                      platformColors[p.platform]
                    )}
                  >
                    {platformIcons[p.platform]} @{p.username}
                    <span className="text-xs opacity-60">{formatNumber(p.followers)}</span>
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                  {lastScraped && (
                    <div className={cn('text-xs flex items-center gap-1', freshnessColor)}>
                      <Clock className="h-3 w-3" />
                      Last updated: {daysSinceUpdate === 0 ? 'Today' : daysSinceUpdate === 1 ? '1 day ago' : `${daysSinceUpdate} days ago`}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Recent Performance (30 Days) — PROMINENT */}
      {primaryPlatform && (primaryPlatform.recent_videos > 0 || primaryPlatform.recent_views > 0) && (
        <div className={cn('rounded-xl border-2 p-6 mb-6', heatColors.border, heatColors.bg)}>
          <h2 className={cn('text-lg font-semibold mb-4 flex items-center gap-2', heatColors.text)}>
            <Flame className="h-5 w-5" />
            Recent Performance (30 Days) — {heatEmoji} {heatLabel}
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="rounded-lg bg-background/50 p-3">
              <div className="text-xs text-muted-foreground mb-1">Videos Posted</div>
              <div className="text-2xl font-bold">{primaryPlatform.recent_videos || 0}</div>
            </div>
            <div className="rounded-lg bg-background/50 p-3">
              <div className="text-xs text-muted-foreground mb-1">Video Views</div>
              <div className="text-2xl font-bold">{formatNumber(primaryPlatform.recent_views || 0)}</div>
            </div>
            <div className="rounded-lg bg-background/50 p-3">
              <div className="text-xs text-muted-foreground mb-1">New Followers</div>
              <div className="text-2xl font-bold text-green-400">+{formatNumber(primaryPlatform.recent_new_followers || 0)}</div>
            </div>
            <div className="rounded-lg bg-background/50 p-3">
              <div className="text-xs text-muted-foreground mb-1">Impressions</div>
              <div className="text-2xl font-bold">{formatNumber(primaryPlatform.impressions || 0)}</div>
            </div>
          </div>
          {primaryPlatform.recent_videos > 0 && primaryPlatform.recent_views > 0 && (
            <div className="mt-3 text-sm text-muted-foreground">
              Avg {formatNumber(Math.round(primaryPlatform.recent_views / primaryPlatform.recent_videos))} views per video
            </div>
          )}
        </div>
      )}

      {/* Metrics grid */}
      {primaryPlatform && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
          {[
            { icon: Users, label: 'Followers', value: formatNumber(primaryPlatform.followers) },
            { icon: Users, label: 'Following', value: formatNumber(primaryPlatform.following) },
            { icon: Eye, label: 'Avg Views', value: formatNumber(primaryPlatform.avg_views) },
            { icon: Heart, label: 'Total Likes', value: formatNumber(primaryPlatform.total_likes) },
            { icon: TrendingUp, label: 'Engagement', value: formatEngagement(primaryPlatform.engagement_rate) },
            { icon: Video, label: 'Total Videos', value: (primaryPlatform.total_videos || 0).toLocaleString() },
          ].map((metric) => (
            <div key={metric.label} className="rounded-xl border border-border bg-card/50 p-4">
              <div className="flex items-center gap-1.5 mb-1">
                <metric.icon className="h-3.5 w-3.5 text-muted" />
                <span className="text-xs text-muted-foreground">{metric.label}</span>
              </div>
              <div className="text-xl font-bold">{metric.value}</div>
            </div>
          ))}
        </div>
      )}

      <div className="grid sm:grid-cols-2 gap-6 mb-6">
        {/* Authenticity breakdown (de-emphasized, secondary) */}
        {audit && (
          <div className="rounded-xl border border-border bg-card/50 p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Shield className="h-5 w-5 text-muted" />
              Authenticity Breakdown
              <span className="text-xs text-muted font-normal ml-auto">Score: {audit.overall_score}/100</span>
            </h2>
            <div className="space-y-4">
              {[
                { label: 'Follower Quality', value: audit.follower_quality, weight: '30%' },
                { label: 'Engagement Authenticity', value: audit.engagement_authenticity, weight: '20%' },
                { label: 'Growth Consistency', value: audit.growth_consistency, weight: '20%' },
                { label: 'Comment Quality', value: audit.comment_quality, weight: '10%' },
              ].map((item) => {
                const color = getScoreColor(item.value);
                return (
                  <div key={item.label}>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-sm">{item.label}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted">w: {item.weight}</span>
                        <span className={cn(
                          'text-sm font-bold',
                          color === 'green' && 'text-green-400',
                          color === 'yellow' && 'text-yellow-400',
                          color === 'red' && 'text-red-400',
                        )}>
                          {item.value}
                        </span>
                      </div>
                    </div>
                    <div className="h-2 rounded-full bg-surface overflow-hidden">
                      <div
                        className={cn(
                          'h-full rounded-full transition-all',
                          color === 'green' && 'bg-green-500',
                          color === 'yellow' && 'bg-yellow-500',
                          color === 'red' && 'bg-red-500',
                        )}
                        style={{ width: `${item.value}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Signals & Red Flags */}
        <div className="rounded-xl border border-border bg-card/50 p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-warning" />
            Signals & Red Flags
          </h2>
          <div className="space-y-3">
            {audit?.signals?.red_flags?.length > 0 ? (
              audit.signals.red_flags.map((flag: string, i: number) => (
                <div key={i} className="flex items-start gap-2 rounded-lg bg-red-500/5 border border-red-500/10 p-3">
                  <AlertTriangle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                  <span className="text-sm text-red-300">{flag}</span>
                </div>
              ))
            ) : null}
            {audit?.signals?.warnings?.length > 0 ? (
              audit.signals.warnings.map((warn: string, i: number) => (
                <div key={i} className="flex items-start gap-2 rounded-lg bg-yellow-500/5 border border-yellow-500/10 p-3">
                  <AlertTriangle className="h-4 w-4 text-yellow-400 shrink-0 mt-0.5" />
                  <span className="text-sm text-yellow-300">{warn}</span>
                </div>
              ))
            ) : null}
            {(!audit?.signals?.red_flags?.length && !audit?.signals?.warnings?.length) && (
              <div className="flex items-start gap-2 rounded-lg bg-green-500/5 border border-green-500/10 p-3">
                <CheckCircle className="h-4 w-4 text-green-400 shrink-0 mt-0.5" />
                <span className="text-sm text-green-300">No red flags detected. This creator appears authentic.</span>
              </div>
            )}

            {/* Key ratios */}
            {primaryPlatform && (
              <div className="mt-4 pt-4 border-t border-border space-y-2">
                <h3 className="text-sm font-medium text-muted-foreground mb-2">Key Ratios</h3>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">View-to-Follower</span>
                  <span className="font-mono">{primaryPlatform.followers > 0 ? ((primaryPlatform.avg_views / primaryPlatform.followers) * 100).toFixed(1) : '0.0'}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Following-to-Follower</span>
                  <span className={cn(
                    'font-mono',
                    primaryPlatform.followers > 0 && primaryPlatform.following / primaryPlatform.followers > 0.5 ? 'text-yellow-400' : ''
                  )}>
                    {primaryPlatform.followers > 0 ? ((primaryPlatform.following / primaryPlatform.followers) * 100).toFixed(2) : '0.00'}%
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Likes per Video</span>
                  <span className="font-mono">{formatNumber(Math.round(primaryPlatform.total_likes / Math.max(primaryPlatform.total_videos, 1)))}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Audience Demographics */}
      {creator.audience_demographics && (
        <div className="rounded-xl border border-border bg-card/50 p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Globe className="h-5 w-5 text-accent" />
            Audience Demographics
            <span className="text-xs font-normal text-muted bg-surface px-2 py-0.5 rounded-full">Estimated</span>
          </h2>
          <div className="grid sm:grid-cols-3 gap-6">
            {/* Gender Split */}
            <div>
              <div className="text-xs text-muted-foreground mb-2 uppercase tracking-wider">Gender</div>
              <div className="space-y-2">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>👨 Male</span>
                    <span className="font-bold">{creator.audience_demographics.gender?.male || 50}%</span>
                  </div>
                  <div className="h-2.5 rounded-full bg-surface overflow-hidden">
                    <div className="h-full rounded-full bg-blue-500" style={{ width: `${creator.audience_demographics.gender?.male || 50}%` }} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>👩 Female</span>
                    <span className="font-bold">{creator.audience_demographics.gender?.female || 50}%</span>
                  </div>
                  <div className="h-2.5 rounded-full bg-surface overflow-hidden">
                    <div className="h-full rounded-full bg-pink-500" style={{ width: `${creator.audience_demographics.gender?.female || 50}%` }} />
                  </div>
                </div>
              </div>
            </div>

            {/* Age Distribution */}
            <div>
              <div className="text-xs text-muted-foreground mb-2 uppercase tracking-wider">Age Range</div>
              <div className="space-y-1.5">
                {creator.audience_demographics.age_distribution && Object.entries(creator.audience_demographics.age_distribution).map(([range, pct]: [string, unknown]) => (
                  <div key={range} className="flex items-center gap-2">
                    <span className="text-xs w-10 text-muted-foreground">{range}</span>
                    <div className="flex-1 h-2 rounded-full bg-surface overflow-hidden">
                      <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="text-xs font-mono w-8 text-right">{pct as number}%</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Audience Location */}
            <div>
              <div className="text-xs text-muted-foreground mb-2 uppercase tracking-wider">Top Locations</div>
              <div className="space-y-1.5">
                {creator.audience_demographics.audience_location && Object.entries(creator.audience_demographics.audience_location).map(([country, pct]: [string, unknown]) => (
                  <div key={country} className="flex items-center gap-2">
                    <span className="text-xs w-10 text-muted-foreground">{country}</span>
                    <div className="flex-1 h-2 rounded-full bg-surface overflow-hidden">
                      <div className="h-full rounded-full bg-green-500" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="text-xs font-mono w-8 text-right">{pct as number}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Recent content */}
      {creator.content_samples?.length > 0 ? (
        <div className="rounded-xl border border-border bg-card/50 p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Video className="h-5 w-5 text-accent" />
            Recent Content
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-muted-foreground">
                  <th className="text-left py-2 pr-4 font-medium">Date</th>
                  <th className="text-right py-2 px-4 font-medium">Views</th>
                  <th className="text-right py-2 px-4 font-medium">Likes</th>
                  <th className="text-right py-2 px-4 font-medium">Comments</th>
                  <th className="text-right py-2 pl-4 font-medium">Shares</th>
                </tr>
              </thead>
              <tbody>
                {creator.content_samples.map((sample: any) => (
                  <tr key={sample.id} className="border-b border-border/50 hover:bg-card-hover/30">
                    <td className="py-2.5 pr-4 text-muted-foreground">{sample.posted_at}</td>
                    <td className="py-2.5 px-4 text-right font-mono">{formatNumber(sample.views)}</td>
                    <td className="py-2.5 px-4 text-right font-mono">{formatNumber(sample.likes)}</td>
                    <td className="py-2.5 px-4 text-right font-mono">{formatNumber(sample.comments)}</td>
                    <td className="py-2.5 pl-4 text-right font-mono">{formatNumber(sample.shares)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {/* Similar Creators */}
      {similarCreators.length > 0 && (
        <div className="rounded-xl border border-border bg-card/50 p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Users className="h-5 w-5 text-accent" />
            Similar Creators
            <span className="text-xs font-normal text-muted bg-surface px-2 py-0.5 rounded-full">
              {creator.country} • {creator.categories?.[0]}
            </span>
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {similarCreators.slice(0, 6).map((similar: any) => (
              <a
                key={similar.id}
                href={`/creator/${similar.id}`}
                className="block p-4 rounded-lg border border-border bg-surface hover:bg-card-hover transition-colors"
              >
                <div className="flex items-start gap-3">
                  <div className="w-12 h-12 rounded-full bg-card-hover flex items-center justify-center text-lg font-bold shrink-0">
                    {similar.name?.charAt(0)?.toUpperCase() || '?'}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-sm truncate">{similar.name}</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {formatNumber(similar.followers)} followers
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {countryFlags[similar.country]} {similar.platform}
                    </div>
                  </div>
                  {similar.heat_score && (
                    <div className="text-xs font-bold text-accent">
                      {similar.heat_score}
                    </div>
                  )}
                </div>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Search(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
    </svg>
  );
}
