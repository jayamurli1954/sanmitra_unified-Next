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

1. Seed the dedicated demo firm (local Mongo):

```powershell
python scripts/seed_mis_demo_firm.py --password "ChangeMe123!"
```

Creates tenant `demo-mfg-mis` ("SanMitra Demo Manufacturing Pvt Ltd"), maker + checker users,
enables MIS flags, and loads a draft manufacturing pack for `2026-07`.

2. Or generate Excel only, then import manually in OfficeMitra:

```powershell
python tools/sanmitra-demo-data-generator/generate_mis_pack.py --industry manufacturing --period 2026-07 --size medium
```

3. OfficeMitra AI → **MIS Packs** → select pack → review dashboard → reconcile → checker approves in **Proposals**.

## Not yet included

- Full GL / 50k bank rows / MitraBooks voucher import ZIP (planned as a separate seeder step).
- Live MitraBooks → MIS connector (ADR-014 step 8).
