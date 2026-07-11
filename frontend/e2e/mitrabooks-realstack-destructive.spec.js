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

async function fileRequest(page, token, method, path, body = undefined, extraHeaders = {}) {
  const response = await page.request.fetch(`${apiBaseFromPage(page)}${path}`, {
    method,
    headers: headers(token, extraHeaders),
    data: body,
  });
  const payload = await response.text().catch(() => '');
  expect(response.ok(), `${method} ${path} failed: ${response.status()} ${payload}`).toBeTruthy();
  return {
    headers: response.headers(),
    text: payload,
  };
}

function expectGovernedExport(download, exportType, exportFormat, accountingEntityId) {
  expect(download.headers['x-sanmitra-export-governed']).toBe('true');
  expect(download.headers['x-sanmitra-export-type']).toBe(exportType);
  expect(download.headers['x-sanmitra-export-format']).toBe(exportFormat);
  expect(download.headers['x-sanmitra-accounting-entity']).toBe(accountingEntityId);
}

async function expectJsonFailure(page, token, method, path, expectedStatus) {
  const response = await page.request.fetch(`${apiBaseFromPage(page)}${path}`, {
    method,
    headers: headers(token),
  });
  const payload = await response.json().catch(() => ({}));
  expect(response.status(), `${method} ${path} expected ${expectedStatus}, got ${response.status()} ${JSON.stringify(payload)}`).toBe(expectedStatus);
  return payload;
}

