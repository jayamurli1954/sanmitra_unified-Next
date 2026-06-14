# GruhaMitra Competitive Review - Housing Society/RWA Apps

Date: 2026-06-13

Scope: competitive review for GruhaMitra housing society/RWA positioning, pricing, and roadmap planning.

Source boundary:

- The seed competitor list came from the referenced `Hsg_Society-Website.ods` spreadsheet from the previous session.
- Live web review was completed for official pages that were reachable on 2026-06-13.
- When an official source was not reachable or did not publish pricing, this document marks the item as source-limited instead of inferring exact pricing.
- ADDA package details were manually verified from a user-provided screenshot of `https://adda.io/pricing`.

## Executive Summary

The Indian housing society/RWA software market splits into three visible categories:

1. Security-led community platforms: MyGate and NoBrokerHood lead with visitor management, guard apps, resident apps, communication, complaints, payments, and broad community engagement.
2. Accounting/operations-led platforms: ApnaComplex/ANACITY and ADDA-style products compete on society billing, accounting, collections, helpdesk, facility management, and committee governance.
3. Smaller/local products: SocietyRun, SocietynMore, Neighbium, OneSociety, Society Maxx, and desktop/accounting tools appear in the spreadsheet as lower-visibility competitors, but several did not have easily verifiable current public pricing or feature pages during this review.

GruhaMitra should not try to outspend security-first platforms on gate hardware, ad networks, or super-app breadth in the first positioning pass. The practical wedge is:

- transparent pricing,
- fast society onboarding,
- maintenance billing and dues clarity,
- audit-ready accounting through MitraBooks,
- committee/resident workflows without mandatory hardware rollout,
- local support and migration from Excel/manual accounting.

## Source-Backed Competitor Notes

| Competitor | Public positioning | Source-backed feature signals | Pricing visibility | Implication for GruhaMitra |
| --- | --- | --- | --- | --- |
| NoBrokerHood | Visitor, society, and accounting management system | Visitor management, domestic staff, communication, maintenance and utility bill payments, safety/SOS, complaints, accounting, residents/apartments, vendors, amenities, admin app, guard app | No public rate card found on reachable homepage; demo/contact-led | Strong in security/community breadth. GruhaMitra should counter with transparent pricing, accounting depth, and no forced gate-hardware dependency. |
| ApnaComplex / ANACITY | Apartment management and security solution | Society billing/accounting, collection gateway, gatekeeper, helpdesk, communication, vehicle sentry, facility management, tanker monitor | Public pricing page states annual subscription with unit-based pricing and editions such as Free, Standard Security, Standard Management, Standard Accounting, and Ultimate; exact numeric rates were not visible in fetched text | Strong accounting and society operations competitor. GruhaMitra must present billing/accounting workflows clearly and avoid inconsistent pricing docs. |
| MyGate | RWA/community platform and ERP/VMS | Gate module, ERP module, accounting, compliance, operations, engagement, audit trails, payment/reconciliation, amenity bookings, helpdesk, workforce/payroll, procurement/vendor bidding, reports/export | Demo/contact-led; no public numeric pricing found in reachable pages | MyGate is broad and enterprise-like. GruhaMitra should avoid matching full scope immediately; win on simpler rollout, audit-ready accounting, and transparent flat-based pricing. |
| ADDA Gatekeeper & Society Management Suite | Accounting/operations-style housing society suite with Lite, Manage, and Books packages | Screenshot-verified features include helpdesk, announcements, resident database/change logs, resident/admin app + portal, guest-code visitor invitations, social network, events, amenity booking, staff/parking/vendor/AMC management, general ledger, income/expense tracking, bank/cash, and utility tracker | Quote-based; screenshot shows `Get Quote` for each package | ADDA confirms the market pattern: publish feature bundles, route price discovery through sales. GruhaMitra can differentiate with clearer public price estimates. |

