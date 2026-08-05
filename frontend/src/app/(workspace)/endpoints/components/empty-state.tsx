'use client';

import { CheckCircle2, Plus, Server } from 'lucide-react';

import { Button } from '@/components/ui/button';

interface EmptyStateProps {
  type: 'managed' | 'available';
  onAction?: () => void;
}

export function EmptyState({ type, onAction }: EmptyStateProps) {
  if (type === 'managed') {
    return (
      <div className="dashboard-card flex flex-col items-center justify-center py-16">
        <div className="rounded-full bg-slate-200/70 p-6 dark:bg-slate-800/70">
          <Server className="h-12 w-12 text-slate-500 dark:text-slate-300" />
        </div>
        <h3 className="mt-4 text-lg font-semibold text-slate-900 dark:text-slate-100">
          No Managed Endpoints
        </h3>
        <p className="mt-2 text-center text-sm text-slate-600 dark:text-slate-300">
          Add endpoints from the &quot;Available Endpoints&quot; tab to start
          managing them.
        </p>
        {onAction && (
          <Button onClick={onAction} className="mt-6 cursor-pointer gap-2">
            <Plus className="h-4 w-4" />
            Browse Available Endpoints
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="dashboard-card flex flex-col items-center justify-center py-16">
      <div className="rounded-full bg-emerald-100 p-6 dark:bg-emerald-900/25">
        <CheckCircle2 className="h-12 w-12 text-emerald-600 dark:text-emerald-400" />
      </div>
      <h3 className="mt-4 text-lg font-semibold text-slate-900 dark:text-slate-100">
        All Endpoints Managed
      </h3>
      <p className="mt-2 text-center text-sm text-slate-600 dark:text-slate-300">
        All your available endpoints are already under Diamond management.
      </p>
    </div>
  );
}
