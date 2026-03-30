'use client';

import { useState, useEffect } from 'react';
import { cn } from '@/lib/cn';
import { MessageSquare, Bug, Lightbulb, Users, AlertTriangle, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';

const typeConfig: Record<string, { label: string; color: string; icon: typeof Bug }> = {
  bug: { label: 'Bug Report', color: 'bg-red-500/10 text-red-400 border-red-500/20', icon: Bug },
  wrong_data: { label: 'Wrong Data', color: 'bg-orange-500/10 text-orange-400 border-orange-500/20', icon: AlertTriangle },
  submit_kol: { label: 'Submit KOL', color: 'bg-green-500/10 text-green-400 border-green-500/20', icon: Users },
  feature: { label: 'Feature Request', color: 'bg-blue-500/10 text-blue-400 border-blue-500/20', icon: Lightbulb },
  other: { label: 'Other', color: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20', icon: MessageSquare },
};

const statusColors: Record<string, string> = {
  new: 'bg-accent/10 text-accent border-accent/20',
  in_progress: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  resolved: 'bg-green-500/10 text-green-400 border-green-500/20',
  dismissed: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20',
};

interface FeedbackEntry {
  id: number;
  type: string;
  url: string | null;
  description: string;
  creator_name: string | null;
  contact: string | null;
  screenshot_url: string | null;
  status: string;
  created_at: string;
  resolved_at: string | null;
}

export default function FeedbackPage() {
  const [feedback, setFeedback] = useState<FeedbackEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [filterType, setFilterType] = useState<string>('all');

  useEffect(() => {
    fetch('/api/feedback')
      .then(res => res.json())
      .then(data => {
        setFeedback(data.feedback || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const filtered = filterType === 'all' ? feedback : feedback.filter(f => f.type === filterType);

  const counts = feedback.reduce((acc, f) => {
    acc[f.type] = (acc[f.type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-2">Feedback & Reports</h1>
        <p className="text-muted-foreground text-sm">{feedback.length} total submissions</p>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap gap-2 mb-6">
        <button
          onClick={() => setFilterType('all')}
          className={cn(
            'rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors',
            filterType === 'all' ? 'bg-accent/10 text-accent border-accent/20' : 'bg-surface border-border text-muted-foreground hover:text-foreground'
          )}
        >
          All ({feedback.length})
        </button>
        {Object.entries(typeConfig).map(([key, cfg]) => (
          <button
            key={key}
            onClick={() => setFilterType(key)}
            className={cn(
              'rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors',
              filterType === key ? cfg.color : 'bg-surface border-border text-muted-foreground hover:text-foreground'
            )}
          >
            {cfg.label} ({counts[key] || 0})
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-20 bg-card rounded-xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p>No feedback yet.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(entry => {
            const cfg = typeConfig[entry.type] || typeConfig.other;
            const Icon = cfg.icon;
            const isExpanded = expandedId === entry.id;

            return (
              <div key={entry.id} className="rounded-xl border border-border bg-card/50 overflow-hidden">
                <button
                  onClick={() => setExpandedId(isExpanded ? null : entry.id)}
                  className="w-full flex items-start gap-3 p-4 text-left hover:bg-card-hover/30 transition-colors"
                >
                  <div className={cn('rounded-lg border p-2 shrink-0', cfg.color)}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={cn('text-xs rounded-full border px-2 py-0.5', cfg.color)}>{cfg.label}</span>
                      <span className={cn('text-xs rounded-full border px-2 py-0.5', statusColors[entry.status] || statusColors.new)}>
                        {entry.status}
                      </span>
                      <span className="text-xs text-muted ml-auto shrink-0">
                        {new Date(entry.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <p className="text-sm mt-1.5 line-clamp-2">{entry.description}</p>
                  </div>
                  {isExpanded ? <ChevronUp className="h-4 w-4 text-muted shrink-0 mt-1" /> : <ChevronDown className="h-4 w-4 text-muted shrink-0 mt-1" />}
                </button>

                {isExpanded && (
                  <div className="border-t border-border px-4 py-4 space-y-3 bg-surface/30">
                    <div>
                      <span className="text-xs text-muted-foreground">Full Description</span>
                      <p className="text-sm whitespace-pre-wrap mt-1">{entry.description}</p>
                    </div>
                    {entry.url && (
                      <div>
                        <span className="text-xs text-muted-foreground">Page URL</span>
                        <a href={entry.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-sm text-accent hover:underline mt-1">
                          {entry.url} <ExternalLink className="h-3 w-3" />
                        </a>
                      </div>
                    )}
                    {entry.creator_name && (
                      <div>
                        <span className="text-xs text-muted-foreground">Creator Name</span>
                        <p className="text-sm mt-1">{entry.creator_name}</p>
                      </div>
                    )}
                    {entry.contact && (
                      <div>
                        <span className="text-xs text-muted-foreground">Contact</span>
                        <p className="text-sm mt-1">{entry.contact}</p>
                      </div>
                    )}
                    {entry.screenshot_url && (
                      <div>
                        <span className="text-xs text-muted-foreground">Screenshot</span>
                        <a href={entry.screenshot_url} target="_blank" rel="noopener noreferrer" className="block mt-1">
                          <img src={entry.screenshot_url} alt="Screenshot" className="max-w-xs rounded-lg border border-border" />
                        </a>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
