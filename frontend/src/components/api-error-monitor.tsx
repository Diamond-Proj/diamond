'use client';

import {
  type PointerEvent as ReactPointerEvent,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  useSyncExternalStore
} from 'react';
import { AlertTriangle, Bug, Trash2, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { useDeveloperMode } from '@/lib/developer-mode';

const MAX_ERRORS = 20;
const MAX_RESPONSE_LENGTH = 12_000;
const API_ERRORS_STORAGE_KEY = 'diamond:api-errors';
const API_ERRORS_CHANGE_EVENT = 'diamond:api-errors-change';
const ERROR_TIME_FORMATTER = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'medium'
});

type ApiError = {
  id: string;
  method: string;
  url: string;
  status: number | null;
  statusText: string;
  response: string;
  occurredAt: string;
};

type CapturedApiError = Omit<ApiError, 'id' | 'occurredAt'>;

type PanelDragState = {
  pointerId: number;
  startX: number;
  startY: number;
  originX: number;
  originY: number;
  panelRect: DOMRect;
};

let isApiErrorMonitorOpen = false;
const apiErrorMonitorOpenListeners = new Set<() => void>();

function setApiErrorMonitorOpen(isOpen: boolean) {
  if (isApiErrorMonitorOpen === isOpen) {
    return;
  }

  isApiErrorMonitorOpen = isOpen;
  apiErrorMonitorOpenListeners.forEach((listener) => listener());
}

function subscribeToApiErrorMonitorOpen(listener: () => void) {
  apiErrorMonitorOpenListeners.add(listener);
  return () => apiErrorMonitorOpenListeners.delete(listener);
}

function getApiErrorMonitorOpenSnapshot() {
  return isApiErrorMonitorOpen;
}

function getApiErrorMonitorOpenServerSnapshot() {
  return false;
}

function createApiError(error: CapturedApiError): ApiError {
  return {
    ...error,
    id: crypto.randomUUID(),
    occurredAt: new Date().toISOString()
  };
}

function readStoredErrors() {
  if (typeof window === 'undefined') {
    return [];
  }

  try {
    const storedErrors = JSON.parse(
      localStorage.getItem(API_ERRORS_STORAGE_KEY) ?? '[]'
    ) as ApiError[];

    return Array.isArray(storedErrors) ? storedErrors.slice(0, MAX_ERRORS) : [];
  } catch {
    return [];
  }
}

function getRequestDetails(input: RequestInfo | URL, init?: RequestInit) {
  const url =
    typeof input === 'string'
      ? input
      : input instanceof URL
        ? input.toString()
        : input.url;
  const method =
    init?.method ?? (input instanceof Request ? input.method : 'GET');

  return { method: method.toUpperCase(), url };
}

function isLocalApiRequest(url: string) {
  try {
    const parsedUrl = new URL(url, window.location.origin);
    return (
      parsedUrl.origin === window.location.origin &&
      parsedUrl.pathname.startsWith('/api/')
    );
  } catch {
    return false;
  }
}

async function readResponse(response: Response) {
  const body = await response.text();

  if (!body) {
    return '(empty response body)';
  }

  let formattedBody = body;

  try {
    formattedBody = JSON.stringify(JSON.parse(body), null, 2);
  } catch {
    // Keep non-JSON responses as plain text.
  }

  if (formattedBody.length <= MAX_RESPONSE_LENGTH) {
    return formattedBody;
  }

  return `${formattedBody.slice(0, MAX_RESPONSE_LENGTH)}\n… response truncated`;
}

export function ApiErrorMonitor() {
  const isDeveloperMode = useDeveloperMode();

  return isDeveloperMode ? <ActiveApiErrorMonitor /> : null;
}

export function ApiErrorMonitorTrigger() {
  const isDeveloperMode = useDeveloperMode();
  const [errorCount, setErrorCount] = useState(() => readStoredErrors().length);

  useEffect(() => {
    const updateErrorCount = () => setErrorCount(readStoredErrors().length);
    const handleStorage = (event: StorageEvent) => {
      if (event.key === API_ERRORS_STORAGE_KEY) {
        updateErrorCount();
      }
    };

    window.addEventListener(API_ERRORS_CHANGE_EVENT, updateErrorCount);
    window.addEventListener('storage', handleStorage);

    return () => {
      window.removeEventListener(API_ERRORS_CHANGE_EVENT, updateErrorCount);
      window.removeEventListener('storage', handleStorage);
    };
  }, []);

  if (!isDeveloperMode) {
    return null;
  }

  return (
    <Button
      type="button"
      variant="outline"
      size="default"
      aria-controls="developer-api-diagnostics"
      aria-label="Open developer diagnostics"
      onClick={() => setApiErrorMonitorOpen(true)}
      className="h-10 cursor-pointer gap-2 rounded-lg border border-slate-300/70 bg-transparent px-4 text-slate-700 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800 dark:hover:text-slate-100"
    >
      <Bug className="h-4 w-4" aria-hidden="true" />
      <span className="sr-only">Developer diagnostics</span>
      <span className="hidden sm:inline">Dev</span>
      <span
        aria-label={`${errorCount} API ${errorCount === 1 ? 'error' : 'errors'}`}
        className={`flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-[0.6875rem] font-bold tabular-nums ${
          errorCount > 0
            ? 'bg-rose-600 text-white'
            : 'bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300'
        }`}
      >
        {errorCount}
      </span>
    </Button>
  );
}

