import { getAllPosts } from '@/lib/blog';

export async function GET() {
  const posts = getAllPosts();
  const baseUrl = 'https://kolbuff.com';

  const items = posts
    .map(
      (post) => `
    <item>
      <title><![CDATA[${post.title}]]></title>
      <link>${baseUrl}/blog/${post.slug}</link>
      <guid isPermaLink="true">${baseUrl}/blog/${post.slug}</guid>
      <description><![CDATA[${post.description}]]></description>
      <pubDate>${new Date(post.date).toUTCString()}</pubDate>
      ${post.tags.map((t) => `<category>${t}</category>`).join('\n      ')}
    </item>`
    )
    .join('');

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>KolBuff Blog</title>
    <link>${baseUrl}/blog</link>
    <description>Creator insights, rankings, and analytics from Southeast Asia.</description>
    <language>en</language>
    <atom:link href="${baseUrl}/blog/feed.xml" rel="self" type="application/rss+xml" />
    ${items}
  </channel>
</rss>`;

  return new Response(xml, {
    headers: {
      'Content-Type': 'application/xml',
    },
  });
}
