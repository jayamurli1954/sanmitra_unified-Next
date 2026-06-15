from scripts.seed_mitrabooks_local_demo import CA_DEMO_FIRMS


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
