import { NextResponse } from 'next/server';
import { getDb } from '@/lib/db';

export async function GET() {
  const db = getDb();

  const creatorCount = await db.prepare('SELECT COUNT(*) as count FROM creators').get() as { count: number } | undefined;
  const countryCount = await db.prepare('SELECT COUNT(DISTINCT country) as count FROM creators').get() as { count: number } | undefined;
  const platformCount = await db.prepare('SELECT COUNT(DISTINCT platform) as count FROM platform_presences').get() as { count: number } | undefined;

  return NextResponse.json({
    creators: creatorCount?.count ?? 0,
    countries: countryCount?.count ?? 0,
    platforms: platformCount?.count ?? 0,
  });
}
