---
name: gst-return-prep
description: Prepare and sanity-check Indian GST returns from MitraBooks - GSTR-1 and GSTR-3B for regular dealers, CMP-08 and GSTR-4 for composition dealers - and summarise them for the user or their CA. Use when the user asks about GST returns, GSTR-1, GSTR-3B, CMP-08, GSTR-4, GST payable or ITC for a period in MitraBooks.
---

# MitraBooks GST return preparation

MitraBooks computes returns from the posted books. Your job is to fetch them, check them
against each other, and explain them in plain language. You do not file anything; filing
happens on the GST portal.

## Which returns
- **Regular dealer:** monthly `get_gstr1(period)` and `get_gstr3b(period)`, period = YYYY-MM.
- **Composition dealer:** quarterly `get_cmp08(quarter)` (YYYY-Qn, FY-start year, Q1 = Apr-Jun)
  and annual `get_gstr4(financial_year)` (YYYY-YY).

If you do not know which scheme applies, call `get_gstr3b` first; a composition company's
data will show it, or ask the user.

## Regular dealer steps
1. `get_gstr1(period)` - outward supplies by section (B2B, B2CL, B2CS, credit/debit notes,
   HSN summary, document summary).
2. `get_gstr3b(period)` - 3.1 outward supplies and tax, 4 ITC, 6.1 tax payable.
3. **Cross-check:** taxable value and output tax in GSTR-1 should agree with 3B table 3.1
   (after credit/debit notes). Report any difference with the amounts on both sides.
4. **Data checks** from the GSTR-1 detail: B2B invoices without a GSTIN, HSN rows with UQC
   "OTH", inter-state vs intra-state tax heads that look inconsistent with place of supply.
5. **ITC:** report eligible ITC from 3B table 4. Remind the user that ITC claimed should be
   matched with their GSTR-2B (MitraBooks has a GSTR-2B reconciliation screen under GST Returns
   for this; it needs the 2B file downloaded from the portal).
6. **Before the period is filed,** run `get_data_health` for the period end: draft or stuck
   sales invoices and purchase bills are missing from the return.

## Composition dealer steps
1. `get_cmp08(quarter)` - turnover and tax payable for the quarter.
2. For the year, `get_gstr4(financial_year)`; check that its quarterly figures agree with the
   four CMP-08 statements.

## Output
- One-paragraph summary: period, outward taxable value, output tax by head (IGST/CGST/SGST/cess),
  ITC available, net tax payable - all from the tool results.
- A table of GSTR-1 vs 3B differences (or "none").
- A list of data issues to fix in MitraBooks before filing.
- Tell the user the GSTN-format JSON is in the tool result / MitraBooks GST Returns screen for
  upload to the portal.

Never state a GST rate, threshold or due date from memory as fact - these change. Use only what
the tools return, and ask the user to confirm current due dates on the GST portal.
