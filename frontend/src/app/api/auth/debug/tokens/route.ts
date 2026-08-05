import { NextResponse } from 'next/server';
import { TokenManagerServer } from '@/lib/auth/tokenManager.server';

export async function GET() {
  if (process.env.NODE_ENV === 'production') {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }

  const tokens = await TokenManagerServer.getTokensFromServerCookies();

  if (!tokens) {
    return NextResponse.json(
      { authenticated: false, resource_servers: [] },
      { status: 200 }
    );
  }

  return NextResponse.json({
    authenticated: true,
    resource_servers: Object.keys(tokens.by_resource_server),
    unrefreshable_resource_servers:
      TokenManagerServer.getUnrefreshableResourceServers(tokens),
    tokens: Object.fromEntries(
      Object.entries(tokens.by_resource_server).map(([key, value]) => [
        key,
        {
          resource_server: value.resource_server,
          expires_at_seconds: value.expires_at_seconds,
          has_refresh_token: !!value.refresh_token,
          scope: value.scope
        }
      ])
    ),
    has_id_token: !!tokens.id_token,
    has_user_claims: !!tokens.id_token_claims,
    id_token_expires_at_seconds: tokens.id_token_claims?.exp ?? null,
    id_token_claims: tokens.id_token_claims ?? null
  });
}
