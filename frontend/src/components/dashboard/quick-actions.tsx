'use client';

import Link from 'next/link';
import { type ComponentType } from 'react';
import { ChevronRight, Container, Cpu, Database } from 'lucide-react';

import { TaskIcon } from '@/components/icons';

type Action = {
  href: string;
  title: string;
  description: string;
  icon: ComponentType<{ className?: string }>;
  iconSurface: string;
  cardSurface: string;
};

const actions: Action[] = [
  {
    href: '/images',
    title: 'Images',
    description: 'Build and manage container images for HPC workloads',
    icon: Container,
    iconSurface: 'bg-sky-600',
    cardSurface: 'bg-sky-50/70 dark:bg-sky-900/18'
  },
  {
    href: '/datasets',
    title: 'Datasets',
    description: 'Register and manage data collections for compute tasks',
    icon: Database,
    iconSurface: 'bg-emerald-600',
    cardSurface: 'bg-emerald-50/70 dark:bg-emerald-900/18'
  },
  {
    href: '/tasks',
    title: 'Tasks',
    description: 'Submit jobs and monitor execution status in real time',
    icon: TaskIcon,
    iconSurface: 'bg-orange-600',
    cardSurface: 'bg-orange-50/70 dark:bg-orange-900/18'
  },
  {
    href: '/endpoints',
    title: 'Endpoints',
    description: 'Configure Globus Compute endpoints and runtime settings',
    icon: Cpu,
    iconSurface: 'bg-slate-600',
    cardSurface: 'bg-slate-50/85 dark:bg-slate-900/40'
  }
];

export function QuickActions() {
  return (
    <section className="dashboard-card flex max-h-130 min-h-0 flex-col overflow-hidden p-6">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
        Quick Actions
      </h3>
      <div className="mt-5 min-h-0 flex-1 overflow-y-auto pr-1">
        <div className="flex flex-col gap-3">
          {actions.map((action) => (
            <Link
              key={action.href}
              href={action.href}
              className={`group flex items-center rounded-2xl border border-slate-200/65 p-4 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-md dark:border-slate-700/60 ${action.cardSurface}`}
            >
              <div
                className={`mr-4 flex h-10 w-10 items-center justify-center rounded-xl text-white shadow-sm transition-transform duration-300 group-hover:scale-105 ${action.iconSurface}`}
              >
                <action.icon className="h-5 w-5" />
              </div>

              <div className="flex-1">
                <p className="font-semibold text-slate-900 dark:text-slate-100">
                  {action.title}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  {action.description}
                </p>
              </div>

              <ChevronRight className="h-5 w-5 text-slate-400 transition-all duration-300 group-hover:translate-x-1 group-hover:text-slate-700 dark:group-hover:text-slate-200" />
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
