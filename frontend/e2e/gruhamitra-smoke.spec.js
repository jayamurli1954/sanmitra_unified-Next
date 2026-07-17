const { test, expect } = require('@playwright/test');

const demoUser = {
  id: 'gm-e2e-admin',
  email: 'gruhamitra.e2e@example.test',
  name: 'GruhaMitra E2E Admin',
  role: 'Admin',
  tenant_id: 'gruhamitra-demo-society',
  society_id: 'gruhamitra-demo-society',
  society_name: 'GruhaMitra Demo Society',
};

async function seedAuthenticatedGruhaSession(page) {
  await page.addInitScript((user) => {
    window.sessionStorage.setItem('access_token', 'playwright-gruhamitra-demo-token');
    window.sessionStorage.setItem('backend_auth_active', 'true');
    window.localStorage.setItem('gruhamitra_tenant_id', user.society_id);
    window.localStorage.setItem('user', JSON.stringify(user));
  }, demoUser);
}

async function mockGruhaApi(page) {
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace(/^\/api\/v1/, '');
    const method = request.method();

    const json = (body, status = 200) => route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });

    if (method === 'GET' && path === '/auth/me') {
      return json(demoUser);
    }

    if (method === 'GET' && path === '/dashboard/summary') {
      return json({
        admin_stats: {
          society_balance: 125000,
          monthly_billing: 50756,
          dues_pending: 45341,
          complaints_open: 2,
          collection_trend: [
            { month: 'Apr', amount: 42000 },
            { month: 'May', amount: 50756 },
          ],
        },
        recent_activities: [
          {
            id: 'activity-1',
            title: 'Maintenance bill generated',
            description: 'Demo April billing cycle',
            icon: 'bill',
          },
        ],
      });
    }

    if (method === 'GET' && path === '/society/gruhamitra-demo-society') {
      return json({
        id: 'gruhamitra-demo-society',
        name: 'GruhaMitra Demo Society',
        address: 'Demo Layout',
      });
    }

    if (method === 'GET' && path.startsWith('/messages/rooms')) {
      if (path.includes('/messages')) {
        return json([]);
      }
      return json([]);
    }

    if (method === 'GET' && path.startsWith('/maintenance/bills')) {
      return json([]);
    }

    if (method === 'GET' && path.startsWith('/maintenance/expense-accounts-for-period')) {
      return json([]);
    }

    if (method === 'GET' && path === '/flats') {
      return json([
        {
          id: 'flat-a-101',
          flat_number: 'A-101',
          block: 'A',
          owner_name: 'Demo Owner',
        },
      ]);
    }

    if (method === 'GET' && path.startsWith('/member-onboarding')) {
      return json([]);
    }

    if (method === 'GET' && path.startsWith('/complaints')) {
      return json([]);
    }

    if (method === 'GET' && path.startsWith('/meetings')) {
      return json([]);
    }

    if (method === 'GET' && path.startsWith('/settings/society')) {
      return json({
        society_profile: { name: 'GruhaMitra Demo Society' },
        billing_rules: {},
        late_fee_rules: {},
      });
    }

    if (method === 'GET' && path.startsWith('/users')) {
      return json([]);
    }

    if (method === 'GET' && path.startsWith('/database/backups')) {
      return json([]);
    }

    if (method === 'GET' && path.startsWith('/assets')) {
      return json([]);
    }

    if (method === 'GET' && path.startsWith('/accounting/accounts')) {
      return json([]);
    }

    if (method === 'GET' && (
      path.includes('/reports/trial-balance') ||
      path.includes('/reports/ledger') ||
      path.includes('/reports/balance-sheet') ||
      path.includes('/reports/income-and-expenditure') ||
      path.includes('/reports/receipts-and-payments')
    )) {
      return json({
        rows: [],
        accounts: [],
        totals: { debit: 0, credit: 0 },
      });
    }

    if (method === 'GET' && path.startsWith('/transactions')) {
      return json([]);
    }

    if (method === 'GET' && path.startsWith('/financial-years')) {
      return json([]);
    }

    if (method === 'POST' || method === 'PUT' || method === 'DELETE') {
      return json({ ok: true, id: 'playwright-mock' });
    }

    return json({});
  });
}

