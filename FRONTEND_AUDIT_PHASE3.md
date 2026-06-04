# Frontend Audit: MitraBooks ERP Phase 3 Readiness

**Date:** 2026-05-30  
**Status:** Assessment complete — Phase 3 frontend wiring ready to begin

---

## Current Frontend Structure

### Shell Files (3 files total)
1. **index.html** — Main app shell
   - Sidebar navigation with module switch buttons (MitraBooks, Platform Owner, MandirMitra, GruhaMitra)
   - Access panel for login (email/password + advanced connection with token)
   - Dialogs for entitlements, payment verification, receipts, and mandir-specific modals
   - Technical context cards
   - **Status:** Minimal, ready to extend with business-specific dialogs

2. **app.js** — Application logic (4,458 lines)
   - Experience configs for all products (mitrabooks, platform, mandir, gruha)
   - Module definitions and navigation items
   - Render functions for dashboards, reports, and list views
   - Event handlers for workspace navigation, list filtering, and API calls
   - **Status:** Extensive MandirMitra implementation; business module skeleton only

3. **manifest.webmanifest** — PWA config
   - **Status:** Ready as-is

---

## Product Implementation Status

| Product | Dashboard | List Views | CRUD Forms | Reports | Status |
|---------|-----------|-----------|-----------|---------|--------|
| **MandirMitra** (temple) | ✅ Full | ✅ Donations, sevas, payments, receipts | ✅ Yes | ✅ Panchang, financial, operational | **Complete** |
| **GruhaMitra** (housing) | ✅ Full | ✅ Flats, members, maintenance, complaints | ⚠️ Partial | ✅ Maintenance, accounting | **Functional** |
| **MitraBooks Business** | ⚠️ Skeleton | ❌ None | ❌ None | ✅ Accounting (shared) | **Needs Phase 3** |
| **Platform Owner** | ✅ Full | ✅ Tenants, approvals | ⚠️ Limited | ✅ Summary view | **Functional** |

---

## What Exists for Business Module

### Backend Integration Points
- **Experience config** — `mitrabooks` mode defined (line 64-92)
- **Module list** — 5 modules enumerated:
  ```javascript
  { module_key: "business", display_name: "Dashboard", frontend_path: "/business" }
  { module_key: "accounting", display_name: "Accounts" }
  { module_key: "gst", display_name: "GST Compliance" }
  { module_key: "inventory", display_name: "Inventory" }
  { module_key: "audit", display_name: "Audit Log" }
  ```
- **Org type mapping** — BUSINESS type correctly mapped to modules (line 59)
- **Dashboard skeleton** — `renderBusinessDashboard()` exists but minimal (line 2801-2822)
  - Shows quick actions and accounting drill-down only
  - No party or voucher forms
  - No recent vouchers list
- **Accounting reports** — Trial balance, income/expenditure, receipts & payments, balance sheet all ready
- **Accounting drill-down** — Month → week → day → voucher navigation ready

### API Calls Already Wired
```javascript
GET /api/v1/platform-owner/dashboard          // Platform owner summary
GET /api/v1/accounting/reports/vouchers/{id}  // Voucher details
GET /api/v1/accounting/...                    // All accounting reports (shared)
```

---

## What's Missing for Phase 3

### 1. **Party Master UI** (Customers & Vendors)
**Backend:** ✅ Complete (Phase 2)  
**Frontend:** ❌ Not wired

**Needs:**
- List view with search/filter/pagination
- Create form (name, GSTIN, opening balance, party type)
- Edit form (update name, GSTIN, opening balance)
- Deactivation action (soft delete)
- Quick lookup for voucher entry

**API endpoints to call:**
```
GET    /api/v1/business/parties              // List customers + vendors
POST   /api/v1/business/parties              // Create party
GET    /api/v1/business/parties/{party_id}   // Get party detail
PATCH  /api/v1/business/parties/{party_id}   // Update party
PATCH  /api/v1/business/parties/{party_id}/deactivate  // Deactivate
```

