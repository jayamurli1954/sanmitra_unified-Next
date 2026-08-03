"""Live Legal Intelligence recency window (prefer 15 days, max 30)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.modules.legal_compat import router as legal_compat_router


def test_filter_recent_items_drops_older_than_window() -> None:
    today = date(2026, 8, 3)
    items = [
        {"title": "Fresh", "date": (today - timedelta(days=5)).isoformat()},
        {"title": "Borderline15", "date": (today - timedelta(days=15)).isoformat()},
        {"title": "Old45", "date": (today - timedelta(days=45)).isoformat()},
        {"title": "Undated"},
    ]
    kept = legal_compat_router._filter_recent_items(items, max_age_days=15, today=today)
    titles = [row["title"] for row in kept]
    assert titles == ["Fresh", "Borderline15"]


def test_select_fresh_live_items_prefers_15_then_widens_to_30() -> None:
    today = date(2026, 8, 3)
    rich = [{"title": f"R{i}", "date": (today - timedelta(days=i)).isoformat()} for i in range(1, 6)]
    preferred = legal_compat_router._select_fresh_live_items(rich, limit=5, today=today)
    assert len(preferred) == 5
    assert all(date.fromisoformat(row["date"]) >= today - timedelta(days=15) for row in preferred)

    thin = [
        {"title": "A", "date": (today - timedelta(days=10)).isoformat()},
        {"title": "B", "date": (today - timedelta(days=20)).isoformat()},
        {"title": "C", "date": (today - timedelta(days=25)).isoformat()},
        {"title": "D", "date": (today - timedelta(days=40)).isoformat()},
    ]
    widened = legal_compat_router._select_fresh_live_items(thin, limit=5, today=today)
    titles = [row["title"] for row in widened]
    assert titles == ["A", "B", "C"]


def test_live_intel_window_constants() -> None:
    assert legal_compat_router.LIVE_INTEL_PREFERRED_DAYS == 15
    assert legal_compat_router.LIVE_INTEL_MAX_DAYS == 30
    assert legal_compat_router.LIVE_INTEL_CACHE_TTL_HOURS == 6
    assert legal_compat_router.LIVE_INTEL_ROTATION_HOURS == 6
    assert legal_compat_router.LIVE_INTEL_SHOWN_COOLDOWN_HOURS == 24


def test_pick_dynamic_live_items_cools_down_recently_shown() -> None:
    legal_compat_router._live_intel_cache.clear()
    now = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
    pool = [{"title": f"Story {i}", "date": "2026-08-01"} for i in range(1, 9)]

    first = legal_compat_router._pick_dynamic_live_items(pool, kind="news", limit=3, now=now)
    first_titles = {row["title"] for row in first}
    assert len(first_titles) == 3

    # Same rotation bucket, but first titles are on cooldown — should prefer others.
    second = legal_compat_router._pick_dynamic_live_items(
        pool, kind="news", limit=3, now=now + timedelta(minutes=10)
    )
    second_titles = {row["title"] for row in second}
    assert first_titles.isdisjoint(second_titles)


def test_rotation_bucket_advances_every_six_hours() -> None:
    t0 = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(hours=5, minutes=59)
    t2 = t0 + timedelta(hours=6)
    assert legal_compat_router._rotation_bucket(t0) == legal_compat_router._rotation_bucket(t1)
    assert legal_compat_router._rotation_bucket(t2) == legal_compat_router._rotation_bucket(t0) + 1
