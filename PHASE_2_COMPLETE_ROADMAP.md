# Phase 2: Complete Business ERP Cycle - Parallel Execution Roadmap

**Goal:** Build and test a complete business accounting workflow: Parties → Vouchers → Dashboard → Sales → Purchase

**Testing Strategy:** One integrated cycle test after all components complete (not incremental)

---

## 📦 Phase 2 Components Overview

| Component | Status | Effort | Dependencies | Start Date |
|-----------|--------|--------|--------------|-----------|
| **Phase 2A: Party Master** | ✅ DONE | - | - | Complete |
| **Phase 2B: Typed Vouchers** | 🔄 IN PROGRESS | 4h | Phase 2A | Now |
| **Phase 2C: Dashboard Enhancements** | 🔄 PARALLEL | 3h | Phase 2A | Now |
| **Phase 2D: Sales Invoices** | 📋 PLANNED | 4h | Phase 2B | After Vouchers |
| **Phase 2E: Purchase Invoices** | 📋 PLANNED | 4h | Phase 2B | After Vouchers |
| **Phase 2F: Full Cycle Testing** | 📋 PLANNED | 2h | All above | Last |

---

## 🔧 Phase 2B: Typed Voucher Entry (4 hours)

### Scope: Payment, Receipt, Contra, Journal Vouchers

#### **2B.1: Searchable Account Selector** (1 hour)
**Why first:** Used by all 4 voucher types

**Files to modify:** `app.js`, `index.css`

**Implementation:**
```javascript
// 1. Load COA on app init
async function loadBusinessAccounts() {
  // Already exists (line 4638)
  // Returns: lastBusinessAccounts array
}

// 2. Account selector component
function renderAccountSelector(fieldId, selectedId = null) {
  // Returns HTML for searchable dropdown:
  // <input type="text" data-account-search>
  // <ul id="account-suggestions" hidden>
  //   <li data-account-id="1">1000 - Cash</li>
  //   <li data-account-id="2">2000 - Bank</li>
  // </ul>
}

// 3. Real-time filter on input
// User types "cas" → Shows accounts containing "cas"
// Min 3 chars to filter, max 20 results shown
```

**HTML needed:** In voucher dialogs, replace account dropdowns with searchable inputs

#### **2B.2: Voucher Create Dialog (1.5 hours)**
**Files:** `index.html` (dialog), `app.js` (functions)

**Dialog structure:**
```html
<dialog id="business-voucher-create-dialog">
  <form id="business-voucher-create-form">
    <!-- Step 1: Voucher Type Selector -->
    <select id="voucher-type-selector">
      <option value="">-- Select Voucher Type --</option>
      <option value="payment">Payment (PV)</option>
      <option value="receipt">Receipt (RV)</option>
      <option value="contra">Contra (CV)</option>
      <option value="journal">Journal (JV)</option>
    </select>
    
    <!-- Step 2: Type-specific form (rendered conditionally) -->
    <div id="voucher-form-container">
      <!-- Payment/Receipt form OR Contra form OR Journal form -->
    </div>
  </form>
</dialog>
```

**4 Voucher Type Forms:**

**Payment Voucher (PV):**
```
- Date (entry_date)
- Amount (decimal)
- Party selector (dropdown)
- Bank/Cash account (searchable)
- Description
- Reference (check number, UPI ref, etc.)
```

**Receipt Voucher (RV):**
```
- Date
- Amount
- Party selector
- Bank/Cash account (searchable)
- Description
- Reference
```

**Contra Voucher (CV):**
```
- Date
- Amount
- From account (searchable)
- To account (searchable)
- Description
```

**Journal Voucher (JV):**
```
- Date
- Description
- Add line button (for multiple debit/credit lines)
- Line item: Account (searchable) + Debit/Credit + Amount
```

#### **2B.3: Voucher API Integration (1 hour)**
**Already partially done** (lines 4725-4780)

**Missing/To-complete:**
```javascript
async function createBusinessVoucher(data) {
  // POST /api/v1/business/vouchers
  // Payload:
  {
    voucher_type: "payment|receipt|contra|journal",
    entry_date: "2026-06-04",
    amount: "1000.00",
    debit_account_id: 2000,
    credit_account_id: 1000,
    description: "Payment to vendor",
    reference: "CHK001",
    party_id: "party-uuid" // nullable
  }
  // Response: voucher with journal_entry_id (proof of posting)
}

async function reverseBusinessVoucher(voucherId, reason) {
  // POST /api/v1/business/vouchers/{voucher_id}/reverse
  // Payload:
  {
    reversal_date: "2026-06-05",
    reason: "Correction"
  }
  // Response: reversal voucher
}
```

#### **2B.4: Voucher List & Management** (0.5 hours)
**Already exists** (see line 3851 in app.js)

**Features:**
- List with filter by voucher_type, date range
- Show: Voucher #, Type, Date, Amount, Party, Status
- Actions: View detail, Reverse
- Pagination (20 per page)

---

