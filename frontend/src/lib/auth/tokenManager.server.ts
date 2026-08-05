import { cookies } from 'next/headers';
import type { NextRequest, NextResponse } from 'next/server';
import { AUTH_COOKIE_NAMES, GLOBUS_TOKEN_URL } from './constants';
import type {
  AuthSession,
  TokenStore,
  UserInfo,
  GlobusTokenResponse,
  TokenData,
  IdTokenClaims,
  IdTokenIdentity
} from './types';
import {
  GLOBUS_COMPUTE_SCOPE,
  REFRESH_BUFFER_SECONDS,
  TOKEN_COOKIE_MAX_AGE
} from './types';

type CookieWriter = {
  set: NextResponse['cookies']['set'];
  delete: NextResponse['cookies']['delete'];
};

type OAuthTokenData = {
  access_token: string;
  refresh_token?: string | null;
  expires_in?: number;
  resource_server?: string;
  token_type?: string;
  scope?: string;
};

const MAX_ID_TOKEN_IDENTITY_SET_ENTRIES = 3;

export class TokenManagerServer {
  private static normalizeResourceServer(
    resourceServer?: string,
    scope?: string
  ): string | null {
    if (scope?.split(' ').includes(GLOBUS_COMPUTE_SCOPE)) {
      return 'funcx_service';
    }

    if (resourceServer) {
      return resourceServer;
    }

    return null;
  }

  private static normalizeTokenData(
    token: Omit<TokenData, 'resource_server'> & { resource_server?: string }
  ): TokenData {
    const resourceServer =
      this.normalizeResourceServer(token.resource_server, token.scope) ||
      'auth.globus.org';

    return {
      ...token,
      resource_server: resourceServer
    };
  }

  private static decodeJwtPayload(token: string): Record<string, unknown> | null {
    try {
      const [, payload] = token.split('.');

      if (!payload) {
        return null;
      }

      const normalizedPayload = payload
        .replace(/-/g, '+')
        .replace(/_/g, '/')
        .padEnd(Math.ceil(payload.length / 4) * 4, '=');

      const decoded =
        typeof atob === 'function'
          ? atob(normalizedPayload)
          : Buffer.from(normalizedPayload, 'base64').toString('utf8');

      return JSON.parse(decoded) as Record<string, unknown>;
    } catch (error) {
      console.error('Failed to decode JWT payload:', error);
      return null;
    }
  }

  private static encodeJwtSegment(value: Record<string, unknown>): string {
    return Buffer.from(JSON.stringify(value), 'utf8').toString('base64url');
  }

  private static compactIdTokenForCookie(idToken: string): string {
    const claims = this.buildIdTokenClaims(idToken);

    if (!claims) {
      return idToken;
    }

    const payload: Record<string, unknown> = {
      sub: claims.sub,
      name: claims.name,
      email: claims.email,
      organization: claims.organization,
      preferred_username: claims.preferred_username,
      identity_provider: claims.identity_provider,
      identity_provider_display_name: claims.identity_provider_display_name,
      amr: claims.amr,
      acr: claims.acr,
      last_authentication: claims.last_authentication,
      identity_set: claims.identity_set,
      iss: claims.iss,
      aud: claims.aud,
      exp: claims.exp,
      iat: claims.iat,
      at_hash: claims.at_hash
    };
    const compactPayload = Object.fromEntries(
      Object.entries(payload).filter(([, value]) => value !== undefined)
    );

    return [
      this.encodeJwtSegment({ alg: 'none', typ: 'JWT' }),
      this.encodeJwtSegment(compactPayload),
      'local-claims'
    ].join('.');
  }

  private static buildIdTokenClaims(idToken?: string): TokenStore['id_token_claims'] {
    if (!idToken) {
      return undefined;
    }

    const payload = this.decodeJwtPayload(idToken);

    if (!payload) {
      return undefined;
    }

    return {
      sub: typeof payload.sub === 'string' ? payload.sub : '',
      name: typeof payload.name === 'string' ? payload.name : undefined,
      email: typeof payload.email === 'string' ? payload.email : undefined,
      organization:
        typeof payload.organization === 'string'
          ? payload.organization
          : undefined,
      preferred_username:
        typeof payload.preferred_username === 'string'
          ? payload.preferred_username
          : undefined,
      identity_provider:
        typeof payload.identity_provider === 'string'
          ? payload.identity_provider
          : undefined,
      identity_provider_display_name:
        typeof payload.identity_provider_display_name === 'string'
          ? payload.identity_provider_display_name
          : undefined,
      amr: this.parseAuthenticationMethods(payload.amr),
      acr: typeof payload.acr === 'string' ? payload.acr : undefined,
      last_authentication:
        typeof payload.last_authentication === 'number'
          ? payload.last_authentication
          : undefined,
      identity_set: this.parseIdentitySet(payload.identity_set),
      iss: typeof payload.iss === 'string' ? payload.iss : undefined,
      aud: this.parseAudience(payload.aud),
      exp: typeof payload.exp === 'number' ? payload.exp : undefined,
      iat: typeof payload.iat === 'number' ? payload.iat : undefined,
      at_hash: typeof payload.at_hash === 'string' ? payload.at_hash : undefined
    };
  }

