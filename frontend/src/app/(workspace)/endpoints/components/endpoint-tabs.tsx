'use client';

import { type KeyboardEvent } from 'react';

interface EndpointTabsProps {
  activeTab: 'managed' | 'available';
  onTabChange: (tab: 'managed' | 'available') => void;
}

export function EndpointTabs({ activeTab, onTabChange }: EndpointTabsProps) {
  const tabs: Array<'managed' | 'available'> = ['managed', 'available'];

  const handleTabKeyDown = (
    event: KeyboardEvent<HTMLButtonElement>,
    tab: 'managed' | 'available'
  ) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
      return;
    }

    event.preventDefault();

    if (event.key === 'Home') {
      onTabChange(tabs[0]);
      return;
    }

    if (event.key === 'End') {
      onTabChange(tabs[tabs.length - 1]);
      return;
    }

    const currentIndex = tabs.indexOf(tab);
    const nextIndex =
      event.key === 'ArrowRight'
        ? (currentIndex + 1) % tabs.length
        : (currentIndex - 1 + tabs.length) % tabs.length;
    onTabChange(tabs[nextIndex]);
  };

  return (
    <div className="dashboard-card p-2">
      <div
        className="grid grid-cols-2 gap-2"
        role="tablist"
        aria-label="Endpoint tabs"
      >
        <button
          type="button"
          onClick={() => onTabChange('managed')}
          onKeyDown={(event) => handleTabKeyDown(event, 'managed')}
          role="tab"
          id="endpoint-tab-managed"
          aria-selected={activeTab === 'managed'}
          aria-controls="endpoint-panel-managed"
          tabIndex={activeTab === 'managed' ? 0 : -1}
          className={`cursor-pointer rounded-xl px-4 py-2.5 text-sm font-semibold transition-colors ${
            activeTab === 'managed'
              ? 'bg-sky-600 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-100'
          }`}
        >
          Managed Endpoints
        </button>
        <button
          type="button"
          data-onboarding-target="available-endpoints"
          onClick={() => onTabChange('available')}
          onKeyDown={(event) => handleTabKeyDown(event, 'available')}
          role="tab"
          id="endpoint-tab-available"
          aria-selected={activeTab === 'available'}
          aria-controls="endpoint-panel-available"
          tabIndex={activeTab === 'available' ? 0 : -1}
          className={`cursor-pointer rounded-xl px-4 py-2.5 text-sm font-semibold transition-colors ${
            activeTab === 'available'
              ? 'bg-sky-600 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-100'
          }`}
        >
          Available Endpoints
        </button>
      </div>
    </div>
  );
}