## 📊 Phase 2C: Dashboard Enhancements (3 hours)

### Scope: Replace mock data with live API data, add widgets

#### **2C.1: Dashboard API Integration** (1 hour)
**Current:** Dashboard uses mock/hardcoded KPI data

**Target:** Pull from `/api/v1/business/dashboard`

**Implementation:**
```javascript
async function loadBusinessDashboardStats() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/dashboard");
  
  if (result.ok) {
    // Store: lastBusinessDashboardStats
    // Re-render dashboard with live data
    dashboardPreview.innerHTML = renderBusinessDashboard();
  }
}

// Dashboard API response (expected):
{
  income: {
    current_month: 1280000,
    current_year: 12800000,
    ytd_growth: 15.5
  },
  expenses: {
    current_month: 740000,
    current_year: 7400000,
    ytd_growth: 12.3
  },
  net_position: {
    profit_loss: 5400000,
    margin: 42.2
  },
  gst_liability: {
    due: 285000,
    filing_status: "Ready"
  },
  cash_bank: 840000,
  receivables: 210000,
  payables: 96000,
  inventory_value: 450000
}
```

#### **2C.2: Collapsible Widgets** (1 hour)
**Current:** All sections always visible

**Target:** Collapsible cards (user preference)

```javascript
// Widget state persistence
const dashboardWidgetState = {
  kpi_cards: true,      // Collapsed: false
  sales_chart: true,
  ceo_insights: true,
  bottom_metrics: true,
  recent_activity: true,
  quick_actions: true
};

// Persistence: localStorage
localStorage.setItem("dashboard_widget_state", JSON.stringify(dashboardWidgetState));
```

**HTML structure:**
```html
<article class="dashboard-card collapsible" data-widget="kpi_cards">
  <div class="card-header">
    <h3>KPI Metrics</h3>
    <button class="collapse-toggle" data-widget="kpi_cards">−</button>
  </div>
  <div class="card-content" data-content="kpi_cards">
    <!-- Content -->
  </div>
</article>
```

#### **2C.3: Customizable Widget Layout** (1 hour)
**Current:** Fixed order, fixed size

**Target:** User can reorder, resize

```javascript
// Drag-and-drop support (HTML5 API)
// Widget order state
const dashboardWidgetOrder = [
  "kpi_cards",
  "sales_chart",
  "ceo_insights",
  "bottom_metrics",
  "quick_actions",
  "recent_activity"
];

// Persistence: save to localStorage
// Re-render in custom order
```

---

## 💰 Phase 2D: Sales Invoices (4 hours)

### Scope: Draft, post, cancel sales invoices with GST

#### **2D.1: Sales Invoice Dialog & Form** (2 hours)
**Fields:**
```
- Invoice date
- Invoice number (auto-generated: INV-2026-000001)
- Customer (party selector)
- Line items:
  - Item name / service description
  - Quantity
  - Rate (per unit)
  - Amount
  - HSN/SAC (optional)
  - GST rate (5%, 12%, 18%, 28%)
- Subtotal (calculated)
- GST CGST/SGST/IGST (calculated)
- Total (calculated)
- Terms (optional)
- Notes (optional)
```

#### **2D.2: Sales Invoice API** (1.5 hours)
**Backend contract (expected):**
```
POST /api/v1/business/invoices/sales
{
  invoice_type: "sales",
  invoice_number: "INV-2026-000001",
  invoice_date: "2026-06-04",
  customer_id: "party-uuid",
  line_items: [
    {
      description: "Consulting services",
      quantity: 10,
      unit_rate: 5000,
      amount: 50000,
      hsn_sac: "998361",
      gst_rate: 18,
      gst_amount: 9000
    }
  ],
  subtotal: 50000,
  gst_total: 9000,
  total: 59000
}

Response:
{
  invoice_id: "uuid",
  invoice_number: "INV-2026-000001",
  journal_entry_id: 12345,  // Posted to GL
  status: "posted",
  created_at: "..."
}
```

#### **2D.3: Sales List & Actions** (0.5 hours)
- List invoices (draft, posted)
- View/Edit (draft only)
- Post (draft → posted)
- Cancel (creates reversal)

---

## 📥 Phase 2E: Purchase Invoices (4 hours)

### Scope: Draft, post, cancel purchase bills with GST

#### **2E.1: Purchase Bill Dialog & Form** (2 hours)
**Fields:** (Similar to Sales, vendor-focused)
```
- Bill date
- Bill number (from vendor)
- Vendor (party selector)
- Line items:
  - Item name / service
  - Quantity
  - Rate
  - Amount
  - HSN/SAC
  - GST rate
  - ITC eligible (checkbox)
- Subtotal
- GST CGST/SGST/IGST
- Total
- Terms & conditions
```

