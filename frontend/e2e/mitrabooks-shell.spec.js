const { test, expect } = require('@playwright/test');

async function mockVerifiedMitraBooksSession(page) {
  const accounts = [
    { id: 101, code: '1001', name: 'Cash in Hand', account_type: 'asset', type: 'asset' },
    { id: 201, code: '4001', name: 'Sales', account_type: 'revenue', type: 'revenue' },
    { id: 301, code: '5001', name: 'Office Expense', account_type: 'expense', type: 'expense' },
  ];
  const parties = [
    {
      party_id: 'p1',
      party_name: 'Karnataka Office Supplies',
      party_type: 'vendor',
      party_code: 'VEND-001',
      gstin: '29ABCDE1234F1Z5',
      balance_source: 'ledger_reports',
      is_active: true,
    },
    {
      party_id: 'p2',
      party_name: 'Bengaluru Retail Customer',
      party_type: 'customer',
      party_code: 'CUST-001',
      gstin: '29BBBBB0000B1Z5',
      balance_source: 'ledger_reports',
      is_active: true,
    },
  ];
  const vouchers = [];
  const invoices = [];
  const bills = [];
  const creditNotes = [];
  const debitNotes = [];
  const caDocuments = [];
  const caClients = [];
  const json = (route, body, status = 200) => route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  });
  const computeLine = (line, isInterState = false) => {
    const taxable = Number(line.quantity || 0) * Number(line.rate || 0);
    const gst = taxable * Number(line.gst_rate || 0) / 100;
    return {
      ...line,
      taxable_amount: taxable,
      cgst_total: isInterState ? 0 : gst / 2,
      sgst_total: isInterState ? 0 : gst / 2,
      igst_total: isInterState ? gst : 0,
      cgst_amount: isInterState ? 0 : gst / 2,
      sgst_amount: isInterState ? 0 : gst / 2,
      igst_amount: isInterState ? gst : 0,
      line_total: taxable + gst,
    };
  };

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
    body: JSON.stringify(accounts),
  }));
  await page.route('**/api/v1/business/parties**', async route => {
    const request = route.request();
    const method = request.method();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path.endsWith('/outstanding')) {
      return json(route, { party_id: path.split('/').at(-2), balance: '0.00', open_items: [] });
    }

    if (method === 'POST' && path.endsWith('/deactivate')) {
      const partyId = path.split('/').at(-2);
      const party = parties.find(item => item.party_id === partyId);
      if (!party) return json(route, { detail: 'Party not found' }, 404);
      party.is_active = false;
      party.is_inactive = true;
      party.status = 'inactive';
      return json(route, party);
    }

    if (method === 'PATCH') {
      const partyId = path.split('/').at(-1);
      const party = parties.find(item => item.party_id === partyId);
      if (!party) return json(route, { detail: 'Party not found' }, 404);
      const payload = request.postDataJSON();
      Object.assign(party, {
        party_name: payload.party_name ?? party.party_name,
        party_type: payload.party_type ?? party.party_type,
        gstin: payload.gstin ?? '',
        pan: payload.pan ?? '',
        city: payload.city ?? '',
        state: payload.state ?? '',
        pincode: payload.pincode ?? '',
      });
      return json(route, party);
    }

    if (method === 'POST') {
      const payload = request.postDataJSON();
      const party = {
        party_id: `p${parties.length + 1}`,
        party_code: `AUTO-${parties.length + 1}`,
        party_name: payload.party_name,
        party_type: payload.party_type || 'customer',
        gstin: payload.gstin || '',
        pan: payload.pan || '',
        city: payload.city || '',
        state: payload.state || '',
        pincode: payload.pincode || '',
        balance_source: 'ledger_reports',
        opening_balance: '0.00',
        current_balance: '0.00',
        is_active: true,
      };
      parties.push(party);
      return json(route, party);
    }

    return json(route, { items: parties.filter(party => party.is_active !== false && !party.is_inactive) });
  });
  await page.route('**/api/v1/business/vouchers**', async route => {
    const request = route.request();
    const method = request.method();
    const url = new URL(request.url());
    const path = url.pathname;

    if (method === 'POST' && path.endsWith('/reverse')) {
      const voucherId = path.split('/').at(-2);
      const voucher = vouchers.find(item => item.voucher_id === voucherId);
      if (!voucher) return json(route, { detail: 'Voucher not found' }, 404);
      voucher.status = 'reversed';
      voucher.reversal_journal_entry_id = `rev-${voucherId}`;
      return json(route, voucher);
    }

    if (method === 'POST') {
      const payload = request.postDataJSON();
      const voucher = {
        voucher_id: `v${vouchers.length + 1}`,
        voucher_type: payload.voucher_type || 'journal',
        entry_date: payload.entry_date,
        reference: payload.reference || `JV-${String(vouchers.length + 1).padStart(3, '0')}`,
        description: payload.description || 'Business voucher',
        total_debit: Number(payload.amount || 0),
        total_credit: Number(payload.amount || 0),
        amount: Number(payload.amount || 0),
        status: 'posted',
        journal_entry_id: `je-${vouchers.length + 1}`,
      };
      vouchers.push(voucher);
      return json(route, voucher);
    }

    return json(route, { items: vouchers });
  });
  await page.route('**/api/v1/business/invoice-settings**', route => json(route, {
    field_config: {
      due_date: { visible: true, required: false },
      place_of_supply: { visible: true, required: false },
      reference: { visible: true, required: false },
      notes: { visible: true, required: false },
      hsn_sac: { visible: true, required: false },
    },
    numbering: { prefix: 'INV', number_format: '{PREFIX}-{FY}-{SEQ}', seq_padding: 3, start_number: 1 },
    branding: {},
  }));
  await page.route('**/api/v1/business/admin-settings**', async route => {
    const request = route.request();
    if (request.method() === 'PUT') {
      return json(route, request.postDataJSON());
    }
    return json(route, {
      organization: { legal_name: 'Acme Corp Ltd', trade_name: 'Acme' },
      branches: [],
      roles: [],
      permissions: { module_permissions: {}, action_permissions: {} },
      voucher_configuration: { journal_prefix: 'JV' },
      financial_controls: {},
      security: {},
      templates: {},
      notifications: {},
      subscription_billing: {},
      integrations: { payment_gateway_provider: 'razorpay', document_storage_provider: 'local_filesystem' },
      ai_settings: { document_review_required: true, posting_review_required: true, auto_post_to_ledger: false },
    });
  });
  await page.route('**/api/v1/business/ca-clients**', async route => {
    const request = route.request();
    if (request.method() === 'POST') {
      const payload = request.postDataJSON();
      const client = {
        client_id: `caclient${caClients.length + 1}`,
        tenant_id: 'demo-mitrabooks-business',
        app_key: 'mitrabooks',
        accounting_entity_id: 'primary',
        client_name: payload.client_name,
        gstin: payload.gstin || '',
        pan: payload.pan || '',
        contact_person: payload.contact_person || '',
        assigned_to: payload.assigned_to || '',
        client_owner: payload.client_owner || '',
        engagement_type: payload.engagement_type || '',
        access_level: payload.access_level || 'view_only',
        compliance_tracks: payload.compliance_tracks || [],
        notes: payload.notes || '',
        active: true,
        created_by: 'businessadmin@sanmitra.local',
        updated_by: '',
        created_at: '2026-06-14T00:00:00Z',
        updated_at: '2026-06-14T00:00:00Z',
      };
      caClients.push(client);
      return json(route, client);
    }
    return json(route, { items: caClients, total: caClients.length });
  });
  await page.route('**/api/v1/business/ca-documents**', async route => {
    const request = route.request();
    const method = request.method();
    const url = new URL(request.url());
    const path = url.pathname;

    if (method === 'PATCH') {
      const documentId = path.split('/').at(-1);
      const document = caDocuments.find(item => item.document_id === documentId);
      if (!document) return json(route, { detail: 'Document not found' }, 404);
      const payload = request.postDataJSON();
      document.status = payload.status || document.status;
      document.next_action = document.status === 'under_review'
        ? 'Complete document review'
        : document.status === 'query_raised'
          ? 'Await client clarification'
          : document.status === 'reviewed'
            ? 'Ready for posting'
            : document.status === 'posted'
              ? 'Linked to posting reference'
              : 'Classify document and assign reviewer';
      return json(route, document);
    }

    if (method === 'POST') {
      const payload = request.postDataJSON();
      const document = {
        document_id: `cadoc${caDocuments.length + 1}`,
        tenant_id: 'demo-mitrabooks-business',
        app_key: 'mitrabooks',
        accounting_entity_id: 'primary',
        client_name: payload.client_name,
        document_type: payload.document_type,
        period: payload.period,
        status: 'uploaded',
        assigned_to: payload.assigned_to || '',
        original_file_name: payload.original_file_name || '',
        next_action: 'Classify document and assign reviewer',
        posting_reference: '',
        notes: payload.notes || '',
        created_by: 'businessadmin@sanmitra.local',
        updated_by: '',
        created_at: '2026-06-14T00:00:00Z',
        updated_at: '2026-06-14T00:00:00Z',
      };
      caDocuments.push(document);
      return json(route, document);
    }

    return json(route, { items: caDocuments, total: caDocuments.length });
  });
  await page.route('**/api/v1/business/tds/sections**', route => json(route, { items: [] }));
  await page.route('**/api/v1/business/dimensions**', route => json(route, { items: [] }));
  await page.route('**/api/v1/business/inventory/items**', route => json(route, { items: [] }));
  await page.route('**/api/v1/business/invoices**', async route => {
    const request = route.request();
    const method = request.method();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path.endsWith('/einvoice')) {
      return json(route, { available: false, detail: 'E-invoice not configured for smoke data' });
    }

    if (method === 'POST' && path.endsWith('/cancel')) {
      const invoiceId = path.split('/').at(-2);
      const invoice = invoices.find(item => item.invoice_id === invoiceId);
      if (!invoice) return json(route, { detail: 'Invoice not found' }, 404);
      invoice.status = 'cancelled';
      invoice.reversal_journal_entry_id = `rev-${invoiceId}`;
      invoice.cancel_reason = 'Reversal';
      return json(route, invoice);
    }

    if (method === 'GET' && !path.endsWith('/invoices')) {
      const invoiceId = path.split('/').at(-1);
      const invoice = invoices.find(item => item.invoice_id === invoiceId);
      return invoice ? json(route, invoice) : json(route, { detail: 'Invoice not found' }, 404);
    }

    if (method === 'POST') {
      const payload = request.postDataJSON();
      const customer = parties.find(party => party.party_id === payload.customer_party_id);
      const lineItems = (payload.line_items || []).map((line) => computeLine(line, !!payload.is_inter_state));
      const taxableTotal = lineItems.reduce((sum, line) => sum + Number(line.taxable_amount || 0), 0);
      const gstTotal = lineItems.reduce((sum, line) => sum + Number(line.cgst_amount || 0) + Number(line.sgst_amount || 0) + Number(line.igst_amount || 0), 0);
      const invoice = {
        invoice_id: `inv${invoices.length + 1}`,
        invoice_number: `INV-2026-${String(invoices.length + 1).padStart(3, '0')}`,
        invoice_date: payload.invoice_date,
        due_date: payload.due_date,
        customer_party_id: payload.customer_party_id,
        customer_name: customer?.party_name || payload.customer_party_id,
        customer_gstin: customer?.gstin || '',
        taxable_total: taxableTotal,
        cgst_total: gstTotal / 2,
        sgst_total: gstTotal / 2,
        igst_total: 0,
        gst_total: gstTotal,
        invoice_total: taxableTotal + gstTotal,
        total_amount: taxableTotal + gstTotal,
        status: 'posted',
        line_items: lineItems,
        is_inter_state: !!payload.is_inter_state,
        reference: payload.reference || '',
        journal_entry_id: `je-inv-${invoices.length + 1}`,
      };
      invoices.push(invoice);
      return json(route, invoice);
    }

    return json(route, { items: invoices });
  });
  await page.route('**/api/v1/business/bills**', async route => {
    const request = route.request();
    const method = request.method();
    const url = new URL(request.url());
    const path = url.pathname;

    if (method === 'POST' && path.endsWith('/cancel')) {
      const billId = path.split('/').at(-2);
      const bill = bills.find(item => item.bill_id === billId);
      if (!bill) return json(route, { detail: 'Bill not found' }, 404);
      bill.status = 'cancelled';
      bill.reversal_journal_entry_id = `rev-${billId}`;
      bill.cancel_reason = 'Reversal';
      return json(route, bill);
    }

    if (method === 'GET' && !path.endsWith('/bills')) {
      const billId = path.split('/').at(-1);
      const bill = bills.find(item => item.bill_id === billId);
      return bill ? json(route, bill) : json(route, { detail: 'Bill not found' }, 404);
    }

    if (method === 'POST') {
      const payload = request.postDataJSON();
      const vendor = parties.find(party => party.party_id === payload.vendor_party_id);
      const lineItems = (payload.line_items || []).map((line) => computeLine(line, !!payload.is_inter_state));
      const taxableTotal = lineItems.reduce((sum, line) => sum + Number(line.taxable_amount || 0), 0);
      const gstTotal = lineItems.reduce((sum, line) => sum + Number(line.cgst_amount || 0) + Number(line.sgst_amount || 0) + Number(line.igst_amount || 0), 0);
      const bill = {
        bill_id: `bill${bills.length + 1}`,
        bill_number: payload.bill_number,
        bill_date: payload.bill_date,
        due_date: payload.due_date,
        vendor_party_id: payload.vendor_party_id,
        vendor_name: vendor?.party_name || payload.vendor_party_id,
        vendor_gstin: vendor?.gstin || '',
        taxable_total: taxableTotal,
        cgst_total: gstTotal / 2,
        sgst_total: gstTotal / 2,
        igst_total: 0,
        gst_total: gstTotal,
        bill_total: taxableTotal + gstTotal,
        status: 'posted',
        line_items: lineItems,
        is_inter_state: !!payload.is_inter_state,
        is_reverse_charge: !!payload.is_reverse_charge,
        journal_entry_id: `je-bill-${bills.length + 1}`,
      };
      bills.push(bill);
      return json(route, bill);
    }

    return json(route, { items: bills });
  });
  await page.route('**/api/v1/business/credit-notes**', async route => {
    const request = route.request();
    const method = request.method();
    const url = new URL(request.url());
    const path = url.pathname;

    if (method === 'POST' && path.endsWith('/cancel')) {
      const noteId = path.split('/').at(-2);
      const note = creditNotes.find(item => item.credit_note_id === noteId);
      if (!note) return json(route, { detail: 'Credit note not found' }, 404);
      note.status = 'cancelled';
      note.reversal_journal_entry_id = `rev-${noteId}`;
      note.cancel_reason = 'Reversal';
      return json(route, note);
    }

    if (method === 'GET' && !path.endsWith('/credit-notes')) {
      const noteId = path.split('/').at(-1);
      const note = creditNotes.find(item => item.credit_note_id === noteId);
      return note ? json(route, note) : json(route, { detail: 'Credit note not found' }, 404);
    }

    if (method === 'POST') {
      const payload = request.postDataJSON();
      const customer = parties.find(party => party.party_id === payload.customer_party_id);
      const lineItems = (payload.line_items || []).map((line) => computeLine(line, !!payload.is_inter_state));
      const taxableTotal = lineItems.reduce((sum, line) => sum + Number(line.taxable_amount || 0), 0);
      const gstTotal = lineItems.reduce((sum, line) => sum + Number(line.cgst_amount || 0) + Number(line.sgst_amount || 0) + Number(line.igst_amount || 0), 0);
      const note = {
        credit_note_id: `cn${creditNotes.length + 1}`,
        credit_note_number: `CN-2026-${String(creditNotes.length + 1).padStart(3, '0')}`,
        customer_party_id: payload.customer_party_id,
        customer_name: customer?.party_name || payload.customer_party_id,
        customer_gstin: customer?.gstin || '',
        note_date: payload.note_date,
        original_invoice_number: payload.original_invoice_number || '',
        reason: payload.reason || 'sales_return',
        income_account_code: payload.income_account_code || '4001',
        place_of_supply: payload.place_of_supply || '',
        taxable_total: taxableTotal,
        cgst_total: gstTotal / 2,
        sgst_total: gstTotal / 2,
        igst_total: 0,
        gst_total: gstTotal,
        note_total: taxableTotal + gstTotal,
        status: 'posted',
        line_items: lineItems,
        is_inter_state: !!payload.is_inter_state,
        journal_entry_id: `je-cn-${creditNotes.length + 1}`,
      };
      creditNotes.push(note);
      return json(route, note);
    }

    return json(route, { items: creditNotes });
  });
  await page.route('**/api/v1/business/debit-notes**', async route => {
    const request = route.request();
    const method = request.method();
    const url = new URL(request.url());
    const path = url.pathname;

    if (method === 'POST' && path.endsWith('/cancel')) {
      const noteId = path.split('/').at(-2);
      const note = debitNotes.find(item => item.debit_note_id === noteId);
      if (!note) return json(route, { detail: 'Debit note not found' }, 404);
      note.status = 'cancelled';
      note.reversal_journal_entry_id = `rev-${noteId}`;
      note.cancel_reason = 'Reversal';
      return json(route, note);
    }

    if (method === 'GET' && !path.endsWith('/debit-notes')) {
      const noteId = path.split('/').at(-1);
      const note = debitNotes.find(item => item.debit_note_id === noteId);
      return note ? json(route, note) : json(route, { detail: 'Debit note not found' }, 404);
    }

    if (method === 'POST') {
      const payload = request.postDataJSON();
      const vendor = parties.find(party => party.party_id === payload.vendor_party_id);
      const lineItems = (payload.line_items || []).map((line) => computeLine(line, !!payload.is_inter_state));
      const taxableTotal = lineItems.reduce((sum, line) => sum + Number(line.taxable_amount || 0), 0);
      const gstTotal = lineItems.reduce((sum, line) => sum + Number(line.cgst_amount || 0) + Number(line.sgst_amount || 0) + Number(line.igst_amount || 0), 0);
      const note = {
        debit_note_id: `dn${debitNotes.length + 1}`,
        debit_note_number: `DN-2026-${String(debitNotes.length + 1).padStart(3, '0')}`,
        vendor_party_id: payload.vendor_party_id,
        vendor_name: vendor?.party_name || payload.vendor_party_id,
        vendor_gstin: vendor?.gstin || '',
        note_date: payload.note_date,
        original_bill_number: payload.original_bill_number || '',
        reason: payload.reason || 'purchase_return',
        expense_account_code: payload.expense_account_code || '5001',
        place_of_supply: payload.place_of_supply || '',
        taxable_total: taxableTotal,
        cgst_total: gstTotal / 2,
        sgst_total: gstTotal / 2,
        igst_total: 0,
        gst_total: gstTotal,
        note_total: taxableTotal + gstTotal,
        status: 'posted',
        line_items: lineItems,
        is_inter_state: !!payload.is_inter_state,
        journal_entry_id: `je-dn-${debitNotes.length + 1}`,
      };
      debitNotes.push(note);
      return json(route, note);
    }

    return json(route, { items: debitNotes });
  });
  await page.route('**/api/v1/business/financial-health**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      summary: 'Ledger-backed health indicators are available for review.',
      as_of: '2026-06-13',
      financial_year_start: '2026-04-01',
      kpis: [
        { label: 'Working capital', value: 'Demo', tone: 'neutral', detail: 'Static shell smoke data' },
      ],
      alerts: [],
      charts: [],
    }),
  }));
  await page.route('**/api/v1/business/returns/**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ period: '2026-06', rows: [], summary: {} }),
  }));
  await page.route('**/api/v1/business/tds/register**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ quarter: 'Q1', rows: [], summary: {} }),
  }));
  await page.route('**/api/v1/business/bank-recon**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ account_id: 'cash', rows: [], summary: {} }),
  }));
  await page.route('**/api/v1/accounting/reports/drilldown**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ summary: { voucher_count: 0 }, items: [] }),
  }));
  await page.route('**/api/v1/accounting/reports/**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ rows: [], totals: {}, summary: {} }),
  }));
}

