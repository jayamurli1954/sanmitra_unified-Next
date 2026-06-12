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
4. Create one Payment Page for each subscription amount. Do not club multiple plans or billing cycles into one Razorpay page because the live dropdown/price-field behavior can confuse customers and reconciliation.
5. For LegalMitra, create these four live pages:
   - LegalMitra Growth Monthly - Rs. 399
   - LegalMitra Growth Yearly - Rs. 3,999
   - LegalMitra Professional Monthly - Rs. 899
   - LegalMitra Professional Yearly - Rs. 8,999
6. Apply the same one-page-per-amount rule for MandirMitra, GruhaMitra, MitraBooks Business, and MitraBooks CA Practice.
7. Keep currency as INR.
8. Add exactly one fixed amount field on each page:
   - The page title, amount label, and amount must match the selected plan.
   - Quantity should be disabled or fixed to 1 where Razorpay allows it.
   - Customer-entered amount should not be enabled for subscriptions.
   - LegalMitra Starter should not get a payment page because it is free signup, not a payment transaction.
9. Add required customer fields:
   - Customer name
   - Email
   - Phone
   - Tenant ID or onboarding reference, if already created
10. Add custom terms text that payment activates subscription access only after successful payment verification.
11. Set the successful-payment action to redirect back to the relevant SanMitra product page.
12. Save the live page and keep the link private until verification is complete.
13. Run one controlled low-value live payment from a SanMitra-owned payment method and keep the Razorpay page ID, payment ID, amount, email, and selected plan for backend verification.
14. Refund or internally account for the verification payment according to the Razorpay settlement/refund workflow.
15. Publish the page link only after webhook verification, subscription update, and billing transaction recording are confirmed.

## Recommended Page Metadata

Razorpay Payment Pages are configured in the dashboard. If the page supports passing notes/custom fields into the payment entity, capture these exact values:

| Field | Example | Required |
| --- | --- | --- |
| `app_key` | `legalmitra`, `mandirmitra`, `gruhamitra`, `mitrabooks`, `mitrabooks-ca-practice` | Yes |
| `plan` | `growth`, `professional`, `starter`, `basic` | Yes |
| `billing_cycle` | `monthly`, `yearly` | Yes |
| `tenant_id` | Tenant ID from onboarding | If available |
| `onboarding_reference` | SanMitra onboarding request ID | If tenant is not yet created |

Because each subscription amount has its own Payment Page, keep a private page-ID mapping sheet after creation. After the first controlled live payment, inspect the Razorpay webhook payload. If Payment Page custom fields do not arrive under `payment.entity.notes`, add a backend mapping table from Razorpay page ID to `app_key`, `plan`, `billing_cycle`, and expected amount before publishing the link broadly.

Current live page mapping:

| Razorpay Page ID | Payment URL | Product | Plan | Billing cycle | Amount paise | Subscription days |
| --- | --- | --- | --- | --- | --- | --- |
| `pl_T0f5if7cZZxXYf` | `https://rzp.io/rzp/d3cGen18` | LegalMitra | Growth | Monthly | `39900` | `30` |
| `pl_T0IIA3gIcKWr9y` | `https://rzp.io/rzp/GL2uoA7` | LegalMitra | Growth | Yearly | `399900` | `365` |
| `pl_T0mNwxh7rvpXf9` | `https://rzp.io/rzp/ffmtLtfK` | LegalMitra | Professional | Monthly | `89900` | `30` |
| `pl_T0mPFYkQ3JVNkG` | `https://rzp.io/rzp/br2LmKM` | LegalMitra | Professional | Yearly | `899900` | `365` |

The backend contains these four current LegalMitra mappings as defaults. Add future product/page IDs through the deployment environment variable below, using the same structure:

```json
{
  "pl_growth_yearly_page_id": {
    "app_key": "legalmitra",
    "plan": "growth",
    "billing_cycle": "yearly",
    "amount_paise": 399900,
    "subscription_days": 365
  },
  "pl_professional_monthly_page_id": {
    "app_key": "legalmitra",
    "plan": "professional",
    "billing_cycle": "monthly",
    "amount_paise": 89900,
    "subscription_days": 30
  }
}
```

```text
RAZORPAY_PAYMENT_PAGE_MAP_JSON=<json object above, compacted to one line for deployment env>
```

On successful webhook processing, the backend now stores these fields on both the user record and the billing transaction:

```text
billing_plan
billing_cycle
subscription_started_at
subscription_expires_at
razorpay_payment_page_id
```

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
RAZORPAY_ACCOUNT_OWNER=Sanmita Tech Solutions
RAZORPAY_MERCHANT_SCOPE=sanmitra_platform
RAZORPAY_PAYMENT_PAGE_MAP_JSON=<one-line JSON mapping for future page IDs>
```

## Validation Checklist

1. Open `/api/v1/payments/razorpay/config/legalmitra` and confirm `shared_platform_account` is `true`.
2. Open `/api/v1/payments/pricing/legalmitra` and confirm Growth and Professional have rupee amounts.
3. Open `/api/v1/payments/pricing/mandirmitra` and confirm there is no Free plan.
4. Open `/api/v1/payments/pricing/gruhamitra` and confirm there is no Free plan.
5. Make one controlled low-value live payment from one private Payment Page link.
6. Confirm Razorpay sends the webhook and the backend accepts the signature.
7. Confirm `core_billing_transactions` records `email`, `amount_paise`, `app_key`, `plan`, `merchant_account`, and Razorpay payment ID.
8. Confirm the user subscription is upgraded only after a successful verified webhook.
9. Refund or internally account for the controlled live payment.
10. Publish public payment links only after the controlled live payment path passes.

## Deferred Scope

- Storing Razorpay Payment Page IDs in code is deferred until dashboard pages are created and test payloads are inspected.
- Automatic reconciliation from Razorpay page ID is active for the current LegalMitra Growth Monthly page and should be extended as new live page IDs are created.
- Direct frontend checkout integration is deferred; Payment Pages are the current operational path.
