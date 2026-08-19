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
  const flaskUrl = process.env.NEXT_PUBLIC_FLASK_URL || 'localhost:5328';
  const protocol = flaskUrl.includes('localhost') ? 'http' : 'https';
  const flaskBaseUrl = flaskUrl.startsWith('http')
    ? flaskUrl
    : `${protocol}://${flaskUrl}`;

  const response = await fetch(`${flaskBaseUrl}/api/globus_login_scopes`, {
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
