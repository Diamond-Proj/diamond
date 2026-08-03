'use client';

import { useEffect, useState, useTransition } from 'react';
import Link from 'next/link';
import { AlertCircle, ArrowRight, ExternalLink } from 'lucide-react';

import type {
  DashboardStats,
  RecentTask,
  StatsResponse
} from '@/components/dashboard/dashboard.types';

import { getUserProfile, updateUserProfile } from '@/lib/taskHandlers';
import { useAuthSessionContext } from '@/lib/auth/session-context';

import { SetupGuide } from '@/components/dashboard/setup-guide';
import { DashboardStatsCards } from '@/components/dashboard/dashboard-stats';
import { RecentActivity } from '@/components/dashboard/recent-activity';
import { QuickActions } from '@/components/dashboard/quick-actions';

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentTasks, setRecentTasks] = useState<RecentTask[]>([]);
  const [isInitialized, setIsInitialized] = useState<boolean | null>(null);
  const [isPending, startTransition] = useTransition();
  const { session } = useAuthSessionContext();
  const user = {
    name: session.userInfo?.name || '',
    email: session.userInfo?.email || '',
    primaryIdentity: session.userInfo?.id || '',
    institution: session.userInfo?.organization || ''
  };

  useEffect(() => {
    startTransition(async () => {
      try {
        const response = await fetch('/api/stats', {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          console.error(`Server error: ${response.statusText}`);
          return;
        }

        const data: StatsResponse = await response.json();

        setStats({
          tasks: data.tasks,
          endpoints: data.endpoints,
          datasets: data.datasets,
          images: data.images
        });
        setRecentTasks(data.recent_tasks || []);
      } catch (error) {
        console.error('Error fetching stats:', error);
      }
    });
  }, [startTransition]);

  useEffect(() => {
    const checkAndUpdateProfile = async () => {
      if (!user.primaryIdentity) {
        // Keep heading in loading state until the auth session resolves an identity.
        return;
      }

      try {
        const profile = await getUserProfile({
          identity_id: user.primaryIdentity
        });

        setIsInitialized(profile.profile?.is_initialized ?? false);

        if (
          !profile.profile ||
          profile.profile.institution !== user.institution
        ) {
          await updateUserProfile({
            identity_id: user.primaryIdentity,
            name: user.name,
            email: user.email,
            institution: user.institution
          });
        }
      } catch (error) {
        console.error('Error updating profile:', error);
        setIsInitialized(true);
      }
    };

    void checkAndUpdateProfile();
  }, [user.email, user.institution, user.name, user.primaryIdentity]);

  return (
    <section className="flex flex-1 flex-col space-y-6">
      <section className="dashboard-card relative overflow-hidden p-5 md:p-6">
        <div className="pointer-events-none absolute -right-16 -top-24 h-56 w-56 rounded-full bg-primary/5 blur-3xl" />
        <div className="pointer-events-none absolute -left-20 -bottom-24 h-52 w-52 rounded-full bg-cyan-400/5 blur-3xl" />

        <div className="relative z-10 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h1
              aria-busy={isInitialized === null}
              className="text-2xl font-bold text-slate-900 dark:text-slate-100"
            >
              {isInitialized === null ? (
                <>
                  <span className="sr-only">Loading dashboard</span>
                  <span
                    aria-hidden="true"
                    className="block h-8 w-56 animate-pulse rounded-lg bg-slate-200/80 dark:bg-slate-700/70"
                  />
                </>
              ) : (
                <>
                  {isInitialized ? 'Welcome back,' : 'Welcome,'}{' '}
                  {user.name.split(' ')[0] || 'Researcher'}
                </>
              )}
            </h1>
          </div>
          <Link
            href="https://docs.diamondhpc.ai"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-300/70 bg-white/80 px-4 py-2 text-sm font-medium text-slate-700 transition-all hover:-translate-y-0.5 hover:border-slate-400 hover:text-slate-900 dark:border-slate-600 dark:bg-slate-900/70 dark:text-slate-200 dark:hover:text-white"
          >
            Documentation
            <ExternalLink className="h-4 w-4" />
          </Link>
        </div>
      </section>

      <SetupGuide />
      <DashboardStatsCards stats={stats} loading={isPending} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <RecentActivity recentTasks={recentTasks} loading={isPending} />
        <QuickActions />
      </div>

      <section className="dashboard-card p-6">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary text-white shadow-sm">
            <AlertCircle className="h-5 w-5" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              New to Diamond HPC?
            </h3>
            <p className="mt-2 text-slate-600 dark:text-slate-300">
              Start by configuring one endpoint, then submit your first test task to validate your runtime stack.
            </p>
            <Link
              href="/endpoints"
              className="mt-4 inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-all hover:-translate-y-0.5 hover:brightness-95"
            >
              Configure Endpoints
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>
    </section>
  );
}
