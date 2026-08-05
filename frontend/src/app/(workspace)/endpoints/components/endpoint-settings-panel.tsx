'use client';

import { useEffect, useState } from 'react';
import {
  ChevronDown,
  Folder,
  Loader2,
  Plus,
  Save,
  Settings2,
  Trash2,
  Undo2,
  X
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useToast } from '@/components/ui/use-toast';
import { cn } from '@/lib/utils';

interface Endpoint {
  endpoint_uuid: string;
  endpoint_name: string;
  is_managed: boolean;
  diamond_dir?: string;
}

interface EndpointSettingsPanelProps {
  endpoint: Endpoint;
}

interface ConfigEntry {
  id: string;
  key: string;
  value: string;
}

const UNSAFE_CONFIG_KEYS = new Set(['__proto__', 'prototype', 'constructor']);

let nextEntryId = 0;

function createEntryId() {
  nextEntryId += 1;
  return `entry-${nextEntryId}`;
}

function cloneEntries(entries: ConfigEntry[]): ConfigEntry[] {
  return entries.map((entry) => ({ ...entry }));
}

function toEditableWorkPath(path?: string) {
  return (path || '').replace(/\/diamond\/?$/, '');
}

function normalizeConfig(value: unknown): ConfigEntry[] {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return [];
  }

  return Object.entries(value).map(([key, entryValue]) => {
    const editableValue =
      typeof entryValue === 'string'
        ? entryValue
        : entryValue === null
          ? 'null'
          : JSON.stringify(entryValue);

    return {
      id: createEntryId(),
      key,
      value: editableValue
    };
  });
}

function parseValue(key: string, rawValue: string): unknown {
  const trimmedValue = rawValue.trim();

  if (trimmedValue === 'true') {
    return true;
  }

  if (trimmedValue === 'false') {
    return false;
  }

  if (trimmedValue === 'null') {
    return null;
  }

  const looksLikeJson =
    (trimmedValue.startsWith('{') && trimmedValue.endsWith('}')) ||
    (trimmedValue.startsWith('[') && trimmedValue.endsWith(']'));

  if (looksLikeJson) {
    try {
      return JSON.parse(trimmedValue);
    } catch {
      throw new Error(`Invalid JSON value for "${key}"`);
    }
  }

  return rawValue;
}

function buildPayload(entries: ConfigEntry[]) {
  const payload = Object.create(null) as Record<string, unknown>;
  const seenKeys = new Set<string>();

  for (const entry of entries) {
    const trimmedKey = entry.key.trim();

    if (!trimmedKey) {
      continue;
    }

    if (UNSAFE_CONFIG_KEYS.has(trimmedKey)) {
      throw new Error(`Unsafe key "${trimmedKey}" is not allowed`);
    }

    if (seenKeys.has(trimmedKey)) {
      throw new Error(`Duplicate key "${trimmedKey}"`);
    }

    seenKeys.add(trimmedKey);

    payload[trimmedKey] = parseValue(trimmedKey, entry.value);
  }

  const finalizedPayload = Object.keys(payload).length > 0 ? payload : null;

  return {
    payload: finalizedPayload,
    normalizedEntries: normalizeConfig(finalizedPayload)
  };
}

function getSignature(entries: ConfigEntry[]) {
  return JSON.stringify(
    entries.map((entry) => ({
      key: entry.key,
      value: entry.value
    }))
  );
}

