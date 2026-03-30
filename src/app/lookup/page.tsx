'use client';

import { useState } from 'react';
import { Search, Loader2, ExternalLink, AlertTriangle, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/cn';

export default function LookupPage() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const handleLookup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const res = await fetch('/api/lookup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      });
      const data = await res.json();
      if (data.error) {
        setError(data.error);
      } else {
        setResult(data);
      }
    } catch {
      setError('Failed to lookup creator. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const detectPlatform = (input: string): string | null => {
    if (input.includes('tiktok.com')) return 'TikTok';
    if (input.includes('instagram.com')) return 'Instagram';
    if (input.includes('youtube.com') || input.includes('youtu.be')) return 'YouTube';
    return null;
  };

  const platform = detectPlatform(url);

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold mb-2">Creator Lookup</h1>
        <p className="text-muted-foreground">
          Paste a TikTok, Instagram, or YouTube profile URL for instant analysis
        </p>
      </div>

      {/* Lookup form */}
      <form onSubmit={handleLookup} className="mb-8">
        <div className="relative group">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-accent via-purple-500 to-pink-500 rounded-2xl opacity-15 group-hover:opacity-25 blur transition-opacity" />
          <div className="relative flex items-center bg-card border border-border rounded-xl overflow-hidden">
            <Search className="ml-5 h-5 w-5 text-muted shrink-0" />
            <input
              type="text"
              placeholder="https://tiktok.com/@username"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="flex-1 bg-transparent px-4 py-4 text-base outline-none placeholder:text-muted"
            />
            {platform && (
              <span className="text-xs text-muted-foreground mr-2 hidden sm:block">
                {platform} detected
              </span>
            )}
            <button
              type="submit"
              disabled={loading || !url.trim()}
              className="m-2 rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white hover:bg-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed shrink-0 flex items-center gap-2"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {loading ? 'Analyzing...' : 'Lookup'}
            </button>
          </div>
        </div>
      </form>

      {/* Example URLs */}
      <div className="mb-8 rounded-xl border border-border bg-card/50 p-5">
        <h3 className="text-sm font-medium mb-3">Supported formats</h3>
        <div className="space-y-2 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <span className="text-pink-400">♪</span>
            <code className="text-xs bg-surface px-2 py-0.5 rounded">https://tiktok.com/@username</code>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-purple-400">📷</span>
            <code className="text-xs bg-surface px-2 py-0.5 rounded">https://instagram.com/username</code>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-red-400">▶</span>
            <code className="text-xs bg-surface px-2 py-0.5 rounded">https://youtube.com/@channelname</code>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-5 mb-6">
          <div className="flex items-start gap-2">
            <AlertTriangle className="h-5 w-5 text-red-400 shrink-0" />
            <div>
              <h3 className="font-medium text-red-300">Lookup failed</h3>
              <p className="text-sm text-red-400/80 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="rounded-xl border border-border bg-card/50 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Lookup Result</h2>
            <span className={cn(
              'inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-medium',
              result.status === 'found' ? 'border-green-500/20 bg-green-500/10 text-green-400' : 'border-yellow-500/20 bg-yellow-500/10 text-yellow-400'
            )}>
              {result.status === 'found' ? <CheckCircle className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3" />}
              {result.status === 'found' ? 'In Database' : 'Not Yet Tracked'}
            </span>
          </div>

          {result.creator ? (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="h-12 w-12 rounded-full bg-card-hover flex items-center justify-center text-xl">
                  {result.platform === 'tiktok' ? '♪' : result.platform === 'instagram' ? '📷' : '▶'}
                </div>
                <div>
                  <div className="font-medium">{result.creator.name}</div>
                  <div className="text-sm text-muted-foreground">@{result.username} · {result.platform}</div>
                </div>
              </div>
              <a
                href={`/creator/${result.creator.id}`}
                className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover transition-colors"
              >
                View Full Profile
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">
              <p>This creator isn&apos;t in our database yet.</p>
              <p className="mt-2">
                On-demand scraping is coming soon. For now, we track creators in our pre-scraped database.
                The scraper will be able to pull profile data in real-time when this feature is enabled.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="rounded-xl border border-border bg-card/50 p-8 text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-accent mb-3" />
          <p className="text-sm text-muted-foreground">
            Analyzing creator profile...
          </p>
        </div>
      )}
    </div>
  );
}
