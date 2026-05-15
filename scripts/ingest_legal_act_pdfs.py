import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF


sys.path.append(os.getcwd())

from app.db.mongo import close_mongo, init_mongo
from app.modules.rag.schemas import RagIngestRequest, RagLegalMetadata
from app.modules.rag.service import ensure_rag_indexes, ingest_document


TENANT_ID = "seed-tenant-1"
APP_KEY = "legalmitra"
CREATED_BY = "manual-act-ingest"
PDF_DIR = Path("data/legal_acts")


@dataclass(frozen=True)
class ActManifestEntry:
    key: str
    title: str
    pdf_filename: str
    external_id: str
    doc_date: str
    effective_date: str | None
    already_ingested: bool = False


ACTS: tuple[ActManifestEntry, ...] = (
    ActManifestEntry(
        key="constitution",
        title="Constitution of India",
        pdf_filename="constitution_of_india.pdf",
        external_id="official-constitution-of-india",
        doc_date="1949-11-26",
        effective_date="1950-01-26",
    ),
    ActManifestEntry(
        key="bns",
        title="Bharatiya Nyaya Sanhita, 2023",
        pdf_filename="bns_2023.pdf",
        external_id="official-bharatiya-nyaya-sanhita-2023",
        doc_date="2023-12-25",
        effective_date="2024-07-01",
        already_ingested=True,
    ),
    ActManifestEntry(
        key="bnss",
        title="Bharatiya Nagarik Suraksha Sanhita, 2023",
        pdf_filename="bnss_2023.pdf",
        external_id="official-bharatiya-nagarik-suraksha-sanhita-2023",
        doc_date="2023-12-25",
        effective_date="2024-07-01",
    ),
    ActManifestEntry(
        key="bsa",
        title="Bharatiya Sakshya Adhiniyam, 2023",
        pdf_filename="bsa_2023.pdf",
        external_id="official-bharatiya-sakshya-adhiniyam-2023",
        doc_date="2023-12-25",
        effective_date="2024-07-01",
    ),
    ActManifestEntry(
        key="cpc",
        title="Code of Civil Procedure, 1908",
        pdf_filename="cpc_1908.pdf",
        external_id="official-code-of-civil-procedure-1908",
        doc_date="1908-03-21",
        effective_date="1909-01-01",
    ),
    ActManifestEntry(
        key="contract",
        title="Indian Contract Act, 1872",
        pdf_filename="contract_act_1872.pdf",
        external_id="official-indian-contract-act-1872",
        doc_date="1872-04-18",
        effective_date="1872-09-01",
    ),
    ActManifestEntry(
        key="evidence",
        title="Indian Evidence Act, 1872",
        pdf_filename="indian_evidence_act_1872.pdf",
        external_id="official-indian-evidence-act-1872",
        doc_date="1872-07-17",
        effective_date="1872-09-01",
    ),
    ActManifestEntry(
        key="companies",
        title="Companies Act, 2013",
        pdf_filename="companies_act_2013.pdf",
        external_id="official-companies-act-2013",
        doc_date="2013-03-29",
        effective_date="2013-04-01",
    ),
    ActManifestEntry(
        key="llp",
        title="The Limited Liability Partnership Act, 2008",
        pdf_filename="limited_liability_partnership_act_2008.pdf",
        external_id="official-limited-liability-partnership-act-2008",
        doc_date="2009-01-07",
        effective_date="2009-03-31",
    ),
    ActManifestEntry(
        key="negotiable",
        title="Negotiable Instruments Act, 1881",
        pdf_filename="negotiable_instruments_act_1881.pdf",
        external_id="official-negotiable-instruments-act-1881",
        doc_date="1881-12-09",
        effective_date="1882-03-01",
    ),
    ActManifestEntry(
        key="ipc",
        title="Indian Penal Code, 1860",
        pdf_filename="ipc_1860.pdf",
        external_id="official-indian-penal-code-1860",
        doc_date="1860-10-06",
        effective_date="1862-01-01",
    ),
    ActManifestEntry(
        key="crpc",
        title="Code of Criminal Procedure, 1973",
        pdf_filename="crpc_1973.pdf",
        external_id="official-code-of-criminal-procedure-1973",
        doc_date="1973-12-25",
        effective_date="1974-04-01",
    ),
    ActManifestEntry(
        key="transfer",
        title="Transfer of Property Act, 1882",
        pdf_filename="transfer_of_property_act_1882.pdf",
        external_id="official-transfer-of-property-act-1882",
        doc_date="1882-12-09",
        effective_date="1883-07-01",
    ),
    ActManifestEntry(
        key="succession",
        title="Indian Succession Act, 1925",
        pdf_filename="indian_succession_act_1925.pdf",
        external_id="official-indian-succession-act-1925",
        doc_date="1925-01-20",
        effective_date="1925-07-01",
    ),
    ActManifestEntry(
        key="registration",
        title="Registration Act, 1908",
        pdf_filename="registration_act_1908.pdf",
        external_id="official-registration-act-1908",
        doc_date="1908-03-21",
        effective_date="1909-01-01",
    ),
    ActManifestEntry(
        key="limitation",
        title="Limitation Act, 1963",
        pdf_filename="limitation_act_1963.pdf",
        external_id="official-limitation-act-1963",
        doc_date="1963-12-25",
        effective_date="1964-01-01",
    ),
    ActManifestEntry(
        key="relief",
        title="Specific Relief Act, 1963",
        pdf_filename="specific_relief_act_1963.pdf",
        external_id="official-specific-relief-act-1963",
        doc_date="1963-12-25",
        effective_date="1964-01-01",
    ),
    ActManifestEntry(
        key="motor_vehicles",
        title="Motor Vehicles Act, 1988",
        pdf_filename="motor_vehicles_act_1988.pdf",
        external_id="official-motor-vehicles-act-1988",
        doc_date="1988-12-30",
        effective_date="1989-06-12",
    ),
    ActManifestEntry(
        key="hindu_marriage",
        title="Hindu Marriage Act, 1955",
        pdf_filename="hindu_marriage_act_1955.pdf",
        external_id="official-hindu-marriage-act-1955",
        doc_date="1955-05-18",
        effective_date="1956-01-01",
    ),
    ActManifestEntry(
        key="information_technology",
        title="Information Technology Act, 2000",
        pdf_filename="information_technology_act_2000.pdf",
        external_id="official-information-technology-act-2000",
        doc_date="2000-10-09",
        effective_date="2000-10-17",
    ),
    ActManifestEntry(
        key="consumer_protection",
        title="Consumer Protection Act, 2019",
        pdf_filename="consumer_protection_act_2019.pdf",
        external_id="official-consumer-protection-act-2019",
        doc_date="2019-08-08",
        effective_date="2020-07-20",
    ),
    ActManifestEntry(
        key="income_tax_amended",
        title="Income Tax Act, 2025 (as amended by FA Act 2026)",
        pdf_filename="income_tax_act_2025_amended.pdf",
        external_id="official-income-tax-act-2025-amended",
        doc_date="2025-02-01",
        effective_date="2026-04-01",
    ),
    ActManifestEntry(
        key="cgst",
        title="Central Goods and Services Tax Act, 2017",
        pdf_filename="cgst_act_2017.pdf",
        external_id="official-cgst-act-2017",
        doc_date="2017-03-29",
        effective_date="2017-07-01",
    ),
    ActManifestEntry(
        key="arbitration",
        title="Arbitration and Conciliation Act, 1996",
        pdf_filename="arbitration_and_conciliation_act_1996.pdf",
        external_id="official-arbitration-and-conciliation-act-1996",
        doc_date="1996-01-25",
        effective_date="1996-07-16",
    ),
    ActManifestEntry(
        key="copyright",
        title="Copyright Act, 1957",
        pdf_filename="copyright_act_1957.pdf",
        external_id="official-copyright-act-1957",
        doc_date="1957-04-30",
        effective_date="1958-01-21",
    ),
    ActManifestEntry(
        key="insolvency",
        title="Insolvency and Bankruptcy Code, 2016",
        pdf_filename="insolvency_and_bankruptcy_code_2016.pdf",
        external_id="official-insolvency-and-bankruptcy-code-2016",
        doc_date="2016-05-28",
        effective_date="2016-12-28",
    ),
    ActManifestEntry(
        key="patents",
        title="Patents Act, 1970",
        pdf_filename="patents_act_1970.pdf",
        external_id="official-patents-act-1970",
        doc_date="1970-09-19",
        effective_date="1972-04-20",
    ),
    ActManifestEntry(
        key="special_marriage",
        title="Special Marriage Act, 1954",
        pdf_filename="special_marriage_act_1954.pdf",
        external_id="official-special-marriage-act-1954",
        doc_date="1954-10-25",
        effective_date="1955-06-01",
    ),
    ActManifestEntry(
        key="environment",
        title="Environment Protection Act, 1986",
        pdf_filename="environment_protection_act_1986.pdf",
        external_id="official-environment-protection-act-1986",
        doc_date="1986-05-23",
        effective_date="1986-11-19",
    ),
    ActManifestEntry(
        key="industrial_disputes",
        title="Industrial Disputes Act, 1947",
        pdf_filename="industrial_disputes_act_1947.pdf",
        external_id="official-industrial-disputes-act-1947",
        doc_date="1947-03-01",
        effective_date="1947-08-01",
    ),
)


