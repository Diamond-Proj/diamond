'use client';

import { useEffect, useMemo, useRef, useState } from 'react';

interface PaeHeatmapProps {
  /** Square matrix: pae[i][j] = expected error (Å) of residue j when aligned on i. */
  pae: number[][];
  maxPae?: number;
  /** Residue indices at which a new chain starts. */
  chainBreaks?: number[];
}

// Single-hue sequential ramp (blue 700 → 100). Low expected error is dark, as
// in the AlphaFold DB PAE plots; the colour bar states the direction.
const RAMP: [number, number, number][] = [
  [13, 54, 107],
  [28, 92, 171],
  [57, 135, 229],
  [134, 182, 239],
  [205, 226, 251]
];
const RAMP_CSS = `linear-gradient(to right, ${RAMP.map(
  ([r, g, b]) => `rgb(${r} ${g} ${b})`
).join(', ')})`;

function rampColor(t: number): [number, number, number] {
  const clamped = Math.min(1, Math.max(0, t));
  const scaled = clamped * (RAMP.length - 1);
  const index = Math.min(RAMP.length - 2, Math.floor(scaled));
  const fraction = scaled - index;
  const from = RAMP[index];
  const to = RAMP[index + 1];
  return [
    Math.round(from[0] + (to[0] - from[0]) * fraction),
    Math.round(from[1] + (to[1] - from[1]) * fraction),
    Math.round(from[2] + (to[2] - from[2]) * fraction)
  ];
}

const LUT: [number, number, number][] = Array.from({ length: 256 }, (_, i) =>
  rampColor(i / 255)
);

export function PaeHeatmap({ pae, maxPae, chainBreaks = [] }: PaeHeatmapProps) {
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [size, setSize] = useState(360);
  const [hover, setHover] = useState<{ i: number; j: number } | null>(null);
  const count = pae.length;

  // Upper end of the colour scale: ColabFold's max_pae when present, else the
  // largest value in the matrix.
  const scaleMax = useMemo(() => {
    let max = maxPae ?? 0;
    if (!(max > 0)) {
      for (const row of pae)
        for (const value of row) if (value > max) max = value;
    }
    return max > 0 ? max : 1;
  }, [pae, maxPae]);

  useEffect(() => {
    const element = wrapperRef.current;
    if (!element) return;
    const observer = new ResizeObserver((entries) => {
      const nextWidth = entries[0]?.contentRect.width;
      if (nextWidth)
        setSize(Math.min(440, Math.max(200, Math.floor(nextWidth))));
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || count === 0) return;
    const max = scaleMax;

    const offscreen = document.createElement('canvas');
    offscreen.width = count;
    offscreen.height = count;
    const offscreenContext = offscreen.getContext('2d');
    if (!offscreenContext) return;
    const image = offscreenContext.createImageData(count, count);
    const data = image.data;
    for (let i = 0; i < count; i += 1) {
      const row = pae[i] ?? [];
      for (let j = 0; j < count; j += 1) {
        const value = row[j] ?? max;
        const [r, g, b] =
          LUT[Math.round(Math.min(1, Math.max(0, value / max)) * 255)];
        const offset = (i * count + j) * 4;
        data[offset] = r;
        data[offset + 1] = g;
        data[offset + 2] = b;
        data[offset + 3] = 255;
      }
    }
    offscreenContext.putImageData(image, 0, 0);

    const context = canvas.getContext('2d');
    if (!context) return;
    canvas.width = size;
    canvas.height = size;
    context.imageSmoothingEnabled = false;
    context.clearRect(0, 0, size, size);
    context.drawImage(offscreen, 0, 0, size, size);
  }, [pae, scaleMax, count, size]);

  if (count === 0) {
    return (
      <div ref={wrapperRef} className="w-full">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          No predicted aligned error available for this model.
        </p>
      </div>
    );
  }

  const cellAt = (
    clientX: number,
    clientY: number,
    canvas: HTMLCanvasElement
  ) => {
    const rect = canvas.getBoundingClientRect();
    const j = Math.floor(((clientX - rect.left) / rect.width) * count);
    const i = Math.floor(((clientY - rect.top) / rect.height) * count);
    return {
      i: Math.min(count - 1, Math.max(0, i)),
      j: Math.min(count - 1, Math.max(0, j))
    };
  };

  const hoverValue = hover ? (pae[hover.i]?.[hover.j] ?? null) : null;
  const cellSize = size / count;

  return (
    <div ref={wrapperRef} className="w-full">
      <div className="mb-1 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
        <span>Scored residue ↓ (rows) · Aligned residue → (columns)</span>
        <span>{count} residues</span>
      </div>
      <div className="relative" style={{ width: size, height: size }}>
        <canvas
          ref={canvasRef}
          role="img"
          aria-label="Predicted aligned error heatmap"
          className="block rounded-md"
          style={{ width: size, height: size, imageRendering: 'pixelated' }}
          onPointerMove={(event) =>
            setHover(cellAt(event.clientX, event.clientY, event.currentTarget))
          }
          onPointerLeave={() => setHover(null)}
        />
        <svg
          className="pointer-events-none absolute inset-0"
          width={size}
          height={size}
          aria-hidden
        >
          {chainBreaks.map((index) => (
            <g key={index}>
              <line
                x1={index * cellSize}
                x2={index * cellSize}
                y1={0}
                y2={size}
                stroke="white"
                strokeOpacity={0.85}
                strokeDasharray="4 3"
              />
              <line
                x1={0}
                x2={size}
                y1={index * cellSize}
                y2={index * cellSize}
                stroke="white"
                strokeOpacity={0.85}
                strokeDasharray="4 3"
              />
            </g>
          ))}
          {hover && (
            <g>
              <line
                x1={(hover.j + 0.5) * cellSize}
                x2={(hover.j + 0.5) * cellSize}
                y1={0}
                y2={size}
                stroke="white"
                strokeOpacity={0.9}
              />
              <line
                x1={0}
                x2={size}
                y1={(hover.i + 0.5) * cellSize}
                y2={(hover.i + 0.5) * cellSize}
                stroke="white"
                strokeOpacity={0.9}
              />
            </g>
          )}
        </svg>
        {hover && hoverValue !== null && (
          <div
            role="status"
            className="pointer-events-none absolute z-10 rounded-md border border-slate-200/80 bg-[hsl(var(--dashboard-surface))] px-2.5 py-1.5 text-xs shadow-md dark:border-slate-700/80"
            style={{
              left: Math.min(size - 150, (hover.j + 0.5) * cellSize + 10),
              top: Math.max(0, (hover.i + 0.5) * cellSize - 44)
            }}
          >
            <div className="font-semibold text-slate-900 dark:text-slate-100">
              {hoverValue.toFixed(1)}{' '}
              <span className="font-normal text-slate-500 dark:text-slate-400">
                Å
              </span>
            </div>
            <div className="text-slate-600 dark:text-slate-300">
              Scored residue {hover.i + 1} · Aligned residue {hover.j + 1}
            </div>
          </div>
        )}
      </div>
      <div className="mt-3" style={{ width: size }}>
        <div
          className="h-2 rounded-full"
          style={{ backgroundImage: RAMP_CSS }}
          aria-hidden
        />
        <div className="mt-1 flex justify-between text-[11px] text-slate-500 dark:text-slate-400">
          <span>0 Å · confident</span>
          <span>Expected position error</span>
          <span>{scaleMax.toFixed(0)} Å</span>
        </div>
      </div>
    </div>
  );
}
