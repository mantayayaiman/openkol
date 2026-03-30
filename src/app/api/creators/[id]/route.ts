import { NextRequest, NextResponse } from 'next/server';
import { getDb } from '@/lib/db';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const db = getDb();
  const { id } = await params;

  const creator = await db.prepare(`
    SELECT *, COALESCE(heat_score, 0) as heat_score FROM creators WHERE id = ?
  `).get(id);

  if (!creator) {
    return NextResponse.json({ error: 'Creator not found' }, { status: 404 });
  }

  const platforms = await db.prepare(`
    SELECT *,
      CASE 
        WHEN avg_views > 0 THEN avg_views
        WHEN total_videos > 0 AND total_likes > 0 
          THEN CAST(total_likes / total_videos / 0.08 AS INTEGER)
        ELSE 0
      END as avg_views,
      COALESCE(recent_videos, 0) as recent_videos,
      COALESCE(recent_views, 0) as recent_views,
      COALESCE(recent_new_followers, 0) as recent_new_followers,
      COALESCE(impressions, 0) as impressions
    FROM platform_presences WHERE creator_id = ?
  `).all(id);

  const audit = await db.prepare(`
    SELECT * FROM audit_scores WHERE creator_id = ?
  `).get(id);

  const presenceIds = (platforms as Record<string, unknown>[]).map((p) => p.id);
  let contentSamples: unknown[] = [];
  if (presenceIds.length > 0) {
    const placeholders = presenceIds.map(() => '?').join(',');
    contentSamples = await db.prepare(`
      SELECT * FROM content_samples WHERE presence_id IN (${placeholders}) ORDER BY posted_at DESC
    `).all(...presenceIds);
  }

  let audience_demographics = null;
  try {
    const demoStr = (creator as Record<string, unknown>).audience_demographics as string;
    if (demoStr) audience_demographics = JSON.parse(demoStr);
  } catch {}

  const storedContact = (creator as Record<string, unknown>).contact_email as string || '';
  let contact_email = storedContact || null;
  if (!contact_email) {
    const bio = (creator as Record<string, unknown>).bio as string || '';
    const emailMatch = bio.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/);
    if (emailMatch) contact_email = emailMatch[0];
  }

  return NextResponse.json({
    ...creator as Record<string, unknown>,
    categories: JSON.parse((creator as Record<string, unknown>).categories as string || '[]'),
    platforms,
    audit: audit ? {
      ...audit as Record<string, unknown>,
      signals: JSON.parse((audit as Record<string, unknown>).signals_json as string || '{}'),
    } : null,
    content_samples: contentSamples,
    audience_demographics,
    contact_email,
  });
}
