'use client';

import { useState } from 'react';
import { Bug, Building2, IdCard, LogOut, Mail, Shield } from 'lucide-react';
import { BrowserStorageInspector } from '@/components/profile/browser-storage-inspector';
import { toast } from '@/components/ui/use-toast';
import { useAuthSessionContext } from '@/lib/auth/session-context';
import { setDeveloperMode, useDeveloperMode } from '@/lib/developer-mode';

export default function ProfilePage() {
  const { session } = useAuthSessionContext();
  const isDeveloperMode = useDeveloperMode();
  const [isSigningOut, setIsSigningOut] = useState(false);
  const userInfo = session.userInfo;

  const name = userInfo?.name || 'Not available';
  const email = userInfo?.email || 'Not available';
  const username = userInfo?.username || 'Not available';
  const institution = userInfo?.organization || 'Not available';

  const handleSignOut = async () => {
    setIsSigningOut(true);
    toast({
      title: 'Logged out successfully',
      description: 'You have been logged out of the Diamond service.'
    });
    await new Promise((resolve) => setTimeout(resolve, 350));
    window.location.href = '/logout';
  };

  return (
    <main className="flex flex-1 flex-col gap-6">
      <section className="dashboard-card p-6">
        <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
          Account Details
        </h3>
        <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">
          This information is managed by Globus Auth. To update it, visit your
          Globus profile settings.
        </p>
        <dl className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200/70 bg-slate-50/70 p-4 dark:border-slate-700/70 dark:bg-slate-900/45">
            <dt className="mb-1 flex items-center gap-2 text-xs font-semibold tracking-[0.08em] text-slate-500 uppercase dark:text-slate-400">
              <IdCard className="h-3.5 w-3.5" />
              Full Name
            </dt>
            <dd className="text-sm font-medium text-slate-900 dark:text-slate-100">
              {name}
            </dd>
          </div>

          <div className="rounded-xl border border-slate-200/70 bg-slate-50/70 p-4 dark:border-slate-700/70 dark:bg-slate-900/45">
            <dt className="mb-1 flex items-center gap-2 text-xs font-semibold tracking-[0.08em] text-slate-500 uppercase dark:text-slate-400">
              <Mail className="h-3.5 w-3.5" />
              Email
            </dt>
            <dd className="text-sm font-medium text-slate-900 dark:text-slate-100">
              {email}
            </dd>
          </div>

          <div className="rounded-xl border border-slate-200/70 bg-slate-50/70 p-4 dark:border-slate-700/70 dark:bg-slate-900/45">
            <dt className="mb-1 flex items-center gap-2 text-xs font-semibold tracking-[0.08em] text-slate-500 uppercase dark:text-slate-400">
              <Shield className="h-3.5 w-3.5" />
              Username
            </dt>
            <dd className="text-sm font-medium text-slate-900 dark:text-slate-100">
              {username}
            </dd>
          </div>

          <div className="rounded-xl border border-slate-200/70 bg-slate-50/70 p-4 dark:border-slate-700/70 dark:bg-slate-900/45">
            <dt className="mb-1 flex items-center gap-2 text-xs font-semibold tracking-[0.08em] text-slate-500 uppercase dark:text-slate-400">
              <Building2 className="h-3.5 w-3.5" />
              Institution
            </dt>
            <dd className="text-sm font-medium text-slate-900 dark:text-slate-100">
              {institution}
            </dd>
          </div>
        </dl>

        <div className="mt-6 flex flex-col gap-4 border-t border-slate-200/70 pt-6 sm:flex-row sm:items-center sm:justify-between dark:border-slate-700/70">
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Account access
            </h3>
            <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">
              Sign out of Diamond on this browser.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void handleSignOut()}
            disabled={isSigningOut}
            className="inline-flex h-10 shrink-0 cursor-pointer items-center justify-center gap-2 rounded-lg border border-rose-300 bg-white px-4 text-sm font-semibold text-rose-600 transition-colors hover:border-rose-400 hover:bg-rose-50 focus-visible:ring-2 focus-visible:ring-rose-400/40 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60 dark:border-rose-800 dark:bg-slate-900 dark:text-rose-400 dark:hover:border-rose-700 dark:hover:bg-rose-950/30"
          >
            <LogOut className="h-4 w-4" aria-hidden="true" />
            {isSigningOut ? 'Signing out...' : 'Sign out'}
          </button>
        </div>
      </section>

      <section className="dashboard-card p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <span className="bg-primary/10 text-primary flex h-10 w-10 shrink-0 items-center justify-center rounded-lg">
              <Bug className="h-5 w-5" aria-hidden="true" />
            </span>
            <div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                Developer Mode
              </h3>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
                Show detailed API response errors in this browser. This setting
                is stored locally and does not affect your account.
              </p>
            </div>
          </div>

          <button
            type="button"
            role="switch"
            aria-checked={isDeveloperMode}
            onClick={() => setDeveloperMode(!isDeveloperMode)}
            className={`focus-visible:ring-primary/45 relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none dark:focus-visible:ring-offset-slate-950 ${
              isDeveloperMode
                ? 'border-primary bg-primary'
                : 'border-slate-300 bg-slate-200 dark:border-slate-600 dark:bg-slate-700'
            }`}
          >
            <span className="sr-only">Toggle developer mode</span>
            <span
              aria-hidden="true"
              className={`mt-0.5 block h-5.5 w-5.5 rounded-full bg-white shadow-sm transition-transform ${
                isDeveloperMode ? 'translate-x-5.5' : 'translate-x-0.5'
              }`}
            />
          </button>
        </div>

        {isDeveloperMode ? <BrowserStorageInspector /> : null}
      </section>
    </main>
  );
}