test.describe('MitraBooks ERP static shell', () => {
  test('shows login validation and password toggle before sign in', async ({ page }) => {
    await page.goto('/mitrabooks-erp/index.html');

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

    await page.goto('/mitrabooks-erp/index.html');

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
    await page.goto('/mitrabooks-erp/index.html');

    await expect(page).toHaveTitle('MitraBooks Pro');
    await expect(page.locator('#brand-title')).toContainText('MitraBooks Pro');
    await expect(page.locator('#brand-subtitle')).toContainText('Unified Enterprise ERP');
    await expect(page.getByRole('button', { name: 'Platform Owner' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'MandirMitra' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'GruhaMitra' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Main Workspaces' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Expenses (Purchases)' })).toBeVisible();
    await expect(page.locator('nav#nav a[data-business-workspace="bills"]')).toHaveAttribute('aria-disabled', 'false');
    await page.getByRole('button', { name: 'Expenses (Purchases)' }).click();
    await expect(page.locator('nav#nav a[data-business-workspace="bills"]')).toBeHidden();
    await page.getByRole('button', { name: 'Expenses (Purchases)' }).click();
    await expect(page.locator('nav#nav a[data-business-workspace="bills"]')).toBeVisible();
    await expect(page.locator('#access-panel')).toBeHidden();
    await expect(page.locator('#context-cards')).toBeHidden();
    await expect(page.locator('.business-dashboard-clean')).toBeVisible();
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
    await expect(page.locator('.business-bottom-metrics')).toBeVisible();
    await expect(page.locator('.business-quick-actions-clean')).toBeVisible();
    await expect(page.locator('.business-quick-actions-clean')).toContainText('Journal');
    await expect(page.locator('.business-recent-activity-clean')).toBeVisible();
    await expect(page.locator('.business-recent-activity-clean')).toContainText('Recent Activity');

    // Dashboard is verified as visible, now test workspace navigation
    await page.locator('nav#nav a[data-business-workspace="parties"]').click();
    await expect(page.locator('.erp-workspace-panel')).toContainText('Parties');
    await expect(page.locator('.erp-workspace-panel').getByRole('button', { name: '+ New Party' })).toBeVisible();

    await page.locator('.erp-workspace-panel').getByRole('button', { name: '+ New Party' }).click();
    await expect(page.locator('#business-party-create-dialog')).toBeVisible();
    await page.locator('#business-party-type').selectOption('customer');
    await page.locator('#business-party-name').fill('Alpha Consulting');
    await page.locator('#business-party-gstin').fill('29AAAAA0000A1Z5');
    await page.locator('#business-party-pan').fill('AAAAA0000A');
    await page.locator('#business-party-city').fill('Bengaluru');
    await page.locator('#business-party-state').fill('Karnataka');
    await page.locator('#business-party-pincode').fill('560001');
    await page.locator('#business-party-create-form').getByRole('button', { name: 'Create Party' }).click();
    await expect(page.locator('#business-party-create-dialog')).toBeHidden();
    await expect(page.locator('.erp-workspace-panel')).toContainText('Alpha Consulting');
    await expect(page.locator('.erp-workspace-panel')).toContainText('Ledger reports');

    let alphaRow = page.getByRole('row', { name: /Alpha Consulting/ });
    await alphaRow.getByRole('button', { name: 'Edit' }).click();
    await expect(page.locator('#business-party-edit-dialog')).toBeVisible();
    await page.locator('#business-party-edit-type').selectOption('both');
    await page.locator('#business-party-edit-name').fill('Alpha Consulting Updated');
    await page.locator('#business-party-edit-form').getByRole('button', { name: 'Save Changes' }).click();
    await expect(page.locator('#business-party-edit-dialog')).toBeHidden();
    await expect(page.locator('.erp-workspace-panel')).toContainText('Alpha Consulting Updated');
    await expect(page.locator('.erp-workspace-panel')).toContainText('both');

    alphaRow = page.getByRole('row', { name: /Alpha Consulting Updated/ });
    page.once('dialog', dialog => dialog.accept());
    await alphaRow.getByRole('button', { name: 'Deactivate' }).click();
    await expect(page.locator('#login-status')).toContainText('Party deactivated');
    await expect(page.getByRole('row', { name: /Alpha Consulting Updated/ })).toHaveCount(0);

    await page.locator('nav#nav a[data-business-workspace="vouchers"]').click();
    await expect(page.locator('.erp-workspace-panel')).toContainText('Vouchers');
    await expect(page.getByRole('button', { name: '+ New Voucher' })).toBeVisible();

    await page.getByRole('button', { name: '+ New Voucher' }).click();
    await expect(page.locator('#business-voucher-create-dialog')).toBeVisible();
    await page.locator('#business-voucher-type-select').selectOption('receipt');
    await expect(page.locator('.voucher-entry-line')).toHaveCount(2);
    await expect(page.locator('.voucher-entry-line.debit-line')).toContainText('Bank / cash ledger');
    await expect(page.locator('.voucher-entry-line.credit-line')).toContainText('Customer receivable / party ledger');
    await expect(page.locator('.account-picker-select[data-field-id="business-voucher-debit-account"]')).toBeVisible();
    await expect(page.locator('.account-picker-select[data-field-id="business-voucher-credit-account"]')).toBeVisible();
    await expect(page.locator('.account-search-input[data-field-id="business-voucher-debit-account"]')).toBeVisible();
    await expect(page.locator('.account-search-input[data-field-id="business-voucher-credit-account"]')).toBeVisible();
    await expect(page.locator('.voucher-balance-panel')).toBeVisible();
    await expect(page.locator('#business-voucher-balance')).toHaveClass(/imbalanced/);
    await expect(page.locator('#business-voucher-submit')).toBeDisabled();

    await page.locator('#business-voucher-create-close').click();

    await page.getByRole('button', { name: '+ New Voucher' }).click();
    await expect(page.locator('#business-voucher-create-dialog')).toBeVisible();
    await page.locator('#business-voucher-type-select').selectOption('journal');
    await page.locator('#business-voucher-description').fill('Browser verified balanced journal');
    await page.locator('#business-voucher-lines .account-picker-select').nth(0).selectOption('101');
    await page.locator('#business-voucher-lines .account-picker-select').nth(1).selectOption('201');
    await page.locator('#business-voucher-lines .voucher-debit').nth(0).fill('125.00');
    await page.locator('#business-voucher-lines .voucher-credit').nth(1).fill('125.00');
    await expect(page.locator('#business-voucher-balance')).toHaveClass(/balanced/);
    await expect(page.locator('#business-voucher-submit')).toBeEnabled();
    await page.locator('#business-voucher-submit').click();
    await expect(page.locator('#business-voucher-create-dialog')).toBeHidden();
    await expect(page.locator('.erp-workspace-panel')).toContainText('JV-001');
    await expect(page.getByRole('row', { name: /JV-001/ })).toContainText('posted');

    const voucherRow = page.getByRole('row', { name: /JV-001/ });
    page.once('dialog', dialog => dialog.accept());
    await voucherRow.getByRole('button', { name: 'Reverse' }).click();
    await expect(page.locator('#login-status')).toContainText('Voucher reversed');
    await expect(page.getByRole('row', { name: /JV-001/ })).toContainText('reversed');

    await page.locator('nav#nav a[data-business-workspace="accounting"]').click();
    await expect(page.locator('.accounting-drilldown-panel')).toBeVisible();
    await expect(page.locator('.accounting-drilldown-panel')).toContainText('Monthly Voucher Drill Down');

    const enabledWorkspaces = [
      ['sales', 'Sales Invoices', '+ New Invoice'],
      ['bills', 'Purchase Bills', '+ New Bill'],
      ['credit-notes', 'Credit Notes', '+ New Credit Note'],
      ['debit-notes', 'Debit Notes', '+ New Debit Note'],
      ['reports', 'Financial Reports', 'Trial Balance'],
      ['gst-returns', 'GST Returns', 'GSTR'],
      ['reconciliation', 'Reconciliation', 'Payment Allocation'],
      ['tds-tcs', 'TDS / TCS', 'TDS'],
      ['bank-recon', 'Bank Reconciliation', 'Bank Reconciliation'],
      ['financial-health', 'Financial Health', 'Refresh'],
      ['ca-access', 'CA Practice Portal', 'Document Metadata'],
      ['settings', 'MitraBooks Settings', 'Business suite'],
    ];

    for (const [workspace, heading, marker] of enabledWorkspaces) {
      await page.locator(`nav#nav a[data-business-workspace="${workspace}"]`).click();
      await expect(page.locator('.erp-workspace-panel')).toContainText(heading);
      await expect(page.locator('.erp-workspace-panel')).toContainText(marker);
    }

    await page.locator('[data-settings-card="organization"]').getByRole('button', { name: 'Open Setup' }).click();
    await expect(page.locator('[data-settings-detail="organization"]')).toContainText('Organization');
    await expect(page.locator('[data-settings-detail="organization"]')).toContainText('Tenant-scoped setup');
    await page.getByRole('button', { name: 'Back to Settings' }).click();
    await expect(page.locator('[data-settings-detail="organization"]')).toBeHidden();
    await page.locator('[data-settings-card="chart-of-accounts"]').getByRole('button', { name: 'Open Related Area' }).click();
    await expect(page.locator('.accounting-drilldown-panel')).toContainText('Monthly Voucher Drill Down');

    const caClientsLoaded = page.waitForResponse(response =>
      response.url().includes('/api/v1/business/ca-clients') &&
      response.request().method() === 'GET'
    ).catch(() => null);
    await page.locator('nav#nav a[data-business-workspace="ca-access"]').click();
    await expect(page.locator('.erp-workspace-panel')).toContainText('CA Practice Portal');
    await caClientsLoaded;
    const caClientForm = page.locator('[data-ca-client-form]');
    await expect(caClientForm.locator('input[name="client_name"]')).toBeVisible();
    await caClientForm.locator('input[name="client_name"]').fill('Jayam Publications');
    await caClientForm.locator('input[name="gstin"]').fill('29ABCDE1234F1Z5');
    await caClientForm.locator('input[name="contact_person"]').fill('Mr Jayam');
    await caClientForm.locator('input[name="assigned_to"]').fill('Staff A');
    await caClientForm.locator('input[name="client_owner"]').fill('Partner A');
    await caClientForm.locator('input[name="engagement_type"]').fill('GST and bookkeeping');
    await caClientForm.locator('input[name="compliance_tracks"]').fill('GST, TDS');
    await expect(caClientForm.locator('input[name="client_name"]')).toHaveValue('Jayam Publications');
    await Promise.all([
      page.waitForResponse(response =>
        response.url().includes('/api/v1/business/ca-clients') &&
        response.request().method() === 'POST'
      ),
      caClientForm.locator('button[type="submit"]').click(),
    ]);
    await expect(page.locator('.erp-workspace-panel')).toContainText('Jayam Publications');

    await page.locator('nav#nav a[data-business-workspace="sales"]').click();
    await page.locator('.erp-workspace-panel').getByRole('button', { name: '+ New Invoice' }).click();
    await expect(page.locator('[data-invoice-form]')).toBeVisible();
    await page.locator('[data-invoice-form] select[name="customer_party_id"]').selectOption('p2');
    await page.locator('[data-invoice-form] input[name="invoice_date"]').fill('2026-06-13');
    await page.locator('[data-invoice-form] input[name="due_date"]').fill('2026-06-30');
    await page.locator('[data-invoice-form] select[name="income_account_code"]').selectOption('4001');
    await page.locator('[data-invoice-form] input[name="place_of_supply"]').fill('Karnataka');
    await page.locator('[data-invoice-form] input[name="reference"]').fill('PO-100');
    await page.locator('[data-invoice-line] input[name="description"]').fill('Consulting service');
    await page.locator('[data-invoice-line] input[name="hsn_sac"]').fill('9983');
    await page.locator('[data-invoice-line] input[name="quantity"]').fill('2');
    await page.locator('[data-invoice-line] input[name="rate"]').fill('1000');
    await page.locator('[data-invoice-line] input[name="gst_rate"]').fill('18');
    await expect(page.locator('[data-total-invoice]')).toContainText('2,360');
    await page.getByRole('button', { name: 'Post Invoice' }).click();
    await expect(page.locator('#login-status')).toContainText('Invoice posted');
    await expect(page.locator('.erp-workspace-panel')).toContainText('INV-2026-001');
    await expect(page.getByRole('row', { name: /INV-2026-001/ })).toContainText('posted');

    await page.getByRole('row', { name: /INV-2026-001/ }).getByRole('button', { name: 'View' }).click();
    await expect(page.locator('.erp-workspace-panel')).toContainText('Invoice INV-2026-001');
    await expect(page.locator('.erp-workspace-panel')).toContainText('Consulting service');
    await page.getByRole('button', { name: 'Reverse Invoice' }).click();
    await expect(page.locator('.reversal-panel')).toBeVisible();
    await page.locator('[data-reversal-date]').fill('2026-06-13');
    await page.getByRole('button', { name: 'Confirm reverse' }).click();
    await expect(page.locator('#login-status')).toContainText('Invoice reversed');
    await expect(page.locator('.erp-workspace-panel')).toContainText('reversed');

    await page.locator('nav#nav a[data-business-workspace="bills"]').click();
    await page.locator('.erp-workspace-panel').getByRole('button', { name: '+ New Bill' }).click();
    await expect(page.locator('[data-bill-form]')).toBeVisible();
    await page.locator('[data-bill-form] select[name="vendor_party_id"]').selectOption('p1');
    await page.locator('[data-bill-form] input[name="bill_number"]').fill('BILL-100');
    await page.locator('[data-bill-form] input[name="bill_date"]').fill('2026-06-13');
    await page.locator('[data-bill-form] input[name="due_date"]').fill('2026-06-30');
    await page.locator('[data-bill-form] select[name="expense_account_code"]').selectOption('5001');
    await page.locator('[data-bill-form] input[name="place_of_supply"]').fill('Karnataka');
    await page.locator('[data-bill-line] input[name="description"]').fill('Office supplies');
    await page.locator('[data-bill-line] input[name="hsn_sac"]').fill('4820');
    await page.locator('[data-bill-line] input[name="quantity"]').fill('3');
    await page.locator('[data-bill-line] input[name="rate"]').fill('500');
    await page.locator('[data-bill-line] input[name="gst_rate"]').fill('18');
    await expect(page.locator('[data-total-bill]')).toContainText('1,770');
    await page.getByRole('button', { name: 'Post Bill' }).click();
    await expect(page.locator('#login-status')).toContainText('Bill posted');
    await expect(page.locator('.erp-workspace-panel')).toContainText('BILL-100');
    await expect(page.getByRole('row', { name: /BILL-100/ })).toContainText('posted');

    await page.getByRole('row', { name: /BILL-100/ }).getByRole('button', { name: 'View' }).click();
    await expect(page.locator('.erp-workspace-panel')).toContainText('Bill BILL-100');
    await expect(page.locator('.erp-workspace-panel')).toContainText('Office supplies');
    await page.getByRole('button', { name: 'Reverse Bill' }).click();
    await expect(page.locator('.reversal-panel')).toBeVisible();
    await page.locator('[data-reversal-date]').fill('2026-06-13');
    await page.getByRole('button', { name: 'Confirm reverse' }).click();
    await expect(page.locator('#login-status')).toContainText('Bill reversed');
    await expect(page.locator('.erp-workspace-panel')).toContainText('reversed');

    await page.locator('nav#nav a[data-business-workspace="credit-notes"]').click();
    await page.locator('.erp-workspace-panel').getByRole('button', { name: '+ New Credit Note' }).click();
    await expect(page.locator('[data-cn-form]')).toBeVisible();
    await page.locator('[data-cn-form] select[name="customer_party_id"]').selectOption('p2');
    await page.locator('[data-cn-form] input[name="note_date"]').fill('2026-06-13');
    await page.locator('[data-cn-form] input[name="original_invoice_number"]').fill('INV-2026-001');
    await page.locator('[data-cn-form] select[name="reason"]').selectOption('sales_return');
    await page.locator('[data-cn-form] select[name="income_account_code"]').selectOption('4001');
    await page.locator('[data-cn-form] input[name="place_of_supply"]').fill('Karnataka');
    await page.locator('[data-cn-line] input[name="description"]').fill('Returned consulting service');
    await page.locator('[data-cn-line] input[name="hsn_sac"]').fill('9983');
    await page.locator('[data-cn-line] input[name="uqc"]').fill('NOS');
    await page.locator('[data-cn-line] input[name="quantity"]').fill('1');
    await page.locator('[data-cn-line] input[name="rate"]').fill('1000');
    await page.locator('[data-cn-line] input[name="gst_rate"]').fill('18');
    await expect(page.locator('[data-total-note]')).toContainText('1,180');
    await page.getByRole('button', { name: 'Post Credit Note' }).click();
    await expect(page.locator('#login-status')).toContainText('Credit note posted');
    await expect(page.locator('.erp-workspace-panel')).toContainText('CN-2026-001');
    await expect(page.getByRole('row', { name: /CN-2026-001/ })).toContainText('posted');

    await page.getByRole('row', { name: /CN-2026-001/ }).getByRole('button', { name: 'View' }).click();
    await expect(page.locator('.erp-workspace-panel')).toContainText('Credit Note CN-2026-001');
    await expect(page.locator('.erp-workspace-panel')).toContainText('Returned consulting service');
    await page.getByRole('button', { name: 'Reverse' }).click();
    await expect(page.locator('.reversal-panel')).toBeVisible();
    await page.locator('[data-reversal-date]').fill('2026-06-13');
    await page.getByRole('button', { name: 'Confirm reverse' }).click();
    await expect(page.locator('#login-status')).toContainText('Credit note reversed');
    await expect(page.locator('.erp-workspace-panel')).toContainText('Reversed');

    await page.locator('nav#nav a[data-business-workspace="debit-notes"]').click();
    await page.locator('.erp-workspace-panel').getByRole('button', { name: '+ New Debit Note' }).click();
    await expect(page.locator('[data-dn-form]')).toBeVisible();
    await page.locator('[data-dn-form] select[name="vendor_party_id"]').selectOption('p1');
    await page.locator('[data-dn-form] input[name="note_date"]').fill('2026-06-13');
    await page.locator('[data-dn-form] input[name="original_bill_number"]').fill('BILL-100');
    await page.locator('[data-dn-form] select[name="reason"]').selectOption('purchase_return');
    await page.locator('[data-dn-form] select[name="expense_account_code"]').selectOption('5001');
    await page.locator('[data-dn-form] input[name="place_of_supply"]').fill('Karnataka');
    await page.locator('[data-dn-line] input[name="description"]').fill('Returned office supplies');
    await page.locator('[data-dn-line] input[name="hsn_sac"]').fill('4820');
    await page.locator('[data-dn-line] input[name="quantity"]').fill('1');
    await page.locator('[data-dn-line] input[name="rate"]').fill('500');
    await page.locator('[data-dn-line] input[name="gst_rate"]').fill('18');
    await expect(page.locator('[data-total-note]')).toContainText('590');
    await page.getByRole('button', { name: 'Post Debit Note' }).click();
    await expect(page.locator('#login-status')).toContainText('Debit note posted');
    await expect(page.locator('.erp-workspace-panel')).toContainText('DN-2026-001');
    await expect(page.getByRole('row', { name: /DN-2026-001/ })).toContainText('posted');

    await page.getByRole('row', { name: /DN-2026-001/ }).getByRole('button', { name: 'View' }).click();
    await expect(page.locator('.erp-workspace-panel')).toContainText('Debit Note DN-2026-001');
    await expect(page.locator('.erp-workspace-panel')).toContainText('Returned office supplies');
    await page.getByRole('button', { name: 'Reverse' }).click();
    await expect(page.locator('.reversal-panel')).toBeVisible();
    await page.locator('[data-reversal-date]').fill('2026-06-13');
    await page.getByRole('button', { name: 'Confirm reverse' }).click();
    await expect(page.locator('#login-status')).toContainText('Debit note reversed');
    await expect(page.locator('.erp-workspace-panel')).toContainText('Reversed');
  });
});
