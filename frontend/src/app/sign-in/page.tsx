import { LoginButton } from '@/components/login-button';
import { TokenManagerServer } from '@/lib/auth/tokenManager.server';
import Image from 'next/image';
import { redirect } from 'next/navigation';
import { Cpu, ShieldCheck, Sparkles } from 'lucide-react';

export default async function SignInPage() {
  const tokens = await TokenManagerServer.getTokensFromServerCookies();
  const session = TokenManagerServer.buildSession(tokens);

  // If already authenticated, redirect to the workspace dashboard.
  if (session.isAuthenticated) {
    redirect('/dashboard');
  }

  return (
    <div className="relative flex min-h-screen w-full items-center justify-center px-4 py-10">
      <section className="relative w-full max-w-4xl overflow-hidden rounded-3xl border border-slate-200/80 bg-[hsl(var(--dashboard-surface))] shadow-xl dark:border-slate-700/80">
        <div className="grid md:grid-cols-[1.1fr_0.9fr]">
          <div className="border-b border-slate-200/70 p-8 md:border-b-0 md:border-r md:p-10 dark:border-slate-700/70">
            <div className="inline-flex items-center gap-2 rounded-full border border-slate-200/80 bg-slate-50/80 px-3 py-1 text-xs font-semibold tracking-wide text-slate-700 dark:border-slate-700/80 dark:bg-slate-800/60 dark:text-slate-200">
              <Sparkles className="h-3.5 w-3.5" />
              Diamond Admin Platform
            </div>

            <div className="mt-6 flex items-center gap-4">
              <div className="relative h-20 w-20 shrink-0">
                <Image
                  src="/Diamond_Logo.png"
                  alt="Diamond Logo"
                  fill
                  style={{ objectFit: 'contain' }}
                  priority
                />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                  Welcome to Diamond
                </h1>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                  HPC operations for researchers and platform admins.
                </p>
              </div>
            </div>

            <div className="mt-8 space-y-3">
              <div className="flex items-start gap-3 rounded-xl border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/55">
                <ShieldCheck className="mt-0.5 h-4.5 w-4.5 text-slate-700 dark:text-slate-300" />
                <p className="text-sm text-slate-700 dark:text-slate-300">
                  Authentication is handled through your Globus account.
                </p>
              </div>
              <div className="flex items-start gap-3 rounded-xl border border-slate-200/70 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-800/55">
                <Cpu className="mt-0.5 h-4.5 w-4.5 text-slate-700 dark:text-slate-300" />
                <p className="text-sm text-slate-700 dark:text-slate-300">
                  Access endpoint, image, dataset, and task management in one place.
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-col justify-center p-8 md:p-10">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Sign in to continue
            </h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              Use Globus OAuth to securely access your Diamond workspace.
            </p>

            <div className="mt-6">
              <LoginButton className="h-11 w-full justify-center gap-2 border-slate-300/80 bg-white text-slate-800 shadow-sm transition-colors duration-200 hover:border-slate-400 hover:bg-slate-100 hover:text-slate-900 dark:border-slate-600 dark:bg-slate-900/80 dark:text-slate-100 dark:hover:border-slate-500 dark:hover:bg-slate-800/90 dark:hover:text-slate-100" />
            </div>

            <p className="mt-4 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
              By signing in, you agree to the Diamond service terms and
              conditions.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
