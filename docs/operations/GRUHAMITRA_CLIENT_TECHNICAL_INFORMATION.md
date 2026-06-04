# GruhaMitra Technical Information for Prospective Clients

Audience: prospective housing society/RWA clients, committee members, society admins, and technical evaluators.

This note explains GruhaMitra at a practical technical level without exposing private infrastructure values, credentials, secrets, database URLs, or internal deployment tokens.

## Product Summary

GruhaMitra is a web-based housing society operations application for RWAs, apartment associations, and gated communities.

It supports:

- Society dashboard
- Flats, blocks, and unit setup
- Owner, tenant, and resident/member onboarding
- Maintenance bill generation
- Maintenance receipt posting
- Member dues tracking
- Complaints and service requests
- Meetings, attendance, minutes, resolutions, and meeting notices
- Message board / notice-room communication
- Society accounting through MitraBooks
- Trial balance, ledger, receipts and payments, income and expenditure, balance sheet, and member dues reports
- PDF/print/export support for accounting and society records where enabled

## Access URLs

Public product page:

```text
https://www.gruhamitra.sanmitratech.in/gruhamitra/
```

Login page:

```text
https://www.gruhamitra.sanmitratech.in/gruhamitra/login
```

Prospective users should be given demo credentials only. Platform-owner or production administrator credentials must not be shared.

## Frontend Information

GruhaMitra is delivered as a browser-based responsive web application.

Current frontend characteristics:

- Built with React.
- Served through Vercel for fast global web delivery.
- Works in modern browsers such as Chrome, Edge, Firefox, and Safari.
- Supports desktop and mobile layouts.
- Includes public landing page, login, society registration, resident registration, admin dashboard, member screens, maintenance billing, accounting, reports, meetings, messages, complaints, and settings.
- Supports PWA-style install experience where the browser/device permits it.
- Uses HTTPS in production.
- Communicates with the backend through protected API routes.

No software installation is required for ordinary users. Users need only a supported browser and internet access.

## Backend Information

GruhaMitra uses the SanMitra unified backend platform.

Current backend characteristics:

- FastAPI-based Python backend.
- Deployed on Render.
- Versioned APIs under `/api/v1`.
- JWT-based authentication for protected APIs.
- Role-based access control for admin/resident workflows.
- App-key and module access checks for GruhaMitra context.
- Tenant-scoped data access so each society has its own isolated workspace.
- Backend CORS is restricted to approved SanMitra frontend domains.
- Health, deployment, and CI checks are managed separately from customer-facing screens.

The backend is shared platform infrastructure, but each society's application context and data are tenant-scoped.

## Data Storage Model

GruhaMitra uses a split data ownership model:

| Data Type | Store | Purpose |
| --- | --- | --- |
| Society, users, members, flats, settings, complaints, meetings, notices, messages | MongoDB | Flexible operational and housing society records |
| Accounts, vouchers, journals, journal lines, ledgers, trial balance, financial reports | PostgreSQL | Financial accounting source of truth |
| Cache/session/job support, where enabled | Redis or equivalent cache | Performance and background coordination |

Financial data is not maintained as a duplicate housing ledger. Accounting-impacting workflows post through MitraBooks accounting.

## Accounting Model

GruhaMitra uses MitraBooks as the accounting engine.

Important accounting rules:

- Maintenance bills post to accounting when the admin chooses to post them.
- Maintenance receipts reduce member dues through proper accounting entries.
- Payments, receipts, journals, and reversals use double-entry accounting.
- Debits and credits must balance before posting.
- Posted accounting entries are treated as immutable.
- Corrections should be done through reversal or adjustment entries, not by directly editing posted ledger rows.
- Reports such as trial balance and ledger are derived from posted accounting records.

Typical maintenance posting pattern:

```text
Maintenance billing:
Dr Member Dues Receivable
Cr Monthly Maintenance Charges

Maintenance receipt:
Dr Bank/Cash
Cr Member Dues Receivable
```

This keeps society dues, collections, and accounting reports aligned.

## Security and Tenant Isolation

GruhaMitra is designed around tenant isolation.

Security controls include:

- Society-specific tenant context for protected requests.
- Authentication required for admin and resident workflows.
- Role-based access for society admin, resident/member, and platform owner workflows.
- App-key validation for GruhaMitra routes.
- Tenant-scoped MongoDB operational records.
- Tenant-scoped PostgreSQL accounting records.
- HTTPS in production.
- Passwords stored as hashes, not plain text.
- Secrets and database credentials kept in hosting environment variables, not frontend code.
- Platform-owner override is restricted and should be used only for support or administration.

