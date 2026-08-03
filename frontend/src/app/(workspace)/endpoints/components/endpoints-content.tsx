'use client';

import { useEffect, useState, useCallback } from 'react';
import { useToast } from '@/components/ui/use-toast';
import { EndpointsHeader } from './endpoints-header';
import { EndpointStats } from './endpoint-stats';
import { EndpointTabs } from './endpoint-tabs';
import { ManagedEndpointCard } from './managed-endpoint-card';
import { AvailableEndpointCard } from './available-endpoint-card';
import { EmptyState } from './empty-state';
import { Loader2 } from 'lucide-react';

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
  is_managed?: boolean;
}

interface EndpointApiResponse {
  name: string;
  is_managed: boolean;
}

interface EndpointOverviewResponse {
  [uuid: string]: EndpointApiResponse;
}

type DataPrepStatus = 'idle' | 'running' | 'success' | 'error';

interface DataPrepProgress {
  completed: number;
  total: number;
  currentEndpoint: string;
}

export function EndpointsContent() {
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [endpointDetails, setEndpointDetails] = useState<EndpointDetail[]>([]);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [managingEndpoints, setManagingEndpoints] = useState<Set<string>>(
    new Set()
  );
  const [activeTab, setActiveTab] = useState<'managed' | 'available'>(
    'managed'
  );
  const [dataPrepStatus, setDataPrepStatus] =
    useState<DataPrepStatus>('idle');
  const [dataPrepProgress, setDataPrepProgress] = useState<DataPrepProgress>({
    completed: 0,
    total: 0,
    currentEndpoint: ''
  });
  const [dataPrepMessage, setDataPrepMessage] = useState('');
  const { toast } = useToast();

  const fetchEndpoints = useCallback(async () => {
    try {
      const response = await fetch('/api/endpoint_overview', {
        credentials: 'include'
      });
      if (!response.ok) {
        toast({
          title: 'Error',
          description: 'Failed to fetch endpoint list. Please try again.',
          variant: 'destructive'
        });
        throw new Error('Failed to fetch endpoints');
      }
      const data = (await response.json()) as EndpointOverviewResponse;

      const endpointArray: Endpoint[] = Object.entries(data).map(
        ([uuid, info]) => ({
          endpoint_uuid: uuid,
          endpoint_name: info.name,
          is_managed: info.is_managed
        })
      );

      const enriched = await Promise.all(
        endpointArray.map(async (ep: Endpoint) => {
          try {
            const res = await fetch(
              `/api/get_diamond_dir?endpoint_uuid=${encodeURIComponent(ep.endpoint_uuid)}`,
              { credentials: 'include' }
            );
            if (!res.ok) return ep;
            const { diamond_dir } = await res.json();
            return { ...ep, diamond_dir: diamond_dir || '' };
          } catch (error) {
            console.error(
              `Failed to fetch diamond_dir for ${ep.endpoint_uuid}:`,
              error
            );
            return ep;
          }
        })
      );
      setEndpoints(enriched);

      // Fetch endpoint details
      try {
        const detailsResponse = await fetch('/api/list_all_endpoints', {
          credentials: 'include'
        });
        if (detailsResponse.ok) {
          const details = (await detailsResponse.json()) as EndpointDetail[];
          setEndpointDetails(details);
        }
      } catch (error) {
        console.error('Failed to fetch endpoint details:', error);
      }
    } catch (error) {
      console.error('Error fetching endpoints:', error);
      toast({
        title: 'Error',
        description: 'Failed to fetch endpoints. Please try again.',
        variant: 'destructive'
      });
    }
  }, [toast]);

  useEffect(() => {
    const loadInitialData = async () => {
      await fetchEndpoints();
      setIsInitialLoading(false);
    };
    loadInitialData();
  }, [fetchEndpoints]);

  const runDataPrepWorkflow = useCallback(
    async (): Promise<{ success: boolean; message?: string }> => {
    setDataPrepStatus('running');
    setDataPrepProgress({ completed: 0, total: 0, currentEndpoint: '' });
    setDataPrepMessage('');

    try {
      const response = await fetch('/api/list_all_endpoints', {
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to fetch endpoints for preparation.');
      }

      const allEndpointDetails = (await response.json()) as EndpointDetail[];
      const eligibleEndpoints = allEndpointDetails.filter(
        (endpoint) =>
          endpoint.endpoint_status === 'online' && endpoint.is_managed
      );

      if (eligibleEndpoints.length === 0) {
        const message =
          'No online, managed endpoints available for preparation.';
        setDataPrepStatus('error');
        setDataPrepMessage(message);
        return { success: false, message };
      }

      const failures: string[] = [];

      for (let i = 0; i < eligibleEndpoints.length; i++) {
        const endpoint = eligibleEndpoints[i];

        setDataPrepProgress({
          completed: i,
          total: eligibleEndpoints.length,
          currentEndpoint: endpoint.endpoint_name
        });

        try {
          const loadResponse = await fetch('/api/load_accounts_partitions', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ endpoint_uuid: endpoint.endpoint_uuid })
          });

          if (!loadResponse.ok) {
            throw new Error('Failed to load endpoint metadata');
          }
        } catch (error) {
          console.error(
            `Failed to prepare endpoint ${endpoint.endpoint_name}`,
            error
          );
          failures.push(endpoint.endpoint_name);
        }
      }

      setDataPrepProgress({
        completed: eligibleEndpoints.length,
        total: eligibleEndpoints.length,
        currentEndpoint: ''
      });

      if (failures.length > 0) {
        const message = `Failed to prepare: ${failures.join(', ')}`;
        setDataPrepStatus('error');
        setDataPrepMessage(message);
        return { success: false, message };
      }

      setDataPrepStatus('success');
      setDataPrepMessage('Endpoint data preparation complete.');
      return { success: true };
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : 'Endpoint preparation failed.';
      setDataPrepStatus('error');
      setDataPrepMessage(message);
      return { success: false, message };
    }
  },
  []);

  const refreshEndpoints = async () => {
    try {
      setIsRefreshing(true);
      const response = await fetch('/api/register_all_endpoints', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to refresh endpoints');
      }

      const prepResult = await runDataPrepWorkflow();
      await fetchEndpoints();

      toast({
        title: prepResult?.success
          ? 'Endpoints refreshed'
          : 'Endpoints refreshed with warnings',
        description:
          prepResult?.success
            ? 'Endpoints and metadata are up to date.'
            : prepResult?.message ||
              'Some endpoints could not be prepared. Please review their status.',
        variant: prepResult?.success ? 'default' : 'destructive'
      });
    } catch (error) {
      console.error('Error refreshing endpoints:', error);
      setDataPrepStatus('error');
      setDataPrepMessage('Failed to refresh endpoints.');
      toast({
        title: 'Error',
        description:
          error instanceof Error
            ? error.message
            : 'Failed to refresh endpoints. Please try again.',
        variant: 'destructive'
      });
    } finally {
      setIsRefreshing(false);
    }
  };

  const toggleEndpointManagement = async (
    endpointUuid: string,
    isManaged: boolean
  ) => {
    try {
      setManagingEndpoints((prev) => new Set(prev).add(endpointUuid));

      const response = await fetch(`/api/manage_endpoint/${endpointUuid}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          is_managed: isManaged
        }),
        credentials: 'include'
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(
          error.error || 'Failed to update endpoint management status'
        );
      }

      toast({
        title: 'Success',
        description: `Endpoint ${isManaged ? 'added to' : 'removed from'} management successfully!`
      });

      setEndpoints((prev) =>
        prev.map((endpoint) =>
          endpoint.endpoint_uuid === endpointUuid
            ? { ...endpoint, is_managed: isManaged }
            : endpoint
        )
      );
    } catch (error) {
      console.error('Error updating endpoint management:', error);
      toast({
        title: 'Error',
        description:
          error instanceof Error
            ? error.message
            : 'Failed to update endpoint management status.',
        variant: 'destructive'
      });

      setEndpoints((prev) => [...prev]);
    } finally {
      setManagingEndpoints((prev) => {
        const next = new Set(prev);
        next.delete(endpointUuid);
        return next;
      });
    }
  };

  const managedEndpoints = endpoints.filter((ep) => ep.is_managed);
  const availableEndpoints = endpoints.filter((ep) => !ep.is_managed);

  return (
    <div className="space-y-6">
      <EndpointsHeader
        isRefreshing={isRefreshing}
        onRefresh={refreshEndpoints}
      />

      {dataPrepStatus !== 'idle' && (
        <div
          className={`dashboard-card flex items-center justify-between p-4 ${
            dataPrepStatus === 'success'
              ? 'border-emerald-200 bg-emerald-50 dark:border-emerald-900/50 dark:bg-emerald-950/30'
              : dataPrepStatus === 'running'
              ? 'border-sky-200 bg-sky-50 dark:border-sky-900/50 dark:bg-sky-950/30'
              : 'border-amber-200 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-950/30'
          }`}
        >
          <div>
            <p className="font-medium text-slate-900 dark:text-slate-100">
              {dataPrepStatus === 'running'
                ? 'Preparing endpoints'
                : dataPrepStatus === 'success'
                ? 'Endpoint data ready'
                : 'Endpoint preparation issue'}
            </p>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              {dataPrepStatus === 'running'
                ? dataPrepProgress.total > 0
                  ? `Prepared ${dataPrepProgress.completed}/${dataPrepProgress.total}${
                      dataPrepProgress.currentEndpoint
                        ? ` • ${dataPrepProgress.currentEndpoint}`
                        : ''
                    }`
                  : 'Starting endpoint preparation...'
                : dataPrepMessage}
            </p>
          </div>
          {dataPrepStatus === 'running' && (
            <Loader2 className="h-5 w-5 animate-spin text-slate-500 dark:text-slate-400" />
          )}
        </div>
      )}

      {isInitialLoading && (
        <>
          {/* Stats Loading Skeleton */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="dashboard-card animate-pulse p-5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="mb-2 h-4 w-20 rounded bg-slate-200 dark:bg-slate-700"></div>
                    <div className="h-8 w-12 rounded bg-slate-200 dark:bg-slate-700"></div>
                  </div>
                  <div className="h-12 w-12 rounded-lg bg-slate-200 dark:bg-slate-700"></div>
                </div>
              </div>
            ))}
          </div>

          {/* Content Loading */}
          <div className="flex items-center justify-center py-16">
            <div className="text-center">
              <Loader2 className="mx-auto h-12 w-12 animate-spin text-slate-600 dark:text-slate-300" />
              <p className="mt-4 text-sm text-slate-600 dark:text-slate-400">
                Loading endpoints...
              </p>
            </div>
          </div>
        </>
      )}

      {!isInitialLoading && (
        <>
          <EndpointStats
            totalEndpoints={endpoints.length}
            managedEndpoints={managedEndpoints.length}
            availableEndpoints={availableEndpoints.length}
            configuredEndpoints={
              managedEndpoints.filter((ep) => ep.diamond_dir).length
            }
          />

          <EndpointTabs activeTab={activeTab} onTabChange={setActiveTab} />

          <div
            role="tabpanel"
            id="endpoint-panel-managed"
            aria-labelledby="endpoint-tab-managed"
            hidden={activeTab !== 'managed'}
            className={activeTab === 'managed' ? 'space-y-4' : 'hidden'}
          >
              {managedEndpoints.length === 0 && (
                <EmptyState
                  type="managed"
                  onAction={() => setActiveTab('available')}
                />
              )}
              {managedEndpoints.length > 0 &&
                managedEndpoints.map((endpoint) => (
                  <ManagedEndpointCard
                    key={endpoint.endpoint_uuid}
                    endpoint={endpoint}
                    endpointDetail={endpointDetails.find(
                      (detail) =>
                        detail.endpoint_uuid === endpoint.endpoint_uuid
                    )}
                    isManaging={managingEndpoints.has(endpoint.endpoint_uuid)}
                    onRemove={() =>
                      toggleEndpointManagement(endpoint.endpoint_uuid, false)
                    }
                  />
                ))}
          </div>

          <div
            role="tabpanel"
            id="endpoint-panel-available"
            aria-labelledby="endpoint-tab-available"
            hidden={activeTab !== 'available'}
            className={activeTab === 'available' ? 'space-y-3' : 'hidden'}
          >
              {availableEndpoints.length === 0 && (
                <EmptyState type="available" />
              )}
              {availableEndpoints.length > 0 && (
                <>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    Add endpoints to Diamond management to configure work paths
                    and enable workflow execution.
                  </p>
                  {availableEndpoints.map((endpoint) => (
                    <AvailableEndpointCard
                      key={endpoint.endpoint_uuid}
                      endpoint={endpoint}
                      isAdding={managingEndpoints.has(endpoint.endpoint_uuid)}
                      onAdd={() =>
                        toggleEndpointManagement(endpoint.endpoint_uuid, true)
                      }
                    />
                  ))}
                </>
              )}
          </div>
        </>
      )}
    </div>
  );
}
