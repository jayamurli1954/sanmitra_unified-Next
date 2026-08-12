import { chromium } from '@playwright/test';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const ROOT = path.resolve(__dirname, '..', '..');
const IMG_DIR = path.join(ROOT, 'docs', 'User_manual_screenshots');
if (!fs.existsSync(IMG_DIR)) {
  fs.mkdirSync(IMG_DIR, { recursive: true });
}

const TARGET_URL = 'http://127.0.0.1:3300/mitrabooks-erp/index.html';

function fulfillJson(route, body, status = 200) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  });
}

async function mockVerifiedMitraBooksSession(page) {
  await page.route('**/health', route => fulfillJson(route, { status: 'ok' }));

  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const parsedUrl = new globalThis.URL(request.url());
    const pathName = parsedUrl.pathname;

    if (pathName === '/api/v1/auth/session') {
      return fulfillJson(route, {
        authenticated: true,
        user: { email: 'businessadmin@sanmitra.local', name: 'Business Admin', role: 'tenant_admin' },
        tenant: { id: 'demo-mitrabooks-business', name: 'Demo Business Tenant', app_key: 'mitrabooks' }
      });
    }

    if (pathName === '/api/v1/tenants/current') {
      return fulfillJson(route, {
        tenant_id: 'demo-mitrabooks-business',
        name: 'Demo Business Tenant',
        organization_type: 'BUSINESS',
        enabled_modules: ['mitrabooks', 'office_ai', 'hr', 'manufacturing']
      });
    }

    if (pathName === '/api/v1/modules' || pathName === '/api/v1/modules/me') {
      return fulfillJson(route, {
        success: true,
        payload: {
          enabled_modules: [
            { module_key: 'overview', display_name: 'Executive Dashboard', nav_group: 'Main Workspaces', frontend_path: '/overview', enabled: true, icon: '▦' },
            { module_key: 'parties', display_name: 'Parties', nav_group: 'Main Workspaces', frontend_path: '/parties', enabled: true, icon: '●' },
            { module_key: 'vouchers', display_name: 'Vouchers & Posting', nav_group: 'Core Ledger', frontend_path: '/vouchers', enabled: true, icon: '📄' },
            { module_key: 'coa', display_name: 'Chart of Accounts', nav_group: 'Core Ledger', frontend_path: '/accounting/coa', enabled: true, icon: '📂' },
            { module_key: 'sales', display_name: 'Sales Invoices', nav_group: 'Income (Sales)', frontend_path: '/business/sales', enabled: true, icon: '💰' },
            { module_key: 'accounting', display_name: 'Trial Balance & Accounting', nav_group: 'Intelligence & Reports', frontend_path: '/accounting', enabled: true, icon: '📊' },
            { module_key: 'hr', display_name: 'HR & Payroll', nav_group: 'Configuration & Extensions', frontend_path: '/hr', enabled: true, icon: '👥' },
            { module_key: 'manufacturing', display_name: 'Manufacturing & Cost Centres', nav_group: 'Configuration & Extensions', frontend_path: '/manufacturing', enabled: true, icon: '🏭' }
          ]
        }
      });
    }

    if (pathName === '/api/v1/officemitra/brief') {
      return fulfillJson(route, {
        success: true,
        brief: {
          summary: 'AI-curated operational highlights & priority digests.',
          pending_tasks: 3,
          unread_emails: 2,
          high_priority_items: ['GST Filing due in 4 days', 'Vendor Payment pending approval']
        }
      });
    }

    if (pathName === '/api/v1/accounting/accounts') {
      return fulfillJson(route, [
        { account_id: 101, code: '11001', name: 'Cash in Hand', type: 'asset', balance: '1400.00' },
        { account_id: 102, code: '11010', name: 'HDFC Bank Account', type: 'asset', balance: '587770.00' },
        { account_id: 103, code: '12001', name: 'Sundry Debtors', type: 'asset', balance: '313970.00' },
        { account_id: 104, code: '21001', name: 'Sundry Creditors', type: 'liability', balance: '176440.00' },
        { account_id: 105, code: '41001', name: 'Sales Revenue', type: 'income', balance: '381500.00' },
        { account_id: 106, code: '51001', name: 'Purchase Expenses', type: 'expense', balance: '236350.00' }
      ]);
    }

    if (pathName === '/api/v1/accounting/reports/drilldown') {
      return fulfillJson(route, {
        success: true,
        period: 'FY 2026-27',
        level: 'month',
        breadcrumbs: ['All Months', 'June 2026'],
        summary: { total_debit: 381500.00, total_credit: 381500.00, net_balance: 0.00, voucher_count: 14 },
        items: [
          { date: '2026-06-01', voucher_no: 'PV-2026-001', particulars: 'Office Rent Payment', debit: 45000, credit: 0 },
          { date: '2026-06-05', voucher_no: 'RV-2026-008', particulars: 'Customer Receipt - Zenith', debit: 0, credit: 125000 },
          { date: '2026-06-12', voucher_no: 'JV-2026-012', particulars: 'Depreciation Adjustment', debit: 12000, credit: 12000 }
        ]
      });
    }

    if (pathName === '/api/v1/parties') {
      return fulfillJson(route, [
        { party_id: 'P001', name: 'Zenith Manufacturing Ltd', party_type: 'customer', gstin: '29ABCDE1234F1Z5', city: 'Bengaluru', outstanding: '125000.00' },
        { party_id: 'P002', name: 'Blue Ocean Exports Pvt Ltd', party_type: 'customer', gstin: '29BCDEF2345G2Z6', city: 'Mumbai', outstanding: '85000.00' }
      ]);
    }

    return fulfillJson(route, {});
  });
}

