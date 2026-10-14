'use client';

import { useEffect, useRef, useState } from 'react';

import { PLDDT_BANDS, plddtBand } from '../colabfold-outputs';

interface PlddtChartProps {
  plddt: number[];
  /** Residue indices at which a new chain starts. */
  chainBreaks?: number[];
  residueLabels?: string[];
  height?: number;
}

const MARGIN = { top: 10, right: 12, bottom: 30, left: 38 };
const Y_TICKS = [0, 50, 70, 90, 100];

function niceStep(count: number): number {
  const target = Math.max(1, count / 6);
  const magnitude = 10 ** Math.floor(Math.log10(target));
  for (const factor of [1, 2, 5, 10]) {
    if (factor * magnitude >= target) return factor * magnitude;
  }
  return 10 * magnitude;
}

export function PlddtChart({
  plddt,
  chainBreaks = [],
  residueLabels,
  height = 220
}: PlddtChartProps) {
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(600);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  useEffect(() => {
    const element = wrapperRef.current;
    if (!element) return;
    const observer = new ResizeObserver((entries) => {
      const nextWidth = entries[0]?.contentRect.width;
      if (nextWidth) setWidth(Math.max(240, Math.floor(nextWidth)));
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const count = plddt.length;
  const plotWidth = Math.max(1, width - MARGIN.left - MARGIN.right);
  const plotHeight = Math.max(1, height - MARGIN.top - MARGIN.bottom);
  const xAt = (index: number) =>
    MARGIN.left +
    (count <= 1 ? plotWidth / 2 : (index / (count - 1)) * plotWidth);
  const yAt = (value: number) =>
    MARGIN.top + (1 - Math.min(100, Math.max(0, value)) / 100) * plotHeight;

  if (count === 0) {
    return (
      <div ref={wrapperRef} className="w-full">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          No per-residue confidence available yet.
        </p>
      </div>
    );
  }

  const linePath = plddt
    .map(
      (value, index) =>
        `${index === 0 ? 'M' : 'L'}${xAt(index).toFixed(1)} ${yAt(value).toFixed(1)}`
    )
    .join(' ');

  const step = niceStep(count);
  const xTicks = [1];
  for (let residue = step; residue <= count; residue += step) {
    if (residue !== 1) xTicks.push(residue);
  }

  const indexFromPointer = (clientX: number, svg: SVGSVGElement) => {
    const rect = svg.getBoundingClientRect();
    const ratio = (clientX - rect.left - MARGIN.left) / plotWidth;
    return Math.min(count - 1, Math.max(0, Math.round(ratio * (count - 1))));
  };

  const moveHover = (delta: number) => {
    setHoverIndex((current) => {
      const base = current ?? 0;
      return Math.min(count - 1, Math.max(0, base + delta));
    });
  };

  const hoverValue = hoverIndex !== null ? plddt[hoverIndex] : null;
  const hoverBand = hoverValue !== null ? plddtBand(hoverValue) : null;
  const tooltipLeft =
    hoverIndex !== null
      ? Math.min(width - 96, Math.max(96, xAt(hoverIndex)))
      : 0;

  return (
    <div ref={wrapperRef} className="relative w-full">
      <svg
        width={width}
        height={height}
        role="img"
        aria-label="Per-residue pLDDT"
        tabIndex={0}
        className="block max-w-full text-slate-700 outline-none select-none focus-visible:ring-2 focus-visible:ring-sky-500/40 dark:text-slate-200"
        onPointerMove={(event) =>
          setHoverIndex(indexFromPointer(event.clientX, event.currentTarget))
        }
        onPointerLeave={() => setHoverIndex(null)}
        onBlur={() => setHoverIndex(null)}
        onKeyDown={(event) => {
          if (event.key === 'ArrowLeft') moveHover(-1);
          else if (event.key === 'ArrowRight') moveHover(1);
          else if (event.key === 'Home') setHoverIndex(0);
          else if (event.key === 'End') setHoverIndex(count - 1);
          else return;
          event.preventDefault();
        }}
      >
        {PLDDT_BANDS.map((band) => (
          <rect
            key={band.key}
            x={MARGIN.left}
            width={plotWidth}
            y={yAt(band.max)}
            height={Math.max(0, yAt(band.min) - yAt(band.max))}
            fill={band.color}
            opacity={0.14}
          />
        ))}

        {Y_TICKS.map((tick) => (
          <g key={tick}>
            <line
              x1={MARGIN.left}
              x2={MARGIN.left + plotWidth}
              y1={yAt(tick)}
              y2={yAt(tick)}
              stroke="currentColor"
              strokeOpacity={tick === 0 ? 0.35 : 0.14}
              strokeDasharray={tick === 0 || tick === 100 ? undefined : '3 3'}
            />
            <text
              x={MARGIN.left - 6}
              y={yAt(tick)}
              textAnchor="end"
              dominantBaseline="middle"
              fontSize={10}
              fill="currentColor"
              fillOpacity={0.7}
            >
              {tick}
            </text>
          </g>
        ))}

        {xTicks.map((residue) => (
          <g key={residue}>
            <line
              x1={xAt(residue - 1)}
              x2={xAt(residue - 1)}
              y1={MARGIN.top + plotHeight}
              y2={MARGIN.top + plotHeight + 4}
              stroke="currentColor"
              strokeOpacity={0.4}
            />
            <text
              x={xAt(residue - 1)}
              y={MARGIN.top + plotHeight + 16}
              textAnchor="middle"
              fontSize={10}
              fill="currentColor"
              fillOpacity={0.7}
            >
              {residue}
            </text>
          </g>
        ))}

        {chainBreaks.map((index) => (
          <line
            key={index}
            x1={xAt(index) - 0.5}
            x2={xAt(index) - 0.5}
            y1={MARGIN.top}
            y2={MARGIN.top + plotHeight}
            stroke="currentColor"
            strokeOpacity={0.5}
            strokeDasharray="4 3"
          />
        ))}

        <path
          d={linePath}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {hoverIndex !== null && hoverValue !== null && hoverBand && (
          <g>
            <line
              x1={xAt(hoverIndex)}
              x2={xAt(hoverIndex)}
              y1={MARGIN.top}
              y2={MARGIN.top + plotHeight}
              stroke="currentColor"
              strokeOpacity={0.45}
            />
            <circle
              cx={xAt(hoverIndex)}
              cy={yAt(hoverValue)}
              r={5}
              fill={hoverBand.color}
              strokeWidth={2}
              style={{ stroke: 'hsl(var(--dashboard-surface))' }}
            />
          </g>
        )}

        <rect
          x={MARGIN.left}
          y={MARGIN.top}
          width={plotWidth}
          height={plotHeight}
          fill="transparent"
        />
      </svg>

      {hoverIndex !== null && hoverValue !== null && hoverBand && (
        <div
          role="status"
          className="pointer-events-none absolute top-1 z-10 -translate-x-1/2 rounded-md border border-slate-200/80 bg-[hsl(var(--dashboard-surface))] px-2.5 py-1.5 text-xs shadow-md dark:border-slate-700/80"
          style={{ left: tooltipLeft }}
        >
          <div className="font-semibold text-slate-900 dark:text-slate-100">
            {hoverValue.toFixed(1)}{' '}
            <span className="font-normal text-slate-500 dark:text-slate-400">
              pLDDT
            </span>
          </div>
          <div className="text-slate-600 dark:text-slate-300">
            Residue {hoverIndex + 1}
            {residueLabels?.[hoverIndex]
              ? ` · ${residueLabels[hoverIndex]}`
              : ''}
          </div>
          <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
            <span
              aria-hidden
              className="inline-block h-2 w-2 rounded-full"
              style={{ backgroundColor: hoverBand.color }}
            />
            {hoverBand.label} ({hoverBand.range})
          </div>
        </div>
      )}

      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600 dark:text-slate-300">
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
    </div>
  );
}