  private static parseAudience(aud: unknown): IdTokenClaims['aud'] {
    if (typeof aud === 'string') {
      return aud;
    }

    if (Array.isArray(aud)) {
      const values = aud.filter((value): value is string => typeof value === 'string');
      return values.length > 0 ? values : undefined;
    }

    return undefined;
  }

  private static parseAuthenticationMethods(amr: unknown): IdTokenClaims['amr'] {
    if (amr === null) {
      return null;
    }

    if (!Array.isArray(amr)) {
      return undefined;
    }

    const values = amr.filter((value): value is string => typeof value === 'string');
    return values.length > 0 ? values : [];
  }

  private static parseIdentitySet(identitySet: unknown): IdTokenIdentity[] | undefined {
    if (!Array.isArray(identitySet)) {
      return undefined;
    }

    const identities = identitySet
      .map((identity) => this.parseIdentitySetEntry(identity))
      .filter((identity): identity is IdTokenIdentity => !!identity);
    const limitedIdentities = identities.slice(
      0,
      MAX_ID_TOKEN_IDENTITY_SET_ENTRIES
    );

    return limitedIdentities.length > 0 ? limitedIdentities : undefined;
  }

  private static parseIdentitySetEntry(identity: unknown): IdTokenIdentity | null {
    if (!identity || typeof identity !== 'object') {
      return null;
    }

    const entry = identity as Record<string, unknown>;

    if (typeof entry.sub !== 'string') {
      return null;
    }

    return {
      sub: entry.sub,
      organization:
        typeof entry.organization === 'string' ? entry.organization : undefined,
      name: typeof entry.name === 'string' ? entry.name : undefined,
      username: typeof entry.username === 'string' ? entry.username : undefined,
      identity_provider:
        typeof entry.identity_provider === 'string'
          ? entry.identity_provider
          : undefined,
      identity_provider_display_name:
        typeof entry.identity_provider_display_name === 'string'
          ? entry.identity_provider_display_name
          : undefined,
      email: typeof entry.email === 'string' ? entry.email : undefined,
      last_authentication:
        typeof entry.last_authentication === 'number'
          ? entry.last_authentication
          : undefined
    };
  }

  private static getCookieOptions() {
    return {
      path: '/',
      maxAge: TOKEN_COOKIE_MAX_AGE,
      httpOnly: true,
      sameSite: 'lax' as const,
      secure: process.env.NODE_ENV === 'production'
    };
  }

  private static buildCookieValues(tokens: TokenStore): Record<string, string> {
    const userInfo = this.getUserInfo(tokens);
    const values: Record<string, string> = {
      tokens: JSON.stringify(tokens.by_resource_server)
    };

    if (tokens.id_token) {
      values.id_token = this.compactIdTokenForCookie(tokens.id_token);
    }

    if (userInfo?.id) {
      values.primary_identity = userInfo.id;
    }

    return values;
  }

  private static createTokenData(
    token: OAuthTokenData,
    now: number,
    fallbackRefreshToken?: string
  ): TokenData {
    const resourceServer =
      this.normalizeResourceServer(token.resource_server, token.scope) ||
      'auth.globus.org';

    return {
      access_token: token.access_token,
      refresh_token: token.refresh_token ?? fallbackRefreshToken ?? null,
      expires_at_seconds: now + (token.expires_in || 3600),
      resource_server: resourceServer,
      token_type: token.token_type || 'Bearer',
      scope: token.scope || ''
    };
  }

  private static clearCookies(clearCookie: (name: string) => void): void {
    AUTH_COOKIE_NAMES.forEach((name) => {
      clearCookie(name);
    });
  }