**Example UI structure (from MandirMitra pattern):**
```
Workspace: business → parties (or grouped under accounting)
  ├─ List view (with search, date range, party type filter)
  ├─ Create form (inline or modal)
  ├─ Edit modal (on row click)
  └─ Bulk actions (deactivate, export)
```

---

### 2. **Typed Vouchers UI** (Payment, Receipt, Contra, Journal)
**Backend:** ✅ Complete (Phase 2)  
**Frontend:** ❌ Not wired

**Needs:**
- List view (vouchers by type, date range, status)
- Typed entry forms:
  - **Payment Voucher** — from account → multiple to accounts
  - **Receipt Voucher** — to account ← multiple from accounts
  - **Contra Voucher** — bank/cash ↔ bank/cash
  - **Journal Voucher** — multi-line double-entry
- Reversal action (via reversal service)
- Draft/posted status tracking
- Quick number lookups by FY

**API endpoints to call:**
```
GET    /api/v1/business/vouchers              // List (filterable by type, status, date)
POST   /api/v1/business/vouchers              // Create typed voucher
GET    /api/v1/business/vouchers/{voucher_id} // Get voucher detail
POST   /api/v1/accounting/reversals           // Reverse a voucher

GET    /api/v1/accounting/accounts            // For account dropdowns
GET    /api/v1/business/parties               // For party dropdowns
```

**Example UI structure (Tally-speed-entry style):**
```
Workspace: business → vouchers
  ├─ Type selector (Payment / Receipt / Contra / Journal)
  ├─ Quick entry form
  │   ├─ Voucher type, date, reference, narration
  │   ├─ Dynamic line grid (account / amount / description)
  │   └─ Debit/credit balance check
  ├─ Recent vouchers (list view, drillable)
  └─ Batch actions (reverse, adjust, export)
```

---

### 3. **Audit Trail UI**
**Backend:** ✅ Complete (Phase 2)  
**Frontend:** ❌ Not wired

**Needs:**
- Filterable event log (by entity type, action, date range, actor)
- Event detail modal (payload view, timestamp, user)
- Export to CSV

**API endpoint:**
```
GET /api/v1/audit/events  // List audit events (filterable)
```

**Example UI structure:**
```
Workspace: audit (or admin/audit)
  ├─ Filters: entity type, action (create/update/delete/post), date range
  ├─ Event log table (entity, action, actor, timestamp)
  └─ Detail modal (full payload, JSON view)
```

---

### 4. **Platform Owner Dashboard**
**Backend:** ✅ Complete (Phase 2)  
**Frontend:** ✅ Partially wired

**Current state:**
- Dashboard exists and calls backend
- Shows pending approvals, active/inactive tenants, subscription plans
- Approvals table with approve/reject buttons

**Needs:**
- Verify all fields render correctly
- Wire approve/reject actions to backend (PATCH /tenants/{id}/entitlements)
- Test with actual data

---

### 5. **BUSINESS Tenant Onboarding Flow**
**Backend:** ✅ Complete (COA auto-seeded on org-type change)  
**Frontend:** ❌ Not wired

**Needs:**
- Registration form with org_type = "BUSINESS"
- Confirmation that COA was seeded (show account list summary)
- Redirect to business dashboard
- Test: email → register → dashboard auto-loads 54 accounts

---

## Navigation Wiring Summary

### Current Routes Mapped
```
MandirMitra:
  /temple/dashboard                 ← existing
  /temple/donations, /sevas, /payments, etc.

GruhaMitra:
  /housing/dashboard                ← existing
  /housing/maintenance, /members, /complaints, etc.

Platform Owner:
  /platform-owner/dashboard         ← existing
```

### Routes to Add (Phase 3)
```
MitraBooks Business:
  /business                         ← dashboard (stub exists)
  /business/parties                 ← party master (new)
  /business/vouchers                ← typed voucher entry (new)
  /business/audit                   ← audit trail (new)

Shared (accessible from business):
  /accounting/reports               ← TB, P&L, BS, R&P (exists)
```

