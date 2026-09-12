#!/usr/bin/env python3
"""Rebuild the cached Table of Contents in MitraBooks_User_Manual.docx.

Word stores TOC results as a content-control field. Adding Heading 1/2
sections does not update that cache until Word refreshes the field. This
script writes the TOC entries from the live headings so HR, Manufacturing,
and OfficeMitra appear immediately after CA Practice Portal.
"""
from __future__ import annotations

import shutil
import zipfile
from copy import deepcopy
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "MitraBooks_User_Manual.docx"
ASSET_COPY = ROOT / "frontend" / "assets" / "mitrabooks" / "MitraBooks_User_Manual.docx"

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NSMAP = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

HEADING_STYLES = {
    "Heading1": "TOC1",
    "Heading2": "TOC2",
    "Heading3": "TOC3",
}

# Fallback page numbers when Word cannot paginate. Existing titles keep
# their previous TOC pages; new optional-feature sections continue after 21.
KNOWN_PAGES = {
    "1. Introduction": "4",
    "2. Getting Started": "4",
    "2.1 Logging In": "4",
    "2.2 Workspace Layout": "4",
    "2.3 Navigation Groups": "4",
    "3. Dashboard": "5",
    "4. Parties (Customers & Vendors)": "5",
    "4.1 Adding a Party": "5",
    "4.2 Editing a Party": "5",
    "4.3 Party Subledger": "6",
    "5. Sales — Invoices": "7",
    "5.1 Creating a Sales Invoice": "7",
    "5.2 Composition Dealer — Bill of Supply": "7",
    "5.3 Invoice List": "7",
    "5.4 e-Invoice (IRN)": "7",
    "6. Sales — Credit Notes": "8",
    "6.1 Creating a Credit Note": "8",
    "7. Purchases — Vendor Bills": "8",
    "7.1 Creating a Vendor Bill": "8",
    "7.2 Debit Notes": "8",
    "8. Payment Allocation": "8",
    "8.1 Allocating a Payment": "9",
    "8.2 Reversing an Allocation": "9",
    "9. Banking — Bank Reconciliation": "10",
    "9.1 Uploading a Bank Statement": "10",
    "9.2 Matching Transactions": "10",
    "9.3 Bank Reconciliation Statement (BRS)": "10",
    "10. Compliance — GST Returns": "11",
    "10.1 GSTR-3B (Monthly Summary)": "11",
    "10.2 GSTR-1 (Outward Supply Details)": "11",
    "10.3 GSTR-2B / ITC Reconciliation": "11",
    "10.4 CMP-08 (Composition Quarterly Statement)": "11",
    "10.5 GSTR-4 (Annual Composition Return)": "12",
    "10.6 GST Settlement": "12",
    "10.7 ITC Reversals (Rule 37)": "12",
    "11. Compliance — TDS / TCS": "13",
    "11.1 TDS on Purchases": "13",
    "11.2 TCS on Sales": "13",
    "11.3 TDS / TCS Register": "13",
    "12. Accounting — Core Ledger & Journal Posts": "14",
    "12.1 Core Ledger (Chart of Accounts)": "14",
    "12.2 Manual Journal Post": "14",
    "12.3 Audit Trails": "14",
    "13. Financial Statements": "15",
    "13.1 Trial Balance": "15",
    "13.2 Profit & Loss": "15",
    "13.3 Balance Sheet": "15",
    "13.4 General Ledger": "15",
    "13.5 Receivables / Payables": "15",
    "13.6 AR / AP Aging": "16",
    "14. Statements & Dunning": "16",
    "14.1 Customer / Vendor Statement": "16",
    "14.2 Dunning Letters": "16",
    "15. Period Locks": "16",
    "16. Opening Balances & Year-End Close": "18",
    "16.1 Uploading Opening Balances": "18",
    "16.2 Year-End Close": "18",
    "17. Fixed Assets": "18",
    "17.1 Asset Register": "18",
    "17.2 Running Depreciation": "19",
    "18. Accounting Dimensions": "19",
    "18.1 Setting Up Dimensions": "19",
    "18.2 Dimension Report": "19",
    "19. Inventory (Optional)": "20",
    "19.1 Item Master": "20",
    "19.2 Stock Register": "20",
    "19.3 Closing Stock Entry": "20",
    "20. Settings": "20",
    "20.1 Invoice Settings": "20",
    "20.2 Numbering Pattern": "21",
    "21. CA Practice Portal": "21",
    "21.1 Inviting a Chartered Accountant (CA)": "21",
    "21.2 CA Login and Password Update Flow": "21",
    "21.3 Managing CA Invites": "21",
    "22. HR & Payroll (Optional add-on)": "22",
    "22.1 Activating HR & Payroll": "22",
    "22.2 Salary Structures": "22",
    "22.3 Adding an Employee": "22",
    "22.4 Appointment & Joining Letters": "22",
    "22.5 Running Payroll": "23",
    "22.6 Leave Management": "23",
    "22.7 Form 12BB (Investment Declarations)": "23",
    "22.8 Full & Final Settlement": "23",
    "22.9 Analytics": "23",
    "23. Manufacturing & Cost Centres (Optional add-on)": "24",
    "23.1 Activating the Add-on": "24",
    "23.2 Cost Centres": "24",
    "23.3 Tagging Postings to a Cost Centre": "24",
    "23.4 Cost-Centre Budgets": "24",
    "23.5 Cost-Centre P&L": "25",
    "23.6 Bills of Materials (BOM)": "25",
    "23.7 Work Orders": "25",
    "23.8 How It Affects Stock and the Ledger": "25",
    "24. OfficeMitra AI (Optional module)": "26",
    "24.1 Opening the workspace": "26",
    "24.2 Tasks": "26",
    "24.3 Email Summary": "26",
    "24.4 Calendar (paste-in)": "26",
    "24.5 Meeting Notes": "27",
    "24.6 Notifications": "27",
    "24.7 Today Brief": "27",
    "24.8 Proposals (confirmation and checker)": "27",
    "24.9 MIS Packs (CA Analysis Pack)": "27",
    "24.10 Advisory and data boundaries": "27",
    "25. Workflow Tips": "28",
    "26. Common Errors & Fixes": "28",
    "27. Glossary": "29",
    "28. Support": "29",
}


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _para_text(p_el: etree._Element) -> str:
    return "".join(p_el.itertext()).strip()


