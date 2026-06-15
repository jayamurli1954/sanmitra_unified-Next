"""Insert section markers into app/modules/mandir_compat/router.py (one-shot, bottom-up)."""
import pathlib

FILE = pathlib.Path("app/modules/mandir_compat/router.py")
lines = FILE.read_text(encoding="utf-8").splitlines(keepends=True)

def marker(title, routes="", note=""):
    bar = "═" * 72
    parts = [f"\n# {bar}\n", f"# SECTION: {title}\n"]
    if routes:
        parts.append(f"# ROUTES : {routes}\n")
    if note:
        parts.append(f"# NOTE   : {note}\n")
    parts.append(f"# {bar}\n\n")
    return "".join(parts)

# (insert_before_line_1indexed, title, routes, note)
SECTIONS = [
    # ── ROUTES ──────────────────────────────────────────────────────────────
    (9754, "ROUTES: Seva reminders (trigger / upcoming / config)",
     "POST /sevas/reminders/trigger  GET .../upcoming  PATCH .../reminder-config  GET /users/me",
     ""),

    (9044, "ROUTES: Seva bookings (POST / quick-ticket / GET / receipt PDF / cancel / reschedule / approve)",
     "POST /sevas/bookings  POST .../quick-ticket  GET .../bookings  GET .../receipt/pdf  POST .../cancel  PUT .../reschedule  POST .../approve-reschedule  GET .../pending",
     ""),

    (8987, "ROUTES: Users (GET list / PUT profile)",
     "GET /users  PUT /users/{user_id}",
     ""),

    (8835, "ROUTES: UPI payments management (list / quick-log)",
     "GET /upi-payments  POST .../quick-log",
     ""),

    (8405, "ROUTES: Public payments management (list / exceptions / reject / correct / verify)",
     "GET /public-payments  GET .../exceptions  PATCH .../reject|correction|verify",
     ""),

    (8185, "ROUTES: Public seva payments (create / status)",
     "POST /public/temples/{temple_id}/seva-payments  GET /public/payments/{payment_id}/status",
     ""),

    (7993, "ROUTES: Public endpoints (temples list / info / sevas / autofill / pincode / donation-categories)",
     "GET /public/temples  GET .../info  GET .../sevas  GET .../devotee/autofill  GET .../donation-categories  GET /public/location/pincode",
     ""),

    (7934, "ROUTES: Version + public UPI intent",
     "GET /mandir/version  GET /public/temples/{temple_id}/upi-intent",
     ""),

    (7804, "ROUTES: UPI payments config (GET / PUT)",
     "GET /upi-payments/config  PUT .../config",
     ""),

    (7471, "ROUTES: Setup wizard + Temples management (CRUD / activate / deactivate / onboard / upload / modules config)",
     "GET /setup-wizard/status  GET /temples  POST /temples/{id}/activate|deactivate|remove  POST /temples/onboard  POST .../upload  GET|PUT .../modules/config",
     ""),

    (7388, "ROUTES: Role permissions (GET list / PUT / GET assignable)",
     "GET /role-permissions  PUT .../role-permissions/{role_key}  GET .../assignable",
     ""),

    (7226, "ROUTES: Reports (donations category-wise / detailed / sevas / daily / monthly / export)",
     "GET /reports/donations/category-wise|detailed  GET /reports/sevas/detailed|schedule  GET /donations/report/daily|monthly  GET /donations/export/excel|pdf",
     ""),

    (7210, "ROUTES: Pincode lookup",
     "GET /pincode/lookup",
     ""),

    (7007, "ROUTES: Panchang display settings + panchang on-date",
     "GET|PUT /panchang/display-settings  GET .../cities  GET /panchang/on-date  GET /panchang/on-date-full",
     ""),

    (6769, "ROUTES: Login + opening balances (template / import)",
     "POST /login  POST /login/access-token  GET /opening-balances/template  POST .../import",
     ""),

    (6169, "ROUTES: Journal entries (GET / POST / drilldown / financial reports / day-book / cash-book / bank-book)",
     "GET /journal-entries  POST .../journal-entries  GET .../reports/drilldown|balance-sheet|accounts-receivable|payable|ledger|category-income|top-donors|day-book|cash-book|bank-book",
     ""),

    (5842, "ROUTES: Inventory (items CRUD / stock-balances / summary)",
     "GET|POST /inventory/items  PUT|DELETE .../items/{item_id}  GET .../stock-balances  GET .../summary",
     ""),

    (5776, "ROUTES: Sacred events, financial closing, auth (forgot / reset), HR, hundi",
     "GET /dashboard/sacred-events  POST /financial-closing/close-month|close-year  GET .../closing-summary|financial-years|period-closings  POST /forgot-password|reset-password  GET /hr/employees|attendance  GET /hundi/masters|openings",
     ""),

    (5637, "ROUTES: Bank reconciliation (accounts / match / reconcile / statements / import / summary / entries)",
     "GET /bank-reconciliation/accounts  POST .../match|reconcile|statements/import  GET .../statements  GET .../statements/{id}/summary|entries|unmatched-book-entries",
     ""),

    (5572, "ROUTES: Assets, backup, bank accounts",
     "GET /assets  GET .../cwip|reports/summary  POST .../revaluation  GET|POST /backup-restore  GET|POST /bank-accounts",
     ""),

    (5368, "ROUTES: Accounts / COA (GET list / GET hierarchy / PUT / import legacy / initialize default)",
     "GET /accounts  GET .../hierarchy  PUT .../accounts/{account_id}  POST .../import-legacy  POST .../initialize-default",
     ""),

    (5295, "ROUTES: Temples current (GET / PUT)",
     "GET /temples/current  PUT .../current",
     ""),

    (4987, "ROUTES: Sevas (GET / POST / PUT / DELETE / import / lists / dropdown-options / payment-accounts)",
     "GET /sevas  POST .../sevas  PUT|DELETE .../sevas/{seva_id}  GET|POST .../import  GET .../priests|dropdown-options|payment-accounts",
     ""),

    (4836, "ROUTES: Devotees (GET / POST / search by mobile / autofill)",
     "GET /devotees  POST .../devotees  GET .../search/by-mobile/{phone}  GET .../autofill/by-mobile/{phone}",
     ""),

    (4334, "ROUTES: Donations (GET list / POST / cancel / receipt PDF / reconcile / cleanup / export / daily|monthly reports)",
     "GET /donations/payment-accounts|categories  GET|POST /donations  GET .../receipt/pdf  POST .../cancel|reconcile-posting  DELETE .../cleanup  GET .../report/daily|monthly  GET .../export/excel|pdf",
     ""),

    (4284, "ROUTES: Panchang (today)",
     "GET /panchang/today",
     ""),

    (4193, "ROUTES: Dashboard stats",
     "GET /dashboard/stats",
     ""),

    # ── HELPERS (listed in reverse so bottom-up insert stays stable) ─────────
    (4109, "PLATFORM + TENANT RESOLVERS",
     "",
     "_is_platform_super_admin, _resolve_tenant_for_mandir_request, _assert_platform_can_write_tenant, _payment_accounts"),

    (3856, "DEVOTEE + UPI HELPERS",
     "",
     "_upi_receipt_number, _mandir_upi_payment_view, _find_devotee_by_phone, _upsert_devotee_from_contribution, _build_upi_intent_uri"),

    (3601, "DASHBOARD STATS + SEVA BUILDERS",
     "",
     "_dashboard_posted_stats, _canonical_seva_name, _build_seva_item, _build_seva_patch, _serialize_seva_doc, _seva_import_template_csv, _normalize_phone, _parse_iso_datetime"),

    (3392, "SEVA BOOKING HELPERS",
     "",
     "_normalize_seva_category/availability/day, _today_weekday, _parse_booking_date, _validate_seva_booking_date, _count_seva_bookings_for_date, _validate_seva_booking_capacity, _compute_seva_available_today, _resolve_report_date_window, _resolve_export_window"),

    (3311, "PINCODE + DATE-WINDOW HELPERS",
     "",
     "_normalize_pincode, _lookup_pincode_city_state, _to_positive_int"),

    (2995, "RECEIPT PDF ORCHESTRATOR",
     "",
     "_build_receipt_pdf_bytes — picks WeasyPrint → Pillow → ReportLab strategy"),

    (2749, "PILLOW IMAGE RECEIPT BUILDER",
     "",
     "_build_receipt_pdf_bytes_pillow — renders receipt as PNG wrapped in PDF using Pillow"),

    (2603, "PILLOW FONT + TEXT RENDERING HELPERS",
     "",
     "_load_receipt_pillow_font, _load_receipt_latin_pillow_font, _receipt_text_runs, _draw_receipt_text, _receipt_text_width, _wrap_receipt_text, _draw_receipt_cell_text"),

    (2417, "WEASYPRINT RECEIPT PDF BUILDER",
     "",
     "_build_receipt_pdf_bytes_weasy, _receipt_weasy_font_css — HTML-to-PDF receipt via WeasyPrint"),

    (2334, "WEASYPRINT + BILINGUAL LABEL HELPERS",
     "",
     "_default_labels, _receipt_html_escape, _receipt_html_mixed, _receipt_weasy_font_css (entry)"),

    (2253, "TEMPLE RECEIPT PROFILE",
     "",
     "_build_temple_receipt_profile, _resolve_temple_receipt_profile, _bilingual_label"),

    (2059, "FONT RESOLUTION + REPORTLAB STYLES",
     "",
     "_font_candidate_paths, _resolve_font_name, _receipt_paragraph, _format_receipt_date, _format_payment_mode_for_receipt, _format_payment_mode_local, _receipt_payment_line, _compose_receipt_line_description, _extract_seva_line_items"),

    (1939, "RECEIPT TEXT COMPOSITION",
     "",
     "_as_text, _first_non_empty_text, _name_prefix_from_sources, _compose_receipt_party_name, _compose_receipt_address_line, _split_amount, _normalize_local_language, _detect_script"),

    (1860, "AMOUNT TO WORDS (English + Kannada)",
     "",
     "_integer_to_words, _amount_to_words, _integer_to_kannada_words, _amount_to_kannada_words, _amount_words_receipt_line"),

    (1553, "SEVA RECEIPT PDF (ReportLab) + SEVA BOOKING VIEW",
     "",
     "_receipt_number_for_seva, _mandir_seva_booking_view, _generate_seva_receipt_pdf_bytes"),

    (1487, "DONATION RECEIPT PDF (ReportLab)",
     "",
     "_generate_donation_receipt_pdf_bytes"),

    (1431, "DONATION VIEW + ROW FILTERING",
     "",
     "_mandir_donation_view, _mandir_row_date_text, _mandir_row_matches_search, _mandir_filter_rows"),

    (1342, "SEQUENCE NUMBERS",
     "",
     "_format_mandir_receipt_number, _format_mandir_sequence_number, _next_receipt_number, _next_journal_entry_number, _receipt_number_for_donation, _sanitize_mongo_doc"),

    (1173, "LEGACY COA IMPORT",
     "",
     "_load_mandir_legacy_accounts, _coerce_account_id, _infer_cash_bank_nature, _infer_flag, _prepare_mandir_account_docs, _upsert_mandir_account_docs"),

    (1063, "OPENING BALANCE HELPERS",
     "",
     "_parse_opening_balance_rows, _find_or_create_opening_balance_offset_account, _current_opening_balance_net"),

    (998,  "SAFE TYPE COERCIONS",
     "",
     "_safe_float, _safe_optional_float, _safe_optional_int, _safe_bool, _safe_optional_str, _parse_opening_balance_decimal"),

    (765,  "ACCOUNT SEEDING",
     "",
     "_mandir_seed_accounts, _mandir_account_view, _dedupe_mandir_account_docs, _ensure_default_mandir_accounts, _sync_mandir_sql_accounts_from_seed, _ensure_default_mandir_sql_accounts"),

    (556,  "RECEIPT CANCELLATION HELPERS",
     "",
     "_mandir_actor_id, _mandir_receipt_cancellation_metadata, _reverse_mandir_source_journal, _cancel_mandir_receipt_source"),

    (305,  "ASYNC ACCOUNT RESOLVERS",
     "",
     "_normalize_mandir_income_accounts, _resolve_mandir_income_account, _resolve_or_create_mandir_account, _mandir_inventory_accounting_enabled, _resolve_mandir_in_kind_debit_account, _resolve_mandir_payment_account_id"),

    (209,  "ACCOUNT CODE + CATEGORY HELPERS",
     "",
     "_normalize_mandir_account_code, _normalize_income_category, _normalize_public_payment_utr_reference, _is_mandir_sponsorship_category, _mandir_cash_income_category, _mandir_in_kind_income_category, _mandir_in_kind_debit_account_target, _mandir_income_bucket_for_account"),

    (1,    "MODULE HEADER + IMPORTS",
     "",
     "9K-line MandirMitra FastAPI router. Use Ctrl+F '# SECTION:' to navigate.\n# Split trigger: when a second developer joins or file exceeds 12K lines."),
]

# Insert bottom-up so earlier line numbers stay valid
for (line1, title, routes, note) in sorted(SECTIONS, key=lambda x: -x[0]):
    idx = line1 - 1
    insert_text = marker(title, routes, note)
    lines.insert(idx, insert_text)

FILE.write_text("".join(lines), encoding="utf-8")
print(f"Done — inserted {len(SECTIONS)} section markers into {FILE}")
