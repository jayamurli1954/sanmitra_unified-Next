const { test, expect } = require('@playwright/test');

const DEMO_TENANT_ID = 'demo-mitrabooks-business';
const email = process.env.E2E_USER_EMAIL || '';
const password = process.env.E2E_USER_PASSWORD || '';
const confirmation = process.env.MITRABOOKS_DEMO_E2E_CONFIRM || '';
const runDestructive = process.env.MITRABOOKS_RUN_DESTRUCTIVE_E2E === 'true';
const baseUrl = (process.env.E2E_BASE_URL || process.env.PLAYWRIGHT_BASE_URL || '').replace(/\/+$/, '');
const apiBaseUrl = (process.env.E2E_API_BASE_URL || '').replace(/\/+$/, '');

function requireDemoGate() {
  return runDestructive && email && password && confirmation === DEMO_TENANT_ID;
}

function apiBaseFromPage(page) {
  if (apiBaseUrl) {
    return `${apiBaseUrl}/api/v1`;
  }
  const current = new URL(page.url());
  if (['127.0.0.1', 'localhost'].includes(current.hostname) && current.port === '3300') {
    return `${current.protocol}//${current.hostname}:8000/api/v1`;
  }
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

function decimalValue(value) {
  const parsed = Number.parseFloat(String(value ?? '0'));
  return Number.isNaN(parsed) ? 0 : parsed;
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

async function textRequest(page, token, method, path, body = undefined, extraHeaders = {}) {
  const response = await page.request.fetch(`${apiBaseFromPage(page)}${path}`, {
    method,
    headers: headers(token, extraHeaders),
    data: body,
  });
  const payload = await response.text().catch(() => '');
  expect(response.ok(), `${method} ${path} failed: ${response.status()} ${payload}`).toBeTruthy();
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
    pan: partyType === 'customer' ? 'AAAAA0000A' : 'ABCDE1234F',
    city: 'Bengaluru',
    state: 'Karnataka',
    pincode: '560001',
    opening_balance: '0.00',
  });
}

