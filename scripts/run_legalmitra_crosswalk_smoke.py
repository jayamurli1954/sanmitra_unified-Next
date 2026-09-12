"""LegalMitra Stage 2.1 / criminal-code crosswalk smoke checks.

Offline (no server) — recommended first:

  python scripts/run_legalmitra_crosswalk_smoke.py

Pytest pack:

  python -m pytest tests/test_legalmitra_code_crosswalk.py tests/test_legalmitra_stage21_quality_gate.py tests/test_legal_statute_verification.py -q

Optional live API (needs bearer token + running backend):

  $env:LEGALMITRA_API_BASE = "http://127.0.0.1:8000"
  $env:LEGALMITRA_TOKEN = "<access_token>"
  python scripts/run_legalmitra_crosswalk_smoke.py --api

Never prints tokens.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.modules.legal_compat import code_crosswalk as cx
from app.modules.legal_compat.statute_normalize import normalize_verified_statute_mappings

# (label, from_code, section, expect_to_code, expect_to_section_prefix, direction)
FORWARD_CASES = [
    ("IPC 420 -> BNS 318*", "IPC", "420", "BNS", "318", "forward"),
    ("IPC 302 -> BNS 103", "IPC", "302", "BNS", "103", "forward"),
    ("IPC 504 -> BNS 352", "IPC", "504", "BNS", "352", "forward"),
    ("IPC 34 -> BNS 3(5)", "IPC", "34", "BNS", "3(5)", "forward"),
    ("CrPC 482 -> BNSS 528", "CrPC", "482", "BNSS", "528", "forward"),
    ("CrPC 458 -> BNSS 504", "CrPC", "458", "BNSS", "504", "forward"),
    ("CrPC 438 -> BNSS 482", "CrPC", "438", "BNSS", "482", "forward"),
    ("CrPC 154 -> BNSS 173", "CrPC", "154", "BNSS", "173", "forward"),
    ("CrPC 41A -> BNSS 35(3)", "CrPC", "41A", "BNSS", "35(3)", "forward"),
    ("IEA 65B -> BSA 63", "IEA", "65B", "BSA", "63", "forward"),
    ("IEA 25 -> BSA 23*", "IEA", "25", "BSA", "23", "forward"),
]

FALSE_CASES = [
    ("false CrPC 482 -> BNSS 504", "CrPC", "482", "BNSS", "504", "528"),
    ("false IPC 504 -> BNSS 504", "IPC", "504", "BNSS", "504", "352"),
]


def _ok(label: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"  PASS  {label}{suffix}")


def _fail(label: str, detail: str) -> None:
    print(f"  FAIL  {label} — {detail}")


def run_offline() -> int:
    print("=== LegalMitra crosswalk smoke (offline) ===")
    cx.load_crosswalk.cache_clear()
    data = cx.load_crosswalk()
    mappings = data.get("mappings") or []
    print(f"Registry version: {data.get('version')}  mappings: {len(mappings)}")
    if len(mappings) < 500:
        _fail("registry size", f"expected ~1000+ pairs, got {len(mappings)}")
        return 1
    _ok("registry loaded", f"v{data.get('version')} / {len(mappings)} pairs")

    failed = 0

    for label, code, section, to_code, to_prefix, direction in FORWARD_CASES:
        result = cx.lookup(from_code=code, section=section, direction=direction)
        if not result.get("found") or not result.get("matches"):
            _fail(label, "not found")
            failed += 1
            continue
        hit = result["matches"][0]
        got_code = str(hit.get("to_code"))
        got_sec = str(hit.get("to_section"))
        if got_code != to_code or not got_sec.startswith(to_prefix):
            _fail(label, f"got {got_code} {got_sec}")
            failed += 1
        else:
            _ok(label, f"{got_code} {got_sec}")

    rev = cx.lookup(from_code="BNSS", section="528", direction="reverse")
    if (
        rev.get("found")
        and rev["matches"][0].get("from_code") == "CrPC"
        and rev["matches"][0].get("from_section") == "482"
    ):
        _ok("reverse BNSS 528 -> CrPC 482")
    else:
        _fail("reverse BNSS 528", str(rev.get("matches")))
        failed += 1

    missing = cx.lookup(from_code="IPC", section="9999")
    if missing.get("found"):
        _fail("missing IPC 9999", "should not invent a mapping")
        failed += 1
    else:
        _ok("missing IPC 9999 does not invent")

    for label, fc, fs, tc, ts, correct in FALSE_CASES:
        false = cx.detect_false_mapping(
            from_code=fc, from_section=fs, to_code=tc, to_section=ts
        )
        if not false or str(false.get("correct_to_section")) != correct:
            _fail(label, str(false))
            failed += 1
        else:
            _ok(label, f"correct -> {false.get('correct_to_code')} {correct}")

    # Normalizer: rewrite false 482 map; preserve genuine BNSS 504
    quash = normalize_verified_statute_mappings(
        "For FIR quashing use Section 504 BNSS as successor to CrPC 482.",
        query="quash FIR inherent powers CrPC 482",
    )
    if "Section 528 BNSS" in quash:
        _ok("normalizer CrPC 482 false map -> BNSS 528")
    else:
        _fail("normalizer CrPC 482", quash[:200])
        failed += 1

    seized = normalize_verified_statute_mappings(
        "Under BNSS Section 504, where no claimant appears within six months "
        "for seized property, the Magistrate may place it at State disposal.",
        query="unclaimed seized property procedure",
    )
    if "504" in seized and "Section 528 BNSS" not in seized:
        _ok("normalizer preserves genuine BNSS 504")
    else:
        _fail("normalizer BNSS 504 preserve", seized[:200])
        failed += 1

    insult = normalize_verified_statute_mappings(
        "IPC Section 504 is now BNSS Section 504 for intentional insult.",
        query="IPC 504 intentional insult",
    )
    if "BNS Section 352" in insult:
        _ok("normalizer IPC 504 false BNSS map -> BNS 352")
    else:
        _fail("normalizer IPC 504", insult[:200])
        failed += 1

    print()
    if failed:
        print(f"RESULT: FAIL ({failed} check(s))")
        return 1
    print("RESULT: PASS")
    return 0


def run_api(base: str, token: str) -> int:
    import urllib.error
    import urllib.parse
    import urllib.request

    print(f"=== LegalMitra crosswalk smoke (API) base={base} ===")
    failed = 0
    headers = {
        "Authorization": f"Bearer {token}",
        "X-App-Key": "legalmitra",
        "Accept": "application/json",
    }

    def get(path: str, params: dict[str, str]) -> dict[str, Any]:
        qs = urllib.parse.urlencode(params)
        url = f"{base.rstrip('/')}/api/v1{path}?{qs}"
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def post(path: str, body: dict[str, str]) -> dict[str, Any]:
        url = f"{base.rstrip('/')}/api/v1{path}"
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={**headers, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))

    try:
        for label, code, section, to_code, to_prefix, _direction in FORWARD_CASES[:6]:
            payload = get(
                "/legalmitra/code-crosswalk",
                {"from_code": code, "section": section, "direction": "forward"},
            )
            matches = payload.get("matches") or []
            if not payload.get("found") or not matches:
                _fail(label, "API not found")
                failed += 1
                continue
            hit = matches[0]
            if str(hit.get("to_code")) != to_code or not str(hit.get("to_section")).startswith(
                to_prefix
            ):
                _fail(label, f"got {hit.get('to_code')} {hit.get('to_section')}")
                failed += 1
            else:
                _ok(label, f"{hit.get('to_code')} {hit.get('to_section')}")

        false = post(
            "/legalmitra/code-crosswalk/validate",
            {
                "from_code": "CrPC",
                "from_section": "482",
                "to_code": "BNSS",
                "to_section": "504",
            },
        )
        if false.get("status") == "known_false":
            _ok("API validate known_false CrPC 482->BNSS 504")
        else:
            _fail("API validate known_false", str(false.get("status")))
            failed += 1

        good = post(
            "/legalmitra/code-crosswalk/validate",
            {
                "from_code": "CrPC",
                "from_section": "482",
                "to_code": "BNSS",
                "to_section": "528",
            },
        )
        if good.get("status") == "verified_in_registry":
            _ok("API validate verified CrPC 482->BNSS 528")
        else:
            _fail("API validate verified", str(good.get("status")))
            failed += 1

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:300]
        print(f"  FAIL  HTTP {exc.code}: {body}")
        return 1
    except Exception as exc:  # noqa: BLE001 — operator smoke script
        print(f"  FAIL  {type(exc).__name__}: {exc}")
        return 1

    print()
    if failed:
        print(f"RESULT: FAIL ({failed} check(s))")
        return 1
    print("RESULT: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="LegalMitra crosswalk smoke checks")
    parser.add_argument(
        "--api",
        action="store_true",
        help="Also hit live /api/v1/legalmitra/code-crosswalk* (needs LEGALMITRA_TOKEN)",
    )
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Skip offline checks; run API only",
    )
    args = parser.parse_args()

    code = 0
    if not args.api_only:
        code = run_offline()
        if code != 0:
            return code

    if args.api or args.api_only:
        base = (
            os.environ.get("LEGALMITRA_API_BASE")
            or os.environ.get("API_BASE")
            or "http://127.0.0.1:8000"
        )
        token = os.environ.get("LEGALMITRA_TOKEN") or os.environ.get("ACCESS_TOKEN") or ""
        if not token:
            print(
                "FAIL: set LEGALMITRA_TOKEN (Bearer access token) for --api mode. "
                "Token is never printed."
            )
            return 1
        code = run_api(base, token)

    print()
    print("More tests:")
    print(
        "  python -m pytest tests/test_legalmitra_code_crosswalk.py "
        "tests/test_legalmitra_stage21_quality_gate.py "
        "tests/test_legal_statute_verification.py -q"
    )
    print("  python scripts/run_legalmitra_stage2_eval.py")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
