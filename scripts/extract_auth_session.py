#!/usr/bin/env python3
"""Extract MitraBooks auth + session helpers (Phase 3 seam 52)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/auth-session.js"

HEADER = '''\
// ====================================================================
// SECTION: AUTH + SESSION
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initAuthSession(...).
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

let pendingForcedPasswordChange = false;

/** DOM refs bound once during init. */
let appRoot;
let sessionPill;
let topbarUser;
let topbarAvatar;
let sidebarAvatar;
let sidebarUserName;
let sidebarUserRole;
let loginEmail;
let loginPassword;
let tokenInput;
let accountMenuPanel;
let accountMenuTrigger;
let passwordForm;
let passwordStatus;
let passwordDialog;
let currentPasswordInput;
let newPasswordInput;
let confirmNewPasswordInput;
let currentOrgType;
let currentOrgTenant;
let dashboardPreview;
let apiOutput;
let moduleState;

export function initAuthSession(injected) {
  deps = injected;
  appRoot = injected.appRoot;
  sessionPill = injected.sessionPill;
  topbarUser = injected.topbarUser;
  topbarAvatar = injected.topbarAvatar;
  sidebarAvatar = injected.sidebarAvatar;
  sidebarUserName = injected.sidebarUserName;
  sidebarUserRole = injected.sidebarUserRole;
  loginEmail = injected.loginEmail;
  loginPassword = injected.loginPassword;
  tokenInput = injected.tokenInput;
  accountMenuPanel = injected.accountMenuPanel;
  accountMenuTrigger = injected.accountMenuTrigger;
  passwordForm = injected.passwordForm;
  passwordStatus = injected.passwordStatus;
  passwordDialog = injected.passwordDialog;
  currentPasswordInput = injected.currentPasswordInput;
  newPasswordInput = injected.newPasswordInput;
  confirmNewPasswordInput = injected.confirmNewPasswordInput;
  currentOrgType = injected.currentOrgType;
  currentOrgTenant = injected.currentOrgTenant;
  dashboardPreview = injected.dashboardPreview;
  apiOutput = injected.apiOutput;
  moduleState = injected.moduleState;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initAuthSession() must be called before using auth-session helpers");
  }
  return deps;
}

function getAccessToken() { return requireDeps().getAccessToken(); }
function getRefreshToken() { return requireDeps().getRefreshToken(); }
function clearAllTokens() { return requireDeps().clearAllTokens(); }
function clearAccessToken() { return requireDeps().clearAccessToken(); }
function setAccessToken(value) { return requireDeps().setAccessToken(value); }
function setRefreshToken(value) { return requireDeps().setRefreshToken(value); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function setCurrentExperience(value) { requireDeps().setCurrentExperience(value); }
function getLastModuleContext() { return requireDeps().getLastModuleContext(); }
function setLastModuleContext(value) { requireDeps().setLastModuleContext(value); }
function getSelectedOrgType() { return requireDeps().getSelectedOrgType(); }
function getOrgSelectorMeta() { return requireDeps().getOrgSelectorMeta(); }
function getExperienceAppKeys() { return requireDeps().getExperienceAppKeys(); }
function getAppKey() { return requireDeps().getAppKey(); }
function getLoginEmailStorageKey() { return requireDeps().getLoginEmailStorageKey(); }
function getDefaultMitraBooksLoginEmail() { return requireDeps().getDefaultMitraBooksLoginEmail(); }
function getLoginRequestTimeoutMs() { return requireDeps().getLoginRequestTimeoutMs(); }
function apiRequest(...args) { return requireDeps().apiRequest(...args); }
function renderJson(...args) { return requireDeps().renderJson(...args); }
function setLoginStatus(...args) { return requireDeps().setLoginStatus(...args); }
function setAuthPanelMode(...args) { return requireDeps().setAuthPanelMode(...args); }
function statusDetailText(...args) { return requireDeps().statusDetailText(...args); }
function escapeHtml(...args) { return requireDeps().escapeHtml(...args); }
function setLastBusinessAccounts(...args) { return requireDeps().setLastBusinessAccounts(...args); }
function setLastBusinessParties(...args) { return requireDeps().setLastBusinessParties(...args); }
function clearVoucherListState(...args) { return requireDeps().clearVoucherListState(...args); }
function setLastAccountingDrilldown(...args) { return requireDeps().setLastAccountingDrilldown(...args); }
function renderModules(...args) { return requireDeps().renderModules(...args); }
function renderModuleState(...args) { return requireDeps().renderModuleState(...args); }
function initialExperience(...args) { return requireDeps().initialExperience(...args); }
function mandirPublicPaymentPageUrl(...args) { return requireDeps().mandirPublicPaymentPageUrl(...args); }
function loadAndRenderGroupedNav(...args) { return requireDeps().loadAndRenderGroupedNav(...args); }
function showMandirSplash(...args) { return requireDeps().showMandirSplash(...args); }
function hideMandirSplash(...args) { return requireDeps().hideMandirSplash(...args); }
function runChecks(...args) { return requireDeps().runChecks(...args); }
function delay(...args) { return requireDeps().delay(...args); }

'''

EXPORT_FUNCS = [
    "hasTrustedSession",
    "updateSessionUi",
    "compactAccountLabel",
    "signOutAndReturnToLogin",
    "closeAccountMenu",
    "openPasswordDialog",
    "loadCurrentUserProfile",
    "completeWorkspaceSignIn",
    "_showPasswordError",
    "_clearPasswordError",
    "updateCurrentPassword",
    "activeOrgSelectorType",
    "syncOrgSelectorOptions",
    "updateTrustedContextUi",
    "signInWithPassword",
]


def find_fn_block(lines: list[str], name: str) -> tuple[int, int]:
    start = next(
        i
        for i, l in enumerate(lines)
        if re.match(rf"^(async )?function {re.escape(name)}\b", l.lstrip())
    )
    depth = 0
    started = False
    end = start
    for i in range(start, len(lines)):
        line = lines[i]
        if "{" in line or "}" in line:
            depth += line.count("{") - line.count("}")
            started = True
        if started and depth <= 0:
            end = i + 1
            break
    else:
        raise SystemExit(f"unterminated function for {name}")
    while end < len(lines) and lines[end].strip() == "":
        end += 1
    return start, end


def rewrite_block(block: str) -> str:
    replacements = [
        ("EXPERIENCE_APP_KEYS", "getExperienceAppKeys()"),
        ("APP_KEY", "getAppKey()"),
        ("LOGIN_EMAIL_STORAGE_KEY", "getLoginEmailStorageKey()"),
        ("DEFAULT_MITRABOOKS_LOGIN_EMAIL", "getDefaultMitraBooksLoginEmail()"),
        ("LOGIN_REQUEST_TIMEOUT_MS", "getLoginRequestTimeoutMs()"),
        ("orgSelectorMeta", "getOrgSelectorMeta()"),
        ("selectedOrgType", "getSelectedOrgType()"),
        ("lastModuleContext", "getLastModuleContext()"),
        ("currentExperience", "getCurrentExperience()"),
    ]
    for old, new in replacements:
        block = block.replace(old, new)

    # Fix double-wrap from case-sensitive partial matches (none expected for these).
    for name in (
        "ExperienceAppKeys",
        "AppKey",
        "LoginEmailStorageKey",
        "DefaultMitraBooksLoginEmail",
        "LoginRequestTimeoutMs",
        "OrgSelectorMeta",
        "SelectedOrgType",
        "LastModuleContext",
        "CurrentExperience",
    ):
        block = block.replace(f"get{name}()()", f"get{name}()")

    block = block.replace(
        "lastModuleContext = null;",
        "setLastModuleContext(null);",
    )
    # After lastModuleContext → getLastModuleContext(), assignment becomes broken:
    block = block.replace(
        "getLastModuleContext() = null;",
        "setLastModuleContext(null);",
    )
    block = block.replace(
        "getCurrentExperience() = initialExperience();",
        "setCurrentExperience(initialExperience());",
    )
    block = block.replace(
        "context = getLastModuleContext()",
        "context = getLastModuleContext()",
    )
    return block


def main() -> None:
    if OUT.exists() and "export function signInWithPassword" in OUT.read_text(encoding="utf-8"):
        print("Already extracted")
        return

    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)

    # Drop shell-owned pendingForcedPasswordChange; module owns it.
    pending_idx = next(
        (i for i, l in enumerate(lines) if l.strip() == "let pendingForcedPasswordChange = false;"),
        None,
    )
    if pending_idx is None:
        raise SystemExit("pendingForcedPasswordChange not found")
    del lines[pending_idx]
    if pending_idx < len(lines) and lines[pending_idx].strip() == "":
        del lines[pending_idx]

    spans: list[tuple[int, int, str]] = []
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

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in block and f"export async function {name}" not in block:
            raise SystemExit(f"export missing for {name}")

    text = "".join(lines)
    text = re.sub(
        r"(?ms)^// ═+\n// SECTION: AUTH \+ SESSION\n.*?^// ═+\n\n+",
        "// Auth + session helpers live in modules/workspaces/auth-session.js\n\n",
        text,
        count=1,
    )

    module = HEADER + block
    if not module.endswith("\n"):
        module += "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")
    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(module.splitlines())} lines)")
    print(f"Updated {APP.relative_to(ROOT)} ({len(text.splitlines())} lines)")


if __name__ == "__main__":
    main()
