from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class BillingCyclePrice:
    cycle: str
    display_price: str
    price_paise: int | None = None
    price_per_flat_paise: int | None = None


@dataclass(frozen=True)
class ProductPlan:
    key: str
    name: str
    cycles: tuple[BillingCyclePrice, ...]
    min_flats: int | None = None
    max_flats: int | None = None
    fair_use: dict[str, int] | None = None
    features: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProductPricing:
    app_key: str
    product_name: str
    currency: str
    one_time_fee_paise: int
    one_time_fee_label: str
    plans: tuple[ProductPlan, ...]
    payment_provider: str = "razorpay"
    merchant_account: str = "SanMitra Technologies Private Limited"
    merchant_scope: str = "sanmitra_platform"


LEGALMITRA_PLAN_KEYS = ("starter", "growth", "professional")
GRUHAMITRA_PLAN_KEYS = ("starter", "growth", "professional")
MANDIRMITRA_PLAN_KEYS = ("starter", "growth", "professional")
MITRABOOKS_PLAN_KEYS = ("free", "basic", "starter", "growth")
MITRABOOKS_CA_PRACTICE_PLAN_KEYS = ("basic", "starter", "growth")

LEGALMITRA_PRICING = ProductPricing(
    app_key="legalmitra",
    product_name="LegalMitra",
    currency="INR",
    one_time_fee_paise=0,
    one_time_fee_label="No one-time setup fee for self-service LegalMitra plans",
    plans=(
        ProductPlan(
            key="starter",
            name="Starter",
            cycles=(
                BillingCyclePrice(cycle="monthly", display_price="Free", price_paise=0),
                BillingCyclePrice(cycle="yearly", display_price="Free", price_paise=0),
            ),
            fair_use={
                "daily_research_queries": 5,
                "monthly_templates": 5,
                "compliance_tracker_records": 10,
                "retention_days": 30,
            },
            features=(
                "Light legal research and basic tools",
                "Limited template drafts",
                "GST Rate Finder and Limitation Calculator",
            ),
        ),
        ProductPlan(
            key="growth",
            name="Growth",
            cycles=(
                BillingCyclePrice(cycle="monthly", display_price="Rs. 399", price_paise=39900),
                BillingCyclePrice(cycle="yearly", display_price="Rs. 3,999", price_paise=399900),
            ),
            fair_use={
                "daily_research_queries": 50,
                "monthly_templates": 30,
                "compliance_tracker_records": 100,
                "retention_days": 150,
            },
            features=(
                "Daily research, drafting, and tracker usage",
                "All Legal Tools",
                "Response save, share, and download actions",
            ),
        ),
        ProductPlan(
            key="professional",
            name="Professional",
            cycles=(
                BillingCyclePrice(cycle="monthly", display_price="Rs. 899", price_paise=89900),
                BillingCyclePrice(cycle="yearly", display_price="Rs. 8,999", price_paise=899900),
            ),
            fair_use={
                "daily_research_queries": 0,
                "monthly_templates": 200,
                "compliance_tracker_records": 0,
                "retention_days": 300,
            },
            features=(
                "High-volume legal workflow capacity",
                "Official PDF upload and auto-fill workflow",
                "Priority workflow capacity",
            ),
        ),
    ),
)

GRUHAMITRA_PRICING = ProductPricing(
    app_key="gruhamitra",
    product_name="GruhaMitra",
    currency="INR",
    one_time_fee_paise=500000,
    one_time_fee_label="One-time implementation, migration, and training fee",
    plans=(
        ProductPlan(
            key="starter",
            name="Starter",
            cycles=(
                BillingCyclePrice(cycle="monthly", display_price="Rs. 25 / flat", price_per_flat_paise=2500),
                BillingCyclePrice(cycle="yearly", display_price="Rs. 250 / flat", price_per_flat_paise=25000),
            ),
            min_flats=25,
            max_flats=50,
        ),
        ProductPlan(
            key="growth",
            name="Growth",
            cycles=(
                BillingCyclePrice(cycle="monthly", display_price="Rs. 35 / flat", price_per_flat_paise=3500),
                BillingCyclePrice(cycle="yearly", display_price="Rs. 350 / flat", price_per_flat_paise=35000),
            ),
            min_flats=51,
            max_flats=100,
        ),
        ProductPlan(
            key="professional",
            name="Professional",
            cycles=(
                BillingCyclePrice(cycle="monthly", display_price="Rs. 50 / flat", price_per_flat_paise=5000),
                BillingCyclePrice(cycle="yearly", display_price="Rs. 500 / flat", price_per_flat_paise=50000),
            ),
            min_flats=101,
            max_flats=None,
        ),
    ),
)

