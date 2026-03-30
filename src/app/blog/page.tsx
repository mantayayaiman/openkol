import type { Metadata } from 'next';
import { getAllPosts, getAllTags } from '@/lib/blog';
import { BlogIndex } from './blog-index';

export const metadata: Metadata = {
  title: 'Blog — KolBuff',
  description:
    'Insights, rankings, and analytics on Southeast Asian creators across TikTok, Instagram, and YouTube.',
  openGraph: {
    title: 'Blog — KolBuff',
    description:
      'Insights, rankings, and analytics on Southeast Asian creators across TikTok, Instagram, and YouTube.',
    url: 'https://kolbuff.com/blog',
    siteName: 'KolBuff',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Blog — KolBuff',
    description:
      'Insights, rankings, and analytics on Southeast Asian creators across TikTok, Instagram, and YouTube.',
  },
  alternates: {
    canonical: 'https://kolbuff.com/blog',
  },
};

export default function BlogPage() {
  const posts = getAllPosts();
  const tags = getAllTags();

  return <BlogIndex posts={posts} tags={tags} />;
}
