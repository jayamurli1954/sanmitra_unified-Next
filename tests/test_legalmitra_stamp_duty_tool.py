"""Stamp duty intake helpers — required fields before estimate/AI handoff."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAMP_JS = ROOT / "frontend" / "legalmitra" / "legal-tools-stamp.js"


def test_stamp_duty_module_requires_state_and_values() -> None:
    text = STAMP_JS.read_text(encoding="utf-8")
    assert "missingStampDutyFields" in text
    assert "Sale consideration and/or Guidance value" in text
    assert "Practical registration checklist" in text
    assert "higher of" in text.lower() or "Math.max" in text
    assert "Do not discuss GST refunds" in text


def test_stamp_duty_checklist_covers_lifecycle_sections() -> None:
    text = STAMP_JS.read_text(encoding="utf-8")
    for section in (
        "Before registration",
        "Documents required",
        "Before signing",
        "At registration office",
        "After registration",
    ):
        assert section in text
