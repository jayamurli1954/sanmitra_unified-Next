"""Load constitutional doctrine/judgment seed JSON for RAG ingest.

Current state: curated Tier-1 and Tier-2 summaries with citations live under
``data/legal_seed/constitutional/``. They are not full judgments and are not
auto-ingested into ``rag_documents``.

Target: operator ingest via ``scripts/ingest_legal_constitutional_seed.py`` into
a tenant-scoped LegalMitra RAG collection.

These records must remain advisory. Verify holdings against the original
reported decision before filing or advising a client.
"""
from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

from pydantic import ValidationError

from app.modules.rag.schemas import RagIngestRequest, RagLegalMetadata

_ROOT = Path(__file__).resolve().parents[3]
_SEED_ROOT = _ROOT / "data" / "legal_seed"
_CONSTITUTIONAL_ROOT = _SEED_ROOT / "constitutional"
_DOCTRINE_DIR = _CONSTITUTIONAL_ROOT / "doctrines"
_JUDGMENT_DIR = _CONSTITUTIONAL_ROOT / "landmark_judgments"
_CROSSWALK_PATH = _SEED_ROOT / "crosswalks" / "doctrine_to_cases.json"

_ADVISORY_PREFIX = (
    "ADVISORY SEED SUMMARY — not the full judgment or statute text. "
    "Verify citations and holdings against the original reported decision "
    "before filing, advising a client, or taking final legal action. "
    "Human review is required.\n\n"
)


def seed_root() -> Path:
    return _SEED_ROOT


def constitutional_root() -> Path:
    return _CONSTITUTIONAL_ROOT


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_doctrine_index() -> dict[str, Any]:
    return _read_json(_DOCTRINE_DIR / "doctrine_index.json")


@lru_cache(maxsize=1)
def load_judgment_index() -> dict[str, Any]:
    return _read_json(_JUDGMENT_DIR / "landmark_index.json")


@lru_cache(maxsize=1)
def load_doctrine_to_cases() -> dict[str, Any]:
    return _read_json(_CROSSWALK_PATH)


def iter_doctrine_records() -> Iterator[dict[str, Any]]:
    for entry in load_doctrine_index().get("doctrines") or []:
        filename = str(entry.get("file") or "").strip()
        if not filename:
            continue
        payload = _read_json(_DOCTRINE_DIR / filename)
        payload["_seed_file"] = f"constitutional/doctrines/{filename}"
        payload["_index_entry"] = entry
        yield payload


def iter_judgment_records() -> Iterator[dict[str, Any]]:
    for entry in load_judgment_index().get("judgments") or []:
        filename = str(entry.get("file") or "").strip()
        if not filename:
            continue
        payload = _read_json(_JUDGMENT_DIR / filename)
        payload["_seed_file"] = f"constitutional/landmark_judgments/{filename}"
        payload["_index_entry"] = entry
        yield payload


def _parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    return date.fromisoformat(text)


def _origin_case(record: dict[str, Any]) -> dict[str, Any]:
    origin = record.get("origin_case")
    return origin if isinstance(origin, dict) else {}


def _ingest_content(record: dict[str, Any]) -> str:
    body = str(record.get("content_for_rag") or record.get("summary") or "").strip()
    proposition = str(record.get("core_proposition") or "").strip()
    outcome = str(record.get("outcome") or "").strip()
    limitations = record.get("limitations") or []
    ratio = record.get("ratio") or []
    parts = [_ADVISORY_PREFIX, body]
    if proposition:
        parts.append(f"\n\nCore proposition: {proposition}")
    if outcome:
        parts.append(f"\n\nOutcome: {outcome}")
    if ratio:
        bullets = "\n".join(f"- {item}" for item in ratio if str(item).strip())
        if bullets:
            parts.append(f"\n\nRatio:\n{bullets}")
    if limitations:
        bullets = "\n".join(f"- {item}" for item in limitations if str(item).strip())
        if bullets:
            parts.append(f"\n\nLimitations:\n{bullets}")
    return "".join(parts).strip()


