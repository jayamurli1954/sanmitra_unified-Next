# LegalMitra Template Engine

## Current State

LegalMitra has a legacy template catalog loaded from `app/modules/legal_compat/data/legacy_legal_templates.json`.
Most catalog entries are plain text bodies with placeholder replacement. The consultancy agreement now has a structured renderer, but the wider catalog still contains many templates that should be treated as legacy placeholders until upgraded.

## Target State

LegalMitra should launch the template marketplace with fewer, lawyer-grade, clause-driven templates rather than a large count of thin drafts. Each launch template should require only party details, amounts, dates, jurisdiction, and business-specific customization before professional review.

The first launch-grade template set is:

| Priority | Template | Primary users | Launch variants |
| --- | --- | --- | --- |
| 1 | Professional Consultancy Agreement | Freelancers, agencies, SaaS consultants, IT firms, legal/financial consultants | IT, marketing, financial, legal, freelance, retainer |
| 2 | Software Development Agreement | Indian startups, developers, software vendors, SaaS teams | fixed-price, milestone, retainer, maintenance-support |
| 3 | Non-Disclosure Agreement | Startups, vendors, investors, employees, consultants | mutual, one-way, employee, investor, vendor |
| 4 | Employment Agreement | Startups, MSMEs, professional offices | full-time, probation, remote, state-aware, startup/MSME |
| 5 | Website Terms and Privacy Policy Bundle | SaaS, marketplaces, AI apps, service businesses | DPDP-ready SaaS, AI disclosure, analytics/cloud/API integrations |

## Gap

The catalog still behaves like a placeholder library for many documents. A launch-quality template must not rely on generic string concatenation alone.

Required gap closure:

1. Store launch templates as structured clause specs.
2. Render numbered clauses with defined terms.
3. Add Indian-law compliance guardrails.
4. Add missing-clause and risky-wording checks.
5. Render export-ready DOCX/PDF with professional page layout.

## Clause-Driven Template Shape

Templates should move toward this structure:

```json
{
  "template_id": "consultancy_agreement",
  "category": "contracts",
  "launch_priority": 1,
  "clauses": [
    {
      "id": "scope_of_services",
      "title": "Scope of Services",
      "required": true,
      "editable": true,
      "compliance_tags": ["indian_contract_act"]
    }
  ]
}
```

This enables guided inputs, clause toggles, AI enhancement, risk scoring, jurisdiction customization, and professional rendering.

## Quality Gate

A template is launch-grade only if it includes:

- Numbered clauses and defined terms.
- Clear party obligations and responsibilities.
- Payment/tax language where commercially relevant.
- Confidentiality, IP, termination, liability, indemnity, governing law, and dispute resolution where relevant.
- Survival clauses for confidentiality, IP, payment, dispute resolution, and liability.
- Indian compliance references where applicable, including Indian Contract Act, Arbitration and Conciliation Act, Information Technology Act, DPDP Act, GST, Shops and Establishments, PF/ESI/gratuity references, or sector-specific laws.
- Signature blocks and witness blocks where appropriate.
- Human-review disclaimer and execution readiness questions.

## Template-Specific Requirements

### Professional Consultancy Agreement

Must include parties, scope, deliverables, timelines, payment terms, GST, confidentiality, IP ownership, non-solicitation, limitation of liability, termination, arbitration or court jurisdiction, and governing law.

Critical guided inputs:

- project-based or monthly retainer
- fixed fee or milestone fee
- IP ownership choice
- remote or on-site services
- confidentiality level

### Software Development Agreement

Must include project scope, technical specifications, milestones, acceptance testing, source-code ownership, open-source licensing, change requests, warranty, maintenance support, SLA, data protection, confidentiality, and limitation of liability.

Critical clauses:

- client ownership of final code
- developer retention of reusable libraries
- change request mechanism
- delivery acceptance workflow

### Non-Disclosure Agreement

Must include definition of confidential information, exclusions, permitted disclosures, duration, return/destruction, injunction rights, and survival.

Variants:

- mutual NDA
- one-way NDA
- employee NDA
- startup investor NDA
- vendor NDA

### Employment Agreement

Must include job role, compensation, probation, leave policy, confidentiality, IP assignment, reasonable restrictive covenants, code of conduct, data protection, termination, notice period, and statutory references.

Indian compliance inputs:

- state
- remote work
- full-time or contractual status
- startup/MSME status

### Website Terms and Privacy Policy Bundle

Must include Terms of Use and Privacy Policy together because SaaS users need both.

Terms of Use should include user obligations, prohibited activities, account suspension, payment/refund, disclaimers, limitation of liability, and governing law.

Privacy Policy should include DPDP Act 2023 readiness, cookie usage, user rights, retention, third-party services, grievance officer, AI usage disclosure, analytics tracking, cloud storage, and API integrations.

## Implementation Sequence

1. Upgrade consultancy agreement to structured renderer. Status: done.
2. Implement software development agreement renderer. Status: done.
3. Add clause spec metadata for all five launch templates. Status: partially done through public strategy metadata.
4. Implement NDA renderer.
5. Implement employment agreement renderer.
6. Implement website terms/privacy bundle renderer.
7. Replace plain PDF text export with professional A4 layout and add DOCX export.
8. Add template quality tests for every launch-grade template.

## Deferred Scope

- Do not claim the full legacy catalog is lawyer-grade until each template passes the quality gate.
- Do not auto-file, auto-execute, or present drafts as final legal advice.
- Do not send confidential tenant documents to external providers unless tenant policy and user authorization permit it.
- Do not merge LegalMitra template UX into MitraBooks ERP.
