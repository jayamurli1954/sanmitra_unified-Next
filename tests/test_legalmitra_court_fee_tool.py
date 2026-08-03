"""Court fee rules config — maintainable state engine, not hard-coded UI tables."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "frontend" / "legalmitra" / "data" / "court-fee-rules.json"
MODULE = ROOT / "frontend" / "legalmitra" / "legal-tools-court-fee.js"


def test_court_fee_rules_json_has_states_and_case_types() -> None:
    data = json.loads(RULES.read_text(encoding="utf-8"))
    assert data["version"]
    assert "karnataka" in data["states"]
    assert "maharashtra" in data["states"]
    assert any(row["key"] == "money_recovery" for row in data["case_types"])
    assert "common_caveats" in data
    assert data["states"]["karnataka"]["act"]
    money = data["states"]["karnataka"]["case_rules"]["money_recovery"]
    assert money["fee_mode"] == "ad_valorem_orientation"
    partition = data["states"]["karnataka"]["case_rules"]["partition"]
    assert partition["fee_mode"] == "schedule_verification"


def test_court_fee_module_requires_intake_and_uses_config() -> None:
    text = MODULE.read_text(encoding="utf-8")
    assert "missingCourtFeeFields" in text
    assert "court-fee-rules.json" in text
    assert "Applicable law" in text or "Applicable Act" in text
    assert "Do not discuss GST refunds" in text


def test_court_fee_app_wires_config_intake_and_ai_gate() -> None:
    app = (ROOT / "frontend" / "legalmitra" / "app.js").read_text(encoding="utf-8")
    assert 'from "./legal-tools-court-fee.js"' in app
    assert "loadCourtFeeRules" in app
    assert "buildCourtFeeAiPrompt" in app
    assert 'toolKey === "court-fee"' in app
    assert "courtFeeToolBodyHtml" in app
    # Avoid inventing binding fee tables in app.js itself
    assert "Karnataka Court Fees" not in app
