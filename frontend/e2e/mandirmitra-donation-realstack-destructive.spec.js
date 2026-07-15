const { test, expect } = require('@playwright/test');

const expectedDemoTenantId = (process.env.MANDIRMITRA_DEMO_TENANT_ID || '').trim();
const email = process.env.MANDIRMITRA_E2E_USER_EMAIL || '';
const password = process.env.MANDIRMITRA_E2E_USER_PASSWORD || '';
const confirmation = process.env.MANDIRMITRA_DEMO_E2E_CONFIRM || '';
const runDestructive = process.env.MANDIRMITRA_RUN_DESTRUCTIVE_E2E === 'true';
const hundiMakerEmail = process.env.MANDIRMITRA_E2E_MAKER_EMAIL || '';
const hundiMakerPassword = process.env.MANDIRMITRA_E2E_MAKER_PASSWORD || '';
const baseUrl = (process.env.E2E_BASE_URL || process.env.PLAYWRIGHT_BASE_URL || '').replace(/\/+$/, '');
const apiBaseUrl = (process.env.E2E_API_BASE_URL || '').replace(/\/+$/, '');

function safeUrl(value) {
  try {
    return new URL(value);
  } catch (_error) {
    return null;
  }
}

function isAllowedDestructiveTarget(value) {
  const target = safeUrl(value);
  if (!target) return false;
  return target.protocol === 'https:' || ['127.0.0.1', 'localhost'].includes(target.hostname);
}

function expectedConfirmation() {
  const apiTarget = safeUrl(apiBaseUrl);
  return expectedDemoTenantId && apiTarget
    ? `DESTROY_DEMO_ONLY:${expectedDemoTenantId}@${apiTarget.origin}`
    : '';
}

function requireDemoGate() {
  return Boolean(
    runDestructive
      && email
      && password
      && hundiMakerEmail
      && hundiMakerPassword
      && email.toLowerCase() !== hundiMakerEmail.toLowerCase()
      && expectedDemoTenantId
      && /(?:demo|test|seed)/i.test(expectedDemoTenantId)
      && baseUrl
      && apiBaseUrl
      && isAllowedDestructiveTarget(baseUrl)
      && isAllowedDestructiveTarget(apiBaseUrl)
      && confirmation === expectedConfirmation()
  );
}

function apiBaseFromPage(page) {
  if (apiBaseUrl) return `${apiBaseUrl}/api/v1`;
  const current = new URL(page.url());
  if (['127.0.0.1', 'localhost'].includes(current.hostname) && current.port === '3300') {
    return `${current.protocol}//${current.hostname}:8000/api/v1`;
  }
  return `${current.origin}/api/v1`;
}

function headers(token, appKey = 'mandirmitra') {
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', 'X-App-Key': appKey };
}

const loginTokenCache = new Map();

async function login(page, loginEmail = email, loginPassword = password) {
  const cacheKey = `${String(loginEmail || '').trim().toLowerCase()}@${apiBaseUrl}`;
  if (loginTokenCache.has(cacheKey)) {
    return loginTokenCache.get(cacheKey);
  }
  const response = await page.request.post(`${apiBaseFromPage(page)}/auth/local-login`, {
    headers: { 'Content-Type': 'application/json', 'X-App-Key': 'mandirmitra' },
    data: { email: loginEmail, password: loginPassword },
  });
  const payload = await response.json().catch(() => ({}));
  expect(response.ok(), `MandirMitra login failed: HTTP ${response.status()}`).toBeTruthy();
  expect(payload.access_token).toBeTruthy();
  loginTokenCache.set(cacheKey, payload.access_token);
  return payload.access_token;
}

function safeResponseDetail(payload) {
  const detail = typeof payload?.detail === 'string'
    ? payload.detail.replace(/[\r\n]+/g, ' ').slice(0, 200)
    : '';
  return detail ? ` detail=${detail}` : '';
}

async function jsonRequest(page, token, method, path, body = undefined, appKey = 'mandirmitra') {
  const response = await page.request.fetch(`${apiBaseFromPage(page)}${path}`, {
    method, headers: headers(token, appKey), data: body,
  });
  const payload = await response.json().catch(() => ({}));
  expect(response.ok(), `${method} ${path} failed: HTTP ${response.status()}${safeResponseDetail(payload)}`).toBeTruthy();
  return payload;
}

