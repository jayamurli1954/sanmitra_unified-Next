const { test, expect } = require('@playwright/test');

test.describe('Global SanMitra public smoke', () => {
  test('login page renders without authentication', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByAltText('MandirMitra')).toBeVisible();
    await expect(page.getByRole('textbox', { name: /email/i })).toBeVisible();
    await expect(page.getByRole('textbox', { name: /^password$/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /^sign in$/i })).toBeVisible();
  });

  test('protected dashboard redirects unauthenticated users to login', async ({ page }) => {
    await page.goto('/');

    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByRole('button', { name: /^sign in$/i })).toBeVisible();
  });

  test('public payment entry route is reachable', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /book a seva|make a donation/i }).click();

    await expect(page).toHaveURL(/\/pay/);
    await expect(page.locator('body')).toContainText(/seva|donation|temple/i);
  });
});
