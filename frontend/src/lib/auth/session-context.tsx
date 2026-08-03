'use client';

import { createContext, useContext, type ReactNode } from 'react';
import type { AuthSession } from './types';

type AuthSessionContextValue = {
  session: AuthSession;
};

const AuthSessionContext = createContext<AuthSessionContextValue | null>(null);

export function AuthSessionProvider({
  children,
  value
}: {
  children: ReactNode;
  value: AuthSessionContextValue;
}) {
  return (
    <AuthSessionContext.Provider value={value}>
      {children}
    </AuthSessionContext.Provider>
  );
}

export function useAuthSessionContext(): AuthSessionContextValue {
  const value = useContext(AuthSessionContext);

  if (!value) {
    throw new Error('useAuthSessionContext must be used within AuthSessionProvider');
  }

  return value;
}
