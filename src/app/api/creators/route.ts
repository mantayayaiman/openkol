import { NextRequest, NextResponse } from 'next/server';
import { getDb } from '@/lib/db';

export async function GET(request: NextRequest) {
  const db = getDb();

  const { searchParams } = request.nextUrl;
  const country = searchParams.get('country');
  const countries = country ? country.split(',').filter(Boolean) : [];
  const platform = searchParams.get('platform');
  const category = searchParams.get('category');
  const search = searchParams.get('q');
  const tier = searchParams.get('tier');
  const minFollowers = searchParams.get('min_followers');
  const maxFollowers = searchParams.get('max_followers');
  const minEr = searchParams.get('min_er');
  const maxEr = searchParams.get('max_er');
  const sort = searchParams.get('sort') || 'followers';
  const limit = parseInt(searchParams.get('limit') || '50');
  const offset = parseInt(searchParams.get('offset') || '0');

  let where = 'WHERE 1=1';
  const params: unknown[] = [];

  if (countries.length > 0) {
    const placeholders = countries.map(() => '?').join(', ');
    where += ` AND c.country IN (${placeholders})`;
    params.push(...countries);
  }
  if (platform) {
    where += ' AND pp.platform = ?';
    params.push(platform);
  }
  if (category) {
    const categoryMap: Record<string, string> = {
      'Beauty & Skincare': 'beauty',
      'Fashion & Style': 'fashion',
      'Food & F&B': 'food',
      'Gaming': 'gaming',
      'Tech & Gadgets': 'tech',
      'Lifestyle': 'lifestyle',
      'Fitness & Health': 'fitness',
      'Travel': 'travel',
      'Comedy & Entertainment': 'comedy',
      'Education': 'education',
      'Music & Dance': 'music',
      'Parenting & Family': 'family',
      'Automotive': 'automotive',
      'Finance & Business': 'finance',
      'Pets & Animals': 'pets',
    };
    const dbCategory = categoryMap[category] || category.toLowerCase();
    where += ' AND c.categories LIKE ?';
    params.push(`%${dbCategory}%`);
  }
  if (tier) {
    const tierRanges: Record<string, [number, number]> = {
      mega: [10000000, 999999999],
      macro: [1000000, 9999999],
      mid: [100000, 999999],
      micro: [10000, 99999],
      nano: [1000, 9999],
    };
    const range = tierRanges[tier];
    if (range) {
      where += ' AND pp.followers >= ? AND pp.followers <= ?';
      params.push(range[0], range[1]);
    }
  }
  if (minFollowers) {
    where += ' AND pp.followers >= ?';
    params.push(parseInt(minFollowers));
  }
  if (maxFollowers) {
    where += ' AND pp.followers <= ?';
    params.push(parseInt(maxFollowers));
  }
  if (minEr) {
    where += ' AND pp.engagement_rate >= ?';
    params.push(parseFloat(minEr));
  }
  if (maxEr) {
    where += ' AND pp.engagement_rate <= ?';
    params.push(parseFloat(maxEr));
  }
  if (search) {
    where += ' AND (c.name LIKE ? OR c.bio LIKE ? OR pp.username LIKE ?)';
    params.push(`%${search}%`, `%${search}%`, `%${search}%`);
  }

  const orderMap: Record<string, string> = {
    followers: 'pp.followers DESC',
    engagement: 'pp.engagement_rate DESC',
    score: 'a.overall_score DESC',
    heat: 'c.heat_score DESC',
    views: 'CASE WHEN pp.avg_views > 0 THEN pp.avg_views WHEN pp.total_videos > 0 AND pp.total_likes > 0 THEN CAST(pp.total_likes / pp.total_videos / 0.08 AS INTEGER) ELSE 0 END DESC',
  };
  const orderBy = orderMap[sort] || 'pp.followers DESC';

  const platformJoin = platform
    ? `LEFT JOIN platform_presences pp ON pp.creator_id = c.id`
    : `LEFT JOIN (
        SELECT pp1.* FROM platform_presences pp1
        INNER JOIN (
          SELECT creator_id, MAX(followers) as max_followers FROM platform_presences GROUP BY creator_id
        ) pp2 ON pp1.creator_id = pp2.creator_id AND pp1.followers = pp2.max_followers
        GROUP BY pp1.creator_id
      ) pp ON pp.creator_id = c.id`;

  const query = `
    SELECT c.*, pp.platform, pp.username, pp.url as platform_url, pp.followers, pp.following,
           pp.total_likes, pp.total_videos,
           CASE 
             WHEN pp.avg_views > 0 THEN pp.avg_views
             WHEN pp.total_videos > 0 AND pp.total_likes > 0 
               THEN CAST(pp.total_likes / pp.total_videos / 0.08 AS INTEGER)
             ELSE 0
           END as avg_views,
           pp.engagement_rate, pp.last_scraped_at,
           COALESCE(c.heat_score, 0) as heat_score,
           a.overall_score, a.follower_quality, a.engagement_authenticity,
           a.growth_consistency, a.comment_quality, a.signals_json
    FROM creators c
    ${platformJoin}
    LEFT JOIN audit_scores a ON a.creator_id = c.id
    ${where}
    ORDER BY ${orderBy}
    LIMIT ? OFFSET ?
  `;
  params.push(limit, offset);

  const creators = await db.prepare(query).all(...params);

  const countQuery = `
    SELECT COUNT(*) as total
    FROM creators c
    ${platformJoin}
    LEFT JOIN audit_scores a ON a.creator_id = c.id
    ${where}
  `;
  const countResult = await db.prepare(countQuery).get(...params.slice(0, -2)) as { total: number } | undefined;

  return NextResponse.json({
    creators,
    total: countResult?.total ?? 0,
    limit,
    offset,
  });
}
