import type { Metadata } from 'next';
import Link from 'next/link';
import { GitHubLogoIcon } from '@radix-ui/react-icons';
import { ArrowUpRight, Mail } from 'lucide-react';

import { LandingHeader } from '@/components/landing/landing-header';
import { LandingFooter } from '@/components/landing/landing-footer';
import contact from '@/content/contact.json';
import { landingPageContent } from '@/content/landing-page-content';

export const metadata: Metadata = {
  title: 'Contact us',
  description:
    'Contact the Diamond HPC team or contribute to the frontend project on GitHub.'
};

const focusRing =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/45 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-slate-950';

const primaryAction = `contact-action group inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[#c90a37] px-4 text-sm font-semibold text-white shadow-[0_10px_24px_rgba(201,10,55,0.14)] hover:bg-[#b50931] hover:shadow-[0_14px_28px_rgba(201,10,55,0.2)] ${focusRing}`;

const secondaryAction = `contact-action group inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-white/60 px-4 text-sm font-semibold text-slate-700 hover:bg-white hover:text-slate-950 dark:bg-slate-900/65 dark:text-slate-300 dark:hover:bg-slate-900 dark:hover:text-white ${focusRing}`;

function SlackLogo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 54.9 54.9" className={className} aria-hidden="true">
      <path
        fill="#E01E5A"
        d="M12.2 34.5c0 3.4-2.7 6.1-6.1 6.1S0 37.9 0 34.5s2.7-6.1 6.1-6.1h6.1v6.1Zm3.1 0c0-3.4 2.7-6.1 6.1-6.1s6.1 2.7 6.1 6.1v15.3c0 3.4-2.7 6.1-6.1 6.1s-6.1-2.7-6.1-6.1V34.5Z"
      />
      <path
        fill="#36C5F0"
        d="M21.4 12.2c-3.4 0-6.1-2.7-6.1-6.1S18 0 21.4 0s6.1 2.7 6.1 6.1v6.1h-6.1Zm0 3.1c3.4 0 6.1 2.7 6.1 6.1s-2.7 6.1-6.1 6.1H6.1C2.7 27.5 0 24.8 0 21.4s2.7-6.1 6.1-6.1h15.3Z"
      />
      <path
        fill="#2EB67D"
        d="M42.8 21.4c0-3.4 2.7-6.1 6.1-6.1s6.1 2.7 6.1 6.1-2.7 6.1-6.1 6.1h-6.1v-6.1Zm-3.1 0c0 3.4-2.7 6.1-6.1 6.1s-6.1-2.7-6.1-6.1V6.1c0-3.4 2.7-6.1 6.1-6.1s6.1 2.7 6.1 6.1v15.3Z"
      />
      <path
        fill="#ECB22E"
        d="M33.6 42.8c3.4 0 6.1 2.7 6.1 6.1s-2.7 6.1-6.1 6.1-6.1-2.7-6.1-6.1v-6.1h6.1Zm0-3.1c-3.4 0-6.1-2.7-6.1-6.1s2.7-6.1 6.1-6.1h15.3c3.4 0 6.1 2.7 6.1 6.1s-2.7 6.1-6.1 6.1H33.6Z"
      />
    </svg>
  );
}

function Rule() {
  return (
    <span
      aria-hidden="true"
      className="block h-px bg-slate-300/90 dark:bg-slate-700"
    />
  );
}

