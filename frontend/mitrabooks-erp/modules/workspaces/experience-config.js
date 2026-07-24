// ====================================================================
// SECTION: EXPERIENCE DETECTION + PRODUCT SHELL CONFIG
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. No init wiring — leaf module with no app.js deps.
// ====================================================================

export function isMandirHost() {
  const host = String(window.location.hostname || "").toLowerCase();
  return host === "mandirmitra.sanmitratech.in"
    || host === "www.mandirmitra.sanmitratech.in"
    || host.includes("mandirmitra");
}

export function isGruhaHost() {
  const host = String(window.location.hostname || "").toLowerCase();
  return host === "gruhamitra.sanmitratech.in"
    || host === "www.gruhamitra.sanmitratech.in"
    || host.includes("gruhamitra");
}

export function isProductionShell() {
  const host = String(window.location.hostname || "").toLowerCase();
  return host && host !== "localhost" && host !== "127.0.0.1" && host !== "::1";
}

export function initialExperience() {
  if (isMandirHost()) {
    return "mandir";
  }
  if (isGruhaHost()) {
    return "gruha";
  }
  return "mitrabooks";
}
export const entitlementModulesByOrgType = {
  TEMPLE: ["temple", "accounting", "audit"],
  HOUSING: ["housing", "accounting", "audit"],
  BUSINESS: ["business", "accounting", "gst", "inventory", "audit"],
  PROFESSIONAL: ["professional", "accounting", "billing", "audit"],
};

export const orgSelectorMeta = {
  BUSINESS: {
    label: "Business Suite",
    subtitle: "SME and accounting",
    statusTitle: "Business workspace active",
    statusCopy: "Using the signed-in business tenant context.",
  },
  PROFESSIONAL: {
    label: "Professional Suite",
    subtitle: "Billing and invoicing",
    statusTitle: "Professional workspace active",
    statusCopy: "Using the signed-in MitraBooks tenant context for billing, client accounts, receipts, and reports.",
  },
  CA_PRACTICE: {
    label: "CA Practice Portal",
    subtitle: "Client document workflow",
    statusTitle: "CA Practice Portal active",
    statusCopy: "Using tenant-scoped document metadata, review queue, staff assignment, and compliance tracking.",
  },
};