def _selected_entries(args: argparse.Namespace) -> list[ActManifestEntry]:
    by_key = {entry.key: entry for entry in ACTS}
    selected_keys = args.only or list(by_key)
    unknown = sorted(set(selected_keys) - set(by_key))
    if unknown:
        raise SystemExit(f"Unknown act key(s): {', '.join(unknown)}")

    entries = [by_key[key] for key in selected_keys]
    if not args.include_already_ingested:
        entries = [entry for entry in entries if not entry.already_ingested]
    return entries


def _extract_pdf_text(path: Path) -> str:
    with fitz.open(path) as pdf:
        return "\n".join(page.get_text("text") for page in pdf).strip()


async def _ingest_entry(entry: ActManifestEntry, pdf_dir: Path) -> None:
    pdf_path = (pdf_dir / entry.pdf_filename).resolve()
    if not pdf_path.exists():
        print(f"SKIP {entry.key}: missing {pdf_path}")
        return

    content = _extract_pdf_text(pdf_path)
    if len(content) < 50:
        print(f"SKIP {entry.key}: no usable text extracted from {pdf_path}")
        return

    payload = RagIngestRequest(
        title=entry.title,
        content=content,
        source_type="statute",
        source_uri=pdf_path.as_uri(),
        language="en",
        tags=["india", "official", "statute", entry.key],
        external_id=entry.external_id,
        doc_version="official",
        effective_date=entry.effective_date,
        legal_metadata=RagLegalMetadata(
            jurisdiction="India",
            act_name=entry.title,
            matter_type="statute",
            doc_date=entry.doc_date,
        ),
        metadata={
            "source_file": str(pdf_path),
            "ingest_manifest_key": entry.key,
        },
        chunk_size=1500,
        chunk_overlap=150,
    )

    try:
        result = await ingest_document(
            tenant_id=TENANT_ID,
            app_key=APP_KEY,
            created_by=CREATED_BY,
            payload=payload,
        )
    except ValueError as exc:
        if "external_id already exists" in str(exc):
            print(f"EXISTS {entry.key}: {entry.title}")
            return
        raise

    print(f"OK {entry.key}: {result['document_id']} ({result['chunk_count']} chunks)")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest official Indian bare-act PDFs into LegalMitra RAG."
    )
    parser.add_argument(
        "--pdf-dir",
        default=str(PDF_DIR),
        help="Directory containing the official PDFs.",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        choices=[entry.key for entry in ACTS],
        help="Only ingest the selected manifest keys.",
    )
    parser.add_argument(
        "--include-already-ingested",
        action="store_true",
        help="Also ingest entries marked as already ingested in the manifest.",
    )
    args = parser.parse_args()

    entries = _selected_entries(args)
    if not entries:
        print("Nothing to ingest.")
        return

    await init_mongo()
    try:
        await ensure_rag_indexes()
        pdf_dir = Path(args.pdf_dir)
        for entry in entries:
            await _ingest_entry(entry, pdf_dir)
    finally:
        await close_mongo()


if __name__ == "__main__":
    asyncio.run(main())
