import { NextResponse } from 'next/server';
import { getSupabase } from '@/lib/db';

export async function GET() {
  try {
    const sb = getSupabase();

    const [creators, countries, platforms] = await Promise.all([
      sb.from('creators').select('*', { count: 'exact', head: true }),
      sb.from('creators').select('country').limit(10000),
      sb.from('platform_presences').select('platform').limit(10000),
    ]);

    const uniqueCountries = new Set((countries.data || []).map(r => r.country));
    const uniquePlatforms = new Set((platforms.data || []).map(r => r.platform));

    return NextResponse.json({
      creators: creators.count ?? 0,
      countries: uniqueCountries.size,
      platforms: uniquePlatforms.size,
    });
  } catch (error: unknown) {
    console.error('Stats API error:', error);
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
