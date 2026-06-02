const { test, expect } = require('@playwright/test');

test.describe('MitraBooks ERP static shell', () => {
  test('loads dashboard and opens core workspaces', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('sanmitra_frontend_access_token', 'static-shell-token');
      window.localStorage.setItem('sanmitra_mitrabooks_login_email', 'businessadmin@sanmitra.local');
    });
    await page.goto('/mitrabooks-erp/');

    await expect(page).toHaveTitle('MitraBooks Pro');
    await expect(page.locator('#brand-title')).toContainText('MitraBooks Pro');
    await expect(page.locator('#brand-subtitle')).toContainText('Unified Enterprise ERP');
    await expect(page.getByRole('button', { name: 'Platform Owner' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'MandirMitra' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'GruhaMitra' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Main Workspaces' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Expenses (Purchases)' })).toBeVisible();
    await expect(page.locator('nav#nav a[data-business-workspace="bills"]')).toHaveAttribute('aria-disabled', 'true');
    await page.getByRole('button', { name: 'Expenses (Purchases)' }).click();
    await expect(page.locator('nav#nav a[data-business-workspace="bills"]')).toBeHidden();
    await page.getByRole('button', { name: 'Expenses (Purchases)' }).click();
    await expect(page.locator('nav#nav a[data-business-workspace="bills"]')).toBeVisible();
    await expect(page.locator('#access-panel')).toBeHidden();
    await expect(page.locator('.business-dashboard')).toBeVisible();
    await expect(page.locator('.erp-health-panel')).toBeVisible();
    await expect(page.locator('.erp-health-panel')).toContainText('Data Health');
    await expect(page.locator('.erp-health-panel')).toContainText('Business tenant context');
    await expect(page.locator('.erp-health-panel')).toContainText('Chart of accounts loaded');
    await expect(page.locator('.erp-health-panel')).toContainText('Cash and bank accounts');
    await expect(page.locator('.erp-health-panel')).toContainText('Party GSTIN sample');
    await expect(page.locator('.erp-health-panel')).toContainText('Voucher drill-down');
    await expect(page.locator('.erp-health-actions')).toContainText('Action Queue');
    await expect(page.locator('.erp-health-actions')).toContainText('Concrete next fixes');
    await expect(page.locator('.accounting-drilldown-panel')).toBeVisible();
    await expect(page.getByText('MitraBooks Dashboard')).toBeVisible();

    await page.locator('nav#nav a[data-business-workspace="parties"]').click();
    await expect(page.locator('.erp-workspace-panel')).toContainText('Parties');
    await expect(page.locator('.erp-workspace-panel').getByRole('button', { name: '+ New Party' })).toBeVisible();

    await page.locator('nav#nav a[data-business-workspace="vouchers"]').click();
    await expect(page.locator('.erp-workspace-panel')).toContainText('Vouchers');
    await expect(page.getByRole('button', { name: '+ New Voucher' })).toBeVisible();

    await page.getByRole('button', { name: '+ New Voucher' }).click();
    await expect(page.locator('#business-voucher-create-dialog')).toBeVisible();
    await expect(page.locator('.voucher-line')).toHaveCount(2);
    await expect(page.locator('.voucher-balance-panel')).toBeVisible();
    await expect(page.locator('#business-voucher-balance')).toHaveClass(/imbalanced/);
    await expect(page.locator('#business-voucher-submit')).toBeDisabled();

    await page.locator('#business-voucher-create-close').click();
    await page.locator('nav#nav a[data-business-workspace="accounting"]').click();
    await expect(page.locator('.accounting-drilldown-panel')).toBeVisible();
    await expect(page.locator('.accounting-drilldown-panel')).toContainText('Monthly Voucher Drill Down');
  });
});
