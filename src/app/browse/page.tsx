'use client';

import { useState, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { CreatorCard } from '@/components/CreatorCard';
import { COUNTRIES, PLATFORMS, CATEGORIES } from '@/lib/types';
import { Search, SlidersHorizontal, X, ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/cn';
import { formatNumber } from '@/lib/types';

function BrowseContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const [creators, setCreators] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showFilters, setShowFilters] = useState(false);

  const country = searchParams.get('country') || '';
  const selectedCountries = country ? country.split(',') : [];
  const platform = searchParams.get('platform') || '';
  const category = searchParams.get('category') || '';
  const query = searchParams.get('q') || '';
  const sort = searchParams.get('sort') || 'followers';
  const minFollowers = searchParams.get('min_followers') || '';
  const maxFollowers = searchParams.get('max_followers') || '';
  const minEr = searchParams.get('min_er') || '';
  const maxEr = searchParams.get('max_er') || '';
  const page = parseInt(searchParams.get('page') || '1');
  const perPage = 50;

  const updateParam = useCallback((key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    // Reset to page 1 when changing filters (not when changing page itself)
    if (key !== 'page') {
      params.delete('page');
    }
    router.push(`/browse?${params.toString()}`);
  }, [searchParams, router]);

  const toggleCountry = useCallback((countryCode: string) => {
    const isSelected = selectedCountries.includes(countryCode);
    let newCountries: string[];
    
    if (isSelected) {
      // Remove country
      newCountries = selectedCountries.filter(c => c !== countryCode);
    } else {
      // Add country
      newCountries = [...selectedCountries, countryCode];
    }
    
    const countryParam = newCountries.join(',');
    updateParam('country', countryParam);
  }, [selectedCountries, updateParam]);

  useEffect(() => {
    const fetchCreators = async () => {
      setLoading(true);
      const params = new URLSearchParams();
      if (country) params.set('country', country);
      if (platform) params.set('platform', platform);
      if (category) params.set('category', category);
      if (query) params.set('q', query);
      if (sort) params.set('sort', sort);
      if (minFollowers) params.set('min_followers', minFollowers);
      if (maxFollowers) params.set('max_followers', maxFollowers);
      if (minEr) params.set('min_er', minEr);
      if (maxEr) params.set('max_er', maxEr);
      params.set('limit', perPage.toString());
      params.set('offset', ((page - 1) * perPage).toString());

      try {
        const res = await fetch(`/api/creators?${params.toString()}`);
        const data = await res.json();
        setCreators(data.creators || []);
        setTotal(data.total || 0);
      } catch (err) {
        console.error('Failed to fetch creators:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchCreators();
  }, [country, platform, category, query, sort, minFollowers, maxFollowers, minEr, maxEr, page]);

  const activeFilters = [country, platform, category, minFollowers, maxFollowers, minEr, maxEr].filter(Boolean).length;
  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Browse Creators</h1>
        <p className="text-muted-foreground">
          Discover and analyze creators across Southeast Asia
        </p>
      </div>

      {/* Search & Filter bar */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted" />
          <input
            type="text"
            placeholder="Search by name, username, or bio..."
            defaultValue={query}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                updateParam('q', (e.target as HTMLInputElement).value);
              }
            }}
            className="w-full rounded-lg border border-border bg-card pl-10 pr-4 py-2.5 text-sm outline-none focus:border-accent/50 transition-colors placeholder:text-muted"
          />
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={cn(
            'flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors',
            showFilters || activeFilters > 0
              ? 'border-accent/50 bg-accent/10 text-accent'
              : 'border-border bg-card text-muted-foreground hover:text-foreground'
          )}
        >
          <SlidersHorizontal className="h-4 w-4" />
          Filters
          {activeFilters > 0 && (
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-accent text-xs text-white">
              {activeFilters}
            </span>
          )}
        </button>

        {/* Sort dropdown */}
        <select
          value={sort}
          onChange={(e) => updateParam('sort', e.target.value)}
          className="rounded-lg border border-border bg-card px-4 py-2.5 text-sm outline-none focus:border-accent/50 transition-colors text-foreground"
        >
          <option value="followers">Most Followers</option>
          <option value="heat">🔥 Heat Score</option>
          <option value="engagement">Highest Engagement</option>
          <option value="views">Most Views</option>
          <option value="score">Authenticity Score</option>
        </select>
      </div>

      {/* Filters panel */}
      {showFilters && (
        <div className="mb-6 rounded-xl border border-border bg-card/50 p-5 space-y-5">
          {/* Countries */}
          <div>
            <h3 className="text-sm font-medium mb-3 text-muted-foreground">
              Country
              {selectedCountries.length > 0 && (
                <span className="ml-1 text-xs bg-accent/20 text-accent px-1.5 py-0.5 rounded-full">
                  {selectedCountries.length}
                </span>
              )}
            </h3>
            <div className="flex flex-wrap gap-2">
              {COUNTRIES.map((c) => (
                <button
                  key={c.value}
                  onClick={() => toggleCountry(c.value)}
                  className={cn(
                    'rounded-full border px-3 py-1.5 text-sm transition-colors',
                    selectedCountries.includes(c.value)
                      ? 'border-accent bg-accent/10 text-accent'
                      : 'border-border text-muted-foreground hover:border-accent/30 hover:text-foreground'
                  )}
                >
                  {c.flag} {c.label}
                </button>
              ))}
            </div>
          </div>

          {/* Platforms */}
          <div>
            <h3 className="text-sm font-medium mb-3 text-muted-foreground">Platform</h3>
            <div className="flex flex-wrap gap-2">
              {PLATFORMS.map((p) => (
                <button
                  key={p.value}
                  onClick={() => updateParam('platform', platform === p.value ? '' : p.value)}
                  className={cn(
                    'rounded-full border px-3 py-1.5 text-sm transition-colors',
                    platform === p.value
                      ? 'border-accent bg-accent/10 text-accent'
                      : 'border-border text-muted-foreground hover:border-accent/30 hover:text-foreground'
                  )}
                >
                  {p.value === 'tiktok' ? '♪' : p.value === 'youtube' ? '▶' : '📷'} {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Categories */}
          <div>
            <h3 className="text-sm font-medium mb-3 text-muted-foreground">Category</h3>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat}
                  onClick={() => updateParam('category', category === cat ? '' : cat)}
                  className={cn(
                    'rounded-full border px-3 py-1.5 text-sm transition-colors',
                    category === cat
                      ? 'border-accent bg-accent/10 text-accent'
                      : 'border-border text-muted-foreground hover:border-accent/30 hover:text-foreground'
                  )}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          {/* Follower Range */}
          <div>
            <h3 className="text-sm font-medium mb-3 text-muted-foreground">Follower Range</h3>
            <div className="flex items-center gap-3">
              <input
                type="text"
                placeholder="Min (e.g. 10000)"
                defaultValue={minFollowers}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') updateParam('min_followers', (e.target as HTMLInputElement).value);
                }}
                onBlur={(e) => updateParam('min_followers', e.target.value)}
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm outline-none focus:border-accent/50 transition-colors placeholder:text-muted"
              />
              <span className="text-muted-foreground text-sm">to</span>
              <input
                type="text"
                placeholder="Max (e.g. 1000000)"
                defaultValue={maxFollowers}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') updateParam('max_followers', (e.target as HTMLInputElement).value);
                }}
                onBlur={(e) => updateParam('max_followers', e.target.value)}
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm outline-none focus:border-accent/50 transition-colors placeholder:text-muted"
              />
            </div>
            <div className="flex gap-2 mt-2">
              {[
                { label: 'Nano (1K-10K)', min: '1000', max: '10000' },
                { label: 'Micro (10K-100K)', min: '10000', max: '100000' },
                { label: 'Mid (100K-1M)', min: '100000', max: '1000000' },
                { label: 'Macro (1M+)', min: '1000000', max: '' },
              ].map((preset) => (
                <button
                  key={preset.label}
                  onClick={() => {
                    const params = new URLSearchParams(searchParams.toString());
                    if (preset.min) params.set('min_followers', preset.min); else params.delete('min_followers');
                    if (preset.max) params.set('max_followers', preset.max); else params.delete('max_followers');
                    params.delete('page');
                    router.push(`/browse?${params.toString()}`);
                  }}
                  className={cn(
                    'rounded-full border px-2.5 py-1 text-xs transition-colors',
                    minFollowers === preset.min && maxFollowers === preset.max
                      ? 'border-accent bg-accent/10 text-accent'
                      : 'border-border text-muted-foreground hover:border-accent/30 hover:text-foreground'
                  )}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          {/* Engagement Rate */}
          <div>
            <h3 className="text-sm font-medium mb-3 text-muted-foreground">Engagement Rate (%)</h3>
            <div className="flex items-center gap-3">
              <input
                type="text"
                placeholder="Min (e.g. 1)"
                defaultValue={minEr}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') updateParam('min_er', (e.target as HTMLInputElement).value);
                }}
                onBlur={(e) => updateParam('min_er', e.target.value)}
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm outline-none focus:border-accent/50 transition-colors placeholder:text-muted"
              />
              <span className="text-muted-foreground text-sm">to</span>
              <input
                type="text"
                placeholder="Max (e.g. 10)"
                defaultValue={maxEr}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') updateParam('max_er', (e.target as HTMLInputElement).value);
                }}
                onBlur={(e) => updateParam('max_er', e.target.value)}
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm outline-none focus:border-accent/50 transition-colors placeholder:text-muted"
              />
            </div>
            <div className="flex gap-2 mt-2">
              {[
                { label: 'Low (<1%)', min: '', max: '1' },
                { label: 'Average (1-3%)', min: '1', max: '3' },
                { label: 'Good (3-6%)', min: '3', max: '6' },
                { label: 'Viral (6%+)', min: '6', max: '' },
              ].map((preset) => (
                <button
                  key={preset.label}
                  onClick={() => {
                    const params = new URLSearchParams(searchParams.toString());
                    if (preset.min) params.set('min_er', preset.min); else params.delete('min_er');
                    if (preset.max) params.set('max_er', preset.max); else params.delete('max_er');
                    params.delete('page');
                    router.push(`/browse?${params.toString()}`);
                  }}
                  className={cn(
                    'rounded-full border px-2.5 py-1 text-xs transition-colors',
                    minEr === preset.min && maxEr === preset.max
                      ? 'border-accent bg-accent/10 text-accent'
                      : 'border-border text-muted-foreground hover:border-accent/30 hover:text-foreground'
                  )}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          {/* Clear filters */}
          {activeFilters > 0 && (
            <button
              onClick={() => router.push('/browse')}
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="h-3.5 w-3.5" />
              Clear all filters
            </button>
          )}
        </div>
      )}

      {/* Results count */}
      <div className="mb-4 text-sm text-muted-foreground">
        {loading ? 'Loading...' : `${total} creator${total !== 1 ? 's' : ''} found`}
      </div>

      {/* Creator grid */}
      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-48 rounded-xl border border-border bg-card/30 animate-pulse" />
          ))}
        </div>
      ) : creators.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Search className="h-12 w-12 text-muted mb-4" />
          <h3 className="text-lg font-medium mb-2">No creators found</h3>
          <p className="text-sm text-muted-foreground max-w-md">
            Try adjusting your filters or search query to find more creators.
          </p>
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            {creators.map((creator) => (
              <CreatorCard key={creator.id} creator={creator} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-8 flex items-center justify-center gap-2">
              <button
                onClick={() => updateParam('page', (page - 1).toString())}
                disabled={page <= 1}
                className={cn(
                  'flex items-center gap-1 rounded-lg border px-3 py-2 text-sm font-medium transition-colors',
                  page <= 1
                    ? 'border-border text-muted cursor-not-allowed'
                    : 'border-border bg-card text-foreground hover:border-accent/50'
                )}
              >
                <ChevronLeft className="h-4 w-4" />
                Prev
              </button>
              <span className="px-4 py-2 text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => updateParam('page', (page + 1).toString())}
                disabled={page >= totalPages}
                className={cn(
                  'flex items-center gap-1 rounded-lg border px-3 py-2 text-sm font-medium transition-colors',
                  page >= totalPages
                    ? 'border-border text-muted cursor-not-allowed'
                    : 'border-border bg-card text-foreground hover:border-accent/50'
                )}
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function BrowsePage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-7xl px-4 py-8">Loading...</div>}>
      <BrowseContent />
    </Suspense>
  );
}
