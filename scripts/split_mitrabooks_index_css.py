"""Split frontend/mitrabooks-erp/index.css into modular sheets under styles/.

Preserves exact rule order via @import from index.css (single entry point).
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "frontend" / "mitrabooks-erp" / "index.css"
STYLES = ROOT / "frontend" / "mitrabooks-erp" / "styles"

# Inclusive 1-based end lines for each chunk (from section banners in index.css).
CHUNKS: list[tuple[str, int, int, str]] = [
    ("index-theme.css", 1, 288, "Theme tokens and base control/widget overrides"),
    ("index-shell.css", 289, 878, "Redesigned shell, signed-out layout, chrome"),
    ("index-platform.css", 879, 1917, "Platform/legacy dashboard and CA workspace surfaces"),
    ("index-dashboard-widgets.css", 1918, 2605, "Dashboard widget controls and chrome"),
    ("index-business-dashboard.css", 2606, 3383, "Clean business / executive dashboard"),
    ("index-auth-profile.css", 3384, 4133, "User profile, credentials, login form"),
    ("index-forms-reports.css", 4134, 10_000_000, "Account selector, vouchers, reports, settings"),
]


def main() -> None:
    lines = CSS.read_text(encoding="utf-8").splitlines(keepends=True)
    total = len(lines)
    STYLES.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    for name, start, end, title in CHUNKS:
        lo = start - 1
        hi = min(end, total)
        chunk = lines[lo:hi]
        if not chunk:
            raise SystemExit(f"Empty chunk for {name} ({start}-{end})")
        header = (
            f"/*\n"
            f"  MitraBooks ERP — {title}\n"
            f"  Extracted from index.css (lines {start}-{hi}) without rule reordering.\n"
            f"  Loaded via index.css @import; do not link this file alone unless load order is preserved.\n"
            f"*/\n\n"
        )
        out = STYLES / name
        out.write_text(header + "".join(chunk), encoding="utf-8", newline="\n")
        written.append(name)
        print(f"wrote {out.relative_to(ROOT)} ({len(chunk)} lines)")

    imports = "\n".join(f'@import url("./styles/{name}");' for name in written)
    index_body = (
        "/*\n"
        "  =========================================\n"
        "  MitraBooks ERP - Theme Enhancement CSS\n"
        "  =========================================\n"
        "  Entry point only. Rules live in ./styles/* and load in this exact order\n"
        "  so cascade behavior matches the former monolithic index.css.\n"
        "*/\n\n"
        f"{imports}\n"
    )
    CSS.write_text(index_body, encoding="utf-8", newline="\n")
    print(f"rewrote {CSS.relative_to(ROOT)} as import entry ({len(index_body.splitlines())} lines)")


if __name__ == "__main__":
    main()
