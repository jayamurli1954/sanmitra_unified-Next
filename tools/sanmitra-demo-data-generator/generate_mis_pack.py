#!/usr/bin/env python3
"""
SanMitra Demo Data Generator — ADR-014 MIS pack Excel (outside MitraBooks ERP).

Produces a SanMitra CA MIS template workbook that OfficeMitra can import via:
  POST /api/v1/officemitra/mis/packs/{pack_id}/import/excel?persist=true

This tool does NOT write into MitraBooks or Mongo. It only emits files under ./output/.

Usage:
  python tools/sanmitra-demo-data-generator/generate_mis_pack.py
  python tools/sanmitra-demo-data-generator/generate_mis_pack.py --industry manufacturing --period 2026-07 --size medium
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"

INDUSTRY_PROFILES: dict[str, dict[str, Any]] = {
    "manufacturing": {
        "pack_key": "manufacturing",
        "company": "SanMitra Demo Manufacturing Pvt Ltd",
        "revenue_base": Decimal("18500000"),
        "cogs_ratio": Decimal("0.62"),
        "opex_ratio": Decimal("0.18"),
    },
    "services": {
        "pack_key": "professional_services",
        "company": "SanMitra Demo Services LLP",
        "revenue_base": Decimal("9200000"),
        "cogs_ratio": Decimal("0.28"),
        "opex_ratio": Decimal("0.42"),
    },
    "ca_practice": {
        "pack_key": "ca_practice",
        "company": "SanMitra Demo CA Practice",
        "revenue_base": Decimal("4800000"),
        "cogs_ratio": Decimal("0.12"),
        "opex_ratio": Decimal("0.55"),
    },
    "housing": {
        "pack_key": "housing",
        "company": "SanMitra Demo Housing Society",
        "revenue_base": Decimal("3600000"),
        "cogs_ratio": Decimal("0.05"),
        "opex_ratio": Decimal("0.78"),
    },
    "temple": {
        "pack_key": "temple",
        "company": "SanMitra Demo Temple Trust",
        "revenue_base": Decimal("6100000"),
        "cogs_ratio": Decimal("0.08"),
        "opex_ratio": Decimal("0.65"),
    },
    "sme_general": {
        "pack_key": "sme_general",
        "company": "SanMitra Demo Trading Co",
        "revenue_base": Decimal("12400000"),
        "cogs_ratio": Decimal("0.71"),
        "opex_ratio": Decimal("0.16"),
    },
}

SIZE_PRESETS = {
    "small": {"customers": 80, "vendors": 30, "months": 6},
    "medium": {"customers": 500, "vendors": 150, "months": 12},
    "large": {"customers": 2000, "vendors": 500, "months": 24},
}


def money(value: Decimal | float | int) -> str:
    return format(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")


def money_d(value: Decimal | float | int) -> Decimal:
    return Decimal(money(value))


def dims(**kwargs: Any) -> str:
    return json.dumps(kwargs, separators=(",", ":"), ensure_ascii=True)


def fact_row(
    *,
    entity_type: str,
    source_ref: str,
    period: str | None = None,
    as_of: str | None = None,
    amount: Decimal | float | int | None = None,
    value: Any = None,
    dimensions: dict[str, Any] | None = None,
    source_id: str | None = None,
    currency: str = "INR",
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "entity_type": entity_type,
        "period": period or "",
        "as_of": as_of or "",
        "source_system": "demo_generator",
        "source_id": source_id or "",
        "source_ref": source_ref,
        "amount_decimal": money(amount) if amount is not None else "",
        "value": "" if value is None else value,
        "currency": currency,
        "dimensions_json": dims(**(dimensions or {})),
    }
    return row


def build_mis_facts(
    *,
    industry: str,
    period: str,
    size: str,
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rng = random.Random(seed)
    profile = INDUSTRY_PROFILES[industry]
    preset = SIZE_PRESETS[size]
    company = profile["company"]
    as_of = f"{period}-28" if len(period) == 7 else period

    revenue = money_d(profile["revenue_base"] * Decimal(str(0.92 + rng.random() * 0.16)))
    cogs = money_d(revenue * profile["cogs_ratio"])
    opex = money_d(revenue * profile["opex_ratio"])
    gp = money_d(revenue - cogs)
    ebit = money_d(gp - opex)
    tax = money_d(max(Decimal("0"), ebit * Decimal("0.25")))
    pat = money_d(ebit - tax)

    cash = money_d(revenue * Decimal("0.08") + Decimal(rng.randint(200000, 900000)))
    bank = money_d(revenue * Decimal("0.12") + Decimal(rng.randint(400000, 1500000)))
    ar = money_d(revenue * Decimal("0.18"))
    inventory = money_d(revenue * Decimal("0.11")) if industry == "manufacturing" else money_d(revenue * Decimal("0.04"))
    ap = money_d(cogs * Decimal("0.22"))
    equity = money_d(cash + bank + ar + inventory - ap + Decimal(rng.randint(500000, 2500000)))

    # Seasonal shock for narrative testing: last third of year weaker.
    seasonal = Decimal("0.78") if period.endswith(("-10", "-11", "-12")) else Decimal("1.0")
    revenue = money_d(revenue * seasonal)
    cogs = money_d(cogs * seasonal)
    gp = money_d(revenue - cogs)
    opex = money_d(opex)
    ebit = money_d(gp - opex)
    tax = money_d(max(Decimal("0"), ebit * Decimal("0.25")))
    pat = money_d(ebit - tax)

    ar_current = money_d(ar * Decimal("0.48"))
    ar_1_30 = money_d(ar * Decimal("0.22"))
    ar_31_60 = money_d(ar * Decimal("0.14"))
    ar_61_90 = money_d(ar * Decimal("0.09"))
    ar_90_plus = money_d(ar - ar_current - ar_1_30 - ar_31_60 - ar_61_90)

    ap_current = money_d(ap * Decimal("0.55"))
    ap_1_30 = money_d(ap * Decimal("0.20"))
    ap_31_60 = money_d(ap * Decimal("0.12"))
    ap_61_90 = money_d(ap * Decimal("0.08"))
    ap_90_plus = money_d(ap - ap_current - ap_1_30 - ap_31_60 - ap_61_90)

    dso = round(float((ar / revenue) * Decimal("30") * Decimal("12")), 1)
    dpo = round(float((ap / max(cogs, Decimal("1"))) * Decimal("30") * Decimal("12")), 1)
    gp_pct = round(float((gp / max(revenue, Decimal("1"))) * Decimal("100")), 1)
    current_ratio = round(float((cash + bank + ar + inventory) / max(ap, Decimal("1"))), 2)
    cash_runway_months = round(float((cash + bank) / max(opex / Decimal("12"), Decimal("1"))), 1)

    facts: list[dict[str, Any]] = []

    # P&L
    for line, amount, code in [
        ("Revenue", revenue, "REV"),
        ("COGS", cogs, "COGS"),
        ("Gross Profit", gp, "GP"),
        ("Operating Expenses", opex, "OPEX"),
        ("EBIT", ebit, "EBIT"),
        ("Tax", tax, "TAX"),
        ("PAT", pat, "PAT"),
    ]:
        facts.append(
            fact_row(
                entity_type="pnl_line",
                period=period,
                amount=amount,
                source_ref=f"PnL!{code}",
                source_id=f"pnl-{code.lower()}",
                dimensions={"line": line, "company": company, "industry": industry},
            )
        )

    # Balance sheet
    for line, amount, code in [
        ("Cash", cash, "CASH"),
        ("Bank", bank, "BANK"),
        ("Accounts Receivable", ar, "AR"),
        ("Inventory", inventory, "INV"),
        ("Accounts Payable", ap, "AP"),
        ("Equity", equity, "EQ"),
    ]:
        facts.append(
            fact_row(
                entity_type="bs_line",
                period=period,
                as_of=as_of,
                amount=amount,
                source_ref=f"BS!{code}",
                source_id=f"bs-{code.lower()}",
                dimensions={"line": line, "company": company},
            )
        )

    # Cash summary
    ops = money_d(pat + Decimal(rng.randint(50000, 250000)))
    investing = money_d(Decimal(rng.randint(-400000, -80000)))
    financing = money_d(Decimal(rng.randint(-150000, 200000)))
    for line, amount, code in [
        ("Operating", ops, "CFO"),
        ("Investing", investing, "CFI"),
        ("Financing", financing, "CFF"),
        ("Net Change", money_d(ops + investing + financing), "NET"),
    ]:
        facts.append(
            fact_row(
                entity_type="cash_summary",
                period=period,
                amount=amount,
                source_ref=f"CF!{code}",
                source_id=f"cf-{code.lower()}",
                dimensions={"line": line, "company": company},
            )
        )

    # Ageing
    for bucket, amount in [
        ("Current", ar_current),
        ("1-30", ar_1_30),
        ("31-60", ar_31_60),
        ("61-90", ar_61_90),
        ("90+", ar_90_plus),
    ]:
        facts.append(
            fact_row(
                entity_type="aging_bucket",
                period=period,
                as_of=as_of,
                amount=amount,
                source_ref=f"AR!{bucket}",
                source_id=f"ar-{bucket.lower().replace('+', 'plus')}",
                dimensions={"side": "AR", "bucket": bucket, "company": company},
            )
        )
    for bucket, amount in [
        ("Current", ap_current),
        ("1-30", ap_1_30),
        ("31-60", ap_31_60),
        ("61-90", ap_61_90),
        ("90+", ap_90_plus),
    ]:
        facts.append(
            fact_row(
                entity_type="aging_bucket",
                period=period,
                as_of=as_of,
                amount=amount,
                source_ref=f"AP!{bucket}",
                source_id=f"ap-{bucket.lower().replace('+', 'plus')}",
                dimensions={"side": "AP", "bucket": bucket, "company": company},
            )
        )

    # KPIs
    for name, value, unit in [
        ("DSO", dso, "days"),
        ("DPO", dpo, "days"),
        ("GrossMarginPct", gp_pct, "percent"),
        ("CurrentRatio", current_ratio, "ratio"),
        ("CashRunwayMonths", cash_runway_months, "months"),
        ("Revenue", float(revenue), "INR"),
        ("PAT", float(pat), "INR"),
        ("CashAndBank", float(cash + bank), "INR"),
    ]:
        facts.append(
            fact_row(
                entity_type="kpi",
                period=period,
                as_of=as_of,
                value=value,
                source_ref=f"KPI!{name}",
                source_id=f"kpi-{name.lower()}",
                dimensions={"kpi": name, "unit": unit, "company": company},
            )
        )

    # Party concentration (top overdue customers / vendors)
    for i in range(5):
        facts.append(
            fact_row(
                entity_type="party",
                period=period,
                as_of=as_of,
                value=float(money_d(ar_90_plus * Decimal(str(0.35 - i * 0.05)))),
                source_ref=f"Party!CUST{i+1:03d}",
                source_id=f"party-ar-{i+1}",
                dimensions={
                    "party_type": "customer",
                    "party_code": f"CUST{i+1:03d}",
                    "name": f"Demo Customer {i+1}",
                    "metric": "overdue_ar",
                },
            )
        )
    for i in range(3):
        facts.append(
            fact_row(
                entity_type="party",
                period=period,
                as_of=as_of,
                value=float(money_d(ap_90_plus * Decimal(str(0.40 - i * 0.08)))),
                source_ref=f"Party!VEND{i+1:03d}",
                source_id=f"party-ap-{i+1}",
                dimensions={
                    "party_type": "vendor",
                    "party_code": f"VEND{i+1:03d}",
                    "name": f"Demo Vendor {i+1}",
                    "metric": "overdue_ap",
                },
            )
        )

    # Multi-month PnL trend for dashboard charts (derived summary only).
    year = int(period[:4]) if len(period) >= 4 and period[:4].isdigit() else date.today().year
    month = int(period[5:7]) if len(period) >= 7 and period[5:7].isdigit() else 7
    for back in range(1, min(preset["months"], 12)):
        m = month - back
        y = year
        while m <= 0:
            m += 12
            y -= 1
        p = f"{y:04d}-{m:02d}"
        factor = Decimal(str(0.85 + rng.random() * 0.30))
        rev_m = money_d(profile["revenue_base"] * Decimal("0.08") * factor)
        cogs_m = money_d(rev_m * profile["cogs_ratio"])
        facts.append(
            fact_row(
                entity_type="pnl_line",
                period=p,
                amount=rev_m,
                source_ref=f"PnLTrend!REV!{p}",
                source_id=f"pnl-trend-rev-{p}",
                dimensions={"line": "Revenue", "company": company, "trend": True},
            )
        )
        facts.append(
            fact_row(
                entity_type="pnl_line",
                period=p,
                amount=money_d(rev_m - cogs_m),
                source_ref=f"PnLTrend!GP!{p}",
                source_id=f"pnl-trend-gp-{p}",
                dimensions={"line": "Gross Profit", "company": company, "trend": True},
            )
        )

    meta = {
        "industry": industry,
        "pack_key": profile["pack_key"],
        "company": company,
        "period": period,
        "as_of": as_of,
        "size": size,
        "seed": seed,
        "fact_count": len(facts),
        "customers_planned": preset["customers"],
        "vendors_planned": preset["vendors"],
        "kpis": {
            "DSO": dso,
            "DPO": dpo,
            "GrossMarginPct": gp_pct,
            "CurrentRatio": current_ratio,
            "CashRunwayMonths": cash_runway_months,
        },
    }
    return facts, meta


def write_xlsx(facts: list[dict[str, Any]], path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "MIS_FACTS"
    headers = [
        "entity_type",
        "period",
        "as_of",
        "source_system",
        "source_id",
        "source_ref",
        "amount_decimal",
        "value",
        "currency",
        "dimensions_json",
    ]
    ws.append(headers)
    for row in facts:
        ws.append([row.get(h, "") for h in headers])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def write_party_csvs(*, industry: str, size: str, seed: int, out_dir: Path) -> None:
    """Optional ERP-import masters (not used by MIS Excel import yet)."""
    rng = random.Random(seed + 17)
    preset = SIZE_PRESETS[size]
    customers = []
    for i in range(preset["customers"]):
        customers.append(
            {
                "customer_code": f"CUST{i+1:05d}",
                "name": f"{industry.title()} Customer {i+1}",
                "city": rng.choice(["Bengaluru", "Chennai", "Hyderabad", "Pune", "Mumbai", "Delhi"]),
                "credit_days": rng.choice([15, 30, 45, 60]),
                "gstin": f"29AAAAA{i+1:05d}A1Z{i % 10}",
            }
        )
    vendors = []
    for i in range(preset["vendors"]):
        vendors.append(
            {
                "vendor_code": f"VEND{i+1:05d}",
                "name": f"{industry.title()} Vendor {i+1}",
                "city": rng.choice(["Bengaluru", "Coimbatore", "Ahmedabad", "Surat", "Jaipur"]),
                "credit_days": rng.choice([15, 30, 45]),
                "gstin": f"27BBBBB{i+1:05d}B1Z{i % 10}",
            }
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "customers.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(customers[0].keys()))
        writer.writeheader()
        writer.writerows(customers)
    with (out_dir / "vendors.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(vendors[0].keys()))
        writer.writeheader()
        writer.writerows(vendors)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate ADR-014 MIS demo Excel (outside ERP).")
    p.add_argument(
        "--industry",
        default="manufacturing",
        choices=sorted(INDUSTRY_PROFILES.keys()),
        help="Demo industry / metric-pack profile",
    )
    p.add_argument("--period", default="2026-07", help="Primary pack period (YYYY-MM)")
    p.add_argument("--size", default="medium", choices=sorted(SIZE_PRESETS.keys()))
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--with-masters",
        action="store_true",
        help="Also write customers.csv / vendors.csv for future MitraBooks demo seeder",
    )
    p.add_argument(
        "--out-dir",
        default=str(OUTPUT_DIR),
        help="Output directory (default: tools/sanmitra-demo-data-generator/output)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    facts, meta = build_mis_facts(
        industry=args.industry,
        period=args.period,
        size=args.size,
        seed=args.seed,
    )
    stem = f"mis_{args.industry}_{args.period}_{args.size}"
    xlsx_path = out_dir / f"{stem}.xlsx"
    meta_path = out_dir / f"{stem}.meta.json"
    write_xlsx(facts, xlsx_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    if args.with_masters:
        write_party_csvs(industry=args.industry, size=args.size, seed=args.seed, out_dir=out_dir / f"{stem}_masters")

    print(f"Wrote {xlsx_path}")
    print(f"Wrote {meta_path}")
    print(f"Facts: {meta['fact_count']} | pack_key={meta['pack_key']} | company={meta['company']}")
    print("Import into OfficeMitra: create MIS pack -> Import Excel -> persist -> reconcile.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
