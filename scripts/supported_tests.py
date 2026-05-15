"""Supported bootstrap test suite for the unified backend foundation."""

from __future__ import annotations

SUPPORTED_TESTS = [
    "tests/test_health.py",
    "tests/test_module_registry.py",
    "tests/test_modules_me_endpoint.py",
    "tests/test_tenants_lifecycle.py",
    "tests/test_module_access_dependency.py",
    "tests/test_users_me_context.py",
    "tests/test_accounting_validation.py",
    "tests/test_accounting_context_isolation.py",
    "tests/test_accounting_app_key_isolation.py",
    "tests/test_mandir_reports.py",
    "tests/test_mandir_posting_guardrails.py",
]

DEFAULT_PYTEST_KEYWORD = "not receipt_pdf"
