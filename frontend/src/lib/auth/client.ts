'use client';

import { AUTH_SESSION_ENDPOINT, DEFAULT_AUTH_SESSION } from './constants';
import type { AuthSession } from './types';

export async function fetchAuthSession(): Promise<AuthSession> {
  const response = await fetch(AUTH_SESSION_ENDPOINT, {
    method: 'GET',
    cache: 'no-store',
    credentials: 'include'
  });

  if (!response.ok) {
    throw new Error('Failed to fetch auth session');
  }

  return (await response.json()) as AuthSession;
}

export async function fetchDynamicGlobusScopes(): Promise<string[]> {
  // Same-origin: next.config.ts rewrites /api/* to the Flask backend.
  const response = await fetch('/api/globus_login_scopes', {
    method: 'GET',
    cache: 'no-store'
  });

  if (!response.ok) {
    throw new Error('Failed to fetch dynamic Globus scopes');
  }

  const data = await response.json();
  return data.scopes || [];
}

export function createDefaultAuthSession(): AuthSession {
  return { ...DEFAULT_AUTH_SESSION };
}
