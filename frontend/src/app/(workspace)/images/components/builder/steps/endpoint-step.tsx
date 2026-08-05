'use client';

import { useState, useEffect, useCallback } from 'react';
import { Server, Cpu, User, Calendar } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { BuilderFormData, Endpoint } from '@/app/(workspace)/images/types';
import { VirtualSelect } from '@/components/ui/virtual-select';

interface EndpointStepProps {
  formData: Partial<BuilderFormData>;
  onUpdate: (data: Partial<BuilderFormData>) => void;
}

export function EndpointStep({ formData, onUpdate }: EndpointStepProps) {
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [partitions, setPartitions] = useState<string[]>([]);
  const [accounts, setAccounts] = useState<string[]>([]);
  const [isLoadingEndpoints, setIsLoadingEndpoints] = useState(false);
  const [isLoadingPartitions, setIsLoadingPartitions] = useState(false);
  const [isLoadingAccounts, setIsLoadingAccounts] = useState(false);
  const [hasDiamondDir, setHasDiamondDir] = useState<boolean>(true);
  const [diamondDirError, setDiamondDirError] = useState<string>('');

  const checkDiamondDir = useCallback(async (endpointUuid: string) => {
    if (!endpointUuid) {
      setHasDiamondDir(true);
      setDiamondDirError('');
      return;
    }

    try {
      const response = await fetch(
        `/api/get_diamond_dir?endpoint_uuid=${endpointUuid}`,
        {
          credentials: 'include'
        }
      );
      const data = await response.json();
      const diamondDirExists = data.diamond_dir !== null && data.diamond_dir !== undefined;
      setHasDiamondDir(diamondDirExists);
      
      if (!diamondDirExists) {
        setDiamondDirError('Diamond directory not configured for this endpoint. Please configure it in settings.');
        onUpdate({ hasDiamondDir: false });
      } else {
        setDiamondDirError('');
        onUpdate({ hasDiamondDir: true });
      }
    } catch (error) {
      console.error('Error checking diamond directory:', error);
      setHasDiamondDir(false);
      setDiamondDirError('Failed to verify diamond directory configuration');
      onUpdate({ hasDiamondDir: false });
    }
  }, [onUpdate]);

  // Fetch all available endpoints on component mount
  useEffect(() => {
    const fetchEndpoints = async () => {
      setIsLoadingEndpoints(true);
      try {
        const response = await fetch('/api/list_active_managed_endpoints', {
          method: 'GET',
          credentials: 'include'
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        setEndpoints(data);
      } catch (error) {
        console.error('Error fetching endpoints:', error);
        setEndpoints([]);
      } finally {
        setIsLoadingEndpoints(false);
      }
    };
    fetchEndpoints();
  }, []);

  // Check diamond directory when endpoint changes
  useEffect(() => {
    if (formData.endpoint) {
      checkDiamondDir(formData.endpoint);
    } else {
      setHasDiamondDir(true);
      setDiamondDirError('');
    }
  }, [formData.endpoint, checkDiamondDir]);

  // Fetch partitions and accounts when endpoint changes
  useEffect(() => {
    if (formData.endpoint) {
      const fetchPartitions = async () => {
        setIsLoadingPartitions(true);
        try {
          const response = await fetch('/api/list_partitions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ endpoint: formData.endpoint })
          });

          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }

          const data = await response.json();
          setPartitions(data || []);
          // setPartitions(['partition1', 'partition2']); // Temporary hardcode for testing
        } catch (error) {
          console.error('Error fetching partitions:', error);
          setPartitions([]);
        } finally {
          setIsLoadingPartitions(false);
        }
      };
      fetchPartitions();

      const fetchAccounts = async () => {
        setIsLoadingAccounts(true);
        try {
          const response = await fetch('/api/list_accounts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ endpoint: formData.endpoint })
          });

          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }

          const data = await response.json();
          setAccounts(data || []);
          // setAccounts(['test', 'test1', 'test2']); // Temporary hardcode for testing
        } catch (error) {
          console.error('Error fetching accounts:', error);
          setAccounts([]);
        } finally {
          setIsLoadingAccounts(false);
        }
      };
      fetchAccounts();
    } else {
      // Clear partitions and accounts when no endpoint is selected
      setPartitions([]);
      setAccounts([]);
    }
  }, [formData.endpoint]);

  const isEndpointSelected = !!formData.endpoint;

  // Filter only online, managed endpoints and create options for VirtualSelect
  const eligibleEndpoints = endpoints.filter(
    (endpoint) => endpoint.endpoint_status === 'online' && endpoint.is_managed
  );
  const endpointOptions = eligibleEndpoints.map(
    (endpoint) => `${endpoint.endpoint_name} (${endpoint.endpoint_status})`
  );

  // Get selected endpoint name for display
  const selectedEndpoint = endpoints.find(
    (ep) => ep.endpoint_uuid === formData.endpoint
  );
  const selectedEndpointDisplay = selectedEndpoint
    ? `${selectedEndpoint.endpoint_name} (${selectedEndpoint.endpoint_status})`
    : undefined;

  const handleEndpointSelect = (displayName: string) => {
    // Find the endpoint UUID from the display name
    const endpoint = eligibleEndpoints.find(
      (ep) => `${ep.endpoint_name} (${ep.endpoint_status})` === displayName
    );
    if (endpoint) {
      onUpdate({ endpoint: endpoint.endpoint_uuid });
      checkDiamondDir(endpoint.endpoint_uuid);
    }
  };

  return (
    <div className="space-y-8">
      {/* Grid Layout for large screens */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        {/* Left Column */}
        <div className="space-y-8">
          {/* Endpoint Selection */}
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-sky-100 dark:bg-sky-950/30">
                <Server className="h-5 w-5 text-sky-700 dark:text-sky-300" />
              </div>
              <div>
                <h4 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                  HPC Endpoint
                </h4>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  Select your compute endpoint
                </p>
              </div>
            </div>

            <div className="space-y-4">
              <VirtualSelect
                options={endpointOptions}
                selected={selectedEndpointDisplay}
                onSelect={handleEndpointSelect}
                placeholder="Choose an HPC endpoint"
                loading={isLoadingEndpoints}
                className={diamondDirError || !hasDiamondDir ? 'border-red-500' : ''}
              />

              {diamondDirError && (
                <p className="text-sm text-red-600">{diamondDirError}</p>
              )}

              {!isLoadingEndpoints &&
                endpoints.length > 0 &&
                eligibleEndpoints.length === 0 && (
                  <p className="text-sm text-amber-600">
                    No online, managed endpoints are available. Please refresh
                    your endpoints in Settings or contact your administrator.
                  </p>
                )}
            </div>
          </div>

          {/* Partition Selection */}
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-100 dark:bg-indigo-950/30">
                <Cpu className="h-5 w-5 text-indigo-700 dark:text-indigo-300" />
              </div>
              <div>
                <h4 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                  Partition
                </h4>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  Choose compute partition
                </p>
              </div>
            </div>

            {!isEndpointSelected ? (
              <div className="rounded-xl border-2 border-dashed border-slate-200/80 bg-slate-50/70 p-8 text-center dark:border-slate-700/80 dark:bg-slate-800/50">
                <Cpu className="mx-auto mb-3 h-8 w-8 text-slate-400 dark:text-slate-500" />
                <p className="mb-1 text-sm font-medium text-slate-600 dark:text-slate-300">
                  Select an endpoint first
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Partitions will be available after endpoint selection
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {partitions.length > 0 ? (
                  <VirtualSelect
                    options={partitions}
                    selected={formData.partition}
                    onSelect={(partition) => onUpdate({ partition })}
                    placeholder="Choose a partition"
                    loading={isLoadingPartitions}
                  />
                ) : (
                  <div className="space-y-3">
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                      Partition Name
                    </label>
                    <Input
                      placeholder="Enter partition name"
                      value={formData.partition || ''}
                      onChange={(e) => onUpdate({ partition: e.target.value })}
                      className="h-11 border-slate-200/80 bg-white/80 dark:border-slate-700/80 dark:bg-slate-900/80 focus-visible:ring-rose-500/25"
                    />
                    {!isLoadingPartitions && (
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        No available partitions found for this endpoint
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-8">
          {/* Account Selection */}
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100 dark:bg-emerald-950/30">
                <User className="h-5 w-5 text-emerald-700 dark:text-emerald-300" />
              </div>
              <div>
                <h4 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                  HPC Account
                </h4>
                <p className="text-sm text-slate-600 dark:text-slate-400">Your compute account</p>
              </div>
            </div>

            {!isEndpointSelected ? (
              <div className="rounded-xl border-2 border-dashed border-slate-200/80 bg-slate-50/70 p-8 text-center dark:border-slate-700/80 dark:bg-slate-800/50">
                <User className="mx-auto mb-3 h-8 w-8 text-slate-400 dark:text-slate-500" />
                <p className="mb-1 text-sm font-medium text-slate-600 dark:text-slate-300">
                  Select an endpoint first
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Accounts will be available after endpoint selection
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {accounts.length > 0 && (
                  <VirtualSelect
                    options={accounts}
                    selected={formData.account}
                    onSelect={(account) => onUpdate({ account })}
                    placeholder="Choose an account"
                    loading={isLoadingAccounts}
                  />
                )}

                <div className="space-y-3">
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                    {accounts.length > 0 ? 'Or enter manually' : 'Account Name'}
                  </label>
                  <Input
                    placeholder="Enter account name"
                    value={formData.account || ''}
                    onChange={(e) => onUpdate({ account: e.target.value })}
                    className="h-11 border-slate-200/80 bg-white/80 dark:border-slate-700/80 dark:bg-slate-900/80 focus-visible:ring-rose-500/25"
                  />
                  {accounts.length === 0 && !isLoadingAccounts && (
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      No available accounts found for this endpoint
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Reservation (Optional) */}
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-100 dark:bg-amber-950/30">
                <Calendar className="h-5 w-5 text-amber-700 dark:text-amber-300" />
              </div>
              <div>
                <h4 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                  Reservation
                  <span className="ml-2 text-sm font-normal text-slate-500 dark:text-slate-400">
                    (Optional)
                  </span>
                </h4>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  Reserved compute resources
                </p>
              </div>
            </div>

            {!isEndpointSelected ? (
              <div className="rounded-xl border-2 border-dashed border-slate-200/80 bg-slate-50/70 p-8 text-center dark:border-slate-700/80 dark:bg-slate-800/50">
                <Calendar className="mx-auto mb-3 h-8 w-8 text-slate-400 dark:text-slate-500" />
                <p className="mb-1 text-sm font-medium text-slate-600 dark:text-slate-300">
                  Select an endpoint first
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Reservations can be specified after endpoint selection
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Reservation Name
                </label>
                <Input
                  placeholder="Enter reservation name (optional)"
                  value={formData.reservation || ''}
                  onChange={(e) => onUpdate({ reservation: e.target.value })}
                  className="h-11 border-slate-200/80 bg-white/80 dark:border-slate-700/80 dark:bg-slate-900/80 focus-visible:ring-rose-500/25"
                />
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Leave empty if no reservation is required
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