  private static getPrimaryToken(tokens: TokenStore): TokenData | null {
    return (
      tokens.by_resource_server['auth.globus.org'] ||
      Object.values(tokens.by_resource_server)[0] ||
      null
    );
  }

  private static parseTokenStore(
    tokensCookie?: string,
    idToken?: string
  ): TokenStore | null {
    if (!tokensCookie) {
      return null;
    }

    const parsedTokens = JSON.parse(tokensCookie) as Record<string, TokenData>;
    const byResourceServer = Object.values(parsedTokens).reduce<
      Record<string, TokenData>
    >((acc, token) => {
      const normalizedToken = this.normalizeTokenData(token);
      acc[normalizedToken.resource_server] = normalizedToken;
      return acc;
    }, {});

    return {
      by_resource_server: byResourceServer,
      id_token: idToken,
      id_token_claims: this.buildIdTokenClaims(idToken)
    };
  }

  /**
   * Check if tokens are expired or need refresh
   */
  static needsRefresh(tokens: TokenStore): boolean {
    const now = Math.floor(Date.now() / 1000);

    const tokenNeedsRefresh = Object.values(tokens.by_resource_server).some(
      (token) => {
        const expiresIn = token.expires_at_seconds - now;
        return expiresIn <= REFRESH_BUFFER_SECONDS;
      }
    );

    if (tokenNeedsRefresh) {
      return true;
    }

    const idTokenExpiry = this.getIdTokenExpiry(tokens);
    if (!idTokenExpiry) {
      return true;
    }

    return idTokenExpiry - now <= REFRESH_BUFFER_SECONDS;
  }

  /**
   * Check if the current auth session is expired.
   * We validate the primary auth token rather than waiting for every
   * resource token to expire, otherwise an expired session can look valid.
   */
  static isExpired(tokens: TokenStore): boolean {
    const now = Math.floor(Date.now() / 1000);
    const primaryToken = this.getPrimaryToken(tokens);
    const idTokenExpiry = this.getIdTokenExpiry(tokens);

    return (
      !primaryToken ||
      primaryToken.expires_at_seconds <= now ||
      !idTokenExpiry ||
      idTokenExpiry <= now
    );
  }

  static getRefreshableResourceServers(tokens: TokenStore): string[] {
    return Object.entries(tokens.by_resource_server)
      .filter(([, token]) => !!token.refresh_token)
      .map(([resourceServer]) => resourceServer)
      .sort((left, right) => {
        // Refresh auth.globus.org first because that refresh response is the
        // source of renewed openid/profile/email claims and the new id_token.
        if (left === 'auth.globus.org') {
          return -1;
        }

        if (right === 'auth.globus.org') {
          return 1;
        }

        return left.localeCompare(right);
      });
  }

  static getUnrefreshableResourceServers(tokens: TokenStore): string[] {
    return Object.entries(tokens.by_resource_server)
      .filter(([, token]) => !token.refresh_token)
      .map(([resourceServer]) => resourceServer)
      .sort((left, right) => left.localeCompare(right));
  }

  static getIdTokenExpiry(tokens: TokenStore): number | null {
    return typeof tokens.id_token_claims?.exp === 'number'
      ? tokens.id_token_claims.exp
      : null;
  }

  static isIdTokenStale(tokens: TokenStore): boolean {
    const idTokenExpiry = this.getIdTokenExpiry(tokens);

    if (!idTokenExpiry) {
      return true;
    }

    const now = Math.floor(Date.now() / 1000);
    return idTokenExpiry - now <= REFRESH_BUFFER_SECONDS;
  }

  static getNextRefreshAtSeconds(tokens: TokenStore): number | null {
    const expiries = Object.values(tokens.by_resource_server).map(
      (token) => token.expires_at_seconds
    );
    const idTokenExpiry = this.getIdTokenExpiry(tokens);

    if (idTokenExpiry) {
      expiries.push(idTokenExpiry);
    }

    if (expiries.length === 0) {
      return null;
    }

    return Math.min(...expiries) - REFRESH_BUFFER_SECONDS;
  }

  static canRefreshTokenStore(tokens: TokenStore): boolean {
    return (
      this.getRefreshableResourceServers(tokens).length > 0 &&
      this.getUnrefreshableResourceServers(tokens).length === 0 &&
      !!tokens.by_resource_server['auth.globus.org']?.refresh_token
    );
  }

