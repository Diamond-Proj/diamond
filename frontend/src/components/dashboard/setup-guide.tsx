'use client';

import Link from 'next/link';
import { useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  ExternalLink,
  HelpCircle,
  TerminalSquare
} from 'lucide-react';

const endpointSteps = [
  {
    label: 'Install Globus Compute Endpoint package:',
    command: 'python3 -m pipx install globus-compute-endpoint'
  },
  {
    label: 'Create an endpoint on your HPC machine:',
    command: 'globus-compute-endpoint configure <endpoint-name>'
  },
  {
    label: 'Start your endpoint:',
    command: 'globus-compute-endpoint start <endpoint-name>'
  }
];

const gettingStartedFeatures = [
  'Images - Build and manage container images for your HPC workloads',
  'Datasets - Register and manage data collections for compute tasks',
  'Tasks - Submit jobs and monitor execution status in real time',
  'Endpoints - Configure Globus Compute endpoints and runtime settings',
  'Profile - Review account identity and platform access details'
];

export function SetupGuide() {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <section className="dashboard-card overflow-hidden">
      <button
        type="button"
        className="group flex w-full cursor-pointer items-center justify-between p-6 text-left"
        onClick={() => setIsExpanded((state) => !state)}
        aria-expanded={isExpanded}
        aria-controls="setup-guide-panel"
      >
        <div className="flex items-center gap-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/15 text-primary transition-transform duration-200 group-hover:scale-105">
            <HelpCircle className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Setup Guide
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              First-time researcher checklist for Diamond onboarding
            </p>
          </div>
        </div>
        <span className="inline-flex items-center gap-2 rounded-full border border-slate-300/70 px-3 py-1 text-xs font-medium text-slate-600 dark:border-slate-600 dark:text-slate-300">
          {isExpanded ? 'Hide steps' : 'Show steps'}
          {isExpanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </span>
      </button>

      <div
        id="setup-guide-panel"
        className={`grid transition-all duration-300 ${
          isExpanded ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'
        }`}
      >
        <div className="overflow-hidden border-t border-slate-200/70 dark:border-slate-700/60">
          <div className="grid gap-6 p-6 lg:grid-cols-2">
            <article className="rounded-2xl border border-sky-200/80 bg-sky-50/70 p-5 dark:border-sky-800/60 dark:bg-sky-900/15">
              <h4 className="flex items-center gap-2 text-base font-semibold text-sky-900 dark:text-sky-100">
                <TerminalSquare className="h-4 w-4" />
                Globus Compute Endpoint Setup
              </h4>
              <p className="mt-3 text-sm text-sky-800 dark:text-sky-200">
                Important: Before using Diamond services, you need to create a{' '}
                <Link
                  href="https://globus-compute.readthedocs.io/en/2.6.0/endpoints.html"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 underline underline-offset-4"
                >
                  Globus Compute endpoint
                  <ExternalLink className="h-3 w-3" />
                </Link>{' '}
                on your HPC machine.
              </p>
              <div className="mt-4 space-y-3">
                {endpointSteps.map((step) => (
                  <div key={step.command} className="space-y-2">
                    <p className="text-sm text-sky-800 dark:text-sky-200">
                      {step.label}
                    </p>
                    <pre
                      className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-xs text-emerald-300"
                      style={{ fontFamily: 'var(--font-mono)' }}
                    >
                      {step.command}
                    </pre>
                  </div>
                ))}
                <p className="text-sm text-sky-800 dark:text-sky-200">
                  Replace {'<endpoint-name>'} with a unique name for your
                  endpoint. This step is required to connect your HPC resources
                  with Diamond.
                </p>
              </div>
            </article>

            <article className="rounded-2xl border border-slate-200/80 bg-slate-50/85 p-5 dark:border-slate-700/70 dark:bg-slate-900/45">
              <h4 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                Getting Started
              </h4>
              <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">
                Welcome to Diamond! You can now use the navigation menu to
                access various features:
              </p>
              <ul className="mt-4 space-y-3">
                {gettingStartedFeatures.map((feature) => (
                  <li
                    key={feature}
                    className="rounded-xl border border-slate-200/75 bg-white/90 px-4 py-3 dark:border-slate-700 dark:bg-slate-900/75"
                  >
                    <p className="text-sm text-slate-600 dark:text-slate-300">
                      {feature}
                    </p>
                  </li>
                ))}
              </ul>
            </article>
          </div>
        </div>
      </div>
    </section>
  );
}
