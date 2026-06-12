# Razorpay Payment Pages Setup

## Current State

SanMitra uses one shared live Razorpay merchant account for LegalMitra, MandirMitra, GruhaMitra, and MitraBooks. The backend already exposes shared Razorpay metadata through `/api/v1/payments/razorpay/config/{app_key}` and records payment webhook metadata such as `app_key`, `plan`, `tenant_id`, merchant account, and merchant scope.

No Razorpay secrets, webhook secrets, live page links, payment data, or customer payment details should be committed to the repository.

## Target State

All four SanMitra products collect payments through the SanMitra Technologies Razorpay account:

- LegalMitra: Starter is Free, Growth is Rs. 399/month or Rs. 3,999/year, Professional is Rs. 899/month or Rs. 8,999/year.
- MitraBooks regular business: Free, Basic, Starter, and Growth plans.
- MitraBooks CA Practice / Bookkeepers: paid Basic, Starter, and Growth plans separate from regular business pricing.
- MandirMitra: paid Starter, Growth, and Professional plans only. No Free plan because temple/trust onboarding needs a minimum threshold.
- GruhaMitra: paid Starter, Growth, and Professional plans only. No Free plan because housing society onboarding needs a minimum flat threshold.

One-time implementation, migration, and training fee remains quote-based where applicable.

## Dashboard Setup Steps

Use the official Razorpay Payment Pages flow: <https://razorpay.com/docs/payments/payment-pages/create/>.

1. Sign in to the Razorpay Dashboard using the SanMitra Technologies account.
2. Stay in Live Mode if the dashboard/account no longer exposes a separate Test Mode.
3. Open Payment Pages and choose Create Payment Page, but do not share the page publicly yet.
4. Create separate Payment Pages for clean reconciliation:
   - LegalMitra Subscriptions
   - MandirMitra Subscriptions
   - GruhaMitra Subscriptions
   - MitraBooks Business Subscriptions
   - MitraBooks CA Practice Subscriptions
5. Keep currency as INR.
6. Add plan price fields:
   - LegalMitra Growth monthly: Rs. 399
   - LegalMitra Growth yearly: Rs. 3,999
   - LegalMitra Professional monthly: Rs. 899
   - LegalMitra Professional yearly: Rs. 8,999
   - Do not add a payment field for LegalMitra Starter because it is free signup, not a payment transaction.
7. Add required customer fields:
   - Customer name
   - Email
   - Phone
   - Product
   - Plan
   - Billing cycle
   - Tenant ID or onboarding reference, if already created
8. Add custom terms text that payment activates subscription access only after successful payment verification.
9. Set the successful-payment action to redirect back to the relevant SanMitra product page.
10. Save the live page and keep the link private until verification is complete.
11. Run one controlled low-value live payment from a SanMitra-owned payment method and keep the Razorpay page ID, payment ID, amount, email, and selected plan for backend verification.
12. Refund or internally account for the verification payment according to the Razorpay settlement/refund workflow.
13. Publish the page link only after webhook verification, subscription update, and billing transaction recording are confirmed.

## Recommended Page Metadata

Razorpay Payment Pages are configured in the dashboard. If the page supports passing notes/custom fields into the payment entity, capture these exact values:

| Field | Example | Required |
| --- | --- | --- |
| `app_key` | `legalmitra`, `mandirmitra`, `gruhamitra`, `mitrabooks`, `mitrabooks-ca-practice` | Yes |
| `plan` | `growth`, `professional`, `starter`, `basic` | Yes |
| `billing_cycle` | `monthly`, `yearly` | Yes |
| `tenant_id` | Tenant ID from onboarding | If available |
| `onboarding_reference` | SanMitra onboarding request ID | If tenant is not yet created |

After the first controlled live payment, inspect the Razorpay webhook payload. If Payment Page custom fields do not arrive under `payment.entity.notes`, add a backend mapping table from Razorpay page ID or selected price field to `app_key`, `plan`, and `billing_cycle` before publishing the link broadly.

## Webhook Setup

Configure the Razorpay webhook in the dashboard:

```text
POST https://<backend-domain>/api/v1/payments/webhook
```

Subscribe to these events:

- `payment.captured`
- `order.paid`
- `subscription.charged`

Set these backend environment variables in the deployment provider, never in committed files:

```text
RAZORPAY_KEY_ID=<public key id>
RAZORPAY_KEY_SECRET=<secret key>
RAZORPAY_WEBHOOK_SECRET=<dashboard webhook secret>
RAZORPAY_ACCOUNT_OWNER=SanMitra Technologies Private Limited
RAZORPAY_MERCHANT_SCOPE=sanmitra_platform
```

## Validation Checklist

1. Open `/api/v1/payments/razorpay/config/legalmitra` and confirm `shared_platform_account` is `true`.
2. Open `/api/v1/payments/pricing/legalmitra` and confirm Growth and Professional have rupee amounts.
3. Open `/api/v1/payments/pricing/mandirmitra` and confirm there is no Free plan.
4. Open `/api/v1/payments/pricing/gruhamitra` and confirm there is no Free plan.
5. Make one controlled low-value live payment from a private Payment Page link.
6. Confirm Razorpay sends the webhook and the backend accepts the signature.
7. Confirm `core_billing_transactions` records `email`, `amount_paise`, `app_key`, `plan`, `merchant_account`, and Razorpay payment ID.
8. Confirm the user subscription is upgraded only after a successful verified webhook.
9. Refund or internally account for the controlled live payment.
10. Publish public payment links only after the controlled live payment path passes.

## Deferred Scope

- Storing Razorpay Payment Page IDs in code is deferred until dashboard pages are created and test payloads are inspected.
- Automatic reconciliation from Payment Page custom fields is deferred if Razorpay does not send those fields in `payment.entity.notes`.
- Direct frontend checkout integration is deferred; Payment Pages are the current operational path.