Customer data should not be entered into a public demo tenant. Demo tenants are for evaluation only.

## Functional Areas

### Society Setup

- Society profile
- Blocks/towers/flats
- Member configuration
- Billing rules
- Late fees and penalties
- Accounting settings
- Payment gateway settings where applicable
- Notification settings where applicable

### Members and Residents

- Admin-led member onboarding
- Resident join request flow
- Owner/tenant member classification
- Flat association
- Occupant count for billing logic
- Member status and visibility controls

### Maintenance Billing

- Monthly bill generation
- Fixed expenses allocation
- Water charges per-person logic where configured
- Per-flat funds such as sinking fund, repair fund, association fund, or other configured billing rules
- Existing bill view, breakdown, reversal, and posting
- Dues tracking after receipt posting

### Accounting

- Chart of accounts
- Receipt voucher
- Payment voucher
- Journal voucher
- Transfer voucher
- Ledger
- Trial balance
- Receipts and payments
- Income and expenditure
- Balance sheet
- Voucher PDFs/prints where enabled

### Communication and Governance

- Meetings
- Agenda items
- Attendance
- Minutes
- Resolutions
- Meeting notices visible to eligible members
- Message board / notice-room style communication

### Complaints

- Complaint creation
- Status tracking
- Admin/member visibility based on role and society context

## Reporting and Exports

Current report areas include:

- Society summary
- Trial balance
- General ledger
- Receipts and payments
- Income and expenditure
- Balance sheet
- Member dues report
- Asset register where enabled
- Voucher print/PDF support
- Excel/PDF/print view support where enabled

Reports should show the respective society's name and contact details where configured.

## Pricing Tiers

Indicative GruhaMitra pricing:

| Plan | Suitable For | Monthly Rate | Yearly Rate |
| --- | --- | --- | --- |
| Starter | 25 to 50 flats | INR 25 per flat per month, minimum 25 flats | INR 250 per flat per year |
| Growth | 51 to 100 flats | INR 35 per flat per month | INR 350 per flat per year |
| Professional | 101 flats and above | INR 50 per flat per month | INR 500 per flat per year |

One-time implementation, migration, and training fee:

```text
INR 5,000
```

Final commercial terms may depend on implementation scope, data migration effort, training needs, payment gateway setup, notification setup, and support agreement.

## Implementation Process

Typical onboarding sequence:

1. Confirm society/RWA details.
2. Create tenant workspace.
3. Configure blocks, flats, and society profile.
4. Configure users, admin access, and member onboarding process.
5. Configure chart of accounts and accounting settings.
6. Configure billing rules such as maintenance, sinking fund, repair fund, association fund, and penalties.
7. Import or enter opening members/flats/dues where applicable.
8. Run test billing and receipt cycle.
9. Train admin/committee users.
10. Go live for residents and members.

## Operational Responsibilities

SanMitra Tech typically handles:

- Application hosting and platform updates
- Technical support for GruhaMitra workflows
- Bug fixes and stability improvements
- Deployment and backend maintenance
- Initial configuration and training based on commercial scope

Society/RWA admin typically handles:

- Correct member and flat data entry
- Billing rule confirmation
- Receipt/payment entry accuracy
- Meeting and notice content
- Complaint resolution workflow
- Payment gateway account ownership if configured
- Data verification before live billing

## Current Configuration Notes

The following areas may be configuration-dependent:

- Payment gateway integration
- Automated SMS/WhatsApp/email notifications
- Custom invoice/receipt formats
- Migration from old Excel/accounting systems
- Advanced approval workflows
- Custom role permissions

These should be confirmed during implementation.

## Contact

SanMitra Tech contact details:

```text
WhatsApp: 7904942915
Email: contact@sanmitratech.in
Website: www.sanmitratech.in
GruhaMitra: www.gruhamitra.sanmitratech.in
```

## Client Assurance Notes

- GruhaMitra is designed to keep each society's data separate.
- Accounting reports are backed by MitraBooks accounting records.
- The product is browser-based and does not require desktop installation.
- Demo credentials can be provided for evaluation.
- Real society data should be entered only after tenant setup and onboarding approval.
- Production credentials, API keys, database URLs, and hosting secrets are never shared with clients or stored in frontend code.
