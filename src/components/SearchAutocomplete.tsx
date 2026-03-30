'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { Search } from 'lucide-react';
import { formatNumber } from '@/lib/types';

interface Suggestion {
  id: number;
  name: string;
  username: string;
  platform: string;
  country: string;
  profile_image: string;
  followers: number;
}

const platformIcons: Record<string, string> = {
  tiktok: '♪',
  instagram: '📷',
  youtube: '▶',
  facebook: '📘',
};

const countryFlags: Record<string, string> = {
  MY: '🇲🇾', ID: '🇮🇩', TH: '🇹🇭', PH: '🇵🇭', VN: '🇻🇳', SG: '🇸🇬',
  US: '🇺🇸', BR: '🇧🇷', JP: '🇯🇵', KR: '🇰🇷', GB: '🇬🇧', IN: '🇮🇳',
  SEA: '🌏', CN: '🇨🇳', TW: '🇹🇼', AU: '🇦🇺', DE: '🇩🇪', FR: '🇫🇷',
  MX: '🇲🇽', RU: '🇷🇺', LATAM: '🌎', AE: '🇦🇪',
};

export function SearchAutocomplete() {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  const fetchSuggestions = useCallback(async (q: string) => {
    if (q.length < 2) {
      setSuggestions([]);
      setShowDropdown(false);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`/api/suggest?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      setSuggestions(data.suggestions || []);
      setShowDropdown(data.suggestions?.length > 0);
    } catch {
      setSuggestions([]);
    }
    setLoading(false);
  }, []);

  const handleInputChange = (value: string) => {
    setQuery(value);
    setSelectedIndex(-1);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchSuggestions(value), 250);
  };

  const handleSelect = (suggestion: Suggestion) => {
    setShowDropdown(false);
    setQuery('');
    router.push(`/creator/${suggestion.id}`);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedIndex >= 0 && suggestions[selectedIndex]) {
      handleSelect(suggestions[selectedIndex]);
    } else if (query.trim()) {
      setShowDropdown(false);
      router.push(`/browse?q=${encodeURIComponent(query.trim())}`);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showDropdown) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => Math.min(prev + 1, suggestions.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => Math.max(prev - 1, -1));
    } else if (e.key === 'Escape') {
      setShowDropdown(false);
    }
  };

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div ref={containerRef} className="relative w-full">
      <form onSubmit={handleSearch}>
        <div className="relative group">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-accent via-purple-500 to-pink-500 rounded-2xl opacity-20 group-hover:opacity-30 blur transition-opacity" />
          <div className="relative flex items-center bg-card border border-border rounded-xl overflow-hidden">
            <Search className="ml-5 h-5 w-5 text-muted shrink-0" />
            <input
              type="text"
              placeholder="Search creators, paste a TikTok/IG/YT URL..."
              value={query}
              onChange={(e) => handleInputChange(e.target.value)}
              onFocus={() => suggestions.length > 0 && setShowDropdown(true)}
              onKeyDown={handleKeyDown}
              className="flex-1 bg-transparent px-4 py-4 text-base sm:text-lg outline-none placeholder:text-muted"
              autoComplete="off"
            />
            <button
              type="submit"
              className="m-2 rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white hover:bg-accent-hover transition-colors shrink-0"
            >
              Search
            </button>
          </div>
        </div>
      </form>

      {/* Dropdown */}
      {showDropdown && (
        <div className="absolute z-50 top-full left-0 right-0 mt-2 rounded-xl border border-border bg-card shadow-2xl shadow-black/20 overflow-hidden">
          {suggestions.map((s, idx) => (
            <button
              key={`${s.id}-${idx}`}
              onClick={() => handleSelect(s)}
              onMouseEnter={() => setSelectedIndex(idx)}
              className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors ${
                idx === selectedIndex ? 'bg-accent/10' : 'hover:bg-card-hover/50'
              } ${idx > 0 ? 'border-t border-border/50' : ''}`}
            >
              {s.profile_image ? (
                <Image
                  src={s.profile_image}
                  alt={s.name}
                  width={36}
                  height={36}
                  className="h-9 w-9 rounded-full bg-card-hover shrink-0"
                  unoptimized
                />
              ) : (
                <div className="h-9 w-9 rounded-full bg-card-hover shrink-0 flex items-center justify-center text-sm font-bold text-muted">
                  {s.name?.charAt(0)?.toUpperCase() || '?'}
                </div>
              )}
              <div className="min-w-0 flex-1">
                <div className="font-medium text-sm truncate">{s.name}</div>
                <div className="text-xs text-muted-foreground">
                  @{s.username} · {platformIcons[s.platform] || ''} {s.platform} · {formatNumber(s.followers)} followers
                </div>
              </div>
              <div className="text-lg shrink-0">{countryFlags[s.country] || ''}</div>
            </button>
          ))}
          {query.trim() && (
            <button
              onClick={() => {
                setShowDropdown(false);
                router.push(`/browse?q=${encodeURIComponent(query.trim())}`);
              }}
              className="w-full flex items-center gap-3 px-4 py-3 text-left border-t border-border/50 hover:bg-card-hover/50 transition-colors text-sm text-muted-foreground"
            >
              <Search className="h-4 w-4 shrink-0" />
              <span>Search all results for &quot;{query}&quot;</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}
