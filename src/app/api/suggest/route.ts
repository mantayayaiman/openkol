import { NextRequest, NextResponse } from 'next/server';
import { getSupabase } from '@/lib/db';

export async function GET(request: NextRequest) {
  try {
    const sb = getSupabase();
    const q = request.nextUrl.searchParams.get('q')?.trim();

    if (!q || q.length < 2) {
      return NextResponse.json({ suggestions: [] });
    }

    const pattern = `%${q}%`;

    const { data, error } = await sb
      .from('creators')
      .select(`
        id, name, country, profile_image,
        platform_presences!inner(username, platform, followers)
      `)
      .or(`name.ilike.${pattern},platform_presences.username.ilike.${pattern}`)
      .order('followers', { referencedTable: 'platform_presences', ascending: false })
      .limit(8);

    if (error) {
      // Fallback: query without cross-table or filter
      const { data: fallback } = await sb
        .from('creators')
        .select(`
          id, name, country, profile_image,
          platform_presences(username, platform, followers)
        `)
        .ilike('name', pattern)
        .order('heat_score', { ascending: false })
        .limit(8);

      const suggestions = (fallback || []).map(c => {
        const pp = (c.platform_presences as any)?.[0];
        return {
          id: c.id,
          name: c.name,
          country: c.country,
          profile_image: c.profile_image,
          username: pp?.username ?? null,
          platform: pp?.platform ?? null,
          followers: pp?.followers ?? null,
        };
      });

      return NextResponse.json({ suggestions });
    }

    const suggestions = (data || []).map(c => {
      const pp = (c.platform_presences as any)?.[0];
      return {
        id: c.id,
        name: c.name,
        country: c.country,
        profile_image: c.profile_image,
        username: pp?.username ?? null,
        platform: pp?.platform ?? null,
        followers: pp?.followers ?? null,
      };
    });

    return NextResponse.json({ suggestions });
  } catch (error: unknown) {
    console.error('Suggest API error:', error);
    return NextResponse.json({ suggestions: [], error: String(error) }, { status: 500 });
  }
}