async function uploadAttachment(page, token, path, name, mimeType, body) {
  const response = await page.request.fetch(`${apiBaseFromPage(page)}${path}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'X-App-Key': 'mitrabooks',
    },
    multipart: {
      file: {
        name,
        mimeType,
        buffer: Buffer.from(body),
      },
    },
  });
  const payload = await response.json().catch(() => ({}));
  expect(response.ok(), `POST ${path} failed: ${response.status()} ${JSON.stringify(payload)}`).toBeTruthy();
  return payload;
}

async function approveIfNeeded(page, token, kind, id, doc, accountingEntityId = 'primary') {
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
    accounting_entity_id: accountingEntityId,
  });
}

async function createParty(page, token, runId, partyType, accountingEntityId = 'primary') {
  return jsonRequest(
    page,
    token,
    'POST',
    '/business/parties',
    {
      party_name: `E2E ${partyType} ${runId}`,
      party_type: partyType,
      party_code: `E2E-${partyType.toUpperCase()}-${accountingEntityId}-${runId}`.slice(0, 80),
      gstin: partyType === 'customer' ? '29AAAAA0000A1Z5' : '29ABCDE1234F1Z5',
      pan: partyType === 'customer' ? 'AAAAA0000A' : 'ABCDE1234F',
      city: 'Bengaluru',
      state: 'Karnataka',
      pincode: '560001',
      opening_balance: '0.00',
    },
    { 'X-Accounting-Entity-ID': accountingEntityId }
  );
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

    const token = await page.evaluate(() => window.sessionStorage.getItem('sanmitra_frontend_access_token') || '');
    expect(token, 'browser login did not store an access token').toBeTruthy();

    const modules = await jsonRequest(page, token, 'GET', '/modules/me');
    expect(modules.tenant_id).toBe(DEMO_TENANT_ID);
    expect(modules.organization_type).toBe('BUSINESS');
    expect((modules.enabled_modules || []).map((item) => item.module_key)).toEqual(
      expect.arrayContaining(['business', 'accounting', 'audit'])
    );

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
    const inventoryEntity = `inventory-e2e-${runId}`;
    const fixedAssetEntity = `fixed-asset-e2e-${runId}`;
    const dimensionsEntity = `dimensions-e2e-${runId}`;
    const branchEntity = `branch-e2e-${runId}`;
    const misHealthEntity = `mis-health-e2e-${runId}`;
    const bankReconRef = `BR-${runId}`;
    const bankReconAmount = '222.37';

    const adminSettings = await jsonRequest(page, token, 'GET', '/business/admin-settings?accounting_entity_id=primary');
    expect(adminSettings.integrations?.document_storage_provider).toBeTruthy();
    expect(adminSettings.ai_settings?.ocr_enabled).toBe(false);
    expect(adminSettings.ai_settings?.document_review_required).toBe(true);
    expect(adminSettings.ai_settings?.posting_review_required).toBe(true);
    expect(adminSettings.ai_settings?.auto_post_to_ledger).toBe(false);

    const caClient = await jsonRequest(page, token, 'POST', '/business/ca-clients', {
      client_name: `E2E Document Client ${runId}`,
      gstin: '29ABCDE1234F1Z5',
      pan: 'ABCDE1234F',
      contact_person: 'Demo Client Owner',
      contact_email: `document-client-${runId}@example.test`,
      engagement_type: 'monthly_bookkeeping',
      assigned_to: 'Demo Reviewer',
      client_owner: 'Demo Partner',
      access_level: 'data_entry',
      compliance_tracks: ['GST', 'Books'],
      notes: 'Real-stack document upload gate client',
      accounting_entity_id: 'primary',
    });
    expect(caClient.tenant_id).toBe(DEMO_TENANT_ID);
    expect(caClient.app_key).toBe('mitrabooks');
    expect(caClient.accounting_entity_id).toBe('primary');

    const caDocument = await jsonRequest(page, token, 'POST', '/business/ca-documents', {
      client_id: caClient.client_id,
      client_name: caClient.client_name,
      document_type: 'purchase_bill',
      period: '2026-07',
      assigned_to: 'Demo Reviewer',
      client_owner: 'Demo Partner',
      priority: 'high',
      due_date: '2026-07-31',
      compliance_area: 'GST',
      client_access_enabled: true,
      original_file_name: `phase3-demo-document-${runId}.pdf`,
      notes: 'Real-stack document upload gate metadata',
      accounting_entity_id: 'primary',
    });
    expect(caDocument.tenant_id).toBe(DEMO_TENANT_ID);
    expect(caDocument.app_key).toBe('mitrabooks');
    expect(caDocument.accounting_entity_id).toBe('primary');
    expect(caDocument.book_id).toBe('primary');
    expect(caDocument.client_id).toBe(caClient.client_id);
    expect(caDocument.status).toBe('uploaded');
    expect(caDocument.attachment_count).toBe(0);
    expect(caDocument.posting_reference).toBeFalsy();

    const attachment = await uploadAttachment(
      page,
      token,
      `/business/ca-documents/${caDocument.document_id}/attachments?accounting_entity_id=primary`,
      `phase3-demo-document-${runId}.pdf`,
      'application/pdf',
      `%PDF-1.4\n% Phase 3 demo document upload ${runId}\n`
    );
    expect(attachment.tenant_id).toBe(DEMO_TENANT_ID);
    expect(attachment.app_key).toBe('mitrabooks');
    expect(attachment.accounting_entity_id).toBe('primary');
    expect(attachment.owner_type).toBe('ca_document');
    expect(attachment.owner_id).toBe(caDocument.document_id);
    expect(attachment.file_name).toBe(`phase3-demo-document-${runId}.pdf`);
    expect(attachment.content_type).toBe('application/pdf');
    expect(attachment.size_bytes).toBeGreaterThan(0);

    const attachments = await jsonRequest(
      page,
      token,
      'GET',
      `/business/ca-documents/${caDocument.document_id}/attachments?accounting_entity_id=primary`
    );
    expect(attachments.total).toBeGreaterThanOrEqual(1);
    expect(attachments.items.map((item) => item.attachment_id)).toContain(attachment.attachment_id);
    await expectJsonFailure(
      page,
      token,
      'GET',
      `/business/ca-documents/${caDocument.document_id}/attachments?accounting_entity_id=other-demo-book`,
      404
    );

    const downloadedAttachment = await textRequest(
      page,
      token,
      'GET',
      `/business/ca-documents/${caDocument.document_id}/attachments/${attachment.attachment_id}/download?accounting_entity_id=primary`
    );
    expect(downloadedAttachment).toContain(`Phase 3 demo document upload ${runId}`);

    const underReviewDocument = await jsonRequest(page, token, 'PATCH', `/business/ca-documents/${caDocument.document_id}`, {
      status: 'under_review',
      notes: 'Demo reviewer opened the uploaded document',
      accounting_entity_id: 'primary',
    });
    expect(underReviewDocument.status).toBe('under_review');
    expect(underReviewDocument.review_started_at).toBeTruthy();
    expect(underReviewDocument.posting_reference).toBeFalsy();

    const reviewedDocument = await jsonRequest(page, token, 'PATCH', `/business/ca-documents/${caDocument.document_id}`, {
      status: 'reviewed',
      next_action: 'No OCR handoff or auto-posting in this demo gate',
      notes: 'Manual review completed without ledger posting',
      accounting_entity_id: 'primary',
    });
    expect(reviewedDocument.status).toBe('reviewed');
    expect(reviewedDocument.reviewed_at).toBeTruthy();
    expect(reviewedDocument.posting_reference).toBeFalsy();
    expect(reviewedDocument.attachment_count).toBeGreaterThanOrEqual(1);
    expect(reviewedDocument.next_action).toContain('No OCR');

    const listedDocuments = await jsonRequest(page, token, 'GET', `/business/ca-documents?client_name=${encodeURIComponent(caClient.client_name)}&accounting_entity_id=primary`);
    expect(listedDocuments.items.map((item) => item.document_id)).toContain(caDocument.document_id);

    const uploadAudit = await jsonRequest(
      page,
      token,
      'GET',
      `/audit/events?action=business_document_attachment_uploaded&entity_type=business_document_attachment&entity_id=${attachment.attachment_id}&limit=10`
    );
    expect(uploadAudit.items.length).toBeGreaterThanOrEqual(1);
    expect(uploadAudit.items[0].tenant_id).toBe(DEMO_TENANT_ID);
    expect(uploadAudit.items[0].product).toBe('mitrabooks');

    const downloadAudit = await jsonRequest(
      page,
      token,
      'GET',
      `/audit/events?action=business_document_attachment_downloaded&entity_type=business_document_attachment&entity_id=${attachment.attachment_id}&limit=10`
    );
    expect(downloadAudit.items.length).toBeGreaterThanOrEqual(1);

    const reviewAudit = await jsonRequest(
      page,
      token,
      'GET',
      `/audit/events?action=business_ca_document_metadata_updated&entity_type=business_ca_document_metadata&entity_id=${caDocument.document_id}&limit=10`
    );
    expect(reviewAudit.items.length).toBeGreaterThanOrEqual(2);

    await jsonRequest(page, token, 'POST', '/accounting/initialize-chart-of-accounts');
    const accounts = await jsonRequest(page, token, 'GET', '/accounting/accounts');
    const asset = accounts.find((account) => account.type === 'asset' || account.account_type === 'asset');
    const bankAccount = accounts.find((account) => account.code === '11010')
      || accounts.find((account) => account.is_cash_bank && /bank/i.test(account.name || ''))
      || accounts.find((account) => account.is_cash_bank);
    const income = accounts.find((account) => account.code === '41001' || ['income', 'revenue'].includes(account.type || account.account_type));
    const expense = accounts.find((account) => account.code === '54001')
      || accounts.find((account) => account.code === '51001')
      || accounts.find((account) => (account.type || account.account_type) === 'expense');
    const credit = accounts.find((account) => ['income', 'revenue', 'liability'].includes(account.type || account.account_type));
    expect(asset?.id, 'asset account missing').toBeTruthy();
    expect(bankAccount?.id, 'bank/cash account missing').toBeTruthy();
    expect(income?.id, 'income account missing').toBeTruthy();
    expect(expense?.id, 'expense account missing').toBeTruthy();
    expect(credit?.id, 'credit account missing').toBeTruthy();

    await jsonRequest(
      page,
      token,
      'POST',
      '/accounting/initialize-chart-of-accounts',
      undefined,
      { 'X-Accounting-Entity-ID': fixedAssetEntity }
    );
    const fixedAsset = await jsonRequest(
      page,
      token,
      'POST',
      `/business/fixed-assets?accounting_entity_id=${fixedAssetEntity}`,
      {
        asset_name: `Phase 3 E2E Laptop ${runId}`,
        asset_account_code: '16003',
        purchase_date: '2098-04-01',
        cost: '120000.00',
        salvage_value: '20000.00',
        method: 'slm',
        useful_life_years: '5',
        opening_accumulated_depreciation: '0.00',
        notes: 'Guarded real-stack fixed asset demo gate',
      }
    );
    expect(fixedAsset.tenant_id).toBe(DEMO_TENANT_ID);
    expect(fixedAsset.app_key).toBe('mitrabooks');
    expect(fixedAsset.accounting_entity_id).toBe(fixedAssetEntity);
    expect(fixedAsset.status).toBe('active');
    expect(fixedAsset.asset_account_code).toBe('16003');

    const fixedAssetPreview = await jsonRequest(
      page,
      token,
      'GET',
      `/business/depreciation/preview?financial_year=${e2eFinancialYear}&accounting_entity_id=${fixedAssetEntity}`
    );
    expect(fixedAssetPreview.can_post).toBe(true);
    expect(fixedAssetPreview.rows?.some((row) => row.asset_id === fixedAsset.asset_id && decimalValue(row.depreciation) > 0)).toBeTruthy();
    expect(decimalValue(fixedAssetPreview.total_depreciation)).toBeGreaterThan(0);

    const depreciationRun = await jsonRequest(
      page,
      token,
      'POST',
      `/business/depreciation/run?accounting_entity_id=${fixedAssetEntity}`,
      { financial_year: e2eFinancialYear },
      { 'X-Idempotency-Key': `phase3-demo-depreciation-${runId}` }
    );
    expect(depreciationRun.created).toBe(true);
    expect(depreciationRun.journal_entry_id).toBeTruthy();
    expect(depreciationRun.financial_year).toBe(e2eFinancialYear);
    expect(depreciationRun.entry_date).toBe('2099-03-31');
    expect(decimalValue(depreciationRun.total_depreciation)).toBeGreaterThan(0);

    const depreciationJournal = await jsonRequest(
      page,
      token,
      'GET',
      `/accounting/journal/${depreciationRun.journal_entry_id}`,
      undefined,
      { 'X-Accounting-Entity-ID': fixedAssetEntity }
    );
    expect(decimalValue(depreciationJournal.total_debit)).toBe(decimalValue(depreciationJournal.total_credit));
    expect(depreciationJournal.source_document_type).toBe('depreciation');

    const fixedAssetListAfterDepreciation = await jsonRequest(
      page,
      token,
      'GET',
      `/business/fixed-assets?accounting_entity_id=${fixedAssetEntity}`
    );
    const depreciatedAsset = fixedAssetListAfterDepreciation.items?.find((item) => item.asset_id === fixedAsset.asset_id);
    expect(decimalValue(depreciatedAsset?.accumulated_depreciation)).toBeGreaterThan(0);
    expect(decimalValue(depreciatedAsset?.book_value)).toBeLessThan(decimalValue(fixedAsset.cost));

    const disposedAsset = await jsonRequest(
      page,
      token,
      'POST',
      `/business/fixed-assets/${fixedAsset.asset_id}/dispose?accounting_entity_id=${fixedAssetEntity}`,
      {
        disposal_date: '2099-03-31',
        sale_value: '90000.00',
        cash_bank_account_code: '11010',
        reason: `Phase 3 E2E fixed asset disposal ${runId}`,
      },
      { 'X-Idempotency-Key': `phase3-demo-fixed-asset-disposal-${runId}` }
    );
    expect(disposedAsset.status).toBe('disposed');
    expect(disposedAsset.journal_entry_id).toBeTruthy();
    expect(disposedAsset.disposal_date).toBe('2099-03-31');
    expect(decimalValue(disposedAsset.total_debit)).toBe(decimalValue(disposedAsset.total_credit));
    expect(decimalValue(disposedAsset.loss)).toBeGreaterThan(0);

    const disposalJournal = await jsonRequest(
      page,
      token,
      'GET',
      `/accounting/journal/${disposedAsset.journal_entry_id}`,
      undefined,
      { 'X-Accounting-Entity-ID': fixedAssetEntity }
    );
    expect(decimalValue(disposalJournal.total_debit)).toBe(decimalValue(disposalJournal.total_credit));
    expect(disposalJournal.source_document_type).toBe('fixed_asset_disposal');

    const fixedAssetListAfterDisposal = await jsonRequest(
      page,
      token,
      'GET',
      `/business/fixed-assets?accounting_entity_id=${fixedAssetEntity}`
    );
    const finalAsset = fixedAssetListAfterDisposal.items?.find((item) => item.asset_id === fixedAsset.asset_id);
    expect(finalAsset?.status).toBe('disposed');
    expect(finalAsset?.disposal_journal_entry_id).toBe(disposedAsset.journal_entry_id);

    const primaryFixedAssets = await jsonRequest(page, token, 'GET', '/business/fixed-assets?accounting_entity_id=primary');
    expect(primaryFixedAssets.items?.some((item) => item.asset_id === fixedAsset.asset_id)).toBeFalsy();

    await jsonRequest(
      page,
      token,
      'POST',
      '/accounting/initialize-chart-of-accounts',
      undefined,
      { 'X-Accounting-Entity-ID': dimensionsEntity }
    );
    const dimensionCustomer = await createParty(page, token, runId, 'customer', dimensionsEntity);
    const dimensionVendor = await createParty(page, token, runId, 'vendor', dimensionsEntity);
    const dimensionCostCentre = await jsonRequest(
      page,
      token,
      'POST',
      `/business/dimensions?accounting_entity_id=${dimensionsEntity}`,
      {
        dimension_type: 'cost_centre',
        code: `DCC${runId.slice(-5)}`,
        name: `Phase 3 E2E Cost Centre ${runId}`,
      }
    );
    const dimensionProject = await jsonRequest(
      page,
      token,
      'POST',
      `/business/dimensions?accounting_entity_id=${dimensionsEntity}`,
      {
        dimension_type: 'project',
        code: `DPR${runId.slice(-5)}`,
        name: `Phase 3 E2E Project ${runId}`,
      }
    );
    expect(dimensionCostCentre.accounting_entity_id).toBe(dimensionsEntity);
    expect(dimensionProject.accounting_entity_id).toBe(dimensionsEntity);

    const dimensionMasters = await jsonRequest(page, token, 'GET', `/business/dimensions?accounting_entity_id=${dimensionsEntity}`);
    expect((dimensionMasters.cost_centres || []).some((row) => row.dimension_id === dimensionCostCentre.dimension_id)).toBeTruthy();
    expect((dimensionMasters.projects || []).some((row) => row.dimension_id === dimensionProject.dimension_id)).toBeTruthy();

    const dimensionInvoiceCreated = await jsonRequest(
      page,
      token,
      'POST',
      '/business/invoices',
      {
        customer_party_id: dimensionCustomer.party_id,
        invoice_date: e2eDate,
        due_date: e2eDueDate,
        income_account_code: '41001',
        place_of_supply: 'Karnataka',
        reference: `DIM-INV-${runId}`,
        cost_centre_id: dimensionCostCentre.dimension_id,
        project_id: dimensionProject.dimension_id,
        accounting_entity_id: dimensionsEntity,
        line_items: [
          {
            description: 'Phase 3 E2E dimension income',
            hsn_sac: '9983',
            quantity: '1',
            rate: '800',
            gst_rate: '18',
            cost_centre_id: dimensionCostCentre.dimension_id,
            project_id: dimensionProject.dimension_id,
          },
          {
            description: 'Phase 3 E2E dimension fallback income',
            hsn_sac: '9983',
            quantity: '1',
            rate: '200',
            gst_rate: '18',
          },
        ],
      },
      { 'X-Idempotency-Key': `phase3-demo-dimension-invoice-${runId}` }
    );
    const dimensionInvoice = await approveIfNeeded(page, token, 'invoice', dimensionInvoiceCreated.invoice_id, dimensionInvoiceCreated, dimensionsEntity);
    expect(dimensionInvoice.status).toBe('posted');

    const dimensionBillCreated = await jsonRequest(
      page,
      token,
      'POST',
      '/business/bills',
      {
        vendor_party_id: dimensionVendor.party_id,
        bill_number: `DIM-BILL-${runId}`,
        bill_date: e2eDate,
        due_date: e2eDueDate,
        expense_account_code: '51001',
        place_of_supply: 'Karnataka',
        cost_centre_id: dimensionCostCentre.dimension_id,
        project_id: dimensionProject.dimension_id,
        accounting_entity_id: dimensionsEntity,
        line_items: [
          {
            description: 'Phase 3 E2E dimension expense',
            hsn_sac: '4820',
            quantity: '1',
            rate: '300',
            gst_rate: '18',
            cost_centre_id: dimensionCostCentre.dimension_id,
            project_id: dimensionProject.dimension_id,
          },
          {
            description: 'Phase 3 E2E dimension fallback expense',
            hsn_sac: '4820',
            quantity: '1',
            rate: '100',
            gst_rate: '18',
          },
        ],
      },
      { 'X-Idempotency-Key': `phase3-demo-dimension-bill-${runId}` }
    );
    const dimensionBill = await approveIfNeeded(page, token, 'bill', dimensionBillCreated.bill_id, dimensionBillCreated, dimensionsEntity);
    expect(dimensionBill.status).toBe('posted');

    const dimensionCreditNoteCreated = await jsonRequest(
      page,
      token,
      'POST',
      '/business/credit-notes',
      {
        customer_party_id: dimensionCustomer.party_id,
        note_date: e2eDate,
        original_invoice_number: dimensionInvoice.invoice_number,
        reason: 'sales_return',
        income_account_code: '41001',
        place_of_supply: 'Karnataka',
        cost_centre_id: dimensionCostCentre.dimension_id,
        project_id: dimensionProject.dimension_id,
        accounting_entity_id: dimensionsEntity,
        line_items: [
          {
            description: 'Phase 3 E2E dimension credit note',
            hsn_sac: '9983',
            quantity: '1',
            rate: '100',
            gst_rate: '18',
            cost_centre_id: dimensionCostCentre.dimension_id,
            project_id: dimensionProject.dimension_id,
          },
        ],
      },
      { 'X-Idempotency-Key': `phase3-demo-dimension-credit-note-${runId}` }
    );
    const dimensionCreditNote = await approveIfNeeded(page, token, 'creditNote', dimensionCreditNoteCreated.credit_note_id, dimensionCreditNoteCreated, dimensionsEntity);
    expect(dimensionCreditNote.status).toBe('posted');

    const dimensionDebitNoteCreated = await jsonRequest(
      page,
      token,
      'POST',
      '/business/debit-notes',
      {
        vendor_party_id: dimensionVendor.party_id,
        note_date: e2eDate,
        original_bill_number: dimensionBill.bill_number,
        reason: 'purchase_return',
        expense_account_code: '51001',
        place_of_supply: 'Karnataka',
        cost_centre_id: dimensionCostCentre.dimension_id,
        project_id: dimensionProject.dimension_id,
        accounting_entity_id: dimensionsEntity,
        line_items: [
          {
            description: 'Phase 3 E2E dimension debit note',
            hsn_sac: '4820',
            quantity: '1',
            rate: '50',
            gst_rate: '18',
            cost_centre_id: dimensionCostCentre.dimension_id,
            project_id: dimensionProject.dimension_id,
          },
        ],
      },
      { 'X-Idempotency-Key': `phase3-demo-dimension-debit-note-${runId}` }
    );
    const dimensionDebitNote = await approveIfNeeded(page, token, 'debitNote', dimensionDebitNoteCreated.debit_note_id, dimensionDebitNoteCreated, dimensionsEntity);
    expect(dimensionDebitNote.status).toBe('posted');

    const dimensionReportQuery = `from_date=${e2eDate}&to_date=${e2eDate}&accounting_entity_id=${dimensionsEntity}`;
    const costCentreReport = await jsonRequest(page, token, 'GET', `/business/dimensions/report?dimension_type=cost_centre&${dimensionReportQuery}`);
    const costCentreRow = (costCentreReport.rows || []).find((row) => row.dimension_id === dimensionCostCentre.dimension_id);
    expect(costCentreRow?.code).toBe(dimensionCostCentre.code);
    expect(decimalValue(costCentreRow?.income)).toBe(900);
    expect(decimalValue(costCentreRow?.expense)).toBe(350);
    expect(decimalValue(costCentreRow?.net)).toBe(550);
    expect(costCentreReport.document_counts).toMatchObject({ invoices: 1, bills: 1, credit_notes: 1, debit_notes: 1 });

    const projectReport = await jsonRequest(page, token, 'GET', `/business/dimensions/report?dimension_type=project&${dimensionReportQuery}`);
    const projectRow = (projectReport.rows || []).find((row) => row.dimension_id === dimensionProject.dimension_id);
    expect(projectRow?.code).toBe(dimensionProject.code);
    expect(decimalValue(projectRow?.income)).toBe(900);
    expect(decimalValue(projectRow?.expense)).toBe(350);
    expect(decimalValue(projectRow?.net)).toBe(550);

    const primaryDimensionReport = await jsonRequest(page, token, 'GET', `/business/dimensions/report?dimension_type=cost_centre&from_date=${e2eDate}&to_date=${e2eDate}&accounting_entity_id=primary`);
    expect((primaryDimensionReport.rows || []).some((row) => row.dimension_id === dimensionCostCentre.dimension_id)).toBeFalsy();

    const dimensionExport = await fileRequest(page, token, 'GET', `/business/dimensions/report/export?dimension_type=cost_centre&format=json&${dimensionReportQuery}`);
    expectGovernedExport(dimensionExport, 'dimension_report', 'json', dimensionsEntity);
    expect(dimensionExport.headers['content-disposition']).toContain('dimension_cost_centre');
    expect(dimensionExport.text).toContain(dimensionCostCentre.code);

    for (const [kind, path, idempotencyKey] of [
      ['dimension invoice', `/business/invoices/${dimensionInvoice.invoice_id}/cancel`, `phase3-demo-dimension-invoice-cancel-${runId}`],
      ['dimension bill', `/business/bills/${dimensionBill.bill_id}/cancel`, `phase3-demo-dimension-bill-cancel-${runId}`],
      ['dimension credit note', `/business/credit-notes/${dimensionCreditNote.credit_note_id}/cancel`, `phase3-demo-dimension-credit-note-cancel-${runId}`],
      ['dimension debit note', `/business/debit-notes/${dimensionDebitNote.debit_note_id}/cancel`, `phase3-demo-dimension-debit-note-cancel-${runId}`],
    ]) {
      const reversed = await jsonRequest(
        page,
        token,
        'POST',
        path,
        { reason: `Phase 3 E2E reverse ${kind}`, cancel_date: e2eDate, accounting_entity_id: dimensionsEntity },
        { 'X-Idempotency-Key': idempotencyKey }
      );
      expect(reversed.status).toBe('cancelled');
      expect(reversed.reversal_journal_entry_id).toBeTruthy();
    }

    await jsonRequest(
      page,
      token,
      'POST',
      '/accounting/initialize-chart-of-accounts',
      undefined,
      { 'X-Accounting-Entity-ID': branchEntity }
    );
    const branchCustomer = await createParty(page, token, runId, 'customer', branchEntity);
    const branchVendor = await createParty(page, token, runId, 'vendor', branchEntity);
    const branchCostCentre = await jsonRequest(
      page,
      token,
      'POST',
      `/business/dimensions?accounting_entity_id=${branchEntity}`,
      {
        dimension_type: 'cost_centre',
        code: `BCC${runId.slice(-5)}`,
        name: `Phase 3 E2E Branch Cost Centre ${runId}`,
      }
    );
    const unmappedCostCentre = await jsonRequest(
      page,
      token,
      'POST',
      `/business/dimensions?accounting_entity_id=${branchEntity}`,
      {
        dimension_type: 'cost_centre',
        code: `BUC${runId.slice(-5)}`,
        name: `Phase 3 E2E Unmapped Cost Centre ${runId}`,
      }
    );
    const branchSettings = await jsonRequest(page, token, 'GET', `/business/admin-settings?accounting_entity_id=${branchEntity}`);
    const branchSettingsSaved = await jsonRequest(page, token, 'PUT', '/business/admin-settings', {
      organization: branchSettings.organization || {},
      branches: [
        {
          branch_code: `BR${runId.slice(-5)}`,
          branch_name: `Phase 3 E2E Branch ${runId}`,
          cost_centre_code: branchCostCentre.code,
          active: true,
        },
      ],
      roles: branchSettings.roles || [],
      permissions: branchSettings.permissions || {},
      voucher_configuration: branchSettings.voucher_configuration || {},
      financial_controls: branchSettings.financial_controls || {},
      security: branchSettings.security || {},
      templates: branchSettings.templates || {},
      notifications: branchSettings.notifications || {},
      subscription_billing: branchSettings.subscription_billing || {},
      integrations: branchSettings.integrations || {},
      ai_settings: branchSettings.ai_settings || {},
      accounting_entity_id: branchEntity,
    });
    expect(branchSettingsSaved.branches?.[0]?.cost_centre_code).toBe(branchCostCentre.code);

    const branchInvoiceCreated = await jsonRequest(
      page,
      token,
      'POST',
      '/business/invoices',
      {
        customer_party_id: branchCustomer.party_id,
        invoice_date: e2eDate,
        due_date: e2eDueDate,
        income_account_code: '41001',
        place_of_supply: 'Karnataka',
        reference: `BR-INV-${runId}`,
        cost_centre_id: branchCostCentre.dimension_id,
        accounting_entity_id: branchEntity,
        line_items: [{
          description: 'Phase 3 E2E branch mapped income',
          hsn_sac: '9983',
          quantity: '1',
          rate: '700',
          gst_rate: '18',
          cost_centre_id: branchCostCentre.dimension_id,
        }],
      },
      { 'X-Idempotency-Key': `phase3-demo-branch-invoice-${runId}` }
    );
    const branchInvoice = await approveIfNeeded(page, token, 'invoice', branchInvoiceCreated.invoice_id, branchInvoiceCreated, branchEntity);
    expect(branchInvoice.status).toBe('posted');

    const branchBillCreated = await jsonRequest(
      page,
      token,
      'POST',
      '/business/bills',
      {
        vendor_party_id: branchVendor.party_id,
        bill_number: `BR-BILL-${runId}`,
        bill_date: e2eDate,
        due_date: e2eDueDate,
        expense_account_code: '51001',
        place_of_supply: 'Karnataka',
        cost_centre_id: branchCostCentre.dimension_id,
        accounting_entity_id: branchEntity,
        line_items: [{
          description: 'Phase 3 E2E branch mapped expense',
          hsn_sac: '4820',
          quantity: '1',
          rate: '200',
          gst_rate: '18',
          cost_centre_id: branchCostCentre.dimension_id,
        }],
      },
      { 'X-Idempotency-Key': `phase3-demo-branch-bill-${runId}` }
    );
    const branchBill = await approveIfNeeded(page, token, 'bill', branchBillCreated.bill_id, branchBillCreated, branchEntity);
    expect(branchBill.status).toBe('posted');

    const unmappedBranchInvoiceCreated = await jsonRequest(
      page,
      token,
      'POST',
      '/business/invoices',
      {
        customer_party_id: branchCustomer.party_id,
        invoice_date: e2eDate,
        due_date: e2eDueDate,
        income_account_code: '41001',
        place_of_supply: 'Karnataka',
        reference: `BR-UNMAPPED-${runId}`,
        cost_centre_id: unmappedCostCentre.dimension_id,
        accounting_entity_id: branchEntity,
        line_items: [{
          description: 'Phase 3 E2E branch unmapped income',
          hsn_sac: '9983',
          quantity: '1',
          rate: '150',
          gst_rate: '18',
          cost_centre_id: unmappedCostCentre.dimension_id,
        }],
      },
      { 'X-Idempotency-Key': `phase3-demo-branch-unmapped-invoice-${runId}` }
    );
    const unmappedBranchInvoice = await approveIfNeeded(
      page,
      token,
      'invoice',
      unmappedBranchInvoiceCreated.invoice_id,
      unmappedBranchInvoiceCreated,
      branchEntity
    );
    expect(unmappedBranchInvoice.status).toBe('posted');

    const untaggedBranchBillCreated = await jsonRequest(
      page,
      token,
      'POST',
      '/business/bills',
      {
        vendor_party_id: branchVendor.party_id,
        bill_number: `BR-UNTAGGED-${runId}`,
        bill_date: e2eDate,
        due_date: e2eDueDate,
        expense_account_code: '51001',
        place_of_supply: 'Karnataka',
        accounting_entity_id: branchEntity,
        line_items: [{
          description: 'Phase 3 E2E branch untagged expense',
          hsn_sac: '4820',
          quantity: '1',
          rate: '75',
          gst_rate: '18',
        }],
      },
      { 'X-Idempotency-Key': `phase3-demo-branch-untagged-bill-${runId}` }
    );
    const untaggedBranchBill = await approveIfNeeded(
      page,
      token,
      'bill',
      untaggedBranchBillCreated.bill_id,
      untaggedBranchBillCreated,
      branchEntity
    );
    expect(untaggedBranchBill.status).toBe('posted');

    const branchReportQuery = `from_date=${e2eDate}&to_date=${e2eDate}&accounting_entity_id=${branchEntity}`;
    const branchReport = await jsonRequest(page, token, 'GET', `/business/dimensions/branch-report?${branchReportQuery}`);
    expect(branchReport.report_type).toBe('branch_consolidated');
    const branchRow = (branchReport.rows || []).find((row) => row.branch_code === `BR${runId.slice(-5)}`);
    expect(branchRow?.cost_centre_code).toBe(branchCostCentre.code);
    expect(decimalValue(branchRow?.income)).toBe(700);
    expect(decimalValue(branchRow?.expense)).toBe(200);
    expect(decimalValue(branchRow?.net)).toBe(500);
    expect(decimalValue(branchReport.unassigned?.income)).toBe(150);
    expect(decimalValue(branchReport.unassigned?.expense)).toBe(75);
    expect((branchReport.unassigned?.unmatched_cost_centres || []).some((row) => row.code === unmappedCostCentre.code)).toBeTruthy();
    expect(decimalValue(branchReport.totals?.income)).toBe(850);
    expect(decimalValue(branchReport.totals?.expense)).toBe(275);
    expect(decimalValue(branchReport.totals?.net)).toBe(575);

    const primaryBranchReport = await jsonRequest(page, token, 'GET', `/business/dimensions/branch-report?from_date=${e2eDate}&to_date=${e2eDate}&accounting_entity_id=primary`);
    expect((primaryBranchReport.rows || []).some((row) => row.branch_code === `BR${runId.slice(-5)}`)).toBeFalsy();
    expect(JSON.stringify(primaryBranchReport)).not.toContain(unmappedCostCentre.code);

    for (const [kind, path, idempotencyKey] of [
      ['branch invoice', `/business/invoices/${branchInvoice.invoice_id}/cancel`, `phase3-demo-branch-invoice-cancel-${runId}`],
      ['branch bill', `/business/bills/${branchBill.bill_id}/cancel`, `phase3-demo-branch-bill-cancel-${runId}`],
      ['branch unmapped invoice', `/business/invoices/${unmappedBranchInvoice.invoice_id}/cancel`, `phase3-demo-branch-unmapped-invoice-cancel-${runId}`],
      ['branch untagged bill', `/business/bills/${untaggedBranchBill.bill_id}/cancel`, `phase3-demo-branch-untagged-bill-cancel-${runId}`],
    ]) {
      const reversed = await jsonRequest(
        page,
        token,
        'POST',
        path,
        { reason: `Phase 3 E2E reverse ${kind}`, cancel_date: e2eDate, accounting_entity_id: branchEntity },
        { 'X-Idempotency-Key': idempotencyKey }
      );
      expect(reversed.status).toBe('cancelled');
      expect(reversed.reversal_journal_entry_id).toBeTruthy();
    }

    await jsonRequest(
      page,
      token,
      'POST',
      '/accounting/initialize-chart-of-accounts',
      undefined,
      { 'X-Accounting-Entity-ID': misHealthEntity }
    );
    const misHealthAccounts = await jsonRequest(
      page,
      token,
      'GET',
      '/accounting/accounts',
      undefined,
      { 'X-Accounting-Entity-ID': misHealthEntity }
    );
    const misHealthBankAccount = misHealthAccounts.find((account) => account.code === '11010')
      || misHealthAccounts.find((account) => account.type === 'asset' && /bank|cash/i.test(account.name || ''));
    expect(misHealthBankAccount?.id, 'MIS/Data Health bank account missing').toBeTruthy();

    const missingGstinCustomer = await jsonRequest(
      page,
      token,
      'POST',
      '/business/parties',
      {
        party_name: `E2E Data Health Customer ${runId}`,
        party_type: 'customer',
        party_code: `DH-CUST-${runId}`,
        city: 'Bengaluru',
        state: 'Karnataka',
        pincode: '560001',
        opening_balance: '0.00',
      },
      { 'X-Accounting-Entity-ID': misHealthEntity }
    );
    const misHealthVendor = await jsonRequest(
      page,
      token,
      'POST',
      '/business/parties',
      {
        party_name: `E2E MIS Vendor ${runId}`,
        party_type: 'vendor',
        party_code: `MIS-VEND-${runId}`,
        gstin: '29ABCDE1234F1Z5',
        pan: 'ABCDE1234F',
        city: 'Bengaluru',
        state: 'Karnataka',
        pincode: '560001',
        opening_balance: '0.00',
      },
      { 'X-Accounting-Entity-ID': misHealthEntity }
    );

    const misHealthInvoiceCreated = await jsonRequest(
      page,
      token,
      'POST',
      '/business/invoices',
      {
        customer_party_id: missingGstinCustomer.party_id,
        invoice_date: e2eDate,
        due_date: e2eDueDate,
        income_account_code: '41001',
        place_of_supply: 'Karnataka',
        reference: `MIS-INV-${runId}`,
        accounting_entity_id: misHealthEntity,
        line_items: [{ description: 'Phase 3 E2E MIS revenue', hsn_sac: '9983', quantity: '1', rate: '1200', gst_rate: '18' }],
      },
      { 'X-Idempotency-Key': `phase3-demo-mis-health-invoice-${runId}` }
    );
    const misHealthInvoice = await approveIfNeeded(page, token, 'invoice', misHealthInvoiceCreated.invoice_id, misHealthInvoiceCreated, misHealthEntity);
    expect(misHealthInvoice.status).toBe('posted');

    const misHealthBillCreated = await jsonRequest(
      page,
      token,
      'POST',
      '/business/bills',
      {
        vendor_party_id: misHealthVendor.party_id,
        bill_number: `MIS-BILL-${runId}`,
        bill_date: e2eDate,
        due_date: e2eDueDate,
        expense_account_code: '51001',
        place_of_supply: 'Karnataka',
        accounting_entity_id: misHealthEntity,
        line_items: [{ description: 'Phase 3 E2E MIS expense', hsn_sac: '4820', quantity: '1', rate: '500', gst_rate: '18' }],
      },
      { 'X-Idempotency-Key': `phase3-demo-mis-health-bill-${runId}` }
    );
    const misHealthBill = await approveIfNeeded(page, token, 'bill', misHealthBillCreated.bill_id, misHealthBillCreated, misHealthEntity);
    expect(misHealthBill.status).toBe('posted');

    const draftHealthInvoice = await jsonRequest(
      page,
      token,
      'POST',
      '/business/invoices',
      {
        customer_party_id: missingGstinCustomer.party_id,
        invoice_date: e2eDate,
        due_date: e2eDueDate,
        income_account_code: '41001',
        place_of_supply: 'Karnataka',
        reference: `DH-DRAFT-${runId}`,
        save_as_draft: true,
        accounting_entity_id: misHealthEntity,
        line_items: [{ description: 'Phase 3 E2E data-health draft', hsn_sac: '9983', quantity: '1', rate: '100', gst_rate: '18' }],
      },
      { 'X-Idempotency-Key': `phase3-demo-data-health-draft-${runId}` }
    );
    expect(draftHealthInvoice.status).toBe('draft');

    await jsonRequest(
      page,
      token,
      'POST',
      `/business/bank-recon/statement?account_id=${misHealthBankAccount.id}&accounting_entity_id=${misHealthEntity}`,
      [
        ['date', 'description', 'ref', 'debit', 'credit', 'balance'],
        [e2eDate, `Phase 3 E2E stale reconciliation ${runId}`, `DH-STMT-${runId}`, '', '25.00', '25.00'],
      ].map((row) => row.join(',')).join('\n')
    );

    const misHealthAsOf = '2098-09-30';
    const misHealthQuery = `as_of=${misHealthAsOf}&accounting_entity_id=${misHealthEntity}`;
    const misKpis = await jsonRequest(page, token, 'GET', `/business/mis/kpis?${misHealthQuery}`);
    expect(misKpis.accounting_entity_id).toBe(misHealthEntity);
    expect(misKpis.source).toMatchObject({
      sales_purchase_trend: 'posted_ledger',
      top_parties: 'open_item_aging',
      financial_health: 'deterministic_financial_health',
    });
    expect(decimalValue(misKpis.working_capital?.receivables)).toBeGreaterThan(0);
    expect(decimalValue(misKpis.working_capital?.payables)).toBeGreaterThan(0);
    expect((misKpis.top_customers || []).some((row) => row.party_id === missingGstinCustomer.party_id && decimalValue(row.outstanding) > 0)).toBeTruthy();
    expect((misKpis.top_vendors || []).some((row) => row.party_id === misHealthVendor.party_id && decimalValue(row.outstanding) > 0)).toBeTruthy();
    expect((misKpis.financial_health?.kpis || []).some((kpi) => kpi.key === 'working_capital')).toBeTruthy();

    const financialHealth = await jsonRequest(page, token, 'GET', `/business/financial-health?narrate=false&${misHealthQuery}`);
    expect((financialHealth.kpis || []).some((kpi) => kpi.key === 'revenue' && decimalValue(kpi.value) > 0)).toBeTruthy();
    expect((financialHealth.kpis || []).some((kpi) => kpi.key === 'working_capital')).toBeTruthy();

    const dataHealth = await jsonRequest(page, token, 'GET', `/business/data-health?${misHealthQuery}`);
    expect(dataHealth.status).toBe('needs_attention');
    expect(dataHealth.issue_count).toBeGreaterThan(0);
    expect(dataHealth.source).toMatchObject({
      overdue_exposure: 'receivables_open_item_aging',
    });
    const dataHealthRules = Object.fromEntries((dataHealth.rules || []).map((rule) => [rule.key, rule]));
    expect(dataHealthRules.missing_gstin?.status).toBe('fail');
    expect(dataHealthRules.unposted_drafts?.status).toBe('fail');
    expect(dataHealthRules.stale_reconciliation?.status).toBe('fail');
    expect(dataHealthRules.overdue_exposure?.status).toBe('fail');
    expect((dataHealth.issues || []).some((issue) => issue.rule_key === 'missing_gstin' && issue.workspace === 'parties')).toBeTruthy();
    expect((dataHealth.issues || []).some((issue) => issue.rule_key === 'unposted_drafts' && issue.workspace === 'sales')).toBeTruthy();
    expect((dataHealth.issues || []).some((issue) => issue.rule_key === 'stale_reconciliation' && issue.workspace === 'bank-recon')).toBeTruthy();
    expect((dataHealth.issues || []).some((issue) => issue.rule_key === 'overdue_exposure' && issue.workspace === 'financial-health')).toBeTruthy();

    const primaryDataHealth = await jsonRequest(page, token, 'GET', `/business/data-health?as_of=${misHealthAsOf}&accounting_entity_id=primary`);
    expect((primaryDataHealth.issues || []).some((issue) => JSON.stringify(issue).includes(missingGstinCustomer.party_id))).toBeFalsy();

    for (const [kind, path, idempotencyKey] of [
      ['MIS/Data Health invoice', `/business/invoices/${misHealthInvoice.invoice_id}/cancel`, `phase3-demo-mis-health-invoice-cancel-${runId}`],
      ['MIS/Data Health bill', `/business/bills/${misHealthBill.bill_id}/cancel`, `phase3-demo-mis-health-bill-cancel-${runId}`],
    ]) {
      const reversed = await jsonRequest(
        page,
        token,
        'POST',
        path,
        { reason: `Phase 3 E2E reverse ${kind}`, cancel_date: e2eDate, accounting_entity_id: misHealthEntity },
        { 'X-Idempotency-Key': idempotencyKey }
      );
      expect(reversed.status).toBe('cancelled');
      expect(reversed.reversal_journal_entry_id).toBeTruthy();
    }

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

    const openingExport = await fileRequest(
      page,
      token,
      'GET',
      '/business/opening-balances/export?accounting_entity_id=primary'
    );
    expectGovernedExport(openingExport, 'opening_balances', 'csv', 'primary');
    expect(openingExport.headers['content-disposition']).toContain('opening_balances.csv');
    expect(openingExport.text).toContain('account_code');
    expect(openingExport.text).toContain('11001');
    expect(openingExport.text).toContain(customer.party_code);
    expect(openingExport.text).not.toContain('Opening Balance Equity');

    await jsonRequest(
      page,
      token,
      'POST',
      '/accounting/initialize-chart-of-accounts',
      undefined,
      { 'X-Accounting-Entity-ID': inventoryEntity }
    );
    const inventorySettings = await jsonRequest(
      page,
      token,
      'GET',
      `/business/invoice-settings?accounting_entity_id=${inventoryEntity}`
    );
    const inventorySettingsPayload = {
      field_config: inventorySettings.field_config || {},
      numbering: inventorySettings.numbering || {},
      custom_fields: inventorySettings.custom_fields || [],
      branding: inventorySettings.branding || {},
      inventory_enabled: true,
      inventory_valuation_policy: 'weighted_average_periodic',
      hr_enabled: !!inventorySettings.hr_enabled,
      cost_centre_enabled: !!inventorySettings.cost_centre_enabled,
      manufacturing_enabled: !!inventorySettings.manufacturing_enabled,
      accounting_entity_id: inventoryEntity,
    };
    const inventorySettingsSaved = await jsonRequest(
      page,
      token,
      'PUT',
      '/business/invoice-settings',
      inventorySettingsPayload
    );
    expect(inventorySettingsSaved.inventory_enabled).toBe(true);

    const inventoryPolicy = await jsonRequest(
      page,
      token,
      'GET',
      `/business/inventory/policy?accounting_entity_id=${inventoryEntity}`
    );
    expect(inventoryPolicy.inventory_enabled).toBe(true);
    expect(inventoryPolicy.valuation_policy).toBe('weighted_average_periodic');

    const inventoryItem = await jsonRequest(
      page,
      token,
      'POST',
      `/business/inventory/items?accounting_entity_id=${inventoryEntity}`,
      {
        code: `E2E-STK-${runId}`,
        name: `Phase 3 E2E Stock ${runId}`,
        uqc: 'NOS',
        hsn_sac: '8471',
        gst_rate: '18',
        opening_qty: '10',
        opening_value: '1000.00',
      }
    );
    expect(inventoryItem.item_id).toBeTruthy();
    expect(inventoryItem.code).toBe(`E2E-STK-${runId}`);

    const inventoryAdjustment = await jsonRequest(
      page,
      token,
      'POST',
      `/business/inventory/movements?accounting_entity_id=${inventoryEntity}`,
      {
        movement_type: 'adjustment',
        movement_date: e2eDate,
        item_id: inventoryItem.item_id,
        quantity: '2',
        value: '300.00',
        reason: `Phase 3 E2E cycle count ${runId}`,
        reference: `INV-ADJ-${runId}`,
      }
    );
    expect(inventoryAdjustment.movement_id).toBeTruthy();

    const inventoryIssue = await jsonRequest(
      page,
      token,
      'POST',
      `/business/inventory/movements?accounting_entity_id=${inventoryEntity}`,
      {
        movement_type: 'issue',
        movement_date: e2eDate,
        item_id: inventoryItem.item_id,
        quantity: '1',
        reason: `Phase 3 E2E stock issue ${runId}`,
        reference: `INV-ISS-${runId}`,
      }
    );
    expect(inventoryIssue.movement_id).toBeTruthy();

    const stockMovements = await jsonRequest(
      page,
      token,
      'GET',
      `/business/inventory/movements?accounting_entity_id=${inventoryEntity}&as_of=${e2eDate}`
    );
    expect(stockMovements.items?.some((movement) => movement.movement_id === inventoryAdjustment.movement_id)).toBeTruthy();
    expect(stockMovements.items?.some((movement) => movement.movement_id === inventoryIssue.movement_id)).toBeTruthy();

    const stockRegister = await jsonRequest(
      page,
      token,
      'GET',
      `/business/inventory/stock-register?accounting_entity_id=${inventoryEntity}&as_of=${e2eDate}`
    );
    const stockRow = (stockRegister.rows || []).find((row) => row.item_id === inventoryItem.item_id);
    expect(stockRow?.closing_qty).toBe('11.000');
    expect(decimalValue(stockRow?.closing_value)).toBeGreaterThan(0);
    expect(stockRegister.negative_stock_items).toBe(0);
    expect(decimalValue(stockRegister.total_closing_value)).toBeGreaterThan(0);

    const closingStock = await jsonRequest(
      page,
      token,
      'POST',
      `/business/inventory/closing-stock?accounting_entity_id=${inventoryEntity}`,
      { as_of: e2eDate },
      { 'X-Idempotency-Key': `phase3-demo-closing-stock-${runId}` }
    );
    expect(closingStock.created).toBe(true);
    expect(closingStock.journal_entry_id).toBeTruthy();
    expect(closingStock.as_of).toBe(e2eDate);
    expect(decimalValue(closingStock.closing_stock_value)).toBeGreaterThan(0);

    const closingStockEntries = await jsonRequest(
      page,
      token,
      'GET',
      `/business/inventory/closing-stock/entries?accounting_entity_id=${inventoryEntity}`
    );
    expect(closingStockEntries.items?.some((entry) => entry.journal_entry_id === closingStock.journal_entry_id)).toBeTruthy();

    const closingStockReversed = await jsonRequest(
      page,
      token,
      'POST',
      `/accounting/journal/${closingStock.journal_entry_id}/reverse`,
      { entry_date: e2eDate, reason: `Phase 3 E2E reverse closing stock ${runId}` },
      {
        'X-Accounting-Entity-ID': inventoryEntity,
        'X-Idempotency-Key': `phase3-demo-closing-stock-reverse-${runId}`,
      }
    );
    expect(closingStockReversed.original_journal_id).toBe(closingStock.journal_entry_id);
    expect(closingStockReversed.id).toBeTruthy();

    const inventoryItemDeactivated = await jsonRequest(
      page,
      token,
      'PATCH',
      `/business/inventory/items/${inventoryItem.item_id}/deactivate?accounting_entity_id=${inventoryEntity}`
    );
    expect(inventoryItemDeactivated.is_active).toBe(false);

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

    const bankReconVoucherCreated = await jsonRequest(
      page,
      token,
      'POST',
      '/business/vouchers',
      {
        voucher_type: 'journal',
        entry_date: e2eDate,
        amount: bankReconAmount,
        debit_account_id: bankAccount.id,
        credit_account_id: income.id,
        description: `Phase 3 E2E bank recon ${bankReconRef}`,
        accounting_entity_id: 'primary',
      },
      { 'X-Idempotency-Key': `phase3-demo-bank-recon-voucher-${runId}` }
    );
    const bankReconVoucher = await approveIfNeeded(page, token, 'voucher', bankReconVoucherCreated.voucher_id, bankReconVoucherCreated);
    expect(bankReconVoucher.status).toBe('posted');
    expect(bankReconVoucher.journal_entry_id).toBeTruthy();

    const bankStatementCsv = [
      'Txn Date,Narration,Ref No,Withdrawal,Deposit,Balance',
      `${e2eDate},Phase 3 E2E bank recon ${bankReconRef},${bankReconRef},,${bankReconAmount},${bankReconAmount}`,
      `${e2eDate},Phase 3 E2E bank charges ${runId},CHG-${runId},12.00,,210.37`,
    ].join('\n');
    const bankStatementUpload = await jsonRequest(
      page,
      token,
      'POST',
      `/business/bank-recon/statement?account_id=${bankAccount.id}&accounting_entity_id=primary`,
      { csv: bankStatementCsv }
    );
    expect(bankStatementUpload.inserted).toBeGreaterThanOrEqual(1);
    expect(bankStatementUpload.parsed).toBe(2);
    expect(bankStatementUpload.batch_id).toBeTruthy();

    const bankReconBeforeMatch = await jsonRequest(
      page,
      token,
      'GET',
      `/business/bank-recon?account_id=${bankAccount.id}&as_of=${e2eDate}&accounting_entity_id=primary`
    );
    const bankSuggestion = (bankReconBeforeMatch.suggestions || []).find((suggestion) =>
      suggestion.statement?.ref === bankReconRef
      || String(suggestion.book?.description || '').includes(bankReconRef)
      || String(suggestion.book?.reference || '').includes(bankReconRef)
    );
    expect(bankSuggestion?.statement_line_id, 'bank reconciliation suggestion missing').toBeTruthy();
    expect(bankSuggestion?.line_id, 'bank reconciliation book line missing').toBeTruthy();
    expect(bankSuggestion.side).toBe('deposit');
    expect(decimalValue(bankSuggestion.amount)).toBe(decimalValue(bankReconAmount));
    const bankChargeLine = (bankReconBeforeMatch.in_bank_not_in_books || []).find((line) => line.ref === `CHG-${runId}`);
    expect(bankChargeLine?.statement_line_id, 'bank-only charge line missing').toBeTruthy();

    const bankChargeVoucherPost = await jsonRequest(
      page,
      token,
      'POST',
      '/business/bank-recon/statement-voucher',
      {
        account_id: bankAccount.id,
        statement_line_id: bankChargeLine.statement_line_id,
        offset_account_id: expense.id,
        description: `Phase 3 E2E bank charges ${runId}`,
        reference: `CHG-${runId}`,
        approve: true,
        accounting_entity_id: 'primary',
      },
      { 'X-Idempotency-Key': `phase3-demo-bank-charge-voucher-${runId}` }
    );
    expect(bankChargeVoucherPost.posting_status).toBe('posted');
    expect(bankChargeVoucherPost.voucher?.voucher_id).toBeTruthy();
    expect(bankChargeVoucherPost.voucher?.journal_entry_id).toBeTruthy();

    const bankReconAfterChargePost = await jsonRequest(
      page,
      token,
      'GET',
      `/business/bank-recon?account_id=${bankAccount.id}&as_of=${e2eDate}&accounting_entity_id=primary`
    );
    expect((bankReconAfterChargePost.suggestions || []).some((suggestion) => suggestion.statement?.ref === `CHG-${runId}`)).toBeTruthy();

    const bankCashBook = await jsonRequest(
      page,
      token,
      'GET',
      `/business/banking/books?from_date=${e2eDate}&to_date=${e2eDate}&book_type=bank&accounting_entity_id=primary`
    );
    expect(bankCashBook.book_type).toBe('bank');
    expect((bankCashBook.accounts || []).some((account) =>
      account.account_id === bankAccount.id
      && (account.lines || []).some((line) => line.reference === `CHG-${runId}`)
    )).toBeTruthy();
    expect(decimalValue(bankCashBook.summary?.total_receipts)).toBeGreaterThan(0);
    expect(decimalValue(bankCashBook.summary?.total_payments)).toBeGreaterThan(0);

    const bankMatch = await jsonRequest(
      page,
      token,
      'POST',
      '/business/bank-recon/match?accounting_entity_id=primary',
      {
        account_id: bankAccount.id,
        statement_line_id: bankSuggestion.statement_line_id,
        line_id: bankSuggestion.line_id,
      }
    );
    expect(bankMatch.status).toBe('active');
    expect(bankMatch.side).toBe('deposit');
    expect(decimalValue(bankMatch.amount)).toBe(decimalValue(bankReconAmount));

    const bankReconAfterMatch = await jsonRequest(
      page,
      token,
      'GET',
      `/business/bank-recon?account_id=${bankAccount.id}&as_of=${e2eDate}&accounting_entity_id=primary`
    );
    expect((bankReconAfterMatch.matched || []).some((match) => match.match_id === bankMatch.match_id)).toBeTruthy();
    expect(bankReconAfterMatch.summary?.matched_count).toBeGreaterThanOrEqual(1);

    const bankMatchReversed = await jsonRequest(
      page,
      token,
      'POST',
      `/business/bank-recon/match/${bankMatch.match_id}/reverse?accounting_entity_id=primary`
    );
    expect(bankMatchReversed.status).toBe('reversed');

    const bankReconAfterUnmatch = await jsonRequest(
      page,
      token,
      'GET',
      `/business/bank-recon?account_id=${bankAccount.id}&as_of=${e2eDate}&accounting_entity_id=primary`
    );
    expect((bankReconAfterUnmatch.matched || []).some((match) => match.match_id === bankMatch.match_id)).toBeFalsy();
    expect((bankReconAfterUnmatch.suggestions || []).some((suggestion) => suggestion.statement?.ref === bankReconRef)).toBeTruthy();

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

    const reportExport = await fileRequest(page, token, 'GET', `/business/reports/export?report=trial_balance&format=json&as_of=${e2eDate}&accounting_entity_id=primary`);
    expectGovernedExport(reportExport, 'business_report', 'json', 'primary');
    expect(reportExport.headers['content-disposition']).toContain('trial_balance');
    expect(reportExport.text).toContain('Trial Balance');

    const invoicePdf = await fileRequest(page, token, 'GET', `/business/invoices/${invoice.invoice_id}/pdf?accounting_entity_id=primary`);
    expectGovernedExport(invoicePdf, 'sales_invoice_pdf', 'pdf', 'primary');
    expect(invoicePdf.headers['content-disposition']).toContain('.pdf');
    expect(invoicePdf.text).toContain('%PDF');

    const tallyXml = await fileRequest(page, token, 'GET', `/business/tally/xml-export?as_of=${e2eDate}&accounting_entity_id=primary`);
    expectGovernedExport(tallyXml, 'tally_xml', 'xml', 'primary');
    expect(tallyXml.headers['content-disposition']).toContain('tally_trial_balance');
    expect(tallyXml.text).toContain('<SANMITRAEXPORT>');
    expect(tallyXml.text).toContain('<SOURCE>trial_balance</SOURCE>');

    const exportAudit = await jsonRequest(
      page,
      token,
      'GET',
      '/audit/events?action=business_export_downloaded&entity_type=business_export&limit=20'
    );
    const exportAuditText = JSON.stringify(exportAudit);
    expect(exportAuditText).toContain('business_report');
    expect(exportAuditText).toContain('dimension_report');
    expect(exportAuditText).toContain('opening_balances');
    expect(exportAuditText).toContain('sales_invoice_pdf');
    expect(exportAuditText).toContain('tally_xml');

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

    const bankReconVoucherReversed = await jsonRequest(
      page,
      token,
      'POST',
      `/business/vouchers/${bankReconVoucher.voucher_id}/reverse`,
      { reason: 'Phase 3 E2E reverse bank reconciliation voucher', reversal_date: e2eDate, accounting_entity_id: 'primary' },
      { 'X-Idempotency-Key': `phase3-demo-bank-recon-voucher-reverse-${runId}` }
    );
    expect(String(bankReconVoucherReversed.status).toLowerCase()).toBe('reversed');
    expect(bankReconVoucherReversed.reversal_journal_entry_id).toBeTruthy();

    const bankChargeVoucherReversed = await jsonRequest(
      page,
      token,
      'POST',
      `/business/vouchers/${bankChargeVoucherPost.voucher.voucher_id}/reverse`,
      { reason: 'Phase 3 E2E reverse bank charge voucher', reversal_date: e2eDate, accounting_entity_id: 'primary' },
      { 'X-Idempotency-Key': `phase3-demo-bank-charge-voucher-reverse-${runId}` }
    );
    expect(String(bankChargeVoucherReversed.status).toLowerCase()).toBe('reversed');
    expect(bankChargeVoucherReversed.reversal_journal_entry_id).toBeTruthy();

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
