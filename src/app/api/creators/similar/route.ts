import { NextRequest, NextResponse } from 'next/server';
import { getDb } from '@/lib/db';

export async function GET(request: NextRequest) {
  const db = getDb();
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
    const query = `
      SELECT DISTINCT c.id, c.name, c.country, c.categories, c.heat_score,
             pp.platform, pp.followers, pp.username
      FROM creators c
      LEFT JOIN platform_presences pp ON pp.creator_id = c.id
      WHERE c.id != ?
        AND c.country = ?
        AND c.categories LIKE ?
        AND pp.followers >= ?
        AND pp.followers <= ?
      ORDER BY RANDOM()
      LIMIT 6
    `;

    const creators = await db.prepare(query).all(
      id,
      country,
      `%${category}%`,
      minFollowers,
      maxFollowers
    );

    return NextResponse.json({ creators });
  } catch (error) {
    console.error('Error fetching similar creators:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
