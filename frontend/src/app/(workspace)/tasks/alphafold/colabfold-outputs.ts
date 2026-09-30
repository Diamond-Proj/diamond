import { TaskOutputEntry } from '../tasks.types';

/**
 * Helpers for reading a ColabFold result directory as listed by
 * /api/task_output_files. File names follow
 *   <job>_(unrelaxed|relaxed)_rank_00N_<model type>_model_M_seed_SSS.pdb
 *   <job>_scores_rank_00N_<model type>_model_M_seed_SSS.json
 *   <job>_plddt.png / <job>_pae.png / <job>_coverage.png / <job>.done.txt
 */

export interface ColabfoldModel {
  rank: number;
  modelType: string;
  modelNumber: number;
  seed: number;
  unrelaxedPdb: string | null;
  relaxedPdb: string | null;
  scoresJson: string | null;
}

export interface ColabfoldOutputs {
  /** Job whose models are exposed (the first one when a FASTA had several queries). */
  jobName: string | null;
  jobNames: string[];
  models: ColabfoldModel[];
  plots: { plddt: string | null; pae: string | null; coverage: string | null };
  done: boolean;
  logFile: string | null;
}

export interface ColabfoldScores {
  plddt?: number[];
  pae?: number[][];
  max_pae?: number;
  ptm?: number;
  iptm?: number;
}

export interface PdbResidueSummary {
  /** One pLDDT per residue (B-factor of the CA atom, or of the first atom seen). */
  plddt: number[];
  chains: string[];
  /** Residue indices at which a new chain starts (never includes 0). */
  chainBreaks: number[];
  residueLabels: string[];
}

const RANKED_FILE_PATTERN =
  /^(.+?)_(unrelaxed|relaxed|scores)_rank_(\d{3})_([a-z0-9_]+?)_model_(\d+)_seed_(\d{3})\.(pdb|json)$/;

export function parseColabfoldOutputs(
  entries: TaskOutputEntry[]
): ColabfoldOutputs {
  const modelsByJob = new Map<string, Map<number, ColabfoldModel>>();
  const plots: ColabfoldOutputs['plots'] = {
    plddt: null,
    pae: null,
    coverage: null
  };
  let done = false;
  let logFile: string | null = null;

  for (const entry of entries) {
    if (entry.is_dir) continue;
    const name = entry.name;
    const match = RANKED_FILE_PATTERN.exec(name);
    if (match) {
      const [, job, kind, rankText, modelType, modelNumberText, seedText] =
        match;
      const rank = parseInt(rankText, 10);
      const byRank = modelsByJob.get(job) ?? new Map<number, ColabfoldModel>();
      const model = byRank.get(rank) ?? {
        rank,
        modelType,
        modelNumber: parseInt(modelNumberText, 10),
        seed: parseInt(seedText, 10),
        unrelaxedPdb: null,
        relaxedPdb: null,
        scoresJson: null
      };
      if (kind === 'unrelaxed') model.unrelaxedPdb = name;
      else if (kind === 'relaxed') model.relaxedPdb = name;
      else model.scoresJson = name;
      byRank.set(rank, model);
      modelsByJob.set(job, byRank);
      continue;
    }
    if (name.endsWith('_plddt.png')) plots.plddt = name;
    else if (name.endsWith('_pae.png')) plots.pae = name;
    else if (name.endsWith('_coverage.png')) plots.coverage = name;
    else if (name.endsWith('.done.txt')) done = true;
    else if (name === 'log.txt') logFile = name;
  }

  const jobNames = [...modelsByJob.keys()].sort();
  const jobName = jobNames[0] ?? null;
  const models = jobName
    ? [...(modelsByJob.get(jobName)?.values() ?? [])].sort(
        (a, b) => a.rank - b.rank
      )
    : [];

  return { jobName, jobNames, models, plots, done, logFile };
}

export function modelPdbFile(model: ColabfoldModel): string | null {
  return model.relaxedPdb ?? model.unrelaxedPdb;
}

export function modelLabel(model: ColabfoldModel): string {
  return `${model.modelType} · model ${model.modelNumber} · seed ${model.seed}`;
}

/** Per-residue pLDDT from the B-factor column of an AlphaFold/ColabFold PDB. */
export function parsePdbResidues(pdbText: string): PdbResidueSummary {
  const plddt: number[] = [];
  const chains: string[] = [];
  const residueLabels: string[] = [];
  let lastKey: string | null = null;

  for (const line of pdbText.split(/\r?\n/)) {
    if (!line.startsWith('ATOM') && !line.startsWith('HETATM')) continue;
    const atomName = line.slice(12, 16).trim();
    const resName = line.slice(17, 20).trim();
    const chain = line.slice(21, 22).trim() || 'A';
    const resSeq = line.slice(22, 27).trim();
    const bFactor = parseFloat(line.slice(60, 66));
    const key = `${chain}:${resSeq}`;
    if (key !== lastKey) {
      plddt.push(Number.isFinite(bFactor) ? bFactor : 0);
      chains.push(chain);
      residueLabels.push(`${resName} ${chain}${resSeq}`);
      lastKey = key;
    } else if (atomName === 'CA' && Number.isFinite(bFactor)) {
      plddt[plddt.length - 1] = bFactor;
    }
  }

  const chainBreaks: number[] = [];
  for (let index = 1; index < chains.length; index += 1) {
    if (chains[index] !== chains[index - 1]) chainBreaks.push(index);
  }
  return { plddt, chains, chainBreaks, residueLabels };
}

/** AlphaFold DB confidence bands and their conventional colours. */
export const PLDDT_BANDS = [
  {
    key: 'very_high',
    label: 'Very high',
    range: 'pLDDT > 90',
    min: 90,
    max: 100,
    color: '#0053d6'
  },
  {
    key: 'confident',
    label: 'Confident',
    range: '70 – 90',
    min: 70,
    max: 90,
    color: '#65cbf3'
  },
  {
    key: 'low',
    label: 'Low',
    range: '50 – 70',
    min: 50,
    max: 70,
    color: '#ffdb13'
  },
  {
    key: 'very_low',
    label: 'Very low',
    range: 'pLDDT < 50',
    min: 0,
    max: 50,
    color: '#ff7d45'
  }
] as const;

export type PlddtBand = (typeof PLDDT_BANDS)[number];

export function plddtBand(value: number): PlddtBand {
  if (value > 90) return PLDDT_BANDS[0];
  if (value > 70) return PLDDT_BANDS[1];
  if (value > 50) return PLDDT_BANDS[2];
  return PLDDT_BANDS[3];
}

export function plddtColor(value: number): string {
  return plddtBand(value).color;
}

export function mean(values: number[]): number | null {
  if (values.length === 0) return null;
  let total = 0;
  for (const value of values) total += value;
  return total / values.length;
}

export function formatScore(value: number | null | undefined, digits = 2) {
  return typeof value === 'number' && Number.isFinite(value)
    ? value.toFixed(digits)
    : '—';
}