async function assertDemoIdentity(page, token, label) {
  const identity = await jsonRequest(page, token, 'GET', '/auth/me');
  const modules = await jsonRequest(page, token, 'GET', '/modules/me');
  const temple = await jsonRequest(page, token, 'GET', '/temples/current');
  expect(identity.tenant_id, `${label} token tenant mismatch`).toBe(expectedDemoTenantId);
  expect(identity.app_key, `${label} token app mismatch`).toBe('mandirmitra');
  expect(
    identity.is_superuser === true || identity.role === 'super_admin',
    `${label} must not use platform-owner override`,
  ).toBe(false);
  expect(['tenant_admin', 'admin']).toContain(String(identity.role || '').toLowerCase());
  expect(modules.tenant_id, `${label} module tenant mismatch`).toBe(expectedDemoTenantId);
  expect(modules.organization_type).toBe('TEMPLE');
  expect(modules.is_platform_owner).toBe(false);
  const enabled = new Set((modules.enabled_modules || []).map((row) => row.module_key));
  for (const key of ['temple', 'accounting', 'audit']) expect(enabled.has(key)).toBeTruthy();
  expect(temple.tenant_id, `${label} temple tenant mismatch`).toBe(expectedDemoTenantId);
  expect(temple.is_placeholder, `${label} demo temple must be persisted`).not.toBe(true);
  expect(temple.platform_can_write, `${label} tenant is not explicitly marked demo-writable`).toBe(true);
  return String(identity.sub || '');
}

// Traces and videos can retain authorization headers and login request bodies.
test.use({ trace: 'off', video: 'off' });