MANDIRMITRA_PRICING = ProductPricing(
    app_key="mandirmitra",
    product_name="MandirMitra",
    currency="INR",
    one_time_fee_paise=1000000,
    one_time_fee_label="One-time implementation, migration, and training fee",
    plans=(
        ProductPlan(
            key="starter",
            name="Starter",
            cycles=(
                BillingCyclePrice(cycle="monthly", display_price="Rs. 500 / month", price_paise=50000),
                BillingCyclePrice(cycle="yearly", display_price="Rs. 5,000 / year", price_paise=500000),
            ),
            fair_use={"receipts_per_month": 500, "seva_bookings_per_month": 100, "users": 3},
            features=("Donations and seva booking", "Bilingual receipts", "Basic roles and access"),
        ),
        ProductPlan(
            key="growth",
            name="Growth",
            cycles=(
                BillingCyclePrice(cycle="monthly", display_price="Rs. 750 / month", price_paise=75000),
                BillingCyclePrice(cycle="yearly", display_price="Rs. 7,500 / year", price_paise=750000),
            ),
            fair_use={"receipts_per_month": 2000, "seva_bookings_per_month": 500, "users": 10},
            features=("Accounting integration", "Advanced reports and audit drilldown", "Priority support"),
        ),
        ProductPlan(
            key="professional",
            name="Professional",
            cycles=(
                BillingCyclePrice(cycle="monthly", display_price="Rs. 1,200 / month", price_paise=120000),
                BillingCyclePrice(cycle="yearly", display_price="Rs. 12,000 / year", price_paise=1200000),
            ),
            fair_use={"receipts_per_month": 10000, "seva_bookings_per_month": 2500, "users": 25},
            features=("Multi-entity controls", "API/webhook integrations", "Advanced governance support"),
        ),
    ),
)

MITRABOOKS_PRICING = ProductPricing(
    app_key="mitrabooks",
    product_name="MitraBooks",
    currency="INR",
    one_time_fee_paise=0,
    one_time_fee_label="One-time implementation, migration, and training fee: get quote",
    plans=(
        ProductPlan(
            key="free",
            name="Free",
            cycles=(
                BillingCyclePrice(cycle="monthly", display_price="Rs. 0 / month", price_paise=0),
                BillingCyclePrice(cycle="yearly", display_price="Rs. 0 / year", price_paise=0),
            ),
            fair_use={
                "companies": 1,
                "users": 1,
                "invoices_per_month": 25,
                "ocr_documents_per_month": 0,
            },
            features=(
                "Single-company books",
                "Basic parties, vouchers, invoices, and reports",
                "Manual data entry only",
                "Community/self-service support",
            ),
        ),
        ProductPlan(
            key="basic",
            name="Basic",
            cycles=(
                BillingCyclePrice(cycle="monthly", display_price="Rs. 499 / month", price_paise=49900),
                BillingCyclePrice(cycle="yearly", display_price="Rs. 4,999 / year", price_paise=499900),
            ),
            fair_use={
                "companies": 1,
                "users": 1,
                "invoices_per_month": 250,
                "ocr_documents_per_month": 25,
            },
            features=(
                "Single-user, single-company accounting",
                "GST preparation reports and TDS/TCS tracking",
                "Basic document upload and OCR queue",
                "Email support",
            ),
        ),
        ProductPlan(
            key="starter",
            name="Starter",
            cycles=(
                BillingCyclePrice(cycle="monthly", display_price="Rs. 999 / month", price_paise=99900),
                BillingCyclePrice(cycle="yearly", display_price="Rs. 9,999 / year", price_paise=999900),
            ),
            fair_use={
                "companies": 5,
                "users": 1,
                "invoices_per_month": 1000,
                "ocr_documents_per_month": 25,
            },
            features=(
                "Single business user with up to 5 companies",
                "Bank reconciliation, ageing, statements, and inventory basics",
                "AI categorization suggestions with human review",
                "Priority email support",
            ),
        ),
        ProductPlan(
            key="growth",
            name="Growth",
            cycles=(
                BillingCyclePrice(cycle="monthly", display_price="Rs. 1,499 / month", price_paise=149900),
                BillingCyclePrice(cycle="yearly", display_price="Rs. 14,999 / year", price_paise=1499900),
            ),
            fair_use={
                "companies": 10,
                "users": 1,
                "invoices_per_month": 5000,
                "ocr_documents_per_month": 100,
            },
            features=(
                "Regular business multi-company workspace",
                "Higher business document limits",
                "AI MIS, document upload, OCR extraction, and reconciliation assistance with review",
                "Priority support",
            ),
        ),
    ),
)

