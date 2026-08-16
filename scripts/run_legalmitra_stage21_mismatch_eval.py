"""Run LegalMitra Stage 2.1 citation-mismatch fault fixtures.

Injects unsupported statute claims via the provider path and expects refuse
or authorized offline fallthrough (never uncited grounded research).

Usage:
  python scripts/run_legalmitra_stage21_mismatch_eval.py
  python scripts/run_legalmitra_stage21_mismatch_eval.py --min-catch-rate 0.95
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.modules.legal_compat import service

FIXTURE = ROOT / "tests" / "fixtures" / "legalmitra_citation_mismatch_eval.json"


def _terms_ok(result: dict, expect: dict) -> bool:
    body = str(result.get("response") or "").lower()
    for term in expect.get("must_include_terms") or []:
        if term.lower() not in body:
            if result.get("confidence") == "insufficient_sources":
                return True
            return False
    return True


async def _run(min_catch_rate: float) -> int:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases = list(fixture.get("cases") or [])
    if not cases:
        print("FAIL: empty mismatch fixture")
        return 1

    async def _no_claude(**_kwargs):
        return None

    caught = 0
    passed = 0
    failures: list[str] = []

    for case in cases:
        inject = str(case.get("inject_provider_text") or "")

        async def _inject_gemini(**_kwargs):
            return inject

        service._call_claude_legal_counsel_text = _no_claude  # type: ignore[method-assign]
        service._call_gemini_text = _inject_gemini  # type: ignore[method-assign]

        result = await service.build_hybrid_legal_response(
            tenant_id="tenant-1",
            app_key="legalmitra",
            query=case["question"],
            rag_result={
                "answer": "",
                "strategy": "hybrid_hash",
                "citations": [
                    {
                        "title": "Practice context note",
                        "snippet": "General chamber practice guidance without the injected section.",
                        "score": 0.5,
                    }
                ],
            },
            background_tasks=None,
        )
        expect = case.get("expect") or {}
        ok = True
        strategy = str(result.get("strategy") or "")
        if expect.get("strategy") and strategy != expect["strategy"]:
            ok = False
            failures.append(f"{case['id']}: strategy {strategy} != {expect['strategy']}")
        if expect.get("confidence") and result.get("confidence") != expect["confidence"]:
            ok = False
            failures.append(
                f"{case['id']}: confidence {result.get('confidence')} != {expect['confidence']}"
            )
        if expect.get("require_audit_mismatch"):
            mismatch = int((result.get("citation_audit") or {}).get("mismatch_count") or 0)
            if strategy != "insufficient_sources" or mismatch < 1:
                ok = False
                failures.append(
                    f"{case['id']}: expected insufficient_sources with mismatch_count>=1 "
                    f"(got strategy={strategy} mismatch={mismatch})"
                )
            else:
                caught += 1
        if expect.get("require_quality_gate_pass"):
            gate = result.get("quality_gate") or {}
            if not gate.get("passed"):
                ok = False
                failures.append(f"{case['id']}: quality_gate did not pass")
            elif expect.get("strategy") and strategy == expect["strategy"]:
                caught += 1
        if expect.get("forbid_uncited_generation"):
            if strategy in {"hybrid_hash_gemini", "hybrid_hash_claude_legal_counsel"}:
                ok = False
                failures.append(f"{case['id']}: uncited provider strategy escaped gate")
        if not _terms_ok(result, expect):
            ok = False
            failures.append(f"{case['id']}: missing required terms")
        if not result.get("human_review_required"):
            ok = False
            failures.append(f"{case['id']}: missing human_review_required")
        if ok:
            passed += 1
        print(
            f"{case['id']}: {'PASS' if ok else 'FAIL'} "
            f"strategy={strategy} confidence={result.get('confidence')} "
            f"mismatch={int((result.get('citation_audit') or {}).get('mismatch_count') or 0)}"
        )

    total = len(cases)
    catch_rate = caught / total if total else 0.0
    print("---")
    print(f"cases={total} passed={passed} fault_caught={caught} catch_rate={catch_rate:.2%}")
    if failures:
        print("failures:")
        for item in failures:
            print(f"  - {item}")
    if passed < total:
        return 1
    if catch_rate + 1e-9 < min_catch_rate:
        print(f"FAIL: catch_rate {catch_rate:.2%} < required {min_catch_rate:.2%}")
        return 1
    print("PASS: Stage 2.1 mismatch fault bar met")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="LegalMitra Stage 2.1 mismatch fault eval")
    parser.add_argument("--min-catch-rate", type=float, default=0.95)
    args = parser.parse_args()
    return asyncio.run(_run(args.min_catch_rate))


if __name__ == "__main__":
    raise SystemExit(main())