## ADDA Screenshot-Verified Package Notes

The user-provided ADDA pricing screenshot shows three quote-based packages:

| Package | Visible features |
| --- | --- |
| Lite Package | HelpDesk, announcements, resident database with change logs, resident app + portal, admin app + portal, booking home services, visitor invitation with guest code, resident ID card with QR on app, and private social network for residents |
| Manage Package | All Lite features plus events calendar and albums, amenity booking, staff manager, parking manager, move-in/move-out, admin reports, projects and meetings, vendor master, and AMC |
| Books Package | All Manage features plus general ledger, income tracker, expense tracker, bank and cash, utility tracker, and advanced amenity booking |

ADDA does not expose numeric pricing in the screenshot. Each package uses a `Get Quote` call-to-action.

## Spreadsheet-Listed Competitors Requiring Manual Verification

These names were present in the spreadsheet seed list but did not produce reliable official-page content through the available web fetch/search path in this session:

| Competitor | Verification status | Use in planning |
| --- | --- | --- |
| OneSociety | Source-limited | Keep as a local/smaller-product benchmark; do not quote exact feature or pricing claims without manual site/app-store confirmation. |
| SocietyRun | Source-limited | Compare only after current official pricing/features are manually verified. |
| SocietynMore | Source-limited | Same as above. |
| HyperSoft Society Account Maintenance | HyperSoft corporate site reachable, but specific current society-account-maintenance details were not clearly available from the fetched page | Treat as a desktop/accounting-oriented benchmark, not a modern resident app benchmark, until verified. |
| Neighbium | Source-limited | Same as above. |
| Society Maxx | Source-limited | Same as above. |

## Competitive Feature Pattern

Features that large competitors commonly emphasize:

- Visitor and gate management.
- Guard app and staff entry/exit tracking.
- Resident app.
- Domestic staff management.
- Maintenance billing and online payments.
- Complaint/helpdesk workflow.
- Notices, announcements, polls, and discussions.
- Facility/amenity booking.
- Vendor/staff/workforce management.
- Accounting reports, collections, reconciliation, and audit support.
- Dashboards and exports for committee/auditors.

Features where GruhaMitra should be explicit:

- Society setup: blocks, flats, members, owners, tenants.
- Billing rules: fixed, per-flat, per-person, fund-based, penalties, waivers, and reversals where implemented.
- Member dues report and receipt posting.
- MitraBooks-backed trial balance, ledger, receipts and payments, income and expenditure, balance sheet.
- Complaints/service requests with status tracking.
- Meetings, attendance, minutes, resolutions, and notices.
- Tenant isolation and role-based access.
- Excel/manual-data migration path.
- Browser-first/PWA-style usage without mandatory hardware procurement.

## Pricing Findings

Observed market pattern:

- Large platforms tend to route pricing through demo/contact forms, especially when gate/security hardware, installation, staff training, or payment collection setup is involved.
- ADDA's official pricing page was user-verified by screenshot as quote-based, with Lite, Manage, and Books packages all using `Get Quote`. The page returned HTTP 403 from this environment, so screenshot-derived notes should be treated as manual verification.
- ApnaComplex publicly states annual, unit-based pricing and plan editions, but the fetched text did not expose exact numeric rates.
- Hardware, SMS/WhatsApp, payment gateway, migration, and onboarding are commonly separate or quote-dependent cost areas.

Current GruhaMitra internal gap:

- `docs/operations/PRICING_SHEET_CUSTOMER.md` says GruhaMitra uses a fixed-plus-per-flat monthly structure:
  - Starter: INR 1,000 + INR 25/flat/month
  - Growth: INR 1,500 + INR 40/flat/month
  - Professional: INR 2,500 + INR 50/flat/month
  - Minimum billing slab: 20 flats
