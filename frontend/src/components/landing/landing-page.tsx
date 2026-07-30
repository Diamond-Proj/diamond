import Image from 'next/image';
import Link from 'next/link';
import {
  ArrowRight,
  Cpu,
  Database,
  ExternalLink,
  Layers3,
  Rocket
} from 'lucide-react';

import { LandingFooter } from '@/components/landing/landing-footer';
import { LandingHeader } from '@/components/landing/landing-header';
import { LandingReveal } from '@/components/landing/landing-reveal';
import { landingPageContent } from '@/content/landing-page-content';

const highlightIcons = {
  cpu: Cpu,
  layers: Layers3,
  database: Database,
  rocket: Rocket
} as const;

const highlightCardStyles = [
  'bg-linear-to-b from-white/95 to-slate-50/90 dark:from-slate-950 dark:to-slate-900',
  'bg-linear-to-b from-white/95 to-rose-50/70 dark:from-slate-950 dark:to-slate-950',
  'bg-linear-to-b from-white/95 to-sky-50/80 dark:from-slate-950 dark:to-slate-900',
  'bg-linear-to-b from-white/95 to-stone-50/80 dark:from-slate-950 dark:to-slate-950'
] as const;

type HpcSystem = {
  name: string;
  org: string;
  image?: {
    src: string;
    alt: string;
  };
};

function CtaLink({
  href,
  label,
  variant = 'primary',
  external = false
}: {
  href: string;
  label: string;
  variant?: 'primary' | 'secondary';
  external?: boolean;
}) {
  return (
    <Link
      href={href}
      target={external ? '_blank' : undefined}
      rel={external ? 'noopener noreferrer' : undefined}
      className={
        variant === 'primary'
          ? 'inline-flex items-center justify-center gap-2 rounded-full bg-[#c90a37] px-5 py-3 text-sm font-semibold text-white shadow-[0_14px_30px_rgba(201,10,55,0.16)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-[#b50931] hover:shadow-[0_18px_34px_rgba(201,10,55,0.2)] dark:bg-[#c90a37] dark:text-white dark:shadow-[0_14px_30px_rgba(0,0,0,0.24)]'
          : 'inline-flex items-center justify-center gap-2 rounded-full border border-white/75 bg-white/78 px-5 py-3 text-sm font-semibold text-slate-700 shadow-[0_10px_26px_rgba(15,23,42,0.08)] backdrop-blur-xl transition-all duration-200 hover:-translate-y-0.5 hover:border-white hover:bg-white hover:text-slate-950 dark:border-slate-700/80 dark:bg-slate-950/72 dark:text-slate-200 dark:shadow-[0_18px_40px_rgba(2,6,23,0.25)] dark:hover:border-slate-500 dark:hover:bg-slate-900 dark:hover:text-slate-50'
      }
    >
      {label}
      {external ? (
        <ExternalLink className="h-4 w-4" />
      ) : (
        <ArrowRight className="h-4 w-4" />
      )}
    </Link>
  );
}

