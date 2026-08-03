'use client';

import { FileTextIcon } from '@radix-ui/react-icons';
import Link from 'next/link';
import { Button } from './ui/button';

export function DocsButton() {
  return (
    <Button
      variant="outline"
      size="default"
      asChild
      className="h-10 cursor-pointer rounded-lg border border-slate-300/70 bg-transparent px-4 text-slate-700 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800 dark:hover:text-slate-100"
    >
      <Link
        href="https://docs.diamondhpc.ai"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-2"
      >
        <FileTextIcon className="h-4 w-4" />
        <span className="sr-only">Documentation</span>
        <span className="hidden sm:inline">Docs</span>
      </Link>
    </Button>
  );
}
