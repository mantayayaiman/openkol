import { NextRequest, NextResponse } from 'next/server';
import { getSupabase } from '@/lib/db';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const sb = getSupabase();
    const { id } = await params;

    const { data: creator, error: creatorErr } = await sb
      .from('creators')
      .select('*')
      .eq('id', id)
      .single();

    if (creatorErr || !creator) {
      return NextResponse.json({ error: 'Creator not found' }, { status: 404 });
    }

    const [platformsRes, auditRes] = await Promise.all([
      sb.from('platform_presences').select('*').eq('creator_id', id),
      sb.from('audit_scores').select('*').eq('creator_id', id).single(),
    ]);

    const platforms = (platformsRes.data || []).map((p: any) => ({
      ...p,
      avg_views: p.avg_views > 0
        ? p.avg_views
        : (p.total_videos > 0 && p.total_likes > 0)
          ? Math.floor(p.total_likes / p.total_videos / 0.08)
          : 0,
      recent_videos: p.recent_videos ?? 0,
      recent_views: p.recent_views ?? 0,
      recent_new_followers: p.recent_new_followers ?? 0,
      impressions: p.impressions ?? 0,
    }));

    // Extract top_content from the best platform presence
    let contentSamples: unknown[] = [];
    for (const p of platforms) {
      const topContent = p.top_content as string;
      if (topContent) {
        try {
          const items = JSON.parse(topContent);
          contentSamples = items.map((item: any) => ({
            url: item.u,
            views: item.v,
            likes: item.l,
            comments: item.c,
            shares: item.s,
            posted_at: item.d,
            caption: item.t,
          }));
          break;
        } catch {}
      }
    }

    let audience_demographics = null;
    try {
      if (creator.audience_demographics) audience_demographics = JSON.parse(creator.audience_demographics);
    } catch {}

    const storedContact = creator.contact_email || '';
    let contact_email = storedContact || null;
    if (!contact_email) {
      const bio = creator.bio || '';
      const emailMatch = bio.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/);
      if (emailMatch) contact_email = emailMatch[0];
    }

    const audit = auditRes.data;

    return NextResponse.json({
      ...creator,
      heat_score: creator.heat_score ?? 0,
      categories: JSON.parse(creator.categories || '[]'),
      platforms,
      audit: audit ? {
        ...audit,
        signals: JSON.parse(audit.signals_json || '{}'),
      } : null,
      content_samples: contentSamples,
      audience_demographics,
      contact_email,
    });
  } catch (error: unknown) {
    console.error('Creator detail API error:', error);
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