export const experienceConfig = {
  mitrabooks: {
    title: "MitraBooks Pro",
    subtitle: "Unified Enterprise ERP",
    logo: "../assets/brand/mitrabooks-pro-logo.png",
    video: "../assets/brand/mitrabooks-pro-logo.mp4",
    theme: "",
    scopeTitle: "MitraBooks Business Workspace",
    scopeCopy: "Business, GST, inventory, parties, vouchers, and financial reports stay close to the old MitraBooks accounting layout.",
    legacyTitle: "MitraBooks workspace",
    legacyCopy: "Business, GST, inventory, parties, vouchers, and financial reports.",
    dashboard: {
      type: "business",
      stats: [
        ["Cash and Bank", "Rs. 8.4L", "available balance"],
        ["Receivables", "Rs. 2.1L", "open invoices"],
        ["Payables", "Rs. 96K", "vendor dues"],
        ["GST Filing", "Ready", "current period"],
      ],
      actions: ["Sales Voucher", "Purchase Entry", "Journal Entry", "Ledger Report", "Trial Balance", "GST Summary"],
      activity: ["Receipt posted from customer account", "Inventory purchase voucher drafted", "Month-end ledger review pending"],
    },
    modules: [
      { module_key: "business", display_name: "Dashboard", frontend_path: "/business", nav_group: "Operations", enabled: true },
      { module_key: "accounting", display_name: "Accounts", frontend_path: "/accounting", nav_group: "Finance", enabled: true },
      { module_key: "gst", display_name: "GST Compliance", frontend_path: "/gst", nav_group: "Compliance", enabled: true },
      { module_key: "inventory", display_name: "Inventory", frontend_path: "/inventory", nav_group: "Operations", enabled: true },
      { module_key: "audit", display_name: "Audit Log", frontend_path: "/audit", nav_group: "Administration", enabled: true },
    ],
  },
  platform: {
    title: "Platform Owner",
    subtitle: "Cross-module onboarding, tenant, subscription, and module status",
    logo: "../assets/brand/mitrabooks-logo.jpg",
    video: "",
    theme: "",
    scopeTitle: "Platform Owner Workspace",
    scopeCopy: "Read-only control view for MandirMitra, GruhaMitra, and MitraBooks onboarding, subscriptions, tenant status, and enabled modules.",
    legacyTitle: "Platform owner dashboard",
    legacyCopy: "Central review layer over module-wise onboarding. Approval actions are intentionally separate from this read-only view.",
    dashboard: {
      type: "platform",
      summary: [
        ["Pending Approvals", "0", "module-wise onboarding"],
        ["Active Tenants", "0", "all tracked apps"],
        ["Inactive Tenants", "0", "needs review"],
        ["Subscription Plans", "0", "configured plans"],
      ],
      appStatus: [
        ["MandirMitra", "0 pending", "0 tenants"],
        ["GruhaMitra", "0 pending", "0 tenants"],
        ["MitraBooks", "0 pending", "0 tenants"],
      ],
    },
    modules: [
      { module_key: "platform_owner", display_name: "Dashboard", frontend_path: "/platform-owner/dashboard", nav_group: "Administration", enabled: true },
      { module_key: "platform_owner", display_name: "Onboarding Requests", frontend_path: "/platform-owner/onboarding", nav_group: "Administration", enabled: true },
      { module_key: "platform_owner", display_name: "Tenant Status", frontend_path: "/platform-owner/tenants", nav_group: "Administration", enabled: true },
      { module_key: "platform_owner", display_name: "Subscriptions", frontend_path: "/platform-owner/subscriptions", nav_group: "Administration", enabled: true },
    ],
  },
  mandir: {
    title: "MandirMitra",
    subtitle: "Temple, trust, donation, seva, and accounting workflows",
    logo: "../assets/brand/mandirmitra-logo.jpeg",
    video: "../assets/brand/mandirmitra-logo.mp4",
    theme: "mandir-theme",
    scopeTitle: "MandirMitra Temple Workspace",
    scopeCopy: "Preserves the old temple layout pattern: dashboard, donations, devotees, sevas, panchang, reports, and accounting.",
    legacyTitle: "MandirMitra layout mode",
    legacyCopy: "Saffron/green visual treatment and temple-first navigation are retained for user familiarity.",
    dashboard: {
      type: "mandir",
      donations: [
        ["Today's Donation", "Rs. 24,500", "18 donations"],
        ["Cumulative for Month", "Rs. 6.8L", "412 donations"],
        ["Cumulative for Year", "Rs. 74.2L", "8,902 donations"],
      ],
      sevas: [
        ["Today's Seva", "Rs. 18,000", "27 bookings"],
        ["Cumulative for Month", "Rs. 4.2L", "685 bookings"],
        ["Cumulative for Year", "Rs. 38.5L", "6,430 bookings"],
      ],
      verification: [
        ["Public UPI Payments", "9 pending", "donation and seva confirmations"],
        ["Receipt Posting", "6 ready", "verified collections awaiting receipt"],
        ["Review Queue", "3 flagged", "amount or UTR needs checking"],
      ],
      groups: [
        ["Public Payments", "Review UPI confirmations, verify UTR, then post donation or seva receipt"],
        ["Sevas", "Book Sevas, Seva Bookings / Reschedule, Seva Management"],
        ["Accounting", "Chart of Accounts, Quick Expense, Journal Entries, Reports"],
      ],
    },
    modules: [
      { module_key: "temple", display_name: "Dashboard", frontend_path: "/temple/dashboard", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Sevas", frontend_path: "/temple/sevas", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Donations", frontend_path: "/temple/donations", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Devotees", frontend_path: "/temple/devotees", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Public Payments", frontend_path: "/temple/public-payments", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Receipts", frontend_path: "/temple/receipts", nav_group: "Operations", enabled: true },
      { module_key: "audit", display_name: "Reports", frontend_path: "/temple/reports", nav_group: "Administration", enabled: true },
      { module_key: "temple", display_name: "Panchang", frontend_path: "/temple/panchang", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Settings", frontend_path: "/temple/settings", nav_group: "Administration", enabled: true },
      { module_key: "audit", display_name: "Implementation Checks", frontend_path: "/temple/implementation-checks", nav_group: "Administration", enabled: true },
      { module_key: "platform_owner", display_name: "Platform Owners", frontend_path: "/platform-owner/dashboard", nav_group: "Administration", enabled: true },
      { module_key: "accounting", display_name: "Accounting", frontend_path: "/accounting", nav_group: "Finance", enabled: true },
    ],
  },
  gruha: {
    title: "GruhaMitra",
    subtitle: "Housing society operations with shared MitraBooks accounting",
    logo: "../assets/brand/gruhamitra-logo.png",
    video: "../assets/brand/gruhamitra-logo.mp4",
    theme: "gruha-theme",
    scopeTitle: "GruhaMitra Housing Workspace",
    scopeCopy: "Preserves the old housing layout pattern: dashboard, maintenance, members, complaints, reports, assets, and settings.",
    legacyTitle: "GruhaMitra layout mode",
    legacyCopy: "Housing-first navigation mirrors the old web app while using the unified shell.",
    dashboard: {
      type: "gruha",
      stats: [
        ["Society Balance", "Rs. 12.6L", "cash and bank"],
        ["This Month Billing", "Rs. 4.8L", "maintenance cycle"],
        ["Dues Pending", "Rs. 1.2L", "42 units"],
        ["Complaints Open", "18", "service desk"],
      ],
      actions: ["Accounting", "Generate Bills", "Members", "Find Society", "My Memberships", "Join Requests", "Complaints", "Reports", "Message", "Meeting", "Society Assets", "Settings"],
      activity: ["Maintenance collection posted", "New member approval pending", "Lift complaint assigned to vendor"],
      trend: ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
    },
    modules: [
      { module_key: "housing", display_name: "Dashboard", frontend_path: "/housing/dashboard", nav_group: "Operations", enabled: true },
      { module_key: "housing", display_name: "Maintenance", frontend_path: "/housing/maintenance", nav_group: "Operations", enabled: true },
      { module_key: "housing", display_name: "Members", frontend_path: "/housing/members", nav_group: "Operations", enabled: true },
      { module_key: "housing", display_name: "Complaints", frontend_path: "/housing/complaints", nav_group: "Operations", enabled: true },
      { module_key: "accounting", display_name: "Accounting", frontend_path: "/accounting", nav_group: "Finance", enabled: true },
      { module_key: "housing", display_name: "Reports", frontend_path: "/housing/reports", nav_group: "Finance", enabled: true },
      { module_key: "audit", display_name: "Settings", frontend_path: "/housing/settings", nav_group: "Administration", enabled: true },
    ],
  },
};

