import { test, expect } from '@playwright/test';

import { mockTasksApi } from '../mocks/mock-api';

// Every Delta template pins its Apptainer image to a path on the cluster, the
// way the AlphaFold template does, instead of picking a container from the
// Diamond database.
const TEMPLATES = [
  {
    name: 'SAM3 Finetuning',
    label: 'SAM3 Container (.sif) *',
    sif: '/projects/bcrc/diamond/images/sam3.sif'
  },
  {
    name: 'SAM3 Image Segmentation',
    label: 'SAM3 Container (.sif) *',
    sif: '/projects/bcrc/diamond/images/sam3.sif'
  },
  {
    name: 'DeepSpeed Finetuning',
    label: 'DeepSpeed Container (.sif) *',
    sif: '/projects/bcrc/diamond/images/deepspeed_chat.sif'
  },
  {
    name: 'Launch vLLM Chat Service',
    label: 'vLLM Container (.sif) *',
    sif: '/projects/bcrc/diamond/images/vllm-openai_nightly.sif'
  }
];

test.describe('Delta task templates', () => {
  for (const template of TEMPLATES) {
    test(`${template.name} pins its container path`, async ({ page }) => {
      await mockTasksApi(page);
      await page.goto('/tasks');

      await page.getByRole('button', { name: /Submit New Task/i }).click();
      await page.getByRole('button', { name: /^Templates$/ }).click();
      await page.getByRole('button', { name: template.name }).click();

      await expect(page.getByText(template.label)).toBeVisible();
      await expect(
        page.getByText(template.label).locator('..').locator('input')
      ).toHaveValue(template.sif);
      // The container dropdown is hidden: the image lives on Delta, not in Diamond.
      await expect(page.getByText('Container *')).toHaveCount(0);
    });
  }
});
