'use client';

import { ChevronDown, Cookie, Database, HardDrive } from 'lucide-react';
import { useState, useSyncExternalStore } from 'react';

type StorageEntry = {
  key: string;
  value: string;
};

type BrowserStorageSnapshot = {
  cookies: StorageEntry[];
  localStorage: StorageEntry[];
  sessionStorage: StorageEntry[];
};

const EMPTY_SNAPSHOT: BrowserStorageSnapshot = {
  cookies: [],
  localStorage: [],
  sessionStorage: []
};

let snapshot = EMPTY_SNAPSHOT;
const listeners = new Set<() => void>();

function readStorage(storage: Storage): StorageEntry[] {
  return Array.from({ length: storage.length }, (_, index) => {
    const key = storage.key(index) ?? '';
    return { key, value: storage.getItem(key) ?? '' };
  }).sort((a, b) => a.key.localeCompare(b.key));
}

function readCookies(): StorageEntry[] {
  if (!document.cookie) return [];

  return document.cookie
    .split(';')
    .map((cookie) => {
      const separatorIndex = cookie.indexOf('=');
      const key = cookie.slice(0, separatorIndex).trim();
      const value = cookie.slice(separatorIndex + 1);
      return { key, value };
    })
    .sort((a, b) => a.key.localeCompare(b.key));
}

function refreshSnapshot() {
  snapshot = {
    cookies: readCookies(),
    localStorage: readStorage(window.localStorage),
    sessionStorage: readStorage(window.sessionStorage)
  };
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);

  if (listeners.size === 1) {
    refreshSnapshot();
  } else {
    listener();
  }

  window.addEventListener('storage', refreshSnapshot);

  return () => {
    listeners.delete(listener);
    window.removeEventListener('storage', refreshSnapshot);
  };
}

function getSnapshot() {
  return snapshot;
}

function getServerSnapshot() {
  return EMPTY_SNAPSHOT;
}

const sections = [
  { key: 'localStorage', label: 'Local storage', Icon: HardDrive },
  { key: 'sessionStorage', label: 'Session storage', Icon: Database },
  { key: 'cookies', label: 'Cookies', Icon: Cookie }
] as const;

function StorageTable({ entries }: { entries: StorageEntry[] }) {
  if (entries.length === 0) {
    return (
      <p className="px-4 py-6 text-center text-sm text-slate-500 dark:text-slate-400">
        No accessible entries.
      </p>
    );
  }

  return (
    <div className="max-h-80 overflow-auto">
      <table className="w-full table-fixed text-left text-xs">
        <thead className="sticky top-0 bg-slate-100/95 text-slate-500 backdrop-blur dark:bg-slate-800/95 dark:text-slate-400">
          <tr>
            <th className="w-2/5 px-4 py-2 font-semibold tracking-wide uppercase">
              Key
            </th>
            <th className="px-4 py-2 font-semibold tracking-wide uppercase">
              Value
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200/70 dark:divide-slate-700/70">
          {entries.map(({ key, value }) => (
            <tr key={key} className="align-top">
              <th
                scope="row"
                className="px-4 py-3 font-mono font-medium break-all text-slate-800 dark:text-slate-200"
              >
                {key}
              </th>
              <td className="px-4 py-3 font-mono break-all whitespace-pre-wrap text-slate-600 dark:text-slate-300">
                {value}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function BrowserStorageInspector() {
  const [isExpanded, setIsExpanded] = useState(false);
  const storage = useSyncExternalStore(
    subscribe,
    getSnapshot,
    getServerSnapshot
  );

  return (
    <div className="mt-6 border-t border-slate-200/70 pt-6 dark:border-slate-700/70">
      <button
        type="button"
        aria-expanded={isExpanded}
        aria-controls="browser-storage-details"
        onClick={() => setIsExpanded((expanded) => !expanded)}
        className="focus-visible:ring-primary/45 group -mx-2 flex w-[calc(100%+1rem)] cursor-pointer items-center justify-between gap-4 rounded-xl px-2 py-2 text-left transition-colors hover:bg-slate-50 focus-visible:ring-2 focus-visible:outline-none dark:hover:bg-slate-800/50"
      >
        <span className="min-w-0">
          <span className="block text-base font-semibold text-slate-900 dark:text-slate-100">
            Browser Storage
          </span>
          <span className="mt-1 block max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
            Values available to this page in the current browser tab. HttpOnly
            cookies are intentionally hidden by the browser.
          </span>
        </span>
        <span className="group-hover:border-primary/30 group-hover:text-primary flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 shadow-sm transition-colors dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400">
          <ChevronDown
            className={`h-4 w-4 transition-transform duration-300 motion-reduce:transition-none ${
              isExpanded ? 'rotate-180' : ''
            }`}
            aria-hidden="true"
          />
        </span>
      </button>

      <div
        id="browser-storage-details"
        aria-hidden={!isExpanded}
        className={`grid transition-[grid-template-rows,opacity] duration-300 ease-out motion-reduce:transition-none ${
          isExpanded
            ? 'grid-rows-[1fr] opacity-100'
            : 'grid-rows-[0fr] opacity-0'
        }`}
      >
        <div className="min-h-0 overflow-hidden">
          <div className="mt-5 space-y-4">
            {sections.map(({ key, label, Icon }) => {
              const entries = storage[key];

              return (
                <section
                  key={key}
                  className="min-w-0 overflow-hidden rounded-xl border border-slate-200/70 bg-slate-50/70 dark:border-slate-700/70 dark:bg-slate-900/45"
                >
                  <div className="flex items-center justify-between border-b border-slate-200/70 px-4 py-3 dark:border-slate-700/70">
                    <h4 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                      <Icon
                        className="text-primary h-4 w-4"
                        aria-hidden="true"
                      />
                      {label}
                    </h4>
                    <span className="rounded-full bg-slate-200/80 px-2 py-0.5 text-xs font-semibold text-slate-600 tabular-nums dark:bg-slate-700 dark:text-slate-300">
                      {entries.length}
                    </span>
                  </div>
                  <StorageTable entries={entries} />
                </section>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
