from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA_FILE = Path(__file__).resolve().parent / "data" / "legacy_legal_templates.json"

# Launch-grade fallback catalog. The old 100+ legacy catalog is intentionally
# not the default because most legacy items are thin placeholders.
_FALLBACK_TEMPLATE_LIBRARY: list[dict[str, Any]] = [
    {
        "template_id": "consultant_agreement",
        "name": "Consultancy Agreement",
        "description": "Lawyer-grade consultancy services agreement with scope, deliverables, fees, GST, confidentiality, IP, termination, liability, and dispute clauses.",
        "category": "contracts",
        "is_premium": False,
        "tags": ["consultancy", "contract", "professional services"],
        "act": ["Indian Contract Act, 1872", "Arbitration and Conciliation Act, 1996"],
        "court": [],
        "fields": [
            {"id": "client_name", "label": "Client Name", "required": True, "type": "text", "placeholder": "ABC Pvt Ltd"},
            {"id": "client_address", "label": "Client Registered/Principal Office Address", "required": True, "type": "textarea", "placeholder": "Registered office address"},
            {"id": "consultant_name", "label": "Consultant Name", "required": True, "type": "text", "placeholder": "Consultant / Firm Name"},
            {"id": "consultant_address", "label": "Consultant Address", "required": True, "type": "textarea", "placeholder": "Consultant address"},
            {"id": "project_name", "label": "Project / Engagement Name", "required": True, "type": "text", "placeholder": "Technology advisory engagement"},
            {"id": "services_description", "label": "Scope of Services", "required": True, "type": "textarea", "placeholder": "Detailed consulting scope"},
            {"id": "deliverables", "label": "Deliverables / Milestones", "required": True, "type": "textarea", "placeholder": "One deliverable per line"},
            {"id": "contract_duration", "label": "Contract Duration (months)", "required": True, "type": "number", "placeholder": "12"},
            {"id": "fees", "label": "Professional Fees (Rs.)", "required": True, "type": "number", "placeholder": "75000"},
            {"id": "payment_terms", "label": "Payment Terms", "required": True, "type": "textarea", "placeholder": "Monthly invoice payable within 15 days"},
            {"id": "gst_applicable", "label": "GST / Taxes", "required": False, "type": "text", "placeholder": "GST extra as applicable"},
            {"id": "termination_notice_days", "label": "Termination Notice (days)", "required": False, "type": "number", "placeholder": "30"},
            {"id": "jurisdiction", "label": "Jurisdiction City", "required": True, "type": "text", "placeholder": "Bengaluru"},
            {"id": "effective_date", "label": "Effective Date", "required": False, "type": "date", "placeholder": ""},
        ],
        "body": ["This template is rendered by the structured LegalMitra consultancy agreement engine."],
    },
    {
        "template_id": "software_development_agreement",
        "name": "Software Development Agreement",
        "description": "Structured software development agreement with milestones, acceptance testing, source code/IP ownership, open-source policy, SLA, support, data protection, and change requests.",
        "category": "contracts",
        "is_premium": True,
        "tags": ["software", "startup", "SaaS", "IP"],
        "act": ["Indian Contract Act, 1872", "Information Technology Act, 2000"],
        "court": [],
        "fields": [
            {"id": "client_name", "label": "Client Name", "required": True, "type": "text", "placeholder": "Client company"},
            {"id": "client_address", "label": "Client Registered Office Address", "required": True, "type": "textarea", "placeholder": "Client registered office"},
            {"id": "developer_name", "label": "Developer / Vendor Name", "required": True, "type": "text", "placeholder": "Developer company"},
            {"id": "developer_address", "label": "Developer Registered Office Address", "required": True, "type": "textarea", "placeholder": "Developer address"},
            {"id": "project_name", "label": "Project Name", "required": True, "type": "text", "placeholder": "SaaS platform development"},
            {"id": "technical_specifications", "label": "Technical Specifications", "required": True, "type": "textarea", "placeholder": "Stack, integrations, environments, assumptions"},
            {"id": "deliverables", "label": "Deliverables / Milestones", "required": True, "type": "textarea", "placeholder": "One milestone per line"},
            {"id": "acceptance_criteria", "label": "Acceptance Criteria", "required": True, "type": "textarea", "placeholder": "Testing and sign-off process"},
            {"id": "fees", "label": "Development Fees (Rs.)", "required": True, "type": "number", "placeholder": "250000"},
            {"id": "payment_terms", "label": "Payment Schedule", "required": True, "type": "textarea", "placeholder": "Milestone-wise payment terms"},
            {"id": "open_source_policy", "label": "Open-source Policy", "required": True, "type": "textarea", "placeholder": "Allowed licences / prohibited copyleft licences"},
            {"id": "maintenance_period", "label": "Maintenance / Warranty Period", "required": False, "type": "text", "placeholder": "90 days"},
            {"id": "jurisdiction", "label": "Jurisdiction City", "required": True, "type": "text", "placeholder": "Bengaluru"},
            {"id": "effective_date", "label": "Effective Date", "required": False, "type": "date", "placeholder": ""},
        ],
        "body": ["This template is rendered by the structured LegalMitra software development agreement engine."],
    },
    {
        "template_id": "nda_agreement",
        "name": "Non-Disclosure Agreement (NDA)",
        "description": "Mutual or one-way NDA with confidential information definition, exclusions, permitted disclosure, return/destruction, injunctive relief, and survival.",
        "category": "contracts",
        "is_premium": False,
        "tags": ["NDA", "confidentiality", "startup", "vendor"],
        "act": ["Indian Contract Act, 1872", "Specific Relief Act, 1963"],
        "court": [],
        "fields": [
            {"id": "disclosing_party", "label": "Disclosing Party", "required": True, "type": "text", "placeholder": "ABC Pvt Ltd"},
            {"id": "receiving_party", "label": "Receiving Party", "required": True, "type": "text", "placeholder": "XYZ Pvt Ltd"},
            {"id": "nda_type", "label": "NDA Type", "required": True, "type": "select", "placeholder": "Mutual", "options": ["Mutual", "One-way"]},
            {"id": "purpose", "label": "Purpose of Disclosure", "required": True, "type": "textarea", "placeholder": "Evaluation of business/technology collaboration"},
            {"id": "confidential_information", "label": "Confidential Information Covered", "required": True, "type": "textarea", "placeholder": "Business plans, financial data, source code, customer data"},
            {"id": "duration", "label": "Confidentiality Duration", "required": True, "type": "text", "placeholder": "3 years"},
            {"id": "jurisdiction", "label": "Jurisdiction City", "required": True, "type": "text", "placeholder": "Bengaluru"},
            {"id": "effective_date", "label": "Effective Date", "required": False, "type": "date", "placeholder": ""},
        ],
        "body": [
            "NON-DISCLOSURE AGREEMENT",
            "",
            "This Non-Disclosure Agreement is entered into on {{effective_date}} between {{disclosing_party}} and {{receiving_party}}.",
            "",
            "1. Purpose",
            "The Parties intend to exchange information for {{purpose}}.",
            "",
            "2. Confidential Information",
            "Confidential Information includes {{confidential_information}} and all commercial, technical, financial, legal, operational, customer, employee, product, software, process, and strategic information disclosed in any form.",
            "",
            "3. Obligations",
            "The Receiving Party shall use Confidential Information only for the stated Purpose, protect it with reasonable care, and restrict access to personnel or advisors who need to know and are bound by confidentiality obligations.",
            "",
            "4. Exclusions",
            "Confidentiality obligations do not apply to information that is public, independently developed, already lawfully known, received from a lawful third party, or required to be disclosed by law or competent authority.",
            "",
            "5. Return and Destruction",
            "Upon written request, the Receiving Party shall return or destroy Confidential Information, except archival copies required by law, compliance, or bona fide record retention.",
            "",
            "6. Term and Survival",
            "The confidentiality obligations shall survive for {{duration}} from disclosure or termination, whichever is later.",
            "",
            "7. Injunctive Relief",
            "The Parties acknowledge that breach may cause irreparable harm and the aggrieved Party may seek injunctive or equitable relief in addition to other remedies.",
            "",
            "8. Governing Law and Jurisdiction",
            "This Agreement shall be governed by Indian law and courts at {{jurisdiction}} shall have jurisdiction, subject to any mutually agreed dispute resolution clause.",
            "",
            "Signed by the Parties:",
            "{{disclosing_party}}: __________________",
            "{{receiving_party}}: __________________",
            "",
            "Drafting Note: Verify sector-specific confidentiality, data protection, export-control, and employment restrictions before execution.",
        ],
    },
    {
        "template_id": "employment_agreement",
        "name": "Employment Agreement",
        "description": "Indian employment agreement for startups/MSMEs with role, compensation, probation, leave, confidentiality, IP assignment, notice period, code of conduct, and statutory references.",
        "category": "hr",
        "is_premium": True,
        "tags": ["employment", "HR", "startup", "MSME"],
        "act": ["Indian Contract Act, 1872", "applicable Shops and Establishments law"],
        "court": [],
        "fields": [
            {"id": "employer_name", "label": "Employer Name", "required": True, "type": "text", "placeholder": "ABC Pvt Ltd"},
            {"id": "employee_name", "label": "Employee Name", "required": True, "type": "text", "placeholder": "Employee name"},
            {"id": "role", "label": "Role / Designation", "required": True, "type": "text", "placeholder": "Software Engineer"},
            {"id": "work_location", "label": "Work Location / Remote Terms", "required": True, "type": "text", "placeholder": "Bengaluru / Hybrid"},
            {"id": "compensation", "label": "Compensation", "required": True, "type": "text", "placeholder": "Rs. 12,00,000 CTC per annum"},
            {"id": "probation_period", "label": "Probation Period", "required": True, "type": "text", "placeholder": "6 months"},
            {"id": "notice_period", "label": "Notice Period", "required": True, "type": "text", "placeholder": "30 days"},
            {"id": "state", "label": "State", "required": True, "type": "text", "placeholder": "Karnataka"},
            {"id": "joining_date", "label": "Joining Date", "required": False, "type": "date", "placeholder": ""},
        ],
        "body": [
            "EMPLOYMENT AGREEMENT",
            "",
            "This Employment Agreement is entered into between {{employer_name}} and {{employee_name}}.",
            "",
            "1. Appointment and Role",
            "{{employer_name}} appoints {{employee_name}} as {{role}} with effect from {{joining_date}}. The Employee shall perform duties assigned by the Employer consistent with the role and business requirements.",
            "",
            "2. Location and Working Arrangement",
            "The primary work arrangement shall be {{work_location}}, subject to business requirements, policies, and lawful directions of the Employer.",
            "",
            "3. Compensation",
            "The Employee shall receive {{compensation}}, subject to tax deduction, statutory contributions, payroll policies, and applicable law.",
            "",
            "4. Probation",
            "The Employee shall be on probation for {{probation_period}}. Confirmation may be subject to satisfactory performance, conduct, and policy compliance.",
            "",
            "5. Leave and Benefits",
            "Leave, holidays, reimbursements, provident fund, ESI, gratuity, and other benefits shall apply as per company policy and applicable law.",
            "",
            "6. Confidentiality and Data Protection",
            "The Employee shall protect confidential information, personal data, customer data, business information, source code, credentials, and internal documents during and after employment.",
            "",
            "7. Intellectual Property",
            "All work product, inventions, documents, designs, code, processes, content, and materials created in the course of employment shall belong to the Employer, subject to applicable law.",
            "",
            "8. Conduct and Compliance",
            "The Employee shall comply with company policies, information security rules, anti-harassment policy, conflict-of-interest rules, and lawful instructions.",
            "",
            "9. Termination",
            "Either Party may terminate employment by giving {{notice_period}} notice or salary in lieu, subject to policy, misconduct provisions, and applicable law.",
            "",
            "10. Governing Law",
            "This Agreement shall be governed by Indian law and applicable employment, labour, tax, and Shops and Establishments laws in {{state}}.",
            "",
            "Employer Signature: __________________",
            "Employee Signature: __________________",
            "",
            "Drafting Note: Verify state-specific labour law, wage code implementation, PF/ESI eligibility, gratuity, and company policies before use.",
        ],
    },
    {
        "template_id": "website_terms_privacy_bundle",
        "name": "Website Terms and Privacy Policy Bundle",
        "description": "SaaS-ready Terms of Use and DPDP-oriented Privacy Policy bundle with AI disclosure, cookies, user obligations, data retention, grievance officer, and third-party services.",
        "category": "technology",
        "is_premium": True,
        "tags": ["terms", "privacy", "DPDP", "SaaS", "website"],
        "act": ["Digital Personal Data Protection Act, 2023", "Information Technology Act, 2000", "Indian Contract Act, 1872"],
        "court": [],
        "fields": [
            {"id": "business_name", "label": "Business / Platform Name", "required": True, "type": "text", "placeholder": "ABC Technologies Pvt Ltd"},
            {"id": "website_url", "label": "Website URL", "required": True, "type": "text", "placeholder": "https://example.com"},
            {"id": "services", "label": "Services Offered", "required": True, "type": "textarea", "placeholder": "Describe platform/services"},
            {"id": "data_categories", "label": "Personal Data Collected", "required": True, "type": "textarea", "placeholder": "Name, email, phone, payment metadata"},
            {"id": "third_party_services", "label": "Third-party Services", "required": False, "type": "textarea", "placeholder": "Analytics, payment gateway, cloud hosting, email"},
            {"id": "retention_period", "label": "Data Retention Period", "required": True, "type": "text", "placeholder": "As required for service, legal, tax, and audit purposes"},
            {"id": "grievance_email", "label": "Grievance / Contact Email", "required": True, "type": "text", "placeholder": "privacy@example.com"},
            {"id": "jurisdiction", "label": "Jurisdiction City", "required": True, "type": "text", "placeholder": "Bengaluru"},
            {"id": "effective_date", "label": "Effective Date", "required": False, "type": "date", "placeholder": ""},
        ],
        "body": [
            "WEBSITE TERMS OF USE AND PRIVACY POLICY BUNDLE",
            "",
            "Effective Date: {{effective_date}}",
            "Platform: {{business_name}}",
            "Website: {{website_url}}",
            "",
            "PART A - TERMS OF USE",
            "",
            "1. Services",
            "{{business_name}} provides {{services}} through {{website_url}}.",
            "",
            "2. User Obligations",
            "Users shall provide accurate information, comply with applicable law, avoid misuse, unauthorized access, scraping, reverse engineering, harmful uploads, fraud, impersonation, and unlawful activity.",
            "",
            "3. Account, Access, and Suspension",
            "The Platform may suspend or restrict access for security risk, unlawful use, payment default, policy breach, or legal requirement.",
            "",
            "4. Payments and Refunds",
            "Pricing, billing cycle, refunds, taxes, and cancellation terms shall be displayed before purchase or subscription confirmation.",
            "",
            "5. AI and Professional Review Disclosure",
            "Where AI-assisted outputs are provided, they are for workflow assistance and require human review before professional, legal, tax, financial, or compliance action.",
            "",
            "6. Liability",
            "To the extent permitted by law, the Platform is not liable for indirect, consequential, special, punitive, or remote losses arising from use or inability to use the services.",
            "",
            "PART B - PRIVACY POLICY",
            "",
            "7. Data Collected",
            "The Platform may collect {{data_categories}} and technical information necessary for security, analytics, account management, billing, support, and service delivery.",
            "",
            "8. Purpose of Processing",
            "Personal data may be processed to provide services, authenticate users, maintain security, process payments, send service communications, improve features, meet legal obligations, and respond to support requests.",
            "",
            "9. Third-party Services",
            "The Platform may use third-party processors or service providers including {{third_party_services}} subject to contractual, security, and lawful processing requirements.",
            "",
            "10. Retention",
            "Data is retained for {{retention_period}} and deleted or anonymized when no longer required, subject to legal, tax, audit, dispute, and security requirements.",
            "",
            "11. User Rights and Contact",
            "Users may contact {{grievance_email}} for privacy requests, grievance escalation, correction, access, or withdrawal-related requests subject to applicable law.",
            "",
            "12. Governing Law",
            "These terms and privacy terms are governed by Indian law, with courts at {{jurisdiction}} having jurisdiction subject to applicable dispute resolution terms.",
            "",
            "Drafting Note: Verify DPDP Act rule updates, consent flows, cookie banners, data processor contracts, payment/refund wording, and sector-specific compliance before publication.",
        ],
    }
]


