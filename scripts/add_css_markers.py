"""Insert section markers into frontend/shared/app-shell.css (one-shot, bottom-up)."""
import pathlib

FILE = pathlib.Path("frontend/shared/app-shell.css")
lines = FILE.read_text(encoding="utf-8").splitlines(keepends=True)

def marker(title, note=""):
    bar = "═" * 68
    parts = [f"\n/* {bar} */\n", f"/* SECTION: {title} */\n"]
    if note:
        parts.append(f"/* NOTE   : {note} */\n")
    parts.append(f"/* {bar} */\n\n")
    return "".join(parts)

# (insert_before_line_1indexed, title, note)
SECTIONS = [
    (6031, "AUTHENTICATION FLOW",
     "Signed-out/signed-in visibility toggling via .app.signed-out / .app.signed-in classes"),

    (5812, "RESPONSIVE — media queries (max-width: 900px)",
     "Mobile layout overrides: sidebar collapses, single-column grid, topbar stack"),

    (5800, "HOME LINKS",
     "Platform home page link grid (.home-links)"),

    (5715, "PILLS / BADGES / MODULE STATE",
     ".pill .ok .warn .danger .neutral  .module-state"),

    (1748, "LEGALMITRA STYLES",
     ".workspace-tabs  .legal-top  .legal-header  .legal-nav  .legal-landing  .legal-chat-*  .legal-history-*  .legal-login-*  .legal-ai-hero  .legal-plan-*  .legal-article-*  .legal-footer  etc."),

    (1694, "DIALOGS + FORM COMPONENTS",
     ".dialog-head  .dialog-actions  .field-label  .checkbox-grid  .checkbox-option  .list-filter-panel  .list-filter-bar"),

    (1355, "ERP TABLE + TYPE CHIPS + EMPTY STATES",
     ".erp-table (dark-header table for MitraBooks, app:not(.mandir-domain) overrides)  .type-chip  .empty-state  .list-filter-bar"),

    (1181, "DASHBOARD GRID + TABLE PREVIEW",
     ".dashboard-main-grid  .table-preview (compact card-style preview table shared across products)"),

    (1095, "PREVIEW HEADING + DASHBOARD METRIC TILES",
     ".preview-heading  .mandir-dashboard .metric-tile  .verification-panel  .gruha-dashboard .metric-tile"),

    (941,  "ERP WORKSPACE — business dashboard + health panel",
     ".business-dashboard  .erp-workspace-panel  .erp-command-grid  .erp-health-panel  .erp-health-list  .erp-health-actions"),

    (825,  "CARDS + FORM CONTROLS + BUTTONS",
     ".card  .field  input  select  button  button.secondary  button.danger"),

    (775,  "TOPBAR BAR",
     ".topbar  .topbar h2  (inner layout; topbar-actions are in TOPBAR ACTIONS section above)"),

    (634,  "SIDEBAR + NAV",
     ".sidebar  .mandir-theme .sidebar  .gruha-theme .sidebar  .invest-theme .sidebar  .nav  .nav a  .nav button  .nav a.active  .nav a.locked"),

    (575,  "ACCESS PANEL",
     ".access-panel  .access-panel-head  (auth/permission gate overlay)"),

    (459,  "MANDIRMITRA — Login + splash screen",
     ".mandir-login-brand  .mandir-login-lock  .mandir-login-links  .mandir-splash  .mandir-splash-frame"),

    (65,   "TOPBAR ACTIONS",
     ".topbar-actions and child elements  (action strip rendered into the right side of the topbar)"),

    (48,   "APP SHELL LAYOUT",
     ".app — outermost grid wrapper (sidebar + content columns)"),

    (1,    "DESIGN TOKENS + RESET",
     ":root CSS variables (--bg, --panel, --text, --accent, --border, --danger, --warning, --success)  *  html  body  a"),
]

# Insert bottom-up so earlier line numbers stay valid
for (line1, title, note) in sorted(SECTIONS, key=lambda x: -x[0]):
    idx = line1 - 1
    insert_text = marker(title, note)
    lines.insert(idx, insert_text)

FILE.write_text("".join(lines), encoding="utf-8")
print(f"Done — inserted {len(SECTIONS)} section markers into {FILE}")
