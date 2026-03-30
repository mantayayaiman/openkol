'use client';

import { useState, useEffect, useCallback } from 'react';
import { Heart, Download, Trash2, Users, TrendingUp, Flame } from 'lucide-react';
import { getShortlist, removeFromShortlist, clearShortlist, exportShortlistCSV, ShortlistItem } from '@/lib/shortlist';
import { formatNumber, formatEngagement, getHeatColor } from '@/lib/types';
import { cn } from '@/lib/cn';
import Image from 'next/image';
import Link from 'next/link';

function ProfileImage({ src, name }: { src: string; name: string }) {
  const [error, setError] = useState(false);
  if (!src || error) {
    return (
      <div className="h-10 w-10 rounded-full bg-card-hover flex items-center justify-center text-sm font-bold text-muted shrink-0">
        {name?.charAt(0)?.toUpperCase() || '?'}
      </div>
    );
  }
  return (
    <Image
      src={src}
      alt={name}
      width={40}
      height={40}
      className="h-10 w-10 rounded-full bg-card-hover shrink-0 object-cover"
      unoptimized
      onError={() => setError(true)}
    />
  );
}

export default function ShortlistPage() {
  const [items, setItems] = useState<ShortlistItem[]>([]);

  const refresh = useCallback(() => {
    setItems(getShortlist());
  }, []);

  useEffect(() => {
    refresh();
    window.addEventListener('shortlist-change', refresh);
    return () => window.removeEventListener('shortlist-change', refresh);
  }, [refresh]);

  const handleRemove = (id: number) => {
    removeFromShortlist(id);
  };

  const handleClear = () => {
    if (confirm('Remove all creators from your shortlist?')) {
      clearShortlist();
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Heart className="h-8 w-8 text-pink-400" />
            My Shortlist
          </h1>
          <p className="text-muted-foreground mt-1">
            {items.length} creator{items.length !== 1 ? 's' : ''} saved
          </p>
        </div>
        {items.length > 0 && (
          <div className="flex gap-2">
            <button
              onClick={() => exportShortlistCSV()}
              className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white hover:bg-accent-hover transition-colors"
            >
              <Download className="h-4 w-4" />
              Export CSV
            </button>
            <button
              onClick={handleClear}
              className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-muted-foreground hover:text-red-400 hover:border-red-500/30 transition-colors"
            >
              <Trash2 className="h-4 w-4" />
              Clear
            </button>
          </div>
        )}
      </div>

      {items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-card/30 p-16 text-center">
          <Heart className="h-12 w-12 text-muted mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">No creators saved yet</h3>
          <p className="text-sm text-muted-foreground mb-6 max-w-md mx-auto">
            Browse creators and click the heart icon to add them to your shortlist. You can then export them as CSV for your campaigns.
          </p>
          <Link
            href="/browse"
            className="inline-flex items-center gap-2 rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white hover:bg-accent-hover transition-colors"
          >
            Browse Creators
          </Link>
        </div>
      ) : (
        <div className="rounded-xl border border-border bg-card/50 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface/50 text-muted-foreground">
                  <th className="text-left py-3 pl-4 pr-3 font-medium">Creator</th>
                  <th className="text-right py-3 px-3 font-medium">Followers</th>
                  <th className="text-right py-3 px-3 font-medium hidden sm:table-cell">Engagement</th>
                  <th className="text-center py-3 px-3 font-medium">🔥 Heat</th>
                  <th className="text-center py-3 pr-4 pl-3 font-medium w-12"></th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const heatColors = getHeatColor(item.heat_score || 0);
                  return (
                    <tr key={item.id} className="border-b border-border/50 hover:bg-card-hover/30 transition-colors">
                      <td className="py-3 pl-4 pr-3">
                        <Link href={`/creator/${item.id}`} className="flex items-center gap-3 hover:text-accent transition-colors">
                          <ProfileImage src={item.profile_image} name={item.name} />
                          <div className="min-w-0">
                            <div className="font-medium truncate">{item.name}</div>
                            <div className="text-xs text-muted-foreground">@{item.username} · {item.platform}</div>
                          </div>
                        </Link>
                      </td>
                      <td className="py-3 px-3 text-right font-mono">{formatNumber(item.followers)}</td>
                      <td className="py-3 px-3 text-right font-mono hidden sm:table-cell">{formatEngagement(item.engagement_rate)}</td>
                      <td className="py-3 px-3 text-center">
                        <span className={cn(
                          'inline-flex items-center justify-center h-7 min-w-[2.5rem] rounded-full text-xs font-bold',
                          heatColors.bg, heatColors.text,
                        )}>
                          {Math.round(item.heat_score || 0)}
                        </span>
                      </td>
                      <td className="py-3 pr-4 pl-3 text-center">
                        <button
                          onClick={() => handleRemove(item.id)}
                          className="p-1.5 rounded-full text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors"
                          title="Remove from shortlist"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
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