  /**
   * Extract user info from tokens
   */
  static getUserInfo(tokens: TokenStore): UserInfo | null {
    const claims = tokens.id_token_claims;
    if (!claims) return null;

    return {
      id: claims.sub,
      name: claims.name,
      email: claims.email,
      username: claims.preferred_username || claims.identity_set?.[0]?.username,
      organization: claims.organization
    };
  }

  static buildSession(tokens: TokenStore | null): AuthSession {
    if (!tokens) {
      return {
        isAuthenticated: false,
        userInfo: null,
        needsRefresh: false,
        nextRefreshAtSeconds: null
      };
    }

    const hasRefreshToken = this.canRefreshTokenStore(tokens);
    const isExpired = this.isExpired(tokens);

    return {
      isAuthenticated: !isExpired || hasRefreshToken,
      userInfo: this.getUserInfo(tokens),
      needsRefresh: this.needsRefresh(tokens),
      nextRefreshAtSeconds: this.getNextRefreshAtSeconds(tokens)
    };
  }

  /**
   * Refresh tokens using Globus OAuth
   */
  static async refreshTokens(refreshToken: string): Promise<TokenStore | null> {
    try {
      const clientId = process.env.NEXT_PUBLIC_GLOBUS_CLIENT_ID;
      const clientSecret = process.env.GLOBUS_CLIENT_SECRET;

      if (!clientId || !clientSecret) {
        throw new Error('Missing Globus credentials');
      }

      const params = new URLSearchParams({
        client_id: clientId,
        client_secret: clientSecret,
        grant_type: 'refresh_token',
        refresh_token: refreshToken
      });

      const response = await fetch(GLOBUS_TOKEN_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: params.toString()
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('Token refresh failed:', errorData);
        return null;
      }

      const tokenResponse: GlobusTokenResponse = await response.json();

      // Format tokens
      return this.formatTokenResponse(tokenResponse, refreshToken);
    } catch (error) {
      console.error('Error refreshing tokens:', error);
      return null;
    }
  }

  static async refreshTokenStore(tokens: TokenStore): Promise<TokenStore | null> {
    if (!this.canRefreshTokenStore(tokens)) {
      const unrefreshableResourceServers =
        this.getUnrefreshableResourceServers(tokens);

      console.error(
        'Token store cannot be fully refreshed.',
        unrefreshableResourceServers.length > 0
          ? { unrefreshableResourceServers }
          : { missingPrimaryRefreshToken: true }
      );
      return null;
    }

    const refreshableResourceServers = this.getRefreshableResourceServers(tokens);
    const requiresIdTokenRefresh = this.isIdTokenStale(tokens);

    if (refreshableResourceServers.length === 0) {
      return null;
    }

    let nextTokens = tokens;

    for (const resourceServer of refreshableResourceServers) {
      const currentToken = nextTokens.by_resource_server[resourceServer];
      const refreshToken = currentToken?.refresh_token;

      if (!refreshToken) {
        console.error(`Missing refresh token for ${resourceServer}`);
        return null;
      }

      const refreshedTokens = await this.refreshTokens(refreshToken);

      if (!refreshedTokens) {
        console.error(`Failed to refresh token for ${resourceServer}`);
        return null;
      }

      if (
        resourceServer === 'auth.globus.org' &&
        requiresIdTokenRefresh &&
        !refreshedTokens.id_token
      ) {
        console.error(
          'auth.globus.org refresh did not return a renewed id_token when one was required'
        );
        return null;
      }

      nextTokens = this.mergeTokenStores(nextTokens, refreshedTokens);
    }

    if (this.isExpired(nextTokens)) {
      console.error('Token refresh completed but the token bundle is still expired');
      return null;
    }

    if (this.needsRefresh(nextTokens)) {
      console.error(
        'Token refresh completed but the token bundle still needs refresh'
      );
      return null;
    }

    return nextTokens;
  }

  static mergeTokenStores(
    currentTokens: TokenStore,
    refreshedTokens: TokenStore
  ): TokenStore {
    const mergedResourceServers = {
      ...currentTokens.by_resource_server
    };

    Object.entries(refreshedTokens.by_resource_server).forEach(
      ([resourceServer, refreshedToken]) => {
        const currentToken = mergedResourceServers[resourceServer];

        mergedResourceServers[resourceServer] = {
          ...currentToken,
          ...refreshedToken,
          refresh_token:
            refreshedToken.refresh_token ?? currentToken?.refresh_token ?? null
        };
      }
    );

    return {
      by_resource_server: mergedResourceServers,
      id_token: refreshedTokens.id_token || currentTokens.id_token,
      id_token_claims:
        refreshedTokens.id_token_claims || currentTokens.id_token_claims
    };
  }

