'use client';

import { LoginButton } from './login-button';
import { UserAvatar } from './user-avatar';
import type { AuthSession } from '@/lib/auth/types';

export function AuthStatus({
  session,
  isLoading
}: {
  session: AuthSession;
  isLoading: boolean;
}) {

  if (isLoading) {
    return (
      <div className="h-10 w-32 animate-pulse rounded-lg bg-slate-200/80 dark:bg-slate-700/70" />
    );
  }

  return (
    <div className="flex items-center">
      {session.isAuthenticated ? (
        <UserAvatar userInfo={session.userInfo} />
      ) : (
        <LoginButton />
      )}
    </div>
  );
}
