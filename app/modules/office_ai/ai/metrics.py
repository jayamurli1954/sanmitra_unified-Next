from __future__ import annotations

from collections import defaultdict
from threading import Lock

_lock = Lock()
_counters: dict[str, int] = defaultdict(int)
_latency_sum_ms: dict[str, int] = defaultdict(int)
_latency_count: dict[str, int] = defaultdict(int)


def incr(metric: str, *, amount: int = 1) -> None:
    with _lock:
        _counters[metric] += amount


def observe_latency(metric: str, latency_ms: int) -> None:
    with _lock:
        _latency_sum_ms[metric] += max(0, int(latency_ms))
        _latency_count[metric] += 1
        _counters[f"{metric}.count"] += 1


def snapshot() -> dict:
    with _lock:
        averages = {}
        for key, total in _latency_sum_ms.items():
            count = _latency_count.get(key) or 0
            averages[key] = int(total / count) if count else 0
        return {
            "counters": dict(_counters),
            "avg_latency_ms": averages,
        }


def reset_for_tests() -> None:
    with _lock:
        _counters.clear()
        _latency_sum_ms.clear()
        _latency_count.clear()
