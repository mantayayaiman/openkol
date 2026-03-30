'use client';

import { useState, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { COUNTRIES, CATEGORIES, formatNumber, formatEngagement, getHeatColor } from '@/lib/types';
import { cn } from '@/lib/cn';
import { Trophy, Crown, Medal, SlidersHorizontal } from 'lucide-react';
import Image from 'next/image';
import { ShortlistButton } from '@/components/ShortlistButton';

const PLATFORMS = [
  { value: 'tiktok', label: 'TikTok', icon: '♪' },
  { value: 'instagram', label: 'Instagram', icon: '📷' },
  { value: 'youtube', label: 'YouTube', icon: '▶' },
  { value: 'facebook', label: 'Facebook', icon: '📘' },
];

const SORT_OPTIONS = [
  { value: 'heat', label: '🔥 Heat Score' },
  { value: 'followers', label: 'Followers' },
  { value: 'engagement', label: 'Engagement Rate' },
  { value: 'views', label: 'Average Views' },
  { value: 'score', label: 'Authenticity Score' },
];

const countryNames: Record<string, string> = {
  MY: 'Malaysia', ID: 'Indonesia', TH: 'Thailand',
  PH: 'Philippines', VN: 'Vietnam', SG: 'Singapore',
};

const platformNames: Record<string, string> = {
  tiktok: 'TikTokers', instagram: 'Instagrammers', youtube: 'YouTubers',
};

const countryFlags: Record<string, string> = {
  MY: '🇲🇾', ID: '🇮🇩', TH: '🇹🇭', PH: '🇵🇭', VN: '🇻🇳', SG: '🇸🇬',
};

function buildPageTitle(country: string, platform: string, category: string, sort: string): string {
  if (sort === 'heat' && !country && !platform && !category) return '🔥 Hottest Creators Right Now';
  if (sort === 'engagement' && !country && !platform && !category) return 'Rising Creators This Week';
  if (sort === 'score' && !country && !platform && !category) return 'Highest Authenticity Scores';

  const parts: string[] = ['Top'];
  if (category) parts.push(category);
  if (platform && platformNames[platform]) {
    parts.push(platformNames[platform]);
  } else {
    parts.push('Creators');
  }
  if (country && countryNames[country]) {
    parts.push('in', countryNames[country]);
  }
  return parts.join(' ');
}

export default function RankingsPage() {
  return (
    <Suspense fallback={
      <div className="mx-auto max-w-6xl px-4 py-8">
        <div className="mb-8">
          <div className="h-10 w-64 rounded-lg bg-card/30 animate-pulse mb-2" />
          <div className="h-5 w-96 rounded-lg bg-card/30 animate-pulse" />
        </div>
        <div className="space-y-3">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="h-16 rounded-xl border border-border bg-card/30 animate-pulse" />
          ))}
        </div>
      </div>
    }>
      <RankingsContent />
    </Suspense>
  );
}

function RankingsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const country = searchParams.get('country') || '';
  const category = searchParams.get('category') || '';
  const platform = searchParams.get('platform') || '';
  const sort = searchParams.get('sort') || 'heat';
  const tier = searchParams.get('tier') || '';
  const [creators, setCreators] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const updateParam = useCallback((key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    router.push(`/rankings?${params.toString()}`);
  }, [searchParams, router]);

  const toggleParam = useCallback((key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (params.get(key) === value) {
      params.delete(key);
    } else {
      params.set(key, value);
    }
    router.push(`/rankings?${params.toString()}`);
  }, [searchParams, router]);

  useEffect(() => {
    const fetchRankings = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams({ sort, limit: '100' });
        if (country) params.set('country', country);
        if (category) params.set('category', category);
        if (platform) params.set('platform', platform);
        if (tier) params.set('tier', tier);

        const res = await fetch(`/api/creators?${params}`);
        const data = await res.json();
        setCreators(data.creators || []);
        setTotal(data.total || 0);
      } catch (e) {
        console.error('Failed to fetch rankings', e);
        setCreators([]);
      }
      setLoading(false);
    };
    fetchRankings();
  }, [country, category, platform, sort]);

  const pageTitle = buildPageTitle(country, platform, category, sort);

  const getRankIcon = (rank: number) => {
    if (rank === 1) return <Crown className="h-5 w-5 text-yellow-400" />;
    if (rank === 2) return <Medal className="h-5 w-5 text-gray-300" />;
    if (rank === 3) return <Medal className="h-5 w-5 text-amber-600" />;
    return <span className="text-sm font-mono text-muted w-5 text-center">{rank}</span>;
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2 flex items-center gap-3">
          <Trophy className="h-8 w-8 text-accent" />
          {pageTitle}
        </h1>
        <p className="text-muted-foreground">
          {!loading && total > 0
            ? `${total.toLocaleString()} creators · Ranked by ${sort === 'heat' ? '🔥 heat score' : sort === 'score' ? 'authenticity score' : sort === 'engagement' ? 'engagement rate' : sort === 'views' ? 'average views' : 'followers'}`
            : 'Top creators ranked by heat score, engagement, and reach'}
        </p>
      </div>

      {/* Filter pills */}
      <div className="space-y-4 mb-8">
        {/* Country */}
        <div>
          <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Country</div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => updateParam('country', '')}
              className={cn(
                'rounded-full px-4 py-2 text-sm font-medium transition-all duration-200',
                !country
                  ? 'bg-accent/15 text-accent border border-accent/30'
                  : 'border border-border bg-card/60 text-muted-foreground hover:border-accent/50 hover:text-foreground'
              )}
            >
              All
            </button>
            {COUNTRIES.map((c) => (
              <button
                key={c.value}
                onClick={() => toggleParam('country', c.value)}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium transition-all duration-200',
                  country === c.value
                    ? 'bg-accent text-white shadow-lg shadow-accent/25 scale-105'
                    : 'border border-border bg-card/60 text-foreground hover:border-accent/50 hover:bg-card'
                )}
              >
                <span>{c.flag}</span>
                {c.label}
              </button>
            ))}
          </div>
        </div>

        {/* Platform */}
        <div>
          <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Platform</div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => updateParam('platform', '')}
              className={cn(
                'rounded-full px-4 py-2 text-sm font-medium transition-all duration-200',
                !platform
                  ? 'bg-accent/15 text-accent border border-accent/30'
                  : 'border border-border bg-card/60 text-muted-foreground hover:border-accent/50 hover:text-foreground'
              )}
            >
              All
            </button>
            {PLATFORMS.map((p) => (
              <button
                key={p.value}
                onClick={() => toggleParam('platform', p.value)}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium transition-all duration-200',
                  platform === p.value
                    ? 'bg-accent text-white shadow-lg shadow-accent/25 scale-105'
                    : 'border border-border bg-card/60 text-foreground hover:border-accent/50 hover:bg-card'
                )}
              >
                <span>{p.icon}</span>
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Category */}
        <div>
          <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Category</div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => updateParam('category', '')}
              className={cn(
                'rounded-full px-4 py-2 text-sm font-medium transition-all duration-200',
                !category
                  ? 'bg-accent/15 text-accent border border-accent/30'
                  : 'border border-border bg-card/60 text-muted-foreground hover:border-accent/50 hover:text-foreground'
              )}
            >
              All
            </button>
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                onClick={() => toggleParam('category', cat)}
                className={cn(
                  'rounded-full px-4 py-2 text-sm font-medium transition-all duration-200',
                  category === cat
                    ? 'bg-accent text-white shadow-lg shadow-accent/25 scale-105'
                    : 'border border-border bg-card/60 text-muted-foreground hover:border-accent/50 hover:text-foreground'
                )}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Creator Tier */}
        <div>
          <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Creator Tier</div>
          <div className="flex flex-wrap gap-2">
            {[
              { value: '', label: 'All Tiers' },
              { value: 'mega', label: '👑 Mega (10M+)' },
              { value: 'macro', label: '🔥 Macro (1M–10M)' },
              { value: 'mid', label: '⭐ Mid-Tier (100K–1M)' },
              { value: 'micro', label: '🌱 Micro (10K–100K)' },
              { value: 'nano', label: '🫧 Nano (1K–10K)' },
            ].map((t) => (
              <button
                key={t.value}
                onClick={() => updateParam('tier', t.value)}
                className={cn(
                  'rounded-full px-4 py-2 text-sm font-medium transition-all duration-200',
                  tier === t.value || (!tier && !t.value)
                    ? t.value ? 'bg-accent text-white shadow-lg shadow-accent/25 scale-105' : 'bg-accent/15 text-accent border border-accent/30'
                    : 'border border-border bg-card/60 text-muted-foreground hover:border-accent/50 hover:text-foreground'
                )}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Sort */}
        <div>
          <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <SlidersHorizontal className="h-3 w-3" />
            Sort by
          </div>
          <div className="flex flex-wrap gap-2">
            {SORT_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => updateParam('sort', opt.value)}
                className={cn(
                  'rounded-full px-4 py-2 text-sm font-medium transition-all duration-200',
                  sort === opt.value
                    ? 'bg-purple-500/15 text-purple-400 border border-purple-500/30'
                    : 'border border-border bg-card/60 text-muted-foreground hover:border-purple-500/50 hover:text-foreground'
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Rankings table */}
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="h-16 rounded-xl border border-border bg-card/30 animate-pulse" />
          ))}
        </div>
      ) : creators.length === 0 ? (
        <div className="rounded-xl border border-border bg-card/30 p-12 text-center">
          <p className="text-muted-foreground text-lg">No creators found matching these filters.</p>
          <p className="text-muted text-sm mt-2">Try adjusting your country, platform, or category filters.</p>
        </div>
      ) : (
        <div className="rounded-xl border border-border bg-card/50 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface/50 text-muted-foreground">
                  <th className="text-left py-3 pl-4 pr-2 font-medium w-12">#</th>
                  <th className="text-left py-3 px-3 font-medium">Creator</th>
                  <th className="text-right py-3 px-3 font-medium">Followers</th>
                  <th className="text-right py-3 px-3 font-medium hidden sm:table-cell">Avg Views</th>
                  <th className="text-right py-3 px-3 font-medium hidden sm:table-cell">Engagement</th>
                  <th className="text-center py-3 px-3 font-medium hidden md:table-cell">Country</th>
                  <th className="text-center py-3 px-3 font-medium">🔥 Heat</th>
                  <th className="text-center py-3 pr-4 pl-2 font-medium w-10"></th>
                </tr>
              </thead>
              <tbody>
                {creators.map((creator, idx) => {
                  const heatColors = getHeatColor(creator.heat_score || 0);
                  return (
                    <tr
                      key={creator.id + '-' + idx}
                      className={cn(
                        'border-b border-border/50 hover:bg-card-hover/30 transition-colors cursor-pointer',
                        idx < 3 && 'bg-accent/[0.02]'
                      )}
                      onClick={() => router.push(`/creator/${creator.id}`)}
                    >
                      <td className="py-3 pl-4 pr-2">
                        {getRankIcon(idx + 1)}
                      </td>
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-3">
                          {creator.profile_image ? (
                            <Image
                              src={creator.profile_image}
                              alt={creator.name}
                              width={36}
                              height={36}
                              className="h-9 w-9 rounded-full bg-card-hover shrink-0"
                              unoptimized
                            />
                          ) : (
                            <div className="h-9 w-9 rounded-full bg-card-hover shrink-0 flex items-center justify-center text-sm font-bold text-muted">
                              {creator.name?.charAt(0)?.toUpperCase() || '?'}
                            </div>
                          )}
                          <div className="min-w-0">
                            <div className="font-medium truncate">{creator.name}</div>
                            <div className="text-xs text-muted-foreground">@{creator.username} · {creator.platform}</div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-3 text-right font-mono">{formatNumber(creator.followers)}</td>
                      <td className="py-3 px-3 text-right font-mono hidden sm:table-cell">{formatNumber(creator.avg_views)}</td>
                      <td className="py-3 px-3 text-right font-mono hidden sm:table-cell">{formatEngagement(creator.engagement_rate)}</td>
                      <td className="py-3 px-3 text-center text-lg hidden md:table-cell">{countryFlags[creator.country]}</td>
                      <td className="py-3 px-3 text-center">
                        <span className={cn(
                          'inline-flex items-center justify-center h-7 min-w-[2.5rem] rounded-full text-xs font-bold',
                          heatColors.bg,
                          heatColors.text,
                        )}>
                          {Math.round(creator.heat_score || 0)}
                        </span>
                      </td>
                      <td className="py-3 pr-4 pl-2 text-center">
                        <ShortlistButton
                          size="sm"
                          creator={{
                            id: creator.id,
                            name: creator.name,
                            username: creator.username,
                            platform: creator.platform,
                            profile_image: creator.profile_image || '',
                            followers: creator.followers || 0,
                            engagement_rate: creator.engagement_rate || 0,
                            heat_score: creator.heat_score || 0,
                            country: creator.country || '',
                            addedAt: '',
                          }}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
