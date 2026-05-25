const { test, expect } = require('@playwright/test');

const email = process.env.E2E_USER_EMAIL;
const password = process.env.E2E_USER_PASSWORD;

test.describe('Global authenticated smoke', () => {
  test.skip(!email || !password, 'Set E2E_USER_EMAIL and E2E_USER_PASSWORD to run authenticated smoke tests.');

  test('test user can log in and reach a protected workspace', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('textbox', { name: /email/i }).fill(email);
    await page.getByRole('textbox', { name: /^password$/i }).fill(password);
    await page.getByRole('button', { name: /^sign in$/i }).click();

    await expect(page).toHaveURL(/\/(brand-intro|dashboard|profile|platform\/operations)/, { timeout: 30000 });

    if (page.url().includes('/brand-intro')) {
      await page.goto('/dashboard');
    }

    await expect(page.locator('body')).toContainText(/dashboard|platform|profile/i);
  });
});
