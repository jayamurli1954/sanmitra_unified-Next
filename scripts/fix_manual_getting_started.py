#!/usr/bin/env python3
"""Reconcile the manual's Getting Started / Dashboard sections to the live UI.

Fixes three drift points in docs/MitraBooks_User_Manual.docx:
  - 2.2 Workspace Layout  : adds the missing "three areas" bullet list.
  - 2.3 Navigation Groups : adds the actual sidebar groups (from app.js).
  - 3.  Dashboard         : replaces the stale widget list with the live
                            dashboard panels (KPIs, trend, CEO Insights, Books
                            Health) and updates the Financial Health note.

Idempotent: skips 2.2/2.3 if their lists already exist; rebuilds the 3. list.
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "MitraBooks_User_Manual.docx"
ASSET_COPY = ROOT / "frontend" / "assets" / "mitrabooks" / "MitraBooks_User_Manual.docx"
BULLET_NUMID = 4

THREE_AREAS = [
    [("Left sidebar", True), (" — navigation grouped by function (Main Workspaces, Core "
        "Ledger, Income, Expenses, Banking, Taxes, Reports, HR, Manufacturing and more).", False)],
    [("Top bar", True), (" — the business/entity selector, Active Period, the Books Health "
        "indicator, quick actions (Journal Post, New Party) and the logged-in user.", False)],
    [("Main panel", True), (" — the active workspace: the Dashboard, a document form, a "
        "report or a module screen.", False)],
]

NAV_GROUPS = [
    "Main Workspaces", "Core Ledger", "Income (Sales)", "Expenses (Purchases)",
    "Banking & Treasury", "Taxes & Compliance", "Intelligence & Reports",
    "Human Resources", "Manufacturing", "Configuration & Extensions",
]

DASHBOARD_WIDGETS = [
    [("Key Performance Indicators", True), (" — Income, Expenses and Net Position "
        "(financial-year-to-date) tiles.", False)],
    [("Sales & Expenses Trend", True), (" — a monthly chart of invoiced sales against "
        "posted expenses.", False)],
    [("CEO Insights", True), (" — key operating figures computed live from posted entries "
        "(e.g. cash & bank coverage of vendor dues, outstanding receivables).", False)],
    [("Books Health", True), (" — the readiness indicator shown in the top bar.", False)],
]


def _set_bullet(p):
    pPr = p._p.get_or_add_pPr()
    numPr = OxmlElement("w:numPr")
    e_ilvl = OxmlElement("w:ilvl"); e_ilvl.set(qn("w:val"), "0")
    e_num = OxmlElement("w:numId"); e_num.set(qn("w:val"), str(BULLET_NUMID))
    numPr.append(e_ilvl); numPr.append(e_num)
    pPr.append(numPr)


def _bullet(doc, runs):
    p = doc.add_paragraph(style="List Paragraph")
    for text, bold in runs:
        r = p.add_run(text)
        if bold:
            r.bold = True
    _set_bullet(p)
    return p


def _find(doc, prefix):
    for p in doc.paragraphs:
        if p.text.strip().startswith(prefix):
            return p
    return None


def _insert_after(anchor, paras):
    for p in reversed(paras):
        anchor._p.addnext(p._p)


def _next_para(anchor):
    nxt = anchor._p.getnext()
    if nxt is not None and nxt.tag == qn("w:p"):
        return Paragraph(nxt, anchor._parent)
    return None


def fix_2_2(doc) -> bool:
    anchor = _find(doc, "The screen is divided into three areas")
    if anchor is None:
        return False
    nxt = _next_para(anchor)
    if nxt is not None and nxt.text.strip().startswith("Left sidebar"):
        return False  # already done
    _insert_after(anchor, [_bullet(doc, r) for r in THREE_AREAS])
    return True


def fix_2_3(doc) -> bool:
    anchor = _find(doc, "MitraBooks organises features into the following sidebar groups")
    if anchor is None:
        return False
    nxt = _next_para(anchor)
    if nxt is not None and nxt.text.strip().startswith("Main Workspaces"):
        return False
    _insert_after(anchor, [_bullet(doc, [(g, False)]) for g in NAV_GROUPS])
    return True


def fix_3(doc) -> bool:
    anchor = _find(doc, "Widgets displayed")
    if anchor is None:
        return False
    # Reword the lead-in.
    if anchor.runs:
        anchor.runs[0].text = "The workspace shows:"
        for r in anchor.runs[1:]:
            r.text = ""
    # Remove existing bullets between the lead-in and "Customising widgets".
    body = anchor._p.getparent()
    nxt = anchor._p.getnext()
    while nxt is not None and nxt.tag == qn("w:p"):
        para = Paragraph(nxt, anchor._parent)
        if para.text.strip().startswith("Customising"):
            break
        after = nxt.getnext()
        body.remove(nxt)
        nxt = after
    # Insert the live panels.
    _insert_after(anchor, [_bullet(doc, r) for r in DASHBOARD_WIDGETS])
    # Refresh the Financial Health note (it is a live module now, not AI-gated).
    fh = _find(doc, "Financial Health panel")
    if fh is not None and fh.runs:
        fh.runs[0].text = ("Financial Health: a deeper CFO-style analysis is available at "
                           "Intelligence & Reports → Financial Health; every figure is "
                           "computed server-side from the posted ledger.")
        for r in fh.runs[1:]:
            r.text = ""
    return True


def main() -> None:
    doc = Document(str(MANUAL))
    changed = []
    if fix_2_2(doc): changed.append("2.2 Workspace Layout")
    if fix_2_3(doc): changed.append("2.3 Navigation Groups")
    if fix_3(doc): changed.append("3. Dashboard")
    if not changed:
        print("Nothing to change (already reconciled).")
        return
    doc.save(str(MANUAL))
    print("Updated:", ", ".join(changed))
    if ASSET_COPY.parent.exists():
        import shutil
        shutil.copyfile(MANUAL, ASSET_COPY)
        print(f"Synced {ASSET_COPY.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
