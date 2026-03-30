import { NextRequest, NextResponse } from 'next/server';
import { getSupabase } from '@/lib/db';

export async function GET(request: NextRequest) {
  const sb = getSupabase();
  const { searchParams } = request.nextUrl;

  const id = searchParams.get('id');
  const country = searchParams.get('country');
  const category = searchParams.get('category');
  const minFollowers = parseInt(searchParams.get('minFollowers') || '0');
  const maxFollowers = parseInt(searchParams.get('maxFollowers') || '999999999');

  if (!id || !country || !category) {
    return NextResponse.json({ error: 'Missing required parameters' }, { status: 400 });
  }

  try {
    const { data, error } = await sb
      .from('creators')
      .select('id, name, country, categories, heat_score, platform_presences(platform, followers, username)')
      .neq('id', id)
      .eq('country', country)
      .ilike('categories', `%${category}%`)
      .limit(50);

    if (error) throw error;

    // Filter by follower range and flatten, then pick random 6
    const filtered = (data || [])
      .map(c => {
        const pp = (c.platform_presences as any[])?.[0];
        if (!pp) return null;
        if (pp.followers < minFollowers || pp.followers > maxFollowers) return null;
        return {
          id: c.id,
          name: c.name,
          country: c.country,
          categories: c.categories,
          heat_score: c.heat_score,
          platform: pp.platform,
          followers: pp.followers,
          username: pp.username,
        };
      })
      .filter(Boolean);

    // Shuffle and take 6
    for (let i = filtered.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [filtered[i], filtered[j]] = [filtered[j], filtered[i]];
    }

    return NextResponse.json({ creators: filtered.slice(0, 6) });
  } catch (error) {
    console.error('Error fetching similar creators:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
