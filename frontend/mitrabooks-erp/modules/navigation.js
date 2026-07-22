// ══════════════════════════════════════════════════════════════════════
// SECTION: NAVIGATION GROUPS + ITEMS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged.
// ══════════════════════════════════════════════════════════════════════

/**
 * Sidebar structure for MitraBooks ERP (hardcoded fallback / primary nav).
 */
export function businessNavigationGroups() {
  return [
    {
      name: "Main Workspaces",
      items: [
        { label: "Dashboard", businessWorkspace: "overview", icon: "DB", module: { module_key: "business", frontend_path: "/business", enabled: true } },
        { label: "Parties", businessWorkspace: "parties", icon: "PT", module: { module_key: "business", frontend_path: "/business/parties", enabled: true } },
      ],
    },
    {
      name: "Core Ledger",
      items: [
        { label: "Core Ledger", businessWorkspace: "accounting", icon: "CL", module: { module_key: "accounting", frontend_path: "/accounting", enabled: true } },
        { label: "Chart of Accounts", businessWorkspace: "coa", icon: "CA", module: { module_key: "accounting", frontend_path: "/accounting/coa", enabled: true } },
        { label: "Journal Post", businessWorkspace: "vouchers", icon: "JP", module: { module_key: "business", frontend_path: "/business/vouchers", enabled: true } },
        { label: "Audit Trails", businessWorkspace: "audit", icon: "AT", module: { module_key: "audit", frontend_path: "/audit", enabled: true } },
      ],
    },
    {
      name: "Income (Sales)",
      items: [
        { label: "Sales", businessWorkspace: "sales", icon: "SL", module: { module_key: "sales", frontend_path: "/business/sales", enabled: true } },
        { label: "Credit Notes", businessWorkspace: "credit-notes", icon: "CN", module: { module_key: "sales", frontend_path: "/business/credit-notes", enabled: true } },
      ],
    },
    {
      name: "Expenses (Purchases)",
      items: [
        { label: "Bills (Vendor)", businessWorkspace: "bills", icon: "BL", module: { module_key: "purchase", frontend_path: "/business/bills", enabled: true } },
        { label: "Purchase Orders", businessWorkspace: "purchase-orders", icon: "PO", module: { module_key: "purchase", frontend_path: "/business/purchase-orders", enabled: false } },
        { label: "Debit Notes", businessWorkspace: "debit-notes", icon: "DN", module: { module_key: "purchase", frontend_path: "/business/debit-notes", enabled: true } },
        { label: "Expenses log", businessWorkspace: "expenses", icon: "EX", module: { module_key: "business", frontend_path: "/business/expenses", enabled: false } },
      ],
    },
    {
      name: "Banking & Treasury",
      items: [
        { label: "Bank Reconciliation", businessWorkspace: "bank-recon", icon: "BR", module: { module_key: "banking", frontend_path: "/business/bank-recon", enabled: true } },
        { label: "UPI / QR Payments", businessWorkspace: "upi-payments", icon: "UP", module: { module_key: "payments", frontend_path: "/business/upi-payments", enabled: false } },
        { label: "Reconciliation", businessWorkspace: "reconciliation", icon: "RC", module: { module_key: "accounting", frontend_path: "/accounting/reconciliation", enabled: true } },
      ],
    },
    {
      name: "Taxes & Compliance",
      items: [
        { label: "GST Returns", businessWorkspace: "gst-returns", icon: "GT", module: { module_key: "gst", frontend_path: "/gst/returns", enabled: true } },
        { label: "TDS / TCS", businessWorkspace: "tds-tcs", icon: "TD", module: { module_key: "tax", frontend_path: "/tax/tds-tcs", enabled: true } },
        { label: "CA Practice Portal", businessWorkspace: "ca-access", icon: "CA", module: { module_key: "ca_access", frontend_path: "/business/ca-access", enabled: true } },
      ],
    },
    {
      name: "Intelligence & Reports",
      items: [
        { label: "Financial Statements", businessWorkspace: "reports", icon: "FS", module: { module_key: "accounting", frontend_path: "/accounting/reports", enabled: true } },
        { label: "Financial Health", businessWorkspace: "financial-health", icon: "FH", module: { module_key: "analytics", frontend_path: "/business/financial-health", enabled: true } },
        { label: "Analytics", businessWorkspace: "analytics", icon: "AN", module: { module_key: "analytics", frontend_path: "/business/analytics", enabled: false } },
      ],
    },
    {
      name: "Human Resources",
      items: [
        // Enterprise HR/Payroll add-on. The menu always renders; the workspace
        // itself gates on GET /business/hr/access (platform + tenant entitlement).
        { label: "HR & Payroll", businessWorkspace: "hr", icon: "HR", module: { module_key: "hr", frontend_path: "/business/hr", enabled: true } },
      ],
    },
    {
      name: "Manufacturing",
      items: [
        // Enterprise Cost-Centre + Manufacturing add-on. The menu always renders;
        // the workspace gates on GET /business/mfg/access (platform + tenant + role).
        { label: "Manufacturing", businessWorkspace: "manufacturing", icon: "MFG", module: { module_key: "manufacturing", frontend_path: "/business/mfg", enabled: true } },
      ],
    },
    {
      name: "Configuration & Extensions",
      items: [
        { label: "Settings", businessWorkspace: "settings", icon: "ST", module: { module_key: "business", frontend_path: "/business/settings", enabled: true } },
        { label: "Future Hub & Add-ons", businessWorkspace: "addons", icon: "FH", module: { module_key: "addons", frontend_path: "/business/addons", enabled: false }, badge: "New" },
        { label: "+ Custom Menu", businessWorkspace: "custom-menu", icon: "CM", module: { module_key: "custom_menu", frontend_path: "/business/custom-menu", enabled: false } },
      ],
    },
  ];
}

export function businessNavigationItems() {
  return businessNavigationGroups().flatMap((group) => group.items);
}