export function EndpointSettingsPanel({
  endpoint
}: EndpointSettingsPanelProps) {
  const pathInputId = `diamond-work-path-${endpoint.endpoint_uuid}`;
  const settingsPanelId = `endpoint-settings-panel-${endpoint.endpoint_uuid}`;
  const [isExpanded, setIsExpanded] = useState(false);
  const [savedPath, setSavedPath] = useState(toEditableWorkPath(endpoint.diamond_dir));
  const [path, setPath] = useState(toEditableWorkPath(endpoint.diamond_dir));
  const [isSavingPath, setIsSavingPath] = useState(false);
  const [isLoadingConfig, setIsLoadingConfig] = useState(false);
  const [isSavingConfig, setIsSavingConfig] = useState(false);
  const [hasLoadedConfig, setHasLoadedConfig] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [savedEntries, setSavedEntries] = useState<ConfigEntry[]>([]);
  const [entries, setEntries] = useState<ConfigEntry[]>([]);
  const { toast } = useToast();

  useEffect(() => {
    setSavedPath(toEditableWorkPath(endpoint.diamond_dir));
    setPath(toEditableWorkPath(endpoint.diamond_dir));
  }, [endpoint.diamond_dir]);

  useEffect(() => {
    setHasLoadedConfig(false);
    setIsLoadingConfig(false);
    setLoadError(null);
    setSavedEntries([]);
    setEntries([]);
    setReloadKey(0);
  }, [endpoint.endpoint_uuid]);

  useEffect(() => {
    let isMounted = true;

    if (!isExpanded) {
      return () => {
        isMounted = false;
      };
    }

    if (hasLoadedConfig && reloadKey === 0) {
      return () => {
        isMounted = false;
      };
    }

    const loadConfig = async () => {
      try {
        setIsLoadingConfig(true);

        const response = await fetch(
          `/api/user_endpoint_config/${endpoint.endpoint_uuid}`,
          {
            credentials: 'include'
          }
        );

        if (!response.ok) {
          throw new Error(`Failed to load config (${response.status})`);
        }

        const data = (await response.json()) as {
          user_endpoint_config?: unknown;
        };

        if (!isMounted) {
          return;
        }

        const normalizedEntries = normalizeConfig(data.user_endpoint_config);
        setSavedEntries(normalizedEntries);
        setEntries(cloneEntries(normalizedEntries));
        setHasLoadedConfig(true);
        setLoadError(null);
        setReloadKey(0);
      } catch (error) {
        console.error('Error fetching endpoint user config:', error);

        if (!isMounted) {
          return;
        }

        setLoadError(
          error instanceof Error
            ? error.message
            : 'Failed to load endpoint config.'
        );
      } finally {
        if (isMounted) {
          setIsLoadingConfig(false);
        }
      }
    };

    loadConfig();

    return () => {
      isMounted = false;
    };
  }, [endpoint.endpoint_uuid, hasLoadedConfig, isExpanded, reloadKey]);

  const normalizedPath = path.trim().replace(/\/diamond\/?$/, '');
  const pathHasChanges = normalizedPath !== savedPath;
  const configHasChanges = getSignature(entries) !== getSignature(savedEntries);
  const isBusy = isSavingPath || isSavingConfig;
  const configSummary =
    hasLoadedConfig && savedEntries.length > 0
      ? `${savedEntries.length} ${savedEntries.length === 1 ? 'key' : 'keys'}`
      : 'No config';
  const canEditLoadedConfig = hasLoadedConfig && !isLoadingConfig;

  const addEntry = () => {
    setEntries((current) => [
      ...current,
      {
        id: createEntryId(),
        key: '',
        value: ''
      }
    ]);
  };

  const updateEntry = (
    id: string,
    field: 'key' | 'value',
    nextValue: string
  ) => {
    setEntries((current) =>
      current.map((entry) =>
        entry.id === id ? { ...entry, [field]: nextValue } : entry
      )
    );
  };

  const removeEntry = (id: string) => {
    setEntries((current) => current.filter((entry) => entry.id !== id));
  };

  const handleUndoConfig = () => {
    setEntries(cloneEntries(savedEntries));
  };

  const handleClearConfig = () => {
    setEntries([]);
  };

  const handleSavePath = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (isBusy) {
      return;
    }

    if (!normalizedPath) {
      toast({
        title: 'Error',
        description: 'Path is required.',
        variant: 'destructive'
      });
      return;
    }

    try {
      setIsSavingPath(true);

      const response = await fetch('/api/set_diamond_work_path', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          endpoint_uuid: endpoint.endpoint_uuid,
          diamond_work_path: normalizedPath
        }),
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to save diamond directory');
      }

      setSavedPath(normalizedPath);
      setPath(normalizedPath);

      toast({
        title: 'Success',
        description: 'Work path saved successfully.'
      });
    } catch (error) {
      console.error('Error saving diamond directory:', error);
      toast({
        title: 'Error',
        description: 'Failed to save work path. Please try again.',
        variant: 'destructive'
      });
    } finally {
      setIsSavingPath(false);
    }
  };

  const handleSaveConfig = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (isBusy) {
      return;
    }

    let preparedConfig: ReturnType<typeof buildPayload>;

    try {
      preparedConfig = buildPayload(entries);
    } catch (error) {
      toast({
        title: 'Invalid value',
        description:
          error instanceof Error
            ? error.message
            : 'One or more values could not be parsed.',
        variant: 'destructive'
      });
      return;
    }

    try {
      setIsSavingConfig(true);

      const response = await fetch(
        `/api/user_endpoint_config/${endpoint.endpoint_uuid}`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'include',
          body: JSON.stringify({
            user_endpoint_config: preparedConfig.payload
          })
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to update endpoint config (${response.status})`);
      }

      setSavedEntries(preparedConfig.normalizedEntries);
      setEntries(cloneEntries(preparedConfig.normalizedEntries));
      setHasLoadedConfig(true);
      setLoadError(null);

      toast({
        title: 'Success',
        description:
          preparedConfig.payload === null
            ? 'Endpoint config cleared.'
            : 'Endpoint config saved successfully.'
      });
    } catch (error) {
      console.error('Error saving endpoint user config:', error);
      toast({
        title: 'Error',
        description: 'Failed to save endpoint config. Please try again.',
        variant: 'destructive'
      });
    } finally {
      setIsSavingConfig(false);
    }
  };

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.94),rgba(248,250,252,0.88))] shadow-sm shadow-slate-950/4 dark:border-slate-800 dark:bg-[linear-gradient(180deg,rgba(15,23,42,0.66),rgba(2,6,23,0.54))]">
      <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-3">
        <div className="flex min-w-0 items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-100 text-sky-700 dark:bg-sky-950/40 dark:text-sky-200">
            <Settings2 className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Endpoint Settings
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] font-medium">
              <span
                className={cn(
                  'rounded-full px-2 py-0.5',
                  savedPath
                    ? 'bg-sky-100 text-sky-700 dark:bg-sky-950/40 dark:text-sky-200'
                    : 'bg-slate-200/90 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
                )}
              >
                {savedPath ? 'Path set' : 'Path missing'}
              </span>
              <span className="rounded-full bg-slate-200/90 px-2 py-0.5 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {configSummary}
              </span>
            </div>
          </div>
        </div>

        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setIsExpanded((current) => !current)}
          aria-expanded={isExpanded}
          aria-controls={settingsPanelId}
          className="h-8 cursor-pointer gap-1.5 rounded-full border-slate-200 bg-white/80 px-2.5 text-xs text-slate-700 transition-all duration-200 hover:border-sky-200 hover:bg-sky-50 hover:text-sky-700 dark:border-slate-700 dark:bg-slate-900/80 dark:text-slate-200 dark:hover:border-sky-900/70 dark:hover:bg-sky-950/30 dark:hover:text-sky-100"
        >
          <ChevronDown
            className={cn(
              'h-4 w-4 transition-transform duration-300',
              isExpanded && 'rotate-180'
            )}
          />
          {isExpanded ? 'Hide' : 'Edit'}
        </Button>
      </div>

      <div
        id={settingsPanelId}
        aria-hidden={!isExpanded}
        inert={!isExpanded}
        className={cn(
          'grid border-t border-slate-200/80 transition-[grid-template-rows,opacity] duration-300 ease-out dark:border-slate-800',
          isExpanded
            ? 'grid-rows-[1fr] opacity-100'
            : 'grid-rows-[0fr] opacity-0 pointer-events-none'
        )}
      >
        <div className="overflow-hidden">
          <div
            className={cn(
              'transition-transform duration-300 ease-out',
              isExpanded ? 'translate-y-0' : '-translate-y-2'
            )}
          >
            <form
              onSubmit={handleSavePath}
              className="grid gap-2 px-3 py-3 lg:grid-cols-[172px_minmax(0,1fr)_auto]"
            >
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100/90 text-slate-600 dark:bg-slate-900/90 dark:text-slate-300">
                  <Folder className="h-4 w-4" />
                </div>
                <div>
                  <label
                    htmlFor={pathInputId}
                    className="text-xs font-semibold whitespace-nowrap text-slate-600 dark:text-slate-300"
                  >
                    Diamond Work Path
                  </label>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">
                    Base directory
                  </p>
                </div>
              </div>

              <Input
                id={pathInputId}
                type="text"
                value={path}
                onChange={(event) => setPath(event.target.value)}
                placeholder="/path/to/diamond/work/directory"
                disabled={isBusy}
                className="h-9 border-slate-200/80 bg-white/85 text-xs text-slate-900 placeholder:text-slate-400 focus-visible:ring-sky-500/20 dark:border-slate-700/80 dark:bg-slate-900/75 dark:text-slate-100 dark:placeholder:text-slate-500"
              />

              <Button
                type="submit"
                disabled={isBusy || !normalizedPath || !pathHasChanges}
                className="h-9 cursor-pointer gap-1.5 rounded-full bg-slate-900 px-3 text-xs text-white transition-all duration-200 hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
              >
                {isSavingPath ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4" />
                    Save Path
                  </>
                )}
              </Button>
            </form>

            <form
              onSubmit={handleSaveConfig}
              className="space-y-3 border-t border-slate-200/80 px-3 py-3 dark:border-slate-800"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100/90 text-slate-600 dark:bg-slate-900/90 dark:text-slate-300">
                    <Settings2 className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">
                      Config
                    </p>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400">
                      Key/value pairs
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={addEntry}
                    disabled={isBusy || !canEditLoadedConfig}
                    className="h-8 cursor-pointer gap-1.5 rounded-full px-2.5 text-xs"
                  >
                    <Plus className="h-4 w-4" />
                    Add Key
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleUndoConfig}
                    disabled={isBusy || !configHasChanges || !hasLoadedConfig}
                    className="h-8 cursor-pointer gap-1.5 rounded-full px-2.5 text-xs"
                  >
                    <Undo2 className="h-4 w-4" />
                    Undo
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleClearConfig}
                    disabled={isBusy || !canEditLoadedConfig || entries.length === 0}
                    className="h-8 cursor-pointer gap-1.5 rounded-full px-2.5 text-xs text-red-600 hover:border-red-200 hover:bg-red-50 hover:text-red-700 dark:text-red-300 dark:hover:border-red-900/70 dark:hover:bg-red-950/20 dark:hover:text-red-200"
                  >
                    <Trash2 className="h-4 w-4" />
                    Clear All
                  </Button>
                  <Button
                    type="submit"
                    size="sm"
                    disabled={
                      isBusy ||
                      isLoadingConfig ||
                      !configHasChanges ||
                      !hasLoadedConfig
                    }
                    className="h-8 cursor-pointer gap-1.5 rounded-full bg-slate-900 px-2.5 text-xs text-white transition-all duration-200 hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
                  >
                    {isSavingConfig ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save className="h-4 w-4" />
                        Save Config
                      </>
                    )}
                  </Button>
                </div>
              </div>

              {isLoadingConfig ? (
                <div className="flex min-h-16 items-center justify-center py-2">
                  <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading...
                  </div>
                </div>
              ) : (
                <>
                  {loadError && (
                    <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
                      <span>Could not load saved config.</span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setReloadKey((value) => value + 1)}
                        className="h-7 cursor-pointer rounded-full px-2 text-amber-900 hover:bg-amber-100 hover:text-amber-950 dark:text-amber-200 dark:hover:bg-amber-900/30 dark:hover:text-amber-50"
                      >
                        Retry
                      </Button>
                    </div>
                  )}

                  {!hasLoadedConfig ? (
                    <div className="px-1 py-4 text-center">
                      <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
                        Config unavailable
                      </p>
                    </div>
                  ) : entries.length === 0 ? (
                    <div className="px-1 py-4 text-center">
                      <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
                        No config
                      </p>
                    </div>
                  ) : (
                    <div className="overflow-hidden">
                      <div className="grid grid-cols-[minmax(0,0.78fr)_minmax(0,1.22fr)_auto] gap-2 px-2 py-1 text-[10px] font-medium uppercase tracking-[0.16em] text-slate-400 dark:text-slate-500">
                        <span>Key</span>
                        <span>Value</span>
                        <span></span>
                      </div>

                      {entries.map((entry, index) => (
                        <div
                          key={entry.id}
                          className="grid grid-cols-[minmax(0,0.78fr)_minmax(0,1.22fr)_auto] gap-2 border-t border-slate-200/70 py-2 first:border-t-0 dark:border-slate-800/80"
                        >
                          <Input
                            value={entry.key}
                            onChange={(event) =>
                              updateEntry(entry.id, 'key', event.target.value)
                            }
                            aria-label={`Config key ${index + 1}`}
                            placeholder={index === 0 ? 'account' : 'key'}
                            disabled={isBusy}
                            className="h-9 border-slate-200/80 bg-white/80 text-xs dark:border-slate-700/80 dark:bg-slate-900/70"
                          />
                          <Input
                            value={entry.value}
                            onChange={(event) =>
                              updateEntry(entry.id, 'value', event.target.value)
                            }
                            aria-label={`Config value ${index + 1}`}
                            placeholder={index === 0 ? 'bcrc-delta-cpu' : 'value'}
                            disabled={isBusy}
                            className="h-9 border-slate-200/80 bg-white/80 text-xs dark:border-slate-700/80 dark:bg-slate-900/70"
                          />
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            onClick={() => removeEntry(entry.id)}
                            disabled={isBusy || !canEditLoadedConfig}
                            aria-label={
                              entry.key.trim()
                                ? `Remove config entry ${entry.key.trim()}`
                                : 'Remove config entry'
                            }
                            className="h-9 w-9 cursor-pointer rounded-md text-slate-500 transition-colors duration-200 hover:bg-red-50 hover:text-red-600 dark:text-slate-400 dark:hover:bg-red-950/20 dark:hover:text-red-300"
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
