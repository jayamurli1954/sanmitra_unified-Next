from pathlib import Path

from scripts.mitrabooks_phase3_business_gate import DEMO_TENANT_ID
from scripts.mitrabooks_phase3_business_gate import DEFAULT_DEPLOYED_API_BASE_URL
from scripts.mitrabooks_phase3_business_gate import destructive_demo_api_base
from scripts.mitrabooks_phase3_business_gate import is_local_frontend_url
from scripts.mitrabooks_phase3_business_gate import main
from scripts.mitrabooks_phase3_business_gate import validate_destructive_demo_auth_context
from scripts.mitrabooks_phase3_business_gate import validate_destructive_demo_policy


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_destructive_demo_policy_accepts_only_confirmed_demo_tenant() -> None:
    ok, errors = validate_destructive_demo_policy(
        DEMO_TENANT_ID,
        {
            "MITRABOOKS_DEMO_E2E_CONFIRM": DEMO_TENANT_ID,
            "E2E_USER_EMAIL": "businessadmin@sanmitra.local",
            "E2E_USER_PASSWORD": "DemoOnly123!",
        },
    )

    assert ok is True
    assert errors == []


def test_destructive_demo_policy_rejects_real_or_unknown_tenant() -> None:
    ok, errors = validate_destructive_demo_policy(
        "real-business-tenant",
        {
            "MITRABOOKS_DEMO_E2E_CONFIRM": DEMO_TENANT_ID,
            "E2E_USER_EMAIL": "businessadmin@sanmitra.local",
            "E2E_USER_PASSWORD": "DemoOnly123!",
        },
    )

    assert ok is False
    assert any("--demo-tenant-id" in error for error in errors)


def test_destructive_demo_policy_requires_confirmation_and_credentials() -> None:
    ok, errors = validate_destructive_demo_policy(DEMO_TENANT_ID, {})

    assert ok is False
    assert any("MITRABOOKS_DEMO_E2E_CONFIRM" in error for error in errors)
    assert any("E2E_USER_EMAIL" in error for error in errors)
    assert any("E2E_USER_PASSWORD" in error for error in errors)


def test_run_destructive_demo_requires_staging_url(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["mitrabooks_phase3_business_gate.py", "--run-destructive-demo", "--skip-browser"])

    assert main() == 2


def test_destructive_demo_api_base_prefers_explicit_override() -> None:
    assert destructive_demo_api_base(
        "https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/",
        {"E2E_API_BASE_URL": "https://api.example.test/"},
    ) == "https://api.example.test"


def test_destructive_demo_api_base_matches_deployed_shell_default() -> None:
    assert destructive_demo_api_base(
        "https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/",
        {},
    ) == DEFAULT_DEPLOYED_API_BASE_URL


def test_destructive_demo_api_base_maps_local_shell_to_local_backend() -> None:
    assert destructive_demo_api_base(
        "http://127.0.0.1:3300/mitrabooks-erp/",
        {},
    ) == "http://127.0.0.1:8000"


def test_local_frontend_url_detection_is_limited_to_local_shell_port() -> None:
    assert is_local_frontend_url("http://127.0.0.1:3300/mitrabooks-erp/") is True
    assert is_local_frontend_url("http://localhost:3300/mitrabooks-erp/") is True
    assert is_local_frontend_url("http://127.0.0.1:8000/mitrabooks-erp/") is False
    assert is_local_frontend_url("https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/") is False


def test_destructive_demo_auth_precheck_explains_local_backend_requirement(monkeypatch) -> None:
    def fake_read_json_response(request, timeout=20):
        raise OSError("connection refused")

    monkeypatch.setattr("scripts.mitrabooks_phase3_business_gate._read_json_response", fake_read_json_response)

    ok, errors = validate_destructive_demo_auth_context(
        "http://127.0.0.1:3300/mitrabooks-erp/",
        DEMO_TENANT_ID,
        {
            "E2E_USER_EMAIL": "business.admin@sanmitra.local",
            "E2E_USER_PASSWORD": "demo-password",
        },
    )

    assert ok is False
    assert any("python -m uvicorn app.main:app" in error for error in errors)


