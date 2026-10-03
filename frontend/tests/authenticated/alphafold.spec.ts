import { test, expect } from '@playwright/test';

import { mockAlphafoldApi, mockTasksApi } from '../mocks/mock-api';

test.describe('AlphaFold structure prediction', () => {
  test('task submission modal exposes the AlphaFold template', async ({
    page
  }) => {
    await mockTasksApi(page);
    await page.goto('/tasks');

    await page.getByRole('button', { name: /Submit New Task/i }).click();
    await page.getByRole('button', { name: /^Templates$/ }).click();
    await page
      .getByRole('button', { name: /AlphaFold Structure Prediction/ })
      .click();

    await expect(page.getByText('Sequence', { exact: true })).toBeVisible();
    await expect(page.getByPlaceholder(/my_protein/)).toBeVisible();
    await expect(page.getByText('Upload FASTA / A3M')).toBeVisible();
    await expect(page.getByText('AlphaFold Container (.sif) *')).toBeVisible();
    await expect(
      page
        .getByText('AlphaFold Container (.sif) *')
        .locator('..')
        .locator('input')
    ).toHaveValue('/projects/bccu/diamond/colabfold_1.6.2-cuda12.sif');
    // The container dropdown is hidden: the image lives on Delta, not in Diamond.
    await expect(page.getByText('Container *')).toHaveCount(0);

    // Sequence, upload and input path are alternatives; none given is an error.
    await page.getByRole('button', { name: 'Submit Task' }).click();
    await expect(
      page.getByText(/Provide Sequence or Upload FASTA \/ A3M/)
    ).toBeVisible();
  });

  test('tasks page links AlphaFold tasks to the structure viewer', async ({
    page
  }) => {
    await mockAlphafoldApi(page);
    await page.goto('/tasks');
    const main = page.getByRole('main');

    await expect(main.getByText('AlphaFold Demo')).toBeVisible();
    await expect(main.getByText('Structure Prediction')).toBeVisible();
    await main.getByRole('link', { name: /Open Structure Viewer/ }).click();

    await page.waitForURL('**/tasks/alphafold/task-alphafold-001');
    await expect(
      page.getByRole('heading', { name: 'AlphaFold Structure Viewer' })
    ).toBeVisible();
    await expect(page.getByText('Mean pLDDT')).toBeVisible();
    await expect(page.getByText('70.0')).toBeVisible();
    await expect(page.getByText('0.71')).toBeVisible();
    await expect(page.getByRole('button', { name: /^Rank 1/ })).toHaveAttribute(
      'aria-pressed',
      'true'
    );
    await expect(
      page.getByRole('heading', { name: 'Predicted Aligned Error' })
    ).toBeVisible();
    await expect(
      page.getByRole('img', { name: 'Per-residue pLDDT' })
    ).toBeVisible();
    await expect(
      page.getByRole('img', { name: 'Predicted aligned error heatmap' })
    ).toBeVisible();
    await expect(page.getByText('2 chains')).toBeVisible();

    // Switching the rank reloads the scores for that model.
    await page.getByRole('button', { name: /^Rank 2/ }).click();
    await expect(page.getByText('60.0')).toBeVisible();
    await expect(page.getByText('0.60')).toBeVisible();

    await expect(
      page.getByRole('link', { name: 'Download PDB' })
    ).toHaveAttribute('href', /af_demo_unrelaxed_rank_002.*download=1/);
  });

  test('viewer explains non-AlphaFold tasks', async ({ page }) => {
    await mockTasksApi(page);
    await page.goto('/tasks/alphafold/task-ui-regression-002');

    await expect(
      page.getByText(/This task is not an AlphaFold task/)
    ).toBeVisible();
  });
});
