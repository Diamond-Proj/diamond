'use client';

import Link from 'next/link';
import { type ComponentType } from 'react';
import {
  Activity,
  BarChart3,
  CheckCircle,
  Container,
  Database,
  Globe,
  Lock,
  Server,
  WifiOff,
  XCircle
} from 'lucide-react';

import { type DashboardStats } from '@/components/dashboard/dashboard.types';

type Metric = {
  label: string;
  value: number;
  rate: number;
  icon: ComponentType<{ className?: string }>;
  bar: string;
  iconColor: string;
};

type StatCard = {
  href: string;
  title: string;
  total: number;
  icon: ComponentType<{ className?: string }>;
  accent: string;
  iconSurface: string;
  metrics: Metric[];
};

const ratio = (value: number, total: number) =>
  total > 0 ? (value / total) * 100 : 0;

function StatusMetric({ metric, loading }: { metric: Metric; loading: boolean }) {
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-xs">
        <span className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
          <metric.icon className={`h-3.5 w-3.5 ${metric.iconColor}`} />
          {metric.label}
        </span>
        <span className="font-semibold text-slate-900 dark:text-slate-100">
          {loading ? '--' : metric.value}
          <span className="ml-1 font-medium text-slate-500 dark:text-slate-400">
            ({loading ? '-%%' : `${metric.rate.toFixed(1)}%`})
          </span>
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-200/80 dark:bg-slate-700/70">
        <div
          className={`h-full rounded-full transition-all duration-500 ${metric.bar}`}
          style={{ width: `${metric.rate}%` }}
        />
      </div>
    </div>
  );
}

function DashboardStatCard({
  href,
  title,
  total,
  icon: Icon,
  accent,
  iconSurface,
  metrics,
  loading
}: StatCard & { loading: boolean }) {
  return (
    <Link
      href={href}
      className="group dashboard-card relative overflow-hidden p-5 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg"
    >
      <div className={`pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100 ${accent}`} />

      <div className="relative z-10">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
              {title}
            </p>
            <p className="mt-1 text-3xl font-bold text-slate-900 dark:text-slate-100">
              {loading ? '--' : total.toLocaleString()}
            </p>
          </div>
          <div
            className={`flex h-11 w-11 items-center justify-center rounded-xl text-white shadow-sm transition-transform duration-300 group-hover:scale-105 ${iconSurface}`}
          >
            <Icon className="h-5 w-5" />
          </div>
        </div>

        <div className="space-y-3">
          {metrics.map((metric) => (
            <StatusMetric key={metric.label} metric={metric} loading={loading} />
          ))}
        </div>
      </div>
    </Link>
  );
}

export function DashboardStatsCards({
  stats,
  loading
}: {
  stats: DashboardStats | null;
  loading: boolean;
}) {
  const tasksTotal = stats
    ? stats.tasks.completed + stats.tasks.running + stats.tasks.failed
    : 0;
  const endpointsTotal = stats
    ? stats.endpoints.online + stats.endpoints.offline
    : 0;
  const datasetsTotal = stats
    ? stats.datasets.public + stats.datasets.private
    : 0;
  const imagesTotal = stats ? stats.images.public + stats.images.private : 0;

  const cards: StatCard[] = [
    {
      href: '/tasks',
      title: 'Tasks',
      total: tasksTotal,
      icon: BarChart3,
      accent: 'bg-sky-500/6 dark:bg-sky-500/12',
      iconSurface: 'bg-sky-600',
      metrics: [
        {
          label: 'Completed',
          value: stats?.tasks.completed ?? 0,
          rate: ratio(stats?.tasks.completed ?? 0, tasksTotal),
          icon: CheckCircle,
          bar: 'bg-emerald-500',
          iconColor: 'text-emerald-500'
        },
        {
          label: 'Running',
          value: stats?.tasks.running ?? 0,
          rate: ratio(stats?.tasks.running ?? 0, tasksTotal),
          icon: Activity,
          bar: 'bg-amber-500',
          iconColor: 'text-amber-500'
        },
        {
          label: 'Failed',
          value: stats?.tasks.failed ?? 0,
          rate: ratio(stats?.tasks.failed ?? 0, tasksTotal),
          icon: XCircle,
          bar: 'bg-rose-500',
          iconColor: 'text-rose-500'
        }
      ]
    },
    {
      href: '/endpoints',
      title: 'Endpoints',
      total: endpointsTotal,
      icon: Server,
      accent: 'bg-emerald-500/6 dark:bg-emerald-500/12',
      iconSurface: 'bg-emerald-600',
      metrics: [
        {
          label: 'Online',
          value: stats?.endpoints.online ?? 0,
          rate: ratio(stats?.endpoints.online ?? 0, endpointsTotal),
          icon: CheckCircle,
          bar: 'bg-emerald-500',
          iconColor: 'text-emerald-500'
        },
        {
          label: 'Offline',
          value: stats?.endpoints.offline ?? 0,
          rate: ratio(stats?.endpoints.offline ?? 0, endpointsTotal),
          icon: WifiOff,
          bar: 'bg-rose-500',
          iconColor: 'text-rose-500'
        }
      ]
    },
    {
      href: '/datasets',
      title: 'Datasets',
      total: datasetsTotal,
      icon: Database,
      accent: 'bg-indigo-500/6 dark:bg-indigo-500/12',
      iconSurface: 'bg-indigo-600',
      metrics: [
        {
          label: 'Public',
          value: stats?.datasets.public ?? 0,
          rate: ratio(stats?.datasets.public ?? 0, datasetsTotal),
          icon: Globe,
          bar: 'bg-sky-500',
          iconColor: 'text-sky-500'
        },
        {
          label: 'Private',
          value: stats?.datasets.private ?? 0,
          rate: ratio(stats?.datasets.private ?? 0, datasetsTotal),
          icon: Lock,
          bar: 'bg-slate-500',
          iconColor: 'text-slate-500'
        }
      ]
    },
    {
      href: '/images',
      title: 'Images',
      total: imagesTotal,
      icon: Container,
      accent: 'bg-orange-500/6 dark:bg-orange-500/12',
      iconSurface: 'bg-orange-600',
      metrics: [
        {
          label: 'Public',
          value: stats?.images.public ?? 0,
          rate: ratio(stats?.images.public ?? 0, imagesTotal),
          icon: Globe,
          bar: 'bg-sky-500',
          iconColor: 'text-sky-500'
        },
        {
          label: 'Private',
          value: stats?.images.private ?? 0,
          rate: ratio(stats?.images.private ?? 0, imagesTotal),
          icon: Lock,
          bar: 'bg-slate-500',
          iconColor: 'text-slate-500'
        }
      ]
    }
  ];

  return (
    <section className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <DashboardStatCard key={card.title} {...card} loading={loading} />
      ))}
    </section>
  );
}
