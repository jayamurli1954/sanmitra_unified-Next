"""MIS pack export scaffold (ADR-014 step 7).

Generates OfficeMitra-owned export artifact metadata after reconcile gate.
Binary/template rendering is deferred; this module enforces governance only.
"""
from __future__ import annotations

from typing import Any, Literal

from app.modules.office_ai.services import mis_store
from app.modules.office_ai.models import utcnow

MISExportFormat = Literal["excel", "pdf_summary", "ppt"]

MIS_EXPORT_FORMATS: frozenset[str] = frozenset({"excel", "pdf_summary", "ppt"})

# ADR-014: block board PPT when pack trust signal is below this threshold.
PPT_MIN_DATA_QUALITY_SCORE = 70

ACTION_TYPE_BY_FORMAT: dict[str, str] = {
    "excel": "export_mis_excel",
    "pdf_summary": "export_mis_pdf_summary",
    "ppt": "export_mis_ppt",
}


class MISExportError(mis_store.MISStoreError):
    pass


class MISExportNotReconciledError(MISExportError):
    pass


class MISExportQualityBlockedError(MISExportError):
    pass


def action_type_for_format(export_format: str) -> str:
    key = str(export_format or "").strip().lower()
    action = ACTION_TYPE_BY_FORMAT.get(key)
    if not action:
        raise MISExportError(f"Unsupported export format: {export_format}")
    return action


async def export_mis_pack(
    *,
    tenant_id: str,
    pack_id: str,
    user: dict[str, Any],
    export_format: MISExportFormat | str,
) -> dict[str, Any]:
    """Export a reconciled MIS pack (metadata scaffold until template engine ships)."""
    fmt = str(export_format or "").strip().lower()
    if fmt not in MIS_EXPORT_FORMATS:
        raise MISExportError(f"Unsupported export format: {export_format}")

    pack = await mis_store.get_pack(tenant_id=tenant_id, pack_id=pack_id)
    if pack is None:
        raise mis_store.MISPackNotFoundError(f"MIS pack not found: {pack_id}")

    status = str(pack.get("status") or "").strip().lower()
    if status not in {"reconciled", "pending_export", "exported"}:
        raise MISExportNotReconciledError("Pack must be reconciled before export")

    if fmt == "ppt":
        score = pack.get("data_quality_score")
        if score is not None and int(score) < PPT_MIN_DATA_QUALITY_SCORE:
            raise MISExportQualityBlockedError(
                f"PPT export blocked: data_quality_score {score} is below {PPT_MIN_DATA_QUALITY_SCORE}"
            )

    now = utcnow()
    artifact = {
        "format": fmt,
        "pack_id": pack_id,
        "tenant_id": tenant_id,
        "pack_key": pack.get("pack_key"),
        "pack_version": pack.get("pack_version"),
        "materiality_rule_version": pack.get("materiality_rule_version"),
        "period": pack.get("period"),
        "data_quality_score": pack.get("data_quality_score"),
        "status": "generated",
        "storage_ref": f"mis-exports/{tenant_id}/{pack_id}/{fmt}-scaffold.json",
        "content_type": _content_type_for_format(fmt),
        "generated_at": now.isoformat(),
        "note": "Scaffold artifact — template rendering not yet implemented",
    }

    updated_pack = await mis_store.mark_pack_exported(
        tenant_id=tenant_id,
        pack_id=pack_id,
        user=user,
    )
    return {"artifact": artifact, "pack": updated_pack}


def _content_type_for_format(export_format: str) -> str:
    if export_format == "excel":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if export_format == "pdf_summary":
        return "application/pdf"
    if export_format == "ppt":
        return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    return "application/octet-stream"
