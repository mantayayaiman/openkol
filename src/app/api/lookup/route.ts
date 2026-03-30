import { NextRequest, NextResponse } from 'next/server';
import { getDb } from '@/lib/db';

function parseCreatorUrl(url: string): { platform: string; username: string } | null {
  try {
    const u = new URL(url);

    if (u.hostname.includes('tiktok.com')) {
      const match = u.pathname.match(/^\/@([^/?]+)/);
      if (match) return { platform: 'tiktok', username: match[1] };
    }

    if (u.hostname.includes('instagram.com')) {
      const match = u.pathname.match(/^\/([^/?]+)/);
      if (match && !['p', 'reel', 'stories', 'explore', 'accounts'].includes(match[1])) {
        return { platform: 'instagram', username: match[1] };
      }
    }

    if (u.hostname.includes('youtube.com') || u.hostname.includes('youtu.be')) {
      const match = u.pathname.match(/^\/@([^/?]+)/) || u.pathname.match(/^\/channel\/([^/?]+)/);
      if (match) return { platform: 'youtube', username: match[1] };
    }

    return null;
  } catch {
    return null;
  }
}

export async function POST(request: NextRequest) {
  const db = getDb();

  const body = await request.json();
  const { url } = body;

  if (!url) {
    return NextResponse.json({ error: 'URL is required' }, { status: 400 });
  }

  const parsed = parseCreatorUrl(url);
  if (!parsed) {
    return NextResponse.json({
      error: 'Could not parse URL. Please provide a valid TikTok, Instagram, or YouTube profile URL.',
    }, { status: 400 });
  }

  const presence = await db.prepare(`
    SELECT pp.*, c.id as creator_id, c.name, c.bio, c.country
    FROM platform_presences pp
    JOIN creators c ON c.id = pp.creator_id
    WHERE pp.platform = ? AND pp.username = ?
  `).get(parsed.platform, parsed.username) as Record<string, unknown> | undefined;

  if (presence) {
    return NextResponse.json({
      status: 'found',
      platform: parsed.platform,
      username: parsed.username,
      creator: {
        id: presence.creator_id,
        name: presence.name,
        bio: presence.bio,
        country: presence.country,
      },
    });
  }

  return NextResponse.json({
    status: 'not_found',
    platform: parsed.platform,
    username: parsed.username,
    creator: null,
    message: 'Creator not found in database. On-demand scraping coming soon.',
  });
}
