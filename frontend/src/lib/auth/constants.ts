import type { AuthSession } from './types';

export const AUTH_SESSION_ENDPOINT = '/api/auth/session';
export const AUTH_REFRESH_ENDPOINT = '/api/auth/refresh';
export const AUTH_REFRESH_RETRY_INTERVAL_MS = 60 * 1000;
export const AUTH_REFRESH_MIN_DELAY_MS = 1000;

export const HOME_ROUTE = '/';
export const LOGIN_ROUTE = '/login';
export const LOGOUT_ROUTE = '/logout';
export const SIGN_IN_ROUTE = '/sign-in';
export const AUTH_CALLBACK_ROUTE = '/auth/callback';

export const PUBLIC_AUTH_ROUTES = [HOME_ROUTE, SIGN_IN_ROUTE, AUTH_CALLBACK_ROUTE] as const;
export const AUTH_EXEMPT_API_ROUTES = ['/api/auth', '/api/healthcheck'] as const;
export const CLIENT_AUTH_REDIRECT_EXEMPT_ROUTES = [
  ...PUBLIC_AUTH_ROUTES,
  LOGOUT_ROUTE
] as const;

export const AUTH_COOKIE_NAMES = [
  'tokens',
  'primary_identity',
  'id_token'
] as const;

export const DEFAULT_AUTH_SESSION: AuthSession = {
  isAuthenticated: false,
  userInfo: null,
  needsRefresh: false,
  nextRefreshAtSeconds: null
};

export const GLOBUS_AUTHORIZE_URL = 'https://auth.globus.org/v2/oauth2/authorize';
export const GLOBUS_TOKEN_URL = 'https://auth.globus.org/v2/oauth2/token';
export const DEFAULT_GLOBUS_SCOPES =
  'openid email profile urn:globus:auth:scope:transfer.api.globus.org:all https://auth.globus.org/scopes/facd7ccc-c5f4-42aa-916b-a0e270e2c2a9/all';

export function pathnameMatches(
  pathname: string,
  routes: readonly string[]
): boolean {
  return routes.some((route) =>
    route === HOME_ROUTE ? pathname === HOME_ROUTE : pathname.startsWith(route)
  );
}
