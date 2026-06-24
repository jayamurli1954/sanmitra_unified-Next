"""Work-order costing (Phase 2b) — standard-cost scaling, variance, lifecycle."""
import pytest

from app.modules.manufacturing.work_orders import (
    _ALLOWED_TRANSITIONS,
    compute_variance,
    scale_standard_cost,
)

BOM_STD = {"material_cost": "326.00", "overhead_cost": "57.75", "total_cost": "383.75"}


def test_scale_standard_cost_scales_by_planned_qty():
    out = scale_standard_cost(bom_standard=BOM_STD, bom_output_qty="1", planned_qty="10")
    assert out["material_cost"] == "3260.00"
    assert out["overhead_cost"] == "577.50"
    assert out["total_cost"] == "3837.50"
    assert out["planned_qty"] == "10.000"


def test_scale_standard_cost_handles_bom_output_qty_above_one():
    # BOM yields 4 units; producing 2 -> half the BOM cost.
    out = scale_standard_cost(bom_standard={"material_cost": "100.00", "overhead_cost": "20.00",
                                            "total_cost": "120.00"}, bom_output_qty="4", planned_qty="2")
    assert out["material_cost"] == "50.00"
    assert out["overhead_cost"] == "10.00"
    assert out["total_cost"] == "60.00"


def test_scale_rejects_zero_qty():
    with pytest.raises(ValueError):
        scale_standard_cost(bom_standard=BOM_STD, bom_output_qty="0", planned_qty="1")


def test_variance_overspend_is_unfavourable():
    std = {"material_cost": "3260.00", "overhead_cost": "577.50", "total_cost": "3837.50"}
    out = compute_variance(standard=std, actual_material="3500.00", actual_overhead="600.00")
    assert out["actual_cost"] == "4100.00"
    assert out["variance"] == "262.50"          # 4100.00 - 3837.50
    assert out["material_variance"] == "240.00"  # 3500 - 3260
    assert out["overhead_variance"] == "22.50"   # 600 - 577.50
    assert out["favourable"] is False


def test_variance_underspend_is_favourable():
    std = {"material_cost": "100.00", "overhead_cost": "20.00", "total_cost": "120.00"}
    out = compute_variance(standard=std, actual_material="90.00", actual_overhead="15.00")
    assert out["actual_cost"] == "105.00"
    assert out["variance"] == "-15.00"
    assert out["favourable"] is True


def test_variance_exact():
    std = {"material_cost": "100.00", "overhead_cost": "20.00", "total_cost": "120.00"}
    out = compute_variance(standard=std, actual_material="100.00", actual_overhead="20.00")
    assert out["variance"] == "0.00"
    assert out["favourable"] is False  # zero is not favourable


def test_lifecycle_transitions():
    assert _ALLOWED_TRANSITIONS["draft"] == {"released", "cancelled"}
    assert "completed" in _ALLOWED_TRANSITIONS["in_progress"]
    assert _ALLOWED_TRANSITIONS["completed"] == set()
    assert _ALLOWED_TRANSITIONS["cancelled"] == set()
