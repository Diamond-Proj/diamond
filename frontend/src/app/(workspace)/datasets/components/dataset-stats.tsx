'use client';

import { Database, Globe, Lock } from 'lucide-react';
import { type ComponentType } from 'react';

import { DisplayDataset } from '../datasets.types';

interface DatasetStatsProps {
  datasets: DisplayDataset[];
  loading: boolean;
}

type StatItem = {
  label: string;
  value: number;
  icon: ComponentType<{ className?: string }>;
  iconSurface: string;
  accent: string;
};

export function DatasetStats({ datasets, loading }: DatasetStatsProps) {
  const publicCount = datasets.filter((d) => d.public).length;
  const privateCount = datasets.filter((d) => !d.public).length;

  const statItems: StatItem[] = [
    {
      label: 'Total Datasets',
      value: datasets.length,
      icon: Database,
      iconSurface: 'bg-indigo-600',
      accent: 'bg-indigo-500/6 dark:bg-indigo-500/12'
    },
    {
      label: 'Public',
      value: publicCount,
      icon: Globe,
      iconSurface: 'bg-sky-600',
      accent: 'bg-sky-500/6 dark:bg-sky-500/12'
    },
    {
      label: 'Private',
      value: privateCount,
      icon: Lock,
      iconSurface: 'bg-slate-600',
      accent: 'bg-slate-500/6 dark:bg-slate-500/12'
    }
  ];

  return (
    <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
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