async function gotoWorkspace(page, workspaceKey, fileName) {
  console.log(`Navigating to workspace: ${workspaceKey}...`);
  await page.evaluate((ws) => {
    if (typeof window.setBusinessWorkspace === 'function') {
      window.setBusinessWorkspace(ws);
    } else {
      const link = document.querySelector(`a[data-business-workspace="${ws}"]`);
      if (link) link.click();
    }
  }, workspaceKey);
  await page.waitForTimeout(2000);
  const title = await page.locator('#view-title').textContent();
  console.log(`  -> Workspace view title: "${title}"`);
  await page.screenshot({ path: path.join(IMG_DIR, fileName) });
}

async function run() {
  const browser = await chromium.launch({ headless: true });

  // 1. Unauthenticated context for login page screenshot
  console.log('Capturing 02-1-login.png...');
  const loginContext = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 });
  const loginPage = await loginContext.newPage();
  await loginPage.goto(TARGET_URL);
  await loginPage.waitForSelector('#access-panel', { timeout: 15000 });
  await loginPage.screenshot({ path: path.join(IMG_DIR, '02-1-login.png') });
  await loginContext.close();

  // 2. Authenticated context with initScript for all workspace screens
  console.log('Capturing Executive Dashboard & Workspace views...');
  const authContext = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 });
  await authContext.addInitScript(() => {
    window.sessionStorage.setItem('sanmitra_frontend_access_token', 'static-shell-token');
    window.localStorage.setItem('sanmitra_mitrabooks_login_email', 'businessadmin@sanmitra.local');
    window.localStorage.removeItem('mitrabooks-widget-states');
  });

  const page = await authContext.newPage();
  page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
  page.on('pageerror', err => console.error('BROWSER ERROR:', err));

  await mockVerifiedMitraBooksSession(page);

  await page.goto(TARGET_URL);
  await page.waitForSelector('.dashboard-quick-execution-bar', { state: 'attached', timeout: 30000 });
  await page.waitForTimeout(2000);

  const dashTitle = await page.locator('#view-title').textContent();
  console.log(`  -> Dashboard title: "${dashTitle}"`);

  await page.screenshot({ path: path.join(IMG_DIR, '03-dashboard.png') });
  await page.screenshot({ path: path.join(IMG_DIR, '2.png') });
  await page.screenshot({ path: path.join(IMG_DIR, '02-2-workspace-layout.png') });

  console.log('Capturing Navigation Groups (2.3 Navigation Groups.png)...');
  const sidebar = page.locator('aside.sidebar');
  if (await sidebar.isVisible()) {
    await sidebar.screenshot({ path: path.join(IMG_DIR, '2.3 Navigation Groups.png') });
  }

  console.log('Capturing Add Party Form (04-1-add-party.png)...');
  await page.evaluate(() => document.getElementById('business-party-create-dialog')?.showModal());
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(IMG_DIR, '04-1-add-party.png') });
  await page.evaluate(() => document.getElementById('business-party-create-dialog')?.close());
  await page.waitForTimeout(500);

  console.log('Capturing Create Voucher Form (12-2-journal-post.png)...');
  await page.evaluate(() => document.getElementById('business-voucher-create-dialog')?.showModal());
  await page.waitForTimeout(1000);
  await page.selectOption('#business-voucher-type-select', 'payment');
  await page.waitForTimeout(500);
  if (await page.locator('#voucher-pv-amount').isVisible()) {
    await page.fill('#voucher-pv-amount', '50000');
    await page.dispatchEvent('#voucher-pv-amount', 'input');
  }
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(IMG_DIR, '12-2-journal-post.png') });
  await page.evaluate(() => document.getElementById('business-voucher-create-dialog')?.close());
  await page.waitForTimeout(500);

  // Navigate to distinct workspaces and capture unique screens
  await gotoWorkspace(page, 'coa', '12-1-coa.png');
  await gotoWorkspace(page, 'sales', '05-1-create-invoice.png');
  await page.screenshot({ path: path.join(IMG_DIR, '05-3-invoice-list.png') });
  await gotoWorkspace(page, 'accounting', '13-1-trial-balance.png');
  await gotoWorkspace(page, 'hr', '22-hr-workspace.png');
  await gotoWorkspace(page, 'manufacturing', '23-mfg-workspace.png');

  await browser.close();
  console.log('SUCCESS: All Node Playwright screenshots captured with unique workspace titles!');
}

run().catch(err => {
  console.error('ERROR capturing screenshots:', err);
  process.exit(1);
});
