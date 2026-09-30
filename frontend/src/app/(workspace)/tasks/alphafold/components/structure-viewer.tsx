'use client';

import { useEffect, useRef, useState } from 'react';
import type { GLViewer } from '3dmol';

import { cn } from '@/lib/utils';

import { plddtColor } from '../colabfold-outputs';

export type StructureStyle = 'cartoon' | 'stick' | 'sphere';
export type StructureColorMode = 'plddt' | 'chain' | 'rainbow';

type StyleSpec = Parameters<GLViewer['setStyle']>[0];
type AtomLike = { b?: number; chain?: string; resi?: number | string };

/** Position of every residue along the chain(s), for N → C rainbow colouring. */
interface ResidueOrder {
  rank: Map<string, number>;
  count: number;
}

function residueKey(atom: AtomLike) {
  return `${atom.chain ?? ''}:${atom.resi ?? ''}`;
}

function hslToHex(hue: number, saturation: number, lightness: number) {
  const chroma = (1 - Math.abs(2 * lightness - 1)) * saturation;
  const x = chroma * (1 - Math.abs(((hue / 60) % 2) - 1));
  const m = lightness - chroma / 2;
  const [r, g, b] =
    hue < 60
      ? [chroma, x, 0]
      : hue < 120
        ? [x, chroma, 0]
        : hue < 180
          ? [0, chroma, x]
          : hue < 240
            ? [0, x, chroma]
            : hue < 300
              ? [x, 0, chroma]
              : [chroma, 0, x];
  const toHex = (value: number) =>
    Math.round((value + m) * 255)
      .toString(16)
      .padStart(2, '0');
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

function rainbowColor(fraction: number) {
  // Blue at the N-terminus through green and yellow to red at the C-terminus.
  return hslToHex(240 * (1 - Math.min(1, Math.max(0, fraction))), 0.85, 0.5);
}

interface StructureViewerProps {
  pdbText: string | null;
  style: StructureStyle;
  colorMode: StructureColorMode;
  spin: boolean;
  /** Bump to re-centre the camera on the model. */
  resetToken: number;
  className?: string;
}

function buildStyle(
  style: StructureStyle,
  colorMode: StructureColorMode,
  order: ResidueOrder
): StyleSpec {
  // AlphaFold PDBs carry the per-residue pLDDT in the B-factor column.
  const color: Record<string, unknown> =
    colorMode === 'plddt'
      ? { colorfunc: (atom: AtomLike) => plddtColor(atom.b ?? 0) }
      : colorMode === 'chain'
        ? { colorscheme: 'chain' }
        : {
            colorfunc: (atom: AtomLike) =>
              rainbowColor(
                (order.rank.get(residueKey(atom)) ?? 0) /
                  Math.max(1, order.count - 1)
              )
          };
  const shape: Record<string, unknown> =
    style === 'stick'
      ? { radius: 0.2 }
      : style === 'sphere'
        ? { scale: 0.3 }
        : {};
  return { [style]: { ...color, ...shape } } as unknown as StyleSpec;
}

export function StructureViewer({
  pdbText,
  style,
  colorMode,
  spin,
  resetToken,
  className
}: StructureViewerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const viewerRef = useRef<GLViewer | null>(null);
  const loadedPdbRef = useRef<string | null>(null);
  const residueOrderRef = useRef<ResidueOrder>({ rank: new Map(), count: 0 });
  const [viewerReady, setViewerReady] = useState(false);
  const [viewerError, setViewerError] = useState<string | null>(null);

  // Create the WebGL viewer once. 3Dmol touches `window` when it loads, so it
  // is imported inside the effect (client only) instead of at module scope.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    let cancelled = false;

    import('3dmol')
      .then((mol) => {
        if (cancelled) return;
        const viewer = mol.createViewer(container, {
          backgroundColor: 'white',
          backgroundAlpha: 0
        });
        if (!viewer) {
          throw new Error('WebGL is not available in this browser.');
        }
        viewerRef.current = viewer;
        setViewerReady(true);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setViewerError(
          error instanceof Error
            ? error.message
            : 'Failed to initialise the 3D viewer.'
        );
      });

    const observer = new ResizeObserver(() => {
      viewerRef.current?.resize();
    });
    observer.observe(container);

    return () => {
      cancelled = true;
      observer.disconnect();
      viewerRef.current?.clear();
      viewerRef.current = null;
      loadedPdbRef.current = null;
      // 3Dmol appends its canvas to the container; drop it so a re-mount
      // (e.g. React strict mode) starts from an empty element.
      container.replaceChildren();
    };
  }, []);

  // Load the model when it changes; only restyle when style/colour change so
  // the camera is not reset on every toggle.
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || !viewerReady) return;
    if (loadedPdbRef.current !== pdbText) {
      viewer.removeAllModels();
      loadedPdbRef.current = pdbText;
      if (pdbText) {
        const model = viewer.addModel(pdbText, 'pdb');
        const rank = new Map<string, number>();
        for (const atom of model.selectedAtoms({}) as AtomLike[]) {
          const key = residueKey(atom);
          if (!rank.has(key)) rank.set(key, rank.size);
        }
        residueOrderRef.current = { rank, count: rank.size };
        viewer.setStyle(
          {},
          buildStyle(style, colorMode, residueOrderRef.current)
        );
        viewer.zoomTo();
      }
    } else if (pdbText) {
      viewer.setStyle(
        {},
        buildStyle(style, colorMode, residueOrderRef.current)
      );
    }
    viewer.render();
  }, [pdbText, style, colorMode, viewerReady]);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || !viewerReady) return;
    viewer.spin(spin ? 'y' : false);
  }, [spin, viewerReady]);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || !viewerReady || !pdbText || resetToken === 0) return;
    viewer.zoomTo();
    viewer.render();
  }, [resetToken, viewerReady, pdbText]);

  return (
    <div className={cn('relative overflow-hidden rounded-xl', className)}>
      <div
        ref={containerRef}
        className="absolute inset-0"
        data-testid="structure-viewer-canvas"
      />
      {viewerError ? (
        <div className="absolute inset-0 flex items-center justify-center p-6 text-center text-sm text-slate-600 dark:text-slate-300">
          {viewerError} Download the PDB file to open it in another viewer.
        </div>
      ) : !pdbText ? (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center text-sm text-slate-500 dark:text-slate-400">
          No model loaded.
        </div>
      ) : null}
    </div>
  );
}
