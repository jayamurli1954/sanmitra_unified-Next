"""BOM standard-cost roll-up (Phase 2a) — the deterministic costing core."""
import pytest

from app.modules.manufacturing.bom import compute_bom_standard_cost


def test_standard_cost_materials_with_scrap_and_overhead():
    out = compute_bom_standard_cost(
        components=[
            {"item_id": "brass", "qty": "1.5", "scrap_pct": "2", "rate": "200.00"},   # 1.5*1.02*200 = 306.00
            {"item_id": "coat", "qty": "0.25", "scrap_pct": "0", "rate": "80.00"},     # 0.25*80 = 20.00
        ],
        operations=[
            {"runtime_hrs": "0.75", "overhead_rate": "45.00"},  # 33.75
            {"runtime_hrs": "1.20", "overhead_rate": "20.00"},  # 24.00
        ],
        output_qty="1",
    )
    assert out["material_cost"] == "326.00"
    assert out["overhead_cost"] == "57.75"
    assert out["total_cost"] == "383.75"
    assert out["per_unit_cost"] == "383.75"


def test_standard_cost_per_unit_divides_by_output_qty():
    out = compute_bom_standard_cost(
        components=[{"item_id": "x", "qty": "10", "scrap_pct": "0", "rate": "5.00"}],  # 50.00
        operations=[],
        output_qty="4",
    )
    assert out["total_cost"] == "50.00"
    assert out["per_unit_cost"] == "12.50"  # 50 / 4


def test_standard_cost_no_operations():
    out = compute_bom_standard_cost(
        components=[{"item_id": "x", "qty": "2", "scrap_pct": "0", "rate": "100.00"}],
        operations=[],
        output_qty="1",
    )
    assert out["overhead_cost"] == "0.00"
    assert out["total_cost"] == "200.00"


def test_standard_cost_rejects_zero_output():
    with pytest.raises(ValueError):
        compute_bom_standard_cost(components=[{"item_id": "x", "qty": "1", "rate": "1"}],
                                  operations=[], output_qty="0")
