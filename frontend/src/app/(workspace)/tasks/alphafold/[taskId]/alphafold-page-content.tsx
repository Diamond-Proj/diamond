'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft,
  Download,
  ExternalLink,
  Loader2,
  Pause,
  Play,
  RefreshCw,
  RotateCcw
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { isSafePathComponent } from '@/lib/utils';

import {
  Task,
  TaskOutputEntry,
  TaskOutputFilesApiResponse,
  TasksApiResponse
} from '../../tasks.types';
import {
  ColabfoldOutputs,
  ColabfoldScores,
  PLDDT_BANDS,
  formatScore,
  mean,
  modelLabel,
  modelPdbFile,
  parseColabfoldOutputs,
  parsePdbResidues,
  plddtBand
} from '../colabfold-outputs';
import { PaeHeatmap } from '../components/pae-heatmap';
import { PlddtChart } from '../components/plddt-chart';
import {
  StructureColorMode,
  StructureStyle,
  StructureViewer
} from '../components/structure-viewer';

interface AlphafoldPageContentProps {
  taskId: string;
}

const TERMINAL_STATES = new Set(['COMPLETED', 'FAILED']);
// Mirrors the backend's per-file read cap (Globus Compute payload limit).
const MAX_FILE_BYTES = 5 * 1024 * 1024;

const STYLE_OPTIONS: { value: StructureStyle; label: string }[] = [
  { value: 'cartoon', label: 'Cartoon' },
  { value: 'stick', label: 'Sticks' },
  { value: 'sphere', label: 'Spheres' }
];
const COLOR_OPTIONS: { value: StructureColorMode; label: string }[] = [
  { value: 'plddt', label: 'pLDDT confidence' },
  { value: 'chain', label: 'Chain' },
  { value: 'rainbow', label: 'N → C rainbow' }
];
const PLOT_LABELS: { key: keyof ColabfoldOutputs['plots']; label: string }[] = [
  { key: 'coverage', label: 'MSA coverage' },
  { key: 'plddt', label: 'pLDDT per model' },
  { key: 'pae', label: 'PAE per model' }
];

function outputFileUrl(taskId: string, filename: string, download = false) {
  const params = new URLSearchParams({ task_id: taskId, filename });
  if (download) params.set('download', '1');
  return `/api/task_output_file?${params.toString()}`;
}

async function readErrorMessage(response: Response, fallback: string) {
  try {
    const data = await response.json();
    if (data?.error) return String(data.error);
  } catch {
    // Non-JSON body (gateway/proxy error page); keep the fallback.
  }
  return fallback;
}

async function fetchOutputText(taskId: string, filename: string) {
  const response = await fetch(outputFileUrl(taskId, filename), {
    credentials: 'include'
  });
  if (!response.ok) {
    throw new Error(
      await readErrorMessage(
        response,
        `Failed to load ${filename} (HTTP ${response.status})`
      )
    );
  }
  return response.text();
}

