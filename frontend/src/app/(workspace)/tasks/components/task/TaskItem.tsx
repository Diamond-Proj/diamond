'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import {
  Trash2,
  AlertTriangle,
  Loader2,
  Copy,
  Check,
  MessageSquare,
  FolderOpen,
  Download,
  ExternalLink,
  RefreshCw
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { isSafePathComponent } from '@/lib/utils';
import {
  Task,
  TaskOutputEntry,
  TaskOutputFilesApiResponse
} from '../../tasks.types';

const INLINE_IMAGE_EXTENSIONS = /\.(png|jpe?g|gif|webp|bmp)$/i;
// Mirrors the backend's 5MB read cap; entries whose name fails the shared
// safe-name check or exceed this size can never be served, so their links are
// disabled up front.
const MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024;

function outputEntryBlocker(entry: TaskOutputEntry): string | null {
  if (!isSafePathComponent(entry.name)) {
    return 'name contains unsupported characters';
  }
  if (entry.size !== null && entry.size > MAX_DOWNLOAD_BYTES) {
    return 'exceeds the 5MB download limit';
  }
  return null;
}

function formatBytes(size: number | null): string {
  if (size === null || Number.isNaN(size)) return '';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export default function TaskItem({
  task,
  deletingTasks,
  deleteTask,
  getStatusIcon,
  getStatusBadgeColor
}: {
  task: Task;
  deletingTasks: Set<string>;
  deleteTask: (taskId: string) => void;
  getStatusIcon: (status: string) => React.ReactNode;
  getStatusBadgeColor: (status: string) => string;
}) {
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [logViewer, setLogViewer] = useState<{
    type: 'stdout' | 'stderr';
    path: string;
  } | null>(null);
  const [logContent, setLogContent] = useState('');
  const [logLoading, setLogLoading] = useState(false);
  const [logError, setLogError] = useState<string | null>(null);
  const [artifactCopied, setArtifactCopied] = useState(false);
  const [showOutputFiles, setShowOutputFiles] = useState(false);
  const [outputFiles, setOutputFiles] = useState<TaskOutputEntry[] | null>(
    null
  );
  const [outputFilesTruncated, setOutputFilesTruncated] = useState(false);
  const [outputFilesLoading, setOutputFilesLoading] = useState(false);
  const [outputFilesError, setOutputFilesError] = useState<string | null>(null);
  const [downloadingFile, setDownloadingFile] = useState<string | null>(null);
  const logPollingRef = useRef<NodeJS.Timeout | null>(null);
  const isVllmChatTask = task.task_type === 'vllm_chat';
  const isVllmChatReady = Boolean(isVllmChatTask && task.status === 'RUNNING');
  const canBrowseOutputFiles = Boolean(
    task.artifact_path && !isVllmChatTask && task.status === 'COMPLETED'
  );

  const outputFileUrl = (filename: string, download: boolean) => {
    const params = new URLSearchParams({
      task_id: task.task_id,
      filename
    });
    if (download) params.set('download', '1');
    return `/api/task_output_file?${params.toString()}`;
  };

  const fetchOutputFiles = async () => {
    setOutputFilesLoading(true);
    setOutputFilesError(null);
    try {
      const params = new URLSearchParams({ task_id: task.task_id });
      const response = await fetch(
        `/api/task_output_files?${params.toString()}`,
        {
          credentials: 'include'
        }
      );
      let data: TaskOutputFilesApiResponse | null = null;
      try {
        data = await response.json();
      } catch {
        data = null;
      }
      if (!response.ok || !data || data.error) {
        throw new Error(
          data?.error || `Failed to load output files (HTTP ${response.status})`
        );
      }
      setOutputFiles(data.entries ?? []);
      setOutputFilesTruncated(Boolean(data.truncated));
    } catch (error) {
      // Keep outputFiles null so reopening the panel retries automatically.
      setOutputFiles(null);
      setOutputFilesTruncated(false);
      setOutputFilesError(
        error instanceof Error ? error.message : 'Failed to load output files'
      );
    } finally {
      setOutputFilesLoading(false);
    }
  };

  const handleToggleOutputFiles = () => {
    const next = !showOutputFiles;
    setShowOutputFiles(next);
    if (next && outputFiles === null && !outputFilesLoading) {
      fetchOutputFiles();
    }
  };

  const handleDownloadFile = async (entry: TaskOutputEntry) => {
    setDownloadingFile(entry.name);
    setOutputFilesError(null);
    try {
      const response = await fetch(outputFileUrl(entry.name, true), {
        credentials: 'include'
      });
      if (!response.ok) {
        let message = `Failed to download ${entry.name} (HTTP ${response.status})`;
        try {
          const data = await response.json();
          if (data?.error) message = String(data.error);
        } catch {
          // keep the HTTP status message
        }
        throw new Error(message);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = entry.name;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      setOutputFilesError(
        error instanceof Error
          ? error.message
          : `Failed to download ${entry.name}`
      );
    } finally {
      setDownloadingFile(null);
    }
  };

  const handleViewLog = (logType: 'stdout' | 'stderr') => {
    const logPath = logType === 'stdout' ? task.result : task.error;
    if (!logPath) {
      return;
    }

    setLogViewer({ type: logType, path: logPath });
    setLogContent('');
    setLogError(null);
    setLogLoading(true);
  };

  const handleCloseLogViewer = () => {
    if (logPollingRef.current) {
      clearInterval(logPollingRef.current);
      logPollingRef.current = null;
    }
    setLogViewer(null);
    setLogContent('');
    setLogError(null);
    setLogLoading(false);
  };

  const handleDeleteClick = () => {
    setShowConfirmDialog(true);
  };

  const handleConfirmDelete = () => {
    deleteTask(task.task_id);
    setShowConfirmDialog(false);
  };

  const handleCancelDelete = () => {
    setShowConfirmDialog(false);
  };

  const handleCopyArtifactPath = async () => {
    if (!task.artifact_path) {
      return;
    }

    try {
      await navigator.clipboard.writeText(task.artifact_path);
      setArtifactCopied(true);
      setTimeout(() => setArtifactCopied(false), 1500);
    } catch (error) {
      console.error('Failed to copy artifact path:', error);
    }
  };

  useEffect(() => {
    if (!logViewer) {
      if (logPollingRef.current) {
        clearInterval(logPollingRef.current);
        logPollingRef.current = null;
      }
      return;
    }

    let isActive = true;

    const fetchTaskLog = async () => {
      try {
        const params = new URLSearchParams({
          task_id: task.task_id,
          endpoint_id: task.details.endpoint_id,
          log_path: logViewer.path
        });

        const response = await fetch(`/api/get_task_log?${params.toString()}`, {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          throw new Error('Failed to fetch task log');
        }

        const data = await response.json();
        if (!isActive) return;
        setLogContent(data.log_content ?? '');
        setLogError(null);
      } catch (error) {
        if (!isActive) return;
        console.error('Error fetching task log:', error);
        setLogError('Failed to load log content.');
      } finally {
        if (!isActive) return;
        setLogLoading(false);
      }
    };

    fetchTaskLog();
    logPollingRef.current = setInterval(fetchTaskLog, 5000);

    return () => {
      isActive = false;
      if (logPollingRef.current) {
        clearInterval(logPollingRef.current);
        logPollingRef.current = null;
      }
    };
  }, [logViewer, task.details.endpoint_id, task.task_id]);

  return (
    <>
      <div className="group dashboard-card p-6 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            {/* Header */}
            <div className="mb-3 flex items-center gap-3">
              <h3 className="text-xl font-semibold text-slate-900 transition-colors duration-200 group-hover:text-slate-700 dark:text-slate-100 dark:group-hover:text-slate-200">
                {task.task_name}
              </h3>
              <div className="flex items-center gap-2">
                <span
                  className={`flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium ${getStatusBadgeColor(task.status)}`}
                >
                  {getStatusIcon(task.status)}
                  {task.status || 'Unknown'}
                </span>
              </div>
            </div>

            {/* Task Details Grid */}
            <div className="mb-4 grid grid-cols-1 gap-4 text-sm md:grid-cols-3">
              <div className="rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/50">
                <span className="block text-xs font-medium tracking-wide text-slate-500 uppercase dark:text-slate-400">
                  Endpoint
                </span>
                <span
                  className="mt-1 block text-sm font-semibold text-slate-900 dark:text-slate-100"
                  style={{ fontFamily: 'var(--font-mono)' }}
                >
                  {task.details.endpoint_name}
                </span>
              </div>
              <div className="rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/50">
                <span className="block text-xs font-medium tracking-wide text-slate-500 uppercase dark:text-slate-400">
                  Task ID
                </span>
                <span
                  className="mt-1 block text-sm font-semibold text-slate-900 dark:text-slate-100"
                  style={{ fontFamily: 'var(--font-mono)' }}
                >
                  {task.task_id}
                </span>
              </div>
              <div className="rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/50">
                <span className="block text-xs font-medium tracking-wide text-slate-500 uppercase dark:text-slate-400">
                  Created
                </span>
                <span className="mt-1 block text-sm font-semibold text-slate-900 dark:text-slate-100">
                  {new Date(task.details.task_create_time).toLocaleString()}
                </span>
              </div>
            </div>

            {(task.result ||
              task.error ||
              task.artifact_path ||
              isVllmChatTask) && (
              <div className="border-t border-slate-200/70 pt-4 dark:border-slate-700/70">
                <div className="space-y-3">
                  <div className="rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/50">
                    <span className="block text-xs font-medium tracking-wide text-slate-500 uppercase dark:text-slate-400">
                      Stdout Log
                    </span>
                    {task.result ? (
                      <button
                        onClick={() => handleViewLog('stdout')}
                        className="mt-1 block w-full cursor-pointer text-left text-sm break-all text-rose-700 underline underline-offset-4 transition-colors hover:text-rose-600 dark:text-rose-200 dark:hover:text-rose-100"
                        style={{ fontFamily: 'var(--font-mono)' }}
                      >
                        {task.result}
                      </button>
                    ) : (
                      <span className="mt-1 block text-sm text-slate-500 dark:text-slate-400">
                        Not available
                      </span>
                    )}
                  </div>

                  <div className="rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/50">
                    <span className="block text-xs font-medium tracking-wide text-slate-500 uppercase dark:text-slate-400">
                      Stderr Log
                    </span>
                    {task.error ? (
                      <button
                        onClick={() => handleViewLog('stderr')}
                        className="mt-1 block w-full cursor-pointer text-left text-sm break-all text-rose-700 underline underline-offset-4 transition-colors hover:text-rose-600 dark:text-rose-200 dark:hover:text-rose-100"
                        style={{ fontFamily: 'var(--font-mono)' }}
                      >
                        {task.error}
                      </button>
                    ) : (
                      <span className="mt-1 block text-sm text-slate-500 dark:text-slate-400">
                        Not available
                      </span>
                    )}
                  </div>

                  {isVllmChatTask && (
                    <div className="rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/50">
                      <span className="block text-xs font-medium tracking-wide text-slate-500 uppercase dark:text-slate-400">
                        Chat Service
                      </span>
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        {typeof task.chat?.port === 'number' && (
                          <span className="rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 text-xs font-medium text-sky-700 dark:border-sky-800/70 dark:bg-sky-950/30 dark:text-sky-200">
                            vLLM Port {task.chat.port}
                          </span>
                        )}
                        <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-200">
                          Model {task.chat?.model || 'diamond-assistant'}
                        </span>
                        {isVllmChatReady ? (
                          <Button size="sm" asChild className="cursor-pointer">
                            <Link
                              href={`/tasks/vllm-chat/${encodeURIComponent(task.task_id)}`}
                            >
                              <MessageSquare className="mr-1 h-3.5 w-3.5" />
                              Open Chat
                            </Link>
                          </Button>
                        ) : (
                          <Button size="sm" variant="secondary" disabled>
                            <Loader2 className="mr-1 h-3.5 w-3.5" />
                            Waiting For RUNNING
                          </Button>
                        )}
                      </div>
                    </div>
                  )}

                  {task.artifact_path && !isVllmChatTask && (
                    <div className="rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/50">
                      <span className="block text-xs font-medium tracking-wide text-slate-500 uppercase dark:text-slate-400">
                        Artifact Path
                      </span>
                      <div className="mt-1 flex items-start gap-3">
                        <span
                          className="flex-1 text-sm font-semibold break-all text-slate-900 dark:text-slate-100"
                          style={{ fontFamily: 'var(--font-mono)' }}
                        >
                          {task.artifact_path}
                        </span>
                        <div className="flex shrink-0 items-center gap-2">
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            className="cursor-pointer"
                            onClick={handleCopyArtifactPath}
                          >
                            {artifactCopied ? (
                              <>
                                <Check className="mr-1 h-3.5 w-3.5" />
                                Copied
                              </>
                            ) : (
                              <>
                                <Copy className="mr-1 h-3.5 w-3.5" />
                                Copy
                              </>
                            )}
                          </Button>
                          {canBrowseOutputFiles && (
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              className="cursor-pointer"
                              onClick={handleToggleOutputFiles}
                            >
                              <FolderOpen className="mr-1 h-3.5 w-3.5" />
                              {showOutputFiles ? 'Hide Files' : 'Browse Files'}
                            </Button>
                          )}
                        </div>
                      </div>

                      {canBrowseOutputFiles && showOutputFiles && (
                        <div className="mt-3 rounded-lg border border-slate-200/70 bg-white p-3 dark:border-slate-700/70 dark:bg-slate-900/50">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-medium tracking-wide text-slate-500 uppercase dark:text-slate-400">
                              Output Files
                            </span>
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              className="cursor-pointer"
                              onClick={fetchOutputFiles}
                              disabled={outputFilesLoading}
                            >
                              <RefreshCw
                                className={`h-3.5 w-3.5 ${outputFilesLoading ? 'animate-spin' : ''}`}
                              />
                            </Button>
                          </div>
                          {outputFilesError && (
                            <p className="mt-2 text-sm text-red-600 dark:text-red-400">
                              {outputFilesError}
                            </p>
                          )}
                          {outputFilesLoading ? (
                            <div className="mt-2 flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
                              <Loader2 className="h-4 w-4 animate-spin" />
                              Loading files from the cluster...
                            </div>
                          ) : outputFiles ===
                            null ? null : outputFiles.length === 0 ? (
                            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                              No files found in the output directory.
                            </p>
                          ) : (
                            <>
                              <ul className="mt-2 divide-y divide-slate-200/70 dark:divide-slate-700/70">
                                {outputFiles.map((entry) => {
                                  const blocker = entry.is_dir
                                    ? null
                                    : outputEntryBlocker(entry);
                                  return (
                                    <li
                                      key={entry.name}
                                      className="flex items-center justify-between gap-3 py-1.5"
                                    >
                                      <span
                                        className="min-w-0 flex-1 truncate text-sm text-slate-900 dark:text-slate-100"
                                        style={{
                                          fontFamily: 'var(--font-mono)'
                                        }}
                                        title={entry.name}
                                      >
                                        {entry.name}
                                        {entry.is_dir ? '/' : ''}
                                      </span>
                                      {!entry.is_dir && (
                                        <>
                                          <span className="shrink-0 text-xs text-slate-500 dark:text-slate-400">
                                            {formatBytes(entry.size)}
                                          </span>
                                          {blocker ? (
                                            <span className="shrink-0 text-xs text-slate-400 italic dark:text-slate-500">
                                              {blocker}
                                            </span>
                                          ) : (
                                            <span className="flex shrink-0 items-center gap-2">
                                              {INLINE_IMAGE_EXTENSIONS.test(
                                                entry.name
                                              ) && (
                                                <a
                                                  href={outputFileUrl(
                                                    entry.name,
                                                    false
                                                  )}
                                                  target="_blank"
                                                  rel="noopener noreferrer"
                                                  className="flex items-center gap-1 text-xs font-medium text-sky-700 hover:underline dark:text-sky-300"
                                                >
                                                  <ExternalLink className="h-3.5 w-3.5" />
                                                  Open
                                                </a>
                                              )}
                                              <button
                                                type="button"
                                                onClick={() =>
                                                  handleDownloadFile(entry)
                                                }
                                                disabled={
                                                  downloadingFile !== null
                                                }
                                                className="flex cursor-pointer items-center gap-1 text-xs font-medium text-slate-700 hover:underline disabled:cursor-default disabled:opacity-50 dark:text-slate-300"
                                              >
                                                {downloadingFile ===
                                                entry.name ? (
                                                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                                ) : (
                                                  <Download className="h-3.5 w-3.5" />
                                                )}
                                                Download
                                              </button>
                                            </span>
                                          )}
                                        </>
                                      )}
                                    </li>
                                  );
                                })}
                              </ul>
                              {outputFilesTruncated && (
                                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                                  Only the first {outputFiles.length} entries
                                  are shown; use the artifact path to access the
                                  rest.
                                </p>
                              )}
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="ml-6">
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDeleteClick}
              disabled={deletingTasks.has(task.task_id)}
              className="flex cursor-pointer items-center gap-2"
            >
              <Trash2 className="h-4 w-4" />
              {deletingTasks.has(task.task_id) ? 'Deleting...' : 'Delete'}
            </Button>
          </div>
        </div>
      </div>

      {logViewer && (
        <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/50 p-4 dark:bg-black/70">
          <div className="w-full max-w-3xl rounded-2xl border border-slate-200/80 bg-[hsl(var(--dashboard-surface))] shadow-xl dark:border-slate-700/80">
            <div className="space-y-4 p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                    {logViewer.type === 'stdout'
                      ? 'Stdout Log Output'
                      : 'Stderr Log Output'}
                  </h3>
                  <p className="mt-1 text-xs break-all text-slate-500 dark:text-slate-400">
                    Path: {logViewer.path}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCloseLogViewer}
                  className="cursor-pointer"
                >
                  Close
                </Button>
              </div>
              <div className="max-h-[60vh] min-h-60 overflow-y-auto rounded-lg border border-slate-200/70 bg-slate-50/70 p-4 dark:border-slate-700/70 dark:bg-slate-800/60">
                {logLoading ? (
                  <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading log...
                  </div>
                ) : logError ? (
                  <p className="text-sm text-red-600 dark:text-red-400">
                    {logError}
                  </p>
                ) : (
                  <pre className="font-mono text-xs wrap-break-word whitespace-pre-wrap text-slate-900 dark:text-slate-100">
                    {logContent || 'Log is empty.'}
                  </pre>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Dialog */}
      {showConfirmDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 dark:bg-black/70">
          <div className="w-full max-w-md rounded-2xl border border-slate-200/80 bg-[hsl(var(--dashboard-surface))] shadow-xl dark:border-slate-700/80">
            <div className="p-6">
              {/* Header */}
              <div className="mb-4 flex items-center gap-3">
                <div className="rounded-full bg-red-100 p-2 dark:bg-red-950/30">
                  <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                  Delete Task
                </h3>
              </div>

              {/* Content */}
              <div className="mb-6">
                <p className="mb-2 text-slate-600 dark:text-slate-400">
                  Are you sure you want to delete this task?
                </p>
                <div className="space-y-2 rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/60">
                  <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                    {task.task_name}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    <span className="font-bold">Task ID:</span>{' '}
                    <span className="font-mono">{task.task_id}</span>
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    <span className="font-bold">Endpoint:</span>{' '}
                    <span className="font-mono">
                      {task.details.endpoint_name}
                    </span>
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    <span className="font-bold">Status:</span>{' '}
                    {task.status || 'Unknown'}
                  </p>
                </div>
                <p className="mt-3 text-sm text-red-600 dark:text-red-400">
                  This action cannot be undone.
                </p>
              </div>

              {/* Actions */}
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
                  Delete Task
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
