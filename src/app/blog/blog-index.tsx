'use client';

import { useState, useMemo } from 'react';
import { Search } from 'lucide-react';
import type { BlogPostMeta } from '@/lib/blog';
import { BlogCard } from '@/components/BlogCard';

export function BlogIndex({
  posts,
  tags,
}: {
  posts: BlogPostMeta[];
  tags: string[];
}) {
  const [query, setQuery] = useState('');
  const [activeTag, setActiveTag] = useState<string | null>(null);

  const filtered = useMemo(() => {
    let result = posts;
    if (activeTag) {
      result = result.filter((p) => p.tags.includes(activeTag));
    }
    if (query) {
      const q = query.toLowerCase();
      result = result.filter(
        (p) =>
          p.title.toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q) ||
          p.tags.some((t) => t.toLowerCase().includes(q))
      );
    }
    return result;
  }, [posts, query, activeTag]);

  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      <header className="mb-10">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Blog
        </h1>
        <p className="mt-2 text-muted-foreground">
          Creator insights, rankings, and analytics from Southeast Asia.
        </p>
      </header>

      {/* Search + Filter */}
      <div className="mb-8 space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            type="text"
            placeholder="Search articles..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full rounded-lg border border-border bg-card py-2.5 pl-10 pr-4 text-sm text-foreground placeholder:text-muted outline-none transition-colors focus:border-accent/50"
          />
        </div>

        {tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setActiveTag(null)}
              className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                activeTag === null
                  ? 'bg-accent text-white'
                  : 'bg-surface text-muted-foreground hover:text-foreground'
              }`}
            >
              All
            </button>
            {tags.map((tag) => (
              <button
                key={tag}
                onClick={() => setActiveTag(activeTag === tag ? null : tag)}
                className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                  activeTag === tag
                    ? 'bg-accent text-white'
                    : 'bg-surface text-muted-foreground hover:text-foreground'
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Posts */}
      {filtered.length === 0 ? (
        <p className="py-12 text-center text-muted-foreground">
          No articles found.
        </p>
      ) : (
        <div className="grid gap-6">
          {filtered.map((post) => (
            <BlogCard key={post.slug} post={post} />
          ))}
        </div>
      )}
    </div>
  );
}
