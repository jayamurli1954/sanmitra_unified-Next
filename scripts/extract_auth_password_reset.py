#!/usr/bin/env python3
"""Fold password-reset helpers into auth-session.js (Phase 3 seam 60)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
AUTH = ROOT / "frontend/mitrabooks-erp/modules/workspaces/auth-session.js"
INDEX = ROOT / "frontend/mitrabooks-erp/index.html"
BASELINE = ROOT / "scripts/file_size_baseline.json"
TEST = ROOT / "tests/test_mitrabooks_frontend_local_api.py"

EXPORT_FUNCS = [
    "isPasswordRecoveryPanelOpen",
    "setAuthPanelMode",
    "showAuthFieldMessage",
    "clearAuthFieldMessage",
    "requestPasswordReset",
    "completePasswordReset",
]


def find_fn_block(lines: list[str], name: str) -> tuple[int, int]:
    start = next(i for i, l in enumerate(lines) if re.match(rf"^(async )?function {re.escape(name)}\b", l))
    depth = 0
    started = False
    end = start
    for i in range(start, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        started = True
        if started and depth <= 0:
            end = i + 1
            break
    else:
        raise SystemExit(f"unterminated {name}")
    while end < len(lines) and lines[end].strip() == "":
        end += 1
    return start, end


def rewrite_block(block: str) -> str:
    block = block.replace("LOGIN_REQUEST_TIMEOUT_MS", "getLoginRequestTimeoutMs()")
    block = block.replace("LOGIN_EMAIL_STORAGE_KEY", "getLoginEmailStorageKey()")
    block = block.replace("APP_KEY", "getAppKey()")
    block = block.replace("pendingPasswordResetToken", "getPendingPasswordResetToken()")
    for name in ("LoginRequestTimeoutMs", "LoginEmailStorageKey", "AppKey", "PendingPasswordResetToken"):
        block = block.replace(f"get{name}()()", f"get{name}()")
    # assignment
    block = block.replace(
        'getPendingPasswordResetToken() = "";',
        'setPendingPasswordResetToken("");',
    )
    return block


def main() -> None:
    auth = AUTH.read_text(encoding="utf-8")
    if "export async function requestPasswordReset" in auth:
        print("Already extracted")
        return

    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    spans = []
    for name in EXPORT_FUNCS:
        start, end = find_fn_block(lines, name)
        spans.append((start, end, name))
    spans.sort(key=lambda s: s[0], reverse=True)
    chunks: dict[str, str] = {}
    for start, end, name in spans:
        chunks[name] = "".join(lines[start:end])
        del lines[start:end]

    block = "".join(chunks[name] for name in EXPORT_FUNCS)
    for name in EXPORT_FUNCS:
        block = re.sub(
            rf"(?m)^(async )?function {name}\b",
            rf"export \1function {name}",
            block,
            count=1,
        )
    block = block.replace("export export ", "export ")
    block = rewrite_block(block)

    # Remove setAuthPanelMode deps wrapper; add DOM + pending token helpers.
    auth = auth.replace(
        "function setAuthPanelMode(...args) { return requireDeps().setAuthPanelMode(...args); }\n",
        "",
    )
    if "let forgotPasswordForm;" not in auth:
        auth = auth.replace(
            "let moduleState;\n",
            "let moduleState;\n"
            "let forgotPasswordForm;\n"
            "let forgotPasswordEmail;\n"
            "let resetPasswordForm;\n"
            "let resetNewPasswordInput;\n"
            "let resetConfirmPasswordInput;\n",
            1,
        )
        auth = auth.replace(
            "  moduleState = injected.moduleState;\n}",
            "  moduleState = injected.moduleState;\n"
            "  forgotPasswordForm = injected.forgotPasswordForm;\n"
            "  forgotPasswordEmail = injected.forgotPasswordEmail;\n"
            "  resetPasswordForm = injected.resetPasswordForm;\n"
            "  resetNewPasswordInput = injected.resetNewPasswordInput;\n"
            "  resetConfirmPasswordInput = injected.resetConfirmPasswordInput;\n}",
            1,
        )
    if "function getPendingPasswordResetToken()" not in auth:
        auth = auth.replace(
            "function getLoginRequestTimeoutMs() { return requireDeps().getLoginRequestTimeoutMs(); }\n",
            "function getLoginRequestTimeoutMs() { return requireDeps().getLoginRequestTimeoutMs(); }\n"
            "function getPendingPasswordResetToken() { return requireDeps().getPendingPasswordResetToken(); }\n"
            "function setPendingPasswordResetToken(value) { requireDeps().setPendingPasswordResetToken(value); }\n",
            1,
        )

    if not auth.endswith("\n"):
        auth += "\n"
    auth += "\n" + block
    if not auth.endswith("\n"):
        auth += "\n"
    AUTH.write_text(auth, encoding="utf-8", newline="\n")

    app = "".join(lines)

    # Expand auth-session import
    old_imp = re.search(
        r'import \{\n(?:  .+\n)+\} from "\./modules/workspaces/auth-session\.js";',
        app,
    )
    if not old_imp:
        raise SystemExit("auth-session import not found")
    old_block = old_imp.group(0)
    if "requestPasswordReset" not in old_block:
        # insert before closing
        new_block = old_block.replace(
            "} from \"./modules/workspaces/auth-session.js\";",
            "  isPasswordRecoveryPanelOpen,\n"
            "  setAuthPanelMode,\n"
            "  showAuthFieldMessage,\n"
            "  clearAuthFieldMessage,\n"
            "  requestPasswordReset,\n"
            "  completePasswordReset,\n"
            "} from \"./modules/workspaces/auth-session.js\";",
            1,
        )
        # Ensure initAuthSession still first if present
        if "initAuthSession" not in new_block:
            raise SystemExit("initAuthSession missing from import rewrite")
        app = app.replace(old_block, new_block, 1)

    # Extend initAuthSession
    idx = app.find("initAuthSession({")
    if idx < 0:
        raise SystemExit("initAuthSession not found")
    end = app.find("});", idx)
    mid = app[idx:end]
    if "forgotPasswordForm," not in mid:
        mid = mid.replace(
            "  moduleState,\n",
            "  moduleState,\n"
            "  forgotPasswordForm,\n"
            "  forgotPasswordEmail,\n"
            "  resetPasswordForm,\n"
            "  resetNewPasswordInput,\n"
            "  resetConfirmPasswordInput,\n",
            1,
        )
    if "getPendingPasswordResetToken:" not in mid:
        mid = mid.replace(
            "  getLoginRequestTimeoutMs: () => LOGIN_REQUEST_TIMEOUT_MS,\n",
            "  getLoginRequestTimeoutMs: () => LOGIN_REQUEST_TIMEOUT_MS,\n"
            "  getPendingPasswordResetToken: () => pendingPasswordResetToken,\n"
            "  setPendingPasswordResetToken: (value) => { pendingPasswordResetToken = value; },\n",
            1,
        )
    mid = mid.replace("  setAuthPanelMode,\n", "")
    app = app[:idx] + mid + app[end:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(r"app\.js\?v=mitrabooks-erp-v97", "app.js?v=mitrabooks-erp-v98", html, count=1)
    if n != 1:
        raise SystemExit(f"cache bump failed n={n}")
    INDEX.write_text(html2, encoding="utf-8", newline="\n")

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    app_lines = len(APP.read_text(encoding="utf-8").splitlines())
    baseline["frontend/mitrabooks-erp/app.js"] = app_lines
    BASELINE.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8", newline="\n")

    # Update contract test expectations
    test = TEST.read_text(encoding="utf-8")
    test = test.replace(
        '    assert "async function requestPasswordReset()" in app_source\n'
        '    assert "async function completePasswordReset()" in app_source\n',
        '    assert "export async function requestPasswordReset()" in auth_source\n'
        '    assert "export async function completePasswordReset()" in auth_source\n',
        1,
    )
    test = test.replace(
        '    assert "/api/v1/auth/forgot-password" in app_source\n'
        '    assert "/api/v1/auth/reset-password" in app_source\n',
        '    assert "/api/v1/auth/forgot-password" in auth_source\n'
        '    assert "/api/v1/auth/reset-password" in auth_source\n',
        1,
    )
    # topbarControlStrip moved to navigation-shell earlier
    if 'topbarControlStrip.hidden = currentExperience !== "mitrabooks";' in test:
        nav_assert = (
            '    nav_source = (\n'
            '        REPO_ROOT / "frontend" / "mitrabooks-erp" / "modules" / "workspaces" / "navigation-shell.js"\n'
            '    ).read_text(encoding="utf-8")\n'
            '    assert \'topbarControlStrip.hidden = getCurrentExperience() !== "mitrabooks";\' in nav_source\n'
        )
        # replace the assert line and ensure nav_source is loaded - check context
        test = test.replace(
            '    assert \'topbarControlStrip.hidden = currentExperience !== "mitrabooks";\' in app_source\n',
            nav_assert,
            1,
        )
    TEST.write_text(test, encoding="utf-8", newline="\n")

    print(f"Folded password-reset into auth-session; app.js={app_lines}; cache=v98")
    print(f"auth-session.js={len(AUTH.read_text(encoding='utf-8').splitlines())} lines")


if __name__ == "__main__":
    main()
