from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class BillingCyclePrice:
    cycle: str
    price_per_flat_paise: int
    display_price: str


@dataclass(frozen=True)
class ProductPlan:
    key: str
    name: str
    min_flats: int
    max_flats: int | None
    cycles: tuple[BillingCyclePrice, ...]


@dataclass(frozen=True)
class ProductPricing:
    app_key: str
    product_name: str
    currency: str
    one_time_fee_paise: int
    one_time_fee_label: str
    plans: tuple[ProductPlan, ...]


GRUHAMITRA_PLAN_KEYS = ("starter", "growth", "professional")

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
            min_flats=25,
            max_flats=50,
            cycles=(
                BillingCyclePrice(cycle="monthly", price_per_flat_paise=2500, display_price="Rs. 25 / flat"),
                BillingCyclePrice(cycle="yearly", price_per_flat_paise=25000, display_price="Rs. 250 / flat"),
            ),
        ),
        ProductPlan(
            key="growth",
            name="Growth",
            min_flats=51,
            max_flats=100,
            cycles=(
                BillingCyclePrice(cycle="monthly", price_per_flat_paise=3500, display_price="Rs. 35 / flat"),
                BillingCyclePrice(cycle="yearly", price_per_flat_paise=35000, display_price="Rs. 350 / flat"),
            ),
        ),
        ProductPlan(
            key="professional",
            name="Professional",
            min_flats=101,
            max_flats=None,
            cycles=(
                BillingCyclePrice(cycle="monthly", price_per_flat_paise=5000, display_price="Rs. 50 / flat"),
                BillingCyclePrice(cycle="yearly", price_per_flat_paise=50000, display_price="Rs. 500 / flat"),
            ),
        ),
    ),
)

PRODUCT_PRICING = {
    GRUHAMITRA_PRICING.app_key: GRUHAMITRA_PRICING,
}


def get_product_pricing(app_key: str) -> dict:
    normalized_app_key = str(app_key or "").strip().lower()
    pricing = PRODUCT_PRICING.get(normalized_app_key)
    if pricing is None:
        raise KeyError("Unknown pricing product")
    return asdict(pricing)

