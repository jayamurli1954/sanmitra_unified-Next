# SanMitra Demo Data Generator

**Outside MitraBooks ERP.** This tool only writes files; it does not touch product Mongo/Postgres tables.

## Purpose

Generate ADR-014-compatible **MIS_FACTS** Excel for OfficeMitra CA Analysis Pack testing:

- P&L / Balance Sheet / Cash Flow summary lines
- AR & AP ageing buckets
- KPIs (DSO, DPO, margin, current ratio, cash runway)
- Party concentration samples
- Multi-month revenue/GP trend rows for dashboard widgets

## Generate

```powershell
cd D:\sanmitra_unified-Next
python tools/sanmitra-demo-data-generator/generate_mis_pack.py --industry manufacturing --period 2026-07 --size medium
```

Optional party masters for a future MitraBooks demo seeder:

```powershell
python tools/sanmitra-demo-data-generator/generate_mis_pack.py --industry ca_practice --with-masters
```

## Industries

| Flag | ADR-014 pack_key |
| --- | --- |
| `manufacturing` | manufacturing |
| `services` | professional_services |
| `ca_practice` | ca_practice |
| `housing` | housing |
| `temple` | temple |
| `sme_general` | sme_general |

## Import path (current)

1. Enable `office_ai.mis` (+ `.import` / `.export` as needed) on a demo tenant.
2. OfficeMitra AI → **MIS Packs** → create pack for the same period.
3. Upload the generated `.xlsx` with **Persist valid rows**.
4. Submit reconcile → checker approves in **Proposals**.
5. Dashboard strip on the MIS tab shows KPI tiles + AR/AP ageing from imported facts.

## Not yet included

- Full GL / 50k bank rows / MitraBooks voucher import ZIP (planned as a separate seeder step).
- Live MitraBooks → MIS connector (ADR-014 step 8).