export function LandingPage() {
  const { header, hero, hpcSystems, highlights, closing } = landingPageContent;
  const marqueeSystems: HpcSystem[] = [
    ...hpcSystems.items,
    ...hpcSystems.items
  ];

  return (
    <main className="relative overflow-hidden bg-[#f4f6f9] dark:bg-[#0b1018]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(201,10,55,0.08),transparent_24%),radial-gradient(circle_at_top_right,rgba(14,121,178,0.06),transparent_28%),radial-gradient(circle_at_50%_18%,rgba(255,255,255,0.94),transparent_38%),linear-gradient(180deg,#f3f6fa_0%,#f7f9fc_34%,#f4f6f9_100%)] dark:bg-[radial-gradient(circle_at_top_left,rgba(201,10,55,0.12),transparent_22%),radial-gradient(circle_at_top_right,rgba(14,121,178,0.08),transparent_26%),radial-gradient(circle_at_50%_18%,rgba(15,23,42,0.72),transparent_36%),linear-gradient(180deg,#0b1018_0%,#0d1320_34%,#101623_100%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,rgba(100,116,139,0.18)_1px,transparent_1px),linear-gradient(to_bottom,rgba(100,116,139,0.18)_1px,transparent_1px)] [mask-image:linear-gradient(to_bottom,white,transparent_90%)] bg-size-[56px_56px] opacity-60 dark:opacity-35" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[36rem] bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.92),transparent_72%)] dark:bg-[radial-gradient(circle_at_top,rgba(15,23,42,0.82),transparent_72%)]" />

      <LandingHeader header={header} />

      <div className="relative z-10 container pt-28 pb-8 md:pt-32 md:pb-10">
        <section className="px-1 py-6 lg:py-10">
          <div className="relative mx-auto max-w-4xl px-2 text-center">
            <div className="pointer-events-none absolute -top-12 left-[10%] h-36 w-36 rounded-full bg-[rgba(201,10,55,0.07)] blur-3xl dark:bg-[rgba(201,10,55,0.1)]" />
            <div className="relative">
              <LandingReveal>
                <h1 className="text-[2.15rem] leading-[1.14] font-medium tracking-[-0.045em] text-slate-950 md:text-[3.7rem] dark:text-slate-50">
                  {hero.headline}
                </h1>
              </LandingReveal>

              <LandingReveal delay={0.18}>
                <div className="mt-8 flex flex-wrap justify-center gap-3">
                  <CtaLink
                    href={hero.primaryCta.href}
                    label={hero.primaryCta.label}
                  />
                </div>
              </LandingReveal>
            </div>
          </div>

          <div className="relative mx-auto mt-12 max-w-[86rem]">
            <div className="pointer-events-none absolute inset-x-10 bottom-0 h-20 bg-[radial-gradient(circle,rgba(15,23,42,0.14),transparent_72%)] blur-3xl dark:bg-[radial-gradient(circle,rgba(2,6,23,0.42),transparent_72%)]" />
            <div className="pointer-events-none absolute -top-10 right-[6%] h-48 w-48 rounded-full bg-sky-500/10 blur-3xl dark:bg-sky-500/10" />

            <LandingReveal delay={0.26}>
              <div className="mx-auto overflow-hidden rounded-lg border border-slate-200 bg-white shadow-[0_34px_90px_rgba(15,23,42,0.12)] dark:border-slate-800 dark:bg-slate-950 dark:shadow-[0_34px_100px_rgba(0,0,0,0.42)]">
                <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
                  <div className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full bg-[#c90a37]" />
                    <span className="h-2.5 w-2.5 rounded-full bg-[#f39237]" />
                    <span className="h-2.5 w-2.5 rounded-full bg-[#0e79b2]" />
                  </div>
                  <p className="hidden text-xs font-semibold tracking-[0.14em] text-slate-500 uppercase sm:block dark:text-slate-400">
                    Diamond Workspace
                  </p>
                </div>

                <div className="grid gap-0 lg:grid-cols-[minmax(0,1fr)_22rem]">
                  <LandingReveal delay={0.06}>
                    <div className="h-full overflow-hidden bg-white dark:bg-slate-950">
                      <Image
                        src={hero.screenshot.src}
                        alt={hero.screenshot.alt}
                        width={2516}
                        height={1332}
                        priority
                        sizes="(min-width: 1024px) 980px, 100vw"
                        className="h-full min-h-[16rem] w-full object-cover object-left-top"
                      />
                    </div>
                  </LandingReveal>

                  <aside className="border-t border-slate-200 bg-slate-50 p-5 lg:border-t-0 lg:border-l dark:border-slate-800 dark:bg-slate-900/70">
                    <LandingReveal delay={0.1}>
                      <p className="text-xs font-semibold tracking-[0.16em] text-slate-500 uppercase dark:text-slate-400">
                        {hero.screenshot.sideCardLabel}
                      </p>
                    </LandingReveal>

                    <div className="mt-4 grid gap-3">
                      {hero.screenshot.sideCardItems.map((item, index) => (
                        <LandingReveal key={item} delay={0.14 + index * 0.06}>
                          <article className="landing-hover-card landing-hover-card--subtle rounded-lg border border-slate-200 bg-white p-4 shadow-sm hover:border-slate-300 hover:shadow-md dark:border-slate-800 dark:bg-slate-950 dark:hover:border-slate-700 dark:hover:shadow-[0_14px_28px_rgba(2,6,23,0.28)]">
                            <p className="text-xs font-semibold tracking-[0.16em] text-[#c90a37] uppercase">
                              {['Access', 'Package', 'Launch'][index] ??
                                `Step ${index + 1}`}
                            </p>
                            <p className="mt-2 text-sm leading-6 text-slate-700 dark:text-slate-200">
                              {item}
                            </p>
                          </article>
                        </LandingReveal>
                      ))}
                    </div>
                  </aside>
                </div>
              </div>
            </LandingReveal>
          </div>
        </section>

        <section className="py-8">
          <LandingReveal delay={0.12}>
            <div className="overflow-hidden rounded-xl border border-white/80 bg-white/72 py-6 shadow-[0_20px_60px_rgba(15,23,42,0.08)] backdrop-blur-xl dark:border-slate-800/80 dark:bg-slate-950/68 dark:shadow-[0_24px_80px_rgba(2,6,23,0.3)]">
              <div className="px-5 md:px-6">
                <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                  <div>
                    <h2 className="text-2xl font-semibold tracking-[-0.04em] text-slate-950 md:text-3xl dark:text-slate-50">
                      {hpcSystems.title}
                    </h2>
                  </div>
                </div>
              </div>

              <div className="mt-7 overflow-hidden bg-white/0 px-5 py-4 md:px-6 dark:bg-slate-950/0">
                <div className="landing-marquee-track flex w-max gap-3">
                  {marqueeSystems.map((system, index) => {
                    const isDuplicate = index >= hpcSystems.items.length;
                    const image = system.image;

                    return (
                      <article
                        key={`${system.name}-${system.org}-${index}`}
                        aria-hidden={isDuplicate}
                        className={
                          image
                            ? 'landing-hover-card relative h-24 min-w-60 overflow-hidden rounded-lg border border-white/80 bg-white/86 shadow-[0_-10px_18px_-12px_rgba(15,23,42,0.14),0_10px_18px_-12px_rgba(15,23,42,0.18)] backdrop-blur-xl hover:border-slate-300/90 hover:shadow-[0_-12px_22px_-12px_rgba(15,23,42,0.18),0_14px_24px_-12px_rgba(15,23,42,0.24)] dark:border-slate-800/80 dark:bg-slate-900/72 dark:shadow-[0_-10px_20px_-12px_rgba(2,6,23,0.28),0_10px_20px_-12px_rgba(2,6,23,0.38)] dark:hover:border-slate-700 dark:hover:shadow-[0_-12px_24px_-12px_rgba(2,6,23,0.34),0_14px_26px_-12px_rgba(2,6,23,0.48)]'
                            : 'landing-hover-card flex min-w-52 items-center justify-between gap-6 rounded-lg border border-[#0e79b2]/30 bg-slate-950 px-5 py-4 shadow-[0_-10px_18px_-12px_rgba(15,23,42,0.14),0_10px_18px_-12px_rgba(15,23,42,0.18)] backdrop-blur-xl hover:border-[#0e79b2]/60 hover:shadow-[0_-12px_22px_-12px_rgba(15,23,42,0.18),0_14px_24px_-12px_rgba(15,23,42,0.24)] dark:border-[#0e79b2]/45 dark:bg-slate-100 dark:shadow-[0_-10px_20px_-12px_rgba(2,6,23,0.28),0_10px_20px_-12px_rgba(2,6,23,0.38)] dark:hover:border-[#0e79b2]/70 dark:hover:shadow-[0_-12px_24px_-12px_rgba(2,6,23,0.34),0_14px_26px_-12px_rgba(2,6,23,0.48)]'
                        }
                      >
                        {image ? (
                          <>
                            <Image
                              src={image.src}
                              alt={isDuplicate ? '' : image.alt}
                              fill
                              sizes="240px"
                              className="object-cover"
                            />
                            <div className="absolute inset-x-0 bottom-0 bg-linear-to-t from-slate-950/88 via-slate-950/56 to-transparent px-4 pt-8 pb-3">
                              <p className="text-sm leading-none font-semibold text-white drop-shadow-sm">
                                {system.name}
                              </p>
                              <p className="mt-1 text-[0.68rem] leading-none font-semibold tracking-[0.14em] text-white/72 uppercase">
                                {system.org}
                              </p>
                            </div>
                          </>
                        ) : (
                          <>
                            <div>
                              <p className="text-base font-semibold text-white dark:text-slate-950">
                                {system.name}
                              </p>
                              <p className="mt-1 text-xs font-semibold tracking-[0.14em] text-sky-200 uppercase dark:text-slate-500">
                                {system.org}
                              </p>
                            </div>
                            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/10 text-sky-200 dark:bg-slate-950/10 dark:text-[#0e79b2]">
                              <Cpu className="h-5 w-5" />
                            </span>
                          </>
                        )}
                      </article>
                    );
                  })}
                </div>
              </div>
            </div>
          </LandingReveal>
        </section>

        <section className="grid gap-8 py-12 lg:grid-cols-[0.86fr_minmax(0,1.14fr)] lg:pt-12 lg:pb-8">
          <div className="max-w-xl space-y-6">
            <LandingReveal delay={0.1}>
              <div>
                <h2 className="text-3xl font-semibold tracking-[-0.04em] text-slate-950 md:text-4xl dark:text-slate-50">
                  {highlights.title}
                </h2>
                {highlights.description ? (
                  <p className="mt-4 max-w-lg text-base leading-8 text-slate-600 dark:text-slate-300">
                    {highlights.description}
                  </p>
                ) : null}
              </div>
            </LandingReveal>

            <LandingReveal delay={0.16}>
              <ul className="space-y-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                {highlights.supportPanel.points.map((point, index) => (
                  <LandingReveal key={point} delay={0.2 + index * 0.06}>
                    <li className="landing-hover-card rounded-lg border border-white/80 bg-white/72 px-4 py-5 shadow-[0_12px_30px_rgba(15,23,42,0.05)] hover:border-slate-200 hover:bg-white/90 hover:shadow-[0_18px_38px_rgba(15,23,42,0.1)] dark:border-slate-800/80 dark:bg-slate-900/72 dark:shadow-none dark:hover:border-slate-700 dark:hover:bg-slate-900 dark:hover:shadow-[0_18px_38px_rgba(2,6,23,0.3)]">
                      {point}
                    </li>
                  </LandingReveal>
                ))}
              </ul>
            </LandingReveal>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {highlights.items.map((item, index) => {
              const Icon =
                highlightIcons[item.icon as keyof typeof highlightIcons];

              return (
                <LandingReveal key={item.title} delay={0.1 + index * 0.06}>
                  <article
                    className={`landing-hover-card landing-hover-card--strong group h-full rounded-xl border border-white/80 p-6 shadow-[0_24px_70px_rgba(15,23,42,0.07)] backdrop-blur-xl hover:border-slate-200 hover:shadow-[0_30px_76px_rgba(15,23,42,0.13)] dark:border-slate-800/80 dark:shadow-[0_24px_80px_rgba(2,6,23,0.28)] dark:hover:border-slate-700 dark:hover:shadow-[0_30px_84px_rgba(2,6,23,0.4)] ${highlightCardStyles[index % highlightCardStyles.length]}`}
                  >
                    <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-[#c90a37] text-white shadow-[0_10px_24px_rgba(201,10,55,0.16)] transition-transform duration-[450ms] ease-[cubic-bezier(0.22,1,0.36,1)] motion-safe:group-hover:scale-105 motion-safe:group-hover:-rotate-3 dark:shadow-none">
                      <Icon className="h-5 w-5" />
                    </div>
                    <h3 className="mt-5 text-xl font-semibold tracking-[-0.03em] text-slate-950 dark:text-slate-50">
                      {item.title}
                    </h3>
                    <p className="mt-3 text-sm leading-7 text-slate-600 dark:text-slate-300">
                      {item.description}
                    </p>
                  </article>
                </LandingReveal>
              );
            })}
          </div>
        </section>

        <section className="relative overflow-hidden rounded-xl border border-white/80 bg-[linear-gradient(135deg,rgba(255,255,255,0.9),rgba(244,247,251,0.92),rgba(247,244,246,0.9))] px-6 py-8 shadow-[0_30px_100px_rgba(15,23,42,0.1)] md:px-8 md:py-10 dark:border-slate-800/80 dark:bg-[linear-gradient(135deg,rgba(12,18,30,0.94),rgba(37,15,30,0.9),rgba(17,29,43,0.92))] dark:shadow-[0_30px_110px_rgba(2,6,23,0.42)]">
          <div className="pointer-events-none absolute -top-20 -right-20 h-48 w-48 rounded-full bg-[rgba(201,10,55,0.08)] blur-3xl dark:bg-[rgba(201,10,55,0.12)]" />
          <div className="pointer-events-none absolute -bottom-20 -left-16 h-44 w-44 rounded-full bg-sky-500/10 blur-3xl dark:bg-sky-400/12" />

          <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <LandingReveal delay={0.1}>
              <div className="max-w-2xl">
                <h2 className="text-3xl font-semibold tracking-[-0.04em] text-slate-950 md:text-4xl dark:text-slate-50">
                  {closing.title}
                </h2>
                <p className="mt-4 text-base leading-8 text-slate-700 dark:text-slate-200">
                  {closing.description}
                </p>
              </div>
            </LandingReveal>

            <LandingReveal delay={0.18}>
              <div className="flex flex-wrap gap-3">
                <CtaLink
                  href={closing.primaryCta.href}
                  label={closing.primaryCta.label}
                />
                <CtaLink
                  href={closing.secondaryCta.href}
                  label={closing.secondaryCta.label}
                  variant="secondary"
                  external
                />
              </div>
            </LandingReveal>
          </div>
        </section>
      </div>

      <LandingFooter />
    </main>
  );
}
