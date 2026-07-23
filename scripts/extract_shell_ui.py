#!/usr/bin/env python3
"""Extract sidebar / org / FY / quick-action listeners into modules/shell-ui.js.

Pure move (Phase 3 seam 13). Two non-contiguous blocks:
  A) Theme toggle buttons + SIDEBAR UI INTERACTIONS (org/FY)
  B) Quick-action helpers + buttons + document-entry keyboard

Health widget helpers and page bootstrap stay in app.js.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/shell-ui.js"

HEADER = """\
// ====================================================================
// SECTION: SHELL UI — theme toggles, sidebar org/FY, quick actions
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: listener bodies unchanged aside from deps.<binding> for shell
// bindings (keeps mutable let assignment semantics). Wire via initShellUi.
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

export function initShellUi(injected) {
  deps = injected;
  installShellUi();
}

function requireDeps() {
  if (!deps) {
    throw new Error("initShellUi() must be called before registering shell UI handlers");
  }
  return deps;
}

function installShellUi() {
  const deps = requireDeps();

BODY_PLACEHOLDER
}
"""

SKIP = {
    "document", "window", "console", "event", "Error", "Promise", "JSON", "Math",
    "Date", "String", "Number", "Boolean", "Array", "Object", "Map", "Set",
    "parseInt", "parseFloat", "isFinite", "encodeURIComponent", "confirm",
    "alert", "prompt", "localStorage", "sessionStorage", "navigator", "location",
    "URL", "Blob", "File", "FormData", "undefined", "null", "NaN", "Infinity",
    "true", "false", "this", "arguments", "async", "await", "of", "in", "new",
    "typeof", "instanceof", "void", "delete", "return", "if", "else", "for",
    "while", "do", "switch", "case", "break", "continue", "try", "catch",
    "finally", "throw", "class", "extends", "super", "import", "export",
    "default", "from", "as", "let", "const", "var", "function", "yield",
    "debugger", "with", "get", "set",
}

DOMISH = {
    "hidden", "value", "checked", "disabled", "focus", "click", "submit",
    "target", "currentTarget", "key", "ctrlKey", "altKey", "shiftKey",
    "metaKey", "preventDefault", "stopPropagation", "closest", "matches",
    "getAttribute", "setAttribute", "querySelector", "querySelectorAll",
    "getElementById", "addEventListener", "classList", "dataset", "innerHTML",
    "textContent", "contains", "toggle", "add", "remove", "length", "forEach",
    "toLowerCase", "trim", "then", "catch", "href", "src", "type", "name",
    "id", "status", "button", "link", "input", "form", "option", "select",
    "data", "view", "workspace", "key", "formConfig", "workspaceByKey",
    "orgType", "selectorMeta", "isOpen", "fy", "e", "o", "percentage",
}


def strip_strings_and_comments(src: str) -> str:
    out = []
    i = 0
    n = len(src)
    while i < n:
        ch = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if ch == "/" and nxt == "/":
            while i < n and src[i] != "\n":
                out.append(" ")
                i += 1
            continue
        if ch == "/" and nxt == "*":
            out.extend([" ", " "])
            i += 2
            while i < n - 1 and not (src[i] == "*" and src[i + 1] == "/"):
                out.append("\n" if src[i] == "\n" else " ")
                i += 1
            if i < n - 1:
                out.extend([" ", " "])
                i += 2
            continue
        if ch in "\"'`":
            quote = ch
            out.append(" ")
            i += 1
            while i < n:
                c = src[i]
                if c == "\\" and quote != "`":
                    out.append(" ")
                    if i + 1 < n:
                        out.append(" ")
                        i += 2
                    else:
                        i += 1
                    continue
                if quote == "`" and c == "$" and i + 1 < n and src[i + 1] == "{":
                    out.extend([" ", " "])
                    i += 2
                    depth = 1
                    start = i
                    while i < n and depth:
                        if src[i] == "{":
                            depth += 1
                        elif src[i] == "}":
                            depth -= 1
                        i += 1
                    out.append(strip_strings_and_comments(src[start : i - 1]))
                    out.append(" ")
                    continue
                if c == quote:
                    out.append(" ")
                    i += 1
                    break
                out.append("\n" if c == "\n" else " ")
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def blank_member_properties(clean: str) -> str:
    return re.sub(r"(\?\.)([A-Za-z_][A-Za-z0-9_]*)|(\.)([A-Za-z_][A-Za-z0-9_]*)", " ", clean)


def collect_declared(clean: str) -> set[str]:
    declared: set[str] = set()
    for m in re.finditer(r"\b(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)", clean):
        declared.add(m.group(1))
    for m in re.finditer(r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)", clean):
        declared.add(m.group(1))
    for m in re.finditer(r"\b(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)", clean):
        declared.add(m.group(1))
    for m in re.finditer(r"\(([^)]*)\)\s*=>", clean):
        for part in m.group(1).split(","):
            part = part.strip().lstrip(".")
            name = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)", part)
            if name:
                declared.add(name.group(1))
    for m in re.finditer(r"function\s*[A-Za-z0-9_]*\s*\(([^)]*)\)", clean):
        for part in m.group(1).split(","):
            part = part.strip().lstrip(".")
            name = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)", part)
            if name:
                declared.add(name.group(1))
    return declared


def collect_app_shell_bindings(pre: str) -> set[str]:
    clean = strip_strings_and_comments(pre)
    bindings: set[str] = set()
    for m in re.finditer(r"(?m)^(async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", clean):
        bindings.add(m.group(2))
    for m in re.finditer(r"(?m)^(const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\b", clean):
        bindings.add(m.group(2))
    for m in re.finditer(r"(?m)^import\s+\{([^}]+)\}\s+from\s+", pre):
        for part in m.group(1).split(","):
            part = part.strip()
            if " as " in part:
                part = part.split(" as ")[-1].strip()
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", part):
                bindings.add(part)
    for m in re.finditer(r"(?m)^import\s+([A-Za-z_][A-Za-z0-9_]*)\s+from\s+", pre):
        bindings.add(m.group(1))
    return bindings


def rewrite_free_to_deps(src: str, free: set[str]) -> str:
    out: list[str] = []
    i = 0
    n = len(src)

    def is_ident_start(c: str) -> bool:
        return c.isalpha() or c == "_"

    def is_ident_cont(c: str) -> bool:
        return c.isalnum() or c == "_"

    while i < n:
        ch = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if ch == "/" and nxt == "/":
            while i < n and src[i] != "\n":
                out.append(src[i])
                i += 1
            continue
        if ch == "/" and nxt == "*":
            out.append(src[i]); out.append(src[i + 1]); i += 2
            while i < n - 1 and not (src[i] == "*" and src[i + 1] == "/"):
                out.append(src[i]); i += 1
            if i < n - 1:
                out.append(src[i]); out.append(src[i + 1]); i += 2
            continue
        if ch in "\"'`":
            quote = ch
            out.append(ch); i += 1
            while i < n:
                c = src[i]; out.append(c)
                if c == "\\" and quote != "`" and i + 1 < n:
                    out.append(src[i + 1]); i += 2; continue
                if quote == "`" and c == "$" and i + 1 < n and src[i + 1] == "{":
                    i += 1; out.append(src[i]); i += 1
                    depth = 1; start = i
                    while i < n and depth:
                        if src[i] == "{": depth += 1
                        elif src[i] == "}": depth -= 1
                        i += 1
                    out.append(rewrite_free_to_deps(src[start : i - 1], free))
                    out.append("}")
                    continue
                i += 1
                if c == quote:
                    break
            continue

        if is_ident_start(ch):
            j = i + 1
            while j < n and is_ident_cont(src[j]):
                j += 1
            ident = src[i:j]
            k = i - 1
            while k >= 0 and src[k] in " \t\n\r":
                k -= 1
            preceded_by_dot = False
            if k >= 2 and src[k - 2 : k + 1] == "...":
                preceded_by_dot = False
            elif k >= 0 and src[k] == ".":
                if k >= 2 and src[k - 2 : k + 1] == "...":
                    preceded_by_dot = False
                else:
                    preceded_by_dot = True
            elif k >= 1 and src[k - 1 : k + 1] == "?.":
                preceded_by_dot = True

            k2 = j
            while k2 < n and src[k2] in " \t\n\r":
                k2 += 1
            is_object_key = k2 < n and src[k2] == ":"
            if is_object_key:
                t = i - 1
                saw_q = False
                while t >= 0:
                    c = src[t]
                    if c in "{,([;" or src[t : t + 6] == "return":
                        break
                    if c == "?" and (t == 0 or src[t - 1] != "?"):
                        if t + 1 < n and src[t + 1] == ".":
                            t -= 1
                            continue
                        saw_q = True
                        break
                    if c in "}])":
                        break
                    t -= 1
                if saw_q:
                    is_object_key = False

            if ident in free and not preceded_by_dot and not is_object_key:
                out.append(f"deps.{ident}")
            else:
                out.append(ident)
            i = j
            continue

        out.append(ch)
        i += 1
    return "".join(out)


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)

    # Block A: theme toggle comment through end of outside-click handler
    a_start = next(i for i, l in enumerate(lines) if "Theme toggle buttons" in l)
    a_end = next(
        i for i, l in enumerate(lines)
        if i > a_start and "HEADER & HEALTH WIDGET" in l
    )
    while a_end > a_start and lines[a_end - 1].strip() == "":
        a_end -= 1

    # Block B: Quick Action Buttons through handleBusinessDocumentEntryKeyboard registration
    b_start = next(i for i, l in enumerate(lines) if "Quick Action Buttons" in l)
    # include the doc comment above if present
    if b_start >= 1 and lines[b_start - 1].strip().startswith("/**"):
        # walk up to start of comment
        j = b_start - 1
        while j > 0 and not lines[j].strip().startswith("/**"):
            j -= 1
        # actually Quick Action is after health - find " * Quick Action"
        pass
    b_start = next(i for i, l in enumerate(lines) if re.search(r"Quick Action Buttons", l))
    # include leading /** block
    j = b_start
    while j > 0 and lines[j - 1].strip() in ("",) or (
        j > 0 and (lines[j - 1].strip().startswith("*") or lines[j - 1].strip().startswith("/**"))
    ):
        if lines[j - 1].strip().startswith("/**"):
            j -= 1
            break
        j -= 1
    # simpler: start at the /** immediately above Quick Action
    for k in range(b_start, max(0, b_start - 6), -1):
        if lines[k].strip().startswith("/**"):
            b_start = k
            break

    b_end = next(
        i for i, l in enumerate(lines)
        if i > b_start and l.startswith("function updatePageHeader")
    )
    while b_end > b_start and lines[b_end - 1].strip() == "":
        b_end -= 1

    body = "".join(lines[a_start:a_end]) + "\n" + "".join(lines[b_start:b_end])
    if not body.endswith("\n"):
        body += "\n"

    shell = collect_app_shell_bindings("".join(lines[:a_start]))
    # also bindings defined only in block B helpers stay local (declared)
    clean = blank_member_properties(strip_strings_and_comments(body))
    declared = collect_declared(clean)
    used = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", clean))
    free = {
        n for n in used
        if n in shell and n not in declared and n not in SKIP and n not in DOMISH
    }
    free.discard("deps")

    rewritten = rewrite_free_to_deps(body, free)
    indented = "".join(
        ("  " + line if line.strip() else line)
        for line in rewritten.splitlines(keepends=True)
    )
    module = HEADER.replace("BODY_PLACEHOLDER", indented.rstrip() + "\n")
    line_count = module.count("\n") + (0 if module.endswith("\n") else 1)
    if line_count > 1490:
        raise SystemExit(f"shell-ui.js would be {line_count} lines — abort")

    OUT.write_text(module, encoding="utf-8", newline="\n")

    # Remove B first (higher indices), then A
    new_lines = lines[:b_start] + lines[b_end:]
    # a_end may still be valid relative to original; recompute after? Use original indices:
    # After removing B, indices >= b_end shift by -(b_end-b_start). A is before B so unchanged.
    new_lines = new_lines[:a_start] + new_lines[a_end:]
    APP.write_text("".join(new_lines), encoding="utf-8", newline="\n")

    print(f"Wrote {OUT.relative_to(ROOT)} ({line_count} lines)")
    print(f"Removed A {a_start+1}-{a_end}, B {b_start+1}-{b_end}")
    print(f"Free deps: {len(free)}")
    for n in sorted(free):
        print(f"  {n}")


if __name__ == "__main__":
    main()
