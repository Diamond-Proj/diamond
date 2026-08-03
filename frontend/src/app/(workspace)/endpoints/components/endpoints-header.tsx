'use client';

import { Loader2, RefreshCw } from 'lucide-react';

interface EndpointsHeaderProps {
  isRefreshing: boolean;
  onRefresh: () => void;
}

export function EndpointsHeader({
  isRefreshing,
  onRefresh
}: EndpointsHeaderProps) {
  return (
    <section className="dashboard-card relative overflow-hidden p-5 md:p-6">
      <div className="pointer-events-none absolute -right-10 -top-16 h-40 w-40 rounded-full bg-emerald-400/6 blur-2xl" />
      <div className="pointer-events-none absolute -left-8 -bottom-12 h-36 w-36 rounded-full bg-primary/5 blur-2xl" />

      <div className="relative z-10 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            Endpoint Management
          </h1>
        </div>

        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="group inline-flex cursor-pointer items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm transition-colors duration-200 hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isRefreshing ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Refreshing...
            </>
          ) : (
            <>
              <RefreshCw className="h-4 w-4 transition-transform duration-200 group-hover:scale-110" />
              Refresh Endpoints
            </>
          )}
        </button>
      </div>
    </section>
  );
}
