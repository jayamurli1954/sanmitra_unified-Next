from fastapi.testclient import TestClient

from app.core.billing.pricing import (
    GRUHAMITRA_PLAN_KEYS,
    LEGALMITRA_PLAN_KEYS,
    MITRABOOKS_CA_PRACTICE_PLAN_KEYS,
    MITRABOOKS_PLAN_KEYS,
    get_product_pricing,
)
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
    starter_monthly = plans["starter"]["cycles"][0]
    assert starter_monthly["cycle"] == "monthly"
    assert starter_monthly["price_per_flat_paise"] == 2500
    assert starter_monthly["display_price"] == "Rs. 25 / flat"
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


def test_legalmitra_pricing_catalog_is_available_for_shared_billing() -> None:
    pricing = get_product_pricing("legalmitra")

    assert pricing["app_key"] == "legalmitra"
    assert pricing["product_name"] == "LegalMitra"
    assert pricing["payment_provider"] == "razorpay"
    assert pricing["merchant_account"] == "SanMitra Technologies Private Limited"
    assert pricing["merchant_scope"] == "sanmitra_platform"

    plans = {plan["key"]: plan for plan in pricing["plans"]}
    assert tuple(plans) == LEGALMITRA_PLAN_KEYS
    assert plans["starter"]["fair_use"]["daily_research_queries"] == 5
    assert plans["growth"]["fair_use"]["daily_research_queries"] == 50
    assert plans["professional"]["fair_use"]["monthly_templates"] == 200


def test_legalmitra_pricing_endpoint_is_public_and_product_scoped() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/payments/pricing/legalmitra")

    assert response.status_code == 200
    assert response.json()["app_key"] == "legalmitra"
    assert [plan["key"] for plan in response.json()["plans"]] == list(LEGALMITRA_PLAN_KEYS)


def test_razorpay_config_endpoint_uses_one_sanmitra_account_for_all_products() -> None:
    client = TestClient(app)

    for app_key in ("legalmitra", "mandirmitra", "gruhamitra", "mitrabooks"):
        response = client.get(f"/api/v1/payments/razorpay/config/{app_key}")

        assert response.status_code == 200
        payload = response.json()
        assert payload["app_key"] == app_key
        assert payload["provider"] == "razorpay"
        assert payload["merchant_account"] == "SanMitra Technologies Private Limited"
        assert payload["merchant_scope"] == "sanmitra_platform"
        assert payload["shared_platform_account"] is True
        assert set(payload["supported_app_keys"]) >= {"legalmitra", "mandirmitra", "gruhamitra", "mitrabooks"}
        assert "key_id_configured" in payload
        assert "webhook_configured" in payload


def test_mitrabooks_pricing_catalog_supports_business_and_ca_practice_modes() -> None:
    pricing = get_product_pricing("mitrabooks")

    assert pricing["app_key"] == "mitrabooks"
    assert pricing["product_name"] == "MitraBooks"
    assert pricing["currency"] == "INR"
    assert pricing["one_time_fee_label"] == "One-time implementation, migration, and training fee: get quote"

    plans = {plan["key"]: plan for plan in pricing["plans"]}
    assert tuple(plans) == MITRABOOKS_PLAN_KEYS

    assert plans["free"]["cycles"][0]["price_paise"] == 0
    assert plans["free"]["fair_use"]["companies"] == 1
    assert plans["basic"]["cycles"][0]["price_paise"] == 49900
    assert plans["basic"]["fair_use"]["ocr_documents_per_month"] == 25
    assert plans["starter"]["fair_use"]["companies"] == 5
    assert plans["starter"]["fair_use"]["users"] == 1
    assert "Single business user with up to 5 companies" in plans["starter"]["features"]
    assert plans["growth"]["cycles"][0]["price_paise"] == 149900
    assert plans["growth"]["cycles"][1]["price_paise"] == 1499900
    assert plans["growth"]["fair_use"]["companies"] == 10
    assert plans["growth"]["fair_use"]["users"] == 1
    assert plans["growth"]["fair_use"]["ocr_documents_per_month"] == 100
    assert "Regular business multi-company workspace" in plans["growth"]["features"]


def test_mitrabooks_ca_practice_pricing_is_separate_from_regular_business() -> None:
    pricing = get_product_pricing("mitrabooks-ca-practice")

    assert pricing["app_key"] == "mitrabooks-ca-practice"
    assert pricing["product_name"] == "MitraBooks CA Practice / Bookkeepers"
    assert pricing["currency"] == "INR"

    plans = {plan["key"]: plan for plan in pricing["plans"]}
    assert tuple(plans) == MITRABOOKS_CA_PRACTICE_PLAN_KEYS

    assert plans["basic"]["cycles"][0]["price_paise"] == 49900
    assert plans["basic"]["fair_use"]["client_companies"] == 5
    assert plans["basic"]["fair_use"]["practice_users"] == 1
    assert plans["basic"]["fair_use"]["ocr_documents_per_month"] == 0
    assert plans["starter"]["cycles"][0]["price_paise"] == 99900
    assert plans["starter"]["fair_use"]["client_companies"] == 25
    assert plans["starter"]["fair_use"]["practice_users"] == 5
    assert plans["starter"]["fair_use"]["ocr_documents_per_month"] == 500
    assert plans["growth"]["cycles"][0]["price_paise"] == 299900
    assert plans["growth"]["cycles"][1]["price_paise"] == 2999900
    assert plans["growth"]["fair_use"]["client_companies"] == 50
    assert plans["growth"]["fair_use"]["practice_users"] == 15
    assert "Full CA/bookkeeper multi-user, multi-company workspace" in plans["growth"]["features"]


def test_mitrabooks_pricing_endpoint_is_public_and_product_scoped() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/payments/pricing/mitrabooks")

    assert response.status_code == 200
    assert response.json()["app_key"] == "mitrabooks"
    assert [plan["key"] for plan in response.json()["plans"]] == list(MITRABOOKS_PLAN_KEYS)


def test_mitrabooks_ca_practice_pricing_endpoint_is_public_and_product_scoped() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/payments/pricing/mitrabooks-ca-practice")

    assert response.status_code == 200
    assert response.json()["app_key"] == "mitrabooks-ca-practice"
    assert [plan["key"] for plan in response.json()["plans"]] == list(MITRABOOKS_CA_PRACTICE_PLAN_KEYS)


def test_unknown_pricing_product_returns_404() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/payments/pricing/unknown")

    assert response.status_code == 404
    assert response.json()["detail"] == "Pricing product not found"

