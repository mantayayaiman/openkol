import { Rocket, Sparkles, Bug, Zap } from 'lucide-react';

type ChangeType = 'feature' | 'fix' | 'improvement';

interface Change {
  type: ChangeType;
  text: string;
}

interface Release {
  version: string;
  date: string;
  title: string;
  changes: Change[];
}

const typeConfig: Record<ChangeType, { label: string; icon: typeof Rocket; color: string; bg: string }> = {
  feature: { label: 'New', icon: Sparkles, color: 'text-green-400', bg: 'bg-green-400/10' },
  fix: { label: 'Fix', icon: Bug, color: 'text-red-400', bg: 'bg-red-400/10' },
  improvement: { label: 'Improved', icon: Zap, color: 'text-blue-400', bg: 'bg-blue-400/10' },
};

const releases: Release[] = [
  {
    version: '0.4.0',
    date: '2026-03-30',
    title: 'Video Performance & Smart Search',
    changes: [
      { type: 'feature', text: 'Search autocomplete — get instant suggestions with creator avatars and follower counts as you type' },
      { type: 'feature', text: 'Top video performance — see each creator\'s best-performing videos with views, likes, comments, and engagement rate' },
      { type: 'feature', text: 'Click any video to open it directly on TikTok' },
      { type: 'feature', text: 'This changelog page — stay updated on what\'s new' },
      { type: 'improvement', text: 'Heat Score now factors in actual video performance, not just follower counts' },
      { type: 'fix', text: 'Fixed incorrect engagement rates showing for some large creators' },
      { type: 'fix', text: 'Stats bar now shows real-time numbers' },
    ],
  },
  {
    version: '0.3.0',
    date: '2026-03-30',
    title: 'Shortlists & Better Rankings',
    changes: [
      { type: 'feature', text: 'Shortlist creators with the ❤️ button — save your favorites from any page' },
      { type: 'feature', text: 'Smarter country and category detection for more accurate filtering' },
      { type: 'feature', text: 'Contact info extraction — email and phone from creator bios where available' },
      { type: 'improvement', text: 'Rankings now correctly show one entry per creator (no duplicates)' },
      { type: 'improvement', text: 'Heat Score rebalanced — larger creators ranked more appropriately' },
      { type: 'fix', text: 'Fixed some creators showing inflated engagement rates' },
    ],
  },
  {
    version: '0.2.0',
    date: '2026-03-29',
    title: 'Multi-Platform & Advanced Filters',
    changes: [
      { type: 'feature', text: 'Instagram, YouTube, and Facebook creators now tracked alongside TikTok' },
      { type: 'feature', text: 'Advanced browse filters — filter by country, platform, category, creator tier, and engagement range' },
      { type: 'feature', text: 'Rankings leaderboard — sortable by followers, heat score, engagement, and avg views' },
      { type: 'feature', text: 'Creator profile pages — detailed stats, bio, audience demographics, and similar creators' },
      { type: 'feature', text: 'On-demand Lookup — paste any TikTok, Instagram, or YouTube URL for instant analysis' },
      { type: 'improvement', text: 'Expanded from 200 to 30,000+ creator profiles across Southeast Asia' },
    ],
  },
  {
    version: '0.1.0',
    date: '2026-03-28',
    title: 'Launch — Hello, Southeast Asia',
    changes: [
      { type: 'feature', text: 'Creator discovery platform for Southeast Asia — Malaysia, Indonesia, Thailand, Philippines, Vietnam, Singapore' },
      { type: 'feature', text: 'Heat Score — real-time virality metric combining posting frequency, views, engagement, and growth' },
      { type: 'feature', text: 'Dark mode UI designed for creator research workflows' },
      { type: 'feature', text: '15 content categories — gaming, beauty, food, tech, comedy, fitness, and more' },
    ],
  },
];

export default function ChangelogPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:py-16">
      <div className="mb-12 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card/50 px-4 py-1.5 text-sm text-muted-foreground mb-4">
          <Rocket className="h-3.5 w-3.5 text-accent" />
          <span>What&apos;s New</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold mb-3">Changelog</h1>
        <p className="text-muted-foreground">New features, improvements, and fixes.</p>
      </div>

      <div className="space-y-12">
        {releases.map((release, rIdx) => (
          <div key={release.version} className="relative">
            {rIdx < releases.length - 1 && (
              <div className="absolute left-[19px] top-12 bottom-0 w-px bg-border" />
            )}

            <div className="flex items-start gap-4">
              <div className="relative shrink-0 mt-1">
                <div className={`h-10 w-10 rounded-full flex items-center justify-center text-xs font-bold ${
                  rIdx === 0 ? 'bg-accent text-white' : 'bg-card border border-border text-muted-foreground'
                }`}>
                  {release.version}
                </div>
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3 mb-1">
                  <h2 className="text-lg font-bold">{release.title}</h2>
                  <span className="text-sm text-muted-foreground">{release.date}</span>
                </div>

                <div className="mt-3 space-y-2">
                  {release.changes.map((change, cIdx) => {
                    const config = typeConfig[change.type];
                    const Icon = config.icon;
                    return (
                      <div key={cIdx} className="flex items-start gap-2.5">
                        <span className={`inline-flex items-center gap-1 shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${config.bg} ${config.color}`}>
                          <Icon className="h-3 w-3" />
                          {config.label}
                        </span>
                        <span className="text-sm text-foreground/80 leading-relaxed">{change.text}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-16 text-center">
        <p className="text-sm text-muted-foreground">
          Built with ⚡ by the <span className="font-medium text-foreground">KolBuff</span> team
        </p>
      </div>
    </div>
  );
}
