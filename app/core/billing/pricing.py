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


GRUHAMITRA_PLAN_KEYS = ("starter", "growth", "professional")
MANDIRMITRA_PLAN_KEYS = ("starter", "growth", "professional")
MITRABOOKS_PLAN_KEYS = ("free", "basic", "starter", "growth")

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
                "companies": 3,
                "users": 3,
                "invoices_per_month": 1000,
                "ocr_documents_per_month": 100,
            },
            features=(
                "Single user with up to 3 companies or small internal team",
                "Bank reconciliation, ageing, statements, and inventory basics",
                "AI categorization suggestions with human review",
                "Priority email support",
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
                "companies": 25,
                "users": 10,
                "invoices_per_month": 5000,
                "ocr_documents_per_month": 500,
            },
            features=(
                "CA practice or bookkeeper multi-user, multi-company workspace",
                "Client assignment, compliance tracking, and review queues",
                "AI MIS, document upload, OCR extraction, and reconciliation assistance",
                "Priority support and onboarding review",
            ),
        ),
    ),
)

PRODUCT_PRICING = {
    GRUHAMITRA_PRICING.app_key: GRUHAMITRA_PRICING,
    MANDIRMITRA_PRICING.app_key: MANDIRMITRA_PRICING,
    MITRABOOKS_PRICING.app_key: MITRABOOKS_PRICING,
}


def get_product_pricing(app_key: str) -> dict:
    normalized_app_key = str(app_key or "").strip().lower()
    pricing = PRODUCT_PRICING.get(normalized_app_key)
    if pricing is None:
        raise KeyError("Unknown pricing product")
    return asdict(pricing)
