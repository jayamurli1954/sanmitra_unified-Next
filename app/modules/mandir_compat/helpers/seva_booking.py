"""MandirMitra seva booking validation and date-window helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.helpers.coercions import (
    _safe_bool,
    _safe_optional_int,
)

_SEVA_ALLOWED_CATEGORIES = {
    "abhisheka",
    "alankara",
    "pooja",
    "archana",
    "vahana_seva",
    "special",
    "festival",
}
_SEVA_ALLOWED_AVAILABILITY = {
    "daily",
    "weekday",
    "weekend",
    "specific_day",
    "except_day",
    "festival_only",
}
def _normalize_seva_category(value: Any) -> str:
    candidate = str(value or "pooja").strip().lower()
    return candidate if candidate in _SEVA_ALLOWED_CATEGORIES else "pooja"


def _normalize_seva_availability(value: Any) -> str:
    candidate = str(value or "daily").strip().lower()
    return candidate if candidate in _SEVA_ALLOWED_AVAILABILITY else "daily"


def _normalize_seva_day(value: Any) -> int | None:
    parsed = _safe_optional_int(value)
    if parsed is None:
        return None
    if 0 <= parsed <= 6:
        return parsed
    return None


_IST_TIMEZONE = ZoneInfo("Asia/Kolkata")


def _today_weekday_js_index() -> int:
    # JavaScript Date.getDay convention: Sunday=0 ... Saturday=6.
    return (datetime.now(_IST_TIMEZONE).weekday() + 1) % 7


def _weekday_js_index_for_date(value: date) -> int:
    # JavaScript Date.getDay convention: Sunday=0 ... Saturday=6.
    return (value.weekday() + 1) % 7


def _parse_booking_date(value: Any) -> date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    normalized = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except Exception:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(raw[:10], fmt).date()
            except Exception:
                continue
    return None


def _validate_seva_booking_date(seva_doc: dict[str, Any] | None, booking_date: date) -> None:
    if not seva_doc:
        return

    target_day = _weekday_js_index_for_date(booking_date)
    specific_day = _normalize_seva_day(seva_doc.get("specific_day"))
    except_day = _normalize_seva_day(seva_doc.get("except_day"))
    day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    if specific_day is not None and target_day != specific_day:
        raise HTTPException(
            status_code=400,
            detail=f"This seva is available only on {day_names[specific_day]}. Please select a {day_names[specific_day]} date.",
        )
    if except_day is not None and target_day == except_day:
        raise HTTPException(
            status_code=400,
            detail=f"This seva is not available on {day_names[except_day]}. Please select another date.",
        )

    availability = _normalize_seva_availability(seva_doc.get("availability"))
    if availability == "weekday" and target_day not in {1, 2, 3, 4, 5}:
        raise HTTPException(status_code=400, detail="This seva is available only on weekdays.")
    if availability == "weekend" and target_day not in {0, 6}:
        raise HTTPException(status_code=400, detail="This seva is available only on weekends.")
    if availability == "festival_only":
        raise HTTPException(status_code=400, detail="This seva is available only on configured festival dates.")


async def _count_seva_bookings_for_date(
    *,
    tenant_id: str,
    app_key: str,
    seva_id: str,
    booking_date: date,
) -> int:
    booking_date_text = booking_date.isoformat()
    docs = await mandir_router.get_collection("mandir_seva_bookings").find(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "seva_id": str(seva_id),
            "booking_date": booking_date_text,
        }
    ).to_list(length=5000)
    return sum(
        1
        for doc in docs
        if str(doc.get("status") or "").strip().lower() not in {"cancelled", "canceled"}
    )


async def _validate_seva_booking_capacity(
    seva_doc: dict[str, Any] | None,
    *,
    tenant_id: str,
    app_key: str,
    seva_id: str,
    booking_date: date,
) -> tuple[int | None, int, int | None]:
    max_bookings = _safe_optional_int((seva_doc or {}).get("max_bookings_per_day"))
    booked_count = await _count_seva_bookings_for_date(
        tenant_id=tenant_id,
        app_key=app_key,
        seva_id=seva_id,
        booking_date=booking_date,
    )
    if max_bookings is None or max_bookings <= 0:
        return None, booked_count, None

    slots_left = max(max_bookings - booked_count, 0)
    if slots_left <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"This seva is fully booked for {booking_date.strftime('%d-%m-%Y')}. Please select another date.",
        )
    return max_bookings, booked_count, slots_left


def _compute_seva_available_today(row: dict[str, Any]) -> bool:
    if not _safe_bool(row.get("is_active"), True):
        return False

    slots_left = _safe_optional_int(row.get("bookings_available"))
    if slots_left is not None and slots_left <= 0:
        return False

    today = _today_weekday_js_index()
    specific_day = _normalize_seva_day(row.get("specific_day"))
    except_day = _normalize_seva_day(row.get("except_day"))

    # Explicit day constraints are authoritative even if availability is stale.
    if specific_day is not None:
        return specific_day == today
    if except_day is not None:
        return except_day != today

    availability = _normalize_seva_availability(row.get("availability"))
    if availability == "weekday":
        return 1 <= today <= 5
    if availability == "weekend":
        return today in {0, 6}
    if availability == "festival_only":
        return False
    return True

def _resolve_report_date_window(
    *,
    from_date: date | None,
    to_date: date | None,
    single_date: date | None = None,
    month: int | None = None,
    year: int | None = None,
) -> tuple[date, date]:
    if single_date is not None:
        return single_date, single_date

    if from_date is not None and to_date is not None:
        if from_date > to_date:
            raise HTTPException(status_code=422, detail="from_date cannot be greater than to_date")
        return from_date, to_date

    if month is not None or year is not None:
        resolved_year = year or datetime.now(timezone.utc).year
        if month is None:
            start = date(resolved_year, 1, 1)
            end = date(resolved_year, 12, 31)
            return start, end

        _, last_day = calendar.monthrange(resolved_year, month)
        start = date(resolved_year, month, 1)
        end = date(resolved_year, month, last_day)
        return start, end

    if from_date is not None and to_date is None:
        return from_date, from_date
    if to_date is not None and from_date is None:
        return to_date, to_date

    raise HTTPException(
        status_code=422,
        detail="Provide either date, from_date/to_date, or month/year query parameters",
    )


def _resolve_export_window(
    *,
    from_date: date | None,
    to_date: date | None,
    date_from: date | None,
    date_to: date | None,
) -> tuple[date, date]:
    start = from_date or date_from
    end = to_date or date_to
    if start is None or end is None:
        raise HTTPException(status_code=422, detail="from_date/to_date (or date_from/date_to) are required")
    if start > end:
        raise HTTPException(status_code=422, detail="from_date cannot be greater than to_date")
    return start, end



