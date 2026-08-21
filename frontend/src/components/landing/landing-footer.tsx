import Image from 'next/image';
import Link from 'next/link';

import { Logo } from '@/components/icons';
import contact from '@/content/contact.json';
import { landingPageContent } from '@/content/landing-page-content';

export function LandingFooter() {
  const { funding } = landingPageContent;

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

        <div className="mt-6 flex flex-col items-center gap-3 border-t border-slate-200/70 pt-5 lg:flex-row lg:justify-between dark:border-slate-800/70">
          <p className="text-center text-xs leading-5 text-slate-400 lg:text-left dark:text-slate-500">
            {funding.acknowledgement}
          </p>

          <ul
            aria-label="NSF awards"
            className="flex flex-wrap items-center justify-center gap-2 lg:justify-end"
          >
            {funding.awards.map((award) => (
              <li key={award.number} className="leading-none">
                <Link
                  href={award.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`View NSF Award ${award.number}`}
                  className="inline-flex rounded-sm opacity-80 transition-[opacity,transform] duration-200 hover:-translate-y-px hover:opacity-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0e79b2]"
                >
                  <Image
                    src={award.badgeSrc}
                    alt={`NSF Award ${award.number}`}
                    width={104}
                    height={20}
                    unoptimized
                  />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </footer>
  );
}
