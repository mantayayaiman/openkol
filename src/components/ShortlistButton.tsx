'use client';

import { useState, useEffect, useCallback } from 'react';
import { Heart } from 'lucide-react';
import { isInShortlist, addToShortlist, removeFromShortlist, ShortlistItem } from '@/lib/shortlist';
import { cn } from '@/lib/cn';

interface ShortlistButtonProps {
  creator: ShortlistItem;
  size?: 'sm' | 'md';
}

export function ShortlistButton({ creator, size = 'sm' }: ShortlistButtonProps) {
  const [inList, setInList] = useState(false);

  const check = useCallback(() => {
    setInList(isInShortlist(creator.id));
  }, [creator.id]);

  useEffect(() => {
    check();
    window.addEventListener('shortlist-change', check);
    return () => window.removeEventListener('shortlist-change', check);
  }, [check]);

  const toggle = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (inList) {
      removeFromShortlist(creator.id);
    } else {
      addToShortlist(creator);
    }
    setInList(!inList);
  };

  const sizeClasses = size === 'sm'
    ? 'h-8 w-8'
    : 'h-10 w-10';
  const iconSize = size === 'sm' ? 'h-4 w-4' : 'h-5 w-5';

  return (
    <button
      onClick={toggle}
      title={inList ? 'Remove from shortlist' : 'Add to shortlist'}
      className={cn(
        'rounded-full flex items-center justify-center transition-all duration-200',
        sizeClasses,
        inList
          ? 'bg-pink-500/20 text-pink-400 hover:bg-pink-500/30'
          : 'bg-card hover:bg-card-hover text-muted-foreground hover:text-pink-400 border border-border'
      )}
    >
      <Heart className={cn(iconSize, inList && 'fill-current')} />
    </button>
  );
}
