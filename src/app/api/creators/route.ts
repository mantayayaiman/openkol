import { NextRequest, NextResponse } from 'next/server';
import { getSupabase } from '@/lib/db';

export async function GET(request: NextRequest) {
  try {
    const sb = getSupabase();

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

    // Build the main query with embedded relations
    // When filtering by platform, use inner join on platform_presences
    // Otherwise, join on primary_platform
    const selectFields = `
      *,
      platform_presences!inner(platform, username, url, followers, following, total_likes, total_videos, avg_views, engagement_rate, last_scraped_at),
      audit_scores(overall_score, follower_quality, engagement_authenticity, growth_consistency, comment_quality, signals_json)
    `;

    let query = sb.from('creators').select(selectFields, { count: 'exact' });

    // Platform filter: either filter by specific platform or by primary_platform
    if (platform) {
      query = query.eq('platform_presences.platform', platform);
    } else {
      // PostgREST doesn't support join conditions directly, so we filter where platform = primary_platform
      // We use an RPC or filter client-side. Simplest: filter by eq on referenced table.
      // We'll use a workaround: fetch with inner join and filter client-side for primary_platform match.
      // Actually, we can use the PostgREST syntax to filter: platform_presences.platform = creators.primary_platform
      // This isn't directly supported. Instead, we use a raw filter.
      // Best approach: use .or() won't work cross-table. Let's just not filter here and handle it below.
    }

    if (countries.length > 0) {
      query = query.in('country', countries);
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
      query = query.ilike('categories', `%${dbCategory}%`);
    }

    if (search) {
      query = query.or(`name.ilike.%${search}%,bio.ilike.%${search}%`);
    }

    // Sorting - for PostgREST we sort on the main table or referenced table
    const sortMap: Record<string, { column: string; table?: string }> = {
      followers: { column: 'followers', table: 'platform_presences' },
      engagement: { column: 'engagement_rate', table: 'platform_presences' },
      score: { column: 'overall_score', table: 'audit_scores' },
      heat: { column: 'heat_score' },
    };
    const sortConfig = sortMap[sort] || sortMap.followers;
    if (sortConfig.table) {
      query = query.order(sortConfig.column, { referencedTable: sortConfig.table, ascending: false });
    } else {
      query = query.order(sortConfig.column, { ascending: false });
    }

    query = query.range(offset, offset + limit - 1);

    const { data, error, count } = await query;

    if (error) throw error;

    // Flatten the nested structure to match the original response shape
    const creators = (data || [])
      .map((c: any) => {
        const pp = Array.isArray(c.platform_presences)
          ? (!platform
              ? c.platform_presences.find((p: any) => p.platform === c.primary_platform) || c.platform_presences[0]
              : c.platform_presences[0])
          : c.platform_presences;
        const a = Array.isArray(c.audit_scores) ? c.audit_scores[0] : c.audit_scores;

        if (!pp) return null;

        // Apply follower/ER filters that are on the platform_presences fields
        if (tier) {
          const tierRanges: Record<string, [number, number]> = {
            mega: [10000000, 999999999],
            macro: [1000000, 9999999],
            mid: [100000, 999999],
            micro: [10000, 99999],
            nano: [1000, 9999],
          };
          const range = tierRanges[tier];
          if (range && (pp.followers < range[0] || pp.followers > range[1])) return null;
        }
        if (minFollowers && pp.followers < parseInt(minFollowers)) return null;
        if (maxFollowers && pp.followers > parseInt(maxFollowers)) return null;
        if (minEr && pp.engagement_rate < parseFloat(minEr)) return null;
        if (maxEr && pp.engagement_rate > parseFloat(maxEr)) return null;

        const avgViews = pp.avg_views > 0
          ? pp.avg_views
          : (pp.total_videos > 0 && pp.total_likes > 0)
            ? Math.floor(pp.total_likes / pp.total_videos / 0.08)
            : 0;

        const { platform_presences, audit_scores, ...creatorFields } = c;
        return {
          ...creatorFields,
          platform: pp.platform,
          username: pp.username,
          platform_url: pp.url,
          followers: pp.followers,
          following: pp.following,
          total_likes: pp.total_likes,
          total_videos: pp.total_videos,
          avg_views: avgViews,
          engagement_rate: pp.engagement_rate,
          last_scraped_at: pp.last_scraped_at,
          heat_score: c.heat_score ?? 0,
          overall_score: a?.overall_score ?? null,
          follower_quality: a?.follower_quality ?? null,
          engagement_authenticity: a?.engagement_authenticity ?? null,
          growth_consistency: a?.growth_consistency ?? null,
          comment_quality: a?.comment_quality ?? null,
          signals_json: a?.signals_json ?? null,
        };
      })
      .filter(Boolean);

    // Sort by views client-side if needed (computed column)
    if (sort === 'views') {
      creators.sort((a: any, b: any) => (b.avg_views || 0) - (a.avg_views || 0));
    }

    return NextResponse.json({
      creators,
      total: count ?? 0,
      limit,
      offset,
    });
  } catch (error: unknown) {
    console.error('Creators API error:', error);
    return NextResponse.json({ error: String(error), creators: [], total: 0 }, { status: 500 });
  }
}
