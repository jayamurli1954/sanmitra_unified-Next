---
name: gruhamitra-housing
description: GruhaMitra housing society workflow for flats, towers, residents, owners, tenants, maintenance billing, collections, complaints, parking, vendors, notices, society accounting, and GruhaMitra integration with MitraBooks. Use when changing GruhaMitra backend, frontend, compatibility APIs, housing society data, maintenance collections, or society accounting.
---

# GruhaMitra Housing

## Domain Overview

GruhaMitra covers housing society workflows:

- flats, towers, blocks, units, and ownership/occupancy lifecycle
- residents, owners, tenants, families, and vehicles
- maintenance billing, penalties, discounts, and collection
- complaints/service requests
- parking allocation and vendor payments
- notices, meetings, society documents, and audit trail
- society accounting through MitraBooks

Use `organization_type = HOUSING` and app key `gruhamitra` where compatibility requires it.

## Tenant And Access Rules

- Society/tenant isolation is mandatory.
- Every flat, resident, complaint, notice, bill, payment, parking record, and vendor record must be tenant-scoped.
- Resident access must be limited to their own unit/family/context unless role permits broader society access.
- Committee/admin actions must be role-gated and audited.
- Do not trust flat id, resident id, or tenant id from request bodies without server-side validation.

## Maintenance Billing

- Maintenance charges must be reproducible from configured rules.
- Billing rules should support area-based, flat-rate, tower/block-specific, and ad-hoc charges where tenant configuration allows.
- Discounts, penalties, waivers, and reversals require actor and reason metadata.
- Collections must post through MitraBooks accounting.
- Accounting failure must not mark a collection as completed.
- Posted collections must not be edited in place; use reversal/adjustment flows.

## Data Expectations

Housing records should usually include:

- `tenant_id`
- organization/society context
- unit/tower/block reference where applicable
- resident/owner/tenant references where applicable
- status and lifecycle dates
- created/updated actor metadata
- audit metadata for financial or notice actions

Maintenance transactions should usually include:

- tenant and unit context
- bill/collection id
- charge period
- amount, currency, and line breakdown
- due date and payment status
- accounting reference when posted
- reversal/cancellation reference when corrected

## Complaints, Notices, And Vendors

- Complaints/service requests need status history and actor metadata.
- Notices and financial actions need audit trail.
- Vendor payments and society expenses must post through accounting.
- Do not embed housing-specific rules inside the shared accounting engine.

## Completion Checklist

- Confirm every housing record is tenant-scoped.
- Confirm resident/user access cannot cross unit or society boundaries.
- Confirm maintenance collections post through MitraBooks accounting.
- Confirm billing and collection failure modes do not leave inconsistent state.
- Confirm complaints/notices/vendor actions have audit trail where needed.
- Confirm organization type remains `HOUSING` and app key compatibility remains `gruhamitra`.
- Add tests for tenant isolation, resident access, billing calculation, collection posting, and accounting failure rollback where practical.
