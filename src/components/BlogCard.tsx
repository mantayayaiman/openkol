import Link from 'next/link';
import type { BlogPostMeta } from '@/lib/blog';

export function BlogCard({ post }: { post: BlogPostMeta }) {
  return (
    <Link
      href={`/blog/${post.slug}`}
      className="group block rounded-xl border border-border bg-card p-6 transition-all hover:border-accent/40 hover:shadow-lg hover:shadow-accent/5"
    >
      {post.image && (
        <div className="mb-4 aspect-[2/1] overflow-hidden rounded-lg bg-surface">
          <img
            src={post.image}
            alt={post.title}
            className="h-full w-full object-cover transition-transform group-hover:scale-105"
          />
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
        <time dateTime={post.date}>
          {new Date(post.date).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          })}
        </time>
        <span>·</span>
        <span>{post.readingTime}</span>
        {post.featured && (
          <>
            <span>·</span>
            <span className="rounded-full bg-accent/10 px-2 py-0.5 text-accent">
              Featured
            </span>
          </>
        )}
      </div>
      <h2 className="mt-3 text-lg font-semibold text-foreground transition-colors group-hover:text-accent">
        {post.title}
      </h2>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground line-clamp-2">
        {post.description}
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        {post.tags.slice(0, 3).map((tag) => (
          <span
            key={tag}
            className="rounded-md bg-surface px-2 py-0.5 text-xs text-muted-foreground"
          >
            {tag}
          </span>
        ))}
      </div>
    </Link>
  );
}
