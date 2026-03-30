'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Menu, X, Trophy, Search, LayoutGrid, ScanLine, Heart, Rocket, BookOpen } from 'lucide-react';
import { cn } from '@/lib/cn';

const NAV_ITEMS = [
  { href: '/', label: 'Home', icon: null },
  { href: '/browse', label: 'Browse', icon: LayoutGrid },
  { href: '/rankings', label: 'Rankings', icon: Trophy },
  { href: '/lookup', label: 'Lookup', icon: ScanLine },
  { href: '/shortlist', label: 'Shortlist', icon: Heart },
  { href: '/blog', label: 'Blog', icon: BookOpen },
  { href: '/changelog', label: 'Changelog', icon: Rocket },
];

export function NavBar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-xl">
      <div className="mx-auto max-w-7xl px-4 flex items-center justify-between h-14">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-1.5 text-lg font-bold tracking-tight">
          Kol<span className="text-accent">Buff</span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden sm:flex items-center gap-1">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
                pathname === item.href
                  ? 'bg-accent/10 text-accent'
                  : 'text-muted-foreground hover:text-foreground hover:bg-card'
              )}
            >
              {item.icon && <item.icon className="h-3.5 w-3.5" />}
              {item.label}
            </Link>
          ))}
        </div>

        {/* Mobile toggle */}
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="sm:hidden p-2 rounded-lg text-muted-foreground hover:text-foreground"
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="sm:hidden border-t border-border bg-background px-4 py-3 space-y-1">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className={cn(
                'flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                pathname === item.href
                  ? 'bg-accent/10 text-accent'
                  : 'text-muted-foreground hover:text-foreground hover:bg-card'
              )}
            >
              {item.icon && <item.icon className="h-4 w-4" />}
              {item.label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  );
}
