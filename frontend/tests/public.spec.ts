import { test, expect } from '@playwright/test';

test.describe('Sign-in page', () => {
  test('renders welcome content and Globus sign-in affordance', async ({
    page
  }) => {
    await page.goto('/sign-in');

    await expect(
      page.getByRole('heading', { name: /Welcome to Diamond/i })
    ).toBeVisible();
    await expect(page.getByText(/Sign in to continue/i)).toBeVisible();
    await expect(
      page.getByText(/Authentication is handled through your Globus account/i)
    ).toBeVisible();

    await expect(page.getByRole('button', { name: /Sign In/i })).toBeVisible();
  });

  test('clicking Sign In requests Globus OAuth with required params', async ({
    page
  }) => {
    // Intercept the navigation to Globus so we don't actually hit an external
    // service. We just want to verify the URL the app would send the user to.
    let capturedUrl: string | null = null;
    await page.route('https://auth.globus.org/**', async (route) => {
      capturedUrl = route.request().url();
      await route.abort();
    });

    await page.goto('/sign-in');
    await page
      .getByRole('button', { name: /Sign In/i })
      .click({ noWaitAfter: true });

    await expect.poll(() => capturedUrl, { timeout: 5_000 }).not.toBeNull();

    const url = new URL(capturedUrl!);
    expect(url.hostname).toBe('auth.globus.org');
    expect(url.pathname).toBe('/v2/oauth2/authorize');
    expect(url.searchParams.get('client_id')).toBeTruthy();
    expect(url.searchParams.get('redirect_uri')).toContain('/auth/callback');
    expect(url.searchParams.get('response_type')).toBe('code');
    expect(url.searchParams.get('scope')).toBeTruthy();
  });
});

test.describe('Auth gate (proxy.ts)', () => {
  // The proxy middleware redirects all non-public routes to /sign-in when
  // unauthenticated. This is the load-bearing security boundary — worth a smoke.
  for (const protectedRoute of [
    '/dashboard',
    '/tasks',
    '/datasets',
    '/images',
    '/endpoints'
  ]) {
    test(`unauthenticated visit to ${protectedRoute} redirects to /sign-in`, async ({
      page
    }) => {
      await page.goto(protectedRoute);
      await page.waitForURL('**/sign-in');
      expect(new URL(page.url()).pathname).toBe('/sign-in');
    });
  }
});