def _heading_style(p_el: etree._Element) -> str | None:
    style = p_el.find(f"{W}pPr/{W}pStyle")
    if style is None:
        return None
    return style.get(f"{W}val")


def _toc_bookmark_name(p_el: etree._Element) -> str | None:
    for bm in p_el.findall(f"{W}bookmarkStart"):
        name = bm.get(f"{W}name") or ""
        if name.startswith("_Toc"):
            return name
    return None


def _max_bookmark_id(root: etree._Element) -> int:
    ids = []
    for bm in root.iter(f"{W}bookmarkStart"):
        raw = bm.get(f"{W}id")
        if raw and raw.isdigit():
            ids.append(int(raw))
    return max(ids) if ids else 0


def _max_toc_seq(root: etree._Element) -> int:
    seqs = []
    for bm in root.iter(f"{W}bookmarkStart"):
        name = bm.get(f"{W}name") or ""
        if name.startswith("_Toc") and name[4:].isdigit():
            seqs.append(int(name[4:]))
    return max(seqs) if seqs else 232456894


def _fix_heading_text(root: etree._Element) -> None:
    for t_el in root.iter(f"{W}t"):
        if not t_el.text:
            continue
        if "(Optional module) (Optional module)" in t_el.text:
            t_el.text = t_el.text.replace(
                "(Optional module) (Optional module)",
                "(Optional module)",
            )


def _ensure_toc_bookmark(
    p_el: etree._Element,
    *,
    bookmark_id: int,
    bookmark_name: str,
) -> None:
    if _toc_bookmark_name(p_el):
        return
    start = etree.Element(f"{W}bookmarkStart")
    start.set(f"{W}id", str(bookmark_id))
    start.set(f"{W}name", bookmark_name)
    end = etree.Element(f"{W}bookmarkEnd")
    end.set(f"{W}id", str(bookmark_id))
    p_pr = p_el.find(f"{W}pPr")
    insert_at = list(p_el).index(p_pr) + 1 if p_pr is not None else 0
    p_el.insert(insert_at, start)
    p_el.append(end)


def _collect_headings(root: etree._Element) -> list[tuple[etree._Element, str, str]]:
    found: list[tuple[etree._Element, str, str]] = []
    for p_el in root.iter(f"{W}p"):
        style = _heading_style(p_el)
        if style not in HEADING_STYLES:
            continue
        title = _para_text(p_el)
        if not title:
            continue
        found.append((p_el, style, title))
    return found


def _find_toc_sdt(root: etree._Element) -> etree._Element:
    for sdt in root.iter(f"{W}sdt"):
        alias = sdt.find(f".//{W}alias")
        if alias is not None and alias.get(f"{W}val") == "Table of Contents":
            return sdt
    raise SystemExit("Table of Contents content control not found")