def test_destructive_demo_auth_precheck_reports_invalid_credentials(monkeypatch) -> None:
    def fake_read_json_response(request, timeout=20):
        assert request.full_url == f"{DEFAULT_DEPLOYED_API_BASE_URL}/api/v1/auth/login"
        return 401, {"detail": "Invalid credentials"}

    monkeypatch.setattr("scripts.mitrabooks_phase3_business_gate._read_json_response", fake_read_json_response)

    ok, errors = validate_destructive_demo_auth_context(
        "https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/",
        DEMO_TENANT_ID,
        {
            "E2E_USER_EMAIL": "business.admin@sanmitra.local",
            "E2E_USER_PASSWORD": "wrong-password",
        },
    )

    assert ok is False
    assert any("Invalid credentials" in error for error in errors)
    assert any("Reset/reseed" in error for error in errors)


def test_destructive_demo_auth_precheck_confirms_tenant_context(monkeypatch) -> None:
    calls = []

    def fake_read_json_response(request, timeout=20):
        calls.append(request.full_url)
        if request.full_url.endswith("/api/v1/auth/login"):
            return 200, {"access_token": "token"}
        return 200, {
            "tenant_id": DEMO_TENANT_ID,
            "organization_type": "BUSINESS",
            "enabled_modules": [
                {"module_key": "business"},
                {"module_key": "accounting"},
                {"module_key": "audit"},
            ],
        }

    monkeypatch.setattr("scripts.mitrabooks_phase3_business_gate._read_json_response", fake_read_json_response)

    ok, errors = validate_destructive_demo_auth_context(
        "https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/",
        DEMO_TENANT_ID,
        {
            "E2E_USER_EMAIL": "business.admin@sanmitra.local",
            "E2E_USER_PASSWORD": "correct-password",
        },
    )

    assert ok is True
    assert errors == []
    assert calls == [
        f"{DEFAULT_DEPLOYED_API_BASE_URL}/api/v1/auth/login",
        f"{DEFAULT_DEPLOYED_API_BASE_URL}/api/v1/modules/me",
    ]


def test_destructive_demo_spec_covers_document_upload_gate() -> None:
    spec = (REPO_ROOT / "frontend" / "e2e" / "mitrabooks-realstack-destructive.spec.js").read_text(encoding="utf-8")

    assert "business/ca-clients" in spec
    assert "business/ca-documents" in spec
    assert "uploadAttachment(" in spec
    assert "business_document_attachment_uploaded" in spec
    assert "business_document_attachment_downloaded" in spec
    assert "business_ca_document_metadata_updated" in spec
    assert "other-demo-book" in spec
    assert "auto_post_to_ledger).toBe(false)" in spec
    assert "ocr_enabled).toBe(false)" in spec


def test_destructive_demo_spec_covers_fixed_asset_gate() -> None:
    spec = (REPO_ROOT / "frontend" / "e2e" / "mitrabooks-realstack-destructive.spec.js").read_text(encoding="utf-8")

    assert "fixedAssetEntity" in spec
    assert "business/fixed-assets" in spec
    assert "business/depreciation/preview" in spec
    assert "business/depreciation/run" in spec
    assert "phase3-demo-depreciation" in spec
    assert "phase3-demo-fixed-asset-disposal" in spec
    assert "fixed_asset_disposal" in spec
    assert "total_debit)).toBe(decimalValue" in spec
    assert "accounting_entity_id=primary" in spec


