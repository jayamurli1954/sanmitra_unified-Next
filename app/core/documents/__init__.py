"""Shared document-PDF layer.

A single reportlab-based renderer for branded business documents (invoices,
receipts, bills, credit/debit notes) across the SanMitra apps. Each app maps its
domain object into a ``DocumentSpec`` and calls ``render_document_pdf`` — the
renderer stays dumb and reusable, the app owns the mapping.

Phase 1 wires only the MitraBooks sales invoice; MandirMitra receipts and
GruhaMitra bills can migrate onto the same renderer later without changing it.
"""
from app.core.documents.spec import (
    DocumentColumn,
    DocumentLine,
    DocumentParty,
    DocumentSpec,
    TotalRow,
)
from app.core.documents.pdf import render_document_pdf

__all__ = [
    "DocumentColumn",
    "DocumentLine",
    "DocumentParty",
    "DocumentSpec",
    "TotalRow",
    "render_document_pdf",
]