---

## File Changes Needed

### 1. **index.html**
- Add dialogs for party create/edit
- Add dialogs for voucher entry (4 types)
- Add audit event detail dialog
- Add entitlements dialog for super_admin (already exists)

### 2. **app.js** — Major additions needed

| Feature | Lines | Complexity | Status |
|---------|-------|-----------|--------|
| Party CRUD render functions | ~300 | Medium | Not started |
| Voucher entry forms (4 types) | ~800 | High | Not started |
| Audit log rendering | ~150 | Low | Not started |
| API call handlers (parties/vouchers) | ~400 | Medium | Not started |
| Event delegation for actions | ~200 | Medium | Not started |
| Workspace navigation for business | ~100 | Low | Not started |
| **Total additions** | **~1,950 lines** | | |

---

## API Header Requirements

### Tenant Context
- **Header:** `X-Tenant-ID` — sent by backend (JWT payload), set in session context
- **Header:** `X-App-Key` — "mitrabooks" for all business workflows
- **Header:** `X-Accounting-Entity-ID` — optional, defaults to "primary" (for multi-book support)

### Implementation note
The frontend already sends tokens; the backend extracts tenant from token. **No changes needed** to auth flow.

---

## Report Integration

### What Already Works
- Trial Balance
- Income & Expenditure
- Receipts & Payments
- Balance Sheet
- Accounting Drill-down (month → week → day → voucher)

All shared with other products (MandirMitra, GruhaMitra). **No changes needed.**

---

## Testing Checkpoints for Phase 3

### End-to-End (E2E) Verification
1. **Onboarding**
   - [ ] Create BUSINESS tenant → COA seeded (54 accounts visible)
   - [ ] Dashboard loads with "MitraBooks Business" title
   - [ ] Navigation shows party, voucher, audit, accounting modules

2. **Party Master**
   - [ ] Create customer (name, GSTIN, opening balance)
   - [ ] List shows all parties, searchable
   - [ ] Edit party (change name, GSTIN)
   - [ ] Deactivate customer (soft delete, no GL impact)

3. **Typed Vouchers**
   - [ ] Create payment voucher (bank debit, expense credit)
   - [ ] Create receipt voucher (bank credit, income debit)
   - [ ] Create contra voucher (bank ↔ cash)
   - [ ] Create journal voucher (multi-line)
   - [ ] List shows recent vouchers
   - [ ] Reverse a voucher (GL entries reversed, original stays for audit)

4. **Accounting Reports**
   - [ ] Trial Balance (all 54 accounts listed, debits = credits)
   - [ ] P&L (income vs expense from posted vouchers)
   - [ ] Balance Sheet (assets = liabilities + equity)
   - [ ] Receipts & Payments (bank/cash movements)

5. **Audit Trail**
   - [ ] List events filtered by entity (party, voucher)
   - [ ] Show action type (create, update, post, reverse)
   - [ ] Timestamp and actor visible
   - [ ] Detail modal shows full payload

6. **Platform Owner**
   - [ ] See BUSINESS tenant in recent tenants list
   - [ ] Approve tenant (enable modules)
   - [ ] Update subscription plan
   - [ ] View pending approvals (if any)

---

## Code Patterns to Follow

### Pattern 1: Workspace Navigation (from MandirMitra)
```javascript
const activeMandirWorkspace = "overview";  // Replace with: const activeBusinessWorkspace = "parties";

// Event delegation:
link.dataset.businessWorkspace = "parties";
link.dataset.businessWorkspace = "vouchers";

// Sync active state:
function syncBusinessNavActiveState() {
  nav.querySelectorAll("a").forEach((link) => {
    const workspace = link.dataset.businessWorkspace || "";
    const isActive = currentExperience === "mitrabooks" && workspace === activeBusinessWorkspace;
    link.classList.toggle("active", isActive);
  });
}
```