function formatBytes(size: number | null): string {
  if (size === null || Number.isNaN(size)) return '';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function StatTile({
  label,
  value,
  hint
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/55">
      <span className="text-xs font-semibold tracking-wide text-slate-500 uppercase dark:text-slate-400">
        {label}
      </span>
      <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">
        {value}
      </p>
      {hint && (
        <p className="text-xs text-slate-500 dark:text-slate-400">{hint}</p>
      )}
    </div>
  );
}

export function AlphafoldPageContent({ taskId }: AlphafoldPageContentProps) {
  const [task, setTask] = useState<Task | null>(null);
  const [taskError, setTaskError] = useState<string | null>(null);
  const [loadingTask, setLoadingTask] = useState(true);

  const [entries, setEntries] = useState<TaskOutputEntry[]>([]);
  const [outputs, setOutputs] = useState<ColabfoldOutputs | null>(null);
  const [filesError, setFilesError] = useState<string | null>(null);
  const [filesLoading, setFilesLoading] = useState(false);

  const [selectedRank, setSelectedRank] = useState<number | null>(null);
  const [pdbText, setPdbText] = useState<string | null>(null);
  const [scores, setScores] = useState<ColabfoldScores | null>(null);
  const [scoresNote, setScoresNote] = useState<string | null>(null);
  const [modelError, setModelError] = useState<string | null>(null);
  const [modelLoading, setModelLoading] = useState(false);

  const [style, setStyle] = useState<StructureStyle>('cartoon');
  const [colorMode, setColorMode] = useState<StructureColorMode>('plddt');
  const [spin, setSpin] = useState(false);
  const [resetToken, setResetToken] = useState(0);

  const taskStatus = task?.status ?? null;
  const artifactPath = task?.artifact_path ?? null;
  const isAlphafoldTask = task?.task_type === 'alphafold';

  const fetchTask = useCallback(async () => {
    try {
      const response = await fetch('/api/get_task_status', {
        method: 'GET',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' }
      });
      if (!response.ok) {
        throw new Error('Failed to fetch task status');
      }
      const data: TasksApiResponse = await response.json();
      const currentTask = data[taskId] ?? null;
      if (!currentTask) {
        setTask(null);
        setTaskError(`Task ${taskId} was not found.`);
        return;
      }
      setTask(currentTask);
      setTaskError(null);
    } catch (error) {
      console.error('Error loading AlphaFold task:', error);
      setTaskError('Failed to load task status.');
    } finally {
      setLoadingTask(false);
    }
  }, [taskId]);

  const fetchOutputFiles = useCallback(async () => {
    setFilesLoading(true);
    setFilesError(null);
    try {
      const params = new URLSearchParams({ task_id: taskId });
      const response = await fetch(
        `/api/task_output_files?${params.toString()}`,
        { credentials: 'include' }
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
      const nextEntries = data.entries ?? [];
      setEntries(nextEntries);
      setOutputs(parseColabfoldOutputs(nextEntries));
    } catch (error) {
      setFilesError(
        error instanceof Error ? error.message : 'Failed to load output files'
      );
    } finally {
      setFilesLoading(false);
    }
  }, [taskId]);

  // Poll while the job is queued or running; stop once it is terminal.
  useEffect(() => {
    fetchTask();
    if (taskStatus && TERMINAL_STATES.has(taskStatus)) return;
    const interval = setInterval(fetchTask, 10000);
    return () => clearInterval(interval);
  }, [fetchTask, taskStatus]);

  // List the output directory once known, and again on every status change so
  // models written by a running job show up without a manual refresh.
  useEffect(() => {
    if (!artifactPath || !isAlphafoldTask) return;
    fetchOutputFiles();
  }, [artifactPath, isAlphafoldTask, taskStatus, fetchOutputFiles]);

  // Default to the top-ranked model once the listing arrives.
  useEffect(() => {
    if (!outputs || outputs.models.length === 0) return;
    if (
      selectedRank === null ||
      !outputs.models.some((model) => model.rank === selectedRank)
    ) {
      setSelectedRank(outputs.models[0].rank);
    }
  }, [outputs, selectedRank]);

  const selectedModel =
    outputs?.models.find((model) => model.rank === selectedRank) ?? null;
  const selectedPdbFile = selectedModel ? modelPdbFile(selectedModel) : null;
  const selectedScoresFile = selectedModel?.scoresJson ?? null;
  const scoresEntrySize =
    entries.find((entry) => entry.name === selectedScoresFile)?.size ?? null;

  // Load the PDB (and the scores JSON when it fits the download cap).
  useEffect(() => {
    if (!selectedPdbFile) {
      setPdbText(null);
      setScores(null);
      return;
    }
    let active = true;
    setModelLoading(true);
    setModelError(null);
    setScoresNote(null);

    (async () => {
      try {
        const pdb = await fetchOutputText(taskId, selectedPdbFile);
        if (!active) return;
        setPdbText(pdb);
      } catch (error) {
        if (!active) return;
        setPdbText(null);
        setModelError(
          error instanceof Error ? error.message : 'Failed to load the model'
        );
      }

      if (!selectedScoresFile) {
        if (active) setScores(null);
      } else if (scoresEntrySize !== null && scoresEntrySize > MAX_FILE_BYTES) {
        if (active) {
          setScores(null);
          setScoresNote(
            'The scores file exceeds the 5MB download limit: pLDDT is read from the PDB B-factors and the PAE heatmap is unavailable.'
          );
        }
      } else {
        try {
          const text = await fetchOutputText(taskId, selectedScoresFile);
          if (!active) return;
          setScores(JSON.parse(text) as ColabfoldScores);
        } catch (error) {
          if (!active) return;
          setScores(null);
          setScoresNote(
            error instanceof Error
              ? error.message
              : 'Failed to load the scores file'
          );
        }
      }
      if (active) setModelLoading(false);
    })();

    return () => {
      active = false;
    };
  }, [taskId, selectedPdbFile, selectedScoresFile, scoresEntrySize]);

  const residues = useMemo(
    () => (pdbText ? parsePdbResidues(pdbText) : null),
    [pdbText]
  );
  const plddt = scores?.plddt ?? residues?.plddt ?? [];
  const meanPlddt = mean(plddt);
  const chainBreaks = residues?.chainBreaks ?? [];
  const isComplex = chainBreaks.length > 0;
  const pae = scores?.pae ?? null;
  const outputFiles = entries.filter((entry) => !entry.is_dir);

  const handleRefresh = () => {
    fetchTask();
    if (artifactPath) fetchOutputFiles();
  };

  return (
    <div className="space-y-6">
      <section className="dashboard-card relative overflow-hidden p-5 md:p-6">
        <div className="pointer-events-none absolute -top-14 -right-10 h-36 w-36 rounded-full bg-sky-400/8 blur-2xl" />
        <div className="bg-primary/5 pointer-events-none absolute -bottom-10 -left-8 h-32 w-32 rounded-full blur-2xl" />

        <div className="relative z-10 flex flex-wrap items-start justify-between gap-3">
          <div>
            <Link
              href="/tasks"
              className="mb-2 inline-flex items-center gap-1 text-sm text-slate-600 underline-offset-4 hover:underline dark:text-slate-300"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Tasks
            </Link>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              AlphaFold Structure Viewer
            </h1>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              {task?.task_name ? `${task.task_name} · ` : ''}Task ID:{' '}
              <span className="font-mono">{taskId}</span>
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={handleRefresh}
              className="cursor-pointer"
            >
              <RefreshCw
                className={`mr-1 h-3.5 w-3.5 ${filesLoading ? 'animate-spin' : ''}`}
              />
              Refresh
            </Button>
            {selectedPdbFile && (
              <Button asChild variant="outline" className="cursor-pointer">
                <a href={outputFileUrl(taskId, selectedPdbFile, true)}>
                  <Download className="mr-1 h-3.5 w-3.5" />
                  Download PDB
                </a>
              </Button>
            )}
          </div>
        </div>
      </section>

      <section className="dashboard-card p-5 md:p-6">
        {loadingTask ? (
          <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading task status...
          </div>
        ) : taskError ? (
          <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-200">
            {taskError}
          </p>
        ) : !task ? (
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Task not found.
          </p>
        ) : !isAlphafoldTask ? (
          <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
            This task is not an AlphaFold task. Launch one with the
            &quot;AlphaFold Structure Prediction&quot; template.
          </p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-3 xl:grid-cols-6">
              <StatTile label="Task Status" value={task.status} />
              <StatTile
                label="Mean pLDDT"
                value={formatScore(meanPlddt, 1)}
                hint={
                  meanPlddt !== null ? plddtBand(meanPlddt).label : undefined
                }
              />
              <StatTile label="pTM" value={formatScore(scores?.ptm)} />
              <StatTile
                label="ipTM"
                value={formatScore(scores?.iptm)}
                hint={isComplex ? 'interface confidence' : 'complexes only'}
              />
              <StatTile
                label="Residues"
                value={plddt.length ? String(plddt.length) : '—'}
                hint={
                  isComplex ? `${chainBreaks.length + 1} chains` : undefined
                }
              />
              <StatTile
                label="Max PAE"
                value={
                  typeof scores?.max_pae === 'number'
                    ? `${formatScore(scores.max_pae, 1)} Å`
                    : '—'
                }
              />
            </div>

            {outputs && outputs.models.length > 0 && (
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold tracking-wide text-slate-500 uppercase dark:text-slate-400">
                  Model
                </span>
                {outputs.models.map((model) => {
                  const active = model.rank === selectedRank;
                  return (
                    <button
                      key={model.rank}
                      type="button"
                      aria-pressed={active}
                      title={modelLabel(model)}
                      onClick={() => setSelectedRank(model.rank)}
                      className={`cursor-pointer rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                        active
                          ? 'border-sky-300 bg-sky-50 text-sky-800 dark:border-sky-700 dark:bg-sky-950/40 dark:text-sky-100'
                          : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-200 dark:hover:border-slate-600'
                      }`}
                    >
                      Rank {model.rank}
                      {model.relaxedPdb && (
                        <span className="ml-1 opacity-70">· relaxed</span>
                      )}
                    </button>
                  );
                })}
                {selectedModel && (
                  <span className="font-mono text-xs text-slate-500 dark:text-slate-400">
                    {modelLabel(selectedModel)}
                  </span>
                )}
                {outputs.jobNames.length > 1 && (
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    Showing query &quot;{outputs.jobName}&quot; of{' '}
                    {outputs.jobNames.length}; the file list below has all of
                    them.
                  </span>
                )}
              </div>
            )}

            {task.status !== 'COMPLETED' && (
              <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
                Task status is {task.status}.{' '}
                {task.status === 'FAILED'
                  ? 'Check the stderr log on the Tasks page for the ColabFold error.'
                  : 'Models appear here as soon as ColabFold writes them; this page refreshes every 10 seconds.'}
              </p>
            )}
            {filesError && (
              <p className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-200">
                {filesError}
              </p>
            )}
            {!filesError &&
              outputs &&
              outputs.models.length === 0 &&
              !filesLoading && (
                <p className="mt-4 text-sm text-slate-600 dark:text-slate-300">
                  No ranked models in the output directory yet.
                </p>
              )}
          </>
        )}
      </section>

      {task && isAlphafoldTask && (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
          <section className="dashboard-card p-5 md:p-6 xl:col-span-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                3D Structure
              </h2>
              <div className="flex flex-wrap items-center gap-2">
                <label className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300">
                  Style
                  <select
                    value={style}
                    onChange={(event) =>
                      setStyle(event.target.value as StructureStyle)
                    }
                    className="border-input bg-background h-8 rounded-md border px-2 text-xs"
                  >
                    {STYLE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300">
                  Colour
                  <select
                    value={colorMode}
                    onChange={(event) =>
                      setColorMode(event.target.value as StructureColorMode)
                    }
                    className="border-input bg-background h-8 rounded-md border px-2 text-xs"
                  >
                    {COLOR_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  aria-pressed={spin}
                  onClick={() => setSpin((value) => !value)}
                  className="cursor-pointer"
                >
                  {spin ? (
                    <Pause className="mr-1 h-3.5 w-3.5" />
                  ) : (
                    <Play className="mr-1 h-3.5 w-3.5" />
                  )}
                  {spin ? 'Stop spin' : 'Spin'}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => setResetToken((value) => value + 1)}
                  className="cursor-pointer"
                >
                  <RotateCcw className="mr-1 h-3.5 w-3.5" />
                  Reset view
                </Button>
              </div>
            </div>

            <div className="relative mt-3">
              <StructureViewer
                pdbText={pdbText}
                style={style}
                colorMode={colorMode}
                spin={spin}
                resetToken={resetToken}
                className="h-[420px] w-full border border-slate-200/70 bg-slate-50/70 md:h-[520px] dark:border-slate-700/70 dark:bg-slate-900/50"
              />
              {modelLoading && (
                <div className="absolute top-3 left-3 inline-flex items-center gap-2 rounded-md border border-slate-200/70 bg-[hsl(var(--dashboard-surface))] px-3 py-1.5 text-xs text-slate-700 dark:border-slate-700/70 dark:text-slate-200">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Loading model from the cluster...
                </div>
              )}
            </div>
            {modelError && (
              <p className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-200">
                {modelError}
              </p>
            )}
            {colorMode === 'plddt' && (
              <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600 dark:text-slate-300">
                {PLDDT_BANDS.map((band) => (
                  <li key={band.key} className="flex items-center gap-1.5">
                    <span
                      aria-hidden
                      className="inline-block h-2.5 w-2.5 rounded-sm"
                      style={{ backgroundColor: band.color }}
                    />
                    <span className="font-medium text-slate-700 dark:text-slate-200">
                      {band.label}
                    </span>
                    <span>{band.range}</span>
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              Drag to rotate, scroll to zoom, right-drag to pan.
            </p>
          </section>

          <div className="space-y-6 xl:col-span-2">
            <section className="dashboard-card p-5 md:p-6">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                Per-residue pLDDT
              </h2>
              <p className="mt-1 mb-3 text-xs text-slate-500 dark:text-slate-400">
                Local confidence of the selected model (0–100).
                {scores?.plddt
                  ? ' From the ColabFold scores file.'
                  : residues
                    ? ' From the PDB B-factor column.'
                    : ''}
              </p>
              <PlddtChart
                plddt={plddt}
                chainBreaks={chainBreaks}
                residueLabels={residues?.residueLabels}
              />
            </section>

            <section className="dashboard-card p-5 md:p-6">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                Predicted Aligned Error
              </h2>
              <p className="mt-1 mb-3 text-xs text-slate-500 dark:text-slate-400">
                Expected position error of each residue (columns) when the
                prediction is aligned on another residue (rows). Dark blocks are
                rigid, well-defined regions; light off-diagonal regions mean
                uncertain relative placement.
              </p>
              {scoresNote && (
                <p className="mb-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
                  {scoresNote}
                </p>
              )}
              {pae ? (
                <PaeHeatmap
                  pae={pae}
                  maxPae={scores?.max_pae}
                  chainBreaks={chainBreaks}
                />
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {modelLoading
                    ? 'Loading scores...'
                    : 'No predicted aligned error available for this model.'}
                </p>
              )}
            </section>
          </div>
        </div>
      )}

      {task && isAlphafoldTask && (
        <section className="dashboard-card p-5 md:p-6">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            ColabFold Output
          </h2>
          <p className="mt-1 text-xs break-all text-slate-500 dark:text-slate-400">
            {artifactPath}
          </p>

          {outputs &&
            PLOT_LABELS.some(({ key }) => outputs.plots[key] !== null) && (
              <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
                {PLOT_LABELS.map(({ key, label }) => {
                  const file = outputs.plots[key];
                  if (!file) return null;
                  const url = outputFileUrl(taskId, file);
                  return (
                    <figure
                      key={key}
                      className="rounded-lg border border-slate-200/70 bg-white p-2 dark:border-slate-700/70 dark:bg-slate-900/50"
                    >
                      <a href={url} target="_blank" rel="noopener noreferrer">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={url}
                          alt={label}
                          loading="lazy"
                          className="w-full rounded-md bg-white"
                        />
                      </a>
                      <figcaption className="mt-2 flex items-center justify-between text-xs text-slate-600 dark:text-slate-300">
                        <span>{label}</span>
                        <a
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 font-medium text-sky-700 hover:underline dark:text-sky-300"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                          Open
                        </a>
                      </figcaption>
                    </figure>
                  );
                })}
              </div>
            )}

          <div className="mt-4">
            <span className="text-xs font-medium tracking-wide text-slate-500 uppercase dark:text-slate-400">
              Files
            </span>
            {filesLoading && outputFiles.length === 0 ? (
              <div className="mt-2 flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading files from the cluster...
              </div>
            ) : outputFiles.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                No files in the output directory yet.
              </p>
            ) : (
              <ul className="mt-2 divide-y divide-slate-200/70 dark:divide-slate-700/70">
                {outputFiles.map((entry) => {
                  const blocked = !isSafePathComponent(entry.name)
                    ? 'name contains unsupported characters'
                    : entry.size !== null && entry.size > MAX_FILE_BYTES
                      ? 'exceeds the 5MB download limit'
                      : null;
                  return (
                    <li
                      key={entry.name}
                      className="flex items-center justify-between gap-3 py-1.5"
                    >
                      <span
                        className="min-w-0 flex-1 truncate font-mono text-sm text-slate-900 dark:text-slate-100"
                        title={entry.name}
                      >
                        {entry.name}
                      </span>
                      <span className="shrink-0 text-xs text-slate-500 dark:text-slate-400">
                        {formatBytes(entry.size)}
                      </span>
                      {blocked ? (
                        <span className="shrink-0 text-xs text-slate-400 italic dark:text-slate-500">
                          {blocked}
                        </span>
                      ) : (
                        <a
                          href={outputFileUrl(taskId, entry.name, true)}
                          className="flex shrink-0 items-center gap-1 text-xs font-medium text-slate-700 hover:underline dark:text-slate-300"
                        >
                          <Download className="h-3.5 w-3.5" />
                          Download
                        </a>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
