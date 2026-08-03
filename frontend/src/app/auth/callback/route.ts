import { NextRequest, NextResponse } from 'next/server';
import {
  AUTH_CALLBACK_ROUTE,
  GLOBUS_TOKEN_URL,
  SIGN_IN_ROUTE
} from '@/lib/auth/constants';
import { TokenManagerServer } from '@/lib/auth/tokenManager.server';
import { type GlobusTokenResponse } from '@/lib/auth/types';

function redirectWithError(request: NextRequest, error: string) {
  const redirectUrl = new URL(SIGN_IN_ROUTE, request.url);
  redirectUrl.searchParams.set('error', error);
  return NextResponse.redirect(redirectUrl);
}

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const code = searchParams.get('code');
    const error = searchParams.get('error');

    console.log('=== Auth Callback Started ===');

    if (error) {
      console.error('OAuth error:', error);
      return redirectWithError(request, 'oauth_failed');
    }

    if (!code) {
      console.error('No authorization code received');
      return redirectWithError(request, 'no_code');
    }

    // Exchange code for tokens
    const clientId = process.env.NEXT_PUBLIC_GLOBUS_CLIENT_ID;
    const clientSecret = process.env.GLOBUS_CLIENT_SECRET;
    const redirectUri = new URL(AUTH_CALLBACK_ROUTE, request.url).toString();

    if (!clientId || !clientSecret) {
      console.error('Missing Globus credentials');
      return redirectWithError(request, 'config_error');
    }

    const params = new URLSearchParams({
      client_id: clientId,
      client_secret: clientSecret,
      grant_type: 'authorization_code',
      code: code,
      redirect_uri: redirectUri
    });

    console.log('Exchanging code for tokens...');

    const tokenResponse = await fetch(GLOBUS_TOKEN_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: params.toString()
    });

    if (!tokenResponse.ok) {
      const errorData = await tokenResponse.json();
      console.error('Token exchange failed:', tokenResponse.status, errorData);
      return redirectWithError(request, 'token_exchange_failed');
    }

    const tokenData = (await tokenResponse.json()) as GlobusTokenResponse;
    console.log('✓ Token exchange successful');
    console.log(
      'Received tokens for resource servers:',
      tokenData.other_tokens
        ? [
            'auth.globus.org',
            ...tokenData.other_tokens.map((token) => token.resource_server)
          ]
        : ['auth.globus.org']
    );

    // Format tokens
    const tokens = TokenManagerServer.formatTokenResponse(tokenData);
    console.log('✓ Tokens formatted');
    console.log(
      'Final resource servers:',
      Object.keys(tokens.by_resource_server)
    );

    // Check if we got funcx_service token
    if (!tokens.by_resource_server['funcx_service']) {
      console.warn('⚠️  WARNING: No funcx_service token received!');
      console.warn(
        'This may indicate missing scopes in the authorization request'
      );
    }

    const userInfo = TokenManagerServer.getUserInfo(tokens);
    console.log('✓ User info extracted:', userInfo);

    // Create redirect response
    const dashboardUrl = new URL('/dashboard', request.url);
    const response = NextResponse.redirect(dashboardUrl);

    console.log('Setting cookies...');
    TokenManagerServer.setTokensOnResponse(response, tokens);
    console.log('Resource servers in cookie:', Object.keys(tokens.by_resource_server));

    console.log('=== Auth Callback Completed ===');
    return response;
  } catch (error) {
    console.error('❌ Error in auth callback:', error);
    return redirectWithError(request, 'callback_failed');
  }
}
