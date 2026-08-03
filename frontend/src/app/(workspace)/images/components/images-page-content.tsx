'use client';

import { useState } from 'react';
import { Plus } from 'lucide-react';

import { ContainerGrid } from './container-grid';
import { ImageBuilderModal } from './image-builder-modal';

interface ImagesPageContentProps {
  isAuthenticated: boolean;
}

export function ImagesPageContent({ isAuthenticated }: ImagesPageContentProps) {
  const [isBuilderOpen, setIsBuilderOpen] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleBuilderSuccess = () => {
    setIsBuilderOpen(false);
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <div className="space-y-6">
      <section className="dashboard-card relative overflow-hidden p-5 md:p-6">
        <div className="pointer-events-none absolute -right-10 -top-16 h-40 w-40 rounded-full bg-sky-400/5 blur-2xl" />
        <div className="pointer-events-none absolute -left-8 -bottom-12 h-36 w-36 rounded-full bg-primary/5 blur-2xl" />

        <div className="relative z-10 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              Container Images
            </h1>
          </div>

          <button
            onClick={() => setIsBuilderOpen(true)}
            className="group inline-flex cursor-pointer items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm transition-colors duration-200 hover:bg-primary/90"
          >
            <Plus className="h-4 w-4 transition-transform duration-200 group-hover:scale-110" />
            Build New Image
          </button>
        </div>
      </section>

      <ContainerGrid
        isAuthenticated={isAuthenticated}
        refreshTrigger={refreshTrigger}
      />

      <ImageBuilderModal
        isOpen={isBuilderOpen}
        onClose={() => setIsBuilderOpen(false)}
        onSuccess={handleBuilderSuccess}
      />
    </div>
  );
}
