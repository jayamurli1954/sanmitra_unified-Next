const { test, expect } = require('@playwright/test');

const DEMO_TENANT_ID = 'demo-mitrabooks-business';
const email = process.env.E2E_USER_EMAIL || '';
const password = process.env.E2E_USER_PASSWORD || '';
const confirmation = process.env.MITRABOOKS_DEMO_E2E_CONFIRM || '';
const runDestructive = process.env.MITRABOOKS_RUN_DESTRUCTIVE_E2E === 'true';

function requireDemoGate() {
  return runDestructive && email && password && confirmation === DEMO_TENANT_ID;
}

function apiBaseFromPage(page) {
  const current = new URL(page.url());
  return `${current.origin}/api/v1`;
}

function headers(token, extra = {}) {
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
    'X-App-Key': 'mitrabooks',
    ...extra,
  };
}

async function jsonRequest(page, token, method, path, body = undefined, extraHeaders = {}) {
  const response = await page.request.fetch(`${apiBaseFromPage(page)}${path}`, {
    method,
    headers: headers(token, extraHeaders),
    data: body,
  });
  const payload = await response.json().catch(() => ({}));
  expect(response.ok(), `${method} ${path} failed: ${response.status()} ${JSON.stringify(payload)}`).toBeTruthy();
  return payload;
}

async function approveIfNeeded(page, token, kind, id, doc) {
  if (doc.status !== 'pending_approval' && doc.approval_status !== 'pending_approval') {
    return doc;
  }
  const paths = {
    voucher: `/business/vouchers/${id}/review`,
    invoice: `/business/invoices/${id}/review`,
    bill: `/business/bills/${id}/review`,
    creditNote: `/business/credit-notes/${id}/review`,
    debitNote: `/business/debit-notes/${id}/review`,
  };
  return jsonRequest(page, token, 'POST', paths[kind], {
    approve: true,
    notes: 'Phase 3 destructive demo E2E approval',
    accounting_entity_id: 'primary',
  });
}

async function createParty(page, token, runId, partyType) {
  return jsonRequest(page, token, 'POST', '/business/parties', {
    party_name: `E2E ${partyType} ${runId}`,
    party_type: partyType,
    party_code: `E2E-${partyType.toUpperCase()}-${runId}`,
    gstin: partyType === 'customer' ? '29AAAAA0000A1Z5' : '29ABCDE1234F1Z5',
    city: 'Bengaluru',
    state: 'Karnataka',
    pincode: '560001',
    opening_balance: '0.00',
  });
}