test.describe('MandirMitra donation destructive real-stack demo E2E', () => {
  test.describe.configure({ mode: 'serial' });
  test.skip(!requireDemoGate(), 'Set explicit demo tenant, target-bound confirmation, and distinct credentials.');

  let approverToken = '';
  let makerToken = '';
  let approverId = '';
  let makerId = '';

  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto(baseUrl || '/mitrabooks-erp/');
    approverToken = await login(page);
    makerToken = await login(page, hundiMakerEmail, hundiMakerPassword);
    approverId = await assertDemoIdentity(page, approverToken, 'Approver');
    makerId = await assertDemoIdentity(page, makerToken, 'Maker');
    expect(approverId).toBeTruthy();
    expect(makerId).toBeTruthy();
    expect(makerId, 'Maker and approver must resolve to distinct authenticated actors').not.toBe(approverId);
    await context.close();
  });

  test.beforeEach(async ({ page }) => {
    await page.goto(baseUrl || '/mitrabooks-erp/');
  });

  test('creates a donation receipt, reports it, and reverses it safely', async ({ page }) => {
    await page.goto(baseUrl || '/mitrabooks-erp/');
    const token = await login(page);
    const runId = `${Date.now()}-${Math.floor(Math.random() * 10000)}`;
    const today = new Date().toISOString().slice(0, 10);
    const amount = '117.25';

    const modules = await jsonRequest(page, token, 'GET', '/modules/me');
    expect(modules.organization_type).toBe('TEMPLE');
    const enabled = new Set((modules.enabled_modules || []).map((row) => row.module_key));
    for (const key of ['temple', 'accounting', 'audit']) expect(enabled.has(key)).toBeTruthy();

    const donation = await jsonRequest(page, token, 'POST', '/donations', {
      amount,
      category: 'General Donation',
      donation_type: 'cash',
      payment_mode: 'Cash',
      devotee_name: `E2E Donor ${runId}`,
      notes: `Guarded MandirMitra donation gate ${runId}`,
    });
    const donationId = donation.donation_id || donation.id;
    expect(donationId).toBeTruthy();
    expect(donation.receipt_number).toBeTruthy();
    expect(Number(donation.amount)).toBeCloseTo(Number(amount), 2);

    const receipt = await page.request.get(`${apiBaseFromPage(page)}/donations/${donationId}/receipt/pdf`, {
      headers: headers(token),
    });
    expect(receipt.ok(), `Receipt PDF failed: ${receipt.status()}`).toBeTruthy();
    expect(receipt.headers()['content-type']).toContain('application/pdf');
    expect((await receipt.body()).subarray(0, 4).toString()).toBe('%PDF');

    const detailed = await jsonRequest(page, token, 'GET', `/reports/donations/detailed?from_date=${today}&to_date=${today}`);
    expect(JSON.stringify(detailed)).toContain(donation.receipt_number);
    expect(JSON.stringify(detailed)).toContain(runId);

    const accountingReport = await jsonRequest(
      page, token, 'GET', `/journal-entries/reports/receipts-payments?from_date=${today}&to_date=${today}`,
    );
    expect(JSON.stringify(accountingReport)).toContain('117.25');

    const wrongApp = await page.request.get(`${apiBaseFromPage(page)}/donations?limit=5`, {
      headers: headers(token, 'mitrabooks'),
    });
    expect(wrongApp.status()).toBe(403);

    const reversed = await jsonRequest(page, token, 'POST', `/donations/${donationId}/cancel`, {
      reason: `Guarded E2E reversal ${runId}`,
    });
    expect(String(reversed.status).toLowerCase()).toBe('reversed');
    expect(reversed.reversal_journal_id).toBeTruthy();
    expect(reversed.cancellation_reason).toContain(runId);

    const repeated = await jsonRequest(page, token, 'POST', `/donations/${donationId}/cancel`, {
      reason: `Repeated guarded E2E reversal ${runId}`,
    });
    expect(repeated._idempotent).toBe(true);
    expect(repeated.reversal_journal_id).toBe(reversed.reversal_journal_id);
  });

  test('maker-checker approves, reports, settles, and idempotently retries a receipt refund', async ({ page }) => {
    test.skip(!hundiMakerEmail || !hundiMakerPassword, 'Set distinct MandirMitra maker credentials.');
    await page.goto(baseUrl || '/mitrabooks-erp/');
    const approverToken = await login(page);
    const makerToken = await login(page, hundiMakerEmail, hundiMakerPassword);
    const runId = `${Date.now()}-${Math.floor(Math.random() * 10000)}`;
    const today = new Date().toISOString().slice(0, 10);

    const donation = await jsonRequest(page, approverToken, 'POST', '/donations', {
      amount: '89.65',
      category: 'General Donation',
      donation_type: 'cash',
      payment_mode: 'Cash',
      devotee_name: `E2E Refund Donor ${runId}`,
      notes: `Guarded refund source ${runId}`,
    });
    const donationId = donation.donation_id || donation.id;

    const refund = await jsonRequest(page, makerToken, 'POST', '/refund-requests', {
      source_kind: 'donation',
      source_id: donationId,
      amount: '89.65',
      reason: `E2E duplicate receipt correction ${runId}`,
      refund_mode: 'Cash',
    });
    expect(refund.status).toBe('pending_approval');
    expect(refund.amount).toBe('89.65');

    const makerApproval = await page.request.post(
      `${apiBaseFromPage(page)}/refund-requests/${refund.id}/approve`,
      { headers: headers(makerToken) },
    );
    expect(makerApproval.status()).toBe(409);

    const approved = await jsonRequest(
      page, approverToken, 'POST', `/refund-requests/${refund.id}/approve`,
    );
    expect(approved.status).toBe('approved_pending_settlement');
    expect(approved.approved_by).not.toBe(refund.created_by);

    const queue = await jsonRequest(
      page, approverToken, 'GET', '/refund-requests?status=approved_pending_settlement',
    );
    expect(queue.some((row) => row.id === refund.id)).toBe(true);

    const report = await jsonRequest(
      page, approverToken, 'GET', `/reports/refunds?from_date=${today}&to_date=${today}`,
    );
    expect(report.items.some((row) => row.id === refund.id)).toBe(true);
    expect(report.amount_by_status.approved_pending_settlement).toBeGreaterThanOrEqual(89.65);

    const exportResponse = await page.request.get(
      `${apiBaseFromPage(page)}/reports/refunds/export.csv?from_date=${today}&to_date=${today}`,
      { headers: headers(approverToken) },
    );
    expect(exportResponse.ok()).toBeTruthy();
    expect(exportResponse.headers()['content-type']).toContain('text/csv');
    expect(await exportResponse.text()).toContain(refund.reference);

    const settlementReference = `CASH-RFD-${runId}`;
    const settled = await jsonRequest(
      page, approverToken, 'POST', `/refund-requests/${refund.id}/settle`,
      { refund_mode: 'Cash', refund_reference: settlementReference, settlement_date: today },
    );
    expect(settled.status).toBe('settled');
    expect(settled.reversal_journal_id).toBeTruthy();
    expect(settled.refund_reference).toBe(settlementReference);

    const repeated = await jsonRequest(
      page, approverToken, 'POST', `/refund-requests/${refund.id}/settle`,
      { refund_mode: 'Cash', refund_reference: settlementReference, settlement_date: today },
    );
    expect(repeated._idempotent).toBe(true);
    expect(repeated.reversal_journal_id).toBe(settled.reversal_journal_id);

    const wrongApp = await page.request.get(`${apiBaseFromPage(page)}/refund-requests`, {
      headers: headers(approverToken, 'mitrabooks'),
    });
    expect(wrongApp.status()).toBe(403);
  });

  test('books a paid seva, reports it, and reverses the receipt safely', async ({ page }) => {
    await page.goto(baseUrl || '/mitrabooks-erp/');
    const token = await login(page);
    const runId = `${Date.now()}-${Math.floor(Math.random() * 10000)}`;
    const today = new Date().toISOString().slice(0, 10);
    const amount = '63.75';

    const booking = await jsonRequest(page, token, 'POST', '/sevas/bookings', {
      seva_name: `E2E Archana ${runId}`,
      booking_date: today,
      amount_paid: amount,
      payment_mode: 'Cash',
      payment_status: 'paid',
      devotee_name: `E2E Seva Devotee ${runId}`,
      special_request: `Guarded seva gate ${runId}`,
    });
    expect(booking.id).toBeTruthy();
    expect(booking.receipt_number).toBeTruthy();
    expect(String(booking.status).toLowerCase()).toBe('confirmed');
    expect(String(booking.payment_status).toLowerCase()).toBe('paid');
    expect(Number(booking.amount_paid)).toBeCloseTo(Number(amount), 2);

    const receipt = await page.request.get(`${apiBaseFromPage(page)}/sevas/bookings/${booking.id}/receipt/pdf`, {
      headers: headers(token),
    });
    expect(receipt.ok(), `Seva receipt PDF failed: ${receipt.status()}`).toBeTruthy();
    expect(receipt.headers()['content-type']).toContain('application/pdf');
    expect((await receipt.body()).subarray(0, 4).toString()).toBe('%PDF');

    const detailed = await jsonRequest(page, token, 'GET', `/reports/sevas/detailed?from_date=${today}&to_date=${today}`);
    expect(JSON.stringify(detailed)).toContain(booking.receipt_number);
    expect(JSON.stringify(detailed)).toContain(runId);
    expect(Number(detailed.total_amount)).toBeGreaterThanOrEqual(Number(amount));

    const schedule = await jsonRequest(page, token, 'GET', '/reports/sevas/schedule?days=1');
    expect(JSON.stringify(schedule)).toContain(runId);

    const accountingReport = await jsonRequest(
      page, token, 'GET', `/journal-entries/reports/receipts-payments?from_date=${today}&to_date=${today}`,
    );
    expect(accountingReport).toBeTruthy();

    const wrongApp = await page.request.get(`${apiBaseFromPage(page)}/sevas/bookings?limit=5`, {
      headers: headers(token, 'mitrabooks'),
    });
    expect(wrongApp.status()).toBe(403);

    const reversed = await jsonRequest(page, token, 'POST', `/sevas/bookings/${booking.id}/cancel`, {
      reason: `Guarded seva reversal ${runId}`,
    });
    expect(String(reversed.status).toLowerCase()).toBe('reversed');
    expect(reversed.reversal_journal_id).toBeTruthy();
    expect(reversed.cancellation_reason).toContain(runId);

    const repeated = await jsonRequest(page, token, 'POST', `/sevas/bookings/${booking.id}/cancel`, {
      reason: `Repeated guarded seva reversal ${runId}`,
    });
    expect(repeated._idempotent).toBe(true);
    expect(repeated.reversal_journal_id).toBe(reversed.reversal_journal_id);
  });

  test('posts validated fund and festival sponsorship designations and reports them', async ({ page }) => {
    await page.goto(baseUrl || '/mitrabooks-erp/');
    const token = await login(page);
    const runId = `${Date.now()}-${Math.floor(Math.random() * 10000)}`;
    const today = new Date().toISOString().slice(0, 10);

    const fund = await jsonRequest(page, token, 'POST', '/funds', {
      name: `E2E Gopuram Fund ${runId}`,
      fund_type: 'restricted',
    });
    const festival = await jsonRequest(page, token, 'POST', '/festivals', {
      name: `E2E Festival ${runId}`,
      start_date: today,
      end_date: today,
    });
    expect(fund.id).toBeTruthy();
    expect(festival.id).toBeTruthy();

    const donation = await jsonRequest(page, token, 'POST', '/donations', {
      amount: '131.45',
      category: 'General Donation',
      fund_id: fund.id,
      festival_id: festival.id,
      is_sponsorship: true,
      payment_mode: 'Cash',
      devotee_name: `E2E Sponsor ${runId}`,
    });
    expect(donation.fund_name).toBe(fund.name);
    expect(donation.festival_name).toBe(festival.name);
    expect(donation.income_category).toBe('Sponsorship Income');

    const fundReport = await jsonRequest(
      page, token, 'GET', `/reports/donations/fund-wise?from_date=${today}&to_date=${today}`,
    );
    const festivalReport = await jsonRequest(
      page, token, 'GET', `/reports/donations/festival-wise?from_date=${today}&to_date=${today}`,
    );
    expect(JSON.stringify(fundReport)).toContain(fund.id);
    expect(JSON.stringify(festivalReport)).toContain(festival.id);

    const wrongApp = await page.request.get(`${apiBaseFromPage(page)}/funds`, {
      headers: headers(token, 'mitrabooks'),
    });
    expect(wrongApp.status()).toBe(403);

    const reversed = await jsonRequest(page, token, 'POST', `/donations/${donation.id}/cancel`, {
      reason: `Guarded designated donation reversal ${runId}`,
    });
    expect(reversed.reversal_journal_id).toBeTruthy();
  });

  test('counts, maker-checker posts, reports, and reverses a hundi opening', async ({ page }) => {
    test.skip(!hundiMakerEmail || !hundiMakerPassword, 'Set distinct MandirMitra Hundi maker credentials.');
    await page.goto(baseUrl || '/mitrabooks-erp/');
    const approverToken = await login(page);
    const makerToken = await login(page, hundiMakerEmail, hundiMakerPassword);
    const runId = `${Date.now()}-${Math.floor(Math.random() * 10000)}`;
    const today = new Date().toISOString().slice(0, 10);
    const amount = '241.35';

    const master = await jsonRequest(page, approverToken, 'POST', '/hundi/masters', {
      name: `E2E Main Hundi ${runId}`,
      location: 'Guarded demo sanctum',
    });
    expect(master.id).toBeTruthy();

    const opening = await jsonRequest(page, makerToken, 'POST', '/hundi/openings', {
      hundi_id: master.id,
      amount,
      counted_on: today,
      witness: `E2E Trustee ${runId}`,
      fund: 'General Fund',
    });
    expect(opening.status).toBe('pending_approval');
    expect(opening.reference).toMatch(/^HUN-/);
    expect(opening.amount).toBe(amount);

    const posted = await jsonRequest(page, approverToken, 'POST', `/hundi/openings/${opening.id}/approve`);
    expect(posted.status).toBe('posted');
    expect(posted.journal_entry_id).toBeTruthy();
    expect(posted.approved_by).not.toBe(opening.created_by);

    const repeatedApproval = await jsonRequest(page, approverToken, 'POST', `/hundi/openings/${opening.id}/approve`);
    expect(repeatedApproval._idempotent).toBe(true);
    expect(repeatedApproval.journal_entry_id).toBe(posted.journal_entry_id);

    const openings = await jsonRequest(page, approverToken, 'GET', '/hundi/openings');
    expect(JSON.stringify(openings)).toContain(opening.reference);
    const accountingReport = await jsonRequest(
      page, approverToken, 'GET', `/journal-entries/reports/receipts-payments?from_date=${today}&to_date=${today}`,
    );
    expect(JSON.stringify(accountingReport)).toContain('241.35');

    const wrongApp = await page.request.get(`${apiBaseFromPage(page)}/hundi/openings`, {
      headers: headers(approverToken, 'mitrabooks'),
    });
    expect(wrongApp.status()).toBe(403);

    const reversed = await jsonRequest(page, approverToken, 'POST', `/hundi/openings/${opening.id}/cancel`, {
      reason: `Guarded hundi correction ${runId}`,
    });
    expect(reversed.status).toBe('reversed');
    expect(reversed.reversal_journal_id).toBeTruthy();

    const repeatedReversal = await jsonRequest(page, approverToken, 'POST', `/hundi/openings/${opening.id}/cancel`, {
      reason: `Repeated guarded hundi correction ${runId}`,
    });
    expect(repeatedReversal._idempotent).toBe(true);
    expect(repeatedReversal.reversal_journal_id).toBe(reversed.reversal_journal_id);
  });

  test('maker-checker transfers between fund subledgers and reverses safely', async ({ page }) => {
    test.skip(!hundiMakerEmail || !hundiMakerPassword, 'Set distinct MandirMitra maker credentials.');
    await page.goto(baseUrl || '/mitrabooks-erp/');
    const approverToken = await login(page);
    const makerToken = await login(page, hundiMakerEmail, hundiMakerPassword);
    const runId = `${Date.now()}-${Math.floor(Math.random() * 10000)}`;
    const today = new Date().toISOString().slice(0, 10);

    const source = await jsonRequest(page, approverToken, 'POST', '/funds', {
      name: `E2E General Fund ${runId}`,
      fund_type: 'general',
    });
    const destination = await jsonRequest(page, approverToken, 'POST', '/funds', {
      name: `E2E Restricted Fund ${runId}`,
      fund_type: 'restricted',
    });
    expect(source.accounting_dimension_id).toBeTruthy();
    expect(destination.accounting_dimension_id).toBeTruthy();

    const opening = await jsonRequest(page, makerToken, 'POST', '/fund-opening-balances', {
      fund_id: source.id,
      amount: '171.35',
      opening_date: today,
      reason: `E2E audited brought-forward balance ${runId}`,
    });
    expect(opening.status).toBe('pending_approval');
    const postedOpening = await jsonRequest(
      page, approverToken, 'POST', `/fund-opening-balances/${opening.id}/approve`,
    );
    expect(postedOpening.status).toBe('posted');
    expect(postedOpening.approved_by).not.toBe(opening.created_by);
    expect(postedOpening.journal_entry_id).toBeTruthy();

    const transfer = await jsonRequest(page, makerToken, 'POST', '/fund-transfers', {
      from_fund_id: source.id,
      to_fund_id: destination.id,
      amount: '71.35',
      transfer_date: today,
      reason: `E2E trustee allocation ${runId}`,
    });
    expect(transfer.status).toBe('pending_approval');
    expect(transfer.amount).toBe('71.35');

    const posted = await jsonRequest(page, approverToken, 'POST', `/fund-transfers/${transfer.id}/approve`);
    expect(posted.status).toBe('posted');
    expect(posted.journal_entry_id).toBeTruthy();
    expect(posted.approved_by).not.toBe(transfer.created_by);

    const repeatedApproval = await jsonRequest(
      page, approverToken, 'POST', `/fund-transfers/${transfer.id}/approve`,
    );
    expect(repeatedApproval._idempotent).toBe(true);
    expect(repeatedApproval.journal_entry_id).toBe(posted.journal_entry_id);

    const subledger = await jsonRequest(
      page, approverToken, 'GET', `/reports/funds/subledger?from_date=${today}&to_date=${today}`,
    );
    expect(JSON.stringify(subledger)).toContain(source.id);
    expect(JSON.stringify(subledger)).toContain(destination.id);
    expect(subledger.totals.transfers_in).toBeGreaterThanOrEqual(71.35);
    expect(subledger.totals.transfers_in).toBe(subledger.totals.transfers_out);
    const sourceRow = subledger.items.find((row) => row.fund_id === source.id);
    expect(sourceRow.opening_entries).toBeGreaterThanOrEqual(171.35);
    expect(sourceRow.closing_balance).toBeGreaterThanOrEqual(100.00);

    const asOf = await jsonRequest(page, approverToken, 'GET', `/reports/funds/as-of?as_of=${today}`);
    const asOfSource = asOf.items.find((row) => row.fund_id === source.id);
    expect(asOfSource.balance).toBeGreaterThanOrEqual(100.00);

    const wrongApp = await page.request.get(`${apiBaseFromPage(page)}/fund-transfers`, {
      headers: headers(approverToken, 'mitrabooks'),
    });
    expect(wrongApp.status()).toBe(403);

    const reversed = await jsonRequest(page, approverToken, 'POST', `/fund-transfers/${transfer.id}/cancel`, {
      reason: `Guarded fund transfer correction ${runId}`,
    });
    expect(reversed.status).toBe('reversed');
    expect(reversed.reversal_journal_id).toBeTruthy();

    const repeatedReversal = await jsonRequest(
      page, approverToken, 'POST', `/fund-transfers/${transfer.id}/cancel`,
      { reason: `Repeated guarded fund transfer correction ${runId}` },
    );
    expect(repeatedReversal._idempotent).toBe(true);
    expect(repeatedReversal.reversal_journal_id).toBe(reversed.reversal_journal_id);

    const openingReversal = await jsonRequest(
      page, approverToken, 'POST', `/fund-opening-balances/${opening.id}/cancel`,
      { reason: `Guarded opening balance correction ${runId}` },
    );
    expect(openingReversal.status).toBe('reversed');
    expect(openingReversal.reversal_journal_id).toBeTruthy();
  });

  test('maker-checker values in-kind stock, issues it, and reverses both movements', async ({ page }) => {
    test.skip(!hundiMakerEmail || !hundiMakerPassword, 'Set distinct MandirMitra maker credentials.');
    await page.goto(baseUrl || '/mitrabooks-erp/');
    const approverToken = await login(page);
    const makerToken = await login(page, hundiMakerEmail, hundiMakerPassword);
    const runId = `${Date.now()}-${Math.floor(Math.random() * 10000)}`;
    const today = new Date().toISOString().slice(0, 10);
    const originalConfig = await jsonRequest(page, approverToken, 'GET', '/temples/modules/config');
    let item;

    try {
      const enabledConfig = await jsonRequest(page, approverToken, 'PUT', '/temples/modules/config', {
        ...originalConfig,
        module_inventory_enabled: true,
      });
      expect(enabledConfig.module_inventory_enabled).toBe(true);

      item = await jsonRequest(page, approverToken, 'POST', '/inventory/items', {
        code: `RICE-${runId}`,
        name: `E2E Rice ${runId}`,
        category: 'FOOD',
        unit: 'KG',
        opening_quantity: '0',
        opening_unit_value: '0',
      });
      expect(item.id).toBeTruthy();

      const donation = await jsonRequest(page, makerToken, 'POST', '/donations', {
        amount: '525.50',
        category: 'Annadanam',
        donation_type: 'in_kind',
        in_kind_item_name: `Rice bags ${runId}`,
        in_kind_item_type: 'rice',
        in_kind_quantity: '10 KG',
        in_kind_valuation_basis: `Supplier invoice ${runId}`,
        inventory_item_id: item.id,
        inventory_quantity: '10',
        devotee_name: `E2E In-kind Sponsor ${runId}`,
      });
      const donationId = donation.donation_id || donation.id;
      expect(donation.status).toBe('pending_valuation');
      expect(donation.valuation_status).toBe('pending_approval');
      expect(donation.journal_entry_id).toBeFalsy();

      const makerApproval = await page.request.post(
        `${apiBaseFromPage(page)}/donations/${donationId}/valuation/approve`,
        {
          headers: headers(makerToken),
          data: { approved_amount: '525.50', approved_quantity: '10', approval_basis: `Checked ${runId}` },
        },
      );
      expect(makerApproval.status()).toBe(409);

      const valued = await jsonRequest(
        page, approverToken, 'POST', `/donations/${donationId}/valuation/approve`,
        { approved_amount: '525.50', approved_quantity: '10', approval_basis: `Checked ${runId}` },
      );
      expect(valued.status).toBe('posted');
      expect(valued.valuation_status).toBe('approved');
      expect(valued.inventory_movement_id).toBeTruthy();
      expect(valued.valuation_approved_by).not.toBe(donation.created_by);

      const consumption = await jsonRequest(page, makerToken, 'POST', '/inventory/consumptions', {
        item_id: item.id,
        quantity: '4.5',
        unit_value: '9999.99',
        consumed_on: today,
        reason: `E2E Annadanam service ${runId}`,
      });
      expect(consumption.status).toBe('pending_approval');
      expect(consumption.unit_value).toBe('52.55');

      const issued = await jsonRequest(
        page, approverToken, 'POST', `/inventory/consumptions/${consumption.id}/approve`,
      );
      expect(issued.status).toBe('posted');
      expect(issued.inventory_movement_id).toBeTruthy();
      expect(issued.approved_by).not.toBe(consumption.created_by);

      const movements = await jsonRequest(page, approverToken, 'GET', '/inventory/movements');
      expect(movements.some((row) => row.id === valued.inventory_movement_id && row.movement_type === 'receipt')).toBe(true);
      expect(movements.some((row) => row.id === issued.inventory_movement_id && row.movement_type === 'issue')).toBe(true);

      const blockedDonationReversal = await page.request.post(
        `${apiBaseFromPage(page)}/donations/${donationId}/cancel`,
        { headers: headers(approverToken), data: { reason: `Stock still consumed ${runId}` } },
      );
      expect(blockedDonationReversal.status()).toBe(409);

      const issueReversal = await jsonRequest(
        page, approverToken, 'POST', `/inventory/consumptions/${consumption.id}/cancel`,
        { reason: `Guarded inventory issue correction ${runId}` },
      );
      expect(issueReversal.status).toBe('reversed');
      expect(issueReversal.reversal_journal_id).toBeTruthy();

      const donationReversal = await jsonRequest(page, approverToken, 'POST', `/donations/${donationId}/cancel`, {
        reason: `Guarded in-kind donation correction ${runId}`,
      });
      expect(donationReversal.status).toBe('reversed');
      expect(donationReversal.inventory_reversal_movement_id).toBeTruthy();
      expect(donationReversal.reversal_journal_id).toBeTruthy();
    } finally {
      if (item && item.id) {
        await jsonRequest(page, approverToken, 'DELETE', `/inventory/items/${item.id}`);
      }
      await jsonRequest(page, approverToken, 'PUT', '/temples/modules/config', originalConfig);
    }
  });

  test('guards tenant 80G readiness and FCRA designated-account acceptance', async ({ page }) => {
    await page.goto(baseUrl || '/mitrabooks-erp/');
    const token = await login(page);
    const runId = `${Date.now()}-${Math.floor(Math.random() * 10000)}`;
    const today = new Date().toISOString().slice(0, 10);
    const paymentAccounts = await jsonRequest(page, token, 'GET', '/donations/payment-accounts');
    const bankAccount = (paymentAccounts.bank_accounts || [])[0];
    test.skip(!bankAccount?.id, 'A demo bank account is required for the guarded FCRA flow.');

    const originalConfig = await jsonRequest(page, token, 'GET', '/compliance/donations/config');
    const createdDonationIds = [];
    try {
      const config = await jsonRequest(page, token, 'PUT', '/compliance/donations/config', {
        enable_80g: true,
        institution_pan: 'ABCDE1234F',
        approval_number: `E2E-80G-${runId}`,
        approval_valid_from: '2026-01-01',
        approval_valid_to: '2027-12-31',
        certificate_label: 'E2E donation certificate',
        receipt_disclaimer: 'E2E readiness evidence only; subject to official filing.',
        cash_eligibility_limit: '2000.00',
        cash_rule_effective_from: '2026-04-01',
        enable_fcra: true,
        fcra_registration_type: 'registration',
        fcra_registration_number: `E2E-FCRA-${runId}`,
        fcra_valid_from: '2026-01-01',
        fcra_valid_to: '2027-12-31',
        fcra_designated_account_id: String(bankAccount.id),
      });
      expect(config.enable_80g).toBe(true);
      expect(config.enable_fcra).toBe(true);

      const eligible = await jsonRequest(page, token, 'POST', '/donations', {
        amount: '501.25',
        category: 'General Donation',
        donation_type: 'cash',
        payment_mode: 'Bank',
        bank_account_id: String(bankAccount.id),
        devotee_name: `E2E 80G Donor ${runId}`,
        request_80g: true,
        donor_pan: 'PQRST6789L',
      });
      createdDonationIds.push(eligible.donation_id || eligible.id);
      expect(eligible['80g_eligibility_status']).toBe('eligible');
      expect(eligible.donor_pan).toBeFalsy();
      expect(eligible.donor_pan_masked).toBe('*****789L');

      const foreign = await jsonRequest(page, token, 'POST', '/donations', {
        amount: '777.50',
        category: 'General Donation',
        donation_type: 'cash',
        payment_mode: 'Bank',
        bank_account_id: String(bankAccount.id),
        devotee_name: `E2E Foreign Donor ${runId}`,
        is_foreign_contribution: true,
        donor_country: 'Singapore',
        foreign_source_declaration: true,
      });
      createdDonationIds.push(foreign.donation_id || foreign.id);
      expect(foreign.fcra_status).toBe('accepted');

      const blocked = await page.request.post(`${apiBaseFromPage(page)}/donations`, {
        headers: headers(token),
        data: {
          amount: '99.00', donation_type: 'cash', payment_mode: 'Cash',
          devotee_name: `Blocked foreign donor ${runId}`,
          is_foreign_contribution: true, donor_country: 'Singapore', foreign_source_declaration: true,
        },
      });
      expect(blocked.status()).toBe(409);

      const report80g = await jsonRequest(
        page, token, 'GET', `/reports/compliance/80g?from_date=${today}&to_date=${today}`,
      );
      expect(report80g.filing_artifact).toBe(false);
      expect(JSON.stringify(report80g)).toContain(eligible.receipt_number);
      expect(JSON.stringify(report80g)).not.toContain('PQRST6789L');

      const reportFcra = await jsonRequest(
        page, token, 'GET', `/reports/compliance/fcra?from_date=${today}&to_date=${today}`,
      );
      expect(reportFcra.filing_artifact).toBe(false);
      expect(JSON.stringify(reportFcra)).toContain(foreign.receipt_number);
    } finally {
      for (const donationId of createdDonationIds) {
        await jsonRequest(page, token, 'POST', `/donations/${donationId}/cancel`, {
          reason: `Guarded compliance E2E cleanup ${runId}`,
        });
      }
      await jsonRequest(page, token, 'PUT', '/compliance/donations/config', originalConfig);
    }
  });
});
