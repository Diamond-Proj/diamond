import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Mirrors the backend's SAFE_PATH_COMPONENT_PATTERN: a single path component
// (no separators or traversal) usable as a filename or staging directory. The
// backend re-validates every such name — this is only for early UX feedback.
const SAFE_PATH_COMPONENT_PATTERN = /^[A-Za-z0-9._-]+$/;

export function isSafePathComponent(name: string): boolean {
  return (
    name !== '' &&
    name !== '.' &&
    name !== '..' &&
    SAFE_PATH_COMPONENT_PATTERN.test(name)
  );
}

/** Coerce an arbitrary filename into a safe single path component. */
export function sanitizePathComponent(name: string): string {
  return name.replace(/[^A-Za-z0-9._-]/g, '_');
}