def _make_toc_para(
    template: etree._Element,
    *,
    toc_style: str,
    title: str,
    bookmark: str,
    page: str,
    include_field_start: bool,
) -> etree._Element:
    para = deepcopy(template)
    style = para.find(f"{W}pPr/{W}pStyle")
    if style is not None:
        style.set(f"{W}val", toc_style)

    hyperlink = para.find(f"{W}hyperlink")
    if hyperlink is None:
        raise SystemExit("TOC template is missing a hyperlink")
    hyperlink.set(f"{W}anchor", bookmark)

    title_set = False
    page_set = False
    for child in list(hyperlink):
        instr = child.find(f"{W}instrText")
        if instr is not None and instr.text and "PAGEREF" in instr.text:
            instr.text = f" PAGEREF {bookmark} \\h "
            continue
        text_el = child.find(f"{W}t")
        if text_el is None:
            continue
        if not title_set:
            text_el.text = title
            title_set = True
        elif not page_set:
            text_el.text = page
            page_set = True

    if include_field_start:
        return para

    # Body TOC rows must not repeat the TOC field begin/instr/separate.
    for child in list(para):
        if _local(child.tag) == "hyperlink":
            continue
        if _local(child.tag) == "pPr":
            continue
        para.remove(child)
    return para


def _rebuild_toc(root: etree._Element, headings: list[tuple[etree._Element, str, str]]) -> list[str]:
    sdt = _find_toc_sdt(root)
    content = sdt.find(f"{W}sdtContent")
    if content is None:
        raise SystemExit("TOC sdtContent missing")

    paras = content.findall(f"{W}p")
    if len(paras) < 3:
        raise SystemExit(f"Unexpected TOC paragraph count: {len(paras)}")

    first_template = paras[0]
    body_template = paras[1]
    end_para = paras[-1]

    new_children: list[etree._Element] = []
    titles: list[str] = []
    for index, (p_el, heading_style, title) in enumerate(headings):
        bookmark = _toc_bookmark_name(p_el)
        if not bookmark:
            raise SystemExit(f"Heading missing TOC bookmark: {title}")
        page = KNOWN_PAGES.get(title, "21")
        para = _make_toc_para(
            first_template if index == 0 else body_template,
            toc_style=HEADING_STYLES[heading_style],
            title=title,
            bookmark=bookmark,
            page=page,
            include_field_start=(index == 0),
        )
        new_children.append(para)
        titles.append(title)

    new_children.append(deepcopy(end_para))
    for child in list(content):
        content.remove(child)
    for child in new_children:
        content.append(child)
    return titles


def _rewrite_document_xml(xml_bytes: bytes) -> tuple[bytes, list[str]]:
    root = etree.fromstring(xml_bytes)
    _fix_heading_text(root)

    headings = _collect_headings(root)
    next_id = _max_bookmark_id(root) + 1
    next_toc = _max_toc_seq(root) + 1
    for p_el, _style, _title in headings:
        if _toc_bookmark_name(p_el):
            continue
        _ensure_toc_bookmark(
            p_el,
            bookmark_id=next_id,
            bookmark_name=f"_Toc{next_toc}",
        )
        next_id += 1
        next_toc += 1

    titles = _rebuild_toc(root, headings)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True), titles


def _rewrite_docx(path: Path) -> list[str]:
    tmp_path = path.with_suffix(path.suffix + ".toc.tmp")
    titles: list[str] = []
    with zipfile.ZipFile(path, "r") as zin, zipfile.ZipFile(
        tmp_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                data, titles = _rewrite_document_xml(data)
            zout.writestr(item, data)
    tmp_path.replace(path)
    return titles


def _try_word_update(path: Path) -> bool:
    try:
        import win32com.client  # type: ignore
    except ImportError:
        return False
    word = None
    doc = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(str(path.resolve()), ReadOnly=False, AddToRecentFiles=False)
        if doc.TablesOfContents.Count >= 1:
            doc.TablesOfContents(1).Update()
        doc.Save()
        return True
    except Exception as exc:
        print(f"Word TOC refresh skipped: {exc}")
        return False
    finally:
        if doc is not None:
            try:
                doc.Close(False)
            except Exception:
                pass
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass


def main() -> None:
    if not MANUAL.exists():
        raise SystemExit(f"Missing manual: {MANUAL}")
    titles = _rewrite_docx(MANUAL)
    word_updated = _try_word_update(MANUAL)
    ASSET_COPY.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MANUAL, ASSET_COPY)

    print(f"Rebuilt TOC with {len(titles)} entries in {MANUAL}")
    print(f"Synced copy: {ASSET_COPY}")
    print(f"Word field refresh: {'yes' if word_updated else 'no (cached page numbers written)'}")
    print("Entries from 21 onward:")
    for title in titles:
        if title.startswith(("21.", "22.", "23.", "24.", "25.", "26.", "27.", "28.")):
            print(f"  {title}")


if __name__ == "__main__":
    main()
