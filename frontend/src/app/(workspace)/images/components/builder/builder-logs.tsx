'use client';

import {
  useState,
  useEffect,
  useCallback,
  useRef,
  type KeyboardEvent
} from 'react';
import {
  Terminal,
  AlertCircle,
  CheckCircle2,
  X,
  RefreshCw
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { BuildLogResponse } from '@/app/(workspace)/images/types';

interface BuilderLogsProps {
  taskId: string;
  containerName: string;
  endpoint: string;
  onComplete: () => void;
}

export function BuilderLogs({
  taskId,
  containerName,
  endpoint,
  onComplete
}: BuilderLogsProps) {
  const [stdoutLogs, setStdoutLogs] = useState<string>('Initializing build...');
  const [stderrLogs, setStderrLogs] = useState<string>('');
  const [buildStatus, setBuildStatus] = useState<string>('starting');
  const [isPolling, setIsPolling] = useState(true);
  const [activeTab, setActiveTab] = useState<'stdout' | 'stderr'>('stdout');

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const stderrPollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const currentLogTaskIdRef = useRef<string | null>(null);
  const currentStderrLogTaskIdRef = useRef<string | null>(null);

  const fetchLogs = useCallback(
    async (logType: 'stdout' | 'stderr') => {
      try {
        const url = new URL('/api/get_build_log', window.location.origin);
        url.searchParams.append('container_name', containerName);
        url.searchParams.append('endpoint_id', endpoint);
        url.searchParams.append('log_type', logType);
        url.searchParams.append('task_id', taskId);

        const logTaskId =
          logType === 'stdout'
            ? currentLogTaskIdRef.current
            : currentStderrLogTaskIdRef.current;
        if (logTaskId) {
          url.searchParams.append('log_task_id', logTaskId);
        }

        const response = await fetch(url);
        if (!response.ok) throw new Error(`Failed to fetch ${logType} logs`);

        const data: BuildLogResponse = await response.json();

        if (data.log_task_id) {
          if (logType === 'stdout') {
            currentLogTaskIdRef.current = data.log_task_id;
          } else {
            currentStderrLogTaskIdRef.current = data.log_task_id;
          }
        }

        if (logType === 'stdout') {
          setStdoutLogs(data.log_content || 'Waiting for build logs...');
          setBuildStatus(data.status);
        } else {
          setStderrLogs(data.log_content || 'No error logs');
        }

        return (
          data.status === 'completed' ||
          data.status === 'failed' ||
          data.status === 'error'
        );
      } catch (error) {
        console.error(`Error fetching ${logType} logs:`, error);
        if (logType === 'stdout') {
          setStdoutLogs('Error fetching build logs');
          setBuildStatus('error');
        } else {
          setStderrLogs('Error fetching error logs');
        }
        return true;
      }
    },
    [containerName, endpoint, taskId]
  );

  useEffect(() => {
    if (!isPolling) return;

    const startPolling = () => {
      // Initial fetch
      fetchLogs('stdout');
      fetchLogs('stderr');

      // Start polling intervals
      pollIntervalRef.current = setInterval(async () => {
        const shouldStop = await fetchLogs('stdout');
        if (shouldStop) {
          setIsPolling(false);
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
          }
        }
      }, 3000);

      stderrPollIntervalRef.current = setInterval(() => {
        fetchLogs('stderr');
      }, 3000);

      // Safety timeout after 30 minutes
      setTimeout(() => {
        setIsPolling(false);
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        if (stderrPollIntervalRef.current)
          clearInterval(stderrPollIntervalRef.current);
      }, 1800000);
    };

    startPolling();

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      if (stderrPollIntervalRef.current)
        clearInterval(stderrPollIntervalRef.current);
    };
  }, [isPolling, fetchLogs]);

  const getStatusIcon = () => {
    switch (buildStatus) {
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'failed':
      case 'error':
        return <X className="h-5 w-5 text-red-500" />;
      default:
        return <RefreshCw className="h-5 w-5 animate-spin text-slate-500 dark:text-slate-400" />;
    }
  };

  const getStatusColor = () => {
    switch (buildStatus) {
      case 'completed':
        return 'text-green-600 dark:text-green-400';
      case 'failed':
      case 'error':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-slate-600 dark:text-slate-300';
    }
  };

  const handleComplete = () => {
    setIsPolling(false);
    onComplete();
  };

  const logTabs: Array<'stdout' | 'stderr'> = ['stdout', 'stderr'];

  const handleTabKeyDown = (
    event: KeyboardEvent<HTMLButtonElement>,
    tab: 'stdout' | 'stderr'
  ) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
      return;
    }

    event.preventDefault();

    if (event.key === 'Home') {
      setActiveTab(logTabs[0]);
      return;
    }

    if (event.key === 'End') {
      setActiveTab(logTabs[logTabs.length - 1]);
      return;
    }

    const currentIndex = logTabs.indexOf(tab);
    const nextIndex =
      event.key === 'ArrowRight'
        ? (currentIndex + 1) % logTabs.length
        : (currentIndex - 1 + logTabs.length) % logTabs.length;
    setActiveTab(logTabs[nextIndex]);
  };

  return (
    <div className="space-y-6 p-6">
      {/* Status Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {getStatusIcon()}
          <div>
            <h3 className="text-lg font-semibold">Building {containerName}</h3>
            <p className={`text-sm font-medium capitalize ${getStatusColor()}`}>
              Status: {buildStatus}
            </p>
          </div>
        </div>

        {buildStatus === 'completed' && (
          <Button
            onClick={handleComplete}
            className="bg-primary text-primary-foreground hover:bg-primary/90"
          >
            Done
          </Button>
        )}
      </div>

      {/* Log Tabs */}
      <div className="border-b border-slate-200/70 dark:border-slate-700/70">
        <div className="flex space-x-1" role="tablist" aria-label="Build logs">
          <button
            onClick={() => setActiveTab('stdout')}
            onKeyDown={(event) => handleTabKeyDown(event, 'stdout')}
            role="tab"
            id="builder-logs-tab-stdout"
            aria-selected={activeTab === 'stdout'}
            aria-controls="builder-logs-panel-stdout"
            tabIndex={activeTab === 'stdout' ? 0 : -1}
            className={`cursor-pointer border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'stdout'
                ? 'border-slate-900 text-slate-900 dark:border-slate-100 dark:text-slate-100'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            <div className="flex items-center gap-2">
              <Terminal className="h-4 w-4" />
              Build Output
            </div>
          </button>
          <button
            onClick={() => setActiveTab('stderr')}
            onKeyDown={(event) => handleTabKeyDown(event, 'stderr')}
            role="tab"
            id="builder-logs-tab-stderr"
            aria-selected={activeTab === 'stderr'}
            aria-controls="builder-logs-panel-stderr"
            tabIndex={activeTab === 'stderr' ? 0 : -1}
            className={`cursor-pointer border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'stderr'
                ? 'border-slate-900 text-slate-900 dark:border-slate-100 dark:text-slate-100'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              Error Output
            </div>
          </button>
        </div>
      </div>

      {/* Log Content */}
      <div className="overflow-hidden rounded-lg border border-slate-200/70 bg-slate-950 p-4 font-mono text-sm text-slate-200 dark:border-slate-700/70">
        <div className="max-h-100 overflow-y-auto">
          <div
            role="tabpanel"
            id="builder-logs-panel-stdout"
            aria-labelledby="builder-logs-tab-stdout"
            hidden={activeTab !== 'stdout'}
          >
            <pre className="whitespace-pre-wrap">{stdoutLogs}</pre>
          </div>
          <div
            role="tabpanel"
            id="builder-logs-panel-stderr"
            aria-labelledby="builder-logs-tab-stderr"
            hidden={activeTab !== 'stderr'}
          >
            <pre className="whitespace-pre-wrap">{stderrLogs}</pre>
          </div>
        </div>
      </div>

      {/* Status Messages */}
      {buildStatus === 'completed' && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-950/20">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-green-500" />
            <div className="text-sm">
              <p className="mb-1 font-medium text-green-900 dark:text-green-100">
                Build Completed Successfully!
              </p>
              <p className="text-green-700 dark:text-green-300">
                {`Your container image "${containerName}" has been built and is
                ready for use.`}
              </p>
            </div>
          </div>
        </div>
      )}

      {(buildStatus === 'failed' || buildStatus === 'error') && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-950/20">
          <div className="flex items-start gap-3">
            <X className="mt-0.5 h-5 w-5 shrink-0 text-red-500" />
            <div className="text-sm">
              <p className="mb-1 font-medium text-red-900 dark:text-red-100">
                Build Failed
              </p>
              <p className="text-red-700 dark:text-red-300">
                The container build process encountered an error. Check the logs
                above for details.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
