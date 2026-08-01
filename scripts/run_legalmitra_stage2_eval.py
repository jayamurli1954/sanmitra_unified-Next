"""Run LegalMitra Stage 2 GST/IT eval fixture against hybrid research.

Scores citation-backed answers vs refusals. Does not call external providers
for fixture cases that hit authorized offline slices or insufficient-source paths.

Usage:
  python scripts/run_legalmitra_stage2_eval.py
  python scripts/run_legalmitra_stage2_eval.py --min-grounding 0.95
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

FIXTURE = ROOT / "tests" / "fixtures" / "legalmitra_gst_s54_eval.json"


def _grounded(result: dict) -> bool:
    if result.get("missing_jurisdiction") or result.get("confidence") == "insufficient_sources":
        return True
    citations = result.get("citations") or []
    if not citations:
        return False
    if not result.get("human_review_required"):
        return False
    if not result.get("advisory_notice"):
        return False
    strategy = str(result.get("strategy") or "")
    if strategy in {"hybrid_hash_gemini", "hybrid_hash_claude_legal_counsel"} and not citations:
        return False
    return True


def _terms_ok(result: dict, expect: dict) -> bool:
    body = str(result.get("response") or "").lower()
    for term in expect.get("must_include_terms") or []:
        if term.lower() not in body:
            # Refusal / missing jurisdiction may omit content terms.
            if result.get("confidence") == "insufficient_sources" or result.get("missing_jurisdiction"):
                return True
            return False
    return True


async def _run(min_grounding: float) -> int:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases = list(fixture.get("cases") or [])
    if not cases:
        print("FAIL: empty fixture")
        return 1

    async def _no_provider(**kwargs):
        return None

    # Keep eval deterministic for Stage 2 contract: offline slices + refusal only.
    service._call_claude_legal_counsel_text = _no_provider  # type: ignore[method-assign]
    service._call_gemini_text = _no_provider  # type: ignore[method-assign]

    passed = 0
    grounded = 0
    failures: list[str] = []

    for case in cases:
        result = await service.build_hybrid_legal_response(
            tenant_id="tenant-1",
            app_key="legalmitra",
            query=case["question"],
            rag_result={"answer": "", "citations": [], "strategy": "hybrid_hash"},
            background_tasks=None,
        )
        expect = case.get("expect") or {}
        ok = True
        if not result.get("human_review_required"):
            ok = False
            failures.append(f"{case['id']}: missing human_review_required")
        if not result.get("advisory_notice"):
            ok = False
            failures.append(f"{case['id']}: missing advisory_notice")
        if expect.get("forbid_uncited_generation") and not _grounded(result):
            ok = False
            failures.append(f"{case['id']}: uncited/ungrounded answer strategy={result.get('strategy')}")
        if not _terms_ok(result, expect):
            ok = False
            failures.append(f"{case['id']}: missing required terms")
        if expect.get("strategy") and result.get("strategy") != expect["strategy"]:
            ok = False
            failures.append(f"{case['id']}: strategy {result.get('strategy')} != {expect['strategy']}")
        if expect.get("confidence") and result.get("confidence") != expect["confidence"]:
            ok = False
            failures.append(f"{case['id']}: confidence {result.get('confidence')} != {expect['confidence']}")
        if expect.get("missing_jurisdiction") and not result.get("missing_jurisdiction"):
            ok = False
            failures.append(f"{case['id']}: expected missing_jurisdiction")

        if _grounded(result):
            grounded += 1
        if ok:
            passed += 1
        print(
            f"{case['id']}: {'PASS' if ok else 'FAIL'} "
            f"strategy={result.get('strategy')} confidence={result.get('confidence')} "
            f"citations={len(result.get('citations') or [])}"
        )

    total = len(cases)
    grounding_rate = grounded / total if total else 0.0
    print("---")
    print(f"cases={total} passed={passed} grounded_or_refused={grounded} grounding_rate={grounding_rate:.2%}")
    if failures:
        print("failures:")
        for item in failures:
            print(f"  - {item}")
    if passed < total:
        return 1
    if grounding_rate + 1e-9 < min_grounding:
        print(f"FAIL: grounding_rate {grounding_rate:.2%} < required {min_grounding:.2%}")
        return 1
    print("PASS: Stage 2 eval bar met")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="LegalMitra Stage 2 GST/IT eval")
    parser.add_argument("--min-grounding", type=float, default=0.95)
    args = parser.parse_args()
    return asyncio.run(_run(args.min_grounding))


if __name__ == "__main__":
    raise SystemExit(main())