test.describe('GruhaMitra public PWA smoke', () => {
  test('landing page exposes core product, pricing, and entry points', async ({ page, request }) => {
    const manifest = await request.get('/gruhamitra/manifest.json');
    expect(manifest.ok()).toBeTruthy();

    await page.goto('/gruhamitra/');

    await expect(page.getByRole('heading', { name: /run your rwa or apartment society/i })).toBeVisible();
    await expect(page.getByLabel('GruhaMitra entry actions').getByRole('link', { name: /^Login$/i })).toBeVisible();
    await expect(page.getByLabel('GruhaMitra entry actions').getByRole('link', { name: /^Register$/i })).toBeVisible();
    await expect(page.getByLabel('GruhaMitra entry actions').getByRole('link', { name: /request demo/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /Maintenance Billing/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /MitraBooks Accounting/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /^Starter$/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /^Growth$/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /^Professional$/i })).toBeVisible();
  });

  test('login and onboarding routes render without authentication', async ({ page }) => {
    await page.goto('/gruhamitra/');
    await page.getByLabel('GruhaMitra entry actions').getByRole('link', { name: /^Login$/i }).click();
    await expect(page.getByRole('heading', { name: /^GruhaMitra$/i })).toBeVisible();
    await expect(page.getByPlaceholder(/enter your email/i)).toBeVisible();
    await expect(page.getByPlaceholder(/enter your password/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /^login$/i })).toBeVisible();

    await page.getByRole('link', { name: /onboard society/i }).click();
    await expect(page.locator('body')).toContainText(/society|register|onboard/i);

    await page.goto('/gruhamitra/');
    await page.getByLabel('GruhaMitra entry actions').getByRole('link', { name: /^Register$/i }).click();
    await expect(page.locator('body')).toContainText(/society|register|onboard|demo/i);
  });
});

test.describe('GruhaMitra authenticated shell smoke', () => {
  test.beforeEach(async ({ page }) => {
    await seedAuthenticatedGruhaSession(page);
    await mockGruhaApi(page);
  });

  test('dashboard opens with core metrics and quick actions', async ({ page }) => {
    await page.goto('/gruhamitra/');

    await expect(page.getByText(/GruhaMitra Demo Society/i)).toBeVisible();
    await expect(page.getByText(/Society Balance/i)).toBeVisible();
    await expect(page.getByText(/This Month Billing/i)).toBeVisible();
    await expect(page.getByText(/Dues Pending/i)).toBeVisible();
    await expect(page.getByText(/Complaints Open/i)).toBeVisible();

    for (const action of [
      'Accounting',
      'Generate Bills',
      'Members',
      'Complaints',
      'Reports',
      'Message',
      'Meeting',
      'Settings',
    ]) {
      await expect(page.getByRole('button', { name: action, exact: true })).toBeVisible();
    }
  });

  test('core authenticated routes load without route-level crashes', async ({ page }) => {
    const routes = [
      ['Generate Bills', /maintenance|bill|generate/i],
      ['Accounting', /accounting|ledger|trial balance|voucher/i],
      ['Members', /member|owner|tenant|resident/i],
      ['Complaints', /complaint|service request/i],
      ['Reports', /report|ledger|trial balance|dues/i],
      ['Message', /message|notice|room/i],
      ['Meeting', /meeting|minutes|notice/i],
      ['Settings', /settings|society|billing/i],
    ];

    for (const [action, expectedText] of routes) {
      await page.goto('/gruhamitra/');
      await expect(page.getByRole('button', { name: action, exact: true })).toBeVisible();
      await page.getByRole('button', { name: action, exact: true }).click();
      await expect(page.locator('body')).toContainText(expectedText);
      await expect(page.locator('body')).not.toContainText(/something went wrong|runtime error/i);
    }
  });
});
