import { Logo } from '@/components/icons';

export default function Loading() {
  return (
    <div className="relative flex w-full flex-col items-center justify-center p-6 min-h-[calc(100dvh-6rem)] md:min-h-[calc(100dvh-7rem)]">
      <div className="relative flex w-full max-w-xl flex-col items-center justify-center rounded-2xl border border-slate-200/80 bg-[hsl(var(--dashboard-surface))] p-10 text-center shadow-xl dark:border-slate-700/80">
        <div className="mb-8">
          <div className="mb-4 inline-flex h-28 w-28 items-center justify-center rounded-full bg-slate-100 dark:bg-slate-800">
            <Logo width={108} height={108} className="h-20 w-20" />
          </div>
        </div>

        <div className="mb-8">
          <p className="mb-2 text-lg text-slate-700 dark:text-slate-300">
            We&apos;re preparing something special for you.
          </p>
          <p className="text-lg text-slate-600 dark:text-slate-400">
            Please wait while we load the content.
          </p>
        </div>

        <div className="flex justify-center space-x-3">
          <div className="h-3.5 w-3.5 animate-bounce rounded-full bg-slate-700 [animation-delay:0ms] [animation-duration:1.4s] dark:bg-slate-200"></div>
          <div className="h-3.5 w-3.5 animate-bounce rounded-full bg-slate-700 [animation-delay:200ms] [animation-duration:1.4s] dark:bg-slate-200"></div>
          <div className="h-3.5 w-3.5 animate-bounce rounded-full bg-slate-700 [animation-delay:400ms] [animation-duration:1.4s] dark:bg-slate-200"></div>
        </div>
      </div>
    </div>
  );
}