def test_destructive_demo_spec_covers_dimensions_gate() -> None:
    spec = (REPO_ROOT / "frontend" / "e2e" / "mitrabooks-realstack-destructive.spec.js").read_text(encoding="utf-8")

    assert "dimensionsEntity" in spec
    assert "business/dimensions?accounting_entity_id" in spec
    assert "dimension_type: 'cost_centre'" in spec
    assert "dimension_type: 'project'" in spec
    assert "phase3-demo-dimension-invoice" in spec
    assert "phase3-demo-dimension-bill" in spec
    assert "phase3-demo-dimension-credit-note" in spec
    assert "phase3-demo-dimension-debit-note" in spec
    assert "business/dimensions/report?dimension_type=cost_centre" in spec
    assert "business/dimensions/report?dimension_type=project" in spec
    assert "business/dimensions/report/export?dimension_type=cost_centre&format=json" in spec
    assert "accounting_entity_id=primary" in spec


def test_destructive_demo_spec_covers_branch_reporting_gate() -> None:
    spec = (REPO_ROOT / "frontend" / "e2e" / "mitrabooks-realstack-destructive.spec.js").read_text(encoding="utf-8")

    assert "branchEntity" in spec
    assert "business/admin-settings?accounting_entity_id" in spec
    assert "cost_centre_code: branchCostCentre.code" in spec
    assert "phase3-demo-branch-invoice" in spec
    assert "phase3-demo-branch-bill" in spec
    assert "phase3-demo-branch-unmapped-invoice" in spec
    assert "phase3-demo-branch-untagged-bill" in spec
    assert "business/dimensions/branch-report" in spec
    assert "branch_consolidated" in spec
    assert "unmatched_cost_centres" in spec
    assert "accounting_entity_id=primary" in spec
    assert "phase3-demo-branch-invoice-cancel" in spec
    assert "phase3-demo-branch-bill-cancel" in spec
    assert "phase3-demo-branch-unmapped-invoice-cancel" in spec
    assert "phase3-demo-branch-untagged-bill-cancel" in spec


def test_destructive_demo_spec_covers_mis_data_health_gate() -> None:
    spec = (REPO_ROOT / "frontend" / "e2e" / "mitrabooks-realstack-destructive.spec.js").read_text(encoding="utf-8")

    assert "misHealthEntity" in spec
    assert "phase3-demo-mis-health-invoice" in spec
    assert "phase3-demo-mis-health-bill" in spec
    assert "phase3-demo-data-health-draft" in spec
    assert "business/mis/kpis" in spec
    assert "business/financial-health?narrate=false" in spec
    assert "business/data-health" in spec
    assert "missing_gstin" in spec
    assert "unposted_drafts" in spec
    assert "stale_reconciliation" in spec
    assert "overdue_exposure" in spec
    assert "receivables_open_item_aging" in spec
    assert "phase3-demo-mis-health-invoice-cancel" in spec
    assert "phase3-demo-mis-health-bill-cancel" in spec


def test_destructive_demo_spec_covers_export_governance_gate() -> None:
    spec = (REPO_ROOT / "frontend" / "e2e" / "mitrabooks-realstack-destructive.spec.js").read_text(encoding="utf-8")

    assert "fileRequest" in spec
    assert "expectGovernedExport" in spec
    assert "x-sanmitra-export-governed" in spec
    assert "business/dimensions/report/export?dimension_type=cost_centre&format=json" in spec
    assert "business/opening-balances/export?accounting_entity_id=primary" in spec
    assert "business/reports/export?report=trial_balance&format=json" in spec
    assert "business/invoices/${invoice.invoice_id}/pdf" in spec
    assert "business/tally/xml-export" in spec
    assert "business_export_downloaded" in spec
    assert "dimension_report" in spec
    assert "opening_balances" in spec
    assert "business_report" in spec
    assert "sales_invoice_pdf" in spec
    assert "tally_xml" in spec