function ActiveApiErrorMonitor() {
  const [errors, setErrors] = useState<ApiError[]>(readStoredErrors);
  const isPanelOpen = useSyncExternalStore(
    subscribeToApiErrorMonitorOpen,
    getApiErrorMonitorOpenSnapshot,
    getApiErrorMonitorOpenServerSnapshot
  );
  const [isDragging, setIsDragging] = useState(false);
  const [panelOffset, setPanelOffset] = useState({ x: 0, y: 0 });
  const panelDragState = useRef<PanelDragState | null>(null);

  const handlePanelPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0 || (event.target as HTMLElement).closest('button')) {
      return;
    }

    const panel = event.currentTarget.closest<HTMLElement>(
      '[data-api-error-panel]'
    );

    if (!panel) {
      return;
    }

    panelDragState.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: panelOffset.x,
      originY: panelOffset.y,
      panelRect: panel.getBoundingClientRect()
    };
    event.currentTarget.setPointerCapture(event.pointerId);
    setIsDragging(true);
    event.preventDefault();
  };

  const handlePanelPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const dragState = panelDragState.current;

    if (!dragState || dragState.pointerId !== event.pointerId) {
      return;
    }

    const nextLeft = Math.min(
      Math.max(dragState.panelRect.left + event.clientX - dragState.startX, 8),
      Math.max(8, window.innerWidth - dragState.panelRect.width - 8)
    );
    const nextTop = Math.min(
      Math.max(dragState.panelRect.top + event.clientY - dragState.startY, 8),
      Math.max(8, window.innerHeight - dragState.panelRect.height - 8)
    );

    setPanelOffset({
      x: dragState.originX + nextLeft - dragState.panelRect.left,
      y: dragState.originY + nextTop - dragState.panelRect.top
    });
  };

  const handlePanelPointerEnd = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (panelDragState.current?.pointerId !== event.pointerId) {
      return;
    }

    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }

    panelDragState.current = null;
    setIsDragging(false);
  };

  useEffect(() => {
    localStorage.setItem(API_ERRORS_STORAGE_KEY, JSON.stringify(errors));
    window.dispatchEvent(new Event(API_ERRORS_CHANGE_EVENT));
  }, [errors]);

  useLayoutEffect(() => {
    let isActive = true;
    const originalFetch = window.fetch.bind(window);

    const addError = (error: CapturedApiError) => {
      if (!isActive) {
        return;
      }

      setErrors((currentErrors) =>
        [createApiError(error), ...currentErrors].slice(0, MAX_ERRORS)
      );
    };

    const monitoredFetch: typeof window.fetch = async (input, init) => {
      const { method, url } = getRequestDetails(input, init);
      const shouldMonitor = isLocalApiRequest(url);

      try {
        const response = await originalFetch(input, init);

        if (shouldMonitor && !response.ok) {
          void readResponse(response.clone()).then((responseBody) => {
            addError({
              method,
              url,
              status: response.status,
              statusText: response.statusText,
              response: responseBody
            });
          });
        }

        return response;
      } catch (error) {
        if (shouldMonitor) {
          addError({
            method,
            url,
            status: null,
            statusText: 'Network error',
            response: error instanceof Error ? error.message : String(error)
          });
        }

        throw error;
      }
    };

    window.fetch = monitoredFetch;

    return () => {
      isActive = false;
      setApiErrorMonitorOpen(false);
      if (window.fetch === monitoredFetch) {
        window.fetch = originalFetch;
      }
    };
  }, []);

  return (
    <>
      <p className="sr-only" aria-live="polite">
        {errors.length > 0
          ? `${errors.length} API ${errors.length === 1 ? 'error' : 'errors'} captured`
          : 'No API errors captured'}
      </p>

      <aside
        id="developer-api-diagnostics"
        data-api-error-panel
        role="region"
        aria-label="API diagnostics"
        aria-hidden={!isPanelOpen}
        inert={isPanelOpen ? undefined : true}
        style={{
          transform: isPanelOpen
            ? `translate3d(${panelOffset.x}px, calc(-50% + ${panelOffset.y}px), 0)`
            : `translate3d(calc(${panelOffset.x}px + 100% + 1rem), calc(-50% + ${panelOffset.y}px), 0)`
        }}
        className={`fixed top-1/2 right-4 z-90 flex h-[min(70vh,40rem)] w-[min(calc(100vw-2rem),42rem)] flex-col overflow-hidden rounded-xl border border-slate-300/80 bg-white/97 shadow-[0_24px_80px_rgba(15,23,42,0.24)] backdrop-blur-xl will-change-transform motion-reduce:transition-none dark:border-slate-700 dark:bg-slate-950/97 ${
          isDragging
            ? 'transition-none'
            : 'transition-[transform,opacity] duration-[450ms] ease-[cubic-bezier(0.22,1,0.36,1)]'
        } ${isPanelOpen ? 'opacity-100' : 'pointer-events-none opacity-0'}`}
      >
        <div
          data-testid="api-error-monitor-drag-handle"
          onPointerDown={handlePanelPointerDown}
          onPointerMove={handlePanelPointerMove}
          onPointerUp={handlePanelPointerEnd}
          onPointerCancel={handlePanelPointerEnd}
          className={`flex touch-none items-center justify-between gap-4 border-b border-slate-200/80 bg-slate-50/85 px-4 py-3 select-none dark:border-slate-800 dark:bg-slate-900/80 ${
            isDragging ? 'cursor-grabbing' : 'cursor-grab'
          }`}
        >
          <div className="flex min-w-0 items-center gap-2.5">
            <h2 className="truncate text-base font-semibold tracking-[0.02em] text-slate-950 [word-spacing:0.18em] dark:text-slate-100">
              API Error Monitor
            </h2>
            <span
              aria-label={`${errors.length} API ${errors.length === 1 ? 'error' : 'errors'}`}
              className={`flex h-6 min-w-6 shrink-0 items-center justify-center rounded-full px-1.5 text-xs font-bold tabular-nums ${
                errors.length > 0
                  ? 'bg-rose-600 text-white'
                  : 'bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300'
              }`}
            >
              {errors.length}
            </span>
          </div>

          <div className="flex shrink-0 items-center gap-1">
            <div className="group relative">
              <button
                type="button"
                onClick={() => setErrors([])}
                disabled={errors.length === 0}
                className="inline-flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg text-slate-600 transition-colors hover:bg-slate-200/70 disabled:cursor-not-allowed disabled:opacity-35 dark:text-slate-300 dark:hover:bg-slate-800"
                aria-label="Clear all API errors"
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
              </button>
              <span
                role="tooltip"
                className="pointer-events-none absolute top-full right-0 z-10 mt-1.5 w-max rounded-md bg-slate-950 px-2 py-1 text-[0.6875rem] font-medium text-white opacity-0 shadow-lg transition-opacity group-focus-within:opacity-100 group-hover:opacity-100 dark:bg-slate-100 dark:text-slate-950"
              >
                Clear all errors
              </span>
            </div>
            <button
              type="button"
              onClick={() => setApiErrorMonitorOpen(false)}
              className="inline-flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg text-slate-600 transition-colors hover:bg-slate-200/70 dark:text-slate-300 dark:hover:bg-slate-800"
              aria-label="Close API diagnostics"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-auto p-4">
          {errors.length > 0 ? (
            <div className="divide-y divide-slate-200 dark:divide-slate-800">
              {errors.map((error) => (
                <article
                  key={error.id}
                  role="alert"
                  aria-label="API response error"
                  className="space-y-3 py-4 first:pt-0 last:pb-0"
                >
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <AlertTriangle
                      className="h-4 w-4 shrink-0 text-rose-600 dark:text-rose-400"
                      aria-hidden="true"
                    />
                    <span className="rounded-md bg-slate-900 px-2 py-1 font-mono font-semibold text-white dark:bg-slate-100 dark:text-slate-950">
                      {error.method}
                    </span>
                    <span className="rounded-md bg-rose-100 px-2 py-1 font-mono font-semibold text-rose-800 dark:bg-rose-950 dark:text-rose-200">
                      {error.status ?? 'NETWORK'} {error.statusText}
                    </span>
                    <time
                      dateTime={error.occurredAt}
                      className="ml-auto text-slate-500 dark:text-slate-400"
                    >
                      {ERROR_TIME_FORMATTER.format(new Date(error.occurredAt))}
                    </time>
                    <button
                      type="button"
                      onClick={() =>
                        setErrors((currentErrors) =>
                          currentErrors.filter(
                            (currentError) => currentError.id !== error.id
                          )
                        )
                      }
                      className="inline-flex h-7 w-7 shrink-0 cursor-pointer items-center justify-center rounded-md text-rose-700 transition-colors hover:bg-rose-100 dark:text-rose-300 dark:hover:bg-rose-950/60"
                      aria-label="Delete API error"
                    >
                      <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                  </div>

                  <p className="font-mono text-xs break-all text-slate-600 dark:text-slate-300">
                    {error.url}
                  </p>

                  <pre className="max-h-72 overflow-auto rounded-lg border border-slate-800 bg-slate-950 p-3 font-mono text-xs leading-5 break-words whitespace-pre-wrap text-rose-200">
                    {error.response}
                  </pre>
                </article>
              ))}
            </div>
          ) : (
            <div className="flex h-full min-h-56 flex-col items-center justify-center text-center">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                No API errors
              </h3>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
