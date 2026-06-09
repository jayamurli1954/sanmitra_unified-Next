"""Generic report exporter — CSV / XLSX / PDF builders (no DB needed)."""
from decimal import Decimal

import pytest

from app.modules.business.report_export import (
    build_csv,
    build_pdf,
    build_xlsx,
    export_report,
)

COLUMNS = [
    {"key": "party_name", "label": "Party"},
    {"key": "balance", "label": "Balance", "numeric": True},
]
ROWS = [
    {"party_name": "Acme", "balance": Decimal("1200.50")},
    {"party_name": "Beta", "balance": "800"},
    {"party_name": "Unallocated", "balance": None},
]
FOOTER = {"party_name": "Total", "balance": Decimal("2000.50")}
META = [("As of", "2026-06-09"), ("Type", "receivable")]


def _kw():
    return dict(title="Sundry Debtors", columns=COLUMNS, rows=ROWS, footer=FOOTER, meta=META)


def test_csv_has_title_meta_header_rows_and_footer():
    text = build_csv(**_kw()).decode("utf-8-sig")
    lines = [l for l in text.splitlines()]
    assert lines[0] == "Sundry Debtors"
    assert "As of,2026-06-09" in lines
    assert "Party,Balance" in lines
    assert "Acme,1200.50" in lines
    assert "Beta,800" in lines
    assert lines[-1] == "Total,2000.50"


def test_csv_uses_bom_for_excel_utf8():
    assert build_csv(**_kw()).startswith(b"\xef\xbb\xbf")


def test_xlsx_is_a_valid_office_zip():
    assert build_xlsx(**_kw())[:2] == b"PK"


def test_pdf_has_magic_header():
    assert build_pdf(**_kw())[:5] == b"%PDF-"


def test_pdf_landscape_path_for_wide_tables():
    wide_cols = [{"key": f"c{i}", "label": f"C{i}", "numeric": i > 0} for i in range(7)]
    wide_rows = [{f"c{i}": i for i in range(7)}]
    assert build_pdf(title="Wide", columns=wide_cols, rows=wide_rows)[:5] == b"%PDF-"


def test_export_report_sets_filename_and_media_type():
    resp = export_report("csv", filename_base="debtors_2026-06-09", **_kw())
    assert resp.media_type == "text/csv"
    assert 'filename="debtors_2026-06-09.csv"' in resp.headers["content-disposition"]

    resp_x = export_report("xlsx", filename_base="x", **_kw())
    assert "spreadsheetml" in resp_x.media_type
    resp_p = export_report("pdf", filename_base="p", **_kw())
    assert resp_p.media_type == "application/pdf"


def test_export_report_rejects_unknown_format():
    with pytest.raises(ValueError, match="csv, xlsx, pdf"):
        export_report("docx", filename_base="x", **_kw())


def test_empty_rows_still_produce_files():
    kw = dict(title="Empty", columns=COLUMNS, rows=[], footer=None, meta=None)
    assert build_csv(**kw).decode("utf-8-sig").splitlines()[0] == "Empty"
    assert build_xlsx(**kw)[:2] == b"PK"
    assert build_pdf(**kw)[:5] == b"%PDF-"
