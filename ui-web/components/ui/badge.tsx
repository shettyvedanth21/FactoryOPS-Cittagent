import React from 'react';
import { cn } from '@/lib/utils';

type BadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'info';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-slate-100 text-slate-700',
  success: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  warning: 'bg-amber-100 text-amber-700 border-amber-200',
  error: 'bg-red-100 text-red-700 border-red-200',
  info: 'bg-blue-100 text-blue-700 border-blue-200',
};

export function Badge({
  children,
  variant = 'default',
  className,
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border',
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const normalizedStatus = status?.toLowerCase() || 'unknown';
  
  let variant: BadgeVariant = 'default';
  
  if (['active', 'online', 'running', 'healthy', 'up'].includes(normalizedStatus)) {
    variant = 'success';
  } else if (['inactive', 'offline', 'stopped', 'down'].includes(normalizedStatus)) {
    variant = 'error';
  } else if (['warning', 'degraded', 'maintenance'].includes(normalizedStatus)) {
    variant = 'warning';
  } else if (['paused', 'pending'].includes(normalizedStatus)) {
    variant = 'info';
  }
  
  return (
    <Badge variant={variant} className={className}>
      <span className="flex items-center gap-1.5">
        <span
          className={cn(
            'w-1.5 h-1.5 rounded-full',
            variant === 'success' && 'bg-emerald-500',
            variant === 'error' && 'bg-red-500',
            variant === 'warning' && 'bg-amber-500',
            variant === 'info' && 'bg-blue-500',
            variant === 'default' && 'bg-slate-500'
          )}
        />
        <span className="capitalize">{status}</span>
      </span>
    </Badge>
  );
}
