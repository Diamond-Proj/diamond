'use client';

import { Loader2, Plus, Server } from 'lucide-react';

import { Button } from '@/components/ui/button';

interface Endpoint {
  endpoint_uuid: string;
  endpoint_name: string;
  is_managed: boolean;
  diamond_dir?: string;
}

interface AvailableEndpointCardProps {
  endpoint: Endpoint;
  isAdding: boolean;
  onAdd: () => void;
}

export function AvailableEndpointCard({
  endpoint,
  isAdding,
  onAdd
}: AvailableEndpointCardProps) {
  return (
    <div className="dashboard-card flex items-center justify-between p-4">
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 dark:border-slate-600 dark:bg-slate-800">
          <Server className="h-5 w-5 text-slate-500 dark:text-slate-300" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="truncate font-medium text-slate-900 dark:text-slate-100">
            {endpoint.endpoint_name}
          </h3>
          <p
            className="truncate text-xs text-slate-600 dark:text-slate-300"
            style={{ fontFamily: 'var(--font-mono)' }}
          >
            UUID: {endpoint.endpoint_uuid}
          </p>
        </div>
      </div>
      <Button
        onClick={onAdd}
        disabled={isAdding}
        size="sm"
        className="ml-4 cursor-pointer gap-2"
      >
        {isAdding ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Adding...
          </>
        ) : (
          <>
            <Plus className="h-4 w-4" />
            Add
          </>
        )}
      </Button>
    </div>
  );
}
