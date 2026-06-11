# MitraBooks Onboarding, Landing, and Pricing Plan

## Current State

MitraBooks has implemented core business accounting slices: parties, vouchers, sales invoices, purchase bills, credit/debit notes, GST preparation reports, TDS/TCS, payment allocation, statements, bank reconciliation, fixed assets, dimensions, inventory, opening balances, year-end close, audit trail, and financial health reporting.

The current generic onboarding service is still platform-level and carries older MandirMitra-shaped fields. MitraBooks business onboarding and CA/bookkeeper practice onboarding need their own request model before production enablement.

## Target State

MitraBooks should onboard three account types:

1. **Single Business**
   - One legal entity or proprietorship.
   - One accounting tenant.
   - Optional branches and GST registrations.
   - Owner/admin creates users and permissions.

2. **Single User, Multi-Company**
   - One professional or business owner handling multiple companies alone.
   - One practice tenant plus multiple client/company accounting entities.
   - User can switch companies from one login.

3. **CA / Bookkeeper Practice**
   - One practice tenant.
   - Multiple client companies.
   - Multiple staff users.
   - Client assignment, access control, compliance tracking, and review queues.

## Onboarding Flow

### Step 1: Select Account Type

Options:

- Business owner / founder
- Accountant inside a business
- CA practice
- Bookkeeper / outsourced accounting firm
- Consultant managing multiple companies

### Step 2: Select Plan

Plans:

- Free
- Basic
- Starter
- Growth

Practice-specific modes:

- Single User - Multi Company
- Multi User - Multi Company

### Step 3: Capture Primary Profile

Fields:

- Organization or practice name
- Legal name
- Trade name
- PAN
- GSTIN
- TAN where applicable
- Address
- Contact person
- Admin email and phone
- Financial year start
- Base currency
- Time zone

### Step 4: Business Classification

Fields:

- Business type: trading, services, professional, manufacturing, mixed
- GST registration type: unregistered, regular, composition
- Inventory required: yes/no
- TDS/TCS required: yes/no
- Branches required: yes/no
- Opening balance import required: yes/no
- Existing data source: manual, Excel, Tally, other accounting software

### Step 5: Practice Details for CA / Bookkeepers

Additional fields:

- Practice registration name
- ICAI/member reference where applicable
- Number of clients
- Number of staff
- Client access model: view-only, data entry, full access
- Work assignment required: yes/no
- Compliance tracking required: GST, TDS, income tax, audit due dates
- Client onboarding import method: one-by-one, CSV, assisted migration

### Step 6: Approval and Provisioning

Target provisioning:

- Create tenant with `app_key = mitrabooks`.
- Preserve `organization_type = BUSINESS` for direct business tenants.
- Use a distinct practice profile for CA/bookkeeper mode instead of misusing temple or housing fields.
- Enable modules according to selected plan and classification.
- Create accounting entity or practice root.
- Create default chart of accounts.
- Create default invoice settings.
- Keep all financial balances at zero until opening balances are posted through the opening-balance journal flow.

## Pricing Structure

All prices are recommended launch prices in INR. Taxes extra where applicable.

| Plan | Target user | Monthly | Yearly | Companies | Users | OCR / AI documents | Included scope |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Free | Trial, very small business | Rs. 0 | Rs. 0 | 1 | 1 | 0/month | Basic parties, vouchers, invoices, and reports with manual entry |
| Basic | Single-user business | Rs. 499 | Rs. 4,999 | 1 | 1 | 25/month | GST prep, TDS/TCS tracking, basic OCR queue, email support |
| Starter | Growing business or single-user multi-company | Rs. 999 | Rs. 9,999 | 3 | 3 | 100/month | Bank reconciliation, ageing, statements, inventory basics, AI categorization suggestions |
| Growth | CA/bookkeeper practice | Rs. 2,999 | Rs. 29,999 | 25 | 10 | 500/month | Multi-client workspace, staff assignment, compliance tracking, AI MIS, OCR, reconciliation assistance |

Recommended add-ons:

- One-time implementation, migration, and training fee: get quote.
- Additional company: Rs. 99/month or Rs. 999/year.
- Additional staff user: Rs. 149/month or Rs. 1,499/year.
- Additional OCR pack: Rs. 199 per 100 documents.
- Live GST/bank API integrations: enabled only after provider review and tenant authorization.

## Feature Allocation

### Free

- One company.
- One user.
- Manual entries only.
- Basic parties, vouchers, sales invoices, purchase bills, and reports.
- No OCR, no AI posting, no CA practice dashboard.

### Basic

- One company.
- One user.
- GST preparation reports.
- TDS/TCS tracking.
- Basic document upload and OCR extraction queue.
- Email support.

### Starter

- Up to three companies or up to three internal users.
- Bank reconciliation.
- Receivable/payable ageing.
- Statements.
- Inventory basics.
- AI categorization suggestions, always requiring human review.

### Growth

- CA/bookkeeper multi-company workspace.
- Up to 25 companies and 10 users.
- Client assignment.
- Client access control.
- Compliance tracking.
- AI MIS, OCR extraction, reconciliation assistance, and document queue.
- Human approval before any ledger posting.

## Landing Page Positioning

The MitraBooks landing page should explain:

- MitraBooks is an accounting-first SaaS for Indian SMEs, CAs, and bookkeepers.
- MitraBooks is positioned as cloud ERP and double-entry accounting software for Indian business workflows.
- It supports proper double-entry books, GST/TDS workflows, invoices, purchases, bank reconciliation, reports, audit trail, and practice workflows.
- AI features are assistant features: OCR, categorization, MIS, reconciliation suggestions, and document review.
- AI must not auto-post to the ledger without human approval.
- It is not a live GST filing portal, bank execution system, payroll engine, or replacement for CA judgment unless those integrations are explicitly enabled later.
- It includes public About, Contact, Privacy Policy, and Terms of Use pages before routing users to the existing login page.

## Non-Goals

- Do not merge LegalMitra or InvestMitra into MitraBooks.
- Do not expose broker/trading or legal research workflows inside MitraBooks.
- Do not auto-file statutory returns without reviewed integrations.
- Do not allow AI/OCR to directly mutate posted accounting records.
- Do not treat settings or onboarding form values as financial balances.

## Implementation Sequence

1. Static landing page and pricing content.
2. MitraBooks onboarding request schema separate from MandirMitra fields.
3. Practice profile and client-company data model.
4. Module entitlement mapping for Free, Basic, Starter, Growth.
5. Frontend onboarding wizard.
6. Platform-owner approval and provisioning.
7. Browser E2E for business onboarding and CA practice onboarding.
