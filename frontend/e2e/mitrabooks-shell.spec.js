const { test, expect } = require('@playwright/test');

async function mockVerifiedMitraBooksSession(page) {
  await page.route('**/health', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ status: 'ok' }),
  }));
  await page.route('**/api/v1/modules/me', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      tenant_id: 'demo-mitrabooks-business',
      tenant_name: 'Acme Corp Ltd',
      organization_type: 'BUSINESS',
      role: 'tenant_admin',
      enabled_modules: [
        { module_key: 'business', display_name: 'MitraBooks Business Operations', frontend_path: '/business', enabled: true },
        { module_key: 'accounting', display_name: 'MitraBooks Accounting Engine', frontend_path: '/accounting', enabled: true },
        { module_key: 'audit', display_name: 'Audit Log', frontend_path: '/audit', enabled: true },
      ],
      available_modules: [],
    }),
  }));
  await page.route('**/api/v1/accounting/accounts', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify([
      { id: 'cash', code: '1001', name: 'Cash in Hand', account_type: 'asset' },
      { id: 'sales', code: '4001', name: 'Sales', account_type: 'revenue' },
      { id: 'expense', code: '5001', name: 'Office Expense', account_type: 'expense' },
    ]),
  }));
  await page.route('**/api/v1/business/parties**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ items: [{ id: 'p1', party_name: 'Karnataka Office Supplies', party_type: 'vendor', gstin: '29ABCDE1234F1Z5' }] }),
  }));
  await page.route('**/api/v1/business/vouchers**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ items: [] }),
  }));
  await page.route('**/api/v1/accounting/reports/drilldown**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ summary: { voucher_count: 0 }, items: [] }),
  }));
}

test.describe('MitraBooks ERP static shell', () => {
  test('shows login validation and password toggle before sign in', async ({ page }) => {
    await page.goto('/mitrabooks-erp/');

    await expect(page.locator('#access-panel')).toBeVisible();
    await expect(page.locator('.erp-sidebar')).toBeHidden();
    await expect(page.locator('#login-error-field')).toBeHidden();

    await page.locator('#login-submit').click();
    await expect(page.locator('#login-error-field')).toBeVisible();
    await expect(page.locator('#login-error-message')).toContainText('Email and password are required.');

    await page.locator('#login-password').fill('admin123');
    await expect(page.locator('#login-password')).toHaveAttribute('type', 'password');
    await page.locator('#toggle-password').click();
    await expect(page.locator('#login-password')).toHaveAttribute('type', 'text');
    await expect(page.locator('#toggle-password')).toHaveAttribute('aria-pressed', 'true');
  });

  test('keeps login page visible when cached token has no tenant session', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('sanmitra_frontend_access_token', 'stale-local-preview-token');
      window.localStorage.setItem('sanmitra_mitrabooks_login_email', 'businessadmin@sanmitra.local');
    });
    await page.route('**/health', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok' }),
    }));
    await page.route('**/api/v1/modules/me', route => route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Unauthorized' }),
    }));

    await page.goto('/mitrabooks-erp/');

    await expect(page.locator('#access-panel')).toBeVisible();
    await expect(page.locator('.erp-sidebar')).toBeHidden();
    await expect(page.locator('#session-pill')).toContainText('Not signed in');
    await expect(page.locator('#login-status')).toContainText('Sign in required');
    await expect.poll(() => page.evaluate(() => window.localStorage.getItem('sanmitra_frontend_access_token'))).toBeNull();
  });

  test('loads dashboard and opens core workspaces', async ({ page }) => {
    await mockVerifiedMitraBooksSession(page);
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
    await expect(page.locator('#context-cards')).toBeHidden();
    await expect(page.locator('.business-dashboard')).toBeVisible();
    const layout = await page.evaluate(() => {
      const topbar = document.querySelector('.erp-topbar')?.getBoundingClientRect();
      const executiveDashboard = document.querySelector('.executive-dashboard')?.getBoundingClientRect();
      return {
        topbarTop: topbar?.top ?? 0,
        executiveTop: executiveDashboard?.top ?? 0,
        executiveLeft: executiveDashboard?.left ?? 0,
        executiveWidth: executiveDashboard?.width ?? 0,
      };
    });
    expect(layout.topbarTop).toBeLessThan(layout.executiveTop);
    expect(layout.executiveLeft).toBeLessThan(420);
    expect(layout.executiveWidth).toBeGreaterThan(700);
    await expect(page.locator('.executive-dashboard')).toBeVisible();
    await expect(page.locator('.executive-dashboard')).toContainText('Sales & Expenses Trend');
    await expect(page.locator('.executive-dashboard')).toContainText('CEO Insights');
    await expect(page.locator('.finance-chart')).toBeVisible();
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
