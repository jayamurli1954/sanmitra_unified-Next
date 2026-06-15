from scripts.seed_mitrabooks_local_demo import CA_DEMO_FIRMS
from scripts.seed_mitrabooks_local_demo import _ca_demo_passwords


def test_ca_demo_firms_are_dummy_and_have_unique_login_contexts() -> None:
    tenant_ids = [firm["tenant_id"] for firm in CA_DEMO_FIRMS]
    emails = [firm["email"] for firm in CA_DEMO_FIRMS]

    assert len(CA_DEMO_FIRMS) == 3
    assert len(set(tenant_ids)) == len(tenant_ids)
    assert len(set(emails)) == len(emails)
    assert all(tenant_id.startswith("demo-ca-practice-") for tenant_id in tenant_ids)
    assert all(email.endswith("@sanmitra.local") for email in emails)


def test_ca_demo_firms_include_document_queue_metadata() -> None:
    required_fields = {
        "document_id",
        "client_name",
        "document_type",
        "period",
        "status",
        "assigned_to",
        "priority",
        "compliance_area",
        "next_action",
    }

    for firm in CA_DEMO_FIRMS:
        assert firm["display_name"]
        assert len(firm["documents"]) >= 2
        for document in firm["documents"]:
            assert required_fields <= set(document)
            assert document["document_id"]
            assert document["client_name"]


def test_ca_demo_generated_passwords_are_distinct_per_firm() -> None:
    passwords = _ca_demo_passwords(shared_password=None, generate_passwords=True)

    assert set(passwords) == {firm["tenant_id"] for firm in CA_DEMO_FIRMS}
    assert len(set(passwords.values())) == len(CA_DEMO_FIRMS)
    for password in passwords.values():
        assert len(password) >= 18
        assert password.startswith("DemoCA-")
        assert password.endswith("9!")


def test_ca_demo_shared_password_mode_uses_supplied_password() -> None:
    passwords = _ca_demo_passwords(shared_password="SharedDemo123!", generate_passwords=False)

    assert set(passwords) == {firm["tenant_id"] for firm in CA_DEMO_FIRMS}
    assert set(passwords.values()) == {"SharedDemo123!"}
