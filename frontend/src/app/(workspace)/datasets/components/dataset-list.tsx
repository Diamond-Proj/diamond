'use client';

import { Database, Globe, Lock, Copy, Check } from 'lucide-react';
import { DisplayDataset } from '../datasets.types';
import { useToast } from '@/components/ui/use-toast';
import { useState, useMemo } from 'react';
import { debounce } from '@/lib/debounce';

interface DatasetListProps {
  datasets: DisplayDataset[];
  loading: boolean;
}

export function DatasetList({ datasets, loading }: DatasetListProps) {
  if (loading) {
    return (
      <div className="dashboard-card py-16 text-center">
        <div className="mx-auto h-12 w-12 animate-spin rounded-full border-b-2 border-slate-600 dark:border-slate-300"></div>
        <p className="mt-4 text-slate-600 dark:text-slate-300">
          Loading datasets...
        </p>
      </div>
    );
  }

  if (datasets.length === 0) {
    return (
      <div className="dashboard-card py-16 text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-slate-200/70 dark:bg-slate-800/70">
          <Database className="h-8 w-8 text-slate-500 dark:text-slate-300" />
        </div>
        <p className="text-lg font-medium text-slate-900 dark:text-slate-100">
          No datasets found
        </p>
        <p className="text-slate-600 dark:text-slate-300">
          Try adjusting your search or filter criteria
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {datasets.map((dataset) => (
        <DatasetListItem key={dataset.id} dataset={dataset} />
      ))}
    </div>
  );
}

function DatasetListItem({ dataset }: { dataset: DisplayDataset }) {
  const { toast } = useToast();
  const [copiedItem, setCopiedItem] = useState<
    'globus_path' | 'system_path' | 'uuid' | null
  >(null);

  const resetCopiedItem = useMemo(
    () =>
      debounce(() => {
        setCopiedItem(null);
      }, 1500),
    []
  );

  const copyToClipboard = async (
    text: string,
    type: 'globus_path' | 'system_path' | 'uuid'
  ) => {
    try {
      await navigator.clipboard.writeText(text);

      // Set the copied item for visual feedback
      setCopiedItem(type);

      // Show toast notification
      const typeLabels = {
        globus_path: 'Globus path',
        system_path: 'System path',
        uuid: 'Collection UUID'
      };

      toast({
        description: (
          <div className="flex items-center gap-2">
            <div className="flex h-5 w-5 items-center justify-center rounded-full bg-green-500">
              <Check className="h-3 w-3 text-white" />
            </div>
            <span className="font-medium">{typeLabels[type]} copied!</span>
          </div>
        ),
        duration: 2000,
        className:
          'border-green-200 bg-green-50 text-green-800 dark:border-green-800 dark:bg-green-900/20 dark:text-green-300'
      });

      // Reset the copied state after animation
      resetCopiedItem();
    } catch {
      toast({
        description: (
          <div className="flex items-center gap-2">
            <div className="flex h-5 w-5 items-center justify-center rounded-full bg-red-500">
              <span className="text-xs text-white">✕</span>
            </div>
            <span className="font-medium">Failed to copy to clipboard</span>
          </div>
        ),
        duration: 3000,
        variant: 'destructive'
      });
    }
  };

  return (
    <div className="group dashboard-card p-6 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="mb-3 flex items-center gap-3">
            <h3 className="text-xl font-semibold text-slate-900 transition-colors duration-200 group-hover:text-slate-700 dark:text-slate-100 dark:group-hover:text-slate-200">
              {dataset.dataset_name}
            </h3>
            <div className="flex items-center gap-2">
              {dataset.public ? (
                <div className="flex items-center gap-1 rounded-full bg-sky-100 px-3 py-1 text-xs font-medium text-sky-700 dark:bg-sky-950/30 dark:text-sky-300">
                  <Globe className="h-3 w-3" />
                  Public
                </div>
              ) : (
                <div className="flex items-center gap-1 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                  <Lock className="h-3 w-3" />
                  Private
                </div>
              )}
            </div>
          </div>

          <p className="mb-4 leading-relaxed text-slate-600 dark:text-slate-400">
            {dataset.description}
          </p>

          <div className="mb-4 grid grid-cols-1 gap-4 text-sm md:grid-cols-3">
            <div className="rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/50">
              <span className="block text-xs font-medium tracking-wide text-slate-500 uppercase dark:text-slate-400">
                Size
              </span>
              <span className="mt-1 block font-semibold text-slate-900 dark:text-slate-100">
                {dataset.size}
              </span>
            </div>
            <div className="rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/50">
              <span className="block text-xs font-medium tracking-wide text-slate-500 uppercase dark:text-slate-400">
                Format
              </span>
              <span className="mt-1 block font-semibold text-slate-900 dark:text-slate-100">
                {dataset.format}
              </span>
            </div>
            <div className="rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/50">
              <span className="block text-xs font-medium tracking-wide text-slate-500 uppercase dark:text-slate-400">
                Machine
              </span>
              <span className="mt-1 block font-semibold text-slate-900 dark:text-slate-100">
                {dataset.machine_name}
              </span>
            </div>
          </div>

          <div className="space-y-3 border-t border-slate-200/70 pt-4 dark:border-slate-700/70">
            <div className="flex items-center justify-between rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/50">
              <div className="min-w-0 flex-1">
                <span className="block text-xs font-medium tracking-wide text-slate-500 uppercase dark:text-slate-400">
                  Globus Path
                </span>
                <span className="mt-1 block truncate font-mono text-sm text-slate-700 dark:text-slate-300">
                  {dataset.globus_path}
                </span>
              </div>
              <button
                onClick={() =>
                  copyToClipboard(dataset.globus_path, 'globus_path')
                }
                className={`ml-3 cursor-pointer rounded-md p-2 transition-all duration-200 ${
                  copiedItem === 'globus_path'
                    ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300'
                    : 'text-slate-400 hover:bg-slate-200 hover:text-slate-600 dark:hover:bg-slate-700 dark:hover:text-slate-200'
                }`}
                title={
                  copiedItem === 'globus_path' ? 'Copied!' : 'Copy Globus path'
                }
              >
                {copiedItem === 'globus_path' ? (
                  <Check className="h-4 w-4 animate-pulse" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </button>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/50">
              <div className="min-w-0 flex-1">
                <span className="block text-xs font-medium tracking-wide text-slate-500 uppercase dark:text-slate-400">
                  System Path
                </span>
                <span className="mt-1 block truncate font-mono text-sm text-slate-700 dark:text-slate-300">
                  {dataset.system_path}
                </span>
              </div>
              <button
                onClick={() =>
                  copyToClipboard(dataset.system_path, 'system_path')
                }
                className={`ml-3 cursor-pointer rounded-md p-2 transition-all duration-200 ${
                  copiedItem === 'system_path'
                    ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300'
                    : 'text-slate-400 hover:bg-slate-200 hover:text-slate-600 dark:hover:bg-slate-700 dark:hover:text-slate-200'
                }`}
                title={
                  copiedItem === 'system_path' ? 'Copied!' : 'Copy system path'
                }
              >
                {copiedItem === 'system_path' ? (
                  <Check className="h-4 w-4 animate-pulse" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </button>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/50">
              <div className="min-w-0 flex-1">
                <span className="block text-xs font-medium tracking-wide text-slate-500 uppercase dark:text-slate-400">
                  Collection UUID
                </span>
                <span
                  className="mt-1 block truncate text-sm text-slate-700 dark:text-slate-300"
                  style={{ fontFamily: 'var(--font-mono)' }}
                >
                  {dataset.collection_uuid}
                </span>
              </div>
              <button
                onClick={() => copyToClipboard(dataset.collection_uuid, 'uuid')}
                className={`ml-3 cursor-pointer rounded-md p-2 transition-all duration-200 ${
                  copiedItem === 'uuid'
                    ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300'
                    : 'text-slate-400 hover:bg-slate-200 hover:text-slate-600 dark:hover:bg-slate-700 dark:hover:text-slate-200'
                }`}
                title={copiedItem === 'uuid' ? 'Copied!' : 'Copy UUID'}
              >
                {copiedItem === 'uuid' ? (
                  <Check className="h-4 w-4 animate-pulse" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
