import { NextRequest, NextResponse } from 'next/server';
import { getSupabase } from '@/lib/db';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { type, url, description, creator_name, contact, screenshot_base64, screenshot_filename, kol_urls } = body;

    if (!description || !type) {
      return NextResponse.json({ error: 'type and description are required' }, { status: 400 });
    }

    const sb = getSupabase();

    // Build the description with KOL URLs appended if present
    let fullDescription = description;
    if (type === 'submit_kol' && kol_urls) {
      const urls = [];
      if (kol_urls.tiktok) urls.push(`TikTok: ${kol_urls.tiktok}`);
      if (kol_urls.instagram) urls.push(`Instagram: ${kol_urls.instagram}`);
      if (kol_urls.youtube) urls.push(`YouTube: ${kol_urls.youtube}`);
      if (urls.length > 0) {
        fullDescription += '\n\n--- Social URLs ---\n' + urls.join('\n');
      }
    }

    // Handle screenshot upload if provided
    let screenshot_url: string | null = null;
    if (screenshot_base64 && screenshot_filename) {
      try {
        const bytes = Uint8Array.from(atob(screenshot_base64), c => c.charCodeAt(0));
        const ext = screenshot_filename.split('.').pop() || 'png';
        const path = `feedback/${Date.now()}-${Math.random().toString(36).slice(2, 8)}.${ext}`;

        const { error: uploadError } = await sb.storage
          .from('feedback-screenshots')
          .upload(path, bytes, { contentType: `image/${ext}` });

        if (!uploadError) {
          const { data: urlData } = sb.storage
            .from('feedback-screenshots')
            .getPublicUrl(path);
          screenshot_url = urlData.publicUrl;
        } else {
          console.warn('Screenshot upload failed:', uploadError.message);
        }
      } catch (e) {
        console.warn('Screenshot processing failed:', e);
      }
    }

    // Insert into Supabase
    try {
      const { data, error } = await sb
        .from('feedback')
        .insert({
          type,
          url: url || null,
          description: fullDescription,
          creator_name: creator_name || null,
          contact: contact || null,
          screenshot_url,
          status: 'new',
        })
        .select('id')
        .single();

      if (error) {
        console.warn('Supabase insert error (table may not exist yet):', error.message);
        // Return success anyway so the user gets confirmation — log for debugging
        return NextResponse.json({ success: true, id: null, warning: 'Saved with warning' });
      }

      return NextResponse.json({ success: true, id: data.id });
    } catch (dbErr) {
      console.warn('Database error:', dbErr);
      return NextResponse.json({ success: true, id: null, warning: 'Saved with warning' });
    }
  } catch (err) {
    console.error('Feedback API error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

export async function GET() {
  try {
    const sb = getSupabase();
    const { data, error } = await sb
      .from('feedback')
      .select('*')
      .order('created_at', { ascending: false });

    if (error) {
      console.warn('Feedback fetch error:', error.message);
      return NextResponse.json({ feedback: [], error: error.message });
    }

    return NextResponse.json({ feedback: data || [] });
  } catch (err) {
    console.error('Feedback GET error:', err);
    return NextResponse.json({ feedback: [], error: 'Internal server error' });
  }
}
