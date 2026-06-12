from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_legalmitra_landing_content_is_public_and_complete() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/legalmitra/landing-content")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["solutions"]) >= 4
    assert len(payload["faq"]) >= 3
    assert payload["about"]["title"]
    assert payload["contact"]["email"]
    footer_labels = {item["label"] for item in payload["footer"]["links"]}
    assert {"About Us", "Contact", "Privacy Policy", "Terms of Service"}.issubset(footer_labels)


def test_legalmitra_public_pages_show_visible_pricing_amounts() -> None:
    landing_source = (REPO_ROOT / "frontend" / "legalmitra" / "index.html").read_text(encoding="utf-8")
    pricing_source = (REPO_ROOT / "frontend" / "legalmitra" / "pricing.html").read_text(encoding="utf-8")

    for source in (landing_source, pricing_source):
        assert "Rs. 399" in source
        assert "Rs. 3,999" in source
        assert "Rs. 899" in source
        assert "Rs. 8,999" in source
