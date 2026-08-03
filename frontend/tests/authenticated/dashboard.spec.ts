import { test, expect } from '@playwright/test';

import {
  mockCommonApi,
  mockDashboardApi,
  mockDatasetsApi,
  mockEndpointInventoryApi,
  mockEndpointsPageApi,
  mockImagesApi,
  mockTasksApi
} from '../mocks/mock-api';

function decodeJwtPayload(token: string) {
  const [, payload] = token.split('.');

  return JSON.parse(Buffer.from(payload, 'base64url').toString('utf8')) as {
    identity_set?: unknown[];
  };
}

test.describe('Authenticated UI regression', () => {
  test('dashboard renders user shell, stats, and quick actions', async ({
    page
  }) => {
    await mockDashboardApi(page);
    await page.goto('/dashboard');

    await expect(
      page.getByRole('heading', { name: /Welcome back, Test/i })
    ).toBeVisible();
    await expect(
      page.getByRole('heading', { name: /New to Diamond HPC/i })
    ).toBeVisible();
    await expect(page.getByRole('link', { name: /^Tasks$/ })).toBeVisible();
    await expect(page.getByRole('link', { name: /^Datasets$/ })).toBeVisible();
    await expect(page.getByRole('link', { name: /^Images$/ })).toBeVisible();
    await expect(
      page.getByRole('link', { name: /Tasks\s+11\s+Completed/i })
    ).toBeVisible();
    await expect(
      page.getByRole('link', { name: /Images\s+13\s+Public/i })
    ).toBeVisible();
  });

  test('dashboard welcomes users who have not completed initialization', async ({
    page
  }) => {
    await mockDashboardApi(page);
    await page.route('**/api/profile**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          profile: {
            identity_id: 'test-user-identity',
            name: 'Test Researcher',
            email: 'test.researcher@example.com',
            institution: 'Diamond UI Test Lab',
            is_initialized: false
          }
        })
      });
    });

    await page.goto('/dashboard');

    await expect(
      page.getByRole('heading', { name: /^Welcome, Test$/i })
    ).toBeVisible();
  });

  test('API response errors are visible in developer mode', async ({
    page
  }) => {
    await mockDashboardApi(page);
    await page.addInitScript(() => {
      localStorage.setItem('diamond:developer-mode', 'true');
    });
    await page.route('**/api/diagnostic-test', async (route) => {
      await route.fulfill({
        status: 422,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invalid diagnostic payload' })
      });
    });
    await page.route('**/api/diagnostic-secondary', async (route) => {
      await route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Secondary diagnostic failure' })
      });
    });

    await page.goto('/dashboard');
    await expect(
      page.getByRole('heading', { name: /Welcome back, Test/i })
    ).toBeVisible();
    await page
      .getByRole('button', { name: 'Open developer diagnostics' })
      .click();
    const diagnosticsPanel = page.getByRole('region', {
      name: 'API diagnostics'
    });
    await expect(diagnosticsPanel).toBeVisible();
    await page.evaluate(() =>
      Promise.all([
        fetch('/api/diagnostic-test'),
        fetch('/api/diagnostic-secondary')
      ])
    );

    const diagnostics = page.getByRole('alert', {
      name: 'API response error'
    });
    await expect(diagnostics).toHaveCount(2);
    await expect(
      diagnosticsPanel.getByRole('heading', { name: 'API Error Monitor' })
    ).toBeVisible();
    await expect(diagnosticsPanel).toContainText('422');
    await expect(diagnosticsPanel).toContainText('Invalid diagnostic payload');
    await expect(diagnosticsPanel).toContainText('503');
    await expect(diagnosticsPanel).toContainText(
      'Secondary diagnostic failure'
    );
    await page.reload();
    await page
      .getByRole('button', { name: 'Open developer diagnostics' })
      .click();
    await expect(diagnostics).toHaveCount(2);
    await expect(diagnosticsPanel).toContainText('Invalid diagnostic payload');
    await expect(diagnosticsPanel).toContainText(
      'Secondary diagnostic failure'
    );
    await page
      .getByRole('button', { name: 'Delete API error' })
      .first()
      .click();
    await expect(diagnostics).toHaveCount(1);
    await expect
      .poll(() =>
        page.evaluate(
          () =>
            JSON.parse(localStorage.getItem('diamond:api-errors') ?? '[]')
              .length
        )
      )
      .toBe(1);
    const clearAllErrors = page.getByRole('button', {
      name: 'Clear all API errors'
    });
    await clearAllErrors.hover();
    await expect
      .soft(page.getByRole('tooltip', { name: 'Clear all errors' }))
      .toBeVisible();
    await clearAllErrors.click();
    await expect(diagnostics).toHaveCount(0);
    await expect
      .poll(() =>
        page.evaluate(
          () =>
            JSON.parse(localStorage.getItem('diamond:api-errors') ?? '[]')
              .length
        )
      )
      .toBe(0);
  });

  test('API response errors stay hidden outside developer mode', async ({
    page
  }) => {
    await mockDashboardApi(page);
    await page.addInitScript(() => {
      localStorage.setItem('diamond:developer-mode', 'false');
    });
    await page.route('**/api/diagnostic-test', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal diagnostic detail' })
      });
    });

    await page.goto('/dashboard');
    await expect(
      page.getByRole('heading', { name: /Welcome back, Test/i })
    ).toBeVisible();
    await page.evaluate(() => fetch('/api/diagnostic-test'));
    await page.waitForTimeout(200);

    await expect(
      page.getByRole('alert', { name: 'API response error' })
    ).toHaveCount(0);
    await expect(
      page.getByRole('button', { name: 'Open developer diagnostics' })
    ).toHaveCount(0);
  });

  test('sidebar navigation keeps primary workspace routes reachable', async ({
    page
  }) => {
    await mockDashboardApi(page);
    await page.goto('/dashboard');

    await mockTasksApi(page);
    await page
      .getByRole('link', { name: /^Tasks$/ })
      .first()
      .click();
    await page.waitForURL('**/tasks');
    expect(new URL(page.url()).pathname).toBe('/tasks');

    await mockDatasetsApi(page);
    await page
      .getByRole('link', { name: /^Datasets$/ })
      .first()
      .click();
    await page.waitForURL('**/datasets');
    expect(new URL(page.url()).pathname).toBe('/datasets');

    await mockImagesApi(page);
    await page
      .getByRole('link', { name: /^Images$/ })
      .first()
      .click();
    await page.waitForURL('**/images');
    expect(new URL(page.url()).pathname).toBe('/images');
  });

  test('dashboard quick action cards route to feature pages', async ({
    page
  }) => {
    await mockDashboardApi(page);
    await page.goto('/dashboard');

    await mockTasksApi(page);
    await page
      .getByRole('link', {
        name: /Tasks Submit jobs and monitor execution status/i
      })
      .click();

    await page.waitForURL('**/tasks');
    expect(new URL(page.url()).pathname).toBe('/tasks');
  });

  test('dashboard setup guide expands onboarding instructions', async ({
    page
  }) => {
    await mockDashboardApi(page);
    await page.goto('/dashboard');

    await page.getByRole('button', { name: /Setup Guide/i }).click();

    await expect(
      page.getByRole('heading', { name: 'Globus Compute Endpoint Setup' })
    ).toBeVisible();
    await expect(
      page.getByText('globus-compute-endpoint configure <endpoint-name>')
    ).toBeVisible();
  });

  test('dashboard stat cards navigate to their workspace pages', async ({
    page
  }) => {
    await mockDashboardApi(page);
    await page.goto('/dashboard');

    await mockDatasetsApi(page);
    await page.getByRole('link', { name: /Datasets\s+9\s+Public/i }).click();

    await page.waitForURL('**/datasets');
    expect(new URL(page.url()).pathname).toBe('/datasets');
  });

  test('tasks page renders mocked task data and filters by search', async ({
    page
  }) => {
    await mockTasksApi(page);
    await page.goto('/tasks');
    const main = page.getByRole('main');

    await expect(main.getByRole('heading', { name: /^Tasks$/ })).toBeVisible();
    await expect(main.getByText('UI Regression Training')).toBeVisible();
    await expect(main.getByText('Completed Dataset Prep')).toBeVisible();

    await page.getByPlaceholder(/Search tasks/i).fill('completed');
    await expect(main.getByText('Completed Dataset Prep')).toBeVisible();
    await expect(main.getByText('UI Regression Training')).toBeHidden();
  });

  test('tasks page confirms and removes a deleted task', async ({ page }) => {
    await mockTasksApi(page);
    await page.goto('/tasks');
    const main = page.getByRole('main');

    await expect(main.getByText('Completed Dataset Prep')).toBeVisible();
    await main
      .getByRole('button', { name: /^Delete$/ })
      .nth(1)
      .click();

    await expect(
      page.getByRole('heading', { name: 'Delete Task' })
    ).toBeVisible();
    await page.getByRole('button', { name: 'Delete Task' }).click();

    await expect(main.getByText('Completed Dataset Prep')).toBeHidden();
    await expect(main.getByText('UI Regression Training')).toBeVisible();
  });

  test('task submission modal opens with core required fields', async ({
    page
  }) => {
    await mockTasksApi(page);
    await page.goto('/tasks');

    await page.getByRole('button', { name: /Submit New Task/i }).click();

    await expect(
      page.getByRole('heading', { name: 'Submit New Task' })
    ).toBeVisible();
    await expect(
      page.getByText('Configure and submit a new computational task')
    ).toBeVisible();
    await expect(page.getByText('Task Name *')).toBeVisible();
    await expect(page.getByText('Endpoint *')).toBeVisible();
    await expect(
      page.getByRole('button', { name: 'Submit Task' })
    ).toBeVisible();
  });

  test('datasets page renders mocked dataset inventory', async ({ page }) => {
    await mockDatasetsApi(page);
    await page.goto('/datasets');
    const main = page.getByRole('main');

    await expect(
      main.getByRole('heading', { name: /^Datasets$/ })
    ).toBeVisible();
    await expect(main.getByText('ui-regression-dataset')).toBeVisible();
    await expect(
      main.getByText('Dataset used by automated UI regression tests')
    ).toBeVisible();
    await expect(main.getByText('public-benchmark-dataset')).toBeVisible();
  });

  test('datasets page filters by search text and visibility', async ({
    page
  }) => {
    await mockDatasetsApi(page);
    await page.goto('/datasets');
    const main = page.getByRole('main');

    await page.getByLabel('Search datasets').fill('public benchmark');
    await expect(main.getByText('public-benchmark-dataset')).toBeVisible();
    await expect(main.getByText('ui-regression-dataset')).toBeHidden();

    await page.getByRole('button', { name: /All Types/i }).click();
    await page.getByRole('button', { name: /^Private$/ }).click();

    await expect(main.getByText('No datasets found')).toBeVisible();
  });

  test('dataset registration modal validates required fields', async ({
    page
  }) => {
    await mockDatasetsApi(page);
    await page.goto('/datasets');

    await page.getByRole('button', { name: /Create Dataset/i }).click();

    await expect(
      page.getByRole('heading', { name: 'Register New Dataset' })
    ).toBeVisible();
    await page.getByRole('button', { name: /Register Dataset/i }).click();

    await expect(page.getByText('Dataset name is required')).toBeVisible();
    await expect(page.getByText('Collection UUID is required')).toBeVisible();
    await expect(page.getByText('Globus path is required')).toBeVisible();
    await expect(page.getByText('System path is required')).toBeVisible();
    await expect(page.getByText('Machine name is required')).toBeVisible();
  });

  test('images page renders private and public containers', async ({
    page
  }) => {
    await mockImagesApi(page);
    await page.goto('/images');

    await expect(
      page.getByRole('heading', { name: /^Container Images$/ })
    ).toBeVisible();
    await expect(
      page.getByRole('heading', { name: 'ui-regression-runtime' })
    ).toBeVisible();
    await expect(
      page.getByRole('heading', { name: 'diamond-public-runtime' })
    ).toBeVisible();
  });

  test('images page confirms and removes an owned container', async ({
    page
  }) => {
    await mockImagesApi(page);
    await page.goto('/images');

    await page.getByRole('button', { name: /^Delete$/ }).click();
    await expect(
      page.getByRole('heading', { name: 'Delete Container' })
    ).toBeVisible();
    await page.getByRole('button', { name: 'Delete Container' }).click();

    await expect(
      page.getByRole('heading', { name: 'ui-regression-runtime' })
    ).toBeHidden();
    await expect(
      page.getByRole('heading', { name: 'diamond-public-runtime' })
    ).toBeVisible();
  });

  test('image builder modal starts on endpoint step with guarded next action', async ({
    page
  }) => {
    await mockImagesApi(page);
    await mockEndpointInventoryApi(page);
    await page.goto('/images');

    await page.getByRole('button', { name: /Build New Image/i }).click();

    await expect(
      page.getByRole('heading', { name: 'Image Builder' })
    ).toBeVisible();
    await expect(page.getByText('Step 1 of 4')).toBeVisible();
    await expect(
      page.getByRole('heading', { name: 'HPC Endpoint' })
    ).toBeVisible();
    await expect(
      page.getByRole('button', { name: 'Next', exact: true })
    ).toBeDisabled();
  });

  test('endpoints page shows managed and available endpoint tabs', async ({
    page
  }) => {
    await mockEndpointsPageApi(page);
    await page.goto('/endpoints');

    await expect(
      page.getByRole('heading', { name: 'Endpoint Management' })
    ).toBeVisible();
    await expect(page.getByText('UI Test GPU Queue')).toBeVisible();
    await expect(page.getByText('gpu01.test')).toBeVisible();
    await expect(page.getByLabel('Diamond Work Path')).toHaveValue('/scratch');

    await page.getByRole('tab', { name: 'Available Endpoints' }).click();
    await expect(page.getByText('Available CPU Queue')).toBeVisible();
    await expect(page.getByRole('button', { name: /^Add$/ })).toBeVisible();
  });

  test('endpoints refresh prepares endpoint metadata', async ({ page }) => {
    await mockEndpointsPageApi(page);
    await page.goto('/endpoints');

    await page.getByRole('button', { name: /Refresh Endpoints/i }).click();

    await expect(page.getByText('Endpoint data ready')).toBeVisible();
    await expect(
      page.getByText('Endpoint data preparation complete.')
    ).toBeVisible();
  });

  test('profile page renders authenticated user details', async ({ page }) => {
    await mockCommonApi(page);
    await page.goto('/profile');

    await expect(
      page.getByRole('heading', { name: 'Account Details' })
    ).toBeVisible();
    await expect(page.getByText('Test Researcher').first()).toBeVisible();
    await expect(
      page.getByText('test.researcher@example.com').first()
    ).toBeVisible();
    await expect(page.getByText('test-researcher').first()).toBeVisible();
    await expect(page.getByText('Diamond UI Test Lab').first()).toBeVisible();
    const developerMode = page.getByRole('switch', {
      name: 'Toggle developer mode'
    });
    await expect(developerMode).not.toBeChecked();
    await developerMode.click();
    await expect(developerMode).toBeChecked();
    const browserStorage = page.getByRole('button', {
      name: /Browser Storage/
    });
    await expect(browserStorage).toBeVisible();
    await expect(browserStorage).toHaveAttribute('aria-expanded', 'false');
    await expect(
      page.getByRole('button', { name: 'Open developer diagnostics' })
    ).toBeVisible();
    await expect
      .poll(() =>
        page.evaluate(() => localStorage.getItem('diamond:developer-mode'))
      )
      .toBe('true');
  });

  test('auth cookie keeps linked identities compact after server writes cookies', async ({
    page
  }) => {
    const response = await page.request.post('/api/auth/debug/expire', {
      data: { target: 'funcx_service' }
    });

    expect(response.ok()).toBe(true);

    const idTokenCookie = (await page.context().cookies()).find(
      (cookie) => cookie.name === 'id_token'
    );

    expect(idTokenCookie).toBeDefined();

    const payload = decodeJwtPayload(idTokenCookie?.value ?? '');

    expect(payload.identity_set).toHaveLength(3);
    expect(idTokenCookie?.value.length).toBeLessThan(2000);
  });
});
