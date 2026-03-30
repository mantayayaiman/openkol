'use client';

import { useState, useEffect, useRef } from 'react';
import { cn } from '@/lib/cn';
import { X, Send, CheckCircle, MessageSquare, AlertTriangle } from 'lucide-react';

const feedbackTypes = [
  { value: 'bug', label: 'Bug Report' },
  { value: 'wrong_data', label: 'Wrong Data' },
  { value: 'submit_kol', label: 'Submit KOL' },
  { value: 'feature', label: 'Feature Request' },
  { value: 'other', label: 'Other' },
];

interface FeedbackWidgetProps {
  defaultType?: string;
  defaultUrl?: string;
  defaultCreatorName?: string;
  trigger?: React.ReactNode;
}

export function FeedbackWidget({ defaultType, defaultUrl, defaultCreatorName, trigger }: FeedbackWidgetProps) {
  const [open, setOpen] = useState(false);
  const [type, setType] = useState(defaultType || 'bug');
  const [url, setUrl] = useState('');
  const [description, setDescription] = useState('');
  const [creatorName, setCreatorName] = useState(defaultCreatorName || '');
  const [contact, setContact] = useState('');
  const [tiktokUrl, setTiktokUrl] = useState('');
  const [instagramUrl, setInstagramUrl] = useState('');
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [screenshot, setScreenshot] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setUrl(defaultUrl || window.location.href);
      if (defaultType) setType(defaultType);
      if (defaultCreatorName) setCreatorName(defaultCreatorName);
    }
  }, [open, defaultUrl, defaultType, defaultCreatorName]);

  // Listen for custom open events (from Report Issue buttons)
  useEffect(() => {
    function handleOpen(e: CustomEvent) {
      const detail = e.detail || {};
      if (detail.type) setType(detail.type);
      if (detail.url) setUrl(detail.url);
      if (detail.creatorName) setCreatorName(detail.creatorName);
      setOpen(true);
    }
    window.addEventListener('open-feedback' as any, handleOpen as EventListener);
    return () => window.removeEventListener('open-feedback' as any, handleOpen as EventListener);
  }, []);

  function reset() {
    setType(defaultType || 'bug');
    setUrl('');
    setDescription('');
    setCreatorName('');
    setContact('');
    setTiktokUrl('');
    setInstagramUrl('');
    setYoutubeUrl('');
    setScreenshot(null);
    setError('');
    if (fileRef.current) fileRef.current.value = '';
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!description.trim()) {
      setError('Please enter a description.');
      return;
    }
    if (type === 'submit_kol' && !tiktokUrl && !instagramUrl && !youtubeUrl) {
      setError('Please provide at least one social media URL.');
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      let screenshotBase64 = '';
      if (screenshot) {
        const buf = await screenshot.arrayBuffer();
        screenshotBase64 = btoa(
          new Uint8Array(buf).reduce((data, byte) => data + String.fromCharCode(byte), '')
        );
      }

      const body: Record<string, unknown> = {
        type,
        url,
        description,
        creator_name: creatorName || null,
        contact: contact || null,
        screenshot_base64: screenshotBase64 || null,
        screenshot_filename: screenshot?.name || null,
      };

      if (type === 'submit_kol') {
        body.kol_urls = {
          tiktok: tiktokUrl || null,
          instagram: instagramUrl || null,
          youtube: youtubeUrl || null,
        };
      }

      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) throw new Error('Failed to submit');

      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        setOpen(false);
        reset();
      }, 2000);
    } catch {
      setError('Failed to submit feedback. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass = 'w-full rounded-lg bg-surface border border-border px-3 py-2 text-sm text-foreground placeholder:text-muted focus:outline-none focus:border-accent transition-colors';

  return (
    <>
      {/* Floating button or custom trigger */}
      {trigger ? (
        <span onClick={() => setOpen(true)}>{trigger}</span>
      ) : (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-5 right-5 z-50 flex items-center gap-2 rounded-full bg-accent hover:bg-accent-hover px-4 py-2.5 text-sm font-medium text-white shadow-lg transition-all hover:scale-105"
        >
          <MessageSquare className="h-4 w-4" />
          Feedback
        </button>
      )}

      {/* Modal overlay */}
      {open && (
        <div className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => { setOpen(false); reset(); }} />
          <div className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto bg-card border border-border rounded-t-2xl sm:rounded-2xl p-6 animate-fade-slide-up z-10">
            {/* Header */}
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold">Send Feedback</h2>
              <button onClick={() => { setOpen(false); reset(); }} className="p-1.5 rounded-lg hover:bg-surface transition-colors">
                <X className="h-5 w-5 text-muted" />
              </button>
            </div>

            {success ? (
              <div className="flex flex-col items-center gap-3 py-8">
                <CheckCircle className="h-12 w-12 text-success" />
                <p className="text-lg font-medium">Thank you!</p>
                <p className="text-sm text-muted-foreground">Your feedback has been submitted.</p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Type */}
                <div>
                  <label className="block text-xs text-muted-foreground mb-1.5">Type</label>
                  <select value={type} onChange={e => setType(e.target.value)} className={inputClass}>
                    {feedbackTypes.map(t => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>

                {/* URL */}
                <div>
                  <label className="block text-xs text-muted-foreground mb-1.5">Page URL</label>
                  <input type="text" value={url} onChange={e => setUrl(e.target.value)} className={inputClass} />
                </div>

                {/* KOL URLs (for Submit KOL type) */}
                {type === 'submit_kol' && (
                  <div className="space-y-3 rounded-lg border border-border bg-surface/50 p-4">
                    <p className="text-xs text-muted-foreground">Provide at least one social media URL:</p>
                    <div>
                      <label className="block text-xs text-muted-foreground mb-1">TikTok URL</label>
                      <input type="url" value={tiktokUrl} onChange={e => setTiktokUrl(e.target.value)} placeholder="https://tiktok.com/@username" className={inputClass} />
                    </div>
                    <div>
                      <label className="block text-xs text-muted-foreground mb-1">Instagram URL</label>
                      <input type="url" value={instagramUrl} onChange={e => setInstagramUrl(e.target.value)} placeholder="https://instagram.com/username" className={inputClass} />
                    </div>
                    <div>
                      <label className="block text-xs text-muted-foreground mb-1">YouTube URL</label>
                      <input type="url" value={youtubeUrl} onChange={e => setYoutubeUrl(e.target.value)} placeholder="https://youtube.com/@channel" className={inputClass} />
                    </div>
                  </div>
                )}

                {/* Creator name (optional, shown for submit_kol and wrong_data) */}
                {(type === 'submit_kol' || type === 'wrong_data') && (
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1.5">Creator Name (optional)</label>
                    <input type="text" value={creatorName} onChange={e => setCreatorName(e.target.value)} placeholder="Creator's name" className={inputClass} />
                  </div>
                )}

                {/* Description */}
                <div>
                  <label className="block text-xs text-muted-foreground mb-1.5">Description</label>
                  <textarea
                    value={description}
                    onChange={e => setDescription(e.target.value)}
                    rows={4}
                    placeholder={type === 'bug' ? 'What went wrong? Steps to reproduce...' : type === 'submit_kol' ? 'Tell us about this creator...' : 'Your feedback...'}
                    className={cn(inputClass, 'resize-none')}
                  />
                </div>

                {/* Contact */}
                <div>
                  <label className="block text-xs text-muted-foreground mb-1.5">Contact (optional)</label>
                  <input type="text" value={contact} onChange={e => setContact(e.target.value)} placeholder="Email or name for follow-up" className={inputClass} />
                </div>

                {/* Screenshot */}
                <div>
                  <label className="block text-xs text-muted-foreground mb-1.5">Screenshot (optional)</label>
                  <input
                    ref={fileRef}
                    type="file"
                    accept="image/*"
                    onChange={e => setScreenshot(e.target.files?.[0] || null)}
                    className="w-full text-sm text-muted-foreground file:mr-3 file:rounded-lg file:border-0 file:bg-surface file:px-3 file:py-1.5 file:text-sm file:text-muted-foreground hover:file:bg-card-hover file:cursor-pointer"
                  />
                </div>

                {/* Error */}
                {error && (
                  <div className="flex items-center gap-2 text-sm text-danger">
                    <AlertTriangle className="h-4 w-4" />
                    {error}
                  </div>
                )}

                {/* Submit */}
                <button
                  type="submit"
                  disabled={submitting}
                  className={cn(
                    'w-full flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all',
                    submitting
                      ? 'bg-accent/50 text-white/50 cursor-not-allowed'
                      : 'bg-accent hover:bg-accent-hover text-white'
                  )}
                >
                  <Send className="h-4 w-4" />
                  {submitting ? 'Submitting...' : 'Submit Feedback'}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}
