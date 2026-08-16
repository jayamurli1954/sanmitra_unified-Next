"""LegalMitra Stage 4 — deterministic action hrefs and suggested next steps."""
from __future__ import annotations


def action_href(matter_id: str | None, *, focus: str = "matter-brief") -> str:
    allowed = {"daily-board", "matter-brief", "document-register"}
    fragment = focus if focus in allowed else "matter-brief"
    if matter_id:
        return f"./tracker.html?matter_id={matter_id}#{fragment}"
    return f"./tracker.html#{fragment}"


def suggested_actions_for(*, alert_type: str, matter: dict) -> list[str]:
    number = matter.get("matter_number") or matter.get("matter_id")
    if alert_type == "hearing_approaching":
        return [
            f"Prepare for hearing on matter {number}",
            "Review last order / timeline entry",
            "Confirm client instructions",
            "Generate Matter Intelligence Brief",
        ]
    if alert_type == "deadline_approaching":
        return [
            f"Prepare filing / response for deadline on {number}",
            "Check required documents are attached",
            "Review applicable law with citations before filing",
            "Generate Matter Intelligence Brief",
        ]
    if alert_type == "compliance_gap_missing_documents":
        return [
            "Attach source documents to the matter file",
            "Request missing papers from the client",
            "Update matter timeline after receipt",
        ]
    if alert_type == "matter_awaiting_review":
        return [
            "Move matter forward or update status",
            "Generate or review Matter Intelligence Brief",
            "Record next hearing/deadline if known",
        ]
    if alert_type == "dormant_matter":
        return [
            "Confirm whether the matter is waiting on client, court, or internal work",
            "Add a timeline note with current status",
            "Set next deadline or place on hold if paused",
        ]
    return ["Open matter and review timeline"]
