from scripts.mitrabooks_phase3_business_gate import DEMO_TENANT_ID
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
