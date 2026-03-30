import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { MDXRemote } from 'next-mdx-remote/rsc';
import Link from 'next/link';
import { ArrowLeft, Calendar, Clock, User } from 'lucide-react';
import {
  getAllPosts,
  getPostBySlug,
  getRelatedPosts,
  extractTOC,
} from '@/lib/blog';
import { TableOfContents } from '@/components/TableOfContents';
import { ShareButtons } from '@/components/ShareButtons';
import { CreatorLink } from '@/components/CreatorLink';
import { BlogCard } from '@/components/BlogCard';

// MDX components available in blog posts
const mdxComponents = {
  CreatorLink,
  h2: (props: React.ComponentProps<'h2'>) => {
    const text = String(props.children);
    const id = text
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-');
    return <h2 id={id} {...props} />;
  },
  h3: (props: React.ComponentProps<'h3'>) => {
    const text = String(props.children);
    const id = text
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-');
    return <h3 id={id} {...props} />;
  },
  h4: (props: React.ComponentProps<'h4'>) => {
    const text = String(props.children);
    const id = text
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-');
    return <h4 id={id} {...props} />;
  },
  a: (props: React.ComponentProps<'a'>) => (
    <a {...props} className="text-accent underline underline-offset-2 hover:text-accent-hover" />
  ),
  table: (props: React.ComponentProps<'table'>) => (
    <div className="my-6 overflow-x-auto rounded-lg border border-border">
      <table {...props} className="w-full text-sm" />
    </div>
  ),
  th: (props: React.ComponentProps<'th'>) => (
    <th {...props} className="bg-surface px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground" />
  ),
  td: (props: React.ComponentProps<'td'>) => (
    <td {...props} className="border-t border-border px-4 py-2 text-muted-foreground" />
  ),
};

export async function generateStaticParams() {
  const posts = getAllPosts();
  return posts.map((post) => ({ slug: post.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = getPostBySlug(slug);
  if (!post) return {};

  const url = `https://kolbuff.com/blog/${post.slug}`;

  return {
    title: `${post.title} — KolBuff`,
    description: post.description,
    openGraph: {
      title: post.title,
      description: post.description,
      url,
      siteName: 'KolBuff',
      type: 'article',
      publishedTime: post.date,
      authors: [post.author],
      tags: post.tags,
      ...(post.image && { images: [{ url: post.image }] }),
    },
    twitter: {
      card: 'summary_large_image',
      title: post.title,
      description: post.description,
      ...(post.image && { images: [post.image] }),
    },
    alternates: {
      canonical: url,
    },
  };
}

export default async function BlogPostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const post = getPostBySlug(slug);
  if (!post) notFound();

  const toc = extractTOC(post.content);
  const related = getRelatedPosts(post.slug, post.tags);
  const url = `https://kolbuff.com/blog/${post.slug}`;

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: post.title,
    description: post.description,
    datePublished: post.date,
    author: {
      '@type': 'Organization',
      name: post.author,
    },
    publisher: {
      '@type': 'Organization',
      name: 'KolBuff',
      url: 'https://kolbuff.com',
    },
    mainEntityOfPage: url,
    ...(post.image && { image: post.image }),
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <div className="mx-auto max-w-7xl px-4 py-12">
        <div className="lg:grid lg:grid-cols-[1fr_220px] lg:gap-12">
          {/* Main content */}
          <article className="mx-auto max-w-3xl lg:mx-0">
            {/* Back link */}
            <Link
              href="/blog"
              className="mb-8 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              All articles
            </Link>

            {/* Header */}
            <header className="mb-10">
              <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <Calendar className="h-3.5 w-3.5" />
                  {new Date(post.date).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </span>
                <span>·</span>
                <span className="flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5" />
                  {post.readingTime}
                </span>
                <span>·</span>
                <span className="flex items-center gap-1.5">
                  <User className="h-3.5 w-3.5" />
                  {post.author}
                </span>
              </div>
              <h1 className="mt-4 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
                {post.title}
              </h1>
              <p className="mt-4 text-lg text-muted-foreground">
                {post.description}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {post.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-md bg-surface px-2.5 py-0.5 text-xs text-muted-foreground"
                  >
                    {tag}
                  </span>
                ))}
              </div>

              <div className="mt-6">
                <ShareButtons url={url} title={post.title} />
              </div>
            </header>

            {/* MDX Content */}
            <div className="prose-blog">
              <MDXRemote source={post.content} components={mdxComponents} />
            </div>

            {/* Footer share */}
            <div className="mt-12 border-t border-border pt-6">
              <ShareButtons url={url} title={post.title} />
            </div>

            {/* Related posts */}
            {related.length > 0 && (
              <section className="mt-12">
                <h2 className="mb-6 text-xl font-semibold text-foreground">
                  Related articles
                </h2>
                <div className="grid gap-4 sm:grid-cols-2">
                  {related.map((r) => (
                    <BlogCard key={r.slug} post={r} />
                  ))}
                </div>
              </section>
            )}
          </article>

          {/* Sidebar TOC */}
          {toc.length > 0 && (
            <aside className="hidden lg:block">
              <div className="sticky top-20">
                <TableOfContents items={toc} />
              </div>
            </aside>
          )}
        </div>
      </div>
    </>
  );
}
