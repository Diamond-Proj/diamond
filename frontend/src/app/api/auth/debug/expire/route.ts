import { NextRequest, NextResponse } from 'next/server';
import { TokenManagerServer } from '@/lib/auth/tokenManager.server';
import type { TokenStore, TokenData } from '@/lib/auth/types';

/**
 * Development-only auth expiry simulator.
 *
 * Browser console usage:
 * await fetch('/api/auth/debug/expire', {
 *   method: 'POST',
 *   headers: { 'Content-Type': 'application/json' },
 *   body: JSON.stringify({ target: 'id_token' })
 * });
 * await fetch('/api/auth/debug/expire', {
 *   method: 'POST',
 *   headers: { 'Content-Type': 'application/json' },
 *   body: JSON.stringify({ target: 'auth.globus.org' })
 * });
 * await fetch('/api/auth/debug/expire', {
 *   method: 'POST',
 *   headers: { 'Content-Type': 'application/json' },
 *   body: JSON.stringify({ target: 'transfer.api.globus.org' })
 * });
 * await fetch('/api/auth/debug/expire', {
 *   method: 'POST',
 *   headers: { 'Content-Type': 'application/json' },
 *   body: JSON.stringify({ target: 'funcx_service' })
 * });
 *
 * Hard-expire examples:
 * await fetch('/api/auth/debug/expire', {
 *   method: 'POST',
 *   headers: { 'Content-Type': 'application/json' },
 *   body: JSON.stringify({ target: 'auth.globus.org', mode: 'hard' })
 * });
 * await fetch('/api/auth/debug/expire', {
 *   method: 'POST',
 *   headers: { 'Content-Type': 'application/json' },
 *   body: JSON.stringify({ target: 'all', mode: 'hard' })
 * });
 */

type ExpireMode = 'refreshable' | 'hard';
type ExpireTarget =
  | 'all'
  | 'id_token'
  | 'auth.globus.org'
  | 'transfer.api.globus.org'
  | 'funcx_service';

function encodeBase64Url(value: string): string {
  return Buffer.from(value, 'utf8')
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '');
}

function expireIdToken(idToken: string, expiredAt: number): string {
  try {
    const [header, payload, signature] = idToken.split('.');

    if (!header || !payload || !signature) {
      return idToken;
    }

    const normalizedPayload = payload
      .replace(/-/g, '+')
      .replace(/_/g, '/')
      .padEnd(Math.ceil(payload.length / 4) * 4, '=');

    const parsedPayload = JSON.parse(
      Buffer.from(normalizedPayload, 'base64').toString('utf8')
    ) as Record<string, unknown>;

    parsedPayload.exp = expiredAt;

    return `${header}.${encodeBase64Url(JSON.stringify(parsedPayload))}.${signature}`;
  } catch {
    return idToken;
  }
}

function expireTokens(
  tokens: TokenStore,
  mode: ExpireMode,
  target: ExpireTarget
): TokenStore {
  const expiredAt = Math.floor(Date.now() / 1000) - 60;
  const shouldExpireIdToken = target === 'all' || target === 'id_token';

  const byResourceServer = Object.fromEntries(
    Object.entries(tokens.by_resource_server).map(([resourceServer, token]) => {
      const shouldExpireToken =
        target === 'all' || target === resourceServer;
      const nextToken: TokenData = {
        ...token,
        expires_at_seconds: shouldExpireToken
          ? expiredAt
          : token.expires_at_seconds,
        refresh_token:
          shouldExpireToken && mode === 'hard' ? null : token.refresh_token
      };

      return [resourceServer, nextToken];
    })
  );

  return {
    ...tokens,
    by_resource_server: byResourceServer,
    id_token:
      shouldExpireIdToken && tokens.id_token
        ? expireIdToken(tokens.id_token, expiredAt)
        : tokens.id_token,
    id_token_claims:
      shouldExpireIdToken && tokens.id_token_claims
        ? {
            ...tokens.id_token_claims,
            exp: expiredAt
          }
        : tokens.id_token_claims
  };
}

function parseMode(mode: unknown): ExpireMode {
  return mode === 'hard' ? 'hard' : 'refreshable';
}

function parseTarget(target: unknown): ExpireTarget {
  if (
    target === 'id_token' ||
    target === 'auth.globus.org' ||
    target === 'transfer.api.globus.org' ||
    target === 'funcx_service'
  ) {
    return target;
  }

  return 'all';
}

export async function POST(request: NextRequest) {
  if (process.env.NODE_ENV === 'production') {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }

  const tokens = await TokenManagerServer.getTokensFromServerCookies();

  if (!tokens) {
    return NextResponse.json(
      { error: 'No auth tokens found in cookies' },
      { status: 401 }
    );
  }

  let requestBody: { mode?: unknown; target?: unknown } = {};

  try {
    requestBody = (await request.json()) as { mode?: unknown; target?: unknown };
  } catch {
    requestBody = {};
  }

  const mode = parseMode(requestBody.mode);
  const target = parseTarget(requestBody.target);
  const expiredTokens = expireTokens(tokens, mode, target);

  const response = NextResponse.json({
    success: true,
    mode,
    target,
    resource_servers: Object.keys(expiredTokens.by_resource_server),
    id_token_expired:
      (target === 'all' || target === 'id_token') && !!expiredTokens.id_token_claims,
    message:
      mode === 'hard'
        ? `Expired ${target} and removed refresh token support where applicable.`
        : `Expired ${target} while keeping existing refresh tokens.`
  });

  TokenManagerServer.setTokensOnResponse(response, expiredTokens);

  return response;
}
