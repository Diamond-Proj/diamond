'use client';

import { Server, Container, Terminal } from 'lucide-react';
import { BuilderFormData, ReviewSection } from '@/app/(workspace)/images/types';

interface BuilderReviewProps {
  formData: BuilderFormData;
}

export function BuilderReview({ formData }: BuilderReviewProps) {
  const sections: ReviewSection[] = [
    {
      title: 'Computing Resources',
      icon: <Server className="h-5 w-5 text-rose-600 dark:text-rose-300" />,
      items: [
        { label: 'Endpoint', value: formData.endpoint },
        { label: 'Partition', value: formData.partition },
        { label: 'Account', value: formData.account },
        { label: 'Reservation', value: formData.reservation || 'None' }
      ]
    },
    {
      title: 'Container Configuration',
      icon: <Container className="h-5 w-5 text-rose-600 dark:text-rose-300" />,
      items: [
        { label: 'Container Name', value: formData.containerName },
        { label: 'Build Location', value: formData.location || 'Default' },
        { label: 'Base Image', value: formData.baseImage }
      ]
    },
    {
      title: 'Build Configuration',
      icon: <Terminal className="h-5 w-5 text-rose-600 dark:text-rose-300" />,
      items: [
        {
          label: 'Dependencies',
          value: formData.dependencies ? 'Configured' : 'None',
          expandable: formData.dependencies,
          content: formData.dependencies
        },
        {
          label: 'Environment Variables',
          value: formData.environment ? 'Configured' : 'None',
          expandable: formData.environment,
          content: formData.environment
        },
        {
          label: 'Build Commands',
          value: formData.commands ? 'Configured' : 'None',
          expandable: formData.commands,
          content: formData.commands
        }
      ]
    }
  ];

  return (
    <div className="space-y-8">
      {/* Build Process Information */}
      <div className="rounded-lg border border-slate-200/80 bg-slate-50/70 p-4 dark:border-slate-700/80 dark:bg-slate-800/55">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-700 dark:bg-slate-200">
            <span className="text-xs text-white dark:text-slate-900">i</span>
          </div>
          <div className="text-sm">
            <p className="mb-1 font-medium text-slate-900 dark:text-slate-100">
              Build Process Information
            </p>
            <p className="text-slate-600 dark:text-slate-400">
              {`The build process may take several minutes to complete depending on your configuration. You'll be able to monitor the build logs in real-time once the process starts.`}
            </p>
          </div>
        </div>
      </div>

      {/* Review Sections */}
      <div className="space-y-6">
        {sections.map((section) => (
          <div
            key={section.title}
            className="rounded-xl border border-slate-200/80 bg-[hsl(var(--dashboard-surface))] p-6 dark:border-slate-700/80"
          >
            <div className="mb-4 flex items-center gap-2">
              {section.icon}
              <h4 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{section.title}</h4>
            </div>

            <div className="space-y-3">
              {section.items.map((item) => (
                <div key={item.label} className="space-y-2">
                  <div className="flex items-start justify-between">
                    <span className="text-sm font-medium text-slate-500 dark:text-slate-400">
                      {item.label}:
                    </span>
                    <span className="ml-4 flex-1 text-right text-sm text-slate-800 dark:text-slate-200">
                      {item.value}
                    </span>
                  </div>

                  {item.expandable && (
                    <div className="mt-2 rounded-md border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/50">
                      <pre className="whitespace-pre-wrap font-mono text-xs text-slate-600 dark:text-slate-300">
                        {item.content}
                      </pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
