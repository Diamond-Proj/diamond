'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';

import { Logo } from '@/components/icons';
import ThemeToggle from '@/components/layout/theme-toggle';
import type { LandingPageContent } from '@/content/landing-page-content';

function HeaderActionLink({
  href,
  label,
  external = false
}: {
  href: string;
  label: string;
  external?: boolean;
}) {
  return (
    <Link
      href={href}
      target={external ? '_blank' : undefined}
      rel={external ? 'noopener noreferrer' : undefined}
      className="hidden h-10 items-center rounded-full border border-white/80 bg-white/72 px-4 text-sm font-medium text-slate-700 shadow-[0_8px_22px_rgba(15,23,42,0.06)] backdrop-blur-xl transition-all duration-200 hover:-translate-y-0.5 hover:bg-white hover:text-slate-950 md:inline-flex dark:border-slate-700/80 dark:bg-slate-950/68 dark:text-slate-200 dark:shadow-[0_14px_30px_rgba(2,6,23,0.24)] dark:hover:border-slate-500 dark:hover:bg-slate-900"
    >
      {label}
    </Link>
  );
}

function PrimaryHeaderCta({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center justify-center gap-2 rounded-full bg-[#c90a37] px-5 py-3 text-sm font-semibold text-white shadow-[0_14px_30px_rgba(201,10,55,0.16)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-[#b50931] hover:shadow-[0_18px_34px_rgba(201,10,55,0.2)] dark:bg-[#c90a37] dark:text-white dark:shadow-[0_14px_30px_rgba(0,0,0,0.24)]"
    >
      {label}
    </Link>
  );
}

export function LandingHeader({
  header
}: {
  header: LandingPageContent['header'];
}) {
  const [isVisible, setIsVisible] = useState(true);
  const lastScrollY = useRef(0);

  useEffect(() => {
    const onScroll = () => {
      const currentScrollY = window.scrollY;

      if (currentScrollY < 24) {
        setIsVisible(true);
        lastScrollY.current = currentScrollY;
        return;
      }

      if (currentScrollY > lastScrollY.current && currentScrollY > 120) {
        setIsVisible(false);
      } else if (currentScrollY < lastScrollY.current) {
        setIsVisible(true);
      }

      lastScrollY.current = currentScrollY;
    };

    window.addEventListener('scroll', onScroll, { passive: true });

    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-transform duration-300 ease-out ${
        isVisible ? 'translate-y-0' : '-translate-y-[120%]'
      }`}
    >
      <div className="container py-4">
        <div className="mx-auto flex max-w-[1240px] items-center justify-between gap-4 rounded-xl border border-white/70 bg-white/64 px-4 py-3 shadow-[0_24px_80px_rgba(15,23,42,0.08)] backdrop-blur-2xl md:px-5 dark:border-slate-800/80 dark:bg-slate-950/72 dark:shadow-[0_28px_90px_rgba(2,6,23,0.4)]">
          <div className="flex min-w-0 items-center gap-3">
            <div className="rounded-lg border border-white/80 bg-white/78 p-1.5 shadow-[0_8px_24px_rgba(15,23,42,0.08)] dark:border-slate-800/80 dark:bg-slate-900/86 dark:shadow-none">
              <Logo width={42} height={42} className="shrink-0" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-slate-950 dark:text-slate-50">
                {header.eyebrow}
              </p>
              <p className="truncate text-xs tracking-[0.18em] text-slate-500 uppercase dark:text-slate-400">
                {header.label}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <HeaderActionLink
              href={header.docsHref}
              label={header.docsLabel}
              external
            />
            <ThemeToggle triggerClassName="rounded-full border-white/80 bg-white/72 shadow-[0_8px_22px_rgba(15,23,42,0.06)] backdrop-blur-xl dark:border-slate-700/80 dark:bg-slate-950/68 dark:shadow-[0_14px_30px_rgba(2,6,23,0.24)]" />
            <PrimaryHeaderCta
              href={header.primaryCta.href}
              label={header.primaryCta.label}
            />
          </div>
        </div>
      </div>
    </header>
  );
}
