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

PRODUCT_PRICING = {
    GRUHAMITRA_PRICING.app_key: GRUHAMITRA_PRICING,
    MANDIRMITRA_PRICING.app_key: MANDIRMITRA_PRICING,
}


def get_product_pricing(app_key: str) -> dict:
    normalized_app_key = str(app_key or "").strip().lower()
    pricing = PRODUCT_PRICING.get(normalized_app_key)
    if pricing is None:
        raise KeyError("Unknown pricing product")
    return asdict(pricing)
