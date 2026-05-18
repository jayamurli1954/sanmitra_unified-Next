from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_legalmitra_template_strategy_exposes_quality_first_launch_catalog():
    response = client.get("/api/v1/legalmitra/template-strategy")

    assert response.status_code == 200
    data = response.json()

    titles = [item["title"] for item in data["launch_templates"]]
    assert titles == [
        "Professional Consultancy Agreement",
        "Software Development Agreement",
        "Non-Disclosure Agreement",
        "Employment Agreement",
        "Website Terms and Privacy Policy Bundle",
    ]
    assert data["launch_templates"][0]["status"] == "structured_renderer_available"
    assert data["launch_templates"][1]["status"] == "structured_renderer_available"
    assert all(item["status"] for item in data["launch_templates"])
    assert "Do not claim the entire legacy catalog is lawyer-grade until upgraded." in data["gap"]
    assert "numbered clauses and defined terms" in data["quality_gate"]
    assert "human-review disclaimer and execution-readiness questions" in data["quality_gate"]


def test_landing_content_includes_template_marketplace_quality_gate():
    response = client.get("/api/v1/legalmitra/landing-content")

    assert response.status_code == 200
    marketplace = response.json()["template_marketplace"]

    assert "Quality-first launch catalog" in marketplace["positioning"]
    assert len(marketplace["launch_templates"]) == 5
    assert marketplace["launch_templates"][1]["template_id"] == "software_development_agreement"
    assert "DPDP Act readiness" in marketplace["launch_templates"][4]["required_clauses"]