MITRABOOKS_CA_PRACTICE_PRICING = ProductPricing(
    app_key="mitrabooks-ca-practice",
    product_name="MitraBooks CA Practice / Bookkeepers",
    currency="INR",
    one_time_fee_paise=0,
    one_time_fee_label="One-time implementation, migration, and training fee: get quote",
    plans=(
        ProductPlan(
            key="basic",
            name="Basic",
            cycles=(
                BillingCyclePrice(cycle="monthly", display_price="Rs. 499 / month", price_paise=49900),
                BillingCyclePrice(cycle="yearly", display_price="Rs. 4,999 / year", price_paise=499900),
            ),
            fair_use={
                "practice_users": 1,
                "client_companies": 5,
                "ocr_documents_per_month": 0,
            },
            features=(
                "Single practitioner workspace",
                "Up to 5 client companies",
                "Manual document and client tracking",
            ),
        ),
        ProductPlan(
            key="starter",
            name="Starter",
            cycles=(
                BillingCyclePrice(cycle="monthly", display_price="Rs. 999 / month", price_paise=99900),
                BillingCyclePrice(cycle="yearly", display_price="Rs. 9,999 / year", price_paise=999900),
            ),
            fair_use={
                "practice_users": 5,
                "client_companies": 25,
                "ocr_documents_per_month": 500,
            },
            features=(
                "Small CA/bookkeeper team workspace",
                "Client document queues and review status",
                "Compliance tracking and staff assignment",
            ),
        ),
        ProductPlan(
            key="growth",
            name="Growth",
            cycles=(
                BillingCyclePrice(cycle="monthly", display_price="Rs. 2,999 / month", price_paise=299900),
                BillingCyclePrice(cycle="yearly", display_price="Rs. 29,999 / year", price_paise=2999900),
            ),
            fair_use={
                "practice_users": 15,
                "client_companies": 50,
                "ocr_documents_per_month": 0,
            },
            features=(
                "Full CA/bookkeeper multi-user, multi-company workspace",
                "Up to 50 client companies",
                "Unlimited OCR subject to fair-use and provider controls",
                "Priority support and onboarding review",
            ),
        ),
    ),
)

PRODUCT_PRICING = {
    LEGALMITRA_PRICING.app_key: LEGALMITRA_PRICING,
    GRUHAMITRA_PRICING.app_key: GRUHAMITRA_PRICING,
    MANDIRMITRA_PRICING.app_key: MANDIRMITRA_PRICING,
    MITRABOOKS_PRICING.app_key: MITRABOOKS_PRICING,
    MITRABOOKS_CA_PRACTICE_PRICING.app_key: MITRABOOKS_CA_PRACTICE_PRICING,
}


def get_product_pricing(app_key: str) -> dict:
    normalized_app_key = str(app_key or "").strip().lower()
    pricing = PRODUCT_PRICING.get(normalized_app_key)
    if pricing is None:
        raise KeyError("Unknown pricing product")
    return asdict(pricing)
