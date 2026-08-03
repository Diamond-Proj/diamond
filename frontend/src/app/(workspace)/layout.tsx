import type { ReactNode } from 'react';

import { AppShell } from '@/components/layout/app-shell';
import { TokenManagerServer } from '@/lib/auth/tokenManager.server';

export default async function WorkspaceLayout({
  children
}: {
  children: ReactNode;
}) {
  const tokens = await TokenManagerServer.getTokensFromServerCookies();
  const initialSession = TokenManagerServer.buildSession(tokens);

  return <AppShell initialSession={initialSession}>{children}</AppShell>;
}