def test_mandirmitra_donation_realstack_spec_is_guarded_and_reversible() -> None:
    spec = (REPO_ROOT / "frontend" / "e2e" / "mandirmitra-donation-realstack-destructive.spec.js").read_text(encoding="utf-8")

    assert "MANDIRMITRA_RUN_DESTRUCTIVE_E2E" in spec
    assert "MANDIRMITRA_DEMO_E2E_CONFIRM" in spec
    assert "MANDIRMITRA_DEMO_TENANT_ID" in spec
    assert "DESTROY_DEMO_ONLY:" in spec
    assert "expectedDemoTenantId" in spec
    assert "'/auth/me'" in spec
    assert "temple.platform_can_write" in spec
    assert "Maker and approver must resolve to distinct authenticated actors" in spec
    assert "trace: 'off'" in spec
    assert "video: 'off'" in spec
    assert "process.env.E2E_USER_PASSWORD" not in spec
    assert "JSON.stringify(payload)" not in spec
    assert "'X-App-Key': 'mandirmitra'" in spec
    assert "'/donations'" in spec
    assert "/receipt/pdf" in spec
    assert "/reports/donations/detailed" in spec
    assert "/journal-entries/reports/receipts-payments" in spec
    assert "/cancel" in spec
    assert "reversal_journal_id" in spec
    assert "_idempotent" in spec


def test_mandirmitra_seva_realstack_spec_is_guarded_and_reversible() -> None:
    spec = (REPO_ROOT / "frontend" / "e2e" / "mandirmitra-donation-realstack-destructive.spec.js").read_text(encoding="utf-8")

    assert "'/sevas/bookings'" in spec
    assert "payment_status: 'paid'" in spec
    assert "String(booking.status).toLowerCase()" in spec
    assert "String(booking.payment_status).toLowerCase()" in spec
    assert "/sevas/bookings/${booking.id}/receipt/pdf" in spec
    assert "/reports/sevas/detailed" in spec
    assert "/reports/sevas/schedule?days=1" in spec
    assert "/sevas/bookings/${booking.id}/cancel" in spec
    assert "Guarded seva reversal" in spec
    assert "reversal_journal_id" in spec
    assert "_idempotent" in spec


def test_mandirmitra_refund_realstack_spec_requires_approval_settlement_reporting_and_reversal() -> None:
    spec = (REPO_ROOT / "frontend" / "e2e" / "mandirmitra-donation-realstack-destructive.spec.js").read_text(encoding="utf-8")

    assert "'POST', '/refund-requests'" in spec
    assert "/refund-requests/${refund.id}/approve" in spec
    assert "makerApproval.status()).toBe(409)" in spec
    assert "approved_pending_settlement" in spec
    assert "'/refund-requests?status=approved_pending_settlement'" in spec
    assert "/reports/refunds?from_date=${today}&to_date=${today}" in spec
    assert "/reports/refunds/export.csv?from_date=${today}&to_date=${today}" in spec
    assert "/refund-requests/${refund.id}/settle" in spec
    assert "settled.reversal_journal_id" in spec
    assert "repeated._idempotent" in spec


def test_mandirmitra_hundi_realstack_spec_requires_maker_checker_and_reversal() -> None:
    spec = (REPO_ROOT / "frontend" / "e2e" / "mandirmitra-donation-realstack-destructive.spec.js").read_text(encoding="utf-8")

    assert "MANDIRMITRA_E2E_MAKER_EMAIL" in spec
    assert "MANDIRMITRA_E2E_MAKER_PASSWORD" in spec
    assert "'/hundi/masters'" in spec
    assert "'/hundi/openings'" in spec
    assert "/hundi/openings/${opening.id}/approve" in spec
    assert "pending_approval" in spec
    assert "posted.approved_by" in spec
    assert "opening.created_by" in spec
    assert "/hundi/openings/${opening.id}/cancel" in spec
    assert "reversal_journal_id" in spec
    assert "_idempotent" in spec


def test_mandirmitra_designated_fund_and_festival_realstack_spec_is_guarded() -> None:
    spec = (REPO_ROOT / "frontend" / "e2e" / "mandirmitra-donation-realstack-destructive.spec.js").read_text(encoding="utf-8")

    assert "'/funds'" in spec
    assert "fund_type: 'restricted'" in spec
    assert "'/festivals'" in spec
    assert "is_sponsorship: true" in spec
    assert "/reports/donations/fund-wise" in spec
    assert "/reports/donations/festival-wise" in spec
    assert "Sponsorship Income" in spec
    assert "Guarded designated donation reversal" in spec