def to_ingest_request(record: dict[str, Any]) -> RagIngestRequest:
    source_type = str(record.get("source_type") or "").strip().lower()
    if source_type not in {"doctrine", "judgment"}:
        raise ValueError(f"unsupported source_type: {source_type!r}")

    origin = _origin_case(record)
    title = str(record.get("name") or record.get("title") or "").strip()
    citation = str(record.get("citation") or origin.get("citation") or "").strip() or None
    court_name = str(record.get("court_name") or origin.get("court") or "").strip() or None
    bench = str(record.get("bench") or origin.get("bench") or "").strip() or None
    tags = [str(tag).strip().lower() for tag in (record.get("tags") or []) if str(tag).strip()]
    tier = record.get("tier") or (record.get("_index_entry") or {}).get("tier") or 1
    tags.extend(["india", "constitutional", source_type, f"tier-{tier}-seed"])
    related = [str(item).strip().lower() for item in (record.get("related_articles") or []) if str(item).strip()]
    tags.extend(related)

    return RagIngestRequest(
        title=title,
        content=_ingest_content(record),
        source_type=source_type,
        source_uri=(str(record.get("source_uri") or "").strip() or None),
        language=str(record.get("language") or "en").strip() or "en",
        tags=tags,
        external_id=str(record.get("id") or "").strip() or None,
        doc_version=str(record.get("version") or "1.0").strip() or "1.0",
        legal_metadata=RagLegalMetadata(
            jurisdiction=str(record.get("jurisdiction") or "India").strip() or "India",
            court_name=court_name,
            bench=bench,
            act_name="Constitution of India",
            citation=citation,
            matter_type=str(record.get("matter_type") or source_type).strip() or source_type,
            practice_area=str(record.get("practice_area") or "Constitutional Law").strip()
            or "Constitutional Law",
            doc_date=_parse_date(record.get("doc_date")),
        ),
        metadata={
            "seed_package": "constitutional",
            "seed_tier": tier,
            "seed_file": record.get("_seed_file"),
            "seed_id": record.get("id"),
            "advisory": True,
            "human_review_required": True,
            "aliases": record.get("aliases") or [],
            "doctrines_applied": record.get("doctrines_applied") or [],
            "related_articles": record.get("related_articles") or [],
        },
        chunk_size=1200,
        chunk_overlap=120,
    )


def iter_ingest_requests() -> Iterator[RagIngestRequest]:
    for record in iter_doctrine_records():
        yield to_ingest_request(record)
    for record in iter_judgment_records():
        yield to_ingest_request(record)


def validate_seed_package() -> list[str]:
    """Return validation problems. Empty list means the package is ingest-ready."""
    problems: list[str] = []
    if not _DOCTRINE_DIR.exists():
        return ["missing constitutional/doctrines directory"]
    if not _JUDGMENT_DIR.exists():
        return ["missing constitutional/landmark_judgments directory"]
    if not _CROSSWALK_PATH.exists():
        return ["missing crosswalks/doctrine_to_cases.json"]

    doctrine_ids: set[str] = set()
    for entry in load_doctrine_index().get("doctrines") or []:
        filename = str(entry.get("file") or "").strip()
        path = _DOCTRINE_DIR / filename
        if not filename or not path.exists():
            problems.append(f"doctrine index points to missing file: {filename!r}")
            continue
        record = _read_json(path)
        record_id = str(record.get("id") or "")
        doctrine_ids.add(record_id)
        if record.get("source_type") != "doctrine":
            problems.append(f"{filename}: source_type must be doctrine")
        if str(entry.get("id") or "") != record_id:
            problems.append(f"{filename}: id does not match doctrine_index")
        try:
            to_ingest_request({**record, "_seed_file": filename})
        except (ValueError, ValidationError) as exc:
            problems.append(f"{filename}: ingest mapping failed: {exc}")

    judgment_ids: set[str] = set()
    for entry in load_judgment_index().get("judgments") or []:
        filename = str(entry.get("file") or "").strip()
        path = _JUDGMENT_DIR / filename
        if not filename or not path.exists():
            problems.append(f"judgment index points to missing file: {filename!r}")
            continue
        record = _read_json(path)
        record_id = str(record.get("id") or "")
        judgment_ids.add(record_id)
        if record.get("source_type") != "judgment":
            problems.append(f"{filename}: source_type must be judgment")
        if str(entry.get("id") or "") != record_id:
            problems.append(f"{filename}: id does not match landmark_index")
        if not str(record.get("citation") or "").strip():
            problems.append(f"{filename}: missing citation")
        try:
            to_ingest_request({**record, "_seed_file": filename})
        except (ValueError, ValidationError) as exc:
            problems.append(f"{filename}: ingest mapping failed: {exc}")

    mappings = (load_doctrine_to_cases().get("mappings") or {})
    for doctrine_id, case_ids in mappings.items():
        if doctrine_id not in doctrine_ids:
            problems.append(f"crosswalk unknown doctrine: {doctrine_id}")
        for case_id in case_ids or []:
            if case_id not in judgment_ids:
                problems.append(f"crosswalk {doctrine_id} unknown judgment: {case_id}")

    return problems
