# MitraBooks vs TallyPrime vs Zoho Books — Competitive Comparison

This is the refreshed, repo-grounded version of the earlier
`MitraBooks_Feature_Comparison` note. The strategy in the original note was sound;
what was stale was the **MitraBooks capability column** — it described MitraBooks
as mostly aspirational ("should build…", "planned…") when a large number of slices
are now implemented in the backend.

This version labels every MitraBooks line with an honest status drawn from the
engineering source of truth, [`MITRABOOKS_ERP_GAP_MATRIX.md`](./MITRABOOKS_ERP_GAP_MATRIX.md).
It is a positioning document, but the status labels are engineering truth, not
marketing.

> A note on Tally/Zoho: descriptions below are kept deliberately conservative.
> Verify against the official product pages before quoting in any external
> material — feature sets change. Primary sources:
> [TallyPrime](https://tallysolutions.com/tally-prime/),
> [Zoho Books India](https://www.zoho.com/in/books/).

## Status legend

| Label | Meaning |
| --- | --- |
| **Implemented** | Backend slice exists, routed, and covered by focused tests. Most still need browser E2E and (for tax) compliance signoff before being called production-filing-ready. |
| **Partial** | A foundation exists but the full workflow is not complete. |
| **Planned** | Designed/intended, not yet built. |
| **Deferred** | Intentionally out of near-term scope (e.g. live filing APIs, AI/OCR, mobile). |

Scope note: **InvestMitra is excluded from the unified backend.** It is not a
MitraBooks differentiator and should not be cited as one. See
[`LIVE_VS_UNIFIED_SAFETY.md`](../operations/LIVE_VS_UNIFIED_SAFETY.md).

---

## 1. Positioning

MitraBooks is best positioned not as "another Tally replacement" but as:

> **An AI-assisted cloud accounting + GST + CA-workflow platform for Indian SMEs,
> accountants, and CA offices** — Indian compliance + simple business-owner
> reporting + accountant collaboration.

Tally owns accounting depth and CA familiarity. Zoho owns modern cloud UX and
integrations. MitraBooks aims at the space between: Indian compliance with
AI-assisted review and a CA/bookkeeper workflow, sharing one accounting engine
across the SanMitra apps (GruhaMitra society accounting, MandirMitra temple/trust
accounting).

---

## 2. Feature comparison (MitraBooks status is honest, not aspirational)

| Feature area | MitraBooks (status) | TallyPrime | Zoho Books |
| --- | --- | --- | --- |
| Double-entry accounting (journal, ledger, TB, P&L, Balance Sheet, R&P) | **Implemented** | Very strong, mature | Strong cloud accounting |
| Parties / customers / vendors master | **Implemented** | Strong | Strong |
| Typed vouchers (payment/receipt/contra/journal) | **Implemented** | Core strength (voucher speed) | Available |
| Sales invoices (GST + TCS, numbering, cancellation reversal) | **Implemented** | Strong | Strong |
| Purchase bills (payable/expense/ITC/RCM/TDS) | **Implemented** | Strong | Strong |
| Credit / debit notes | **Implemented** | Strong | Available |
| GST returns prep: GSTR-1, GSTR-3B, GSTR-2B recon, CMP-08, GSTR-4 | **Implemented** (prep + JSON; compliance signoff pending) | Strong, connected filing | Strong, GSP-connected |
| GST composition scheme (Bill of Supply, ITC-as-cost) | **Implemented** | Supported | Supported |
| TDS / TCS | **Implemented** | Supported | Supported |
| Receivables / payables: open-item allocation, ageing, statements, dunning | **Implemented** | Strong | Strong |
| Bank reconciliation | **Implemented** (manual CSV import + matching) | One-click auto bank recon | Automatic bank feeds + recon |
| Fixed assets (register, SLM/WDV depreciation) | **Implemented** | Supported | Available |
| Accounting dimensions (cost centre / project) | **Implemented** | Cost centres | Available |
| Inventory | **Implemented** (opt-in, weighted-average) | Very strong (batch, godown, mfg) | Available |
| Opening balances + year-end close | **Implemented** | Strong | Available |
| E-invoicing (IRN) | **Partial** — INV-01 payload, readiness checks, manual IRN record; live IRP API **Deferred** | Single-click + bulk IRN/QR | GSP-connected IRP |
| Financial health / MIS dashboard | **Partial** — ledger-backed summary; full KPI dashboard **Planned** | Dashboards, cash-flow views | 70+ reports |
| CA / bookkeeper workflow (upload → review → query → post) | **Partial** — CA access/invite exists; client-upload review loop **Planned** | Practice-driven, not workflow-native | Accountant collaboration |
| Multi-company / multi-entity | **Partial** — tenant/app/accounting-entity context exists; multi-client CA practice model **Planned** | Strong | Available |
| Report export (PDF/print) | **Implemented**; Excel/JSON/Tally XML **Planned** | Strong | Strong |
| E-way bill | **Planned** | Strong | GSP-connected |
| Data Health Score | **Planned** | — | — |
| Document upload inbox / OCR | **Planned** (inbox); OCR/AI auto-allocation **Deferred** | Add-on/integration | Available (attachments) |
| AI-assisted GST review / bookkeeping | **Planned** (deterministic first) | Limited | Automation, some AI |
| Bank API sync | **Deferred** | Connected banking | Bank feeds |
| Payroll | **Deferred** (not near-term scope) | Supported | Zoho Payroll ecosystem |
| Mobile app | **Deferred** | Available | Strong |
| Multi-location / batch-serial inventory | **Deferred** | Strong | Available |

---

## 3. What is actually shipped today (summary)

From the gap matrix, MitraBooks has **implemented backend slices** for: the full
double-entry core; parties; typed vouchers; sales invoices; purchase bills;
credit/debit notes; the GST returns suite (GSTR-1, 3B, 2B reconciliation, CMP-08,
GSTR-4) plus composition scheme and GST settlement; TDS/TCS; AR/AP open-item
allocation, ageing, statements, and dunning; manual bank reconciliation; fixed
assets with depreciation; cost-centre/project dimensions; opt-in inventory with
weighted-average valuation; opening balances; year-end close; and the e-invoicing
foundation (INV-01 payload, readiness, manual IRN).

The honest caveats: most slices still need **browser E2E coverage**, the tax
outputs are **preparation/reporting** until compliance review, and the
**CA-workflow, MIS/Data-Health, document inbox, and AI** layers are where the
real differentiation still has to be built.

This is substantial — well beyond "planned" — but it is **not** Tally/Zoho-level
maturity yet. The gap is breadth of edge cases, compliance hardening, integration
ecosystem, and market trust, not the absence of core accounting.

---

## 4. Where MitraBooks can genuinely differentiate

These are the areas where MitraBooks is **not** trying to out-feature Tally/Zoho on
their home turf, but to own a distinct niche:

1. **AI-assisted GST review** before filing — wrong rate, wrong HSN/SAC, wrong
   place of supply, missing GSTIN, RCM applicability, ITC mismatch, duplicate
   invoice. (Planned; deterministic checks first, AI second.)
2. **CA-office workflow** — client uploads → bookkeeper review → system flags →
   CA query → client response → posting → confirmation → return-readiness.
   (Foundation in CA access; full loop Planned.)
3. **AI financial-health report** for owners — cash-flow warning, debtor/creditor
   pressure, GST liability estimate, profitability snapshot, PPT/PDF output.
   (Ledger-backed summary exists; full version Planned.)
4. **Two modes** — Business-Owner mode (simple) and Accountant mode (ledgers,
   journals, GST, audit trail).
5. **SanMitra ecosystem** — one shared accounting engine across MitraBooks
   business, MandirMitra temple/trust, and GruhaMitra society accounting.
   (InvestMitra is **not** part of this — out of unified scope.)

---

## 5. Where Tally and Zoho remain stronger

- **TallyPrime**: traditional accounting depth, CA familiarity, inventory depth
  (batch/godown/manufacturing), offline-first usage, large installed base, mature
  GST/e-way-bill, customization ecosystem.
- **Zoho Books**: true-cloud UX, mobile, online invoicing, payment-gateway and
  bank-feed integrations, workflow automation, Zoho ecosystem, client portal.

MitraBooks should not try to beat these head-on before its own core is
E2E-hardened and compliance-reviewed.

---

## 6. Verdict by use case

| Use case | Best fit today |
| --- | --- |
| Traditional accountant / CA office (deep books) | TallyPrime |
| Trader / wholesaler / manufacturer (deep inventory) | TallyPrime |
| Startup / service business / online-first SMB | Zoho Books |
| Modern cloud accounting + automation | Zoho Books |
| Indian SME wanting AI-assisted GST review + CA workflow | **MitraBooks opportunity** |
| One accounting engine across temple / society / business | **MitraBooks** |
| Financial-health dashboard + AI owner reports | **MitraBooks differentiation (in progress)** |

**Recommendation:** keep building MitraBooks as a cloud-native, AI-assisted
GST/accounting workflow platform for Indian SMEs and CA offices. The accounting
and GST core is now real; the next differentiation is the CA workflow, MIS/data
health, document inbox, and AI review — in that order, deterministic before AI.
