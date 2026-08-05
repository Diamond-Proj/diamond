'use client';

import { CheckCircle, Clock, XCircle, Zap } from 'lucide-react';

import { type RecentTask } from '@/components/dashboard/dashboard.types';

const getActivityIcon = (status: RecentTask['status']) => {
  switch (status) {
    case 'COMPLETED':
      return <CheckCircle className="h-4 w-4" />;
    case 'RUNNING':
      return <Zap className="h-4 w-4" />;
    case 'FAILED':
      return <XCircle className="h-4 w-4" />;
    default:
      return <Clock className="h-4 w-4" />;
  }
};

const getActivityColor = (status: RecentTask['status']) => {
  switch (status) {
    case 'COMPLETED':
      return 'bg-emerald-600';
    case 'RUNNING':
      return 'bg-sky-600';
    case 'FAILED':
      return 'bg-rose-600';
    default:
      return 'bg-slate-600';
  }
};

const getStatusBadgeStyle = (status: RecentTask['status']) => {
  switch (status) {
    case 'COMPLETED':
      return 'border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300';
    case 'RUNNING':
      return 'border-sky-300 bg-sky-50 text-sky-700 dark:border-sky-700 dark:bg-sky-900/20 dark:text-sky-300';
    case 'FAILED':
      return 'border-rose-300 bg-rose-50 text-rose-700 dark:border-rose-700 dark:bg-rose-900/20 dark:text-rose-300';
    default:
      return 'border-slate-300 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-900/20 dark:text-slate-300';
  }
};

const formatTimeAgo = (timeString: string) => {
  try {
    const date = new Date(timeString);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffInSeconds < 60) return `${diffInSeconds} seconds ago`;
    if (diffInSeconds < 3600) {
      const minutes = Math.floor(diffInSeconds / 60);
      return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    }
    if (diffInSeconds < 86400) {
      const hours = Math.floor(diffInSeconds / 3600);
      return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    }

    const days = Math.floor(diffInSeconds / 86400);
    return `${days} day${days > 1 ? 's' : ''} ago`;
  } catch {
    return timeString;
  }
};

const formatDateTime = (timeString: string) => {
  try {
    const date = new Date(timeString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  } catch {
    return timeString;
  }
};

export function RecentActivity({
  recentTasks,
  loading
}: {
  recentTasks: RecentTask[];
  loading: boolean;
}) {
  return (
    <section className="dashboard-card flex max-h-130 min-h-0 flex-col overflow-hidden p-6">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
        Recent Activity
      </h3>

      <div className="mt-5 min-h-0 flex-1 overflow-y-auto pr-1">
        <div className="flex flex-col gap-3">
          {loading &&
            [...Array(4)].map((_, index) => (
              <div
                key={index}
                className="flex animate-pulse items-start gap-4 rounded-2xl border border-slate-200/70 bg-slate-100/60 p-4 dark:border-slate-700/60 dark:bg-slate-800/40"
              >
                <div className="h-10 w-10 rounded-xl bg-slate-200 dark:bg-slate-700" />
                <div className="flex-1 space-y-2.5">
                  <div className="h-4 w-40 rounded bg-slate-200 dark:bg-slate-700" />
                  <div className="h-3 w-56 rounded bg-slate-200 dark:bg-slate-700" />
                  <div className="h-3 w-36 rounded bg-slate-200 dark:bg-slate-700" />
                </div>
              </div>
            ))}

          {!loading && recentTasks.length === 0 && (
            <div className="rounded-2xl border border-dashed border-slate-300/80 bg-slate-50/80 p-10 text-center dark:border-slate-700 dark:bg-slate-900/30">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-slate-200 text-slate-500 dark:bg-slate-800 dark:text-slate-300">
                <Clock className="h-5 w-5" />
              </div>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
                No recent tasks found
              </p>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Tasks will appear here once jobs are submitted
              </p>
            </div>
          )}

          {!loading &&
            recentTasks.map((task) => (
              <article
                key={task.task_id}
                className="group rounded-2xl border border-slate-200/70 bg-white/75 p-4 transition-all duration-300 hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-sm dark:border-slate-700/60 dark:bg-slate-900/40 dark:hover:border-slate-600"
              >
                <div className="flex items-start gap-4">
                  <div
                    className={`mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-white shadow-sm ${getActivityColor(task.status)}`}
                  >
                    {getActivityIcon(task.status)}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <p className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
                        {task.name}
                      </p>
                      <span
                        className={`inline-flex shrink-0 items-center rounded-full border px-3 py-1 text-xs font-semibold ${getStatusBadgeStyle(task.status)}`}
                      >
                        {task.status}
                      </span>
                    </div>

                    <div className="mt-3 grid gap-1 text-xs text-slate-500 dark:text-slate-400">
                      <p>
                        <span className="font-medium text-slate-700 dark:text-slate-300">
                          Created:
                        </span>{' '}
                        {formatDateTime(task.create_time)}
                      </p>
                      <p>
                        <span className="font-medium text-slate-700 dark:text-slate-300">
                          Updated:
                        </span>{' '}
                        {formatTimeAgo(task.last_update_time)}
                      </p>
                      <p
                        className="truncate"
                        style={{ fontFamily: 'var(--font-mono)' }}
                        title={task.task_id}
                      >
                        <span className="font-medium text-slate-700 dark:text-slate-300">
                          Task ID:
                        </span>{' '}
                        {task.task_id}
                      </p>
                    </div>
                  </div>
                </div>
              </article>
            ))}
        </div>
      </div>
    </section>
  );
}
