# MitraBooks Bank Feed Policy

## Current State

MitraBooks supports manual bank statement CSV import, reconciliation suggestions,
explicit match/unmatch, and voucher posting from imported bank-only statement
lines. The local/demo flow is guarded by tenant, app-key, and accounting-entity
scope.

## Target State

Live bank feeds may be added later through a provider connector, but only as an
import source for statement lines. Feed sync must not post ledger entries,
auto-match transactions, or store banking credentials in the frontend.

## Policy

- Bank-feed connectors must be provider-gated per tenant and disabled by default.
- Consent must identify the tenant, bank account, provider, scopes, and expiry.
- Provider tokens must be stored only in the approved backend secret store.
- Frontend code must never receive bank credentials, refresh tokens, or raw
  provider secrets.
- Imported feed rows must pass through the same statement-line model as CSV
  imports, including dedupe fingerprints and tenant/app/entity scoping.
- Matching remains metadata-only and must require explicit user confirmation.
- Bank-only feed rows must post only through the typed voucher workflow and
  normal approval/reversal controls.
- Every sync must write an audit event with actor or system job id, account,
  provider, period/window, inserted count, duplicate count, and failure detail.
- Provider outages must leave existing statement lines and ledger entries
  untouched.

## Non-Goals

- No direct balance mutation from bank feeds.
- No automatic ledger posting from provider data.
- No payment initiation, mandate creation, or fund transfer support.
- No storage of downloaded bank statements outside approved document retention.

## Production Signoff

Before enabling any live provider, run a production review for tenant consent,
secret handling, audit log evidence, provider failure handling, duplicate import
behavior, and reconciliation/voucher approval flow.