test.describe('MitraBooks destructive real-stack demo E2E', () => {
  test.skip(!requireDemoGate(), 'Set MITRABOOKS_RUN_DESTRUCTIVE_E2E=true, MITRABOOKS_DEMO_E2E_CONFIRM=demo-mitrabooks-business, E2E_USER_EMAIL, and E2E_USER_PASSWORD.');

  test('creates, posts, reports, and reverses core business documents on the demo tenant', async ({ page }) => {
    await page.goto(baseUrl || '/mitrabooks-erp/');
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
    const income = accounts.find((account) => account.code === '41001' || ['income', 'revenue'].includes(account.type || account.account_type));
    const credit = accounts.find((account) => ['income', 'revenue', 'liability'].includes(account.type || account.account_type));
    expect(asset?.id, 'asset account missing').toBeTruthy();
    expect(income?.id, 'income account missing').toBeTruthy();
    expect(credit?.id, 'credit account missing').toBeTruthy();

    const runId = Date.now().toString().slice(-8);
    const e2eDate = '2098-07-02';
    const e2eDueDate = '2098-07-20';
    const e2ePeriod = '2098-07';
    const e2eQuarter = '2098-Q2';
    const e2eFinancialYear = '2098-99';
    const e2eReturnPeriod = '072098';
    const openingAsOf = '2098-06-30';
    const yearEndBaseYear = 2200 + (Number.parseInt(runId.slice(-5), 10) % 7000);
    const yearEndFinancialYear = `${yearEndBaseYear}-${String((yearEndBaseYear + 1) % 100).padStart(2, '0')}`;
    const yearEndActivityDate = `${yearEndBaseYear}-07-05`;
    const yearEndCloseDate = `${yearEndBaseYear + 1}-03-31`;
    const customer = await createParty(page, token, runId, 'customer');
    const vendor = await createParty(page, token, runId, 'vendor');

    const openingCsv = [
      'account_code,account_name,party,debit,credit',
      `11001,Cash in Hand,,2500.00,`,
      `12001,Sundry Debtors,${customer.party_code},750.00,`,
      `21001,Sundry Creditors,${vendor.party_code},,300.00`,
    ].join('\n');
    const openingPreview = await jsonRequest(
      page,
      token,
      'POST',
      '/business/opening-balances/preview?accounting_entity_id=primary',
      { csv: openingCsv, as_of: openingAsOf }
    );
    expect(openingPreview.can_post).toBe(true);
    expect(openingPreview.balancing_line?.account_code).toBe('31004');
    expect(decimalValue(openingPreview.balancing_line?.credit)).toBeGreaterThan(0);
    expect(openingPreview.lines?.some((line) => line.party_id === customer.party_id)).toBeTruthy();
    expect(openingPreview.lines?.some((line) => line.party_id === vendor.party_id)).toBeTruthy();

    const openingPost = await jsonRequest(
      page,
      token,
      'POST',
      '/business/opening-balances?accounting_entity_id=primary',
      { csv: openingCsv, as_of: openingAsOf, allow_duplicate: true },
      { 'X-Idempotency-Key': `phase3-demo-opening-balance-${runId}` }
    );
    expect(openingPost.created).toBe(true);
    expect(openingPost.journal_entry_id).toBeTruthy();
    expect(openingPost.line_count).toBeGreaterThanOrEqual(4);
    expect(openingPost.balancing_line?.account_code).toBe('31004');

    const openingExport = await textRequest(
      page,
      token,
      'GET',
      '/business/opening-balances/export?accounting_entity_id=primary'
    );
    expect(openingExport).toContain('account_code');
    expect(openingExport).toContain('11001');
    expect(openingExport).toContain(customer.party_code);
    expect(openingExport).not.toContain('Opening Balance Equity');

    const voucherCreated = await jsonRequest(
      page,
      token,
      'POST',
      '/business/vouchers',
      {
        voucher_type: 'journal',
        entry_date: e2eDate,
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

    const yearEndSeedCreated = await jsonRequest(
      page,
      token,
      'POST',
      '/business/vouchers',
      {
        voucher_type: 'journal',
        entry_date: yearEndActivityDate,
        amount: '345.00',
        debit_account_id: asset.id,
        credit_account_id: income.id,
        description: `Phase 3 E2E year-end seed ${runId}`,
        accounting_entity_id: 'primary',
      },
      { 'X-Idempotency-Key': `phase3-demo-year-end-seed-${runId}` }
    );
    const yearEndSeed = await approveIfNeeded(page, token, 'voucher', yearEndSeedCreated.voucher_id, yearEndSeedCreated);
    expect(yearEndSeed.status).toBe('posted');
    expect(yearEndSeed.journal_entry_id).toBeTruthy();

    const invoiceCreated = await jsonRequest(
      page,
      token,
      'POST',
      '/business/invoices',
      {
        customer_party_id: customer.party_id,
        invoice_date: e2eDate,
        due_date: e2eDueDate,
        income_account_code: '41001',
        place_of_supply: 'Karnataka',
        reference: `PH3-INV-${runId}`,
        line_items: [{ description: 'Phase 3 E2E service', hsn_sac: '9983', quantity: '1', rate: '1000', gst_rate: '18' }],
        tcs_section: '206C-1H',
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
        bill_date: e2eDate,
        due_date: e2eDueDate,
        expense_account_code: '51001',
        place_of_supply: 'Karnataka',
        line_items: [{ description: 'Phase 3 E2E purchase', hsn_sac: '4820', quantity: '1', rate: '500', gst_rate: '18' }],
        tds_section: '194C',
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
        note_date: e2eDate,
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
        note_date: e2eDate,
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

    const trialBalance = await jsonRequest(page, token, 'GET', `/accounting/reports/trial-balance?as_of=${e2eDate}`);
    expect(trialBalance).toBeTruthy();

    const tdsSections = await jsonRequest(page, token, 'GET', '/business/tds/sections');
    expect((tdsSections.tds || []).map((row) => row.section)).toEqual(expect.arrayContaining(['194C']));
    expect((tdsSections.tcs || []).map((row) => row.section)).toEqual(expect.arrayContaining(['206C-1H']));

    const tdsRegister = await jsonRequest(page, token, 'GET', `/business/tds/register?quarter=${e2eQuarter}`);
    const tds194c = (tdsRegister.tds?.sections || []).find((row) => row.section === '194C');
    expect(tds194c?.entries?.some((entry) => entry.doc_number === bill.bill_number)).toBeTruthy();
    expect(decimalValue(tds194c?.total_tax)).toBeGreaterThan(0);
    const tcs206c = (tdsRegister.tcs?.sections || []).find((row) => row.section === '206C-1H');
    expect(tcs206c?.entries?.some((entry) => entry.doc_number === invoice.invoice_number)).toBeTruthy();
    expect(decimalValue(tcs206c?.total_tax)).toBeGreaterThan(0);

    const gstr3b = await jsonRequest(page, token, 'GET', `/business/returns/gstr-3b?period=${e2ePeriod}`);
    expect(gstr3b.return_type).toBe('GSTR-3B');
    expect(decimalValue(gstr3b.outward_supplies?.taxable?.taxable_value)).toBeGreaterThan(0);
    expect(decimalValue(gstr3b.totals?.total_output_tax)).toBeGreaterThan(0);
    expect(gstr3b.gstn_json?.ret_period).toBe(e2eReturnPeriod);

    const gstr1 = await jsonRequest(page, token, 'GET', `/business/returns/gstr-1?period=${e2ePeriod}`);
    expect(gstr1.return_type).toBe('GSTR-1');
    expect(gstr1.sections?.b2b?.invoices).toBeGreaterThan(0);
    expect(gstr1.sections?.cdnr?.notes).toBeGreaterThan(0);
    expect(gstr1.gstn_json?.fp).toBe(e2eReturnPeriod);

    const gstr2b = await jsonRequest(
      page,
      token,
      'POST',
      `/business/returns/gstr-2b/reconcile?period=${e2ePeriod}`,
      {
        data: {
          docdata: {
            b2b: [
              {
                ctin: vendor.gstin,
                inv: [
                  {
                    inum: bill.bill_number,
                    idt: e2eDate,
                    val: decimalValue(bill.bill_total),
                    itms: [
                      {
                        itm_det: {
                          rt: 18,
                          txval: decimalValue(bill.taxable_total),
                          iamt: decimalValue(bill.igst_total),
                          camt: decimalValue(bill.cgst_total),
                          samt: decimalValue(bill.sgst_total),
                        },
                      },
                    ],
                  },
                ],
              },
            ],
          },
        },
      }
    );
    expect(gstr2b.report_type).toBe('GSTR-2B-reconciliation');
    expect(gstr2b.summary?.matched_count).toBeGreaterThan(0);
    expect(decimalValue(gstr2b.summary?.matched_itc)).toBeGreaterThan(0);

    const openingReversed = await jsonRequest(
      page,
      token,
      'POST',
      `/accounting/journal/${openingPost.journal_entry_id}/reverse`,
      { entry_date: e2eDate, reason: `Phase 3 E2E reverse opening balance ${runId}` },
      { 'X-Idempotency-Key': `phase3-demo-opening-balance-reverse-${runId}` }
    );
    expect(openingReversed.original_journal_id).toBe(openingPost.journal_entry_id);
    expect(openingReversed.id).toBeTruthy();

    const yearEndPreview = await jsonRequest(
      page,
      token,
      'GET',
      `/business/year-end/preview?financial_year=${yearEndFinancialYear}&accounting_entity_id=primary`
    );
    expect(yearEndPreview.financial_year).toBe(yearEndFinancialYear);
    expect(yearEndPreview.can_post).toBe(true);
    expect(yearEndPreview.already_closed || []).toHaveLength(0);
    expect(decimalValue(yearEndPreview.net_profit)).toBeGreaterThan(0);
    expect(yearEndPreview.closing_lines?.some((line) => line.account_id === income.id)).toBeTruthy();
    expect(yearEndPreview.retained_earnings?.account_code).toBe('31003');

    const yearEndClose = await jsonRequest(
      page,
      token,
      'POST',
      '/business/year-end/close?accounting_entity_id=primary',
      { financial_year: yearEndFinancialYear },
      { 'X-Idempotency-Key': `phase3-demo-year-end-close-${runId}` }
    );
    expect(yearEndClose.created).toBe(true);
    expect(yearEndClose.financial_year).toBe(yearEndFinancialYear);
    expect(yearEndClose.entry_date).toBe(yearEndCloseDate);
    expect(yearEndClose.journal_entry_id).toBeTruthy();
    expect(yearEndClose.line_count).toBeGreaterThanOrEqual(2);

    const yearEndClosedPreview = await jsonRequest(
      page,
      token,
      'GET',
      `/business/year-end/preview?financial_year=${yearEndFinancialYear}&accounting_entity_id=primary`
    );
    expect(yearEndClosedPreview.can_post).toBe(false);
    expect(yearEndClosedPreview.already_closed?.some((entry) => entry.journal_entry_id === yearEndClose.journal_entry_id)).toBeTruthy();

    const yearEndCloseReversed = await jsonRequest(
      page,
      token,
      'POST',
      `/accounting/journal/${yearEndClose.journal_entry_id}/reverse`,
      { entry_date: yearEndCloseDate, reason: `Phase 3 E2E reverse year-end close ${runId}` },
      { 'X-Idempotency-Key': `phase3-demo-year-end-close-reverse-${runId}` }
    );
    expect(yearEndCloseReversed.original_journal_id).toBe(yearEndClose.journal_entry_id);
    expect(yearEndCloseReversed.id).toBeTruthy();

    const cmp08 = await jsonRequest(page, token, 'GET', `/business/returns/cmp-08?quarter=${e2eQuarter}`);
    expect(cmp08.return_type).toBe('CMP-08');
    expect(cmp08.gstn_json?.ret_period).toBe(e2eQuarter);
    const gstr4 = await jsonRequest(page, token, 'GET', `/business/returns/gstr-4?financial_year=${e2eFinancialYear}`);
    expect(gstr4.return_type).toBe('GSTR-4');
    expect(gstr4.gstn_json?.fy).toBe(e2eFinancialYear);

    const settlementPreview = await jsonRequest(page, token, 'GET', `/business/gst-settlement/preview?period=${e2ePeriod}`);
    expect(settlementPreview.status).toBe('preview');
    expect(settlementPreview.posted).toBe(false);
    expect(decimalValue(settlementPreview.total_output)).toBeGreaterThan(0);

    const settlement = await jsonRequest(
      page,
      token,
      'POST',
      '/business/gst-settlement',
      { period: e2ePeriod, lock_period: true, accounting_entity_id: 'primary' },
      { 'X-Idempotency-Key': `phase3-demo-gst-settlement-${runId}` }
    );
    expect(settlement.status).toBe('posted');
    expect(settlement.posted).toBe(true);
    expect(settlement.period_locked).toBe(true);
    expect(settlement.journal_entry_id).toBeTruthy();

    const settlementReversed = await jsonRequest(
      page,
      token,
      'POST',
      `/business/gst-settlement/${e2ePeriod}/reverse`,
      {
        reason: `Phase 3 E2E reverse GST settlement ${runId}`,
        reversal_date: e2eDate,
        unlock_period: true,
        accounting_entity_id: 'primary',
      },
      { 'X-Idempotency-Key': `phase3-demo-gst-settlement-reverse-${runId}` }
    );
    expect(settlementReversed.status).toBe('reversed');
    expect(settlementReversed.posted).toBe(false);
    expect(settlementReversed.period_locked).toBe(false);
    expect(settlementReversed.reversal_journal_entry_id).toBeTruthy();

    let gstPeriodLocked = false;
    try {
      const lockedPeriod = await jsonRequest(page, token, 'PUT', '/business/gst-period-locks', {
        period: e2ePeriod,
        locked: true,
        note: `Phase 3 E2E temporary compliance lock ${runId}`,
        accounting_entity_id: 'primary',
      });
      gstPeriodLocked = lockedPeriod.locked === true;
      expect(lockedPeriod.locked).toBe(true);
    } finally {
      if (gstPeriodLocked) {
        const unlockedPeriod = await jsonRequest(page, token, 'PUT', '/business/gst-period-locks', {
          period: e2ePeriod,
          locked: false,
          note: `Phase 3 E2E unlock before cleanup ${runId}`,
          accounting_entity_id: 'primary',
        });
        expect(unlockedPeriod.locked).toBe(false);
      }
    }

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
        { reason: `Phase 3 E2E reverse ${label}`, cancel_date: e2eDate },
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
      { reason: 'Phase 3 E2E reverse voucher', reversal_date: e2eDate, accounting_entity_id: 'primary' },
      { 'X-Idempotency-Key': `phase3-demo-voucher-reverse-${runId}` }
    );
    expect(String(voucherReversed.status).toLowerCase()).toBe('reversed');
    expect(voucherReversed.reversal_journal_entry_id).toBeTruthy();

    const yearEndSeedReversed = await jsonRequest(
      page,
      token,
      'POST',
      `/business/vouchers/${yearEndSeed.voucher_id}/reverse`,
      { reason: 'Phase 3 E2E reverse year-end seed voucher', reversal_date: yearEndCloseDate, accounting_entity_id: 'primary' },
      { 'X-Idempotency-Key': `phase3-demo-year-end-seed-reverse-${runId}` }
    );
    expect(String(yearEndSeedReversed.status).toLowerCase()).toBe('reversed');
    expect(yearEndSeedReversed.reversal_journal_entry_id).toBeTruthy();

    await page.locator('nav#nav a[data-business-workspace="reports"]').click();
    await expect(page.locator('.erp-workspace-panel')).toContainText('Financial Reports');
    await expect(page.locator('.erp-workspace-panel')).toContainText('Trial Balance');
  });
});
