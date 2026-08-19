import { NextRequest, NextResponse } from 'next/server';
import {
  AUTH_EXEMPT_API_ROUTES,
  DEFAULT_GLOBUS_SCOPES,
  GLOBUS_AUTHORIZE_URL,
  LOGIN_ROUTE,
  LOGOUT_ROUTE,
  PUBLIC_AUTH_ROUTES,
  SIGN_IN_ROUTE,
  pathnameMatches
} from './constants';
import { TokenManagerServer } from './tokenManager.server';
import type { TokenStore } from './types';
import { fetchDynamicGlobusScopes } from './client'; // Import fetchDynamicGlobusScopes

function getBaseUrl(request: NextRequest): string {
  return request.nextUrl.origin;
}

function createSignInRedirect(
  request: NextRequest,
  clearCookies = false
): NextResponse {
  const signInUrl = new URL(SIGN_IN_ROUTE, getBaseUrl(request));
  console.log('Redirecting to sign-in:', signInUrl.toString());
  const response = NextResponse.redirect(signInUrl);

  if (clearCookies) {
    TokenManagerServer.clearCookiesOnResponse(response);
  }

  return response;
}

function createAuthenticatedResponse(
  request: NextRequest,
  tokens: TokenStore
): NextResponse {
  TokenManagerServer.setTokensOnRequest(request, tokens);
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('cookie', request.cookies.toString());

  const response = NextResponse.next({
    request: {
      headers: requestHeaders
    }
  });

  TokenManagerServer.setTokensOnResponse(response, tokens);
  return response;
}

function getExpiredSessionRedirect(
  request: NextRequest,
  tokens: TokenStore
): NextResponse | null {
  if (!TokenManagerServer.isExpired(tokens)) {
    return null;
  }

  return createSignInRedirect(request, true);
}

async function initiateGlobusLogin(request: NextRequest): Promise<NextResponse> {
  try {
    const clientId = process.env.NEXT_PUBLIC_GLOBUS_CLIENT_ID;
    const staticScopes = process.env.NEXT_PUBLIC_GLOBUS_SCOPES
      ? process.env.NEXT_PUBLIC_GLOBUS_SCOPES.split(' ')
      : [];
    const redirectUri = `${getBaseUrl(request)}/auth/callback`;

    if (!clientId) {
      throw new Error('GLOBUS_CLIENT_ID not configured');
    }

    const dynamicScopes = await fetchDynamicGlobusScopes();
    const allScopes = Array.from(
      new Set([...DEFAULT_GLOBUS_SCOPES.split(' '), ...staticScopes, ...dynamicScopes])
    ).join(' ');

    const params = new URLSearchParams({
      client_id: clientId,
      redirect_uri: redirectUri,
      response_type: 'code',
      scope: allScopes,
      access_type: 'offline'
    });

    const loginUrl = `${GLOBUS_AUTHORIZE_URL}?${params.toString()}`;
    console.log('Initiating Globus login:', loginUrl);

    return NextResponse.redirect(loginUrl);
  } catch (error) {
    console.error('Error initiating Globus login:', error);
    return createSignInRedirect(request);
  }
}

async function signOut(request: NextRequest): Promise<NextResponse> {
  console.log('Processing sign-out...');

  const response = NextResponse.redirect(new URL(SIGN_IN_ROUTE, request.url));
  TokenManagerServer.clearCookiesOnResponse(response);

  console.log('Sign-out successful');
  return response;
}

async function maybeRefreshTokens(
  request: NextRequest,
  tokens: TokenStore
): Promise<NextResponse | null> {
  if (!TokenManagerServer.needsRefresh(tokens)) {
    return null;
  }

  console.log('Tokens need refresh, attempting refresh...');

  if (!TokenManagerServer.canRefreshTokenStore(tokens)) {
    console.log('Token bundle is not fully refreshable, redirecting to sign-in');
    return getExpiredSessionRedirect(request, tokens);
  }

  const refreshedTokens = await TokenManagerServer.refreshTokenStore(tokens);

  if (!refreshedTokens) {
    console.log('Token refresh failed for expired session, redirecting to sign-in');
    return getExpiredSessionRedirect(request, tokens);
  }

  console.log('Tokens refreshed in proxy');
  return createAuthenticatedResponse(request, refreshedTokens);
}

export async function auth(request: NextRequest): Promise<NextResponse> {
  try {
    const pathname = request.nextUrl.pathname;
    console.log('Auth check for:', pathname);

    // Handle logout
    if (pathname.startsWith(LOGOUT_ROUTE)) {
      return signOut(request);
    }

    // Handle login initiation
    if (pathname.startsWith(LOGIN_ROUTE)) {
      return initiateGlobusLogin(request);
    }

    // Allow public routes without any auth check
    if (pathnameMatches(pathname, PUBLIC_AUTH_ROUTES)) {
      console.log('Public route, allowing access');
      return NextResponse.next();
    }

    // Allow API routes (they handle their own auth)
    if (pathnameMatches(pathname, AUTH_EXEMPT_API_ROUTES)) {
      console.log('API route, allowing access');
      return NextResponse.next();
    }

    // Check authentication for protected routes
    const tokens = TokenManagerServer.getTokensFromRequest(request);

    if (!tokens) {
      console.log('No tokens found, redirecting to sign-in');
      return createSignInRedirect(request, true);
    }

    const refreshResponse = await maybeRefreshTokens(request, tokens);

    if (refreshResponse) {
      return refreshResponse;
    }

    // Allow authenticated request
    console.log('User authenticated, allowing access');
    return NextResponse.next();
  } catch (error) {
    console.error('Error in auth middleware:', error);
    return createSignInRedirect(request);
  }
}
