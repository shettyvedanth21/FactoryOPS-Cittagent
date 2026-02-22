import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatIST(utcTimestamp: string | null): string {
  if (!utcTimestamp) return 'No data received';
  
  try {
    const date = new Date(utcTimestamp);
    if (isNaN(date.getTime())) return 'Invalid date';
    
    // Convert UTC to IST (UTC + 5:30)
    const istOffset = 5.5 * 60 * 60 * 1000; // 5 hours 30 minutes in ms
    const istDate = new Date(date.getTime() + istOffset);
    
    return istDate.toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
      timeZone: 'Asia/Kolkata'
    }) + ' IST';
  } catch {
    return 'Invalid date';
  }
}

export function getRelativeTime(utcTimestamp: string | null): string {
  if (!utcTimestamp) return '';
  
  try {
    const date = new Date(utcTimestamp);
    if (isNaN(date.getTime())) return '';
    
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    
    if (diffSec < 5) return '(just now)';
    if (diffSec < 60) return `(${diffSec} seconds ago)`;
    if (diffMin < 60) return `(${diffMin} minute${diffMin > 1 ? 's' : ''} ago)`;
    if (diffHour < 24) return `(${diffHour} hour${diffHour > 1 ? 's' : ''} ago)`;
    return '';
  } catch {
    return '';
  }
}