### Pattern 2: List View with Filters (from MandirMitra donations)
```javascript
const businessListState = {
  parties: {
    offset: 0,
    q: "",
    party_type: "",  // customer/vendor/both
    from_date: "",
    to_date: "",
  },
  vouchers: {
    offset: 0,
    q: "",
    voucher_type: "",  // payment/receipt/contra/journal
    status: "",  // draft/posted
    from_date: "",
    to_date: "",
  },
};
```

### Pattern 3: API Calls (from existing patterns)
```javascript
const result = await apiRequest("mitrabooks", "/api/v1/business/parties", {
  method: "POST",
  body: JSON.stringify({ name, gstin, opening_balance_paise, party_type }),
});

if (result.ok) {
  // Update UI, show success message
  await runChecks();  // Refresh list
} else {
  setLoginStatus("danger", "Create party failed", result.payload?.detail);
}
```

---

## Decision Points for Phase 3

1. **Voucher Entry UX**
   - Option A: Inline grid (like spreadsheet) — faster entry, less clicking
   - Option B: Form with add-line modal — safer, fewer mistakes
   - **Recommendation:** Start with Option B (safer), add inline grid later if time permits

2. **Accounting Entity Dimension**
   - Option A: Single book ("primary") for now, hide header
   - Option B: Show book selector in topbar, allow multi-book switching
   - **Recommendation:** Option A for Phase 3 (simpler), plumb infrastructure for Option B

3. **Report Integration**
   - Reuse shared accounting reports or build business-specific versions?
   - **Recommendation:** Reuse (already working, tested)

4. **Mobile/Responsive**
   - App shell already responsive; voucher forms may be tight on mobile
   - **Recommendation:** Desktop-first for Phase 3, mobile optimize in Phase 4

---

## Deployment Notes

### Before Merge
- [ ] All 4 experience modes (mitrabooks, mandir, gruha, platform) render without errors
- [ ] No console errors on tab switch
- [ ] Party/voucher forms validate inputs
- [ ] API calls include X-App-Key: "mitrabooks"
- [ ] Audit events show with correct timestamps

### CI/CD
- No CSS or shared infrastructure changes expected
- `backend-ci` already passing (Phase 2)
- `codeql-analysis` will scan new JS for security issues
- **No new dependencies** (use existing fetch/JSON patterns)

---

## Work Breakdown for Phase 3 Implementation

| Task | Estimate | Priority | Dependency |
|------|----------|----------|------------|
| Party CRUD UI + API wiring | 4–5 hours | P0 | Backend ready |
| Voucher entry forms (4 types) | 6–8 hours | P0 | Backend ready |
| Workspace nav + routing | 1–2 hours | P0 | Party/voucher UI |
| Audit trail UI | 2–3 hours | P1 | Backend ready |
| Business dashboard build-out | 1–2 hours | P1 | Party/voucher UI |
| E2E testing (manual) | 2–3 hours | P1 | All above |
| **Total** | **16–23 hours** | | |

---

## Next Steps

1. **Review this audit** with the team
2. **Decide on patterns** (voucher entry UX, accounting entity handling)
3. **Start Phase 3 implementation** — begin with party CRUD (least complex, foundation for vouchers)
4. **Merge frontend** once all E2E checkpoints pass
5. **Deploy to Render staging** for live testing with real data

---

## Appendix: Current Module Navigation (MitraBooks Experience)

```javascript
mitrabooks: {
  modules: [
    { module_key: "business", display_name: "Dashboard", frontend_path: "/business", enabled: true },
    { module_key: "accounting", display_name: "Accounts", frontend_path: "/accounting", enabled: true },
    { module_key: "gst", display_name: "GST Compliance", frontend_path: "/gst", enabled: true },
    { module_key: "inventory", display_name: "Inventory", frontend_path: "/inventory", enabled: true },
    { module_key: "audit", display_name: "Audit Log", frontend_path: "/audit", enabled: true },
  ],
}
```

All enabled; GST, inventory, and audit are currently stubs (MandirMitra-style reports/logs will handle audit).