def _normalize_template(item: dict[str, Any]) -> dict[str, Any]:
    template = dict(item)
    template_id = str(template.get("template_id") or "").strip()
    if not template_id:
        return {}

    fields = template.get("fields") if isinstance(template.get("fields"), list) else []
    normalized_fields: list[dict[str, Any]] = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        field_id = str(field.get("id") or "").strip()
        if not field_id:
            continue
        normalized = {
            "id": field_id,
            "label": str(field.get("label") or field_id),
            "required": bool(field.get("required", False)),
            "type": str(field.get("type") or "text"),
            "placeholder": str(field.get("placeholder") or ""),
        }
        if isinstance(field.get("options"), list) and field.get("options"):
            normalized["options"] = [str(opt) for opt in field["options"]]
        if field.get("help_text"):
            normalized["help_text"] = str(field["help_text"])
        normalized_fields.append(normalized)

    body = template.get("body")
    if isinstance(body, str):
        body_lines = body.splitlines()
    elif isinstance(body, list):
        body_lines = [str(line) for line in body]
    else:
        body_lines = []

    template["template_id"] = template_id
    template["name"] = str(template.get("name") or template_id)
    template["description"] = str(template.get("description") or "")
    template["category"] = str(template.get("category") or "general")
    template["is_premium"] = bool(template.get("is_premium", False))
    template["tags"] = [str(tag) for tag in (template.get("tags") or [])]
    template["act"] = [str(act) for act in (template.get("act") or [])]
    template["court"] = [str(court) for court in (template.get("court") or [])]
    template["fields"] = normalized_fields
    template["body"] = body_lines
    return template


@lru_cache(maxsize=1)
def get_template_library() -> list[dict[str, Any]]:
    if os.getenv("LEGALMITRA_SHOW_LEGACY_TEMPLATES", "").strip().lower() in {"1", "true", "yes"} and _DATA_FILE.exists():
        try:
            data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                normalized = [_normalize_template(item) for item in data if isinstance(item, dict)]
                normalized = [item for item in normalized if item]
                if normalized:
                    return normalized
        except Exception:
            pass

    return [dict(item) for item in _FALLBACK_TEMPLATE_LIBRARY]
