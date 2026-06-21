"""Data contract for the shared document renderer.

These are deliberately render-agnostic value objects: an app maps its domain
record into a ``DocumentSpec`` (deciding which columns/totals to show), and the
renderer turns it into PDF bytes. Keeping the columns app-decided is what lets a
composition "Bill of Supply" simply omit the GST columns while a regular tax
invoice includes them — without the renderer knowing anything about GST.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DocumentParty:
    """A named party block (seller or buyer)."""
    name: str
    address_lines: list[str] = field(default_factory=list)
    gstin: str | None = None


@dataclass
class DocumentColumn:
    key: str
    label: str
    align: str = "left"  # "left" | "right" | "center"
    weight: float = 1.0  # relative column width


@dataclass
class DocumentLine:
    """One row in the line-item table; cells keyed by column key."""
    cells: dict[str, str]


@dataclass
class TotalRow:
    label: str
    value: str
    emphasize: bool = False


@dataclass
class DocumentSpec:
    title: str                                    # e.g. "Tax Invoice" / "Bill of Supply"
    number: str
    seller: DocumentParty
    buyer: DocumentParty
    columns: list[DocumentColumn]
    lines: list[DocumentLine]
    totals: list[TotalRow] = field(default_factory=list)
    meta: list[tuple[str, str]] = field(default_factory=list)   # header key/value pairs
    buyer_heading: str = "Bill To"
    notes: str | None = None
    declaration: str | None = None
    footer_note: str | None = None
    page_size: str = "A4"
