const { test, expect } = require('@playwright/test');

test.describe('Global SanMitra public smoke', () => {
  test('local frontend landing page renders', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByRole('heading', { name: 'SanMitra Local Frontends' })).toBeVisible();
    await expect(page.getByAltText('SanMitra')).toBeVisible();
    await expect(page.getByText(/pre-deployment testing against the unified backend/i)).toBeVisible();
  });

  test('mitrabooks entrypoint opens the public landing page', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('link', { name: 'Open' }).first().click();

    await expect(page).toHaveURL(/\/mitrabooks-erp\/landing\.html$/);
    await expect(page.getByRole('heading', { name: 'MitraBooks', exact: true })).toBeVisible();
    await expect(page.getByRole('navigation', { name: 'MitraBooks sections' })).toBeVisible();
    await expect(page.getByRole('link', { name: /^Login$/i }).first()).toBeVisible();
  });

  test('mitrabooks login shell remains reachable', async ({ page }) => {
    await page.goto('/mitrabooks-erp/login.html');

    await expect(page).toHaveURL(/\/mitrabooks-erp\/(login\.html|index\.html)/);
    await expect(page.getByRole('button', { name: /^sign in$/i })).toBeVisible();
    await expect(page.locator('#brand-title')).toContainText('MitraBooks');
  });

  test('legalmitra entrypoint is reachable', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: 'Open' }).nth(1).click();

    await expect(page).toHaveURL(/\/legalmitra\/?$/);
    await expect(page.locator('body')).toContainText(/LegalMitra/i);
  });
});
