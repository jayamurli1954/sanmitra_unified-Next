#!/usr/bin/env python3
"""Phase 3 seams 66–68: fold remaining app.js helpers into existing modules."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
AUTH = ROOT / "frontend/mitrabooks-erp/modules/workspaces/auth-session.js"
ACCOUNT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/account-selector.js"
SHELL = ROOT / "frontend/mitrabooks-erp/modules/shell-ui.js"
INDEX = ROOT / "frontend/mitrabooks-erp/index.html"
BASELINE = ROOT / "scripts/file_size_baseline.json"
TEST = ROOT / "tests/test_mitrabooks_frontend_local_api.py"


def find_fn_block(text: str, name: str) -> tuple[int, int]:
    lines = text.splitlines(keepends=True)
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


def extract_fn(text: str, name: str) -> tuple[str, str]:
    lines = text.splitlines(keepends=True)
    start, end = find_fn_block(text, name)
    block = "".join(lines[start:end])
    remainder = "".join(lines[:start] + lines[end:])
    return block, remainder


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if "export function setLoginStatus" in AUTH.read_text(encoding="utf-8"):
        print("Already folded")
        return

    # --- Seam 66: setLoginStatus -> auth-session ---
    set_login_block, app = extract_fn(app, "setLoginStatus")
    set_login_export = re.sub(
        r"(?m)^function setLoginStatus\b",
        "export function setLoginStatus",
        set_login_block,
        count=1,
    )

    auth = AUTH.read_text(encoding="utf-8")
    if "let loginStatus;" not in auth:
        auth = auth.replace(
            "let resetConfirmPasswordInput;\n",
            "let resetConfirmPasswordInput;\nlet loginStatus;\n",
            1,
        )
    auth = auth.replace(
        "  resetConfirmPasswordInput = injected.resetConfirmPasswordInput;\n}",
        "  resetConfirmPasswordInput = injected.resetConfirmPasswordInput;\n"
        "  loginStatus = injected.loginStatus;\n}",
        1,
    )
    # Replace dep-forwarder with real export (keep escapeHtml via deps)
    auth = auth.replace(
        "function setLoginStatus(...args) { return requireDeps().setLoginStatus(...args); }\n",
        "",
        1,
    )
    # Insert export after requireDeps helpers / before hasTrustedSession
    marker = "export function hasTrustedSession()"
    if marker not in auth:
        raise SystemExit("hasTrustedSession marker missing")
    auth = auth.replace(marker, set_login_export + "\n" + marker, 1)
    AUTH.write_text(auth, encoding="utf-8", newline="\n")

    # app.js: import setLoginStatus; pass loginStatus; drop setLoginStatus from auth init deps
    app = app.replace(
        "  completePasswordReset,\n} from \"./modules/workspaces/auth-session.js\";",
        "  completePasswordReset,\n"
        "  setLoginStatus,\n} from \"./modules/workspaces/auth-session.js\";",
        1,
    )
    app = app.replace(
        "  resetConfirmPasswordInput,\n"
        "  getAccessToken,",
        "  resetConfirmPasswordInput,\n"
        "  loginStatus,\n"
        "  getAccessToken,",
        1,
    )
    app = app.replace(
        "  apiRequest,\n  renderJson,\n  setLoginStatus,\n  statusDetailText,\n",
        "  apiRequest,\n  renderJson,\n  statusDetailText,\n",
        1,
    )
    app = app.replace(
        "// Nav workspace mapping + sync live in modules/workspaces/navigation-shell.js\n\n"
        "// Auth + session helpers live in modules/workspaces/auth-session.js\n",
        "// Nav workspace mapping + sync live in modules/workspaces/navigation-shell.js\n"
        "// Auth + session helpers (incl. setLoginStatus) live in modules/workspaces/auth-session.js\n",
        1,
    )

    # --- Seam 67: document listeners -> account-selector ---
    listener_re = re.compile(
        r"(?ms)^// ========== Account Selector Event Handlers ==========.*?^document\.addEventListener\(\"keydown\", \(event\) => \{.*?\n\}\);\n\n",
    )
    m = listener_re.search(app)
    if not m:
        raise SystemExit("account selector listener block not found")
    listeners = m.group(0)
    # Strip banner; keep as install function body
    body = listeners
    body = re.sub(r"(?m)^// ========== Account Selector Event Handlers ==========\n\n", "", body)
    body = re.sub(r"(?m)^// Account selector helpers.*\n", "", body)
    body = re.sub(r"(?m)^// Mixed document listeners.*\n", "", body)

    app = listener_re.sub(
        "// Account selector helpers + document listeners live in modules/workspaces/account-selector.js\n\n",
        app,
        count=1,
    )

    account = ACCOUNT.read_text(encoding="utf-8")
    account = account.replace(
        "// Mixed document listeners (payment-allocation + voucher amounts) remain in app.js.\n",
        "// Document listeners (account selector + allocation/voucher amounts) installed via init.\n",
        1,
    )
    # Expand init deps wrappers
    if "function setAllocationLineAmount" not in account:
        account = account.replace(
            "function updateVoucherBalance() { return requireDeps().updateVoucherBalance(); }\n",
            "function updateVoucherBalance() { return requireDeps().updateVoucherBalance(); }\n"
            "function setAllocationLineAmount(...args) { return requireDeps().setAllocationLineAmount(...args); }\n"
            "function loadVoucherPartyOutstanding(...args) { return requireDeps().loadVoucherPartyOutstanding(...args); }\n",
            1,
        )
    install_fn = (
        "\nexport function installAccountSelectorListeners() {\n"
        + "".join("  " + line if line.strip() else line for line in body.splitlines(keepends=True))
        + "}\n"
    )
    # Fix indentation for nested content - body already has no leading indent on document.addEventListener
    # Rebuild more carefully:
    install_lines = ["\nexport function installAccountSelectorListeners() {\n"]
    for line in body.splitlines(True):
        if line.strip() == "":
            install_lines.append("\n")
        else:
            install_lines.append("  " + line)
    install_lines.append("}\n")
    install_fn = "".join(install_lines)

    if "export function installAccountSelectorListeners" not in account:
        account = account.rstrip() + "\n" + install_fn
        # Call from initAccountSelector
        account = account.replace(
            "export function initAccountSelector(injected) {\n  deps = injected;\n}",
            "export function initAccountSelector(injected) {\n"
            "  deps = injected;\n"
            "  installAccountSelectorListeners();\n}",
            1,
        )
    ACCOUNT.write_text(account, encoding="utf-8", newline="\n")

    app = app.replace(
        "initAccountSelector({\n"
        "  escapeHtml,\n"
        "  businessAccountsForSelection,\n"
        "  getLastBusinessAccounts: () => lastBusinessAccounts,\n"
        "  filterBusinessAccountsByQuery,\n"
        "  populateAccountPickerSelect,\n"
        "  normalizeBusinessAccount,\n"
        "  updateVoucherBalance,\n"
        "});",
        "initAccountSelector({\n"
        "  escapeHtml,\n"
        "  businessAccountsForSelection,\n"
        "  getLastBusinessAccounts: () => lastBusinessAccounts,\n"
        "  filterBusinessAccountsByQuery,\n"
        "  populateAccountPickerSelect,\n"
        "  normalizeBusinessAccount,\n"
        "  updateVoucherBalance,\n"
        "  setAllocationLineAmount,\n"
        "  loadVoucherPartyOutstanding,\n"
        "});",
        1,
    )

    # --- Seam 68: header helpers -> shell-ui ---
    update_block, app = extract_fn(app, "updatePageHeader")
    init_header_block, app = extract_fn(app, "initializeHeader")

    update_export = re.sub(
        r"(?m)^function updatePageHeader\b",
        "export function updatePageHeader",
        update_block,
        count=1,
    )
    init_export = re.sub(
        r"(?m)^function initializeHeader\b",
        "export function initializeHeader",
        init_header_block,
        count=1,
    )
    init_export = init_export.replace(
        "initializeHealthWidget();",
        "requireDeps().initializeHealthWidget();",
    )

    shell = SHELL.read_text(encoding="utf-8")
    # Change import in app from initShellUi only to also updatePageHeader
    # Append exports before closing of file / after installShellUi
    if "export function updatePageHeader" not in shell:
        # Remove empty JSDoc stub at end of installShellUi
        shell = re.sub(
            r"(?ms)\n  /\*\*\n   \* Update page title and breadcrumb based on current view\n"
            r"   \* @param \{string\} parentName - Parent breadcrumb name\n"
            r"   \* @param \{string\} currentName - Current breadcrumb name\n"
            r"   \* @param \{string\} pageTitle - Full page title\n"
            r"   \*/\n\n\}",
            "\n}",
            shell,
            count=1,
        )
        shell = shell.rstrip() + "\n\n" + update_export + "\n" + init_export + "\n"
        # Do NOT call initializeHeader from initShellUi — it needs initAccountHelpers first.
    SHELL.write_text(shell, encoding="utf-8", newline="\n")

    app = app.replace(
        'import { initShellUi } from "./modules/shell-ui.js";',
        'import { initShellUi, updatePageHeader, initializeHeader } from "./modules/shell-ui.js";',
        1,
    )
    # Pass initializeHealthWidget into initShellUi (for initializeHeader via deps)
    if "initializeHealthWidget," not in app[app.find("initShellUi({") : app.find("initShellUi({") + 800]:
        app = app.replace(
            "initShellUi({\n",
            "initShellUi({\n  initializeHealthWidget,\n",
            1,
        )
    # Keep late initializeHeader() call (after account-helpers init). Restore if extract removed the fn but left the call.
    if "initializeHeader();" not in app:
        # Place before production API base bootstrap
        app = app.replace(
            "if (isProductionShell()) {",
            "initializeHeader();\n\nif (isProductionShell()) {",
            1,
        )
    app = re.sub(
        r"(?m)^// HEADER & HEALTH WIDGET.*\n^// =+\n\n",
        "",
        app,
        count=1,
    )
    app = app.replace(
        "// Books health widget lives in modules/workspaces/account-helpers.js\n\n",
        "// Header helpers live in modules/shell-ui.js; books health widget in account-helpers.js\n\n",
        1,
    )
    app = app.replace(
        "// Call on app initialization\n",
        "",
        1,
    )

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(r"app\.js\?v=mitrabooks-erp-v103", "app.js?v=mitrabooks-erp-v104", html, count=1)
    if n != 1:
        raise SystemExit(f"cache bump failed n={n}")
    INDEX.write_text(html2, encoding="utf-8", newline="\n")

    test = TEST.read_text(encoding="utf-8")
    test2, tn = re.subn(
        r'assert "app\.js\?v=mitrabooks-erp-v103" in index_source',
        'assert "app.js?v=mitrabooks-erp-v104" in index_source',
        test,
        count=1,
    )
    if tn != 1:
        raise SystemExit(f"cache test bump failed n={tn}")
    TEST.write_text(test2, encoding="utf-8", newline="\n")

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    app_lines = len(APP.read_text(encoding="utf-8").splitlines())
    baseline["frontend/mitrabooks-erp/app.js"] = app_lines
    BASELINE.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"Folded seams 66–68; app.js={app_lines}; cache=v104")


if __name__ == "__main__":
    main()
