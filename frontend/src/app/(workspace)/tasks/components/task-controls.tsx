'use client';

import { ChevronDown, Filter, Search } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

interface TaskControlsProps {
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  filter: 'all' | 'completed' | 'pending' | 'running' | 'failed';
  setFilter: (
    filter: 'all' | 'completed' | 'pending' | 'running' | 'failed'
  ) => void;
}

const filterOptions = [
  { value: 'all', label: 'All Status' },
  { value: 'running', label: 'Running' },
  { value: 'pending', label: 'Pending' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' }
] as const;

export function TaskControls({
  searchTerm,
  setSearchTerm,
  filter,
  setFilter
}: TaskControlsProps) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const currentOption = filterOptions.find((option) => option.value === filter);

  return (
    <section className="dashboard-card relative z-20 overflow-visible p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-center">
        <div className="relative w-full md:w-auto">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            aria-label="Search tasks"
            placeholder="Search tasks..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-xl border border-slate-300/75 bg-white/85 py-2.5 pl-10 pr-4 text-slate-900 transition-all placeholder:text-slate-500 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 focus:outline-none md:w-80 dark:border-slate-600 dark:bg-slate-900/55 dark:text-slate-100"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400" />
          <div className="relative" ref={dropdownRef}>
            <button
              type="button"
              onClick={() => setIsDropdownOpen((state) => !state)}
              className="flex min-w-37 cursor-pointer items-center justify-between rounded-xl border border-slate-300/75 bg-white/85 px-4 py-2.5 text-sm text-slate-900 transition-all hover:border-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 focus:outline-none dark:border-slate-600 dark:bg-slate-900/55 dark:text-slate-100"
            >
              <span>{currentOption?.label}</span>
              <ChevronDown
                className={`h-4 w-4 text-slate-400 transition-transform ${
                  isDropdownOpen ? 'rotate-180' : ''
                }`}
              />
            </button>

            {isDropdownOpen && (
              <div className="absolute left-0 top-full z-50 mt-1.5 w-full rounded-xl border border-slate-200 bg-white p-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">
                {filterOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => {
                      setFilter(option.value);
                      setIsDropdownOpen(false);
                    }}
                    className={`w-full cursor-pointer rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                      filter === option.value
                        ? 'bg-sky-100 text-sky-700 dark:bg-sky-900/35 dark:text-sky-300'
                        : 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
