from scripts.mitrabooks_phase3_business_gate import DEMO_TENANT_ID
from scripts.mitrabooks_phase3_business_gate import DEFAULT_DEPLOYED_API_BASE_URL
from scripts.mitrabooks_phase3_business_gate import destructive_demo_api_base
from scripts.mitrabooks_phase3_business_gate import is_local_frontend_url
from scripts.mitrabooks_phase3_business_gate import main
from scripts.mitrabooks_phase3_business_gate import validate_destructive_demo_auth_context
from scripts.mitrabooks_phase3_business_gate import validate_destructive_demo_policy


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
