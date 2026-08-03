import { test as setup } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const authFile = path.join(__dirname, '.auth/user.json');
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000';
const cookieDomain = new URL(baseURL).hostname;
const expiresAtSeconds = Math.floor(Date.now() / 1000) + 7 * 24 * 60 * 60;

function base64Url(value: unknown) {
  return Buffer.from(JSON.stringify(value)).toString('base64url');
}

function createMockIdToken() {
  return [
    base64Url({ alg: 'none', typ: 'JWT' }),
    base64Url({
      sub: 'test-user-identity',
      name: 'Test Researcher',
      email: 'test.researcher@example.com',
      organization: 'Diamond UI Test Lab',
      preferred_username: 'test-researcher',
      identity_set: Array.from({ length: 8 }, (_, index) => ({
        sub: `test-user-identity-${index + 1}`,
        name: `Linked Test Identity ${index + 1}`,
        username: `linked-test-${index + 1}`,
        email: `linked-test-${index + 1}@example.com`,
        organization: 'Diamond UI Test Lab'
      })),
      exp: expiresAtSeconds,
      iat: Math.floor(Date.now() / 1000),
      iss: 'https://auth.globus.org',
      aud: 'diamond-admin-dashboard'
    }),
    'test-signature'
  ].join('.');
}

setup('create automatic auth state', async ({ context }) => {
  const byResourceServer = {
    'auth.globus.org': {
      access_token: 'mock-auth-access-token',
      refresh_token: 'mock-auth-refresh-token',
      expires_at_seconds: expiresAtSeconds,
      resource_server: 'auth.globus.org',
      token_type: 'Bearer',
      scope: 'openid email profile'
    },
    funcx_service: {
      access_token: 'mock-compute-access-token',
      refresh_token: 'mock-compute-refresh-token',
      expires_at_seconds: expiresAtSeconds,
      resource_server: 'funcx_service',
      token_type: 'Bearer',
      scope:
        'https://auth.globus.org/scopes/facd7ccc-c5f4-42aa-916b-a0e270e2c2a9/all'
    }
  };

  await context.addCookies([
    {
      name: 'tokens',
      value: encodeURIComponent(JSON.stringify(byResourceServer)),
      domain: cookieDomain,
      path: '/',
      expires: expiresAtSeconds,
      httpOnly: true,
      secure: false,
      sameSite: 'Lax'
    },
    {
      name: 'id_token',
      value: createMockIdToken(),
      domain: cookieDomain,
      path: '/',
      expires: expiresAtSeconds,
      httpOnly: true,
      secure: false,
      sameSite: 'Lax'
    },
    {
      name: 'primary_identity',
      value: 'test-user-identity',
      domain: cookieDomain,
      path: '/',
      expires: expiresAtSeconds,
      httpOnly: true,
      secure: false,
      sameSite: 'Lax'
    }
  ]);

  fs.mkdirSync(path.dirname(authFile), { recursive: true });
  await context.storageState({ path: authFile });
});
