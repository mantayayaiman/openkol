'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { Search, Shield, TrendingUp, Globe, BarChart3, Users, Zap, ArrowRight, Trophy, Crown, Medal, Flame, Heart } from 'lucide-react';
import { SearchAutocomplete } from '@/components/SearchAutocomplete';
import { ShortlistButton } from '@/components/ShortlistButton';
import { COUNTRIES, CATEGORIES, formatNumber, formatEngagement, getHeatColor } from '@/lib/types';
import { cn } from '@/lib/cn';

const PLATFORMS = [
  { value: 'tiktok', label: 'TikTok', icon: '♪' },
  { value: 'instagram', label: 'Instagram', icon: '📷' },
  { value: 'youtube', label: 'YouTube', icon: '▶' },
  { value: 'facebook', label: 'Facebook', icon: '📘' },
];

const countryFlags: Record<string, string> = {
  MY: '🇲🇾', ID: '🇮🇩', TH: '🇹🇭', PH: '🇵🇭', VN: '🇻🇳', SG: '🇸🇬',
};

export default function Home() {
  const router = useRouter();
  const [stats, setStats] = useState({ creators: 0, countries: 0, platforms: 4 });
  const [statsLoaded, setStatsLoaded] = useState(false);

  // Filter state
  const [selectedCountry, setSelectedCountry] = useState('');
  const [selectedPlatform, setSelectedPlatform] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedTier, setSelectedTier] = useState('');
  const [sortBy, setSortBy] = useState<'followers' | 'heat'>('followers');
  const [creators, setCreators] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  useEffect(() => {
    fetch('/api/stats').then(r => r.json()).then(d => { 
      if (d && d.creators !== undefined) { setStats(d); setStatsLoaded(true); }
    }).catch(() => {});
  }, []);

  const fetchCreators = useCallback(async () => {
    if (!selectedCountry) return;
    setLoading(true);
    setHasSearched(true);
    const params = new URLSearchParams({ sort: sortBy === 'heat' ? 'heat' : 'followers', limit: '20' });
    if (selectedCountry) params.set('country', selectedCountry);
    if (selectedPlatform) params.set('platform', selectedPlatform);
    if (selectedCategory) params.set('category', selectedCategory);
    if (selectedTier) params.set('tier', selectedTier);
    try {
      const res = await fetch(`/api/creators?${params}`);
      const data = await res.json();
      setCreators(data.creators || []);
    } catch {
      setCreators([]);
    }
    setLoading(false);
  }, [selectedCountry, selectedPlatform, selectedCategory, selectedTier, sortBy]);

  useEffect(() => {
    if (selectedCountry) fetchCreators();
  }, [fetchCreators, selectedCountry]);

  const handleCountryClick = (code: string) => {
    if (selectedCountry === code) {
      setSelectedCountry('');
      setSelectedPlatform('');
      setSelectedCategory('');
      setSelectedTier('');
      setCreators([]);
      setHasSearched(false);
    } else {
      setSelectedCountry(code);
      setSelectedPlatform('');
      setSelectedCategory('');
      setSelectedTier('');
    }
  };

  const handlePlatformClick = (value: string) => {
    setSelectedPlatform(selectedPlatform === value ? '' : value);
  };

  const handleCategoryClick = (cat: string) => {
    setSelectedCategory(selectedCategory === cat ? '' : cat);
  };

  const buildFilterTitle = () => {
    const parts: string[] = ['Top'];
    if (selectedCategory) parts.push(selectedCategory);
    if (selectedPlatform) {
      const names: Record<string, string> = { tiktok: 'TikTokers', instagram: 'Instagrammers', youtube: 'YouTubers', facebook: 'Facebook Creators' };
      parts.push(names[selectedPlatform] || 'Creators');
    } else {
      parts.push('Creators');
    }
    if (selectedCountry) {
      const names: Record<string, string> = { MY: 'Malaysia', ID: 'Indonesia', TH: 'Thailand', PH: 'Philippines', VN: 'Vietnam', SG: 'Singapore' };
      parts.push('in', names[selectedCountry] || selectedCountry);
    }
    return parts.join(' ');
  };

  const getRankIcon = (rank: number) => {
    if (rank === 1) return <Crown className="h-5 w-5 text-yellow-400" />;
    if (rank === 2) return <Medal className="h-5 w-5 text-gray-300" />;
    if (rank === 3) return <Medal className="h-5 w-5 text-amber-600" />;
    return <span className="text-sm font-mono text-muted w-5 text-center">{rank}</span>;
  };

  return (
    <div className="relative">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-accent/10 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute top-40 left-1/4 w-[400px] h-[400px] bg-purple-500/5 rounded-full blur-[100px] pointer-events-none" />

        <div className="relative mx-auto max-w-7xl px-4 pt-20 pb-12 sm:pt-28 sm:pb-16 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card/50 px-4 py-1.5 text-sm text-muted-foreground mb-8">
            <Zap className="h-3.5 w-3.5 text-accent" />
            <span>Creator Intelligence for Southeast Asia</span>
          </div>

          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight leading-[1.1] mb-6">
            Discover. Audit.
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent via-purple-400 to-pink-400">
              Trust.
            </span>
          </h1>

          <p className="mx-auto max-w-2xl text-lg sm:text-xl text-muted-foreground mb-8 leading-relaxed">
            The open intelligence platform for creator partnerships across TikTok, Instagram, and YouTube.
          </p>
        </div>
      </section>

      {/* Interactive Discovery Flow */}
      <section className="relative py-8 sm:py-12">
        <div className="mx-auto max-w-5xl px-4">
          <div className="text-center mb-8">
            <h2 className="text-2xl sm:text-3xl font-bold mb-2">
              Explore Top Creators
            </h2>
            <p className="text-muted-foreground text-base">
              Select a country to start discovering creators
            </p>
          </div>

          {/* Step 1: Country Pills */}
          <div className="mb-4">
            <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-2">
              <span className="h-5 w-5 rounded-full bg-accent/20 text-accent text-xs flex items-center justify-center font-bold">1</span>
              Country
            </div>
            <div className="flex flex-wrap gap-2">
              {COUNTRIES.map((c) => (
                <button
                  key={c.value}
                  onClick={() => handleCountryClick(c.value)}
                  className={cn(
                    'inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition-all duration-200',
                    selectedCountry === c.value
                      ? 'bg-accent text-white shadow-lg shadow-accent/25 scale-105'
                      : 'border border-border bg-card/60 text-foreground hover:border-accent/50 hover:bg-card'
                  )}
                >
                  <span className="text-lg">{c.flag}</span>
                  {c.label}
                </button>
              ))}
            </div>
          </div>

          {/* Step 2: Platform Pills (shown after country selected) */}
          {selectedCountry && (
            <div className="mb-4 animate-fade-slide-in">
              <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-2">
                <span className="h-5 w-5 rounded-full bg-accent/20 text-accent text-xs flex items-center justify-center font-bold">2</span>
                Platform
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setSelectedPlatform('')}
                  className={cn(
                    'inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition-all duration-200',
                    !selectedPlatform
                      ? 'bg-accent/15 text-accent border border-accent/30'
                      : 'border border-border bg-card/60 text-foreground hover:border-accent/50'
                  )}
                >
                  All
                </button>
                {PLATFORMS.map((p) => (
                  <button
                    key={p.value}
                    onClick={() => handlePlatformClick(p.value)}
                    className={cn(
                      'inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition-all duration-200',
                      selectedPlatform === p.value
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
          )}

          {/* Step 3: Category Pills (shown after country selected) */}
          {selectedCountry && (
            <div className="mb-6 animate-fade-slide-in" style={{ animationDelay: '100ms' }}>
              <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-2">
                <span className="h-5 w-5 rounded-full bg-accent/20 text-accent text-xs flex items-center justify-center font-bold">3</span>
                Category
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setSelectedCategory('')}
                  className={cn(
                    'inline-flex items-center rounded-full px-4 py-2 text-sm font-medium transition-all duration-200',
                    !selectedCategory
                      ? 'bg-accent/15 text-accent border border-accent/30'
                      : 'border border-border bg-card/60 text-foreground hover:border-accent/50'
                  )}
                >
                  All Categories
                </button>
                {CATEGORIES.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => handleCategoryClick(cat)}
                    className={cn(
                      'inline-flex items-center rounded-full px-4 py-2 text-sm font-medium transition-all duration-200',
                      selectedCategory === cat
                        ? 'bg-accent text-white shadow-lg shadow-accent/25 scale-105'
                        : 'border border-border bg-card/60 text-muted-foreground hover:border-accent/50 hover:text-foreground'
                    )}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 4: Creator Tier / Follower Range (shown after country selected) */}
          {selectedCountry && (
            <div className="mb-6 animate-fade-slide-in" style={{ animationDelay: '200ms' }}>
              <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-2">
                <span className="h-5 w-5 rounded-full bg-accent/20 text-accent text-xs flex items-center justify-center font-bold">4</span>
                Creator Tier
              </div>
              <div className="flex flex-wrap gap-2">
                {[
                  { value: '', label: 'All Tiers', emoji: '' },
                  { value: 'mega', label: 'Mega (10M+)', emoji: '👑' },
                  { value: 'macro', label: 'Macro (1M–10M)', emoji: '🔥' },
                  { value: 'mid', label: 'Mid-Tier (100K–1M)', emoji: '⭐' },
                  { value: 'micro', label: 'Micro (10K–100K)', emoji: '🌱' },
                  { value: 'nano', label: 'Nano (1K–10K)', emoji: '🫧' },
                ].map((tier) => (
                  <button
                    key={tier.value}
                    onClick={() => setSelectedTier(selectedTier === tier.value ? '' : tier.value)}
                    className={cn(
                      'inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium transition-all duration-200',
                      (tier.value === '' ? !selectedTier : selectedTier === tier.value)
                        ? tier.value === '' ? 'bg-accent/15 text-accent border border-accent/30' : 'bg-accent text-white shadow-lg shadow-accent/25 scale-105'
                        : 'border border-border bg-card/60 text-muted-foreground hover:border-accent/50 hover:text-foreground'
                    )}
                  >
                    {tier.emoji && <span>{tier.emoji}</span>}
                    {tier.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Results */}
          {hasSearched && (
            <div className="animate-fade-slide-up">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg sm:text-xl font-bold flex items-center gap-2">
                  <Trophy className="h-5 w-5 text-accent" />
                  {buildFilterTitle()}
                </h3>
                <div className="flex items-center gap-2">
                  {/* Sort toggle */}
                  <div className="flex rounded-full border border-border bg-card/60 p-0.5">
                    <button
                      onClick={() => setSortBy('followers')}
                      className={cn(
                        'rounded-full px-3 py-1 text-xs font-medium transition-all',
                        sortBy === 'followers' ? 'bg-accent text-white' : 'text-muted-foreground hover:text-foreground'
                      )}
                    >
                      👥 Top
                    </button>
                    <button
                      onClick={() => setSortBy('heat')}
                      className={cn(
                        'rounded-full px-3 py-1 text-xs font-medium transition-all',
                        sortBy === 'heat' ? 'bg-orange-500 text-white' : 'text-muted-foreground hover:text-foreground'
                      )}
                    >
                      🔥 Trending
                    </button>
                  </div>
                  <Link
                    href={`/rankings?country=${selectedCountry}${selectedPlatform ? `&platform=${selectedPlatform}` : ''}${selectedCategory ? `&category=${encodeURIComponent(selectedCategory)}` : ''}`}
                    className="text-sm text-accent hover:underline flex items-center gap-1"
                  >
                    View all <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </div>

              {loading ? (
                <div className="space-y-2">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="h-14 rounded-xl border border-border bg-card/30 animate-pulse" />
                  ))}
                </div>
              ) : creators.length === 0 ? (
                <div className="rounded-xl border border-border bg-card/30 p-8 text-center">
                  <p className="text-muted-foreground">No creators found for this combination.</p>
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
                          <th className="text-center py-3 px-3 font-medium hidden sm:table-cell">🔥 Heat</th>
                          <th className="text-center py-3 pr-4 pl-2 font-medium w-10"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {creators.slice(0, 20).map((creator, idx) => {
                          const heatColors = getHeatColor(creator.heat_score || 0);
                          return (
                            <tr
                              key={`${creator.id}-${creator.platform}-${idx}`}
                              className={cn(
                                'border-b border-border/50 hover:bg-card-hover/30 transition-colors cursor-pointer',
                                idx < 3 && 'bg-accent/[0.02]'
                              )}
                              onClick={() => router.push(`/creator/${creator.id}`)}
                            >
                              <td className="py-3 pl-4 pr-2">{getRankIcon(idx + 1)}</td>
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
                              <td className="py-3 px-3 text-center hidden sm:table-cell">
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
          )}
        </div>
      </section>

      {/* Search section */}
      <section className="py-12 sm:py-16">
        <div className="mx-auto max-w-7xl px-4 text-center">
          <h2 className="text-xl sm:text-2xl font-bold mb-6">Or search for any creator</h2>
          <div className="mx-auto max-w-2xl">
            <SearchAutocomplete />
          </div>
        </div>
      </section>

      {/* Stats bar — dynamic */}
      <section className="border-y border-border bg-card/30">
        <div className="mx-auto max-w-7xl px-4 py-8 grid grid-cols-2 sm:grid-cols-4 gap-8">
          {[
            { value: statsLoaded && stats.creators ? `${stats.creators.toLocaleString()}+` : '...', label: 'Creators tracked', icon: Users },
            { value: statsLoaded && stats.countries ? stats.countries.toString() : '...', label: 'Countries', icon: Globe },
            { value: '15', label: 'Categories', icon: BarChart3 },
            { value: statsLoaded && stats.platforms ? stats.platforms.toString() : '...', label: 'Platforms', icon: TrendingUp },
          ].map((stat) => (
            <div key={stat.label} className="text-center">
              <stat.icon className="mx-auto h-5 w-5 text-accent mb-2" />
              <div className="text-2xl sm:text-3xl font-bold">{stat.value}</div>
              <div className="text-sm text-muted-foreground">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-7xl px-4 py-20 sm:py-28">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">Creator intelligence, reimagined.</h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            Go beyond vanity metrics. Understand the real value behind every creator partnership.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {[
            { icon: Flame, title: '🔥 Heat Score', desc: 'Real-time virality metric (0-100) based on recent posting frequency, view velocity, engagement, and growth rate.', color: 'text-orange-400' },
            { icon: BarChart3, title: 'Deep Analytics', desc: 'Engagement rates, view-to-follower ratios, posting frequency, and content performance breakdowns.', color: 'text-blue-400' },
            { icon: TrendingUp, title: 'Growth Tracking', desc: 'Monitor follower growth trends and detect suspicious spikes that signal bought followers.', color: 'text-purple-400' },
            { icon: Globe, title: 'SEA Coverage', desc: 'Comprehensive coverage of Malaysia, Indonesia, Thailand, Philippines, Vietnam, and Singapore.', color: 'text-amber-400' },
            { icon: Users, title: 'Cross-Platform', desc: 'Unified profiles across TikTok, Instagram, and YouTube — one view per creator.', color: 'text-pink-400' },
            { icon: Search, title: 'On-Demand Lookup', desc: 'Paste any creator URL for instant analysis. No pre-scraping needed.', color: 'text-cyan-400' },
          ].map((feature) => (
            <div
              key={feature.title}
              className="group rounded-xl border border-border bg-card/50 p-6 hover:border-accent/30 hover:bg-card transition-all"
            >
              <feature.icon className={`h-8 w-8 ${feature.color} mb-4`} />
              <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{feature.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border bg-card/30">
        <div className="mx-auto max-w-7xl px-4 py-20 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">Ready to find authentic creators?</h2>
          <p className="text-muted-foreground text-lg mb-8 max-w-xl mx-auto">
            Start browsing creators or paste a profile URL for instant analysis.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a href="/rankings" className="rounded-lg bg-accent px-8 py-3 text-base font-medium text-white hover:bg-accent-hover transition-colors">
              Explore Rankings
            </a>
            <a href="/lookup" className="rounded-lg border border-border px-8 py-3 text-base font-medium text-foreground hover:bg-card transition-colors">
              Lookup a Creator
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="mx-auto max-w-7xl px-4 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold">Kol<span className="text-accent">Buff</span></span>
          </div>
          <p className="text-sm text-muted">© 2025 KolBuff. Creator intelligence for Southeast Asia.</p>
        </div>
      </footer>
    </div>
  );
}