def test_mandirmitra_fund_transfer_realstack_spec_requires_subledger_maker_checker_and_reversal() -> None:
    spec = (REPO_ROOT / "frontend" / "e2e" / "mandirmitra-donation-realstack-destructive.spec.js").read_text(encoding="utf-8")

    assert "accounting_dimension_id" in spec
    assert "'/fund-transfers'" in spec
    assert "/fund-transfers/${transfer.id}/approve" in spec
    assert "posted.approved_by" in spec
    assert "transfer.created_by" in spec
    assert "/reports/funds/subledger" in spec
    assert "subledger.totals.transfers_in" in spec
    assert "subledger.totals.transfers_out" in spec
    assert "/fund-transfers/${transfer.id}/cancel" in spec
    assert "Guarded fund transfer correction" in spec
    assert "reversal_journal_id" in spec
    assert "_idempotent" in spec
    assert "'/fund-opening-balances'" in spec
    assert "/fund-opening-balances/${opening.id}/approve" in spec
    assert "postedOpening.approved_by" in spec
    assert "sourceRow.opening_entries" in spec
    assert "sourceRow.closing_balance" in spec
    assert "/reports/funds/as-of?as_of=${today}" in spec
    assert "/fund-opening-balances/${opening.id}/cancel" in spec
    assert "Guarded opening balance correction" in spec


def test_mandirmitra_in_kind_inventory_realstack_spec_requires_valuation_and_stock_reversal() -> None:
    spec = (REPO_ROOT / "frontend" / "e2e" / "mandirmitra-donation-realstack-destructive.spec.js").read_text(encoding="utf-8")

    assert "module_inventory_enabled: true" in spec
    assert "donation_type: 'in_kind'" in spec
    assert "/valuation/approve" in spec
    assert "makerApproval.status()).toBe(409)" in spec
    assert "valuation_status).toBe('approved')" in spec
    assert "'/inventory/consumptions'" in spec
    assert "consumption.unit_value).toBe('52.55')" in spec
    assert "/inventory/consumptions/${consumption.id}/approve" in spec
    assert "blockedDonationReversal.status()).toBe(409)" in spec
    assert "/inventory/consumptions/${consumption.id}/cancel" in spec
    assert "inventory_reversal_movement_id" in spec
    assert "'/temples/modules/config', originalConfig" in spec


def test_mandirmitra_compliance_realstack_spec_is_guarded_and_restores_tenant_config() -> None:
    spec = (REPO_ROOT / "frontend" / "e2e" / "mandirmitra-donation-realstack-destructive.spec.js").read_text(encoding="utf-8")

    assert "'/compliance/donations/config'" in spec
    assert "request_80g: true" in spec
    assert "donor_pan_masked" in spec
    assert "is_foreign_contribution: true" in spec
    assert "foreign_source_declaration: true" in spec
    assert "blocked.status()).toBe(409)" in spec
    assert "/reports/compliance/80g" in spec
    assert "/reports/compliance/fcra" in spec
    assert "filing_artifact).toBe(false)" in spec
    assert "'/compliance/donations/config', originalConfig" in spec


def test_mandirmitra_compliance_shell_exposes_governed_operator_controls() -> None:
    shell = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")

    assert '"/api/v1/compliance/donations/config"' in shell
    assert '/api/v1/reports/compliance/80g?' in shell
    assert '/api/v1/reports/compliance/fcra?' in shell
    assert 'data-mandir-compliance-form' in shell
    assert 'Save Compliance Configuration' in shell
    assert 'name="request_80g"' in shell
    assert 'name="donor_pan"' in shell
    assert 'name="is_foreign_contribution"' in shell
    assert 'name="foreign_source_declaration"' in shell
    assert '80G is off for this tenant.' in shell
    assert 'FCRA is off for this tenant.' in shell
    assert 'donor_pan_masked' in shell
    assert 'this is not an official certificate or filing' in shell
    assert 'this is not an official filing' in shell


