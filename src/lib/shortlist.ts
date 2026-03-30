'use client';

const STORAGE_KEY = 'openkol_shortlist';

export interface ShortlistItem {
  id: number;
  name: string;
  username: string;
  platform: string;
  profile_image: string;
  followers: number;
  engagement_rate: number;
  heat_score: number;
  country: string;
  addedAt: string;
}

export function getShortlist(): ShortlistItem[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function addToShortlist(item: ShortlistItem): void {
  const list = getShortlist();
  if (list.some(i => i.id === item.id)) return;
  list.push({ ...item, addedAt: new Date().toISOString() });
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  window.dispatchEvent(new Event('shortlist-change'));
}

export function removeFromShortlist(id: number): void {
  const list = getShortlist().filter(i => i.id !== id);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  window.dispatchEvent(new Event('shortlist-change'));
}

export function isInShortlist(id: number): boolean {
  return getShortlist().some(i => i.id === id);
}

export function clearShortlist(): void {
  localStorage.removeItem(STORAGE_KEY);
  window.dispatchEvent(new Event('shortlist-change'));
}

export function exportShortlistCSV(): void {
  const list = getShortlist();
  if (list.length === 0) return;

  const headers = ['Name', 'Username', 'Platform', 'Country', 'Followers', 'Engagement Rate', 'Heat Score', 'Added At'];
  const rows = list.map(item => [
    item.name,
    `@${item.username}`,
    item.platform,
    item.country,
    item.followers.toString(),
    item.engagement_rate.toFixed(2) + '%',
    Math.round(item.heat_score).toString(),
    item.addedAt,
  ]);

  const csv = [headers, ...rows].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `openkol-shortlist-${new Date().toISOString().split('T')[0]}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
