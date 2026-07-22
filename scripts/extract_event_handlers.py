#!/usr/bin/env python3
"""Extract app.js EVENT HANDLERS into modules/events.js (Phase 3 final seam).

Pure move of the SECTION: EVENT HANDLERS block (through experience mode buttons).
Free identifiers are rewritten to deps.<binding> so mutable let assignments in app.js
remain correct via getters/setters passed from initEventHandlers({...}).

Sidebar / quick-action listeners stay in app.js (follow-up if needed).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/events.js"

HEADER = """\
// ====================================================================
// SECTION: EVENT HANDLERS — click / change / input / keydown
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: listener bodies unchanged aside from deps.<binding> for shell
// bindings (keeps mutable let assignment semantics). Wire via initEventHandlers.
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

export function initEventHandlers(injected) {
  deps = injected;
  installEventHandlers();
}

function requireDeps() {
  if (!deps) {
    throw new Error("initEventHandlers() must be called before registering handlers");
  }
  return deps;
}

function installEventHandlers() {
  const deps = requireDeps();

BODY_PLACEHOLDER
}
"""

SKIP = {
    "document", "window", "console", "event", "Error", "Promise", "JSON", "Math",
    "Date", "String", "Number", "Boolean", "Array", "Object", "Map", "Set",
    "parseInt", "parseFloat", "isFinite", "encodeURIComponent", "confirm",
    "alert", "prompt", "localStorage", "sessionStorage", "navigator", "location",
    "URL", "Blob", "File", "FormData", "Headers", "Request", "Response",
    "HTMLElement", "Element", "Node", "undefined", "null", "NaN", "Infinity",
    "true", "false", "this", "arguments", "async", "await", "of", "in", "new",
    "typeof", "instanceof", "void", "delete", "return", "if", "else", "for",
    "while", "do", "switch", "case", "break", "continue", "try", "catch",
    "finally", "throw", "class", "extends", "super", "import", "export",
    "default", "from", "as", "let", "const", "var", "function", "yield",
    "debugger", "with", "enum", "implements", "interface", "package",
    "private", "protected", "public", "static", "get", "set",
}

DOMISH = {
    "hidden", "value", "checked", "disabled", "focus", "click", "submit",
    "target", "currentTarget", "key", "ctrlKey", "altKey", "shiftKey",
    "metaKey", "preventDefault", "stopPropagation", "closest", "matches",
    "getAttribute", "setAttribute", "hasAttribute", "removeAttribute",
    "querySelector", "querySelectorAll", "getElementById", "addEventListener",
    "classList", "dataset", "innerHTML", "textContent", "appendChild",
    "remove", "contains", "toggle", "add", "length", "push", "pop", "map",
    "filter", "find", "forEach", "some", "every", "reduce", "includes",
    "startsWith", "endsWith", "replace", "split", "join", "trim",
    "toLowerCase", "toUpperCase", "slice", "splice", "stringify", "parse",
    "then", "catch", "finally", "href", "src", "type", "name", "id",
    "method", "status", "ok", "payload", "items", "detail", "title",
    "label", "message", "error", "code", "rate", "amount", "date", "notes",
    "files", "file", "result", "reason", "kind", "view", "panel", "dialog",
    "button", "link", "input", "form", "option", "select", "row", "rows",
    "line", "lines", "data", "meta", "copy", "tone", "tab", "priority",
    "progress", "timeoutMs", "surfaceErrors", "requestId", "action",
    "mandirAction", "gruhaAction", "accountingAction", "businessAction",
    "coaAction", "partyId", "orgType", "isOpen", "selectorMeta", "formConfig",
    "appKey", "style", "reset", "round", "resent",
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
    for m in re.finditer(r"\b(?:const|let|var)\s*\{([^}]+)\}", clean):
        for part in m.group(1).split(","):
            part = part.strip()
            if not part or part.startswith("..."):
                continue
            if ":" in part:
                left, right = part.split(":", 1)
                declared.add(left.strip())
                right = right.strip().split("=")[0].strip()
                if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", right):
                    declared.add(right)
            else:
                name = part.split("=")[0].strip()
                if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
                    declared.add(name)
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
    for m in re.finditer(r"\bcatch\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)", clean):
        declared.add(m.group(1))
    return declared


def rewrite_free_to_deps(src: str, free: set[str]) -> str:
    """Rewrite free identifiers to deps.NAME, skipping strings/comments and member props."""
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
            out.append(src[i])
            out.append(src[i + 1])
            i += 2
            while i < n - 1 and not (src[i] == "*" and src[i + 1] == "/"):
                out.append(src[i])
                i += 1
            if i < n - 1:
                out.append(src[i])
                out.append(src[i + 1])
                i += 2
            continue
        if ch in "\"'`":
            quote = ch
            out.append(ch)
            i += 1
            while i < n:
                c = src[i]
                out.append(c)
                if c == "\\" and quote != "`" and i + 1 < n:
                    out.append(src[i + 1])
                    i += 2
                    continue
                if quote == "`" and c == "$" and i + 1 < n and src[i + 1] == "{":
                    # already appended '$'; append '{' then rewrite expression
                    i += 1
                    out.append(src[i])  # {
                    i += 1
                    depth = 1
                    start = i
                    while i < n and depth:
                        if src[i] == "{":
                            depth += 1
                        elif src[i] == "}":
                            depth -= 1
                        i += 1
                    expr = src[start : i - 1]
                    out.append(rewrite_free_to_deps(expr, free))
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
            # preceded by . or ?.  → property, do not rewrite
            # BUT `...ident` is spread, not member access (third `.` would false-positive).
            k = i - 1
            while k >= 0 and src[k] in " \t\n\r":
                k -= 1
            preceded_by_dot = False
            if k >= 2 and src[k - 2 : k + 1] == "...":
                preceded_by_dot = False
            elif k >= 0 and src[k] == ".":
                # single/double-dot member; exclude spread already handled
                if k >= 1 and src[k - 1] == ".":
                    # `..` leftover — treat as not a member prop rewrite skip only if `...`
                    if k >= 2 and src[k - 2] == ".":
                        preceded_by_dot = False
                    else:
                        preceded_by_dot = True
                else:
                    preceded_by_dot = True
            elif k >= 1 and src[k - 1 : k + 1] == "?.":
                preceded_by_dot = True
            elif k >= 0 and src[k] == "?" and k + 1 < i and src[k + 1] == ".":
                preceded_by_dot = True

            # Object-literal keys must stay bare: `{ client_name: ... }` / shorthand.
            k2 = j
            while k2 < n and src[k2] in " \t\n\r":
                k2 += 1
            is_object_key = k2 < n and src[k2] == ":" and not (
                # ternary: `cond ? ident :` — keep rewrite for the middle operand
                # Heuristic: if `?` appears before ident at same nesting depth without
                # an intervening `{` or `,` or `(`, treat as ternary middle.
                False  # refined below
            )
            if is_object_key:
                # Distinguish ternary `a ? b : c` from `{ b: c }` by scanning left
                # for unmatched `?` vs `{` / `,` / `(` / `[` / `=>` / `=` / `return`.
                t = i - 1
                saw_q = False
                while t >= 0:
                    c = src[t]
                    if c in "{,([;" or src[t : t + 6] == "return":
                        break
                    if c == "?" and (t == 0 or src[t - 1] != "?"):
                        # skip `?.`
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


def collect_app_shell_bindings(pre_section: str) -> set[str]:
    """Top-level functions/lets/consts in app.js before the event-handler section."""
    clean = strip_strings_and_comments(pre_section)
    bindings: set[str] = set()
    # Approximate top-level: line starts with function/let/const/var (possibly async)
    for m in re.finditer(
        r"(?m)^(async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        clean,
    ):
        bindings.add(m.group(2))
    for m in re.finditer(
        r"(?m)^(export\s+)?(async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        clean,
    ):
        bindings.add(m.group(3))
    for m in re.finditer(
        r"(?m)^(const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\b",
        clean,
    ):
        bindings.add(m.group(2))
    # imported bindings
    for m in re.finditer(
        r"(?m)^import\s+\{([^}]+)\}\s+from\s+",
        pre_section,
    ):
        for part in m.group(1).split(","):
            part = part.strip()
            if not part:
                continue
            if " as " in part:
                part = part.split(" as ")[-1].strip()
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", part):
                bindings.add(part)
    for m in re.finditer(
        r"(?m)^import\s+([A-Za-z_][A-Za-z0-9_]*)\s+from\s+",
        pre_section,
    ):
        bindings.add(m.group(1))
    return bindings


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)

    a_start = next(i for i, l in enumerate(lines) if "SECTION: EVENT HANDLERS" in l)
    a_end = next(i for i, l in enumerate(lines) if i > a_start and "Wire widget system deps" in l)
    while a_end > a_start and lines[a_end - 1].strip() == "":
        a_end -= 1

    body = "".join(lines[a_start:a_end])
    if not body.endswith("\n"):
        body += "\n"

    shell = collect_app_shell_bindings("".join(lines[:a_start]))
    clean = blank_member_properties(strip_strings_and_comments(body))
    declared = collect_declared(clean)
    used = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", clean))
    free = {
        n
        for n in used
        if n in shell
        and n not in declared
        and n not in SKIP
        and n not in DOMISH
    }
    # Never rewrite the local deps binding we introduce
    free.discard("deps")

    rewritten = rewrite_free_to_deps(body, free)
    # Indent body one level inside installEventHandlers
    indented = "".join(
        ("  " + line if line.strip() else line)
        for line in rewritten.splitlines(keepends=True)
    )

    module = HEADER.replace("BODY_PLACEHOLDER", indented.rstrip() + "\n")
    line_count = module.count("\n") + (0 if module.endswith("\n") else 1)
    if line_count > 1490:
        raise SystemExit(f"events.js would be {line_count} lines — abort")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")

    APP.write_text("".join(lines[:a_start] + lines[a_end:]), encoding="utf-8", newline="\n")

    print(f"Wrote {OUT.relative_to(ROOT)} ({line_count} lines)")
    print(f"Removed app.js lines {a_start+1}-{a_end}")
    print(f"Free deps rewritten: {len(free)}")
    for n in sorted(free):
        print(f"  {n}")


if __name__ == "__main__":
    main()
