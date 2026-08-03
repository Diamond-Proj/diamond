'use client';

import { DashboardIcon, PersonIcon } from '@radix-ui/react-icons';
import { Container, Cpu, Database } from 'lucide-react';

import { TaskIcon } from '@/components/icons';

import { NavItem } from './nav-item';

const workspaceLinks = [
  { href: '/dashboard', label: 'Dashboard', Icon: DashboardIcon },
  { href: '/images', label: 'Images', Icon: Container },
  { href: '/datasets', label: 'Datasets', Icon: Database },
  { href: '/tasks', label: 'Tasks', Icon: TaskIcon }
];

const settingsLinks = [
  { href: '/profile', label: 'Profile', Icon: PersonIcon },
  { href: '/endpoints', label: 'Endpoints', Icon: Cpu }
];

export function SideNav({ compact = false }: { compact?: boolean }) {
  return (
    <nav className="flex h-full min-h-0 flex-col px-2 text-sm font-medium">
      <p
        data-desktop-nav-section-label
        className={`overflow-hidden px-3 text-[11px] font-semibold tracking-[0.12em] whitespace-nowrap text-slate-500 uppercase transition-[max-height,opacity,padding,margin] duration-300 ease-out dark:text-slate-400 ${
          compact
            ? 'mb-0 max-h-0 pb-0 opacity-0'
            : 'mb-0 max-h-8 pb-2 opacity-100'
        }`}
      >
        Workspace
      </p>

      <div className="space-y-0.5">
        {workspaceLinks.map(({ href, label, Icon }, index) => (
          <div
            key={href}
            className={
              index > 0
                ? 'relative pt-1 before:absolute before:top-0 before:right-4 before:left-4 before:h-px before:bg-slate-200/35 dark:before:bg-slate-700/35'
                : undefined
            }
          >
            <NavItem
              href={href}
              label={label}
              compact={compact}
              icon={<Icon className="h-4.5 w-4.5 shrink-0" />}
            />
          </div>
        ))}
      </div>

      <div className="my-4 border-t border-slate-200/70 dark:border-slate-700/70" />

      <p
        data-desktop-nav-section-label
        className={`overflow-hidden px-3 text-[11px] font-semibold tracking-[0.12em] whitespace-nowrap text-slate-500 uppercase transition-[max-height,opacity,padding,margin] duration-300 ease-out dark:text-slate-400 ${
          compact
            ? 'mb-0 max-h-0 pb-0 opacity-0'
            : 'mb-0 max-h-8 pb-2 opacity-100'
        }`}
      >
        Account
      </p>
      <div className="space-y-0.5">
        {settingsLinks.map(({ href, label, Icon }, index) => (
          <div
            key={href}
            className={
              index > 0
                ? 'relative pt-1 before:absolute before:top-0 before:right-4 before:left-4 before:h-px before:bg-slate-200/35 dark:before:bg-slate-700/35'
                : undefined
            }
          >
            <NavItem
              href={href}
              label={label}
              compact={compact}
              icon={<Icon className="h-4.5 w-4.5 shrink-0" />}
            />
          </div>
        ))}
      </div>
    </nav>
  );
}
