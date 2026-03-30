'use client';

import { getHeatLevel, getHeatLabel, getHeatColor } from '@/lib/types';
import { cn } from '@/lib/cn';

export function ScoreBadge({ score, size = 'md' }: { score: number; size?: 'sm' | 'md' | 'lg' }) {
  const label = getHeatLabel(score);
  const colors = getHeatColor(score);

  if (size === 'lg') {
    // Gauge-style display for creator profile
    const rotation = (score / 100) * 180 - 90; // -90 to 90 degrees
    return (
      <div className="flex flex-col items-center gap-2">
        {/* Gauge */}
        <div className="relative w-28 h-16 overflow-hidden">
          {/* Background arc */}
          <div className="absolute bottom-0 left-0 w-28 h-28 rounded-full border-[6px] border-surface" 
               style={{ clipPath: 'polygon(0 0, 100% 0, 100% 50%, 0 50%)' }} />
          {/* Colored segments */}
          <div className="absolute bottom-0 left-0 w-28 h-28 rounded-full border-[6px] border-transparent"
               style={{ 
                 borderTopColor: score >= 20 ? '#6b7280' : 'transparent',
                 borderRightColor: score >= 50 ? '#eab308' : 'transparent', 
                 borderBottomColor: 'transparent',
                 borderLeftColor: score >= 80 ? '#ef4444' : score >= 60 ? '#f97316' : 'transparent',
                 clipPath: 'polygon(0 0, 100% 0, 100% 50%, 0 50%)',
                 transform: 'rotate(0deg)',
               }} />
          {/* Score number */}
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 flex flex-col items-center">
            <span className={cn('text-2xl font-bold', colors.text)}>{Math.round(score)}</span>
          </div>
        </div>
        {/* Heat bar */}
        <div className="w-28 h-2 rounded-full bg-surface overflow-hidden flex">
          <div className="h-full bg-gray-600" style={{ width: '20%' }} />
          <div className="h-full bg-yellow-500" style={{ width: '20%' }} />
          <div className="h-full bg-orange-500" style={{ width: '20%' }} />
          <div className="h-full bg-red-500" style={{ width: '20%' }} />
          <div className="h-full bg-red-600" style={{ width: '20%' }} />
        </div>
        {/* Marker showing position */}
        <div className="relative w-28 -mt-2.5">
          <div className="absolute h-3 w-0.5 bg-white rounded-full" 
               style={{ left: `${Math.min(Math.max(score, 2), 98)}%`, transform: 'translateX(-50%)' }} />
        </div>
        <span className={cn('text-sm font-semibold -mt-1', colors.text)}>
          🔥 {label}
        </span>
      </div>
    );
  }

  const sizeClasses = {
    sm: 'h-8 w-8 text-xs',
    md: 'h-12 w-12 text-sm',
    lg: 'h-20 w-20 text-xl',
  };

  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className={cn(
          'rounded-full border-2 flex items-center justify-center font-bold',
          sizeClasses[size],
          colors.border,
          colors.bg,
          colors.text,
        )}
      >
        {Math.round(score)}
      </div>
      {size !== 'sm' && (
        <span className={cn('text-xs font-medium', colors.text)}>
          🔥 {label}
        </span>
      )}
    </div>
  );
}

/** Inline heat pill for tables */
export function HeatPill({ score }: { score: number }) {
  const colors = getHeatColor(score);
  return (
    <span className={cn(
      'inline-flex items-center justify-center h-7 min-w-[2.5rem] rounded-full text-xs font-bold gap-0.5',
      colors.bg,
      colors.text,
    )}>
      {Math.round(score)}
    </span>
  );
}