  /**
   * Format Globus token response into our TokenStore structure
   */
  static formatTokenResponse(
    tokenResponse: GlobusTokenResponse,
    fallbackRefreshToken?: string
  ): TokenStore {
    const now = Math.floor(Date.now() / 1000);
    const primaryToken = this.createTokenData(
      tokenResponse,
      now,
      fallbackRefreshToken
    );
    const byResourceServer: Record<string, TokenData> = {
      [primaryToken.resource_server]: primaryToken
    };

    // Handle other_tokens if present
    if (
      tokenResponse.other_tokens &&
      Array.isArray(tokenResponse.other_tokens)
    ) {
      tokenResponse.other_tokens.forEach((token) => {
        const normalizedToken = this.createTokenData(token, now);
        byResourceServer[normalizedToken.resource_server] = normalizedToken;
      });
    }

    // Decode ID token claims if present
    return {
      by_resource_server: byResourceServer,
      id_token: tokenResponse.id_token,
      id_token_claims: this.buildIdTokenClaims(tokenResponse.id_token)
    };
  }

  /**
   * Get tokens from server-side cookies
   * Reads the 'tokens' cookie which contains by_resource_server JSON (Flask backend format)
   */
  static async getTokensFromServerCookies(): Promise<TokenStore | null> {
    const cookieStore = await cookies();

    try {
      // Read the 'tokens' cookie which contains by_resource_server structure
      const tokensCookie = cookieStore.get('tokens')?.value;
      const idToken = cookieStore.get('id_token')?.value;

      console.log('Reading tokens from cookies:', {
        hasTokensCookie: !!tokensCookie,
        hasIdToken: !!idToken
      });

      if (!tokensCookie) {
        console.log('No tokens cookie found');
        return null;
      }

      const tokenStore = this.parseTokenStore(tokensCookie, idToken);

      if (!tokenStore) {
        return null;
      }

      console.log('✓ Parsed by_resource_server from tokens cookie');
      console.log(
        'Resource servers:',
        Object.keys(tokenStore.by_resource_server)
      );

      console.log('✓ Successfully loaded TokenStore from cookies');
      return tokenStore;
    } catch (error) {
      console.error('Failed to get tokens from cookies:', error);
      return null;
    }
  }

  static getTokensFromRequest(request: NextRequest): TokenStore | null {
    try {
      const tokensCookie = request.cookies.get('tokens')?.value;
      const idToken = request.cookies.get('id_token')?.value;

      return this.parseTokenStore(tokensCookie, idToken);
    } catch (error) {
      console.error('Failed to get tokens from request cookies:', error);
      return null;
    }
  }

  /**
   * Set auth cookies on a response object.
   */
  static setTokensOnResponse(
    response: { cookies: CookieWriter },
    tokens: TokenStore
  ): void {
    const cookieOptions = this.getCookieOptions();
    const values = this.buildCookieValues(tokens);

    this.clearCookiesOnResponse(response);

    // Store tokens cookie as by_resource_server JSON (for Flask backend)
    Object.entries(values).forEach(([name, value]) => {
      response.cookies.set(name, value, cookieOptions);
    });

    console.log('✓ Set auth cookies on response');
  }

  static setTokensOnRequest(request: NextRequest, tokens: TokenStore): void {
    const values = this.buildCookieValues(tokens);

    this.clearCookiesOnRequest(request);

    Object.entries(values).forEach(([name, value]) => {
      request.cookies.set(name, value);
    });
  }

  /**
   * Clear auth cookies on a response object.
   */
  static clearCookiesOnResponse(response: { cookies: CookieWriter }): void {
    this.clearCookies((name) => {
      response.cookies.delete(name);
    });
  }

  static clearCookiesOnRequest(request: NextRequest): void {
    this.clearCookies((name) => {
      request.cookies.delete(name);
    });
  }

  /**
   * Clear all auth cookies (server-side)
   */
  static async clearServerCookies(): Promise<void> {
    const cookieStore = await cookies();
    const responseLike = {
      cookies: {
        set: cookieStore.set.bind(cookieStore),
        delete: cookieStore.delete.bind(cookieStore)
      } satisfies CookieWriter
    };

    this.clearCookiesOnResponse(responseLike);
  }
}
