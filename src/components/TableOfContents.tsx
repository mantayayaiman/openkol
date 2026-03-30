'use client';

import { useEffect, useState } from 'react';
import type { TOCItem } from '@/lib/blog';
import { cn } from '@/lib/cn';

export function TableOfContents({ items }: { items: TOCItem[] }) {
  const [activeId, setActiveId] = useState('');

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        }
      },
      { rootMargin: '-80px 0px -70% 0px' }
    );

    for (const item of items) {
      const el = document.getElementById(item.id);
      if (el) observer.observe(el);
    }

    return () => observer.disconnect();
  }, [items]);

  if (items.length === 0) return null;

  return (
    <nav className="space-y-1">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">
        On this page
      </p>
      {items.map((item) => (
        <a
          key={item.id}
          href={`#${item.id}`}
          className={cn(
            'block text-sm leading-relaxed transition-colors hover:text-foreground',
            item.level === 3 && 'pl-4',
            item.level === 4 && 'pl-8',
            activeId === item.id
              ? 'text-accent font-medium'
              : 'text-muted-foreground'
          )}
        >
          {item.text}
        </a>
      ))}
    </nav>
  );
}
