'use client';

import { useState } from 'react';
import { Trash2, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ContainerData } from '@/app/(workspace)/images/types';

export default function ContainerItem({
  containerName,
  data,
  deletingContainers,
  deleteContainer,
  getStatusIcon,
  getStatusBadgeColor
}: {
  containerName: string;
  data: ContainerData;
  deletingContainers?: Set<string>;
  deleteContainer?: (name: string, taskId: string) => void;
  getStatusIcon: (status: string) => React.ReactNode;
  getStatusBadgeColor: (status: string) => string;
}) {
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const deleteSet = deletingContainers ?? new Set<string>();
  const canDelete = !!deleteContainer && data.is_owner;
  const isDeleting = !!(canDelete && deleteSet.has(containerName));

  const handleDeleteClick = () => setShowConfirmDialog(true);
  const handleConfirmDelete = () => {
    if (deleteContainer) {
      deleteContainer(containerName, data.container_task_id);
    }
    setShowConfirmDialog(false);
  };
  const handleCancelDelete = () => setShowConfirmDialog(false);

  return (
    <>
      <div className="group dashboard-card p-6 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="mb-3 flex items-center gap-3">
              <h3 className="text-xl font-semibold text-slate-900 transition-colors duration-200 group-hover:text-slate-700 dark:text-slate-100 dark:group-hover:text-slate-200">
                {containerName}
              </h3>
              <div className="flex items-center gap-2">
                <span
                  className={`flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium ${getStatusBadgeColor(
                    data.status
                  )}`}
                >
                  {getStatusIcon(data.status)}
                  {data.status || 'Unknown'}
                </span>
                {data.is_public && (
                  <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800 dark:bg-amber-950/50 dark:text-amber-300">
                    Public
                  </span>
                )}
              </div>
            </div>

            <div className="mb-4 grid grid-cols-1 gap-4 text-sm md:grid-cols-3">
              {data.base_image && (
                <div className="rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/50">
                  <span className="block text-xs font-medium tracking-wide text-slate-500 uppercase dark:text-slate-400">
                    Base Image
                  </span>
                  <span className="mt-1 block font-mono text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {data.base_image}
                  </span>
                </div>
              )}
              {data.host_name && (
                <div className="rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/50">
                  <span className="block text-xs font-medium tracking-wide text-slate-500 uppercase dark:text-slate-400">
                    Host Name
                  </span>
                  <span className="mt-1 block font-mono text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {data.host_name}
                  </span>
                </div>
              )}
              {data.location && (
                <div className="rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/50">
                  <span className="block text-xs font-medium tracking-wide text-slate-500 uppercase dark:text-slate-400">
                    Location
                  </span>
                  <span className="mt-1 block font-mono text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {data.location}
                  </span>
                </div>
              )}
            </div>
          </div>

          {canDelete && (
            <div className="ml-6">
              <Button
                variant="destructive"
                size="sm"
                onClick={handleDeleteClick}
                disabled={isDeleting}
                className="flex cursor-pointer items-center gap-2"
              >
                <Trash2 className="h-4 w-4" />
                {isDeleting ? 'Deleting...' : 'Delete'}
              </Button>
            </div>
          )}
        </div>
      </div>

      {showConfirmDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 dark:bg-black/70">
          <div className="w-full max-w-md rounded-2xl border border-slate-200/80 bg-[hsl(var(--dashboard-surface))] shadow-xl dark:border-slate-700/80">
            <div className="p-6">
              <div className="mb-4 flex items-center gap-3">
                <div className="rounded-full bg-red-100 p-2 dark:bg-red-950/30">
                  <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                  Delete Container
                </h3>
              </div>

              <div className="mb-6">
                <p className="mb-2 text-slate-600 dark:text-slate-400">
                  Are you sure you want to delete this container?
                </p>
                <div className="space-y-2 rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/60">
                  <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                    {containerName}
                  </p>
                  {data.base_image && (
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      <span className="font-bold">Base Image:</span>{' '}
                      <span className="font-mono">{data.base_image}</span>
                    </p>
                  )}
                  {data.host_name && (
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      <span className="font-bold">Host Name:</span>{' '}
                      <span className="font-mono">{data.host_name}</span>
                    </p>
                  )}
                  {data.location && (
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      <span className="font-bold">Location:</span> {data.location}
                    </p>
                  )}
                  {data.is_public && (
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      <span className="font-bold">Visibility:</span> Public
                    </p>
                  )}
                </div>
                <p className="mt-3 text-sm text-red-600 dark:text-red-400">
                  This action cannot be undone.
                </p>
              </div>

              {canDelete && (
                <div className="flex justify-end gap-3">
                  <Button
                    variant="outline"
                    onClick={handleCancelDelete}
                    className="cursor-pointer"
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={handleConfirmDelete}
                    className="cursor-pointer"
                  >
                    Delete Container
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
