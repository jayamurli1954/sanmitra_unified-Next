from fastapi.testclient import TestClient

from app.main import app


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
