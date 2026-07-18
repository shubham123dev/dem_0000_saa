import { expect, test } from '@playwright/test';

test('loads the Phase 1 foundation without exposing raw endpoint controls', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', {name:'Frontend foundation ready'})).toBeVisible();
  await expect(page.getByRole('complementary', {name:'Ask AI placeholder'})).toBeVisible();
  await expect(page.locator('body')).not.toContainText('/agent/actions/propose');
});