- `docs/operations/GRUHAMITRA_CLIENT_TECHNICAL_INFORMATION.md` says a different per-flat-only structure:
  - Starter: INR 25/flat/month, minimum 25 flats
  - Growth: INR 35/flat/month
  - Professional: INR 50/flat/month
  - One-time implementation/training fee: INR 5,000

Recommendation: standardize GruhaMitra pricing docs before publishing or building payment pages. Use one source of truth for fixed fee, per-flat fee, minimum flats, annual discount, setup fee, and third-party pass-through charges.

## Recommended GruhaMitra Positioning

Primary message:

GruhaMitra helps housing societies manage members, maintenance billing, dues, complaints, meetings, notices, and accounting with transparent pricing and MitraBooks-backed financial reports.

Differentiators to emphasize:

- Accounting-first trust: trial balance, ledger, receipts and payments, income and expenditure, balance sheet, and member dues are not afterthoughts.
- Transparent commercial model: publish monthly and annual estimates by flat count.
- No mandatory security hardware: start with society operations and add integrations later.
- Small-society friendly: useful for 20 to 100 flats without enterprise sales overhead.
- Committee/auditor readiness: reports, receipts, and posting references should be easy to review.
- Migration support: import from Excel or prior manual records should be a paid, defined onboarding service.

Avoid overclaiming:

- Do not claim parity with MyGate/NoBrokerHood gate hardware, guard patrol, procurement bidding, payroll, or large-scale ad/super-app features unless implemented.
- Do not present advanced integrations, payment automation, WhatsApp/SMS automation, or resident mobile apps as current if they are only planned.

## Product Roadmap Implications

Phase 1: saleable operations core

- Society profile, towers/blocks/flats.
- Member/resident setup.
- Maintenance billing and dues.
- Receipt posting through MitraBooks accounting.
- Complaint tracking.
- Notices/meetings/minutes.
- Accounting reports and exports.
- Admin/resident role separation.

Phase 2: growth features

- Payment gateway handoff and reconciliation.
- Email/SMS/WhatsApp reminders as configured pass-through services.
- Facility/amenity booking.
- Vendor and expense workflows through accounting.
- Resident self-service improvements.

Phase 3: advanced/enterprise features

- Gate/security integrations.
- Staff/vendor attendance.
- Advanced approval workflows.
- Multi-society/property manager dashboard.
- Analytics and scheduled reports.
- API/webhooks where commercially justified.

## Pricing Direction For Decision

Recommended public structure:

| Plan | Suggested position | Pricing direction |
| --- | --- | --- |
| Starter | Small societies that need member records, maintenance billing, dues, complaints, and basic reports | Keep affordable, with a minimum flat slab and clear setup fee. |
| Growth | Societies that need full billing, receipt posting, MitraBooks accounting reports, meetings/notices, and priority support | Make this the recommended plan. |
| Professional | Larger societies or committees needing stronger controls, custom onboarding, integrations, and advanced reports | Use higher per-flat pricing plus setup/migration quote. |

Use the fixed-plus-per-flat model if SanMitra wants predictable support margin:

```text
Monthly invoice = fixed platform fee + (billable flats x per-flat fee)
```

Use the per-flat-only model if the immediate goal is simpler public pricing:

```text
Monthly invoice = max(minimum flat slab, actual flats) x per-flat fee
```

Do not publish both models at the same time.

## Source Links Reviewed

- NoBrokerHood official homepage: https://nobrokerhood.com/
- ApnaComplex official homepage: https://www.apnacomplex.com/
- ApnaComplex pricing page: https://www.apnacomplex.com/pricing
- MyGate official homepage: https://mygate.com/
- MyGate community management/RWA page: https://mygate.com/community-management/
- MyGate offerings/features page: https://mygate.com/offerings/
- HyperSoft official homepage: https://www.hypersoftindia.com/
- ADDA official pricing page: https://adda.io/pricing (blocked/403 during fetch; user provided screenshot showing Lite, Manage, and Books packages with `Get Quote` calls-to-action)
