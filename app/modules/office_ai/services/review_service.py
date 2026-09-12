"""OfficeMitra Review orchestration (ADR-015).

Links engagements to existing MIS packs (Excel import stays on ADR-014).
Scan and working papers read MIS facts only — never MitraBooks journals.
"""
from __future__ import annotations

from typing import Any

from app.modules.office_ai.models import REVIEW_PAPER_TYPES, REVIEW_RULE_VERSION, utcnow
from app.modules.office_ai.services import (
    mis_store,
    notification_service,
    review_papers,
    review_scan,
    review_store,
    task_service,
)


class ReviewServiceError(review_store.ReviewStoreError):
    pass


async def create_engagement(
    *,
    tenant_id: str,
    user: dict[str, Any],
    period: str,
    pack_id: str | None = None,
    accounting_entity_id: str | None = None,
    jurisdiction: str = "IN",
) -> dict[str, Any]:
    if pack_id:
        await _require_pack(tenant_id=tenant_id, pack_id=pack_id)
    return await review_store.create_engagement(
        tenant_id=tenant_id,
        user=user,
        period=period,
        pack_id=pack_id,
        accounting_entity_id=accounting_entity_id,
        jurisdiction=jurisdiction,
    )


async def link_pack(
    *,
    tenant_id: str,
    engagement_id: str,
    user: dict[str, Any],
    pack_id: str,
) -> dict[str, Any]:
    await _require_pack(tenant_id=tenant_id, pack_id=pack_id)
    return await review_store.update_engagement(
        tenant_id=tenant_id,
        engagement_id=engagement_id,
        user=user,
        updates={"pack_id": pack_id},
    )


async def scan_engagement(
    *,
    tenant_id: str,
    engagement_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    engagement = await review_store.get_engagement(tenant_id=tenant_id, engagement_id=engagement_id)
    if engagement is None:
        raise review_store.ReviewNotFoundError(f"Engagement not found: {engagement_id}")
    pack_id = str(engagement.get("pack_id") or "").strip()
    if not pack_id:
        raise ReviewServiceError("Link a MIS pack before scanning")
    facts = await mis_store.list_facts(tenant_id=tenant_id, pack_id=pack_id, limit=2000)
    issues, score = review_scan.scan_facts(facts)
    saved = await review_store.replace_issues(
        tenant_id=tenant_id,
        engagement_id=engagement_id,
        user=user,
        issues=issues,
    )
    updated = await review_store.update_engagement(
        tenant_id=tenant_id,
        engagement_id=engagement_id,
        user=user,
        updates={
            "status": "scanned",
            "engagement_risk_score": score,
            "last_scanned_at": utcnow(),
            "rule_version": REVIEW_RULE_VERSION,
        },
    )
    return {
        "engagement": updated,
        "issues": saved,
        "issue_count": len(saved),
        "engagement_risk_score": score,
        "data_quality_score": None,
        "engine": "review_rules",
        "ssdv_cli": False,
    }


async def generate_working_papers(
    *,
    tenant_id: str,
    engagement_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    engagement = await review_store.get_engagement(tenant_id=tenant_id, engagement_id=engagement_id)
    if engagement is None:
        raise review_store.ReviewNotFoundError(f"Engagement not found: {engagement_id}")
    pack_id = str(engagement.get("pack_id") or "").strip()
    if not pack_id:
        raise ReviewServiceError("Link a MIS pack before generating working papers")
    facts = await mis_store.list_facts(tenant_id=tenant_id, pack_id=pack_id, limit=2000)
    papers = []
    for paper_type in sorted(REVIEW_PAPER_TYPES):
        builder = review_papers.PAPER_BUILDERS[paper_type]
        content, filename = builder(facts)
        papers.append(
            await review_store.save_paper(
                tenant_id=tenant_id,
                engagement_id=engagement_id,
                user=user,
                paper_type=paper_type,
                filename=filename,
                content_type=review_papers.EXCEL_TYPE,
                content=content,
            )
        )
    return {"items": papers, "count": len(papers)}


async def create_note_with_task(
    *,
    tenant_id: str,
    engagement_id: str,
    user: dict[str, Any],
    description: str,
    issue_id: str | None = None,
    assigned_to: str | None = None,
) -> dict[str, Any]:
    finding = ""
    if issue_id:
        issue = await review_store.get_issue(tenant_id=tenant_id, issue_id=issue_id)
        if issue is None or issue.get("engagement_id") != engagement_id:
            raise review_store.ReviewNotFoundError(f"Review issue not found: {issue_id}")
        finding = str(issue.get("finding_code") or "")
    title = f"Review note{': ' + finding if finding else ''}"[:500]
    task = await task_service.create_task(
        tenant_id=tenant_id,
        user=user,
        title=title,
        notes=description,
        source="manual",
    )
    note = await review_store.create_note(
        tenant_id=tenant_id,
        engagement_id=engagement_id,
        user=user,
        description=description,
        issue_id=issue_id,
        assigned_to=assigned_to,
        task_id=str(task.get("id") or ""),
    )
    notify_user = dict(user)
    if assigned_to:
        notify_user = {"sub": assigned_to, "user_id": assigned_to, "id": assigned_to}
        await notification_service.create_notification(
            tenant_id=tenant_id,
            user=notify_user,
            title=title,
            body=description[:400],
            kind="review_note_assigned",
            href="/business/office-ai",
            dedupe_key=f"review_note:{note.get('id')}",
        )
    return {"item": note, "task": task}


async def _require_pack(*, tenant_id: str, pack_id: str) -> dict[str, Any]:
    pack = await mis_store.get_pack(tenant_id=tenant_id, pack_id=pack_id)
    if pack is None:
        raise ReviewServiceError("MIS pack not found for this tenant")
    return pack
