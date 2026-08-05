import { NextResponse } from 'next/server';
import { TokenManagerServer } from '@/lib/auth/tokenManager.server';

export async function GET() {
  const tokens = await TokenManagerServer.getTokensFromServerCookies();
  const session = TokenManagerServer.buildSession(tokens);

  return NextResponse.json(session, {
    headers: {
      'Cache-Control': 'no-store'
    }
  });
}