def test_mandirmitra_stage3_browser_smoke_has_no_embedded_password_and_checks_compliance() -> None:
    smoke = (REPO_ROOT / "scripts" / "mandirmitra_stage3_browser_smoke.py").read_text(encoding="utf-8")

    assert "MANDIRMITRA_SMOKE_PASSWORD" in smoke
    assert 'default="admin123"' not in smoke
    assert 'login.text()' not in smoke
    assert '"/api/v1/compliance/donations/config"' in smoke
    assert '"/api/v1/reports/compliance/80g"' in smoke
    assert '"/api/v1/reports/compliance/fcra"' in smoke
    assert "filing_artifact=false" in smoke
    assert "donor_pan_masked" in smoke
    assert "dispatch_event(\"click\")" in smoke
    assert "mandir-stage3-browser-smoke.json" in smoke
    assert "Fund Subledger" in smoke
    assert "Inventory Stock Valuation" in smoke
    assert "Inventory Audit Trail" in smoke
    assert '"tenant_id": modules_payload.get("tenant_id")' in smoke
    assert '"app_key": "mandirmitra"' in smoke


def test_mandirmitra_production_signoff_is_fail_closed() -> None:
    verifier = (REPO_ROOT / "scripts" / "verify_mandirmitra_stage3_signoff.py").read_text(encoding="utf-8")

    assert "production signoff requires a clean worktree" in verifier
    assert "backend-vMAJOR.MINOR.PATCH" in verifier
    assert '"merge-base", "--is-ancestor"' in verifier
    assert '"financial_rollback_policy"' in verifier
    assert '"reversal_or_adjustment_only"' in verifier
    assert '"scripts/preflight.py", "--all"' in verifier
    assert '"scripts/release_preflight.py"' in verifier
    assert "path must remain inside the workspace" in verifier
    assert "last_successful_backup_at" in verifier
    assert "last_restore_test_at" in verifier


def test_mandirmitra_stage3_automated_smoke_discovers_all_mandir_tests() -> None:
    smoke = (REPO_ROOT / "scripts" / "mandirmitra_stage3_smoke.py").read_text(encoding="utf-8")

    assert '.glob("test_mandir*.py")' in smoke
    assert "SHARED_FOCUSED_TESTS" in smoke


def test_mandirmitra_shell_exposes_accounting_backed_fund_and_inventory_drilldown() -> None:
    shell = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")

    assert "/api/v1/reports/donations/fund-wise?" in shell
    assert "/api/v1/reports/donations/festival-wise?" in shell
    assert "/api/v1/reports/funds/subledger?" in shell
    assert "/api/v1/reports/funds/as-of?" in shell
    assert '"/api/v1/inventory/summary"' in shell
    assert '"/api/v1/inventory/stock-balances"' in shell
    assert '"/api/v1/inventory/movements"' in shell
    assert '"/api/v1/inventory/consumptions"' in shell
    assert "Fund and Inventory Drill-down" in shell
    assert "Fund Subledger" in shell
    assert "Inventory Stock Valuation" in shell
    assert "Inventory Audit Trail" in shell
    assert "Promise.all([" in shell


def test_mandirmitra_destructive_launcher_prompts_secrets_and_writes_sanitized_evidence() -> None:
    launcher = (REPO_ROOT / "scripts" / "run_mandirmitra_stage3_destructive.py").read_text(encoding="utf-8")

    assert "getpass.getpass" in launcher
    assert 'add_argument("--password"' not in launcher
    assert "DESTROY_DEMO_ONLY:" in launcher
    assert "tenant ID must be explicit and visibly marked demo/test/seed" in launcher
    assert "evidence path must remain inside the workspace" in launcher
    assert '"trace_and_video_disabled": True' in launcher
    assert '"distinct_actor_check": True' in launcher
    assert '"approver_email"' not in launcher
    assert '"maker_email"' not in launcher
    assert "shell=True" not in launcher