test.describe('MitraBooks destructive real-stack demo E2E', () => {
  test.skip(!requireDemoGate(), 'Set MITRABOOKS_RUN_DESTRUCTIVE_E2E=true, MITRABOOKS_DEMO_E2E_CONFIRM=demo-mitrabooks-business, E2E_USER_EMAIL, and E2E_USER_PASSWORD.');

  test('creates, posts, reports, and reverses core business documents on the demo tenant', async ({ page }) => {
    await page.goto('/');
    await page.locator('#login-email').fill(email);
    await page.locator('#login-password').fill(password);
    await page.locator('#login-submit').click();
    await expect(page.locator('#login-status')).toContainText(/Signed in|workspace is loading/i, { timeout: 30000 });
    await expect(page.locator('#menu-tenant-display')).toContainText(DEMO_TENANT_ID, { timeout: 30000 });

    const token = await page.evaluate(() => window.localStorage.getItem('sanmitra_frontend_access_token') || '');
    expect(token, 'browser login did not store an access token').toBeTruthy();

    const modules = await jsonRequest(page, token, 'GET', '/modules/me');
    expect(modules.tenant_id).toBe(DEMO_TENANT_ID);
    expect(modules.organization_type).toBe('BUSINESS');
    expect((modules.enabled_modules || []).map((item) => item.module_key)).toEqual(
      expect.arrayContaining(['business', 'accounting', 'audit'])
    );

    await jsonRequest(page, token, 'POST', '/accounting/initialize-chart-of-accounts');
    const accounts = await jsonRequest(page, token, 'GET', '/accounting/accounts');
    const asset = accounts.find((account) => account.type === 'asset' || account.account_type === 'asset');
    const credit = accounts.find((account) => ['income', 'revenue', 'liability'].includes(account.type || account.account_type));
    expect(asset?.id, 'asset account missing').toBeTruthy();
    expect(credit?.id, 'credit account missing').toBeTruthy();

    const runId = Date.now().toString().slice(-8);
    const customer = await createParty(page, token, runId, 'customer');
    const vendor = await createParty(page, token, runId, 'vendor');

    const voucherCreated = await jsonRequest(
      page,
      token,
      'POST',
      '/business/vouchers',
      {
        voucher_type: 'journal',
        entry_date: '2026-07-02',
        amount: '125.00',
        debit_account_id: asset.id,
        credit_account_id: credit.id,
        description: `Phase 3 E2E voucher ${runId}`,
        party_id: customer.party_id,
        accounting_entity_id: 'primary',
      },
      { 'X-Idempotency-Key': `phase3-demo-voucher-${runId}` }
    );
    const voucher = await approveIfNeeded(page, token, 'voucher', voucherCreated.voucher_id, voucherCreated);
    expect(voucher.status).toBe('posted');
    expect(voucher.journal_entry_id).toBeTruthy();

    const invoiceCreated = await jsonRequest(
      page,
      token,
      'POST',
      '/business/invoices',
      {
        customer_party_id: customer.party_id,
        invoice_date: '2026-07-02',
        due_date: '2026-07-20',
        income_account_code: '41001',
        place_of_supply: 'Karnataka',
        reference: `PH3-INV-${runId}`,
        line_items: [{ description: 'Phase 3 E2E service', hsn_sac: '9983', quantity: '1', rate: '1000', gst_rate: '18' }],
      },
      { 'X-Idempotency-Key': `phase3-demo-invoice-${runId}` }
    );
    const invoice = await approveIfNeeded(page, token, 'invoice', invoiceCreated.invoice_id, invoiceCreated);
    expect(invoice.status).toBe('posted');
    expect(invoice.journal_entry_id).toBeTruthy();

    const billCreated = await jsonRequest(
      page,
      token,
      'POST',
      '/business/bills',
      {
        vendor_party_id: vendor.party_id,
        bill_number: `PH3-BILL-${runId}`,
        bill_date: '2026-07-02',
        due_date: '2026-07-20',
        expense_account_code: '51001',
        place_of_supply: 'Karnataka',
        line_items: [{ description: 'Phase 3 E2E purchase', hsn_sac: '4820', quantity: '1', rate: '500', gst_rate: '18' }],
      },
      { 'X-Idempotency-Key': `phase3-demo-bill-${runId}` }
    );
    const bill = await approveIfNeeded(page, token, 'bill', billCreated.bill_id, billCreated);
    expect(bill.status).toBe('posted');
    expect(bill.journal_entry_id).toBeTruthy();

    const creditNoteCreated = await jsonRequest(
      page,
      token,
      'POST',
      '/business/credit-notes',
      {
        customer_party_id: customer.party_id,
        note_date: '2026-07-02',
        original_invoice_number: invoice.invoice_number,
        reason: 'sales_return',
        income_account_code: '41001',
        place_of_supply: 'Karnataka',
        line_items: [{ description: 'Phase 3 E2E sales return', hsn_sac: '9983', quantity: '1', rate: '100', gst_rate: '18' }],
      },
      { 'X-Idempotency-Key': `phase3-demo-credit-note-${runId}` }
    );
    const creditNote = await approveIfNeeded(page, token, 'creditNote', creditNoteCreated.credit_note_id, creditNoteCreated);
    expect(creditNote.status).toBe('posted');
    expect(creditNote.journal_entry_id).toBeTruthy();

    const debitNoteCreated = await jsonRequest(
      page,
      token,
      'POST',
      '/business/debit-notes',
      {
        vendor_party_id: vendor.party_id,
        note_date: '2026-07-02',
        original_bill_number: bill.bill_number,
        reason: 'purchase_return',
        expense_account_code: '51001',
        place_of_supply: 'Karnataka',
        line_items: [{ description: 'Phase 3 E2E purchase return', hsn_sac: '4820', quantity: '1', rate: '100', gst_rate: '18' }],
      },
      { 'X-Idempotency-Key': `phase3-demo-debit-note-${runId}` }
    );
    const debitNote = await approveIfNeeded(page, token, 'debitNote', debitNoteCreated.debit_note_id, debitNoteCreated);
    expect(debitNote.status).toBe('posted');
    expect(debitNote.journal_entry_id).toBeTruthy();

    const trialBalance = await jsonRequest(page, token, 'GET', '/accounting/reports/trial-balance?as_of=2026-07-02');
    expect(trialBalance).toBeTruthy();

    const reversals = [
      ['invoice', `/business/invoices/${invoice.invoice_id}/cancel`, `phase3-demo-invoice-cancel-${runId}`],
      ['bill', `/business/bills/${bill.bill_id}/cancel`, `phase3-demo-bill-cancel-${runId}`],
      ['credit note', `/business/credit-notes/${creditNote.credit_note_id}/cancel`, `phase3-demo-credit-note-cancel-${runId}`],
      ['debit note', `/business/debit-notes/${debitNote.debit_note_id}/cancel`, `phase3-demo-debit-note-cancel-${runId}`],
    ];
    for (const [label, path, key] of reversals) {
      const reversed = await jsonRequest(
        page,
        token,
        'POST',
        path,
        { reason: `Phase 3 E2E reverse ${label}`, cancel_date: '2026-07-02' },
        { 'X-Idempotency-Key': key }
      );
      expect(['cancelled', 'reversed']).toContain(String(reversed.status).toLowerCase());
      expect(reversed.reversal_journal_entry_id, `${label} reversal journal missing`).toBeTruthy();
    }

    const voucherReversed = await jsonRequest(
      page,
      token,
      'POST',
      `/business/vouchers/${voucher.voucher_id}/reverse`,
      { reason: 'Phase 3 E2E reverse voucher', reversal_date: '2026-07-02', accounting_entity_id: 'primary' },
      { 'X-Idempotency-Key': `phase3-demo-voucher-reverse-${runId}` }
    );
    expect(String(voucherReversed.status).toLowerCase()).toBe('reversed');
    expect(voucherReversed.reversal_journal_entry_id).toBeTruthy();

    await page.locator('nav#nav a[data-business-workspace="reports"]').click();
    await expect(page.locator('.erp-workspace-panel')).toContainText('Financial Reports');
    await expect(page.locator('.erp-workspace-panel')).toContainText('Trial Balance');
  });
});