#### **2E.2: Purchase Bill API** (1.5 hours)
```
POST /api/v1/business/invoices/purchase
{
  invoice_type: "purchase",
  bill_number: "VENDOR-INV-0042",
  bill_date: "2026-06-04",
  vendor_id: "party-uuid",
  line_items: [
    {
      description: "Office supplies",
      quantity: 5,
      unit_rate: 1000,
      amount: 5000,
      hsn_sac: "482300",
      gst_rate: 5,
      gst_amount: 250,
      itc_eligible: true
    }
  ],
  subtotal: 5000,
  gst_total: 250,
  total: 5250
}
```

#### **2E.3: Purchase List & Actions** (0.5 hours)
- List bills
- View/Edit draft
- Post
- Cancel

---

## 🧪 Phase 2F: Full Cycle Integration Testing (2 hours)

### Test Scenario: Complete Business Transaction Flow

**Test Case 1: Customer Payment Flow**
```
1. Create party "Acme Corp" (customer)
2. Create sales invoice for Acme (INV-2026-000001)
   - Service: Consulting, ₹50,000 + ₹9,000 GST
3. Post invoice (creates GL entry)
4. Create receipt voucher against party
   - Amount: ₹59,000
5. Check Trial Balance:
   - AR should decrease by ₹59,000
   - Cash should increase by ₹59,000
   - Revenue should show ₹50,000
   - GST payable should show ₹9,000
```

**Test Case 2: Vendor Payment Flow**
```
1. Create party "Office Mart" (vendor)
2. Create purchase bill (VENDOR-INV-0042)
   - Office supplies: ₹5,000 + ₹250 GST
3. Post bill (creates GL entry)
4. Create payment voucher against party
   - Amount: ₹5,250
5. Check Trial Balance:
   - AP should decrease by ₹5,250
   - Cash should decrease by ₹5,250
   - Expense should show ₹5,000
   - GST input (ITC) should show ₹250
```

**Test Case 3: Contra & Journal Entries**
```
1. Create bank transfer (Contra)
   - From: Savings Account → To: Current Account
   - Amount: ₹100,000
2. Create expense journal entry
   - Debit: Office Rent (₹10,000)
   - Credit: Cash (₹10,000)
3. Verify GL balanced
```

**Verification Checklist:**
- [ ] Parties list shows all created parties
- [ ] Vouchers list shows all posted vouchers
- [ ] Dashboard stats are live (not mocked)
- [ ] Dashboard widgets collapse/expand
- [ ] All GL entries balanced (debits = credits)
- [ ] Trial Balance correct
- [ ] Income Statement shows correct totals
- [ ] Receipt & Payments report correct
- [ ] Reversals create linked entries
- [ ] Audit trail captures all actions
- [ ] No console errors

---

## 🎯 Work Prioritization & Timeline

### **Workstream 1: Phase 2B - Vouchers (START IMMEDIATELY)**
1. **Hour 1:** Searchable account selector component
2. **Hour 2:** Voucher create dialog with type selector
3. **Hour 3:** Type-specific forms (payment, receipt, contra, journal)
4. **Hour 4:** API integration + list rendering + reverse functionality

**Blocker:** None (Party Master done)

### **Workstream 2: Dashboard Enhancements (START IMMEDIATELY - PARALLEL)**
1. **Hour 1:** API integration for live data
2. **Hour 2:** Collapsible widgets
3. **Hour 3:** Customizable layout

**Blocker:** None (uses existing dashboard structure)

### **Workstream 3: Sales Invoices (START AFTER VOUCHERS DONE)**
1. Build invoice dialog (2h)
2. API integration (1.5h)
3. List & actions (0.5h)

### **Workstream 4: Purchase Invoices (START AFTER SALES DONE)**
1. Build bill dialog (2h)
2. API integration (1.5h)
3. List & actions (0.5h)

### **Workstream 5: Testing (START AFTER ALL DONE)**
1. Run test scenarios (1h)
2. Fix issues found (1h)

**Total Time:** ~16-18 hours across all phases
**Parallel streams:** 2-3 simultaneous (Vouchers + Dashboard + others)

---

## 📌 Key Dependencies & Notes

**Dependency Chain:**
```
Party Master (Done)
    ↓
    ├─ Vouchers (Phase 2B) ← START NOW
    │   ├─ Account selector needed
    │   └─ Reverse functionality
    │
    ├─ Dashboard Enhancements ← START NOW (PARALLEL)
    │   └─ Live API data
    │
    ├─ Sales Invoices (Phase 2D) ← After Vouchers
    │   └─ Uses party + account selectors
    │
    └─ Purchase Invoices (Phase 2E) ← After Vouchers
        └─ Uses party + account selectors
```

**Testing requires:**
- All 4 components (Vouchers, Dashboard, Sales, Purchase) complete
- No incremental testing until full cycle ready
- Real backend available with all APIs (parties, vouchers, invoices)

---

## 🚀 Ready to Start?

**Recommendation:** Begin with **Parallel Workstreams 1 & 2:**
1. **Phase 2B:** Searchable account selector first (used by everything)
2. **Phase 2C:** Dashboard API integration (simple, quick win)

Both can proceed simultaneously with no conflicts.

**Next Step:** Confirm you want me to start Phase 2B (Voucher component) now!
