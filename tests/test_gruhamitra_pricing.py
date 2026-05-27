from fastapi.testclient import TestClient

from app.core.billing.pricing import GRUHAMITRA_PLAN_KEYS, get_product_pricing
from app.main import app


def test_gruhamitra_pricing_catalog_matches_approved_tiers() -> None:
    pricing = get_product_pricing("gruhamitra")

    assert pricing["app_key"] == "gruhamitra"
    assert pricing["product_name"] == "GruhaMitra"
    assert pricing["currency"] == "INR"
    assert pricing["one_time_fee_paise"] == 500000

    plans = {plan["key"]: plan for plan in pricing["plans"]}
    assert tuple(plans) == GRUHAMITRA_PLAN_KEYS

    assert plans["starter"]["min_flats"] == 25
    assert plans["starter"]["max_flats"] == 50
    assert plans["starter"]["cycles"][0] == {
        "cycle": "monthly",
        "price_per_flat_paise": 2500,
        "display_price": "Rs. 25 / flat",
    }
    assert plans["starter"]["cycles"][1]["price_per_flat_paise"] == 25000

    assert plans["growth"]["min_flats"] == 51
    assert plans["growth"]["max_flats"] == 100
    assert plans["growth"]["cycles"][0]["price_per_flat_paise"] == 3500
    assert plans["growth"]["cycles"][1]["price_per_flat_paise"] == 35000

    assert plans["professional"]["min_flats"] == 101
    assert plans["professional"]["max_flats"] is None
    assert plans["professional"]["cycles"][0]["price_per_flat_paise"] == 5000
    assert plans["professional"]["cycles"][1]["price_per_flat_paise"] == 50000


def test_gruhamitra_pricing_endpoint_is_public_and_product_scoped() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/payments/pricing/gruhamitra")

    assert response.status_code == 200
    assert response.json()["app_key"] == "gruhamitra"
    assert [plan["key"] for plan in response.json()["plans"]] == list(GRUHAMITRA_PLAN_KEYS)


def test_unknown_pricing_product_returns_404() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/payments/pricing/unknown")

    assert response.status_code == 404
    assert response.json()["detail"] == "Pricing product not found"

