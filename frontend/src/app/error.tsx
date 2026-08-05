'use client'; // Error boundaries must be Client Components

import { useEffect } from 'react';
import Link from 'next/link';
import { AlertTriangle, Home, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function Error({
  error,
  reset
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error(error);
  }, [error]);

  return (
    <div className="relative flex w-full items-center justify-center p-6 min-h-[calc(100dvh-6rem)] md:min-h-[calc(100dvh-7rem)]">
      <div className="w-full max-w-2xl rounded-2xl border border-slate-200/80 bg-[hsl(var(--dashboard-surface))] p-7 shadow-xl dark:border-slate-700/80">
        <div className="space-y-6 text-center">
          <div className="flex justify-center">
            <div className="rounded-full bg-red-100 p-4 dark:bg-red-950/30">
              <AlertTriangle className="h-10 w-10 text-red-600 dark:text-red-400" />
            </div>
          </div>

          <div className="space-y-2">
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Something went wrong
            </h1>
            <p className="text-slate-600 dark:text-slate-400">
              An unexpected error occurred while loading this page.
            </p>
          </div>

          <div className="space-y-3 text-left">
            {error.message && (
              <div className="rounded-lg border border-slate-200/80 bg-slate-50/70 p-4 dark:border-slate-700/80 dark:bg-slate-800/55">
                <h3 className="mb-2 font-medium text-slate-900 dark:text-slate-100">
                  Error Message
                </h3>
                <p className="break-words font-mono text-sm text-slate-600 dark:text-slate-400">
                  {error.message}
                </p>
              </div>
            )}

            {error.digest && (
              <div className="rounded-lg border border-slate-200/80 bg-slate-50/70 p-4 dark:border-slate-700/80 dark:bg-slate-800/55">
                <h3 className="mb-2 font-medium text-slate-900 dark:text-slate-100">
                  Error Digest
                </h3>
                <p className="break-words font-mono text-sm text-slate-600 dark:text-slate-400">
                  {error.digest}
                </p>
              </div>
            )}
          </div>

          <div className="flex flex-col justify-center gap-3 sm:flex-row">
            <Button
              onClick={reset}
              className="h-11 gap-2 bg-slate-900 text-white hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
            >
              <RefreshCw className="h-4 w-4" />
              Try again
            </Button>

            <Button asChild variant="outline" className="h-11 gap-2">
              <Link href="/dashboard">
                <Home className="h-4 w-4" />
                Back to Dashboard
              </Link>
            </Button>
          </div>

          <p className="text-sm text-slate-500 dark:text-slate-400">
            If this keeps happening, refresh and try again.
          </p>
        </div>
      </div>
    </div>
  );
}
