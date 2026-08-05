import { NextResponse } from 'next/server';
import { TokenManagerServer } from '@/lib/auth/tokenManager.server';

function unauthorized(error: string) {
  const response = NextResponse.json({ error }, { status: 401 });
  TokenManagerServer.clearCookiesOnResponse(response);
  return response;
}

export async function POST() {
  try {
    console.log('Token refresh request received');

    // Get tokens from cookies
    const tokens = await TokenManagerServer.getTokensFromServerCookies();

    if (!tokens) {
      console.error('No tokens found in cookies');
      return unauthorized('No tokens found');
    }

    if (!TokenManagerServer.canRefreshTokenStore(tokens)) {
      console.error('Token bundle is not fully refreshable');
      return unauthorized('No refresh token available');
    }

    // Refresh all resource-server tokens plus id_token
    const refreshedTokens = await TokenManagerServer.refreshTokenStore(tokens);

    if (!refreshedTokens) {
      console.error('Failed to refresh tokens');
      return unauthorized('Failed to refresh tokens');
    }

    console.log('Tokens refreshed successfully');

    const response = NextResponse.json({
      success: true,
      session: TokenManagerServer.buildSession(refreshedTokens)
    });

    TokenManagerServer.setTokensOnResponse(response, refreshedTokens);

    return response;
  } catch (error) {
    console.error('Error in token refresh:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: (error as Error).message },
      { status: 500 }
    );
  }
}
