"""Open-source OCR + Indian-GST rules backend (DEFAULT).

Tesseract reads the document locally (no API key, no per-document cost, nothing
leaves the server/device); a deterministic rules layer maps the text to accounting
fields. Rules are intentionally conservative — most results land below the
auto-threshold and route to human review, which is the safe default. The LLM-vision
backend is what lifts confidence high enough to auto-draft.

Tesseract/PIL are optional: if they are not installed, the backend returns an empty
result and the item falls back to human review instead of crashing.
"""
from __future__ import annotations

import io
import re
from typing import Any

from app.modules.business.capture.backends.base import PageImage, empty_result
from app.modules.business.capture.validators import gstin_check_digit_ok

_GSTIN_RE = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z][0-9A-Z]\b")
_AMOUNT_RE = re.compile(r"(?:₹|rs\.?|inr)?\s*([0-9][0-9,]*\.?[0-9]{0,2})", re.IGNORECASE)
_DATE_RES = [
    (re.compile(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b"), "ymd"),
    (re.compile(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})\b"), "dmy"),
]
# Require an explicit no/number/# marker so a bare "Invoice" heading doesn't match.
_INV_NO_RE = re.compile(r"(?:invoice|bill|inv)\s*(?:no\.?|number|#)\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9/\-]{2,})", re.IGNORECASE)


def _num(s: str) -> float | None:
    try:
        return float(s.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def _amounts_in(line: str) -> list[float]:
    out: list[float] = []
    for m in _AMOUNT_RE.finditer(line):
        n = _num(m.group(1))
        if n is not None:
            out.append(n)
    return out


def _parse_date(text: str) -> str | None:
    for rx, kind in _DATE_RES:
        m = rx.search(text)
        if not m:
            continue
        try:
            if kind == "ymd":
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            else:
                d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if y < 100:
                    y += 2000
            if 1 <= mo <= 12 and 1 <= d <= 31 and 2000 <= y <= 2100:
                return f"{y:04d}-{mo:02d}-{d:02d}"
        except (ValueError, IndexError):
            continue
    return None


def _structure(text: str, page_quality: float) -> tuple[dict[str, Any], dict[str, float], str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    fields: dict[str, Any] = {}
    conf: dict[str, float] = {}

    # Vendor GSTIN — first checksum-valid GSTIN in the text.
    for m in _GSTIN_RE.finditer(text.upper()):
        if gstin_check_digit_ok(m.group(0)):
            fields["vendor_gstin"] = m.group(0)
            conf["vendor_gstin"] = round(0.9 * page_quality, 3)
            break

    # Invoice number.
    m = _INV_NO_RE.search(text)
    if m:
        fields["invoice_number"] = m.group(1).strip()
        conf["invoice_number"] = round(0.7 * page_quality, 3)

    # Invoice date.
    d = _parse_date(text)
    if d:
        fields["invoice_date"] = d
        conf["invoice_date"] = round(0.7 * page_quality, 3)

    # Total — the largest amount on a line mentioning "total", else the largest overall.
    total_candidates: list[float] = []
    for ln in lines:
        if re.search(r"\b(grand\s*total|total|amount\s*payable|net\s*payable)\b", ln, re.IGNORECASE):
            total_candidates.extend(_amounts_in(ln))
    all_amounts = [a for ln in lines for a in _amounts_in(ln)]
    if total_candidates:
        fields["total_amount"] = max(total_candidates)
        conf["total_amount"] = round(0.72 * page_quality, 3)
    elif all_amounts:
        fields["total_amount"] = max(all_amounts)
        conf["total_amount"] = round(0.5 * page_quality, 3)

    # Taxable value & tax amounts by keyword.
    def _near(keyword: str) -> float | None:
        for ln in lines:
            if re.search(keyword, ln, re.IGNORECASE):
                amts = _amounts_in(ln)
                if amts:
                    return amts[-1]
        return None

    taxable = _near(r"\btaxable\b")
    if taxable is not None:
        fields["taxable_value"] = taxable
        conf["taxable_value"] = round(0.6 * page_quality, 3)
    cgst = _near(r"\bcgst\b")
    sgst = _near(r"\bsgst\b")
    igst = _near(r"\bigst\b")
    if any(v is not None for v in (cgst, sgst, igst)):
        fields["cgst_amount"] = cgst
        fields["sgst_amount"] = sgst
        fields["igst_amount"] = igst
        fields["tax_amount"] = sum(v for v in (cgst, sgst, igst) if v is not None)
        conf["tax_amount"] = round(0.6 * page_quality, 3)

    # Vendor name — top-of-document heuristic (first substantial line). Low confidence.
    for ln in lines[:5]:
        if len(ln) >= 3 and not _GSTIN_RE.search(ln.upper()) and not re.fullmatch(r"[\d\W]+", ln):
            fields["vendor_name"] = ln[:120]
            conf["vendor_name"] = round(0.45 * page_quality, 3)
            break

    doc_type = "purchase_bill" if fields else "unknown"
    return fields, conf, doc_type


class OcrRulesBackend:
    name = "ocr_rules"

    async def extract(
        self,
        *,
        tenant_id: str,
        pages: list[PageImage],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            import pytesseract  # optional dependency
            from PIL import Image
        except Exception:
            return empty_result(engine=self.name, error_code="ocr_unavailable")

        texts: list[str] = []
        quality_samples: list[float] = []
        try:
            for page in pages:
                img = Image.open(io.BytesIO(page.data))
                texts.append(pytesseract.image_to_string(img))
                data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                confs = [int(c) for c in data.get("conf", []) if str(c).lstrip("-").isdigit() and int(c) >= 0]
                if confs:
                    quality_samples.append(sum(confs) / len(confs) / 100.0)
        except Exception:
            return empty_result(engine=self.name, error_code="ocr_failed")

        text = "\n".join(texts)
        page_quality = min(quality_samples) if quality_samples else 0.6
        fields, conf, doc_type = _structure(text, page_quality)
        return {
            "extracted": bool(fields),
            "document_type": doc_type,
            "fields": fields,
            "field_confidences": conf,
            "engine": self.name,
            "provider": "tesseract",
            "model": "tesseract",
            "error_code": None if fields else "no_fields_found",
            "telemetry_id": None,
            "page_quality": round(page_quality, 3),
        }
