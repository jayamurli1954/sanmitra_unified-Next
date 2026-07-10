const { test, expect } = require('@playwright/test');

const fulfillJson = (route, body, status = 200) => route.fulfill({
  status,
  contentType: 'application/json',
  body: JSON.stringify(body),
});

async function mockVerifiedMitraBooksSession(page) {
  const accounts = [
    { id: 101, code: '1001', name: 'Cash in Hand', account_type: 'asset', type: 'asset' },
    { id: 102, code: '11010', name: 'Bank Account', account_type: 'asset', type: 'asset' },
    { id: 103, code: '12001', name: 'Sundry Debtors', account_type: 'asset', type: 'asset' },
    { id: 104, code: '21001', name: 'Sundry Creditors', account_type: 'liability', type: 'liability' },
    { id: 105, code: '31004', name: 'Opening Balance Equity', account_type: 'equity', type: 'equity' },
    { id: 106, code: '31003', name: 'Retained Earnings', account_type: 'equity', type: 'equity' },
    { id: 107, code: '16001', name: 'Furniture and Fixtures', account_type: 'asset', type: 'asset' },
    { id: 108, code: '16099', name: 'Accumulated Depreciation', account_type: 'asset', type: 'asset' },
    { id: 201, code: '4001', name: 'Sales', account_type: 'revenue', type: 'revenue' },
    { id: 202, code: '42003', name: 'Miscellaneous Income', account_type: 'income', type: 'income' },
    { id: 301, code: '5001', name: 'Office Expense', account_type: 'expense', type: 'expense' },
    { id: 302, code: '54003', name: 'Depreciation Expense', account_type: 'expense', type: 'expense' },
    { id: 303, code: '54005', name: 'Miscellaneous Expense', account_type: 'expense', type: 'expense' },
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
  const dimensions = [
    {
      dimension_id: 'dim-cc-blr',
      dimension_type: 'cost_centre',
      code: 'BLR',
      name: 'Bengaluru',
      is_active: true,
    },
    {
      dimension_id: 'dim-cc-mum',
      dimension_type: 'cost_centre',
      code: 'MUM',
      name: 'Mumbai',
      is_active: true,
    },
    {
      dimension_id: 'dim-prj-alpha',
      dimension_type: 'project',
      code: 'ALPHA',
      name: 'Project Alpha',
      is_active: true,
    },
  ];
  const allocations = [];
  const paidBillIds = new Set();
  let openingBalancePosted = false;
  let openingBalancePostCount = 0;
  let yearEndClosed = false;
  const gstPeriodLocks = [
    { period: '2026-05', locked: true, updated_by: 'businessadmin@sanmitra.local', updated_at: '2026-06-20T00:00:00Z' },
  ];
  let gstSettlementPosted = false;
  const caDocuments = [];
  const caClients = [];
  const caAttachments = [];
  const inventoryItems = [
    {
      item_id: 'item-widget-a',
      code: 'WIDGET-A',
      name: 'Widget A',
      uqc: 'NOS',
      hsn_sac: '8473',
      gst_rate: '18.00',
      opening_qty: '10.000',
      opening_value: '1200.00',
      is_active: true,
    },
  ];
  const inventoryMovements = [];
  const closingStockEntries = [];
  const fixedAssets = [
    {
      asset_id: 'fa-van-1',
      asset_name: 'Delivery Van',
      asset_account_code: '16001',
      purchase_date: '2026-04-01',
      cost: '100000.00',
      salvage_value: '10000.00',
      method: 'slm',
      useful_life_years: '5',
      depreciation_rate: null,
      opening_accumulated_depreciation: '0.00',
      accumulated_depreciation: '0.00',
      book_value: '100000.00',
      status: 'active',
    },
  ];
  let depreciationPosted = false;
  let bankStatementImported = false;
  const bankReconMatches = [];
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
  await page.route('**/api/v1/business/dashboard**', route => json(route, {
    as_of: '2026-06-30',
    financial_year_start: '2026-04-01',
    income: { fytd: '1000000.00', current_month: '250000.00', ytd_growth: 8.0 },
    expenses: { fytd: '600000.00' },
    net_position: { profit_loss: '400000.00' },
    cash_and_bank: '300000.00',
    receivables: '250000.00',
    payables: '150000.00',
    gst: { payable: '50000.00', status: 'Due' },
    monthly_trend: [
      ['Jan', 1.0, 0.8],
      ['Feb', 1.2, 0.9],
      ['Mar', 1.1, 1.0],
      ['Apr', 1.5, 1.1],
      ['May', 1.3, 1.0],
      ['Jun', 2.5, 1.2],
    ],
  }));
  await page.route('**/api/v1/business/mis/kpis**', route => json(route, {
    as_of: '2026-06-30',
    financial_year_start: '2026-04-01',
    source: {
      sales_purchase_trend: 'posted_ledger',
      working_capital: 'posted_ledger',
      top_parties: 'open_item_aging',
      overdue_dashboards: 'open_item_aging',
      financial_health: 'deterministic_financial_health',
    },
    monthly_sales_purchase_trend: [
      { month: 'Apr', sales: '150000.00', purchases: '110000.00', net: '40000.00' },
      { month: 'May', sales: '130000.00', purchases: '100000.00', net: '30000.00' },
      { month: 'Jun', sales: '250000.00', purchases: '120000.00', net: '130000.00' },
    ],
    top_customers: [
      { rank: 1, party_id: 'p2', party_name: 'Bengaluru Retail Customer', outstanding: '125000.00', overdue: '75000.00', over_90: '10000.00' },
    ],
    top_vendors: [
      { rank: 1, party_id: 'p1', party_name: 'Karnataka Office Supplies', outstanding: '150000.00', overdue: '30000.00', over_90: '0.00' },
    ],
    working_capital: {
      cash_and_bank: '300000.00',
      receivables: '250000.00',
      payables: '150000.00',
      gst_payable: '50000.00',
      current_assets: '550000.00',
      current_liabilities: '200000.00',
      net_working_capital: '350000.00',
      current_ratio: 2.75,
    },
    overdue: {
      receivables: { total: '250000.00', current: '175000.00', overdue: '75000.00', over_90: '10000.00' },
      payables: { total: '150000.00', current: '120000.00', overdue: '30000.00', over_90: '0.00' },
    },
    financial_health: {
      summary: 'MIS KPI contracts are source-backed for this tenant.',
      kpis: [],
      alerts: [],
      charts: [],
    },
  }));
  await page.route('**/api/v1/business/tally/xml-export**', route => route.fulfill({
    status: 200,
    contentType: 'application/xml',
    headers: {
      'Content-Disposition': 'attachment; filename="tally_trial_balance_2026-06-30.xml"',
      'X-SanMitra-Export-Governed': 'true',
      'X-SanMitra-Export-Format': 'xml',
    },
    body: '<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDATA><TALLYMESSAGE><LEDGER NAME="Bank Account"><NAME>Bank Account</NAME></LEDGER></TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>',
  }));
  await page.route('**/api/v1/business/data-health**', route => json(route, {
    as_of: '2026-06-30',
    score: 71,
    grade: 'C',
    status: 'needs_attention',
    summary: '2 data-health rule(s) need attention.',
    rules: [
      {
        key: 'missing_gstin',
        label: 'Missing GSTIN',
        status: 'fail',
        severity: 'warning',
        count: 1,
        score_impact: 4,
        detail: 'Active customers/vendors should carry GSTIN where the party is registered.',
        action: 'Open Parties and complete GSTIN/PAN details before filing or e-invoice work.',
        evidence: [{ party_id: 'p2', party_name: 'Bengaluru Retail Customer' }],
      },
      {
        key: 'duplicate_invoices',
        label: 'Duplicate invoice numbers',
        status: 'fail',
        severity: 'danger',
        count: 1,
        score_impact: 10,
        detail: 'Invoice numbers must be unique inside the active tenant book.',
        action: 'Investigate duplicate invoice numbers and correct with cancellation/reversal where needed.',
        evidence: [{ invoice_number: 'INV-001', count: 2 }],
      },
    ],
    issues: [
      {
        issue_id: 'data-health:missing_gstin:business_party:p2',
        rule_key: 'missing_gstin',
        severity: 'warning',
        title: 'Missing GSTIN',
        description: 'Active customers/vendors should carry GSTIN where the party is registered.',
        entity_type: 'business_party',
        entity_id: 'p2',
        entity_label: 'Bengaluru Retail Customer',
        workspace: 'parties',
        action_label: 'Open Parties',
        action: 'Open Parties and complete GSTIN/PAN details before filing or e-invoice work.',
        status: 'open',
      },
      {
        issue_id: 'data-health:duplicate_invoices:business_sales_invoice:inv-001',
        rule_key: 'duplicate_invoices',
        severity: 'danger',
        title: 'Duplicate invoice numbers',
        description: 'Invoice numbers must be unique inside the active tenant book.',
        entity_type: 'business_sales_invoice',
        entity_id: 'INV-001',
        entity_label: 'Invoice INV-001',
        workspace: 'sales',
        action_label: 'Open Sales',
        action: 'Investigate duplicate invoice numbers and correct with cancellation/reversal where needed.',
        status: 'open',
      },
    ],
    issue_count: 2,
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
        debit_account_id: payload.debit_account_id,
        credit_account_id: payload.credit_account_id,
        cost_centre_id: payload.cost_centre_id || null,
        project_id: payload.project_id || null,
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
      organization: {
        legal_name: 'Acme Corp Ltd',
        trade_name: 'Acme',
        gstin: '29ABCDE1234F1Z5',
        gst_registration_type: 'regular',
        financial_year_start: '2026-04-01',
      },
      branches: [
        {
          branch_code: 'BLR',
          branch_name: 'Bengaluru Head Office',
          gstin: '29ABCDE1234F1Z5',
          cost_centre_code: 'BLR',
          active: true,
        },
      ],
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

    if (path.includes('/attachments')) {
      const parts = path.split('/');
      const documentId = path.endsWith('/attachments') ? parts.at(-2) : parts.at(-4);
      const document = caDocuments.find(item => item.document_id === documentId);
      if (!document) return json(route, { detail: 'Document not found' }, 404);
      if (method === 'POST') {
        const attachment = {
          attachment_id: `caatt${caAttachments.length + 1}`,
          tenant_id: 'demo-mitrabooks-business',
          app_key: 'mitrabooks',
          accounting_entity_id: document.accounting_entity_id || 'primary',
          owner_type: 'ca_document',
          owner_id: documentId,
          file_name: 'gst-working.xlsx',
          content_type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          size_bytes: 4,
          uploaded_by: 'businessadmin@sanmitra.local',
          uploaded_at: '2026-06-14T00:00:00Z',
        };
        caAttachments.push(attachment);
        document.attachment_count = caAttachments.filter(item => item.owner_id === documentId).length;
        return json(route, attachment);
      }
      if (method === 'GET' && path.endsWith('/download')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          body: 'PK',
        });
      }
      return json(route, {
        items: caAttachments.filter(item => item.owner_id === documentId),
        total: caAttachments.filter(item => item.owner_id === documentId).length,
      });
    }

    if (method === 'PATCH') {
      const documentId = path.split('/').at(-1);
      const document = caDocuments.find(item => item.document_id === documentId);
      if (!document) return json(route, { detail: 'Document not found' }, 404);
      const payload = request.postDataJSON();
      document.status = payload.status || document.status;
      document.review_started_at = document.status === 'under_review' ? '2026-06-14T00:00:00Z' : document.review_started_at;
      document.review_started_by = document.status === 'under_review' ? 'businessadmin@sanmitra.local' : document.review_started_by;
      document.reviewed_at = document.status === 'reviewed' ? '2026-06-14T00:00:00Z' : document.reviewed_at;
      document.reviewed_by = document.status === 'reviewed' ? 'businessadmin@sanmitra.local' : document.reviewed_by;
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
      const client = caClients.find(item => item.client_id === payload.client_id);
      const document = {
        document_id: `cadoc${caDocuments.length + 1}`,
        tenant_id: 'demo-mitrabooks-business',
        app_key: 'mitrabooks',
        accounting_entity_id: 'primary',
        book_id: 'primary',
        client_id: payload.client_id || '',
        client_name: client?.client_name || payload.client_name,
        document_type: payload.document_type,
        period: payload.period,
        status: 'uploaded',
        assigned_to: payload.assigned_to || client?.assigned_to || '',
        client_owner: payload.client_owner || client?.client_owner || '',
        original_file_name: payload.original_file_name || '',
        attachment_count: 0,
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
  await page.route('**/api/v1/business/tds/sections**', route => json(route, {
    tds: [
      { section: '194C', label: 'Contractor payments', rate: '1.00', applies_to: 'vendor_payments' },
      { section: '194J', label: 'Professional fees', rate: '10.00', applies_to: 'vendor_payments' },
    ],
    tcs: [
      { section: '206C(1H)', label: 'Sale of goods', rate: '0.10', applies_to: 'customer_receipts' },
    ],
  }));
  await page.route('**/api/v1/business/dimensions**', async route => {
    const request = route.request();
    const method = request.method();
    const url = new URL(request.url());
    const path = url.pathname;
    const active = () => dimensions.filter(row => row.is_active !== false);
    const listPayload = () => {
      const items = active();
      return {
        items,
        cost_centres: items.filter(row => row.dimension_type === 'cost_centre'),
        projects: items.filter(row => row.dimension_type === 'project'),
        count: items.length,
      };
    };
    const taxable = row => Number(row.taxable_total || 0);
    const reportPayload = () => {
      const type = url.searchParams.get('dimension_type') || 'cost_centre';
      const field = type === 'project' ? 'project_id' : 'cost_centre_id';
      const dimRows = dimensions.filter(row => row.dimension_type === type);
      const sums = new Map();
      const bucket = id => {
        const key = id || '__untagged__';
        if (!sums.has(key)) sums.set(key, { income: 0, expense: 0 });
        return sums.get(key);
      };
      const applyDocument = (row, amountField, side, sign) => {
        const lineItems = Array.isArray(row.line_items) ? row.line_items : [];
        if (lineItems.length) {
          lineItems.forEach(line => {
            bucket(line[field] || row[field])[side] += sign * Number(line.taxable_amount || 0);
          });
          return;
        }
        bucket(row[field])[side] += sign * Number(row[amountField] || 0);
      };
      invoices.filter(row => row.status === 'posted').forEach(row => applyDocument(row, 'taxable_total', 'income', 1));
      creditNotes.filter(row => row.status === 'posted').forEach(row => applyDocument(row, 'taxable_total', 'income', -1));
      bills.filter(row => row.status === 'posted').forEach(row => applyDocument(row, 'taxable_total', 'expense', 1));
      debitNotes.filter(row => row.status === 'posted').forEach(row => applyDocument(row, 'taxable_total', 'expense', -1));
      vouchers.filter(row => row.status === 'posted').forEach(row => {
        const amount = Number(row.amount || 0);
        const debitType = accounts.find(account => String(account.id) === String(row.debit_account_id))?.type;
        const creditType = accounts.find(account => String(account.id) === String(row.credit_account_id))?.type;
        if (debitType === 'expense') bucket(row[field]).expense += amount;
        if (debitType === 'income' || debitType === 'revenue') bucket(row[field]).income -= amount;
        if (creditType === 'expense') bucket(row[field]).expense -= amount;
        if (creditType === 'income' || creditType === 'revenue') bucket(row[field]).income += amount;
      });
      const rows = dimRows
        .filter(row => sums.has(row.dimension_id))
        .map(row => {
          const v = sums.get(row.dimension_id);
          return {
            dimension_id: row.dimension_id,
            code: row.code,
            name: row.name,
            income: v.income.toFixed(2),
            expense: v.expense.toFixed(2),
            net: (v.income - v.expense).toFixed(2),
          };
        });
      const untagged = sums.get('__untagged__') || { income: 0, expense: 0 };
      const totals = [...sums.values()].reduce((acc, row) => ({
        income: acc.income + row.income,
        expense: acc.expense + row.expense,
      }), { income: 0, expense: 0 });
      return {
        dimension_type: type,
        from_date: url.searchParams.get('from_date') || '2026-04-01',
        to_date: url.searchParams.get('to_date') || '2027-03-31',
        rows,
        untagged: {
          income: untagged.income.toFixed(2),
          expense: untagged.expense.toFixed(2),
          net: (untagged.income - untagged.expense).toFixed(2),
        },
        totals: {
          income: totals.income.toFixed(2),
          expense: totals.expense.toFixed(2),
          net: (totals.income - totals.expense).toFixed(2),
        },
        document_counts: {
          invoices: invoices.filter(row => row.status === 'posted').length,
          bills: bills.filter(row => row.status === 'posted').length,
          credit_notes: creditNotes.filter(row => row.status === 'posted').length,
          debit_notes: debitNotes.filter(row => row.status === 'posted').length,
          vouchers: vouchers.filter(row => row.status === 'posted').length,
        },
        notes: ['Credit notes reduce income and debit notes reduce expense.'],
      };
    };
    const branchReportPayload = () => {
      const report = reportPayload();
      const byCode = new Map((report.rows || []).map(row => [String(row.code || '').toUpperCase(), row]));
      const branchRows = [{
        branch_code: 'BLR',
        branch_name: 'Bengaluru Head Office',
        gstin: '29ABCDE1234F1Z5',
        cost_centre_code: 'BLR',
        cost_centre_name: byCode.get('BLR')?.name || null,
        income: byCode.get('BLR')?.income || '0.00',
        expense: byCode.get('BLR')?.expense || '0.00',
        net: byCode.get('BLR')?.net || '0.00',
      }];
      const unmatched = (report.rows || []).filter(row => String(row.code || '').toUpperCase() !== 'BLR');
      const unassignedIncome = unmatched.reduce((sum, row) => sum + Number(row.income || 0), Number(report.untagged?.income || 0));
      const unassignedExpense = unmatched.reduce((sum, row) => sum + Number(row.expense || 0), Number(report.untagged?.expense || 0));
      return {
        report_type: 'branch_consolidated',
        from_date: report.from_date,
        to_date: report.to_date,
        rows: branchRows,
        unassigned: {
          income: unassignedIncome.toFixed(2),
          expense: unassignedExpense.toFixed(2),
          net: (unassignedIncome - unassignedExpense).toFixed(2),
          unmatched_cost_centres: unmatched,
        },
        totals: report.totals,
        document_counts: report.document_counts,
        notes: ['Branch consolidation maps branch settings to cost-centre tags.'],
      };
    };

    if (method === 'GET' && path.endsWith('/report/export')) {
      const format = url.searchParams.get('format') || 'csv';
      const body = format === 'json'
        ? JSON.stringify({ title: 'Dimension Report', rows: [{ dimension: 'BLR', income: '0.00', expense: '0.00', net: '0.00' }] })
        : 'dimension,income,expense,net\nBLR,0.00,0.00,0.00\n';
      return route.fulfill({
        status: 200,
        contentType: format === 'json' ? 'application/json' : 'text/csv',
        headers: {
          'Content-Disposition': `attachment; filename="dimension_report.${format}"`,
          'X-SanMitra-Export-Governed': 'true',
          'X-SanMitra-Export-Format': format,
        },
        body,
      });
    }

    if (method === 'GET' && path.endsWith('/branch-report')) return json(route, branchReportPayload());

    if (method === 'GET' && path.endsWith('/report')) return json(route, reportPayload());

    if (method === 'PATCH' && path.endsWith('/deactivate')) {
      const dimensionId = path.split('/').at(-2);
      const dim = dimensions.find(row => row.dimension_id === dimensionId);
      if (!dim) return json(route, { detail: 'Dimension not found' }, 404);
      dim.is_active = false;
      return json(route, dim);
    }

    if (method === 'POST') {
      const payload = request.postDataJSON();
      const dim = {
        dimension_id: `dim-${dimensions.length + 1}`,
        dimension_type: payload.dimension_type || 'cost_centre',
        code: String(payload.code || payload.name || `DIM-${dimensions.length + 1}`).trim().toUpperCase(),
        name: payload.name,
        is_active: true,
      };
      dimensions.push(dim);
      return json(route, dim);
    }

    return json(route, listPayload());
  });
  await page.route('**/api/v1/business/inventory/items**', async route => {
    const request = route.request();
    const method = request.method();
    const path = new URL(request.url()).pathname;

    if (method === 'PATCH' && path.endsWith('/deactivate')) {
      const itemId = path.split('/').at(-2);
      const item = inventoryItems.find(row => row.item_id === itemId);
      if (!item) return json(route, { detail: 'Item not found' }, 404);
      item.is_active = false;
      return json(route, item);
    }

    if (method === 'POST') {
      const payload = request.postDataJSON();
      const item = {
        item_id: `item-${inventoryItems.length + 1}`,
        code: String(payload.code || payload.name || `ITEM-${inventoryItems.length + 1}`).trim().toUpperCase(),
        name: payload.name,
        uqc: payload.uqc || 'NOS',
        hsn_sac: payload.hsn_sac || '',
        gst_rate: payload.gst_rate || '0.00',
        opening_qty: Number(payload.opening_qty || 0).toFixed(3),
        opening_value: Number(payload.opening_value || 0).toFixed(2),
        is_active: true,
      };
      inventoryItems.push(item);
      return json(route, item);
    }

    const active = inventoryItems.filter(row => row.is_active);
    return json(route, { inventory_enabled: true, items: active, count: active.length });
  });
  await page.route('**/api/v1/business/inventory/policy**', route => json(route, {
    inventory_enabled: true,
    accounting_entity_id: 'primary',
    valuation_policy: 'weighted_average_periodic',
    display_name: 'Weighted average (periodic)',
    supported_policies: ['weighted_average_periodic'],
    policy_locked: true,
    notes: [
      'Purchases and positive adjustments build the weighted-average cost pool.',
      'Stock issues and negative adjustments reduce quantity.',
    ],
  }));
  await page.route('**/api/v1/business/inventory/movements**', async route => {
    const request = route.request();
    if (request.method() === 'POST') {
      const payload = request.postDataJSON();
      const item = inventoryItems.find(row => row.item_id === payload.item_id);
      const movement = {
        movement_id: `move-${inventoryMovements.length + 1}`,
        movement_type: payload.movement_type || 'issue',
        movement_date: payload.movement_date || '2026-06-30',
        item_id: payload.item_id,
        item_code: item?.code || payload.item_id,
        item_name: item?.name || payload.item_id,
        quantity: Number(payload.quantity || 0).toFixed(3),
        value: Number(payload.value || 0).toFixed(2),
        reason: payload.reason || '',
        reference: payload.reference || '',
      };
      inventoryMovements.unshift(movement);
      return json(route, movement);
    }
    return json(route, { items: inventoryMovements, count: inventoryMovements.length });
  });
  await page.route('**/api/v1/business/inventory/stock-register**', route => {
    const asOf = new URL(route.request().url()).searchParams.get('as_of') || '2026-06-30';
    const widgetMovements = inventoryMovements.filter(row => row.item_id === 'item-widget-a');
    const adjustmentIn = widgetMovements
      .filter(row => row.movement_type === 'adjustment' && Number(row.quantity) > 0)
      .reduce((sum, row) => sum + Number(row.quantity || 0), 0);
    const adjustmentOut = widgetMovements
      .filter(row => row.movement_type === 'issue' || Number(row.quantity) < 0)
      .reduce((sum, row) => sum + Math.abs(Number(row.quantity || 0)), 0);
    const widgetClosingQty = 12 + adjustmentIn - adjustmentOut;
    const widgetClosingValue = widgetClosingQty * 150;
    return json(route, {
      as_of: asOf,
      item_count: inventoryItems.filter(row => row.is_active).length,
      total_closing_value: widgetClosingValue.toFixed(2),
      negative_stock_items: 0,
      untracked_purchase_value: '0.00',
      rows: inventoryItems.filter(row => row.is_active).map(row => ({
        item_id: row.item_id,
        code: row.code,
        name: row.name,
        uqc: row.uqc,
        opening_qty: row.opening_qty,
        purchased_qty: row.item_id === 'item-widget-a' ? '5.000' : '0.000',
        produced_qty: '0.000',
        sold_qty: row.item_id === 'item-widget-a' ? '3.000' : '0.000',
        consumed_qty: '0.000',
        adjustment_in_qty: row.item_id === 'item-widget-a' ? adjustmentIn.toFixed(3) : '0.000',
        adjustment_out_qty: row.item_id === 'item-widget-a' ? adjustmentOut.toFixed(3) : '0.000',
        closing_qty: row.item_id === 'item-widget-a' ? widgetClosingQty.toFixed(3) : row.opening_qty,
        avg_cost: row.item_id === 'item-widget-a' ? '150.00' : '0.00',
        closing_value: row.item_id === 'item-widget-a' ? widgetClosingValue.toFixed(2) : '0.00',
        negative_stock: false,
      })),
      notes: [
        'Valuation is weighted-average cost of purchases + production (taxable value, GST excluded).',
        'Reverse the closing-stock journal before posting a new position.',
      ],
    });
  });
  await page.route('**/api/v1/business/inventory/closing-stock/entries**', route => json(route, {
    items: closingStockEntries,
    count: closingStockEntries.length,
  }));
  await page.route('**/api/v1/business/inventory/closing-stock', route => {
    const payload = route.request().postDataJSON();
    const entry = {
      journal_entry_id: 9301,
      entry_date: payload.as_of || '2026-06-30',
      description: `Closing stock as of ${payload.as_of || '2026-06-30'}`,
    };
    closingStockEntries.unshift(entry);
    return json(route, {
      journal_entry_id: entry.journal_entry_id,
      created: true,
      as_of: entry.entry_date,
      closing_stock_value: '1800.00',
      item_count: inventoryItems.filter(row => row.is_active).length,
    });
  });
  await page.route('**/api/v1/business/fixed-assets**', async route => {
    const request = route.request();
    const method = request.method();
    const path = new URL(request.url()).pathname;
    const listPayload = () => {
      const items = fixedAssets.map(asset => {
        const acc = asset.status === 'disposed' ? asset.accumulated_depreciation : (depreciationPosted ? '18000.00' : asset.accumulated_depreciation);
        const book = asset.status === 'disposed' ? asset.disposal_book_value : (Number(asset.cost) - Number(acc)).toFixed(2);
        return { ...asset, accumulated_depreciation: acc, book_value: book };
      });
      const activeItems = items.filter(asset => asset.status !== 'disposed');
      return {
        items,
        count: items.length,
        total_cost: items.reduce((sum, asset) => sum + Number(asset.cost || 0), 0).toFixed(2),
        total_book_value: activeItems.reduce((sum, asset) => sum + Number(asset.book_value || 0), 0).toFixed(2),
      };
    };

    if (method === 'POST' && path.endsWith('/dispose')) {
      const assetId = path.split('/').at(-2);
      const asset = fixedAssets.find(row => row.asset_id === assetId);
      if (!asset) return json(route, { detail: 'Fixed asset not found' }, 404);
      const payload = request.postDataJSON();
      const accumulated = depreciationPosted ? 18000 : Number(asset.accumulated_depreciation || 0);
      const bookValue = Number(asset.cost || 0) - accumulated;
      const saleValue = Number(payload.sale_value || 0);
      const gain = Math.max(0, saleValue - bookValue);
      const loss = Math.max(0, bookValue - saleValue);
      Object.assign(asset, {
        status: 'disposed',
        accumulated_depreciation: accumulated.toFixed(2),
        book_value: bookValue.toFixed(2),
        disposal_date: payload.disposal_date,
        disposal_sale_value: saleValue.toFixed(2),
        disposal_book_value: bookValue.toFixed(2),
        disposal_gain: gain.toFixed(2),
        disposal_loss: loss.toFixed(2),
        disposal_journal_entry_id: 'FAD-2026-001',
      });
      return json(route, {
        asset_id: assetId,
        status: 'disposed',
        created: true,
        journal_entry_id: 'FAD-2026-001',
        disposal_date: asset.disposal_date,
        sale_value: asset.disposal_sale_value,
        book_value: asset.disposal_book_value,
        gain: asset.disposal_gain,
        loss: asset.disposal_loss,
      });
    }

    if (method === 'POST') {
      const payload = request.postDataJSON();
      const asset = {
        asset_id: `fa-${fixedAssets.length + 1}`,
        asset_name: payload.asset_name,
        asset_account_code: payload.asset_account_code || '16001',
        purchase_date: payload.purchase_date,
        cost: Number(payload.cost || 0).toFixed(2),
        salvage_value: Number(payload.salvage_value || 0).toFixed(2),
        method: payload.method || 'slm',
        useful_life_years: payload.useful_life_years || null,
        depreciation_rate: payload.depreciation_rate || null,
        opening_accumulated_depreciation: Number(payload.opening_accumulated_depreciation || 0).toFixed(2),
        accumulated_depreciation: Number(payload.opening_accumulated_depreciation || 0).toFixed(2),
        book_value: Number(payload.cost || 0).toFixed(2),
        status: 'active',
      };
      fixedAssets.push(asset);
      return json(route, asset);
    }

    return json(route, listPayload());
  });
  await page.route('**/api/v1/business/depreciation/preview**', route => {
    const financialYear = new URL(route.request().url()).searchParams.get('financial_year') || '2026-27';
    const rows = fixedAssets.filter(asset => asset.status === 'active').map(asset => {
      const openingBook = depreciationPosted ? '82000.00' : asset.book_value;
      return {
        asset_id: asset.asset_id,
        asset_name: asset.asset_name,
        asset_account_code: asset.asset_account_code,
        method: asset.method,
        purchase_date: asset.purchase_date,
        cost: asset.cost,
        accumulated_before: depreciationPosted ? '18000.00' : '0.00',
        opening_book_value: openingBook,
        depreciation: depreciationPosted ? '18000.00' : '18000.00',
        closing_book_value: depreciationPosted ? '82000.00' : '82000.00',
      };
    });
    return json(route, {
      financial_year: financialYear,
      from_date: '2026-04-01',
      to_date: '2027-03-31',
      rows,
      asset_count: rows.length,
      total_depreciation: rows.length ? '18000.00' : '0.00',
      already_run: depreciationPosted,
      existing_run: depreciationPosted ? { run_id: 'dep-run-1', journal_entry_id: 'DEP-2026-001' } : null,
      can_post: rows.length > 0 && !depreciationPosted,
      notes: ['Posting writes one journal: Dr Depreciation Expense, Cr Accumulated Depreciation.'],
    });
  });
  await page.route('**/api/v1/business/depreciation/run', route => {
    depreciationPosted = true;
    fixedAssets.forEach(asset => {
      if (asset.status === 'active') {
        asset.accumulated_depreciation = '18000.00';
        asset.book_value = '82000.00';
      }
    });
    return json(route, {
      run_id: 'dep-run-1',
      journal_entry_id: 'DEP-2026-001',
      created: true,
      financial_year: route.request().postDataJSON().financial_year || '2026-27',
      entry_date: '2027-03-31',
      total_depreciation: '18000.00',
      asset_count: fixedAssets.filter(asset => asset.status === 'active').length,
    });
  });
  await page.route('**/api/v1/business/opening-balances**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const csvText = [
      'account_code,account_name,party,debit,credit',
      '11010,Bank Account,,150000,',
      '12001,Sundry Debtors,CUST-001,40000,',
      '21001,Sundry Creditors,VEND-001,,30000',
      '',
    ].join('\n');

    if (request.method() === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'text/csv',
        headers: { 'Content-Disposition': path.endsWith('/export') ? 'attachment; filename="opening_balances.csv"' : 'attachment; filename="opening_balances_template.csv"' },
        body: csvText,
      });
    }

    const payload = request.postDataJSON();
    const existing = openingBalancePosted
      ? [{ journal_entry_id: 'OB-2026-001', entry_date: '2026-04-01', description: 'Opening balances as of 2026-04-01' }]
      : [];
    const preview = {
      as_of: payload.as_of || '2026-04-01',
      lines: [
        { row_number: 2, account_id: 102, account_code: '11010', account_name: 'Bank Account', party_id: null, party_name: null, debit: '150000.00', credit: '0.00' },
        { row_number: 3, account_id: 103, account_code: '12001', account_name: 'Sundry Debtors', party_id: 'p2', party_name: 'Bengaluru Retail Customer', debit: '40000.00', credit: '0.00' },
        { row_number: 4, account_id: 104, account_code: '21001', account_name: 'Sundry Creditors', party_id: 'p1', party_name: 'Karnataka Office Supplies', debit: '0.00', credit: '30000.00' },
      ],
      errors: [],
      line_count: 3,
      error_count: 0,
      total_debit: '190000.00',
      total_credit: '30000.00',
      difference: '160000.00',
      balancing_line: { account_code: '31004', account_name: 'Opening Balance Equity', debit: '0.00', credit: '160000.00' },
      can_post: true,
      existing_opening_entries: existing,
      notes: [
        'Posting writes ONE opening journal entry dated as-of; any debit/credit difference goes to Opening Balance Equity.',
        'Rows on Sundry Debtors/Creditors with a party post party-wise - they appear in aging, statements and allocation.',
        'To redo an opening balance, reverse the previous opening journal first, then upload again.',
      ],
    };

    if (path.endsWith('/preview')) {
      return json(route, preview);
    }

    openingBalancePosted = true;
    openingBalancePostCount += 1;
    return json(route, {
      journal_entry_id: 'OB-2026-001',
      created: openingBalancePostCount === 1,
      as_of: preview.as_of,
      line_count: 4,
      total_debit: preview.total_debit,
      total_credit: preview.total_credit,
      balancing_line: preview.balancing_line,
    });
  });
  await page.route('**/api/v1/business/year-end/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const financialYear = request.method() === 'POST'
      ? request.postDataJSON().financial_year
      : (url.searchParams.get('financial_year') || '2025-26');
    const preview = {
      financial_year: financialYear,
      from_date: '2025-04-01',
      to_date: '2026-03-31',
      income_total: '100000.00',
      expense_total: '60000.00',
      net_profit: '40000.00',
      closing_lines: [
        { account_id: 201, account_code: '4001', account_name: 'Sales', account_type: 'income', debit: '100000.00', credit: '0.00' },
        { account_id: 301, account_code: '5001', account_name: 'Office Expense', account_type: 'expense', debit: '0.00', credit: '60000.00' },
      ],
      retained_earnings: { account_code: '31003', account_name: 'Retained Earnings', debit: '0.00', credit: '40000.00' },
      already_closed: yearEndClosed ? [{ journal_entry_id: 'YE-2025-26-001', entry_date: '2026-03-31' }] : [],
      can_post: !yearEndClosed,
      notes: [
        'Closing zeroes every income/expense account for the year and moves the net result to Retained Earnings on 31 March.',
        'Post all year-end adjustments (depreciation, provisions) BEFORE closing.',
        'The close is one reversible journal entry - reverse it to reopen the year.',
      ],
    };

    if (path.endsWith('/preview')) {
      return json(route, preview);
    }

    yearEndClosed = true;
    return json(route, {
      journal_entry_id: 'YE-2025-26-001',
      created: true,
      financial_year: financialYear,
      entry_date: '2026-03-31',
      net_profit: '40000.00',
      line_count: 3,
    });
  });
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
        cost_centre_id: payload.cost_centre_id || null,
        project_id: payload.project_id || null,
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

    if (method === 'POST' && path.endsWith('/payment')) {
      const payload = request.postDataJSON();
      const billId = path.split('/').at(-2);
      const bill = bills.find(item => item.bill_id === billId) || {
        bill_id: billId,
        bill_number: billId === 'bill1' ? 'BILL-100' : billId,
        bill_total: '1770.00',
        net_payable: '1770.00',
      };
      paidBillIds.add(billId);
      Object.assign(bill, {
        paid_amount: payload.paid_amount,
        paid_date: payload.paid_date,
        payment_status: Number(payload.paid_amount || 0) >= Number(bill.net_payable || bill.bill_total || 0)
          ? 'paid'
          : 'partial',
      });
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
        net_payable: taxableTotal + gstTotal,
        payment_status: 'unpaid',
        status: 'posted',
        line_items: lineItems,
        is_inter_state: !!payload.is_inter_state,
        is_reverse_charge: !!payload.is_reverse_charge,
        cost_centre_id: payload.cost_centre_id || null,
        project_id: payload.project_id || null,
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
        cost_centre_id: payload.cost_centre_id || null,
        project_id: payload.project_id || null,
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
        cost_centre_id: payload.cost_centre_id || null,
        project_id: payload.project_id || null,
        journal_entry_id: `je-dn-${debitNotes.length + 1}`,
      };
      debitNotes.push(note);
      return json(route, note);
    }

    return json(route, { items: debitNotes });
  });
  await page.route('**/api/v1/business/party-ledger**', async route => {
    const url = new URL(route.request().url());
    const kind = url.searchParams.get('kind') || 'receivable';
    const receivableItems = [
      { party_id: 'p2', party_name: 'Bengaluru Retail Customer', balance: '2360.00' },
    ];
    const payableItems = [
      { party_id: 'p1', party_name: 'Karnataka Office Supplies', balance: '1770.00' },
    ];
    const items = kind === 'payable' ? payableItems : receivableItems;
    return json(route, { kind, as_of: url.searchParams.get('as_of') || '2026-06-13', items, total_balance: items[0]?.balance || '0.00' });
  });
  await page.route('**/api/v1/business/allocations/aging**', async route => {
    const url = new URL(route.request().url());
    const kind = url.searchParams.get('kind') || 'receivable';
    const bucketsOrder = ['0-30', '31-60', '61-90', '90+'];
    const byParty = kind === 'payable'
      ? [{ party_id: 'p1', party_name: 'Karnataka Office Supplies', buckets: { '0-30': '1770.00', '31-60': '0.00', '61-90': '0.00', '90+': '0.00' }, total: '1770.00' }]
      : [{ party_id: 'p2', party_name: 'Bengaluru Retail Customer', buckets: { '0-30': '0.00', '31-60': '2360.00', '61-90': '0.00', '90+': '0.00' }, total: '2360.00' }];
    const totals = byParty[0].buckets;
    return json(route, {
      kind,
      as_of: url.searchParams.get('as_of') || '2026-06-13',
      buckets_order: bucketsOrder,
      by_party: byParty,
      totals,
      grand_total: byParty[0].total,
    });
  });
  await page.route('**/api/v1/business/allocations/unallocated-payments**', async route => {
    const url = new URL(route.request().url());
    const kind = url.searchParams.get('kind') || 'receivable';
    const items = kind === 'payable'
      ? [{ payment_id: 'pay1', payment_number: 'PAY-2026-001', payment_date: '2026-06-18', amount: '1770.00', unallocated: '1770.00' }]
      : [{ payment_id: 'rcpt1', payment_number: 'RCT-2026-001', payment_date: '2026-06-18', amount: '2360.00', unallocated: '2360.00' }];
    return json(route, { kind, items, total_unallocated: items[0].unallocated });
  });
  await page.route('**/api/v1/business/allocations/open-items**', async route => {
    const url = new URL(route.request().url());
    const kind = url.searchParams.get('kind') || 'receivable';
    const items = kind === 'payable'
      ? [{ open_item_id: 'bill1', open_item_number: 'BILL-100', item_date: '2026-06-13', due_date: '2026-06-30', total: '1770.00', outstanding: '1770.00', days_overdue: 0 }]
      : [{ open_item_id: 'inv1', open_item_number: 'INV-2026-001', item_date: '2026-06-13', due_date: '2026-06-30', total: '2360.00', outstanding: '2360.00', days_overdue: 45 }];
    return json(route, { kind, items, total_outstanding: items[0].outstanding });
  });
  await page.route('**/api/v1/business/allocations/fifo-suggestion**', async route => {
    const url = new URL(route.request().url());
    const kind = url.searchParams.get('kind') || 'receivable';
    const allocationsPayload = kind === 'payable'
      ? [{ open_item_id: 'bill1', allocated_amount: '1770.00' }]
      : [{ open_item_id: 'inv1', allocated_amount: '2360.00' }];
    return json(route, { kind, payment_id: url.searchParams.get('payment_id'), allocations: allocationsPayload });
  });
  await page.route('**/api/v1/business/allocations/reconciliation**', async route => {
    const url = new URL(route.request().url());
    const kind = url.searchParams.get('kind') || 'receivable';
    const value = kind === 'payable' ? '1770.00' : '2360.00';
    return json(route, {
      kind,
      as_of: url.searchParams.get('as_of') || '2026-06-13',
      open_items_outstanding: value,
      unallocated_payments: allocations.length ? '0.00' : value,
      computed_net: allocations.length ? value : '0.00',
      ledger_balance: value,
      difference: allocations.length ? '0.00' : value,
      balanced: allocations.length > 0,
    });
  });
  await page.route('**/api/v1/business/allocations', async route => {
    const request = route.request();
    if (request.method() !== 'POST') return json(route, { items: allocations, total: allocations.length });
    const payload = request.postDataJSON();
    const docs = (payload.allocations || []).map((line, index) => ({
      allocation_id: `alloc${allocations.length + index + 1}`,
      kind: payload.kind,
      payment_id: payload.payment_id,
      open_item_id: line.open_item_id,
      allocated_amount: String(line.allocated_amount),
      status: 'active',
    }));
    allocations.push(...docs);
    return json(route, { count: docs.length, allocations: docs });
  });
  await page.route('**/api/v1/business/statements/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    if (request.method() === 'POST' && path.endsWith('/dunning')) {
      return json(route, {
        dunning_log_id: 'dun1',
        party_id: 'p2',
        level: 2,
        label: 'Second reminder',
        overdue_total: '2360.00',
        note: request.postDataJSON().note || '',
        created_by: 'businessadmin@sanmitra.local',
        created_at: '2026-06-20T00:00:00Z',
      });
    }
    const partyId = path.split('/').filter(Boolean).at(-1);
    const kind = url.searchParams.get('kind') || 'receivable';
    if (kind === 'payable') {
      const party = parties.find(item => item.party_id === partyId) || parties.find(item => item.party_type === 'vendor');
      const openingBalance = openingBalancePosted ? '30000.00' : '0.00';
      const closingBalance = openingBalancePosted ? '31770.00' : '1770.00';
      return json(route, {
        party: { party_id: party?.party_id || 'p1', party_name: party?.party_name || 'Karnataka Office Supplies', gstin: party?.gstin || '' },
        business_name: 'Acme Corp Ltd',
        kind,
        from_date: url.searchParams.get('from_date') || '2026-04-01',
        to_date: url.searchParams.get('to_date') || '2026-06-30',
        opening_balance: openingBalance,
        total_debit: '0.00',
        total_credit: '1770.00',
        closing_balance: closingBalance,
        transactions: [
          { entry_date: '2026-06-13', document_type: 'Bill', reference: 'BILL-100', description: 'Office supplies payable', debit: '0.00', credit: '1770.00', balance: '1770.00' },
        ],
        open_items: [
          { open_item_id: 'bill1', open_item_number: 'BILL-100', item_date: '2026-06-13', due_date: '2026-06-30', total: '1770.00', outstanding: '1770.00', days_overdue: 0 },
        ],
        dunning: { suggestion: { level: 0, label: 'No reminder needed' }, letter: '', log: [] },
        notes: ['Vendor statement lines come from the posted party sub-ledger.'],
      });
    }
    const party = parties.find(item => item.party_id === partyId) || parties.find(item => item.party_type === 'customer');
    const openingBalance = openingBalancePosted ? '40000.00' : '0.00';
    const closingBalance = openingBalancePosted ? '42360.00' : '2360.00';
    return json(route, {
      party: { party_id: party?.party_id || 'p2', party_name: party?.party_name || 'Bengaluru Retail Customer', gstin: party?.gstin || '' },
      business_name: 'Acme Corp Ltd',
      kind,
      from_date: url.searchParams.get('from_date') || '2026-04-01',
      to_date: url.searchParams.get('to_date') || '2026-06-30',
      opening_balance: openingBalance,
      total_debit: '2360.00',
      total_credit: '0.00',
      closing_balance: closingBalance,
      transactions: [
        { entry_date: '2026-06-13', document_type: 'Invoice', reference: 'INV-2026-001', description: 'Consulting service', debit: '2360.00', credit: '0.00', balance: '2360.00' },
      ],
      open_items: [
        { open_item_id: 'inv1', open_item_number: 'INV-2026-001', item_date: '2026-06-13', due_date: '2026-06-30', total: '2360.00', outstanding: '2360.00', days_overdue: 45 },
      ],
      dunning: {
        suggestion: { level: 2, label: 'Second reminder', max_days_overdue: 45, overdue_count: 1, overdue_total: '2360.00' },
        letter: 'Dear Bengaluru Retail Customer,\\nPlease clear overdue invoice INV-2026-001.',
        log: [],
      },
      notes: ['Statement lines come from the posted party sub-ledger.'],
    });
  });
  await page.route('**/api/v1/business/itc-reversals/preview**', async route => {
    const candidate = bills.find(item => item.bill_id === 'bill1') || {
      bill_id: 'bill1',
      bill_number: 'BILL-100',
      vendor_name: 'Karnataka Office Supplies',
      bill_date: '2026-06-13',
      due_date: '2026-06-30',
      bill_total: '1770.00',
      net_payable: '1770.00',
      gst_total: '270.00',
      payment_status: 'unpaid',
    };
    const candidates = candidate.payment_status === 'paid' || paidBillIds.has(candidate.bill_id) ? [] : [{
      bill_id: candidate.bill_id,
      bill_number: candidate.bill_number,
      vendor_name: candidate.vendor_name || 'Karnataka Office Supplies',
      bill_date: candidate.bill_date || '2026-06-13',
      due_date: candidate.due_date || '2026-06-30',
      days_overdue: 181,
      itc_total: candidate.gst_total || '270.00',
      interest_amount: '23.96',
      net_payable: candidate.net_payable || candidate.bill_total || '1770.00',
      bill_total: candidate.bill_total || '1770.00',
      payment_status: candidate.payment_status || 'unpaid',
      gstr3b_ref: '4(B)(2)',
    }];
    return json(route, {
      as_of: new URL(route.request().url()).searchParams.get('as_of') || '2026-12-28',
      count: candidates.length,
      candidates,
      total_itc: candidates.length ? '270.00' : '0.00',
      total_interest: candidates.length ? '23.96' : '0.00',
    });
  });
  await page.route('**/api/v1/business/gst-period-locks**', async route => {
    const request = route.request();
    if (request.method() === 'PUT') {
      const payload = request.postDataJSON();
      const existing = gstPeriodLocks.find(item => item.period === payload.period);
      if (existing) {
        existing.locked = !!payload.locked;
        existing.updated_by = 'businessadmin@sanmitra.local';
      } else {
        gstPeriodLocks.push({
          period: payload.period,
          locked: !!payload.locked,
          updated_by: 'businessadmin@sanmitra.local',
          updated_at: '2026-06-20T00:00:00Z',
        });
      }
      return json(route, gstPeriodLocks.find(item => item.period === payload.period));
    }
    return json(route, { items: gstPeriodLocks });
  });
  await page.route('**/api/v1/business/gst-settlement/preview**', async route => {
    const period = new URL(route.request().url()).searchParams.get('period') || '2026-06';
    return json(route, {
      period,
      status: gstSettlementPosted ? 'posted' : 'preview',
      period_locked: gstSettlementPosted,
      settled_by: gstSettlementPosted ? 'businessadmin@sanmitra.local' : '',
      journal_entry_id: gstSettlementPosted ? 'GSTSET-2026-06' : '',
      output: { igst: '0.00', cgst: '180.00', sgst: '180.00' },
      input_credit: { igst: '0.00', cgst: '135.00', sgst: '135.00' },
      utilized: { igst: '0.00', cgst: '135.00', sgst: '135.00' },
      cash_payable: { igst: '0.00', cgst: '45.00', sgst: '45.00' },
      itc_carry_forward: { igst: '0.00', cgst: '0.00', sgst: '0.00' },
      total_output: '360.00',
      total_input: '270.00',
      net_cash_payable: '90.00',
      note: 'Preview uses posted invoices, purchase bills, and GST ledger balances only.',
    });
  });
  await page.route('**/api/v1/business/gst-settlement', async route => {
    const payload = route.request().postDataJSON();
    gstSettlementPosted = true;
    if (payload.lock_period && !gstPeriodLocks.some(item => item.period === payload.period)) {
      gstPeriodLocks.push({
        period: payload.period,
        locked: true,
        updated_by: 'businessadmin@sanmitra.local',
        updated_at: '2026-06-20T00:00:00Z',
      });
    }
    return json(route, {
      period: payload.period,
      status: 'posted',
      period_locked: !!payload.lock_period,
      settled_by: 'businessadmin@sanmitra.local',
      journal_entry_id: 'GSTSET-2026-06',
      output: { igst: '0.00', cgst: '180.00', sgst: '180.00' },
      input_credit: { igst: '0.00', cgst: '135.00', sgst: '135.00' },
      utilized: { igst: '0.00', cgst: '135.00', sgst: '135.00' },
      cash_payable: { igst: '0.00', cgst: '45.00', sgst: '45.00' },
      itc_carry_forward: { igst: '0.00', cgst: '0.00', sgst: '0.00' },
      total_output: '360.00',
      total_input: '270.00',
      net_cash_payable: '90.00',
      note: 'Settlement posted through the GST control accounts.',
    });
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
  await page.route('**/api/v1/business/returns/**', route => {
    const path = new URL(route.request().url()).pathname;
    if (path.includes('/gstr-3b')) {
      return json(route, {
        period: '2026-06',
        gstin: '29ABCDE1234F1Z5',
        outward_supplies: {
          taxable: { taxable_value: '2000.00', igst: '0.00', cgst: '180.00', sgst: '180.00' },
          inward_reverse_charge: { taxable_value: '0.00', igst: '0.00', cgst: '0.00', sgst: '0.00' },
        },
        itc: {
          available_rcm: { igst: '0.00', cgst: '0.00', sgst: '0.00' },
          available_all_other: { igst: '0.00', cgst: '135.00', sgst: '135.00' },
          reversed_others: { igst: '0.00', cgst: '0.00', sgst: '0.00' },
          net_available: { igst: '0.00', cgst: '135.00', sgst: '135.00' },
        },
        tax_payment: {
          igst: { tax_payable: '0.00', paid_through_itc: '0.00', paid_in_cash: '0.00' },
          cgst: { tax_payable: '180.00', paid_through_itc: '135.00', paid_in_cash: '45.00' },
          sgst: { tax_payable: '180.00', paid_through_itc: '135.00', paid_in_cash: '45.00' },
        },
        totals: { total_output_tax: '360.00', total_itc_net: '270.00', total_cash_payable: '90.00' },
        gstn_json: { gstin: '29ABCDE1234F1Z5', ret_period: '062026' },
        notes: ['GSTR-3B is assembled from posted GST ledgers only.'],
      });
    }
    if (path.includes('/gstr-1')) {
      return json(route, {
        period: '2026-06',
        gstin: '29ABCDE1234F1Z5',
        sections: {
          docs: { total: 1, from: 'INV-2026-001', to: 'INV-2026-001' },
          b2b: { invoices: 1, recipients: 1, taxable_value: '2000.00', tax: '360.00' },
          b2cl: { invoices: 0, taxable_value: '0.00', tax: '0.00' },
          b2cs: { rows: 1, taxable_value: '2000.00', tax: '360.00' },
          exp: { invoices: 0, taxable_value: '0.00', tax: '0.00' },
          cdnr: { notes: 0, taxable_value: '0.00', tax: '0.00' },
          hsn: { rows: 1, taxable_value: '2000.00', tax: '360.00' },
        },
        b2cs_rows: [{ pos: '29-Karnataka', supply_type: 'INTRA', rate: '18', taxable_value: '2000.00', igst: '0.00', cgst: '180.00', sgst: '180.00' }],
        hsn_rows: [{ hsn_sac: '9983', uqc: 'NOS', rate: '18', quantity: '2', taxable_value: '2000.00', igst: '0.00', cgst: '180.00', sgst: '180.00' }],
        gstn_json: { gstin: '29ABCDE1234F1Z5', fp: '062026' },
        notes: ['GSTR-1 uses posted sales invoices and credit notes.'],
      });
    }
    return json(route, { period: '2026-06', rows: [], summary: {} });
  });
  await page.route('**/api/v1/business/tds/register**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      quarter: '2026-Q1',
      period_start: '2026-04-01',
      period_end: '2026-06-30',
      tds: {
        total_tax: '100.00',
        total_base: '10000.00',
        entry_count: 1,
        pan_missing_count: 0,
        sections: [{
          section: '194C',
          label: 'Contractor payments',
          total_base: '10000.00',
          total_tax: '100.00',
          entries: [{
            doc_date: '2026-06-13',
            doc_number: 'BILL-100',
            party_name: 'Karnataka Office Supplies',
            pan: 'ABCDE1234F',
            pan_missing: false,
            base_amount: '10000.00',
            rate: '1',
            tax_amount: '100.00',
          }],
        }],
      },
      tcs: {
        total_tax: '0.00',
        total_base: '0.00',
        entry_count: 0,
        pan_missing_count: 0,
        sections: [],
      },
      generated_notes: ['TDS is deducted on the GST-exclusive taxable value.'],
    }),
  }));
  await page.route('**/api/v1/business/bank-recon**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const activeMatches = bankReconMatches.filter(item => item.status === 'active');
    const hasMatch = activeMatches.some(item => item.statement_line_id === 'stmt-1' && item.line_id === 7001);
    const statementLines = bankStatementImported ? [
      {
        statement_line_id: 'stmt-1',
        txn_date: '2026-06-14',
        description: 'NEFT FROM BENGALURU RETAIL CUSTOMER',
        ref: 'UTR-2360',
        withdrawal: '0.00',
        deposit: '2360.00',
        balance: '2360.00',
      },
      {
        statement_line_id: 'stmt-2',
        txn_date: '2026-06-15',
        description: 'BANK CHARGES',
        ref: 'CHG-118',
        withdrawal: '118.00',
        deposit: '0.00',
        balance: '2242.00',
      },
    ] : [];
    const bookLine = {
      line_id: 7001,
      journal_id: 7101,
      entry_date: '2026-06-13',
      reference: 'RCT-2026-001 UTR-2360',
      description: 'Receipt from Bengaluru Retail Customer',
      debit: '2360.00',
      credit: '0.00',
    };
    const bankReconPayload = () => ({
      account: { account_id: 102, code: '11010', name: 'Bank Account' },
      as_of: '2026-06-30',
      summary: {
        book_balance: '2360.00',
        statement_balance: bankStatementImported ? '2242.00' : null,
        expected_statement_balance: bankStatementImported ? '2242.00' : '2360.00',
        difference: bankStatementImported ? '0.00' : null,
        matched_count: activeMatches.length,
        statement_lines_total: statementLines.length,
        book_lines_total: 1,
        uncleared_withdrawals: '0.00',
        deposits_in_transit: hasMatch ? '0.00' : '2360.00',
        bank_only_deposits: hasMatch ? '0.00' : (bankStatementImported ? '2360.00' : '0.00'),
        bank_only_withdrawals: bankStatementImported ? '118.00' : '0.00',
      },
      matched: activeMatches,
      in_bank_not_in_books: statementLines.filter(row => !(hasMatch && row.statement_line_id === 'stmt-1')),
      in_books_not_in_bank: hasMatch ? [] : [bookLine],
      suggestions: bankStatementImported && !hasMatch ? [{
        statement_line_id: 'stmt-1',
        line_id: 7001,
        journal_id: 7101,
        side: 'deposit',
        amount: '2360.00',
        date_diff_days: 1,
        confidence: 'ref',
        statement: { txn_date: '2026-06-14', description: 'NEFT FROM BENGALURU RETAIL CUSTOMER', ref: 'UTR-2360' },
        book: { entry_date: '2026-06-13', reference: 'RCT-2026-001 UTR-2360', description: 'Receipt from Bengaluru Retail Customer' },
      }] : [],
      notes: ['Matching is metadata only - confirming a match never posts to the ledger.'],
    });

    if (request.method() === 'POST' && path.endsWith('/statement')) {
      bankStatementImported = true;
      return json(route, { inserted: 2, skipped_duplicates: 0, parsed: 2, batch_id: 'bank-batch-1' });
    }

    if (request.method() === 'POST' && path.endsWith('/statement-voucher')) {
      const payload = request.postDataJSON();
      return json(route, {
        statement_line_id: payload.statement_line_id,
        posting_status: 'posted',
        voucher: {
          voucher_id: 'bank-voucher-1',
          voucher_number: 'JV-2026-000045',
          voucher_type: 'journal',
          tenant_id: 'demo-mitrabooks-business',
          app_key: 'mitrabooks',
          accounting_entity_id: 'primary',
          amount: '118.00',
          entry_date: '2026-06-15',
          debit_account_id: Number(payload.offset_account_id),
          credit_account_id: Number(payload.account_id),
          description: 'BANK CHARGES',
          reference: 'CHG-118',
          status: 'posted',
          approval_required: true,
          approval_status: 'approved',
          journal_entry_id: 7201,
          created: true,
          created_by: 'tester',
          created_at: '2026-06-15T00:00:00+00:00',
          updated_at: '2026-06-15T00:00:00+00:00',
        },
      });
    }

    if (request.method() === 'POST' && path.includes('/match/') && path.endsWith('/reverse')) {
      const matchId = path.split('/').at(-2);
      const match = bankReconMatches.find(item => item.match_id === matchId);
      if (match) match.status = 'reversed';
      return json(route, { match_id: matchId, status: 'reversed' });
    }

    if (request.method() === 'POST' && path.endsWith('/match')) {
      const payload = request.postDataJSON();
      const match = {
        match_id: 'match-1',
        account_id: Number(payload.account_id || 102),
        statement_line_id: payload.statement_line_id,
        line_id: Number(payload.line_id),
        journal_id: 7101,
        side: 'deposit',
        amount: '2360.00',
        statement_txn_date: '2026-06-14',
        book_entry_date: '2026-06-13',
        status: 'active',
      };
      bankReconMatches.push(match);
      return json(route, match);
    }

    return json(route, bankReconPayload());
  });
  await page.route('**/api/v1/business/banking/books**', async route => {
    const url = new URL(route.request().url());
    const bookType = url.searchParams.get('book_type') || 'all';
    const accounts = [
      {
        account_id: 101,
        account_code: '11001',
        account_name: 'Cash in Hand',
        book_type: 'cash',
        opening_balance: '1000.00',
        total_receipts: '500.00',
        total_payments: '100.00',
        closing_balance: '1400.00',
        lines: [
          {
            line_id: 8101,
            journal_id: 8201,
            entry_date: '2026-06-10',
            reference: 'CR-100',
            description: 'Cash receipt',
            source_document_type: 'voucher',
            receipt: '500.00',
            payment: '0.00',
            running_balance: '1500.00',
          },
          {
            line_id: 8102,
            journal_id: 8202,
            entry_date: '2026-06-11',
            reference: 'CP-100',
            description: 'Cash payment',
            source_document_type: 'voucher',
            receipt: '0.00',
            payment: '100.00',
            running_balance: '1400.00',
          },
        ],
      },
      {
        account_id: 102,
        account_code: '11010',
        account_name: 'Bank Account',
        book_type: 'bank',
        opening_balance: '2000.00',
        total_receipts: '2360.00',
        total_payments: '118.00',
        closing_balance: '4242.00',
        lines: [
          {
            line_id: 8201,
            journal_id: 8301,
            entry_date: '2026-06-14',
            reference: 'UTR-2360',
            description: 'Receipt from Bengaluru Retail Customer',
            source_document_type: 'voucher',
            receipt: '2360.00',
            payment: '0.00',
            running_balance: '4360.00',
          },
          {
            line_id: 8202,
            journal_id: 8302,
            entry_date: '2026-06-15',
            reference: 'CHG-118',
            description: 'BANK CHARGES',
            source_document_type: 'voucher',
            receipt: '0.00',
            payment: '118.00',
            running_balance: '4242.00',
          },
        ],
      },
    ].filter(account => bookType === 'all' || account.book_type === bookType);
    const total = (field) => accounts.reduce((sum, row) => sum + Number(row[field] || 0), 0).toFixed(2);
    return json(route, {
      book_type: bookType,
      from_date: url.searchParams.get('from_date') || '2026-04-01',
      to_date: url.searchParams.get('to_date') || '2026-06-30',
      summary: {
        opening_balance: total('opening_balance'),
        total_receipts: total('total_receipts'),
        total_payments: total('total_payments'),
        closing_balance: total('closing_balance'),
        account_count: accounts.length,
      },
      accounts,
    });
  });
  await page.route('**/api/v1/accounting/reports/drilldown**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ summary: { voucher_count: 0 }, items: [] }),
  }));
  await page.route('**/api/v1/accounting/reports/**', route => {
    const path = new URL(route.request().url()).pathname;
    if (path.includes('/trial-balance')) {
      return json(route, {
        as_of: '2026-06-13',
        balanced: true,
        lines: openingBalancePosted ? [
          { account_id: 102, account_code: '11010', account_name: 'Bank Account', debit_total: '150000.00', credit_total: '0.00', net_balance: '150000.00' },
          { account_id: 103, account_code: '12001', account_name: 'Sundry Debtors', debit_total: '40000.00', credit_total: '0.00', net_balance: '40000.00' },
          { account_id: 104, account_code: '21001', account_name: 'Sundry Creditors', debit_total: '0.00', credit_total: '30000.00', net_balance: '-30000.00' },
          { account_id: 105, account_code: '31004', account_name: 'Opening Balance Equity', debit_total: '0.00', credit_total: '160000.00', net_balance: '-160000.00' },
        ] : [],
      });
    }
    return json(route, { rows: [], totals: {}, summary: {} });
  });
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

  test('supports forgot password and reset-link password update before sign in', async ({ page }) => {
    let forgotPayload = null;
    let resetPayload = null;
    await page.route('**/api/v1/auth/forgot-password', async route => {
      forgotPayload = JSON.parse(route.request().postData() || '{}');
      return fulfillJson(route, {
        status: 'ok',
        message: 'If this account exists, password reset instructions have been sent.',
      });
    });
    await page.route('**/api/v1/auth/reset-password', async route => {
      resetPayload = JSON.parse(route.request().postData() || '{}');
      return fulfillJson(route, { status: 'ok', message: 'Password updated successfully' });
    });

    await page.goto('/mitrabooks-erp/index.html');
    await page.locator('#forgot-password-open').click();
    await expect(page.locator('#forgot-password-form')).toBeVisible();
    await expect(page.locator('#reset-password-form')).toBeHidden();
    await expect(page.locator('#access-title')).toContainText('Reset password');
    await expect(page.locator('#forgot-password-form')).toContainText('Your user ID is your registered email');
    await page.locator('#forgot-email').fill('owner@example.com');
    await page.locator('#forgot-password-submit').click();
    await expect(page.locator('#login-status')).toContainText('Reset link requested');
    expect(forgotPayload).toEqual({ email: 'owner@example.com' });

    await page.goto('/mitrabooks-erp/index.html?action=reset&token=reset-token-123');
    await expect(page.locator('#reset-password-form')).toBeVisible();
    await expect(page.locator('#forgot-password-form')).toBeHidden();
    await expect(page.locator('#access-title')).toContainText('Set new password');
    await page.locator('#reset-new-password').fill('newpass123');
    await page.locator('#reset-confirm-password').fill('newpass123');
    await page.locator('#reset-password-submit').click();
    await expect(page.locator('#login-status')).toContainText('Password updated');
    await expect(page.locator('#login-form')).toBeVisible();
    expect(resetPayload).toEqual({
      token: 'reset-token-123',
      new_password: 'newpass123',
      confirm_password: 'newpass123',
    });
  });

  test('offers MitraBooks PWA install prompts for native and iOS devices', async ({ page }) => {
    await page.goto('/mitrabooks-erp/index.html');
    await page.evaluate(() => {
      const event = new Event('beforeinstallprompt');
      event.prompt = () => Promise.resolve();
      event.userChoice = Promise.resolve({ outcome: 'accepted' });
      window.dispatchEvent(event);
    });
    await expect(page.locator('#sanmitra-install-suggestion')).toContainText('Install MitraBooks');
    await expect(page.locator('#sanmitra-install-suggestion')).toContainText('Android phone');
  });

  test('shows MitraBooks iPhone and iPad home-screen install instructions', async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(window.navigator, 'userAgent', {
        value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1',
        configurable: true,
      });
    });
    await page.goto('/mitrabooks-erp/index.html');
    await expect(page.locator('#sanmitra-install-suggestion')).toContainText('Add MitraBooks to Home Screen');
    await expect(page.locator('#sanmitra-install-suggestion')).toContainText('iPhone or iPad');
  });

  test('keeps login page visible when cached token has no tenant session', async ({ page }) => {
    await page.addInitScript(() => {
      window.sessionStorage.setItem('sanmitra_frontend_access_token', 'stale-local-preview-token');
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
    await expect.poll(() => page.evaluate(() => window.sessionStorage.getItem('sanmitra_frontend_access_token'))).toBeNull();
  });

  test('loads dashboard and opens core workspaces', async ({ page }) => {
    test.setTimeout(120000);
    await mockVerifiedMitraBooksSession(page);
    await page.addInitScript(() => {
      window.sessionStorage.setItem('sanmitra_frontend_access_token', 'static-shell-token');
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
    await expect(page.locator('.executive-dashboard')).toContainText('MIS KPI Contracts');
    await expect(page.locator('.executive-dashboard')).toContainText('Working capital');
    await expect(page.locator('.executive-dashboard')).toContainText('Top Customers');
    await expect(page.locator('.executive-dashboard')).toContainText('Bengaluru Retail Customer');
    await expect(page.locator('.executive-dashboard')).toContainText('Karnataka Office Supplies');
    await expect(page.locator('.finance-chart')).toBeVisible();
    await expect(page.locator('.business-bottom-metrics')).toBeVisible();
    await expect(page.locator('.business-quick-actions-clean')).toBeVisible();
    await expect(page.locator('.business-quick-actions-clean')).toContainText('Journal');
    await expect(page.locator('.business-recent-activity-clean')).toBeVisible();
    await expect(page.locator('.business-recent-activity-clean')).toContainText('Recent Activity');
    await expect(page.locator('.business-dashboard-clean .erp-health-panel')).toHaveCount(0);

    await page.locator('nav#nav a[data-business-workspace="settings"]').click();
    await expect(page.locator('.mitrabooks-settings-workspace')).toContainText('MitraBooks Settings');
    await expect(page.locator('.erp-health-panel')).toContainText('Data Health Score');
    await expect(page.locator('.erp-health-panel')).toContainText('71/100');
    await expect(page.locator('.erp-health-panel')).toContainText('Duplicate invoice numbers');
    await expect(page.locator('.erp-health-panel')).toContainText('Remediation Queue');
    await page.locator('.erp-health-panel button[data-data-health-rule="duplicate_invoices"]').click();
    await expect(page.locator('.erp-workspace-panel')).toContainText('Sales Invoices');

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
    await expect(page.getByRole('row', { name: /Alpha Consulting Updated/ })).toHaveCount(0);

    await page.locator('nav#nav a[data-business-workspace="vouchers"]').click();
    await expect(page.locator('.erp-workspace-panel')).toContainText('Vouchers');
    await expect(page.getByRole('button', { name: '+ New Voucher' })).toBeVisible();

    await page.keyboard.press('Control+Alt+V');
    await expect(page.locator('#business-voucher-create-dialog')).toBeVisible();
    await expect(page.locator('#business-voucher-type-select')).toBeFocused();
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
    await expect(page.locator('#business-voucher-cost-centre')).toBeVisible();
    await expect(page.locator('#business-voucher-project')).toBeVisible();
    await page.locator('#business-voucher-cost-centre').selectOption('dim-cc-blr');
    await page.locator('#business-voucher-project').selectOption('dim-prj-alpha');
    await page.locator('#business-voucher-description').fill('Browser verified balanced journal');
    await page.keyboard.press('Alt+L');
    await expect(page.locator('#business-voucher-lines .voucher-line')).toHaveCount(3);
    await page.locator('#business-voucher-lines .voucher-line').last().getByRole('button', { name: 'Remove' }).click();
    await expect(page.locator('#business-voucher-lines .voucher-line')).toHaveCount(2);
    await page.locator('#business-voucher-lines .account-picker-select').nth(0).selectOption('301');
    await page.locator('#business-voucher-lines .account-picker-select').nth(1).selectOption('201');
    await page.locator('#business-voucher-lines .voucher-debit').nth(0).fill('125.00');
    await page.locator('#business-voucher-lines .voucher-credit').nth(1).fill('125.00');
    await expect(page.locator('#business-voucher-balance')).toHaveClass(/balanced/);
    await expect(page.locator('#business-voucher-submit')).toBeEnabled();
    await page.keyboard.press('Control+Enter');
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

    await page.locator('nav#nav a[data-business-workspace="reports"]').click();
    await expect(page.locator('.erp-workspace-panel')).toContainText('Financial Reports');
    await page.locator('[data-business-action="report-tab"][data-report-tab="receivables-payables"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('Sundry Debtors');
    await expect(page.locator('#business-report-printable')).toContainText('Bengaluru Retail Customer');
    await expect(page.locator('#business-report-printable')).toContainText('Sundry Creditors');
    await expect(page.locator('#business-report-printable')).toContainText('Karnataka Office Supplies');

    await page.locator('[data-business-action="report-tab"][data-report-tab="aging"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('Receivables aging');
    await expect(page.locator('#business-report-printable')).toContainText('31-60');
    await expect(page.locator('#business-report-printable')).toContainText('Bengaluru Retail Customer');
    await page.locator('[data-business-action="aging-kind"][data-alloc-kind="payable"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('Payables aging');
    await expect(page.locator('#business-report-printable')).toContainText('Karnataka Office Supplies');

    await page.locator('[data-business-action="report-tab"][data-report-tab="payment-allocation"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('Unallocated Receipts');
    await expect(page.locator('#business-report-printable')).toContainText('RCT-2026-001');
    await page.getByRole('button', { name: 'Allocate' }).click();
    await expect(page.locator('#business-report-printable')).toContainText('Match against open items');
    await expect(page.locator('#business-report-printable')).toContainText('INV-2026-001');
    await expect(page.locator('input[data-alloc-line="inv1"]')).toHaveValue('2360.00');
    await page.getByRole('button', { name: 'Post Allocation' }).click();
    await expect(page.locator('#login-status')).toContainText('Allocation posted');
    await expect(page.locator('#business-report-printable')).toContainText('reconciled');

    await page.locator('[data-business-action="report-tab"][data-report-tab="statements"]').click();
    await page.locator('[data-stmt-party]').selectOption('p2');
    await page.locator('[data-stmt-kind]').selectOption('receivable');
    await page.locator('[data-stmt-from]').fill('2026-06-01');
    await page.locator('[data-stmt-to]').fill('2026-06-30');
    await page.locator('[data-business-action="stmt-load"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('Statement for');
    await expect(page.locator('#business-report-printable')).toContainText('INV-2026-001');
    await expect(page.locator('#business-report-printable')).toContainText('Payment reminders');
    await expect(page.locator('#business-report-printable')).toContainText('Second reminder');
    await page.locator('[data-dunning-note]').fill('emailed to accounts team');
    await page.locator('[data-business-action="dunning-record"]').click();
    await expect(page.locator('#login-status')).toContainText('Reminder recorded');

    await page.locator('[data-business-action="report-tab"][data-report-tab="statements"]').click();
    await page.locator('[data-stmt-party]').selectOption('p1');
    await page.locator('[data-stmt-kind]').selectOption('payable');
    await page.locator('[data-stmt-from]').fill('2026-06-01');
    await page.locator('[data-stmt-to]').fill('2026-06-30');
    await page.locator('[data-business-action="stmt-load"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('Karnataka Office Supplies');
    await expect(page.locator('#business-report-printable')).toContainText('Bill');
    await expect(page.locator('#business-report-printable')).toContainText('BILL-100');
    await expect(page.locator('#business-report-printable')).toContainText('Open items');
    await expect(page.locator('#business-report-printable')).not.toContainText('Payment reminders');

    await page.locator('[data-business-action="report-tab"][data-report-tab="payment-allocation"]').click();
    await page.locator('[data-business-action="alloc-kind"][data-alloc-kind="payable"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('Unallocated Payments');
    await expect(page.locator('#business-report-printable')).toContainText('PAY-2026-001');
    await page.locator('[data-business-action="alloc-select-payment"][data-payment-id="pay1"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('Match against open items');
    await expect(page.locator('#business-report-printable')).toContainText('BILL-100');
    await expect(page.locator('input[data-alloc-line="bill1"]')).toHaveValue('1770.00');
    await page.locator('[data-business-action="alloc-submit"]').click();
    await expect(page.locator('#login-status')).toContainText('Allocation posted');
    await expect(page.locator('#business-report-printable')).toContainText('reconciled');

    await page.locator('[data-business-action="report-tab"][data-report-tab="itc-reversals"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('BILL-100');
    await expect(page.locator('#business-report-printable')).toContainText('Karnataka Office Supplies');
    await expect(page.locator('#business-report-printable')).toContainText('Mark paid');
    await page.locator('[data-business-action="bill-mark-paid"][data-bill-id="bill1"]').click();
    await expect(page.locator('#login-status')).toContainText('Payment recorded');
    await expect(page.locator('#business-report-printable')).toContainText('No bills are overdue beyond 180 days');

    await page.locator('[data-business-action="report-tab"][data-report-tab="tds"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('TDS deducted (26Q)');
    await expect(page.locator('#business-report-printable')).toContainText('194C');
    await expect(page.locator('#business-report-printable')).toContainText('Karnataka Office Supplies');
    await expect(page.locator('#business-report-printable')).toContainText('BILL-100');

    await page.locator('[data-business-action="report-tab"][data-report-tab="bank-recon"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('Select bank account');
    await page.locator('[data-bankrecon-account]').selectOption('102');
    await page.locator('[data-bankrecon-file]').setInputFiles({
      name: 'bank-statement.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from([
        'Txn Date,Narration,Ref No,Withdrawal,Deposit,Balance',
        '14/06/2026,NEFT FROM BENGALURU RETAIL CUSTOMER,UTR-2360,,2360,2360',
        '15/06/2026,BANK CHARGES,CHG-118,118,,2242',
        '',
      ].join('\n')),
    });
    await page.locator('[data-business-action="bankrecon-upload"]').click();
    await expect(page.locator('#login-status')).toContainText('Statement imported');
    await expect(page.locator('#business-report-printable')).toContainText('Suggested matches');
    await expect(page.locator('#business-report-printable')).toContainText('UTR-2360');
    await expect(page.locator('#business-report-printable')).toContainText('BANK CHARGES');
    await page.locator('[data-bankrecon-offset="stmt-2"]').selectOption('301');
    await page.locator('[data-business-action="bankrecon-post-voucher"][data-stmt-id="stmt-2"]').click();
    await expect(page.locator('#login-status')).toContainText('Voucher posted');
    await page.locator('[data-business-action="bankrecon-match"][data-stmt-id="stmt-1"]').click();
    await expect(page.locator('#login-status')).toContainText('Matched');
    await expect(page.locator('#business-report-printable')).toContainText('Matched (1)');
    await expect(page.locator('#business-report-printable')).toContainText('reconciled');
    await page.locator('[data-business-action="bankrecon-unmatch"][data-match-id="match-1"]').click();
    await expect(page.locator('#login-status')).toContainText('Unmatched');
    await expect(page.locator('#business-report-printable')).toContainText('Suggested matches');

    await page.locator('[data-business-action="report-tab"][data-report-tab="bank-cash-book"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('Bank / Cash Book');
    await expect(page.locator('#business-report-printable')).toContainText('11001 - Cash in Hand');
    await expect(page.locator('#business-report-printable')).toContainText('11010 - Bank Account');
    await page.locator('[data-business-report-filters] select[name="book_type"]').selectOption('bank');
    await page.locator('[data-business-action="apply-report-filter"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('bank');
    await expect(page.locator('#business-report-printable')).toContainText('UTR-2360');
    await expect(page.locator('#business-report-printable')).toContainText('CHG-118');

    await page.locator('[data-business-action="report-tab"][data-report-tab="gst-settlement"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('Set-off for');
    await expect(page.locator('#business-report-printable')).toContainText('Net cash payable');
    await expect(page.locator('#business-report-printable')).toContainText('90.00');
    await expect(page.locator('#business-report-printable')).toContainText('Lock this period after settlement');
    await page.locator('[data-business-action="gst-post"]').click();
    await expect(page.locator('#login-status')).toContainText('GST settled');
    await expect(page.locator('#business-report-printable')).toContainText('settled');
    await expect(page.locator('#business-report-printable')).toContainText('period locked');

    await page.locator('[data-business-action="report-tab"][data-report-tab="inventory"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('Item master');
    await expect(page.locator('#business-report-printable')).toContainText('WIDGET-A');
    await page.locator('[data-item-form] input[name="item_code"]').fill('widget-b');
    await page.locator('[data-item-form] input[name="item_name"]').fill('Widget B');
    await page.locator('[data-item-form] input[name="item_hsn"]').fill('8473');
    await page.locator('[data-item-form] input[name="item_gst"]').fill('18');
    await page.locator('[data-item-form] input[name="item_open_qty"]').fill('2');
    await page.locator('[data-item-form] input[name="item_open_val"]').fill('300');
    await page.locator('[data-business-action="item-create"]').click();
    await expect(page.locator('#login-status')).toContainText('Item created');
    await expect(page.locator('#business-report-printable')).toContainText('WIDGET-B');
    await expect(page.locator('#business-report-printable')).toContainText('Weighted average (periodic)');
    await page.locator('[data-stock-movement-form] select[name="movement_type"]').selectOption('adjustment');
    await page.locator('[data-stock-movement-form] select[name="item_id"]').selectOption('item-widget-a');
    await page.locator('[data-stock-movement-form] input[name="movement_date"]').fill('2026-06-20');
    await page.locator('[data-stock-movement-form] input[name="quantity"]').fill('2');
    await page.locator('[data-stock-movement-form] input[name="value"]').fill('300');
    await page.locator('[data-stock-movement-form] input[name="reason"]').fill('Cycle count correction');
    await page.locator('[data-business-action="stock-movement-create"]').click();
    await expect(page.locator('#login-status')).toContainText('Stock movement recorded');
    await expect(page.locator('#business-report-printable')).toContainText('Cycle count correction');
    await page.locator('[data-stock-asof]').fill('2026-06-30');
    await page.locator('[data-business-action="stock-register-load"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('Total closing stock');
    await expect(page.locator('#business-report-printable')).toContainText('Adj in');
    await expect(page.locator('#business-report-printable')).toContainText('2.000');
    await expect(page.locator('#business-report-printable')).toContainText('closing');
    await expect(page.locator('#business-report-printable')).toContainText('2,100.00');
    await page.locator('[data-business-action="closing-stock-post"]').click();
    await expect(page.locator('#login-status')).toContainText('Closing stock posted');
    await expect(page.locator('#business-report-printable')).toContainText('Last closing-stock journal');
    await page.locator('[data-business-action="item-deactivate"][data-item-id="item-2"]').click();
    await expect(page.locator('#login-status')).toContainText('Item deactivated');

    await page.locator('[data-business-action="report-tab"][data-report-tab="fixed-assets"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('Fixed-asset register');
    await expect(page.locator('#business-report-printable')).toContainText('Delivery Van');
    await page.locator('[data-business-action="fa-toggle-form"]').click();
    await page.locator('[data-fa-form] input[name="fa_name"]').fill('Office Laptop');
    await page.locator('[data-fa-form] select[name="fa_account"]').selectOption('16001');
    await page.locator('[data-fa-form] input[name="fa_date"]').fill('2026-04-01');
    await page.locator('[data-fa-form] input[name="fa_cost"]').fill('60000');
    await page.locator('[data-fa-form] input[name="fa_salvage"]').fill('5000');
    await page.locator('[data-fa-form] input[name="fa_life"]').fill('5');
    await page.locator('[data-business-action="fa-create"]').click();
    await expect(page.locator('#login-status')).toContainText('Asset registered');
    await expect(page.locator('#business-report-printable')).toContainText('Office Laptop');
    await page.locator('[data-dep-fy]').selectOption('2026-27');
    await page.locator('[data-business-action="dep-preview"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('ready to post');
    await expect(page.locator('#business-report-printable')).toContainText('Depreciation run');
    await page.locator('[data-business-action="dep-post"]').click();
    await expect(page.locator('#login-status')).toContainText('Depreciation posted');
    await expect(page.locator('#business-report-printable')).toContainText('already posted');
    const fixedAssetRow = page.locator('#business-report-printable table').first().getByRole('row', { name: /Delivery Van/ });
    await fixedAssetRow.locator('[data-fa-dispose-date]').fill('2027-03-31');
    await fixedAssetRow.locator('[data-fa-dispose-sale]').fill('70000');
    await fixedAssetRow.locator('[data-fa-dispose-bank]').selectOption('11010');
    await fixedAssetRow.getByRole('button', { name: 'Dispose' }).click();
    await expect(page.locator('#login-status')).toContainText('Asset disposed');
    const disposedRegisterRow = page.locator('#business-report-printable table').first().getByRole('row', { name: /Delivery Van/ });
    await expect(disposedRegisterRow).toContainText('disposed');
    await expect(disposedRegisterRow).toContainText('Journal #FAD-2026-001');

    await page.locator('[data-business-action="report-tab"][data-report-tab="gst-returns"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('GSTR-3B summary');
    await expect(page.locator('#business-report-printable')).toContainText('GSTIN 29ABCDE1234F1Z5');
    await expect(page.locator('#business-report-printable')).toContainText('6.1 Payment of tax');
    await expect(page.locator('#business-report-printable')).toContainText('Net cash payable');
    await page.locator('[data-business-action="gst-return-type"][data-return-type="gstr1"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('GSTR-1 outward supplies');
    await expect(page.locator('#business-report-printable')).toContainText('B2B (4A)');
    await expect(page.locator('#business-report-printable')).toContainText('HSN summary');
    await expect(page.locator('#business-report-printable')).toContainText('9983');

    await page.locator('[data-business-action="report-tab"][data-report-tab="period-locks"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('Finalise a month after filing its GST return');
    await expect(page.locator('#business-report-printable')).toContainText('2026-05');
    await page.locator('[data-period-lock-input]').fill('2026-06');
    await page.locator('[data-business-action="lock-period"]').click();
    await expect(page.locator('#login-status')).toContainText('Period locked');
    await expect(page.locator('#business-report-printable')).toContainText('2026-06');
    await page.locator('[data-business-action="unlock-period"][data-period="2026-06"]').click();
    await expect(page.locator('#login-status')).toContainText('Period unlocked');

    await page.locator('[data-business-action="report-tab"][data-report-tab="opening-yearend"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('Opening balances (CSV import)');
    await page.locator('[data-ob-asof]').fill('2026-04-01');
    await page.locator('[data-ob-file]').setInputFiles({
      name: 'opening-balances.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from([
        'account_code,account_name,party,debit,credit',
        '11010,Bank Account,,150000,',
        '12001,Sundry Debtors,CUST-001,40000,',
        '21001,Sundry Creditors,VEND-001,,30000',
        '',
      ].join('\n')),
    });
    await page.locator('[data-business-action="ob-preview"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('3 line(s) resolved as of 2026-04-01');
    await expect(page.locator('#business-report-printable')).toContainText('ready to post');
    await expect(page.locator('#business-report-printable')).toContainText('Bengaluru Retail Customer');
    await expect(page.locator('#business-report-printable')).toContainText('Karnataka Office Supplies');
    await expect(page.locator('#business-report-printable')).toContainText('31004 - Opening Balance Equity');
    await expect(page.locator('#business-report-printable')).toContainText('1,60,000.00');
    await expect(page.locator('[data-business-action="ob-post"]')).toBeVisible();
    await page.locator('[data-business-action="ob-post"]').click();
    await expect(page.locator('#login-status')).toContainText('Opening balances posted');

    await page.locator('[data-business-action="report-tab"][data-report-tab="trial-balance"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('balanced');
    await expect(page.locator('#business-report-printable')).toContainText('Bank Account');
    await expect(page.locator('#business-report-printable')).toContainText('Sundry Debtors');
    await expect(page.locator('#business-report-printable')).toContainText('Sundry Creditors');
    await expect(page.locator('#business-report-printable')).toContainText('Opening Balance Equity');
    await page.locator('[data-business-action="report-tab"][data-report-tab="statements"]').click();
    await page.locator('[data-stmt-party]').selectOption('p2');
    await page.locator('[data-stmt-kind]').selectOption('receivable');
    await page.locator('[data-stmt-from]').fill('2026-06-01');
    await page.locator('[data-stmt-to]').fill('2026-06-30');
    await page.locator('[data-business-action="stmt-load"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('Opening');
    await expect(page.locator('#business-report-printable')).toContainText('40,000.00');
    await expect(page.locator('#business-report-printable')).toContainText('42,360.00');

    await page.locator('[data-business-action="report-tab"][data-report-tab="opening-yearend"]').click();
    await page.locator('[data-ob-file]').setInputFiles({
      name: 'opening-balances.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from('account_code,account_name,party,debit,credit\n11010,Bank Account,,150000,\n'),
    });
    await page.locator('[data-business-action="ob-preview"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('Opening journal already posted');
    await expect(page.locator('#business-report-printable')).toContainText('Reverse it first');
    await expect(page.locator('[data-ob-allow-duplicate]')).toBeVisible();
    await page.locator('[data-business-action="ob-export"]').click();
    await expect(page.locator('#api-output')).toContainText('ob_export');

    await page.locator('[data-ye-fy]').selectOption('2025-26');
    await page.locator('[data-business-action="ye-preview"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('FY 2025-26');
    await expect(page.locator('#business-report-printable')).toContainText('ready to close');
    await expect(page.locator('#business-report-printable')).toContainText('4001 - Sales');
    await expect(page.locator('#business-report-printable')).toContainText('5001 - Office Expense');
    await expect(page.locator('#business-report-printable')).toContainText('31003 - Retained Earnings');
    await expect(page.locator('#business-report-printable')).toContainText('1,00,000.00');
    await expect(page.locator('#business-report-printable')).toContainText('60,000.00');
    await expect(page.locator('#business-report-printable')).toContainText('40,000.00');
    await expect(page.locator('[data-business-action="ye-post"]')).toBeVisible();
    await page.locator('[data-business-action="ye-post"]').click();
    await expect(page.locator('#login-status')).toContainText('Year closed');
    await expect(page.locator('#business-report-printable')).toContainText('already closed');
    await expect(page.locator('#business-report-printable')).toContainText('YE-2025-26-001');
    await expect(page.locator('#business-report-printable')).toContainText('Reverse that entry to reopen the year');
    await expect(page.locator('[data-business-action="ye-post"]')).toHaveCount(0);

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
    await expect(page.locator('[data-settings-detail="organization"] textarea[data-settings-json="organization"]')).toContainText('29ABCDE1234F1Z5');
    await expect(page.locator('[data-settings-detail="organization"] textarea[data-settings-json="organization"]')).toContainText('regular');
    await page.getByRole('button', { name: 'Back to Settings' }).click();
    await expect(page.locator('[data-settings-detail="organization"]')).toBeHidden();
    await expect(page.locator('[data-settings-card="tax-and-compliance"]')).toContainText('GST registration mode');
    await page.locator('[data-settings-card="tax-and-compliance"]').getByRole('button', { name: 'Open Related Area' }).click();
    await expect(page.locator('.erp-workspace-panel')).toContainText('GST Returns');
    await expect(page.locator('.erp-workspace-panel')).toContainText('GSTR-1');
    await page.locator('nav#nav a[data-business-workspace="settings"]').click();
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

    await expect(page.locator('[data-ca-document-form] select[name="client_id"] option[value="caclient1"]')).toHaveCount(1);
    const caDocumentForm = page.locator('[data-ca-document-form]');
    await caDocumentForm.locator('select[name="client_id"]').selectOption('caclient1');
    await caDocumentForm.locator('input[name="client_name"]').fill('Jayam Publications');
    await caDocumentForm.locator('select[name="document_type"]').selectOption('Bank statement');
    await caDocumentForm.locator('input[name="period"]').fill('May 2026');
    await caDocumentForm.locator('input[name="assigned_to"]').fill('Staff A');
    await caDocumentForm.locator('input[name="client_owner"]').fill('Partner A');
    await caDocumentForm.locator('select[name="priority"]').selectOption('high');
    await caDocumentForm.locator('select[name="compliance_area"]').selectOption('GST');
    await caDocumentForm.locator('input[name="ca_attachments"]').setInputFiles({
      name: 'gst-working.xlsx',
      mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      buffer: Buffer.from('PK'),
    });
    await Promise.all([
      page.waitForResponse(response =>
        response.url().includes('/api/v1/business/ca-documents') &&
        response.request().method() === 'POST'
      ),
      caDocumentForm.evaluate(form => form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))),
    ]);
    await expect(page.locator('.erp-workspace-panel')).toContainText('Book primary');
    await expect(page.locator('.erp-workspace-panel')).toContainText('attachment(s)');

    await page.locator('nav#nav a[data-business-workspace="sales"]').click();
    await page.keyboard.press('Control+Alt+I');
    await expect(page.locator('[data-invoice-form]')).toBeVisible();
    await expect(page.locator('[data-invoice-form] select[name="customer_party_id"]')).toBeFocused();
    await page.locator('[data-invoice-form] select[name="customer_party_id"]').selectOption('p2');
    await page.locator('[data-invoice-form] input[name="invoice_date"]').fill('2026-06-13');
    await page.locator('[data-invoice-form] input[name="due_date"]').fill('2026-06-30');
    await page.locator('[data-invoice-form] select[name="income_account_code"]').selectOption('4001');
    await page.locator('[data-invoice-form] input[name="place_of_supply"]').fill('Karnataka');
    await page.locator('[data-invoice-form] input[name="reference"]').fill('PO-100');
    await page.locator('[data-invoice-form] select[name="cost_centre_id"]').selectOption('dim-cc-blr');
    await page.locator('[data-invoice-form] select[name="project_id"]').selectOption('dim-prj-alpha');
    await page.locator('[data-invoice-line] input[name="description"]').fill('Consulting service');
    await page.locator('[data-invoice-line] input[name="hsn_sac"]').fill('9983');
    await page.locator('[data-invoice-line] input[name="quantity"]').fill('2');
    await page.locator('[data-invoice-line] input[name="rate"]').fill('1000');
    await page.locator('[data-invoice-line] input[name="gst_rate"]').fill('18');
    await page.locator('[data-invoice-line] select[name="line_cost_centre_id"]').selectOption('dim-cc-mum');
    await page.locator('[data-invoice-line] select[name="line_project_id"]').selectOption('dim-prj-alpha');
    await page.keyboard.press('Alt+L');
    await expect(page.locator('[data-invoice-line]')).toHaveCount(2);
    await page.locator('[data-invoice-line]').last().getByRole('button').click();
    await expect(page.locator('[data-invoice-line]')).toHaveCount(1);
    await expect(page.locator('[data-total-invoice]')).toContainText('2,360');
    await page.keyboard.press('Control+Enter');
    await expect(page.locator('#login-status')).toContainText('Invoice posted');
    await expect(page.locator('.erp-workspace-panel')).toContainText('INV-2026-001');
    await expect(page.getByRole('row', { name: /INV-2026-001/ })).toContainText('posted');

    await page.locator('nav#nav a[data-business-workspace="reports"]').click();
    await page.locator('[data-business-action="report-tab"][data-report-tab="dimensions"]').click();
    await expect(page.locator('#business-report-printable')).toContainText('Mumbai');
    await expect(page.locator('#business-report-printable')).toContainText('2,000.00');
    await expect(page.locator('#business-report-printable')).toContainText('Credit notes reduce income');
    await expect(page.locator('#business-report-printable')).toContainText('Branch consolidated P&L');
    await expect(page.locator('#business-report-printable')).toContainText('Bengaluru Head Office');
    await expect(page.locator('#business-report-printable')).toContainText('Unassigned');
    await expect(page.locator('#business-report-printable')).toContainText('MUM - Mumbai');
    const exportResponse = await Promise.all([
      page.waitForResponse(response => response.url().includes('/api/v1/business/dimensions/report/export')),
      page.locator('[data-business-action="dim-report-export"][data-format="json"]').click(),
    ]);
    expect(exportResponse[0].headers()['x-sanmitra-export-governed']).toBe('true');
    expect(exportResponse[0].headers()['x-sanmitra-export-format']).toBe('json');

    await page.locator('nav#nav a[data-business-workspace="sales"]').click();
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
    await page.keyboard.press('Control+Alt+B');
    await expect(page.locator('[data-bill-form]')).toBeVisible();
    await expect(page.locator('[data-bill-form] select[name="vendor_party_id"]')).toBeFocused();
    await page.locator('[data-bill-form] select[name="vendor_party_id"]').selectOption('p1');
    await page.locator('[data-bill-form] input[name="bill_number"]').fill('BILL-100');
    await page.locator('[data-bill-form] input[name="bill_date"]').fill('2026-06-13');
    await page.locator('[data-bill-form] input[name="due_date"]').fill('2026-06-30');
    await page.locator('[data-bill-form] select[name="expense_account_code"]').selectOption('5001');
    await page.locator('[data-bill-form] input[name="place_of_supply"]').fill('Karnataka');
    await page.locator('[data-bill-form] select[name="cost_centre_id"]').selectOption('dim-cc-blr');
    await page.locator('[data-bill-form] select[name="project_id"]').selectOption('dim-prj-alpha');
    await page.locator('[data-bill-line] input[name="description"]').fill('Office supplies');
    await page.locator('[data-bill-line] input[name="hsn_sac"]').fill('4820');
    await page.locator('[data-bill-line] input[name="quantity"]').fill('3');
    await page.locator('[data-bill-line] input[name="rate"]').fill('500');
    await page.locator('[data-bill-line] input[name="gst_rate"]').fill('18');
    await page.locator('[data-bill-line] select[name="line_cost_centre_id"]').selectOption('dim-cc-mum');
    await page.locator('[data-bill-line] select[name="line_project_id"]').selectOption('dim-prj-alpha');
    await page.keyboard.press('Alt+L');
    await expect(page.locator('[data-bill-line]')).toHaveCount(2);
    await page.locator('[data-bill-line]').last().getByRole('button').click();
    await expect(page.locator('[data-bill-line]')).toHaveCount(1);
    await expect(page.locator('[data-total-bill]')).toContainText('1,770');
    await page.keyboard.press('Control+Enter');
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
    await page.keyboard.press('Control+Alt+C');
    await expect(page.locator('[data-cn-form]')).toBeVisible();
    await expect(page.locator('[data-cn-form] select[name="customer_party_id"]')).toBeFocused();
    await page.locator('[data-cn-form] select[name="customer_party_id"]').selectOption('p2');
    await page.locator('[data-cn-form] input[name="note_date"]').fill('2026-06-13');
    await page.locator('[data-cn-form] select[name="original_invoice_id"]').selectOption('inv1');
    await expect(page.locator('[data-cn-form] select[name="original_invoice_id"]')).toContainText('INV-2026-001');
    await page.locator('[data-cn-form] select[name="reason"]').selectOption('sales_return');
    await page.locator('[data-cn-form] select[name="income_account_code"]').selectOption('4001');
    await page.locator('[data-cn-form] input[name="place_of_supply"]').fill('Karnataka');
    await page.locator('[data-cn-form] select[name="cost_centre_id"]').selectOption('dim-cc-blr');
    await page.locator('[data-cn-form] select[name="project_id"]').selectOption('dim-prj-alpha');
    await page.locator('[data-cn-line] select[name="line_cost_centre_id"]').selectOption('dim-cc-mum');
    await page.locator('[data-cn-line] select[name="line_project_id"]').selectOption('dim-prj-alpha');
    await page.locator('[data-cn-line] input[name="description"]').fill('Returned consulting service');
    await page.locator('[data-cn-line] input[name="hsn_sac"]').fill('9983');
    await page.locator('[data-cn-line] input[name="uqc"]').fill('NOS');
    await page.locator('[data-cn-line] input[name="quantity"]').fill('1');
    await page.locator('[data-cn-line] input[name="rate"]').fill('1000');
    await page.locator('[data-cn-line] input[name="gst_rate"]').fill('18');
    await page.keyboard.press('Alt+L');
    await expect(page.locator('[data-cn-line]')).toHaveCount(2);
    await page.locator('[data-cn-line]').last().getByRole('button').click();
    await expect(page.locator('[data-cn-line]')).toHaveCount(1);
    await expect(page.locator('[data-total-note]')).toContainText('1,180');
    await page.keyboard.press('Control+Enter');
    await expect(page.locator('#login-status')).toContainText('Credit note posted');
    await expect(page.locator('.erp-workspace-panel')).toContainText('CN-2026-001');
    await expect(page.getByRole('row', { name: /CN-2026-001/ })).toContainText('posted');

    await page.getByRole('row', { name: /CN-2026-001/ }).getByRole('button', { name: 'View' }).click();
    await expect(page.locator('.erp-workspace-panel')).toContainText('Credit Note CN-2026-001');
    await expect(page.locator('[data-credit-note-printable]')).toContainText('against INV-2026-001');
    await expect(page.locator('.erp-workspace-panel')).toContainText('Returned consulting service');
    await expect(page.locator('[data-credit-note-printable] [data-business-action="print-credit-note"]')).toBeVisible();
    await page.locator('[data-credit-note-printable] [data-business-action="export-credit-note-json"]').click();
    await expect(page.locator('#api-output')).toContainText('credit_note_export');
    await page.getByRole('button', { name: 'Reverse' }).click();
    await expect(page.locator('.reversal-panel')).toBeVisible();
    await page.locator('[data-reversal-date]').fill('2026-06-13');
    await page.getByRole('button', { name: 'Confirm reverse' }).click();
    await expect(page.locator('#login-status')).toContainText('Credit note reversed');
    await expect(page.locator('.erp-workspace-panel')).toContainText('Reversed');

    await page.locator('nav#nav a[data-business-workspace="debit-notes"]').click();
    await page.keyboard.press('Control+Alt+D');
    await expect(page.locator('[data-dn-form]')).toBeVisible();
    await expect(page.locator('[data-dn-form] select[name="vendor_party_id"]')).toBeFocused();
    await page.locator('[data-dn-form] select[name="vendor_party_id"]').selectOption('p1');
    await page.locator('[data-dn-form] input[name="note_date"]').fill('2026-06-13');
    await page.locator('[data-dn-form] select[name="original_bill_id"]').selectOption('bill1');
    await expect(page.locator('[data-dn-form] select[name="original_bill_id"]')).toContainText('BILL-100');
    await page.locator('[data-dn-form] select[name="reason"]').selectOption('purchase_return');
    await page.locator('[data-dn-form] select[name="expense_account_code"]').selectOption('5001');
    await page.locator('[data-dn-form] input[name="place_of_supply"]').fill('Karnataka');
    await page.locator('[data-dn-form] select[name="cost_centre_id"]').selectOption('dim-cc-blr');
    await page.locator('[data-dn-form] select[name="project_id"]').selectOption('dim-prj-alpha');
    await page.locator('[data-dn-line] select[name="line_cost_centre_id"]').selectOption('dim-cc-mum');
    await page.locator('[data-dn-line] select[name="line_project_id"]').selectOption('dim-prj-alpha');
    await page.locator('[data-dn-line] input[name="description"]').fill('Returned office supplies');
    await page.locator('[data-dn-line] input[name="hsn_sac"]').fill('4820');
    await page.locator('[data-dn-line] input[name="quantity"]').fill('1');
    await page.locator('[data-dn-line] input[name="rate"]').fill('500');
    await page.locator('[data-dn-line] input[name="gst_rate"]').fill('18');
    await page.keyboard.press('Alt+L');
    await expect(page.locator('[data-dn-line]')).toHaveCount(2);
    await page.locator('[data-dn-line]').last().getByRole('button').click();
    await expect(page.locator('[data-dn-line]')).toHaveCount(1);
    await expect(page.locator('[data-total-note]')).toContainText('590');
    await page.keyboard.press('Control+Enter');
    await expect(page.locator('#login-status')).toContainText('Debit note posted');
    await expect(page.locator('.erp-workspace-panel')).toContainText('DN-2026-001');
    await expect(page.getByRole('row', { name: /DN-2026-001/ })).toContainText('posted');

    await page.getByRole('row', { name: /DN-2026-001/ }).getByRole('button', { name: 'View' }).click();
    await expect(page.locator('.erp-workspace-panel')).toContainText('Debit Note DN-2026-001');
    await expect(page.locator('[data-debit-note-printable]')).toContainText('against BILL-100');
    await expect(page.locator('.erp-workspace-panel')).toContainText('Returned office supplies');
    await expect(page.locator('[data-debit-note-printable] [data-business-action="print-debit-note"]')).toBeVisible();
    await page.locator('[data-debit-note-printable] [data-business-action="export-debit-note-json"]').click();
    await expect(page.locator('#api-output')).toContainText('debit_note_export');
    await page.getByRole('button', { name: 'Reverse' }).click();
    await expect(page.locator('.reversal-panel')).toBeVisible();
    await page.locator('[data-reversal-date]').fill('2026-06-13');
    await page.getByRole('button', { name: 'Confirm reverse' }).click();
    await expect(page.locator('#login-status')).toContainText('Debit note reversed');
    await expect(page.locator('.erp-workspace-panel')).toContainText('Reversed');
  });
});
