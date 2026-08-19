import Link from 'next/link';

import { Logo } from '@/components/icons';
import contact from '@/content/contact.json';

export function LandingFooter() {
  return (
    <footer className="relative z-10 border-t border-slate-200/60 bg-[linear-gradient(180deg,rgba(244,246,249,0.6),rgba(240,243,247,0.9))] backdrop-blur-xl dark:border-slate-800/60 dark:bg-[linear-gradient(180deg,rgba(11,16,24,0.6),rgba(8,12,20,0.9))]">
      <div className="container py-6 md:py-8">
        <div className="flex flex-col items-center justify-between gap-6 md:flex-row">
          <div className="flex items-center gap-3">
            <Logo width={28} height={28} className="shrink-0 opacity-70" />
            <span className="text-sm font-medium text-slate-500 dark:text-slate-400">
              Diamond HPC
            </span>
          </div>

          <nav className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
            <Link
              href={contact.navigation.href}
              className="text-sm text-slate-500 transition-colors hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            >
              {contact.navigation.label}
            </Link>
            <Link
              href="https://docs.diamondhpc.ai"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-slate-500 transition-colors hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            >
              Docs
            </Link>
            <Link
              href="/dashboard"
              className="text-sm text-slate-500 transition-colors hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            >
              Workspace
            </Link>
          </nav>

          <p className="text-xs text-slate-400 dark:text-slate-500">
            &copy; {new Date().getFullYear()} Diamond HPC
          </p>
        </div>
      </div>
    </footer>
  );
}
