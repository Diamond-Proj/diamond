'use client';

import { CheckCircle, Clock, Loader, Play, XCircle } from 'lucide-react';
import { type ComponentType } from 'react';

import { Task } from '../tasks.types';

interface TaskStatsProps {
  tasks: Task[];
  loading: boolean;
}

type StatItem = {
  label: string;
  value: number;
  icon: ComponentType<{ className?: string }>;
  iconSurface: string;
  accent: string;
};

export function TaskStats({ tasks, loading }: TaskStatsProps) {
  const stats = {
    total: tasks.length,
    running: tasks.filter((task) => task.status === 'RUNNING').length,
    completed: tasks.filter((task) => task.status === 'COMPLETED').length,
    pending: tasks.filter((task) => task.status === 'PENDING').length,
    failed: tasks.filter((task) => task.status === 'FAILED').length
  };

  const statItems: StatItem[] = [
    {
      label: 'Total Tasks',
      value: stats.total,
      icon: Play,
      iconSurface: 'bg-sky-600',
      accent: 'bg-sky-500/6 dark:bg-sky-500/12'
    },
    {
      label: 'Running',
      value: stats.running,
      icon: Loader,
      iconSurface: 'bg-amber-600',
      accent: 'bg-amber-500/6 dark:bg-amber-500/12'
    },
    {
      label: 'Completed',
      value: stats.completed,
      icon: CheckCircle,
      iconSurface: 'bg-emerald-600',
      accent: 'bg-emerald-500/6 dark:bg-emerald-500/12'
    },
    {
      label: 'Pending',
      value: stats.pending,
      icon: Clock,
      iconSurface: 'bg-orange-600',
      accent: 'bg-orange-500/6 dark:bg-orange-500/12'
    },
    {
      label: 'Failed',
      value: stats.failed,
      icon: XCircle,
      iconSurface: 'bg-rose-600',
      accent: 'bg-rose-500/6 dark:bg-rose-500/12'
    }
  ];

  return (
    <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
      {statItems.map((stat) => {
        const Icon = stat.icon;
        return (
          <div
            key={stat.label}
            className="group dashboard-card relative overflow-hidden p-5 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg"
          >
            <div className={`pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100 ${stat.accent}`} />
            <div className="relative z-10 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
                  {stat.label}
                </p>
                <p className="text-3xl font-bold text-slate-900 dark:text-slate-100">
                  {loading ? '--' : stat.value}
                </p>
              </div>
              <div
                className={`flex h-11 w-11 items-center justify-center rounded-xl text-white shadow-sm ${stat.iconSurface}`}
              >
                <Icon className="h-5 w-5" />
              </div>
            </div>
          </div>
        );
      })}
    </section>
  );
}
