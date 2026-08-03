'use client';

import { Activity, Loader2, Server, X } from 'lucide-react';

import { Button } from '@/components/ui/button';

import { EndpointSettingsPanel } from './endpoint-settings-panel';

interface Endpoint {
  endpoint_uuid: string;
  endpoint_name: string;
  is_managed: boolean;
  diamond_dir?: string;
}

interface EndpointDetail {
  endpoint_name: string;
  endpoint_uuid: string;
  endpoint_host: string;
  endpoint_status: string;
  diamond_dir: string;
}

interface ManagedEndpointCardProps {
  endpoint: Endpoint;
  endpointDetail?: EndpointDetail;
  isManaging: boolean;
  onRemove: () => void;
}

export function ManagedEndpointCard({
  endpoint,
  endpointDetail,
  isManaging,
  onRemove
}: ManagedEndpointCardProps) {
  const isOnline = endpointDetail?.endpoint_status === 'online';

  return (
    <div className="group dashboard-card p-6 transition-all duration-200 hover:shadow-md">
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-sky-100 dark:bg-sky-900/30">
              <Server className="h-5 w-5 text-sky-600 dark:text-sky-400" />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                {endpoint.endpoint_name}
              </h3>
              <p
                className="mt-0.5 text-xs text-slate-600 dark:text-slate-300"
                style={{ fontFamily: 'var(--font-mono)' }}
              >
                UUID: {endpoint.endpoint_uuid}
              </p>

              {!endpointDetail && (
                <div className="mt-2 flex items-center gap-2">
                  <Loader2 className="h-3 w-3 animate-spin text-slate-400" />
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    Loading details...
                  </span>
                </div>
              )}

              {endpointDetail && (
                <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
                  <div className="flex items-center gap-1.5">
                    <Activity
                      className={`h-3.5 w-3.5 ${
                        isOnline
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-slate-400 dark:text-slate-500'
                      }`}
                    />
                    <span
                      className={`font-medium ${
                        isOnline
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-slate-600 dark:text-slate-300'
                      }`}
                    >
                      {endpointDetail.endpoint_status}
                    </span>
                  </div>
                  {endpointDetail.endpoint_host && (
                    <>
                      <span className="text-slate-300 dark:text-slate-600">•</span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-slate-500 dark:text-slate-400">
                          Host:
                        </span>
                        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                          {endpointDetail.endpoint_host}
                        </span>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>

          <Button
            onClick={onRemove}
            disabled={isManaging}
            variant="ghost"
            size="sm"
            className="cursor-pointer gap-2 text-slate-600 transition-all hover:bg-red-50 hover:text-red-600 dark:text-slate-300 dark:hover:bg-red-900/20 dark:hover:text-red-400"
          >
            {isManaging ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Removing...
              </>
            ) : (
              <>
                <X className="h-4 w-4" />
                Remove
              </>
            )}
          </Button>
        </div>

        <EndpointSettingsPanel endpoint={endpoint} />
      </div>
    </div>
  );
}
