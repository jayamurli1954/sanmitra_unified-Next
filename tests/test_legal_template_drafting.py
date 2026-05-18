from app.modules.legal_compat.template_catalog import get_template_library
from app.modules.legal_compat.template_drafting import render_template_document


def _template(template_id: str) -> dict:
    for item in get_template_library():
        if item["template_id"] == template_id:
            return item
    raise AssertionError(f"Template not found: {template_id}")


def test_consultancy_agreement_renders_professional_clause_structure():
    draft = render_template_document(
        template=_template("consultant_agreement"),
        fields={
            "client_name": "ABC Pvt Ltd",
            "client_address": "Bengaluru, Karnataka",
            "consultant_name": "Raghavendra Hussur",
            "consultant_address": "Mysuru, Karnataka",
            "services_description": "Software architecture consulting, API integration guidance, and deployment assistance.",
            "contract_duration": "24",
            "fees": "75000",
            "deliverables": "Weekly architecture review; API documentation; Technical audit report",
            "payment_terms": "Invoices shall be payable within 15 days from receipt.",
            "jurisdiction": "Bengaluru",
            "effective_date": "2026-05-17",
        },
    )

    text = draft["rendered_document"]

    assert draft["draft_status"] == "ready"
    assert draft["firmness_score"] >= 90
    assert "[AI will expand" not in text
    assert "CONSULTANCY SERVICES AGREEMENT" in text
    assert "2. Definitions" in text
    assert "3. Appointment and Scope of Services" in text
    assert "4. Deliverables and Timelines" in text
    assert "5. Fees, Taxes, and Payment Terms" in text
    assert "7. Confidentiality" in text
    assert "8. Intellectual Property Rights" in text
    assert "10. Independent Contractor" in text
    assert "12. Limitation of Liability" in text
    assert "14. Term and Termination" in text
    assert "16. Governing Law and Dispute Resolution" in text
    assert "Witness 1" in text


def test_consultancy_agreement_asks_for_execution_ready_details():
    draft = render_template_document(
        template=_template("consultant_agreement"),
        fields={
            "client_name": "ABC Pvt Ltd",
            "consultant_name": "Raghavendra Hussur",
            "services_description": "Technology consulting.",
            "contract_duration": "12",
            "fees": "50000",
        },
    )

    questions = " ".join(draft["follow_up_questions"])
    recommended = " ".join(draft["recommended_clauses"])

    assert draft["draft_status"] == "needs_more_information"
    assert "Client's full registered/principal office address" in questions
    assert "Consultant's full address" in questions
    assert "deliverables" in questions.lower()
    assert "Exclusive jurisdiction" in recommended


def test_software_development_agreement_renders_launch_grade_structure():
    draft = render_template_document(
        template=_template("software_development_agreement"),
        fields={
            "client_name": "ABC Pvt Ltd",
            "client_address": "Bengaluru, Karnataka",
            "developer_name": "XYZ Technologies",
            "developer_address": "Hyderabad, Telangana",
            "project_name": "Customer Portal",
            "project_scope": "Design and develop a SaaS web application with admin dashboard and REST APIs.",
            "technical_specifications": "React frontend, FastAPI backend, PostgreSQL database, and payment gateway integration.",
            "milestones": "Requirements confirmation; MVP build; UAT fixes; Deployment handover",
            "fees": "250000",
            "payment_terms": "40% advance, 40% on UAT, and 20% on final deployment.",
            "acceptance_period_days": "10",
            "maintenance_period": "30 days after final acceptance",
            "sla": "Critical production issue response within 1 business day.",
            "open_source_policy": "Open-source components are permitted if licence-compliant and disclosed before delivery.",
            "jurisdiction": "Bengaluru",
            "effective_date": "2026-05-17",
        },
    )

    text = draft["rendered_document"]

    assert draft["draft_status"] == "ready"
    assert draft["firmness_score"] >= 90
    assert "SOFTWARE DEVELOPMENT AGREEMENT" in text
    assert "3. Project Scope and Technical Specifications" in text
    assert "5. Acceptance Testing" in text
    assert "6. Change Requests and Scope Control" in text
    assert "8. Intellectual Property and Source Code Ownership" in text
    assert "9. Open-Source and Third-Party Components" in text
    assert "10. Maintenance, Support, and SLA" in text
    assert "12. Data Protection and Security" in text
    assert "18. Governing Law and Dispute Resolution" in text
    assert "[AI expands" not in text


def test_software_development_agreement_flags_missing_technical_details():
    draft = render_template_document(
        template=_template("software_development_agreement"),
        fields={
            "client_name": "ABC Pvt Ltd",
            "developer_name": "XYZ Technologies",
            "project_name": "Customer Portal",
            "project_scope": "Build a customer portal.",
            "fees": "250000",
        },
    )

    questions = " ".join(draft["follow_up_questions"])
    recommended = " ".join(draft["recommended_clauses"])

    assert draft["draft_status"] == "needs_more_information"
    assert "technical specifications" in questions.lower()
    assert "milestones" in questions.lower()
    assert "open-source" in questions.lower()
    assert "Source-code ownership" in recommended
