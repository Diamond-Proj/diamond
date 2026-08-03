'use client';

import Link from 'next/link';
import { Home, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function NotFound() {
  return (
    <div className="relative flex w-full items-center justify-center p-6 min-h-[calc(100dvh-6rem)] md:min-h-[calc(100dvh-7rem)]">
      <div className="w-full max-w-2xl rounded-2xl border border-slate-200/80 bg-[hsl(var(--dashboard-surface))] p-7 shadow-xl dark:border-slate-700/80">
        <div className="space-y-6 text-center">
          <div className="space-y-2">
            <div className="text-5xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              404
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Page Not Found
            </h1>
            <p className="text-slate-600 dark:text-slate-400">
              We couldn&apos;t find this page. It may have moved or no longer exists.
            </p>
          </div>

          <div className="rounded-lg border border-slate-200/80 bg-slate-50/70 p-4 dark:border-slate-700/80 dark:bg-slate-800/55">
            <div className="mb-2 flex items-center gap-2">
              <Search className="h-4 w-4 text-slate-500 dark:text-slate-400" />
              <h3 className="text-sm font-medium text-slate-900 dark:text-slate-100">
                What you can do
              </h3>
            </div>
            <ul className="space-y-1 text-left text-sm text-slate-600 dark:text-slate-400">
              <li>• Check the URL for typos</li>
              <li>• Return to the dashboard</li>
              <li>• Use the sidebar navigation</li>
            </ul>
          </div>

          <div className="flex flex-col justify-center gap-3 sm:flex-row">
            <Button
              asChild
              className="h-11 gap-2 bg-slate-900 text-white hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
            >
              <Link href="/dashboard">
                <Home className="h-4 w-4" />
                Back to Dashboard
              </Link>
            </Button>

            <Button
              variant="outline"
              className="h-11"
              onClick={() => window.history.back()}
            >
              Go Back
            </Button>
          </div>

          <p className="text-sm text-slate-500 dark:text-slate-400">
            Need help? Contact support or check docs.
          </p>
        </div>
      </div>
    </div>
  );
}
