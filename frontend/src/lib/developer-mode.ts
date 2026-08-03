'use client';

import { useSyncExternalStore } from 'react';

export const DEVELOPER_MODE_STORAGE_KEY = 'diamond:developer-mode';

const DEVELOPER_MODE_CHANGE_EVENT = 'diamond:developer-mode-change';

function getDeveloperModeSnapshot() {
  return localStorage.getItem(DEVELOPER_MODE_STORAGE_KEY) === 'true';
}

function getServerSnapshot() {
  return false;
}

function subscribeToDeveloperMode(onStoreChange: () => void) {
  const handleStorage = (event: StorageEvent) => {
    if (event.key === DEVELOPER_MODE_STORAGE_KEY) {
      onStoreChange();
    }
  };
  const handleLocalChange = () => onStoreChange();

  window.addEventListener('storage', handleStorage);
  window.addEventListener(DEVELOPER_MODE_CHANGE_EVENT, handleLocalChange);

  return () => {
    window.removeEventListener('storage', handleStorage);
    window.removeEventListener(DEVELOPER_MODE_CHANGE_EVENT, handleLocalChange);
  };
}

export function setDeveloperMode(enabled: boolean) {
  localStorage.setItem(DEVELOPER_MODE_STORAGE_KEY, String(enabled));
  window.dispatchEvent(new Event(DEVELOPER_MODE_CHANGE_EVENT));
}

export function useDeveloperMode() {
  return useSyncExternalStore(
    subscribeToDeveloperMode,
    getDeveloperModeSnapshot,
    getServerSnapshot
  );
}
