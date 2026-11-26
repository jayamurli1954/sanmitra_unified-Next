# Supreme Court judgment index (metadata only)

`sc_judgments.jsonl.gz` lists every Supreme Court of India judgment in the
public open dataset (1950 onwards, ~38k): parties, decision date, bench,
outcome, neutral citation (`2021 INSC 469`) and SCR citation. Judgment PDFs are
**not** stored here — LegalMitra links to them on the public bucket and they
are opened only when a user needs one.

Used by the Citation Checker and the Judgment Finder
(`app/modules/legal_compat/sc_judgment_index.py`).

## Source and licence

Judgment data: Dattam Labs, *Indian Supreme Court Judgments*, AWS Open Data
Registry — <https://registry.opendata.aws/indian-supreme-court-judgments/> —
licensed **CC BY 4.0**. Attribution must stay visible wherever this data is
shown (the API returns it as `attribution`).

The dataset carries SCR and neutral citations only. SCC / AIR citations are
proprietary reporters and are not included.

## Refresh

The source updates roughly every two months. To rebuild:

```bash
pip install pyarrow
python scripts/build_sc_judgment_index.py            # all years
python scripts/build_sc_judgment_index.py --from-year 2025   # quick partial check
```

Commit the regenerated `sc_judgments.jsonl.gz` and `manifest.json`.
Note: a partial-year run overwrites the file with only those years.
