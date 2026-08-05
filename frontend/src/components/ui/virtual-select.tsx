'use client';

import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check, Search } from 'lucide-react';
import { cn } from '@/lib/utils';

interface VirtualSelectProps {
  options: string[];
  selected?: string;
  onSelect: (value: string) => void;
  placeholder: string;
  allowCustomInput?: boolean;
  searchPlaceholder?: string;
  disabled?: boolean;
  loading?: boolean;
  className?: string;
}

export function VirtualSelect({
  options,
  selected,
  onSelect,
  placeholder,
  allowCustomInput = false,
  searchPlaceholder = 'Search options...',
  disabled = false,
  loading = false,
  className = ''
}: VirtualSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const filteredOptions = options.filter((option) =>
    option.toLowerCase().includes(searchTerm.toLowerCase())
  );
  const trimmedSearchTerm = searchTerm.trim();
  const showCustomInputOption =
    allowCustomInput &&
    trimmedSearchTerm.length > 0 &&
    !options.includes(trimmedSearchTerm);
  const displayOptions = showCustomInputOption
    ? [`Use "${trimmedSearchTerm}"`, ...filteredOptions]
    : filteredOptions;

  useEffect(() => {
    if (isOpen && searchRef.current) {
      searchRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setSearchTerm('');
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex((prev) =>
          prev < displayOptions.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : prev));
        break;
      case 'Enter':
        e.preventDefault();
        if (!displayOptions[highlightedIndex]) return;
        if (showCustomInputOption && highlightedIndex === 0) {
          handleSelect(trimmedSearchTerm);
        } else {
          const optionIndex = showCustomInputOption
            ? highlightedIndex - 1
            : highlightedIndex;
          if (filteredOptions[optionIndex]) {
            handleSelect(filteredOptions[optionIndex]);
          }
        }
        break;
      case 'Escape':
        setIsOpen(false);
        setSearchTerm('');
        break;
    }
  };

  const handleSelect = (option: string) => {
    onSelect(option);
    setIsOpen(false);
    setSearchTerm('');
  };

  if (loading) {
    return (
      <div className="relative">
        <div
          className={cn(
            'flex h-10 w-full items-center justify-between rounded-lg border border-slate-200/80 bg-white/90 px-3 text-sm text-slate-500 transition-colors dark:border-slate-700/80 dark:bg-slate-900/80 dark:text-slate-400',
            className
          )}
        >
          <span>Loading options...</span>
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-500 dark:border-slate-600 dark:border-t-slate-300" />
        </div>
      </div>
    );
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        className={cn(
          'flex h-10 w-full items-center justify-between rounded-lg border px-3 text-left text-sm transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-rose-500/25',
          disabled
            ? 'cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400 dark:border-slate-700 dark:bg-slate-800/70 dark:text-slate-500'
            : isOpen
              ? 'cursor-pointer border-rose-300/80 bg-white text-slate-900 dark:border-rose-400/40 dark:bg-slate-900 dark:text-slate-100'
              : 'cursor-pointer border-slate-200/80 bg-white/90 text-slate-900 hover:border-slate-300 dark:border-slate-700/80 dark:bg-slate-900/80 dark:text-slate-100 dark:hover:border-slate-600',
          className
        )}
      >
        <span className={cn('truncate', selected ? '' : 'text-slate-500 dark:text-slate-400')}>
          {selected || placeholder}
        </span>
        <ChevronDown
          className={`h-4 w-4 text-slate-400 transition-transform dark:text-slate-500 ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-2 w-full rounded-xl border border-slate-200/80 bg-[hsl(var(--dashboard-surface))] p-1.5 shadow-lg shadow-slate-900/10 dark:border-slate-700/80 dark:shadow-black/35">
          <div className="border-b border-slate-200/70 px-1.5 pb-2 dark:border-slate-700/70">
            <div className="relative">
              <Search className="absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-slate-400 dark:text-slate-500" />
              <input
                ref={searchRef}
                type="text"
                aria-label="Search options"
                placeholder={searchPlaceholder}
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setHighlightedIndex(0);
                }}
                onKeyDown={handleKeyDown}
                className="h-9 w-full rounded-lg border border-slate-200/80 bg-white/80 py-1.5 pr-3 pl-9 text-sm text-slate-700 placeholder:text-slate-400 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-rose-500/25 dark:border-slate-700/80 dark:bg-slate-900/80 dark:text-slate-200 dark:placeholder:text-slate-500"
              />
            </div>
          </div>

          <div className="max-h-60 overflow-y-auto py-1">
            {displayOptions.length === 0 ? (
              <div className="px-4 py-7 text-center text-sm text-slate-500 dark:text-slate-400">
                No options found
              </div>
            ) : (
              <div>
                {displayOptions.map((displayOption, index) => {
                  const isCustomOption = showCustomInputOption && index === 0;
                  const option = isCustomOption
                    ? trimmedSearchTerm
                    : filteredOptions[showCustomInputOption ? index - 1 : index];
                  if (!option) return null;
                  return (
                    <button
                      key={isCustomOption ? `custom-${option}` : option}
                      type="button"
                      onClick={() => handleSelect(option)}
                      onMouseEnter={() => setHighlightedIndex(index)}
                      className={`flex w-full cursor-pointer items-center justify-between rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                        index === highlightedIndex
                          ? 'bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-slate-100'
                          : selected === option
                            ? 'bg-rose-50 text-rose-700 dark:bg-rose-950/20 dark:text-rose-200'
                            : 'text-slate-700 hover:bg-slate-100/80 dark:text-slate-300 dark:hover:bg-slate-800'
                      }`}
                    >
                      <span className="truncate">{displayOption}</span>
                      {!isCustomOption && selected === option && (
                        <Check className="h-4 w-4 shrink-0 text-rose-600 dark:text-rose-300" />
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
