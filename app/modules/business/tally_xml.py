"""Tally XML export proof of concept for MitraBooks reports."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from xml.sax.saxutils import escape


def _amount(value) -> Decimal:
    try:
        return Decimal(str(value or "0")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def _xml_text(value) -> str:
    return escape(str(value or ""), {'"': "&quot;", "'": "&apos;"})


def _signed_closing(row: dict) -> Decimal:
    debit = _amount(row.get("debit"))
    credit = _amount(row.get("credit"))
    return debit - credit


def _tally_group(row: dict) -> str:
    name = str(row.get("account_name") or "").lower()
    code = str(row.get("account_code") or "")
    if "cash" in name or "bank" in name or code.startswith(("10", "11")):
        return "Bank Accounts" if "bank" in name else "Cash-in-Hand"
    if "debtor" in name or code.startswith("12"):
        return "Sundry Debtors"
    if "creditor" in name or code.startswith("21"):
        return "Sundry Creditors"
    if "sales" in name or code.startswith("4"):
        return "Sales Accounts"
    if "purchase" in name or "expense" in name or code.startswith("5"):
        return "Indirect Expenses"
    if "capital" in name or "equity" in name or code.startswith("3"):
        return "Capital Account"
    return "Current Assets"


def build_trial_balance_tally_xml(*, spec: dict, company_name: str | None = None, as_of: str | None = None) -> bytes:
    """Build a Tally-compatible ledger-master envelope from a trial balance spec.

    This is intentionally a data-portability proof, not a live Tally sync. It
    exports ledger masters and closing balances derived from posted reports.
    """
    rows = spec.get("rows") or []
    company = company_name or spec.get("org_name") or "MitraBooks Export"
    meta = dict(spec.get("meta") or [])
    export_as_of = as_of or meta.get("As of") or ""
    ledger_messages = []
    for row in rows:
        name = row.get("account_name")
        if not name:
            continue
        closing = _signed_closing(row)
        ledger_messages.append(
            "\n".join([
                "<TALLYMESSAGE xmlns:UDF=\"TallyUDF\">",
                f"  <LEDGER NAME=\"{_xml_text(name)}\" ACTION=\"Create\">",
                f"    <NAME>{_xml_text(name)}</NAME>",
                f"    <PARENT>{_xml_text(_tally_group(row))}</PARENT>",
                "    <ISBILLWISEON>No</ISBILLWISEON>",
                "    <AFFECTSSTOCK>No</AFFECTSSTOCK>",
                f"    <OPENINGBALANCE>{closing}</OPENINGBALANCE>",
                f"    <SANMITRALEDGERCODE>{_xml_text(row.get('account_code'))}</SANMITRALEDGERCODE>",
                "  </LEDGER>",
                "</TALLYMESSAGE>",
            ])
        )
    xml = "\n".join([
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        "<ENVELOPE>",
        "  <HEADER>",
        "    <TALLYREQUEST>Import Data</TALLYREQUEST>",
        "  </HEADER>",
        "  <BODY>",
        "    <IMPORTDATA>",
        "      <REQUESTDESC>",
        "        <REPORTNAME>All Masters</REPORTNAME>",
        "        <STATICVARIABLES>",
        f"          <SVCURRENTCOMPANY>{_xml_text(company)}</SVCURRENTCOMPANY>",
        "        </STATICVARIABLES>",
        "      </REQUESTDESC>",
        "      <REQUESTDATA>",
        *[f"        {line}" for message in ledger_messages for line in message.splitlines()],
        "      </REQUESTDATA>",
        "    </IMPORTDATA>",
        "  </BODY>",
        f"  <SANMITRAEXPORT><SOURCE>trial_balance</SOURCE><ASOF>{_xml_text(export_as_of)}</ASOF></SANMITRAEXPORT>",
        "</ENVELOPE>",
        "",
    ])
    return xml.encode("utf-8")
