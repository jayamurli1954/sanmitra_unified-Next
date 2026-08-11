from __future__ import annotations

from io import BytesIO

import pytest
from fastapi import UploadFile
from openpyxl import Workbook

from app.modules.office_ai.services.mis_excel_import import parse_mis_excel


def _xlsx_bytes(*, sheet_name: str, headers: list[str], rows: list[list[object]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _upload(filename: str, content: bytes) -> UploadFile:
    # parse_mis_excel reads file.file.read() synchronously.
    return UploadFile(filename=filename, file=BytesIO(content))


def test_parse_mis_excel_valid_row():
    content = _xlsx_bytes(
        sheet_name="MISFacts",
        headers=[
            "entity_type",
            "fact_id",
            "source_ref",
            "period",
            "amount_decimal",
            "currency",
            "source_system",
        ],
        rows=[
            ["pnl_line", "F1", "PnL!B12", "2026-07", 1000.5, "INR", "excel_import"],
        ],
    )
    file = _upload("mis.xlsx", content)

    facts, report = parse_mis_excel(file=file, sheet_name="MISFacts")
    assert report["errors"] == []
    assert len(facts) == 1
    assert facts[0]["entity_type"] == "pnl_line"
    assert facts[0]["source_ref"] == "PnL!B12"
    assert facts[0]["amount_decimal"] is not None


def test_parse_mis_excel_invalid_entity_type_reports_row_error():
    content = _xlsx_bytes(
        sheet_name="MISFacts",
        headers=["entity_type", "source_ref", "amount_decimal"],
        rows=[
            ["unknown_entity", "X1", 10],
        ],
    )
    file = _upload("mis.xlsx", content)
    facts, report = parse_mis_excel(file=file, sheet_name="MISFacts")
    assert facts == []
    assert len(report["errors"]) == 1
    err = report["errors"][0]
    assert err["row"] == 2
    assert err["column"] == "entity_type"


def test_parse_mis_excel_missing_required_column_entity_type():
    content = _xlsx_bytes(
        sheet_name="MISFacts",
        headers=["source_ref", "amount_decimal"],
        rows=[
            ["X1", 10],
        ],
    )
    file = _upload("mis.xlsx", content)
    facts, report = parse_mis_excel(file=file, sheet_name="MISFacts")
    assert facts == []
    assert any(e["column"] == "entity_type" for e in report["errors"])

