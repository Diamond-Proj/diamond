import { defineConfig, devices } from '@playwright/test';

const AUTH_STATE = 'tests/.auth/user.json';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI
    ? [['list'], ['html']]
    : [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure'
  },

  projects: [
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts$/,
      use: { ...devices['Desktop Chrome'] }
    },
    {
      // Public tests verify behavior available without auth (sign-in page,
      // proxy.ts redirect gate). They run in a fresh context — no storageState.
      name: 'chromium-public',
      use: { ...devices['Desktop Chrome'] },
      testIgnore: [/.*\.setup\.ts$/, /authenticated\/.*/]
    },
    {
      // Authenticated tests reuse the storage state captured by `setup`.
      name: 'chromium-authenticated',
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
        storageState: AUTH_STATE
      },
      testMatch: /authenticated\/.*\.spec\.ts$/
    }
  ],

  webServer: {
    command: 'pnpm dev',
    env: {
      NEXT_PUBLIC_GLOBUS_CLIENT_ID:
        process.env.NEXT_PUBLIC_GLOBUS_CLIENT_ID ?? 'playwright-client-id',
      NEXT_PUBLIC_GLOBUS_SCOPES:
        process.env.NEXT_PUBLIC_GLOBUS_SCOPES ?? 'openid email profile'
    },
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000
  }
});
