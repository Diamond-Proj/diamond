'use client';

import { useState } from 'react';
import { TaskTemplate } from '../tasks.types';
import { X, ChevronDown, ChevronRight, LayoutTemplate } from 'lucide-react';

interface TemplateSelectorProps {
  templates: TaskTemplate[];
  activeTemplateId: string | null;
  onSelect: (template: TaskTemplate) => void;
  onClear: () => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  'Fine-tuning':
    'bg-rose-100 text-rose-700 dark:bg-rose-950/30 dark:text-rose-200',
  Inference:
    'bg-sky-100 text-sky-700 dark:bg-sky-950/30 dark:text-sky-200',
  Evaluation:
    'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-200',
  Training:
    'bg-amber-100 text-amber-700 dark:bg-amber-950/30 dark:text-amber-200',
};

function getCategoryColor(category: string): string {
  return (
    CATEGORY_COLORS[category] ??
    'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
  );
}

export function TemplateSelector({
  templates,
  activeTemplateId,
  onSelect,
  onClear,
}: TemplateSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (templates.length === 0) return null;

  const activeTemplate = templates.find((t) => t.id === activeTemplateId);

  return (
    <div className="border-b border-slate-200/70 bg-slate-50/65 dark:border-slate-700/70 dark:bg-slate-900/45">
      <div className="flex items-center justify-between px-6 py-3">
        <button
          type="button"
          onClick={() => setIsOpen((v) => !v)}
          className="flex cursor-pointer items-center gap-2 text-sm font-semibold text-slate-700 transition-colors hover:text-slate-900 dark:text-slate-200 dark:hover:text-slate-100"
        >
          <LayoutTemplate className="h-4 w-4 text-slate-400 dark:text-slate-500" />
          Templates
          {isOpen ? (
            <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-slate-400" />
          )}
        </button>

        {activeTemplate && (
          <div className="flex items-center gap-2">
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${getCategoryColor(activeTemplate.category)}`}
            >
              {activeTemplate.name}
            </span>
            <button
              type="button"
              onClick={onClear}
              title="Clear template"
              className="cursor-pointer text-slate-400 transition-colors hover:text-slate-700 dark:hover:text-slate-200"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
      </div>

      {isOpen && (
        <div className="flex gap-3 overflow-x-auto px-6 pb-4">
          {templates.map((template) => {
            const isActive = template.id === activeTemplateId;
            return (
              <button
                key={template.id}
                type="button"
                title={template.description}
                onClick={() => {
                  onSelect(template);
                  setIsOpen(false);
                }}
                className={`flex min-w-55 max-w-65 shrink-0 cursor-pointer flex-col gap-2 rounded-xl border p-4 text-left transition-all duration-150 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-rose-500/25 ${
                  isActive
                    ? 'border-rose-300/80 bg-rose-50/70 shadow-sm dark:border-rose-400/40 dark:bg-rose-950/20'
                    : 'border-slate-200/80 bg-[hsl(var(--dashboard-surface))] hover:border-slate-300 dark:border-slate-700/80 dark:hover:border-slate-600'
                }`}
              >
                <span
                  className={`self-start rounded-full px-2 py-0.5 text-xs font-medium ${getCategoryColor(template.category)}`}
                >
                  {template.category}
                </span>
                <span
                  className={`text-sm font-semibold leading-snug ${
                    isActive
                      ? 'text-rose-700 dark:text-rose-200'
                      : 'text-slate-900 dark:text-slate-100'
                  }`}
                >
                  {template.name}
                </span>
                <span className="line-clamp-2 text-xs text-slate-500 dark:text-slate-400">
                  {template.description}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