export default function ContactPage() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-[#f4f6f9] text-slate-950 dark:bg-[#0b1018] dark:text-slate-50">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(201,10,55,0.08),transparent_25%),radial-gradient(circle_at_top_right,rgba(14,121,178,0.06),transparent_29%),linear-gradient(180deg,#f3f6fa_0%,#f7f9fc_42%,#f4f6f9_100%)] dark:bg-[radial-gradient(circle_at_top_left,rgba(201,10,55,0.12),transparent_24%),radial-gradient(circle_at_top_right,rgba(14,121,178,0.09),transparent_28%),linear-gradient(180deg,#0b1018_0%,#0d1320_42%,#101623_100%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,rgba(100,116,139,0.12)_1px,transparent_1px),linear-gradient(to_bottom,rgba(100,116,139,0.12)_1px,transparent_1px)] [mask-image:linear-gradient(to_bottom,white,transparent_82%)] bg-size-[56px_56px] opacity-45 dark:opacity-25" />

      <LandingHeader header={landingPageContent.header} showContact={false} />

      <div className="relative z-10 container pt-32 pb-16 md:pt-40 md:pb-20">
        <div className="mx-auto max-w-6xl">
          <h1 className="max-w-3xl text-[clamp(2.25rem,4.5vw,4.25rem)] leading-[0.98] font-semibold tracking-[-0.055em]">
            {contact.page.title}
          </h1>

          <div className="mt-12">
            <section className="contact-channel grid gap-6 py-8 lg:grid-cols-[4rem_13rem_minmax(0,1fr)] lg:py-10">
              <p className="contact-channel-number font-mono text-xs font-semibold text-[#c90a37] dark:text-rose-400">
                01
              </p>
              <div className="contact-channel-heading flex items-center gap-3 lg:items-start">
                <SlackLogo className="h-6 w-6 shrink-0" />
                <h2 className="text-lg font-semibold tracking-[-0.025em]">
                  {contact.slack.label}
                </h2>
              </div>
              <div className="contact-channel-content">
                {contact.slack.joinUrl ? (
                  <Link
                    href={contact.slack.joinUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={primaryAction}
                  >
                    Join Slack
                    <ArrowUpRight
                      className="h-4 w-4 transition-transform duration-[220ms] ease-out group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                      aria-hidden="true"
                    />
                  </Link>
                ) : (
                  <p className="inline-flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                    <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
                    {contact.slack.status}
                  </p>
                )}
              </div>
            </section>

            <Rule />

            <section className="contact-channel grid gap-6 py-8 lg:grid-cols-[4rem_13rem_minmax(0,1fr)] lg:py-10">
              <p className="contact-channel-number font-mono text-xs font-semibold text-[#c90a37] dark:text-rose-400">
                02
              </p>
              <div className="contact-channel-heading flex items-center gap-3 lg:items-start">
                <GitHubLogoIcon
                  className="h-6 w-6 shrink-0"
                  aria-hidden="true"
                />
                <h2 className="text-lg font-semibold tracking-[-0.025em]">
                  GitHub
                </h2>
              </div>
              <div className="contact-channel-content">
                {contact.github.map((repository, index) => (
                  <article
                    key={`${repository.repositoryUrl}-${index}`}
                    className={
                      index === 0
                        ? undefined
                        : 'mt-7 border-t border-slate-300/80 pt-7 dark:border-slate-700'
                    }
                  >
                    <h3 className="text-xl font-semibold tracking-[-0.03em]">
                      {repository.label}
                    </h3>
                    <div className="mt-5 flex flex-wrap gap-2">
                      <Link
                        href={repository.issuesUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={primaryAction}
                      >
                        New issue
                        <ArrowUpRight
                          className="h-4 w-4 transition-transform duration-[220ms] ease-out group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                          aria-hidden="true"
                        />
                      </Link>
                      <Link
                        href={repository.repositoryUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={secondaryAction}
                      >
                        Repository
                        <ArrowUpRight
                          className="h-4 w-4 transition-transform duration-[220ms] ease-out group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                          aria-hidden="true"
                        />
                      </Link>
                      <Link
                        href={repository.pullRequestsUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={secondaryAction}
                      >
                        Pull requests
                        <ArrowUpRight
                          className="h-4 w-4 transition-transform duration-[220ms] ease-out group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                          aria-hidden="true"
                        />
                      </Link>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <Rule />

            <section className="contact-channel grid gap-6 py-8 lg:grid-cols-[4rem_13rem_minmax(0,1fr)] lg:py-10">
              <p className="contact-channel-number font-mono text-xs font-semibold text-[#c90a37] dark:text-rose-400">
                03
              </p>
              <div className="contact-channel-heading flex items-center gap-3 lg:items-start">
                <Mail
                  className="h-6 w-6 shrink-0 text-[#c90a37] dark:text-rose-400"
                  aria-hidden="true"
                />
                <h2 className="text-lg font-semibold tracking-[-0.025em]">
                  Email
                </h2>
              </div>
              <div className="contact-channel-content">
                {contact.emails.map((person, index) => (
                  <article
                    key={`${person.email}-${index}`}
                    className={
                      index === 0
                        ? undefined
                        : 'mt-9 border-t border-slate-300/80 pt-9 dark:border-slate-700'
                    }
                  >
                    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                      <h3 className="text-2xl font-semibold tracking-[-0.035em]">
                        {person.name}
                      </h3>
                      <p className="text-sm leading-6 text-slate-500 dark:text-slate-400">
                        {person.role}
                      </p>
                    </div>
                    <p className="mt-5 text-sm leading-7 text-slate-600 dark:text-slate-300">
                      {person.bio}
                    </p>
                    <Link
                      href={`mailto:${person.email}`}
                      aria-label={`Email ${person.name}`}
                      className={`${primaryAction} mt-6`}
                    >
                      <Mail className="h-4 w-4" aria-hidden="true" />
                      {person.email}
                    </Link>
                  </article>
                ))}
              </div>
            </section>
          </div>
        </div>
      </div>
      <LandingFooter />
    </main>
  );
}
