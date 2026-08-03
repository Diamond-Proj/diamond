'use client';

import { AlertCircle, CheckCircle2, FolderOpen, Server } from 'lucide-react';
import { type ComponentType } from 'react';

interface EndpointStatsProps {
  totalEndpoints: number;
  managedEndpoints: number;
  availableEndpoints: number;
  configuredEndpoints: number;
}

type StatItem = {
  label: string;
  value: number;
  icon: ComponentType<{ className?: string }>;
  iconSurface: string;
  accent: string;
};

export function EndpointStats({
  totalEndpoints,
  managedEndpoints,
  availableEndpoints,
  configuredEndpoints
}: EndpointStatsProps) {
  const statItems: StatItem[] = [
    {
      label: 'Total Endpoints',
      value: totalEndpoints,
      icon: Server,
      iconSurface: 'bg-violet-600',
      accent: 'bg-violet-500/6 dark:bg-violet-500/12'
    },
    {
      label: 'Managed',
      value: managedEndpoints,
      icon: CheckCircle2,
      iconSurface: 'bg-sky-600',
      accent: 'bg-sky-500/6 dark:bg-sky-500/12'
    },
    {
      label: 'Available',
      value: availableEndpoints,
      icon: AlertCircle,
      iconSurface: 'bg-amber-600',
      accent: 'bg-amber-500/6 dark:bg-amber-500/12'
    },
    {
      label: 'Configured',
      value: configuredEndpoints,
      icon: FolderOpen,
      iconSurface: 'bg-emerald-600',
      accent: 'bg-emerald-500/6 dark:bg-emerald-500/12'
    }
  ];

  return (
    <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
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
                  {stat.value}
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
