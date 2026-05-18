from __future__ import annotations

import re
from datetime import datetime
from typing import Any

_REQUIRED_NOTICE_KEYS = [
    "sender_name",
    "recipient_name",
    "amount_due",
    "invoice_ref",
]


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _is_empty(value: Any) -> bool:
    return _to_text(value) == ""


def _normalize_fields(fields: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in (fields or {}).items():
        normalized[str(key)] = _to_text(value)

    if not normalized.get("date"):
        normalized["date"] = datetime.now().date().isoformat()
    return normalized


def _looks_notice_template(template: dict[str, Any]) -> bool:
    category = _to_text(template.get("category")).lower()
    name = _to_text(template.get("name")).lower()
    template_id = _to_text(template.get("template_id")).lower()

    return (
        category in {"legal_notice", "legal_notices"}
        or "notice" in name
        or "notice" in template_id
    )


def _looks_consultancy_agreement(template: dict[str, Any]) -> bool:
    category = _to_text(template.get("category")).lower()
    name = _to_text(template.get("name")).lower()
    template_id = _to_text(template.get("template_id")).lower()
    combined = f"{template_id} {name} {category}"
    return "consult" in combined and "agreement" in combined


def _looks_software_development_agreement(template: dict[str, Any]) -> bool:
    category = _to_text(template.get("category")).lower()
    name = _to_text(template.get("name")).lower()
    template_id = _to_text(template.get("template_id")).lower()
    combined = f"{template_id} {name} {category}"
    return "software" in combined and "development" in combined and "agreement" in combined


def _replace_placeholders(text: str, fields: dict[str, str]) -> str:
    rendered = text
    for key, value in fields.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
        rendered = rendered.replace(f"{{{key}}}", value)
    return rendered


def _extract_unresolved_placeholders(text: str) -> list[str]:
    unresolved: set[str] = set()
    for match in re.findall(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", text):
        unresolved.add(match)
    for match in re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", text):
        unresolved.add(match)
    return sorted(unresolved)


def _template_missing_required_fields(template: dict[str, Any], fields: dict[str, str]) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    for field in template.get("fields") or []:
        field_id = _to_text(field.get("id"))
        if not field_id:
            continue
        if bool(field.get("required", False)) and _is_empty(fields.get(field_id)):
            missing.append(
                {
                    "id": field_id,
                    "label": _to_text(field.get("label")) or field_id,
                }
            )
    return missing


def _first_non_empty(fields: dict[str, str], keys: list[str], fallback: str = "") -> str:
    for key in keys:
        value = _to_text(fields.get(key))
        if value:
            return value
    return fallback


def _safe_int(value: str, default: int) -> int:
    text = _to_text(value)
    if not text:
        return default
    digits = re.sub(r"[^0-9]", "", text)
    if not digits:
        return default
    try:
        return int(digits)
    except Exception:
        return default


def _amount_to_words_indian(n: int) -> str:
    if n == 0:
        return "Zero"

    ones = [
        "",
        "One",
        "Two",
        "Three",
        "Four",
        "Five",
        "Six",
        "Seven",
        "Eight",
        "Nine",
    ]
    teens = [
        "Ten",
        "Eleven",
        "Twelve",
        "Thirteen",
        "Fourteen",
        "Fifteen",
        "Sixteen",
        "Seventeen",
        "Eighteen",
        "Nineteen",
    ]
    tens = [
        "",
        "",
        "Twenty",
        "Thirty",
        "Forty",
        "Fifty",
        "Sixty",
        "Seventy",
        "Eighty",
        "Ninety",
    ]

    def two_digits(x: int) -> str:
        if x < 10:
            return ones[x]
        if 10 <= x < 20:
            return teens[x - 10]
        t = x // 10
        o = x % 10
        return f"{tens[t]} {ones[o]}".strip()

    def three_digits(x: int) -> str:
        h = x // 100
        r = x % 100
        if h and r:
            return f"{ones[h]} Hundred {two_digits(r)}"
        if h:
            return f"{ones[h]} Hundred"
        return two_digits(r)

    crore = n // 10000000
    n %= 10000000
    lakh = n // 100000
    n %= 100000
    thousand = n // 1000
    n %= 1000
    hundred_part = n

    parts: list[str] = []
    if crore:
        parts.append(f"{two_digits(crore)} Crore")
    if lakh:
        parts.append(f"{two_digits(lakh)} Lakh")
    if thousand:
        parts.append(f"{two_digits(thousand)} Thousand")
    if hundred_part:
        parts.append(three_digits(hundred_part))

    return " ".join(part.strip() for part in parts if part.strip()).strip()


def _amount_display(fields: dict[str, str]) -> tuple[str, str]:
    raw = _first_non_empty(fields, ["amount_due", "amount", "claim_amount", "invoice_amount"], "")
    amount_value = _safe_int(raw, 0)
    if amount_value <= 0:
        return (raw or "[Amount]", "[Amount in words]")
    return (f"{amount_value:,}", _amount_to_words_indian(amount_value) + " only")


def _notice_legal_basis(template: dict[str, Any]) -> str:
    template_id = _to_text(template.get("template_id")).lower()
    name = _to_text(template.get("name")).lower()
    combined = f"{template_id} {name}"

    if "138" in combined or "cheque" in combined or "ni" in combined:
        return (
            "You are liable under Section 138 read with other applicable provisions of the Negotiable Instruments Act, 1881, "
            "subject to statutory timelines and compliance requirements."
        )
    if "gst" in combined:
        return (
            "Your non-payment/default attracts consequences under the contractual arrangement and applicable provisions of the CGST/SGST framework, "
            "including tax and compliance implications."
        )
    if "rent" in combined or "lease" in combined:
        return (
            "Your default constitutes breach of tenancy/lease obligations and entitles my client to proceed under applicable rent and civil law remedies."
        )
    return (
        "Your default constitutes breach of binding contractual and payment obligations, entitling my client to initiate appropriate civil and other lawful proceedings."
    )


def _render_firm_notice(template: dict[str, Any], fields: dict[str, str]) -> str:
    sender = _first_non_empty(fields, ["sender_name", "client_name", "complainant_name"], "[Sender Name]")
    sender_address = _first_non_empty(fields, ["sender_address", "client_address"], "")
    recipient = _first_non_empty(fields, ["recipient_name", "opposite_party", "accused_name"], "[Recipient Name]")
    recipient_address = _first_non_empty(fields, ["recipient_address", "opposite_party_address", "accused_address"], "")

    invoice_ref = _first_non_empty(fields, ["invoice_ref", "invoice_no", "reference_no", "cheque_no"], "[Reference]")
    invoice_date = _first_non_empty(fields, ["invoice_date", "cheque_date", "transaction_date"], "")
    due_date = _first_non_empty(fields, ["due_date", "payment_due_date"], "")
    date_text = _first_non_empty(fields, ["date"], datetime.now().date().isoformat())
    notice_days = _safe_int(_first_non_empty(fields, ["notice_period", "notice_period_days"], "15"), 15)
    jurisdiction = _first_non_empty(fields, ["jurisdiction", "court_city"], "[Jurisdiction]")
    facts = _first_non_empty(fields, ["facts", "description", "transaction_details", "default_details"], "")
    interest_rate = _first_non_empty(fields, ["interest_rate", "interest"], "")

    amount_figures, amount_words = _amount_display(fields)
    legal_basis = _notice_legal_basis(template)

    amount_line = f"INR {amount_figures} (Rupees {amount_words})"
    if amount_words.startswith("["):
        amount_line = f"INR {amount_figures}"

    interest_line = ""
    if interest_rate:
        interest_line = (
            f"6. My client shall also be entitled to claim contractual/statutory interest at {interest_rate}% per annum and all legal costs incurred for recovery."
        )

    facts_block = facts or (
        f"My client raised invoice/reference {invoice_ref}" + (f" dated {invoice_date}" if invoice_date else "") +
        " for goods/services duly provided. Despite repeated follow-ups, you have failed to clear the outstanding amount."
    )

    lines = [
        "WITHOUT PREJUDICE",
        "",
        "LEGAL NOTICE",
        "",
        f"Date: {date_text}",
        "",
        "To,",
        recipient,
    ]
    if recipient_address:
        lines.append(recipient_address)
    lines.extend(
        [
            "",
            f"Subject: Final demand notice for payment default against reference {invoice_ref}",
            "",
            f"Under instructions from and on behalf of my client {sender}" + (f", {sender_address}" if sender_address else "") + ", this notice is issued as under:",
            "",
            "1. " + facts_block,
            f"2. The outstanding amount legally due and payable by you is {amount_line}.",
        ]
    )
    if due_date:
        lines.append(f"3. The amount became due on {due_date} and remains unpaid till date.")
        lines.append("4. " + legal_basis)
    else:
        lines.append("3. " + legal_basis)
        lines.append("4. Your continued default is deliberate and prejudicial to my client's legal and commercial rights.")

    lines.extend(
        [
            f"5. You are hereby finally called upon to pay the above amount within {notice_days} days from receipt of this notice, failing which my client shall initiate appropriate civil/criminal and other lawful proceedings against you, entirely at your risk as to costs and consequences.",
        ]
    )
    if interest_line:
        lines.append(interest_line)

    lines.extend(
        [
            f"7. TAKE NOTICE that jurisdiction for all proceedings shall be at {jurisdiction}, without prejudice to any other forum available in law.",
            "8. This notice is issued without prejudice to all other rights, claims, and remedies available to my client in law and equity.",
            "",
            "You are advised to treat this as most urgent.",
            "",
            "Authorized Signatory",
            sender,
        ]
    )

    return "\n".join(lines).strip()


def _split_deliverables(value: str) -> list[str]:
    text = _to_text(value)
    if not text:
        return []
    parts = re.split(r"[\n;]+", text)
    cleaned = [part.strip(" -\t") for part in parts if part.strip(" -\t")]
    if len(cleaned) == 1 and "," in cleaned[0]:
        cleaned = [part.strip() for part in cleaned[0].split(",") if part.strip()]
    return cleaned[:10]


def _render_consultancy_agreement(template: dict[str, Any], fields: dict[str, str]) -> str:
    client = _first_non_empty(fields, ["client_name"], "[Client Name]")
    client_address = _first_non_empty(fields, ["client_address", "registered_office"], "[Client Address]")
    consultant = _first_non_empty(fields, ["consultant_name"], "[Consultant Name]")
    consultant_address = _first_non_empty(fields, ["consultant_address"], "[Consultant Address]")
    services = _first_non_empty(fields, ["services_description", "scope_of_services"], "[Describe services in detail]")
    deliverables = _split_deliverables(_first_non_empty(fields, ["deliverables", "milestones"], ""))
    duration = _first_non_empty(fields, ["contract_duration", "duration_months", "agreement_term"], "[Duration]")
    fees = _first_non_empty(fields, ["fees", "professional_fees", "monthly_fee"], "[Fees]")
    payment_terms = _first_non_empty(
        fields,
        ["payment_terms", "invoice_cycle"],
        "Invoices shall be raised monthly in arrears and shall be payable within 15 days from receipt.",
    )
    gst_text = _first_non_empty(fields, ["gst_applicable", "taxes"], "Applicable taxes, including GST where leviable, shall be charged extra.")
    effective_date = _first_non_empty(fields, ["effective_date", "date"], datetime.now().date().isoformat())
    jurisdiction = _first_non_empty(fields, ["jurisdiction", "court_city"], "[City]")
    notice_period = _first_non_empty(fields, ["termination_notice_days", "notice_period"], "30")
    project = _first_non_empty(fields, ["project_name", "engagement_name"], "the Client's business/project")

    deliverable_lines = deliverables or [
        "Written advisory notes, reports, or review comments reasonably required for the engagement.",
        "Periodic consultation calls or meetings as mutually agreed.",
        "Final handover of work product, documents, and agreed supporting materials.",
    ]

    lines = [
        "CONSULTANCY SERVICES AGREEMENT",
        "",
        f"This Consultancy Services Agreement (\"Agreement\") is entered into on {effective_date}.",
        "",
        "1. Parties",
        f"1.1 Client: {client}, having its registered/principal office at {client_address}.",
        f"1.2 Consultant: {consultant}, having address/principal place of work at {consultant_address}.",
        "1.3 The Client and the Consultant are individually referred to as a \"Party\" and collectively as the \"Parties\".",
        "",
        "2. Definitions",
        "2.1 \"Services\" means the professional consultancy services described in Clause 3 and any written statement of work accepted by both Parties.",
        "2.2 \"Deliverables\" means reports, notes, documents, work product, recommendations, specifications, or other outputs created specifically for the Client under this Agreement.",
        "2.3 \"Confidential Information\" includes business, technical, financial, legal, client, customer, operational, and strategic information disclosed by either Party in any form.",
        "2.4 \"Pre-existing IP\" means intellectual property, tools, templates, know-how, methods, software, or materials owned or developed by the Consultant before this Agreement or independently of the Services.",
        "",
        "3. Appointment and Scope of Services",
        f"3.1 The Client appoints the Consultant to provide consultancy services for {project}.",
        f"3.2 The Consultant shall provide the following Services: {services}",
        "3.3 The Consultant shall perform the Services with reasonable professional skill, care, diligence, and in accordance with applicable Indian law.",
        "3.4 Any material change in scope, timeline, fee, or responsibility shall be recorded in writing by the Parties.",
        "",
        "4. Deliverables and Timelines",
    ]
    for idx, item in enumerate(deliverable_lines, start=1):
        lines.append(f"4.{idx} {item}")
    lines.extend(
        [
            "4.4 Timelines shall be mutually agreed in writing. Delay caused by non-availability of Client inputs, approvals, access, or documents shall extend the relevant timeline proportionately.",
            "",
            "5. Fees, Taxes, and Payment Terms",
            f"5.1 The Client shall pay the Consultant professional fees of INR {fees}.",
            f"5.2 {payment_terms}",
            f"5.3 {gst_text}",
            "5.4 Pre-approved out-of-pocket expenses, if any, shall be reimbursed by the Client against supporting documents.",
            "5.5 Delayed payment beyond the agreed due date may attract reasonable interest or suspension of Services after written notice.",
            "",
            "6. Client Responsibilities",
            "6.1 The Client shall provide accurate instructions, timely approvals, relevant documents, access, and information required for performance of the Services.",
            "6.2 The Consultant shall not be responsible for delay, defect, or legal/commercial consequence arising from incomplete, incorrect, delayed, or withheld Client information.",
            "",
            "7. Confidentiality",
            "7.1 Each Party shall keep the other Party's Confidential Information confidential and shall use it only for performance of this Agreement.",
            "7.2 Confidentiality obligations shall not apply to information that is public, independently developed, already known without restriction, or required to be disclosed by law or a competent authority.",
            "7.3 This clause shall survive termination of this Agreement.",
            "",
            "8. Intellectual Property Rights",
            "8.1 Subject to full payment of undisputed fees, Deliverables specifically created for the Client shall belong to the Client unless otherwise agreed in writing.",
            "8.2 The Consultant shall retain ownership of Pre-existing IP, generic know-how, methods, frameworks, templates, and reusable tools.",
            "8.3 The Consultant grants the Client a non-exclusive, perpetual licence to use any Consultant Pre-existing IP embedded in the Deliverables only to the extent necessary for internal use of the Deliverables.",
            "",
            "9. Compliance, Data, and Professional Standards",
            "9.1 Each Party shall comply with applicable laws, tax obligations, confidentiality obligations, and data protection requirements relevant to the engagement.",
            "9.2 The Consultant shall not represent that any output is a statutory filing, legal opinion, audit certificate, or regulated professional certification unless expressly agreed and legally permitted.",
            "",
            "10. Independent Contractor",
            "10.1 The Consultant is an independent contractor and nothing in this Agreement creates employment, partnership, agency, or joint venture between the Parties.",
            "10.2 The Consultant shall be responsible for its own statutory, professional, and tax compliance unless otherwise required by law.",
            "",
            "11. Non-Solicitation",
            "11.1 During the term of this Agreement and for 12 months thereafter, neither Party shall knowingly solicit for employment the employees or key personnel of the other Party who were directly involved in the engagement, except with prior written consent.",
            "",
            "12. Limitation of Liability",
            "12.1 Neither Party shall be liable for indirect, consequential, special, punitive, or remote losses, including loss of profit, goodwill, or business opportunity.",
            "12.2 The Consultant's aggregate liability under this Agreement shall not exceed the fees actually received by the Consultant under this Agreement during the three months immediately preceding the claim, except for fraud, wilful misconduct, confidentiality breach, or liabilities that cannot be limited under law.",
            "",
            "13. Indemnity",
            "13.1 Each Party shall indemnify the other against direct losses arising from its material breach of this Agreement, fraud, wilful misconduct, or violation of applicable law.",
            "13.2 The Client shall indemnify the Consultant against claims arising from Client-provided materials, instructions, data, or use of Deliverables contrary to agreed scope.",
            "",
            "14. Term and Termination",
            f"14.1 This Agreement shall remain valid for {duration} months from the Effective Date unless terminated earlier in accordance with this Agreement.",
            f"14.2 Either Party may terminate this Agreement by giving {notice_period} days' written notice.",
            "14.3 Either Party may terminate immediately upon material breach by the other Party if such breach is not cured within 15 days of written notice.",
            "14.4 Upon termination, the Client shall pay all undisputed fees for Services performed and approved expenses incurred up to the termination date.",
            "14.5 Clauses relating to confidentiality, intellectual property, payment, liability, indemnity, dispute resolution, and governing law shall survive termination.",
            "",
            "15. Force Majeure",
            "15.1 Neither Party shall be liable for delay or failure caused by events beyond reasonable control, including acts of God, government action, court orders, strikes, war, epidemic, network outage, or other force majeure events.",
            "",
            "16. Governing Law and Dispute Resolution",
            "16.1 This Agreement shall be governed by and construed in accordance with the laws of India.",
            f"16.2 Subject to any mutually agreed arbitration clause, the courts at {jurisdiction} shall have exclusive jurisdiction.",
            "16.3 The Parties shall first attempt to resolve disputes through good-faith discussion before initiating formal proceedings.",
            "",
            "17. Notices",
            "17.1 Notices shall be sent by hand delivery, registered post, courier, or email to the addresses last notified by the Parties in writing.",
            "",
            "18. Miscellaneous",
            "18.1 This Agreement constitutes the entire understanding between the Parties for the Services and supersedes prior discussions on the same subject.",
            "18.2 No amendment shall be valid unless recorded in writing and accepted by both Parties.",
            "18.3 If any provision is held invalid, the remaining provisions shall continue in force.",
            "",
            "IN WITNESS WHEREOF, the Parties have executed this Agreement on the date first written above.",
            "",
            "For the Client",
            f"Name: {client}",
            "Authorised Signatory: __________________",
            "Designation: __________________________",
            "Date: _________________________________",
            "",
            "For the Consultant",
            f"Name: {consultant}",
            "Signature: ____________________________",
            "Date: _________________________________",
            "",
            "Witness 1",
            "Name: _________________________________",
            "Address: ______________________________",
            "Signature: ____________________________",
            "",
            "Witness 2",
            "Name: _________________________________",
            "Address: ______________________________",
            "Signature: ____________________________",
            "",
            "Drafting Note: This template is a structured first draft for professional review. Verify stamp duty, tax treatment, sector-specific regulation, and enforceability before execution.",
        ]
    )
    return "\n".join(lines).strip()


def _render_software_development_agreement(template: dict[str, Any], fields: dict[str, str]) -> str:
    client = _first_non_empty(fields, ["client_name"], "[Client Name]")
    client_address = _first_non_empty(fields, ["client_address", "registered_office"], "[Client Address]")
    developer = _first_non_empty(fields, ["developer_name", "vendor_name", "consultant_name"], "[Developer Name]")
    developer_address = _first_non_empty(fields, ["developer_address", "vendor_address", "consultant_address"], "[Developer Address]")
    project_name = _first_non_empty(fields, ["project_name", "software_name"], "[Project/Software Name]")
    scope = _first_non_empty(fields, ["project_scope", "scope_of_work", "services_description"], "[Detailed project scope]")
    specifications = _first_non_empty(fields, ["technical_specifications", "specifications"], "[Technical specifications]")
    milestones = _split_deliverables(_first_non_empty(fields, ["milestones", "deliverables"], ""))
    fees = _first_non_empty(fields, ["fees", "project_fee", "development_fee"], "[Fees]")
    payment_terms = _first_non_empty(
        fields,
        ["payment_terms"],
        "Payment shall be linked to mutually agreed milestones and invoices shall be payable within 15 days from receipt.",
    )
    acceptance_period = _first_non_empty(fields, ["acceptance_period_days", "acceptance_period"], "10")
    maintenance_period = _first_non_empty(fields, ["maintenance_period", "support_period"], "30 days after final acceptance")
    sla = _first_non_empty(fields, ["sla", "support_sla"], "commercially reasonable response times during business hours")
    change_request = _first_non_empty(
        fields,
        ["change_request_process"],
        "Any change in scope, timeline, technical specification, or fee shall be documented in a written change request approved by both Parties.",
    )
    open_source = _first_non_empty(
        fields,
        ["open_source_policy"],
        "The Developer may use reputable open-source components only in compliance with their applicable licences and shall disclose material copyleft dependencies before delivery.",
    )
    effective_date = _first_non_empty(fields, ["effective_date", "date"], datetime.now().date().isoformat())
    jurisdiction = _first_non_empty(fields, ["jurisdiction", "court_city"], "[City]")
    notice_period = _first_non_empty(fields, ["termination_notice_days", "notice_period"], "30")

    milestone_lines = milestones or [
        "Requirements confirmation and technical architecture note.",
        "Development build with agreed core features.",
        "Testing, defect fixes, deployment support, and final handover.",
    ]

    lines = [
        "SOFTWARE DEVELOPMENT AGREEMENT",
        "",
        f"This Software Development Agreement (\"Agreement\") is entered into on {effective_date}.",
        "",
        "1. Parties",
        f"1.1 Client: {client}, having its registered/principal office at {client_address}.",
        f"1.2 Developer: {developer}, having its registered/principal office/place of work at {developer_address}.",
        "1.3 The Client and Developer are individually referred to as a \"Party\" and collectively as the \"Parties\".",
        "",
        "2. Definitions",
        f"2.1 \"Project\" means development of {project_name} as described in this Agreement and any accepted statement of work.",
        "2.2 \"Deliverables\" means source code, object code, documentation, configurations, designs, APIs, deployment scripts, and other work product created specifically for the Client.",
        "2.3 \"Acceptance Criteria\" means the functional, technical, security, and performance requirements agreed in writing by the Parties.",
        "2.4 \"Background Materials\" means pre-existing code, reusable libraries, tools, frameworks, know-how, templates, and components owned or controlled by the Developer before or independently of the Project.",
        "2.5 \"Open-Source Software\" means third-party software distributed under an open-source licence.",
        "",
        "3. Project Scope and Technical Specifications",
        f"3.1 The Developer shall design, develop, test, and deliver {project_name} for the Client.",
        f"3.2 Project Scope: {scope}",
        f"3.3 Technical Specifications: {specifications}",
        "3.4 The Developer shall use reasonable professional skill and care and shall comply with applicable Indian law, data protection obligations, and agreed security practices.",
        "",
        "4. Milestones and Delivery Schedule",
    ]
    for idx, item in enumerate(milestone_lines, start=1):
        lines.append(f"4.{idx} {item}")
    lines.extend(
        [
            "4.4 Delivery dates depend on timely Client approvals, credentials, content, test data, API access, third-party approvals, and infrastructure readiness.",
            "",
            "5. Acceptance Testing",
            f"5.1 The Client shall test each Deliverable within {acceptance_period} days from delivery.",
            "5.2 A Deliverable shall be deemed accepted if the Client gives written acceptance, uses it in production, or does not report material defects within the acceptance period.",
            "5.3 Reported defects must be reproducible and materially deviate from the Acceptance Criteria. Cosmetic preferences, new requirements, and scope changes shall be handled as change requests.",
            "5.4 The Developer shall correct accepted material defects within a commercially reasonable time.",
            "",
            "6. Change Requests and Scope Control",
            f"6.1 {change_request}",
            "6.2 The Developer is not obliged to perform out-of-scope work unless the Parties agree revised fees, timelines, and responsibilities in writing.",
            "",
            "7. Fees, Taxes, and Payment Terms",
            f"7.1 The Client shall pay development fees of INR {fees}.",
            f"7.2 {payment_terms}",
            "7.3 Applicable taxes, including GST where leviable, shall be charged extra unless expressly included.",
            "7.4 Delay in payment may result in suspension of development, deployment, support, or access to deliverables after written notice.",
            "",
            "8. Intellectual Property and Source Code Ownership",
            "8.1 Subject to full payment of undisputed fees, the Client shall own the final project-specific Deliverables created exclusively for the Client.",
            "8.2 The Developer retains ownership of Background Materials, reusable libraries, generic tools, know-how, development methods, and independently created components.",
            "8.3 The Developer grants the Client a perpetual, non-exclusive licence to use embedded Background Materials only as necessary to use the Deliverables.",
            "8.4 Until full payment is received, ownership and transfer rights in the Deliverables shall not pass to the Client except to the extent required by law or expressly agreed in writing.",
            "",
            "9. Open-Source and Third-Party Components",
            f"9.1 {open_source}",
            "9.2 The Client shall be responsible for paid third-party subscriptions, hosting, domains, APIs, app-store fees, and licences unless expressly included in the fees.",
            "9.3 The Developer shall not knowingly include third-party components that prevent the Client from commercially using the Deliverables in the agreed manner.",
            "",
            "10. Maintenance, Support, and SLA",
            f"10.1 The Developer shall provide maintenance support for {maintenance_period}.",
            f"10.2 Support SLA: {sla}.",
            "10.3 Maintenance excludes new features, major redesign, third-party failures, hosting outages, infrastructure changes, user-caused issues, and issues caused by unauthorized modification.",
            "",
            "11. Warranty",
            "11.1 The Developer warrants that the Deliverables will materially conform to the agreed scope and Acceptance Criteria at the time of delivery.",
            "11.2 Except as expressly stated, the Developer does not warrant uninterrupted operation, error-free performance, business outcome, marketplace approval, search ranking, or compatibility with future third-party changes.",
            "",
            "12. Data Protection and Security",
            "12.1 Each Party shall comply with applicable Indian data protection, privacy, cyber security, and confidentiality obligations, including DPDP Act readiness where personal data is processed.",
            "12.2 The Client shall not provide production personal data unless required for the Project and authorized under applicable law and tenant/user policy.",
            "12.3 The Developer shall use reasonable safeguards for credentials, repositories, test data, and production access shared by the Client.",
            "",
            "13. Confidentiality",
            "13.1 Each Party shall protect the other Party's confidential, technical, business, financial, product, user, and source-code information.",
            "13.2 Confidentiality obligations shall survive termination.",
            "",
            "14. Limitation of Liability",
            "14.1 Neither Party shall be liable for indirect, consequential, special, punitive, or remote losses, including loss of profit, revenue, goodwill, data, or business opportunity.",
            "14.2 The Developer's aggregate liability shall not exceed the fees actually received for the Project during the three months preceding the claim, except for fraud, wilful misconduct, confidentiality breach, or liabilities that cannot be limited by law.",
            "",
            "15. Indemnity",
            "15.1 Each Party shall indemnify the other against direct losses arising from its material breach, fraud, wilful misconduct, or violation of applicable law.",
            "15.2 The Client shall indemnify the Developer for claims arising from Client materials, instructions, data, illegal content, third-party platform decisions, or use of Deliverables beyond agreed scope.",
            "",
            "16. Term and Termination",
            f"16.1 Either Party may terminate this Agreement by giving {notice_period} days' written notice.",
            "16.2 Either Party may terminate immediately for uncured material breach after 15 days' written cure notice.",
            "16.3 On termination, the Client shall pay for work completed, committed third-party costs, and approved expenses up to the termination date.",
            "16.4 Confidentiality, IP, payment, liability, indemnity, dispute resolution, and governing law clauses shall survive termination.",
            "",
            "17. Force Majeure",
            "17.1 Neither Party shall be liable for delay or non-performance caused by events beyond reasonable control, including government action, court orders, war, epidemic, network outage, data-centre failure, platform outage, or other force majeure event.",
            "",
            "18. Governing Law and Dispute Resolution",
            "18.1 This Agreement shall be governed by the laws of India.",
            f"18.2 Subject to any mutually agreed arbitration clause, courts at {jurisdiction} shall have exclusive jurisdiction.",
            "18.3 The Parties shall first attempt good-faith commercial resolution before formal proceedings.",
            "",
            "19. Notices and Miscellaneous",
            "19.1 Notices shall be sent by hand delivery, registered post, courier, or email to the latest address notified by each Party.",
            "19.2 This Agreement is the entire agreement for the Project and may be amended only in writing accepted by both Parties.",
            "19.3 If any provision is invalid, the remaining provisions shall continue in force.",
            "",
            "IN WITNESS WHEREOF, the Parties have executed this Agreement on the date first written above.",
            "",
            "For the Client",
            f"Name: {client}",
            "Authorised Signatory: __________________",
            "Designation: __________________________",
            "Date: _________________________________",
            "",
            "For the Developer",
            f"Name: {developer}",
            "Authorised Signatory/Signature: ________",
            "Designation: __________________________",
            "Date: _________________________________",
            "",
            "Witness 1",
            "Name: _________________________________",
            "Address: ______________________________",
            "Signature: ____________________________",
            "",
            "Witness 2",
            "Name: _________________________________",
            "Address: ______________________________",
            "Signature: ____________________________",
            "",
            "Drafting Note: Verify technical scope, acceptance criteria, open-source licences, GST/TDS, stamp duty, data protection obligations, and enforceability before execution.",
        ]
    )
    return "\n".join(lines).strip()


def _render_base_template(template: dict[str, Any], fields: dict[str, str]) -> str:
    body_lines = template.get("body") or []
    rendered = _replace_placeholders("\n".join(str(line) for line in body_lines), fields)
    return rendered.strip()


def _recommended_clauses(template: dict[str, Any], fields: dict[str, str]) -> list[str]:
    if _looks_software_development_agreement(template):
        recommendations = [
            "Detailed statement of work with technical specifications and assumptions",
            "Milestone-linked payment schedule and acceptance testing period",
            "Source-code ownership with developer reusable-library carve-out",
            "Open-source component disclosure and licence compliance clause",
            "Change request, warranty, maintenance support, SLA, and defect-classification workflow",
            "DPDP/data protection, credential handling, confidentiality, liability, indemnity, and jurisdiction clauses",
        ]
        if _is_empty(fields.get("jurisdiction")):
            recommendations.append("Exclusive jurisdiction city before execution")
        if _is_empty(fields.get("milestones")) and _is_empty(fields.get("deliverables")):
            recommendations.append("Milestones and acceptance criteria")
        if _is_empty(fields.get("technical_specifications")):
            recommendations.append("Technical specifications and platform assumptions")
        return recommendations

    if _looks_consultancy_agreement(template):
        recommendations = [
            "Statement of work with deliverables, acceptance criteria, and timelines",
            "GST, TDS, invoicing, expense reimbursement, and late-payment language",
            "Client ownership of project deliverables with consultant pre-existing IP carve-out",
            "Confidentiality, data protection, and survival clauses",
            "Termination, limitation of liability, indemnity, governing law, and jurisdiction clauses",
        ]
        if _is_empty(fields.get("jurisdiction")):
            recommendations.append("Exclusive jurisdiction city before execution")
        if _is_empty(fields.get("deliverables")):
            recommendations.append("Specific deliverables and acceptance criteria")
        return recommendations

    if not _looks_notice_template(template):
        return []

    recommendations: list[str] = []
    if _is_empty(fields.get("interest_rate")) and _is_empty(fields.get("interest")):
        recommendations.append("Interest clause with rate and accrual period")
    if _is_empty(fields.get("jurisdiction")):
        recommendations.append("Exclusive jurisdiction clause")
    if _is_empty(fields.get("mode_of_service")):
        recommendations.append("Service/dispatch proof clause (RPAD/Email/Courier)")
    recommendations.append("Without prejudice and reservation of rights clause")
    recommendations.append("Legal costs and consequences clause")
    return recommendations


def _follow_up_questions(
    template: dict[str, Any],
    fields: dict[str, str],
    missing_required: list[dict[str, str]],
    unresolved: list[str],
) -> list[str]:
    questions: list[str] = []

    for item in missing_required:
        questions.append(f"Please provide {item['label']} for a complete and enforceable draft.")

    for key in unresolved[:8]:
        questions.append(f"Please share the value for '{key}' to complete all template clauses.")

    if _looks_notice_template(template):
        if _is_empty(fields.get("recipient_address")):
            questions.append("What is the full service address of the notice recipient?")
        if _is_empty(fields.get("due_date")):
            questions.append("What was the exact due date/payment deadline under the invoice or agreement?")
        if _is_empty(fields.get("jurisdiction")):
            questions.append("Which city/forum should be mentioned as jurisdiction?")
        if _is_empty(fields.get("transaction_details")) and _is_empty(fields.get("facts")) and _is_empty(fields.get("description")):
            questions.append("Please provide 3-5 concise facts (transaction, default, reminders) to strengthen legal firmness.")
        if _is_empty(fields.get("supporting_documents")):
            questions.append("Which documents are available (invoice, delivery proof, emails, ledger, reminders)?")

    if _looks_consultancy_agreement(template):
        if _is_empty(fields.get("client_address")):
            questions.append("What is the Client's full registered/principal office address?")
        if _is_empty(fields.get("consultant_address")):
            questions.append("What is the Consultant's full address or principal place of work?")
        if _is_empty(fields.get("deliverables")):
            questions.append("What are the exact deliverables, milestones, or acceptance criteria?")
        if _is_empty(fields.get("payment_terms")):
            questions.append("What invoice cycle and payment due date should be used?")
        if _is_empty(fields.get("jurisdiction")):
            questions.append("Which city should be used for governing jurisdiction?")

    if _looks_software_development_agreement(template):
        if _is_empty(fields.get("client_address")):
            questions.append("What is the Client's full registered/principal office address?")
        if _is_empty(fields.get("developer_address")) and _is_empty(fields.get("vendor_address")):
            questions.append("What is the Developer's full registered/principal office address?")
        if _is_empty(fields.get("technical_specifications")) and _is_empty(fields.get("specifications")):
            questions.append("What are the technical specifications, platform assumptions, and integrations?")
        if _is_empty(fields.get("milestones")) and _is_empty(fields.get("deliverables")):
            questions.append("What milestones, deliverables, and acceptance criteria should be used?")
        if _is_empty(fields.get("payment_terms")):
            questions.append("What milestone payment schedule and invoice due date should be used?")
        if _is_empty(fields.get("jurisdiction")):
            questions.append("Which city should be used for governing jurisdiction?")
        if _is_empty(fields.get("open_source_policy")):
            questions.append("Are open-source components allowed, and are any copyleft licences prohibited?")

    seen: set[str] = set()
    unique_questions: list[str] = []
    for q in questions:
        token = q.lower().strip()
        if token in seen:
            continue
        seen.add(token)
        unique_questions.append(q)

    return unique_questions[:12]


def render_template_document(*, template: dict[str, Any], fields: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_fields(fields)
    missing_required = _template_missing_required_fields(template, normalized)

    if _looks_notice_template(template):
        rendered = _render_firm_notice(template, normalized)
    elif _looks_consultancy_agreement(template):
        rendered = _render_consultancy_agreement(template, normalized)
    elif _looks_software_development_agreement(template):
        rendered = _render_software_development_agreement(template, normalized)
    else:
        rendered = _render_base_template(template, normalized)

    unresolved = _extract_unresolved_placeholders(rendered)
    follow_up_questions = _follow_up_questions(template, normalized, missing_required, unresolved)

    # Notice drafts are considered filing-ready only when core fields are present and no unresolved placeholders remain.
    core_missing = []
    if _looks_notice_template(template):
        for key in _REQUIRED_NOTICE_KEYS:
            if _is_empty(normalized.get(key)):
                core_missing.append(key)

    needs_more_information = bool(missing_required or unresolved or core_missing)
    if _looks_consultancy_agreement(template) and follow_up_questions:
        needs_more_information = True
    if _looks_software_development_agreement(template) and follow_up_questions:
        needs_more_information = True
    draft_status = "needs_more_information" if needs_more_information else "ready"

    firmness_score = 88 if _looks_notice_template(template) else 80
    if _looks_consultancy_agreement(template):
        firmness_score = 91
    if _looks_software_development_agreement(template):
        firmness_score = 92
    if needs_more_information:
        firmness_score = max(65, firmness_score - 14)

    return {
        "rendered_document": rendered,
        "draft_status": draft_status,
        "missing_required_fields": missing_required,
        "unresolved_placeholders": unresolved,
        "follow_up_questions": follow_up_questions,
        "recommended_clauses": _recommended_clauses(template, normalized),
        "firmness_score": firmness_score,
    }



def _normalize_parties(parties: Any) -> dict[str, str]:
    out: dict[str, str] = {}
    if not isinstance(parties, dict):
        return out
    for key, value in parties.items():
        out[str(key).strip().lower()] = _to_text(value)
    return out


def _find_party(parties: dict[str, str], candidates: list[str], fallback: str = "") -> str:
    for key in candidates:
        value = _to_text(parties.get(key.lower()))
        if value:
            return value
    return fallback


def _build_non_notice_draft(
    *,
    document_type: str,
    facts: str,
    parties: dict[str, str],
    grounds: list[str],
    prayer: str,
) -> str:
    sender = _find_party(parties, ["sender", "client", "complainant", "petitioner"], "[Client Name]")
    recipient = _find_party(parties, ["recipient", "opposite_party", "respondent", "accused"], "[Opposite Party Name]")
    sender_address = _find_party(parties, ["sender_address", "client_address", "petitioner_address"])
    recipient_address = _find_party(parties, ["recipient_address", "opposite_party_address", "respondent_address"])
    date_text = datetime.now().date().isoformat()
    doc_label = (document_type or "document").strip().title()

    lines = [
        "WITHOUT PREJUDICE",
        "",
        f"DRAFT {doc_label.upper()}",
        "",
        f"Date: {date_text}",
        "",
        "1. Parties:",
        f"- Client/Applicant: {sender}" + (f", {sender_address}" if sender_address else ""),
        f"- Opposite Party/Respondent: {recipient}" + (f", {recipient_address}" if recipient_address else ""),
        "",
        "2. Factual Matrix:",
        facts or "[Please provide full factual chronology with dates and documentary references.]",
        "",
        "3. Legal Grounds:",
    ]
    if grounds:
        for idx, item in enumerate(grounds, start=1):
            lines.append(f"{idx}. {item}")
    else:
        lines.append("1. [Please provide statutory and contractual grounds.]")

    lines.extend(
        [
            "",
            "4. Relief/Prayer:",
            prayer or "[Please provide specific and quantifiable relief sought.]",
            "",
            "5. Reservation of Rights:",
            "This draft is prepared without prejudice to all rights, claims, and remedies available in law and equity.",
        ]
    )
    return "\n".join(lines).strip()


def _follow_up_for_document(
    *,
    document_type: str,
    facts: str,
    parties: dict[str, str],
    grounds: list[str],
    prayer: str,
    notice_specific: dict[str, str],
) -> list[str]:
    questions: list[str] = []

    sender = _find_party(parties, ["sender", "client", "complainant", "petitioner"])
    recipient = _find_party(parties, ["recipient", "opposite_party", "respondent", "accused"])
    recipient_address = _find_party(parties, ["recipient_address", "opposite_party_address", "respondent_address"])

    if not sender:
        questions.append("Who is the exact client/issuer name to be shown in the draft?")
    if not recipient:
        questions.append("Who is the exact notice recipient/opposite party?")
    if not recipient_address:
        questions.append("What is the complete service address of the recipient for enforceable notice dispatch?")

    if not facts or len(facts.strip()) < 120:
        questions.append("Please provide a full factual chronology with dates, invoices/communications, and default events.")
    if not grounds or len(grounds) < 2:
        questions.append("Please provide at least 2-3 specific legal grounds/statutory provisions supporting your claim.")
    if not prayer or len(prayer.strip()) < 30:
        questions.append("Please specify exact relief sought (amount, timeline, interest, and costs) in measurable terms.")

    if "notice" in document_type:
        if _is_empty(notice_specific.get("amount_due")):
            questions.append("What is the exact outstanding amount (in INR) to be demanded?")
        if _is_empty(notice_specific.get("invoice_ref")):
            questions.append("Please provide invoice/reference number and date for a legally strong demand notice.")
        if _is_empty(notice_specific.get("due_date")):
            questions.append("What was the contractual/statutory due date for payment?")
        if _is_empty(notice_specific.get("jurisdiction")):
            questions.append("Which city/forum should be specified for jurisdiction?")

    seen: set[str] = set()
    out: list[str] = []
    for item in questions:
        token = item.lower().strip()
        if token in seen:
            continue
        seen.add(token)
        out.append(item)
    return out[:12]


def render_guided_document_draft(
    *,
    document_type: str,
    facts: str,
    parties: Any,
    legal_grounds: list[str],
    prayer: str,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    doc_type = _to_text(document_type).lower() or "legal notice"
    facts_text = _to_text(facts)
    prayer_text = _to_text(prayer)
    parties_map = _normalize_parties(parties)
    grounds = [_to_text(g) for g in (legal_grounds or []) if _to_text(g)]
    extras = {str(k): _to_text(v) for k, v in (extra_fields or {}).items()}

    if "notice" in doc_type:
        notice_fields = {
            "sender_name": _find_party(parties_map, ["sender", "client", "complainant"], ""),
            "sender_address": _find_party(parties_map, ["sender_address", "client_address"], ""),
            "recipient_name": _find_party(parties_map, ["recipient", "opposite_party", "accused"], ""),
            "recipient_address": _find_party(parties_map, ["recipient_address", "opposite_party_address", "accused_address"], ""),
            "amount_due": _to_text(extras.get("amount_due")),
            "invoice_ref": _to_text(extras.get("invoice_ref")),
            "invoice_date": _to_text(extras.get("invoice_date")),
            "due_date": _to_text(extras.get("due_date")),
            "notice_period": _to_text(extras.get("notice_period")) or "15",
            "interest_rate": _to_text(extras.get("interest_rate")),
            "jurisdiction": _to_text(extras.get("jurisdiction")),
            "transaction_details": facts_text,
            "date": _to_text(extras.get("date")) or datetime.now().date().isoformat(),
        }
        notice_template = {
            "category": "legal_notices",
            "name": "Guided Legal Notice Draft",
            "template_id": "guided_legal_notice",
            "fields": [
                {"id": "sender_name", "label": "Sender Name", "required": True},
                {"id": "recipient_name", "label": "Recipient Name", "required": True},
                {"id": "amount_due", "label": "Amount Due", "required": True},
                {"id": "invoice_ref", "label": "Invoice/Reference", "required": True},
            ],
        }
        notice_draft = render_template_document(template=notice_template, fields=notice_fields)
        rendered = notice_draft["rendered_document"]
        if grounds:
            rendered += "\n\nLegal Grounds Asserted:\n" + "\n".join(f"- {g}" for g in grounds)
        if prayer_text:
            rendered += "\n\nRelief Sought:\n" + prayer_text
        follow_up = _follow_up_for_document(
            document_type=doc_type,
            facts=facts_text,
            parties=parties_map,
            grounds=grounds,
            prayer=prayer_text,
            notice_specific=notice_fields,
        )
        needs_more = notice_draft["draft_status"] != "ready" or bool(follow_up)
        return {
            "drafted_document": rendered.strip(),
            "draft_status": "needs_more_information" if needs_more else "ready",
            "follow_up_questions": follow_up or notice_draft["follow_up_questions"],
            "recommended_clauses": notice_draft["recommended_clauses"],
            "firmness_score": notice_draft["firmness_score"],
        }

    rendered = _build_non_notice_draft(
        document_type=doc_type,
        facts=facts_text,
        parties=parties_map,
        grounds=grounds,
        prayer=prayer_text,
    )
    follow_up = _follow_up_for_document(
        document_type=doc_type,
        facts=facts_text,
        parties=parties_map,
        grounds=grounds,
        prayer=prayer_text,
        notice_specific={},
    )
    needs_more = bool(follow_up)
    recommendations = [
        "Attach chronology table with date-wise events and evidence references.",
        "Add jurisdiction and limitation paragraph before finalization.",
        "Cross-check relief language against documentary record.",
    ]
    return {
        "drafted_document": rendered,
        "draft_status": "needs_more_information" if needs_more else "ready",
        "follow_up_questions": follow_up,
        "recommended_clauses": recommendations,
        "firmness_score": 72 if needs_more else 84,
    }
