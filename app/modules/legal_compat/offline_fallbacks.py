"""Authorized offline legal research fallbacks for LegalMitra Stage 2."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_CLOSING_DISCLAIMER = (
    "\n\n---\n"
    "*Disclaimer: This note is prepared for the use of the instructing advocate only. "
    "Verify the current legal position, recent amendments, and jurisdiction-specific practice "
    "before filing, advising a client, or taking final legal action. "
    "No professional liability attaches to this output.*"
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_query(query: str) -> str:
    return " ".join((query or "").strip().lower().split())


def offline_legal_fallback(query: str, query_type: str) -> dict[str, Any] | None:
    """Return narrow, source-backed guidance when the AI provider is unavailable."""
    q = _normalize_query(query)

    # Stage 2 GST refund / Section 54 family — authorized offline slice.
    # Senior-counsel spine: Executive view → Direct answer → Relevant dates →
    # Authorities → Risk areas → Practical note → Recommended next steps →
    # Related provisions → Limitations → Disclaimer. No invented judgments.
    if (
        ("section 54" in q or "s.54" in q or "s 54" in q)
        and ("gst" in q or "cgst" in q or "igst" in q or "refund" in q or "interest" in q)
    ) or (
        "refund" in q and ("gst" in q or "cgst" in q or "igst" in q or "tax refund" in q)
    ):
        wants_cases = any(
            token in q
            for token in (
                "case",
                "cases",
                "judgment",
                "judgement",
                "judgments",
                "judgements",
                "precedent",
                "referred",
                "citation",
                "authorities",
            )
        )
        judgments_block = (
            "**Judgments**\n"
            "- No matching judgments retrieved from the current corpus for this query. "
            "LegalMitra will not invent case names. Ingest or sync refund/limitation "
            "judgments for this tenant, then retry with an explicit case-search request."
            if wants_cases
            else "**Judgments**\n"
            "- Not searched for this query. Ask for referred cases / judgments if you "
            "need corpus-backed authorities."
        )
        response = (
            "**Time Limit — CGST Act Section 54 Refund Claims**\n\n"
            "**Executive view:** My preliminary view is that most refund limitation "
            "disputes under Section 54 arise from an incorrect determination of the "
            "**relevant date**, rather than disagreement about the two-year period "
            "itself. Before advising a client, identify the refund category and map "
            "it to the applicable clause of the Explanation to Section 54 "
            "(verify the current statutory text).\n\n"
            "**Direct answer:** Under **Section 54(1)** of the Central Goods and Services "
            "Tax Act, 2017, a refund application for tax, interest, or any other amount "
            "must ordinarily be filed within **two years from the relevant date** in the "
            "prescribed form and manner.\n\n"
            "**Relevant date (illustrative categories from the Explanation to Section 54)**\n\n"
            "| Refund / claim situation | Relevant date (statutory concept) |\n"
            "| --- | --- |\n"
            "| Excess tax / amount paid | Date of payment of such tax / amount |\n"
            "| Export of goods | Date on which the ship / aircraft leaves India "
            "(or goods leave India, for land/postal situations as specified) |\n"
            "| Export of services | Date of receipt of payment in convertible foreign "
            "exchange / permitted currency (or invoice-linked rule where advance is "
            "received, as specified) |\n"
            "| Supplies to SEZ / related zero-rated situations | As specified in the "
            "Explanation for the relevant zero-rated supply class |\n"
            "| Deemed exports | Date on which the return relating to such deemed "
            "exports is furnished |\n"
            "| Unutilised ITC refund under Section 54(3) | Refer to the specific "
            "Explanation clause applicable to refunds under Section 54(3) for the "
            "claim period (do not assume a single clock without the current text) |\n"
            "| Finalisation of provisional assessment | Date of adjustment of tax after "
            "the final assessment |\n"
            "| Refund arising from judgment / decree / order / appeal | Date of "
            "communication of such judgment / decree / order |\n\n"
            "Treat the table as a **navigation aid** to the Explanation — confirm the "
            "exact clause that applies to the claim type and period.\n\n"
            "**Authorities Retrieved**\n\n"
            "**Statute**\n"
            "- Central Goods and Services Tax Act, 2017 — Section 54 (including "
            "Section 54(1) limitation and the Explanation defining relevant date)\n\n"
            "**Rules**\n"
            "- Central Goods and Services Tax Rules, 2017 — refund procedure "
            "(including Rule 89 family for applications / documentation; verify the "
            "current rule text for the claim period)\n\n"
            "**Circulars**\n"
            "- None retrieved from the current corpus for this offline package.\n\n"
            f"{judgments_block}\n\n"
            "**Risk areas**\n"
            "- Wrong determination of the relevant date\n"
            "- Incorrect refund category mapping\n"
            "- Incomplete supporting documentation\n"
            "- Mismatch with GST returns / tax payment trails\n"
            "- Failure to comply with Rule 89 procedural requirements\n"
            "- Delayed filing attributed to portal / form defects without checking "
            "carve-outs and current circulars\n\n"
            "**Practical note**\n"
            "- Compute limitation only after locking the refund category and the "
            "matching Explanation clause.\n"
            "- Confirm returns / tax payment trails that support the claim are on "
            "record before counting the two-year window as closed.\n"
            "- Portal / form defects and notification carve-outs can affect "
            "eligibility and process even when limitation appears open — verify "
            "current CGST Rules and CBIC guidance for the claim period.\n"
            "- Electronic cash-ledger refund situations and any special exclusion "
            "periods (if claimed) must be checked against current circulars / "
            "orders; this package does not invent those authorities.\n\n"
            "**Recommended next steps**\n"
            "1. Identify the exact refund category for the client's claim.\n"
            "2. Determine the applicable Explanation clause to Section 54.\n"
            "3. Compute the two-year limitation from that relevant date.\n"
            "4. Verify Rule 89 form / documentary compliance for the claim period.\n"
            "5. Review any retrieved CBIC circulars / notifications for that period "
            "(none are included in this offline package).\n"
            "6. Only then prepare or review the refund application.\n\n"
            "**Related provisions (secondary)**\n"
            "- **Section 54(3)** — refund of unutilised input tax credit (ITC) in "
            "specified cases (including inverted duty structure), subject to "
            "conditions and notifications.\n"
            "- **Section 54(5)** / **Section 54(8)** — unjust enrichment: where the "
            "incidence of tax has been passed on, refund is generally not paid to "
            "the applicant and may be credited to the Consumer Welfare Fund; "
            "Section 54(8) lists situations where refund may still be paid to the "
            "applicant (verify current text).\n"
            "- **Section 54(6)** — provisional refund in eligible zero-rated "
            "supply cases, subject to conditions.\n"
            "- Interest / withholding — related statutory and rule provisions "
            "govern delayed refunds and withholding situations.\n\n"
            "**Limitations:** Exact eligibility, documentary checklist, notification "
            "carve-outs, and portal procedure must be verified against the current "
            "CGST Act, CGST Rules, and circulars for the claim period."
        )
        now = _now_utc().isoformat()
        return {
            "response": response + _CLOSING_DISCLAIMER,
            "citations": [
                {
                    "title": "Central Goods and Services Tax Act, 2017 - Section 54",
                    "source": "India Code / Central Act",
                    "source_type": "statute",
                    "snippet": (
                        "Section 54(1): refund application ordinarily within two years "
                        "from the relevant date. Explanation to Section 54 defines "
                        "relevant date by claim category; confirm the exact clause "
                        "for Section 54(3) and other classes from the current text."
                    ),
                    "legal_metadata": {
                        "jurisdiction": "India (Central)",
                        "act": "Central Goods and Services Tax Act, 2017",
                        "section": "54",
                        "citation": "CGST Act s.54",
                    },
                    "retrieved_at": now,
                    "source_date": "2017-07-01",
                    "staleness_status": "possibly_stale",
                },
                {
                    "title": "CGST Act, 2017 - Section 54(1) and Explanation (relevant date)",
                    "source": "India Code / Central Act",
                    "source_type": "statute",
                    "snippet": (
                        "Two-year limitation from relevant date; Explanation maps "
                        "refund situations to the applicable relevant date."
                    ),
                    "legal_metadata": {
                        "jurisdiction": "India (Central)",
                        "act": "Central Goods and Services Tax Act, 2017",
                        "section": "54",
                        "citation": "CGST Act s.54(1) / Explanation",
                    },
                    "retrieved_at": now,
                    "source_date": "2017-07-01",
                    "staleness_status": "possibly_stale",
                },
                {
                    "title": "CGST Rules, 2017 - Rule 89 (refund application)",
                    "source": "CGST Rules",
                    "source_type": "rule",
                    "snippet": (
                        "Prescribed manner, form, and documentary process for GST "
                        "refund applications under the CGST Rules (Rule 89 family)."
                    ),
                    "legal_metadata": {
                        "jurisdiction": "India (Central)",
                        "act": "Central Goods and Services Tax Rules, 2017",
                        "section": "89",
                        "citation": "CGST Rules r.89",
                    },
                    "retrieved_at": now,
                    "source_date": "2017-07-01",
                    "staleness_status": "possibly_stale",
                },
                {
                    "title": "CGST Act, 2017 - Section 54(3)",
                    "source": "India Code / Central Act",
                    "source_type": "statute",
                    "snippet": "Refund of unutilised ITC including inverted duty structure cases, subject to conditions.",
                    "legal_metadata": {
                        "jurisdiction": "India (Central)",
                        "act": "Central Goods and Services Tax Act, 2017",
                        "section": "54(3)",
                        "citation": "CGST Act s.54(3)",
                    },
                    "retrieved_at": now,
                    "source_date": "2017-07-01",
                    "staleness_status": "possibly_stale",
                },
                {
                    "title": "CGST Act, 2017 - Section 54(5)/(6)/(8)",
                    "source": "India Code / Central Act",
                    "source_type": "statute",
                    "snippet": (
                        "Unjust enrichment: where tax incidence has been passed on, "
                        "refund is generally not paid to the applicant; Section 54(8) "
                        "lists situations where refund may be paid to the applicant; "
                        "provisional refund for eligible zero-rated supplies under "
                        "Section 54(6)."
                    ),
                    "legal_metadata": {
                        "jurisdiction": "India (Central)",
                        "act": "Central Goods and Services Tax Act, 2017",
                        "section": "54(5)/(6)/(8)",
                        "citation": "CGST Act s.54(5)/(6)/(8)",
                    },
                    "retrieved_at": now,
                    "source_date": "2017-07-01",
                    "staleness_status": "possibly_stale",
                },
            ],
            "strategy": "offline_cgst_section_54_refund_fallback",
            "note": (
                "Authorized Stage 2 GST Section 54 senior-counsel package "
                "(executive view, relevant-date table, risk areas, next steps). "
                "No invented judgments or circular numbers."
            ),
            "dropped_citation_count": 0,
        }

    # Stage 2 Income-tax Act — Section 139 return-of-income family.
    if (
        ("section 139" in q or "s.139" in q or "s 139" in q or "return of income" in q)
        and (
            "income tax" in q
            or "income-tax" in q
            or "it act" in q
            or "section 139" in q
            or "belated return" in q
            or "revised return" in q
        )
    ):
        response = (
            "**Return of Income Under the Income-tax Act, 1961 — Section 139 Family**\n\n"
            "**Core provision:** Section 139 of the Income-tax Act, 1961 governs filing of "
            "return of income.\n\n"
            "**Key rules (verify current Finance Act amendments before advising):**\n"
            "1. **Who must file:** Section **139(1)** requires specified persons to furnish a "
            "return of income for the previous year on or before the due date.\n"
            "2. **Belated return:** Section **139(4)** permits a belated return within the "
            "prescribed window after the end of the relevant assessment year (subject to "
            "current statutory cut-off).\n"
            "3. **Revised return:** Section **139(5)** permits revision of a return already "
            "furnished, within the prescribed time, on discovering omission or wrong statement.\n"
            "4. **Updated return:** Later amendments introduced an updated-return mechanism "
            "(verify the current Section **139(8A)** / related provisions for the relevant year).\n"
            "5. **Defective return:** Section **139(9)** addresses defective returns and the "
            "opportunity to rectify defects.\n\n"
            "**Limitations:** Due dates, forms, e-filing mandates, and Finance Act changes "
            "vary by assessment year. Confirm the year-specific position before client advice."
        )
        return {
            "response": response + _CLOSING_DISCLAIMER,
            "citations": [
                {
                    "title": "Income-tax Act, 1961 - Section 139",
                    "source": "India Code / Central Act",
                    "source_type": "statute",
                    "snippet": "Return of income — who must file and related filing duties.",
                    "legal_metadata": {
                        "jurisdiction": "India (Central)",
                        "act": "Income-tax Act, 1961",
                        "section": "139",
                        "citation": "IT Act s.139",
                    },
                    "retrieved_at": _now_utc().isoformat(),
                    "source_date": "1962-04-01",
                    "staleness_status": "possibly_stale",
                },
                {
                    "title": "Income-tax Act, 1961 - Section 139(4)/(5)",
                    "source": "India Code / Central Act",
                    "source_type": "statute",
                    "snippet": "Belated and revised returns within prescribed statutory windows.",
                    "legal_metadata": {
                        "jurisdiction": "India (Central)",
                        "act": "Income-tax Act, 1961",
                        "section": "139(4)/(5)",
                        "citation": "IT Act s.139(4)/(5)",
                    },
                    "retrieved_at": _now_utc().isoformat(),
                    "source_date": "1962-04-01",
                    "staleness_status": "possibly_stale",
                },
                {
                    "title": "Income-tax Act, 1961 - Section 139(9)",
                    "source": "India Code / Central Act",
                    "source_type": "statute",
                    "snippet": "Defective return and rectification opportunity.",
                    "legal_metadata": {
                        "jurisdiction": "India (Central)",
                        "act": "Income-tax Act, 1961",
                        "section": "139(9)",
                        "citation": "IT Act s.139(9)",
                    },
                    "retrieved_at": _now_utc().isoformat(),
                    "source_date": "1962-04-01",
                    "staleness_status": "possibly_stale",
                },
            ],
            "strategy": "offline_it_section_139_return_fallback",
            "note": "Authorized Stage 2 Income-tax Section 139 family offline fallback; verify current Finance Act.",
            "dropped_citation_count": 0,
        }

    if (
        ("25" in q or "twenty five" in q or "twenty-five" in q)
        and ("act" in q or "acts" in q or "law" in q or "laws" in q)
        and ("india" in q or "indian" in q)
    ):
        response = (
            "**25 Important Indian Acts**\n\n"
            "**Core and procedural laws**\n"
            "1. Constitution of India\n"
            "2. Bharatiya Nyaya Sanhita, 2023\n"
            "3. Bharatiya Nagarik Suraksha Sanhita, 2023\n"
            "4. Bharatiya Sakshya Adhiniyam, 2023\n"
            "5. Code of Civil Procedure, 1908\n\n"
            "**Business, corporate and commercial laws**\n"
            "6. Companies Act, 2013\n"
            "7. Limited Liability Partnership Act, 2008\n"
            "8. Indian Contract Act, 1872\n"
            "9. Sale of Goods Act, 1930\n"
            "10. Insolvency and Bankruptcy Code, 2016\n\n"
            "**Taxation laws**\n"
            "11. Income-tax Act, 1961\n"
            "12. Central Goods and Services Tax Act, 2017\n"
            "13. Integrated Goods and Services Tax Act, 2017\n\n"
            "**Labour and employment laws**\n"
            "14. Employees' Provident Funds and Miscellaneous Provisions Act, 1952\n"
            "15. Payment of Gratuity Act, 1972\n"
            "16. Minimum Wages Act, 1948\n"
            "17. Industrial Disputes Act, 1947\n\n"
            "**Consumer, technology and data laws**\n"
            "18. Consumer Protection Act, 2019\n"
            "19. Information Technology Act, 2000\n"
            "20. Digital Personal Data Protection Act, 2023\n\n"
            "**Property and real estate laws**\n"
            "21. Transfer of Property Act, 1882\n"
            "22. Registration Act, 1908\n"
            "23. Real Estate (Regulation and Development) Act, 2016\n\n"
            "**Family and financial crime laws**\n"
            "24. Special Marriage Act, 1954\n"
            "25. Prevention of Money Laundering Act, 2002\n\n"
            "**Freshness note:** This is a deterministic LegalMitra reference list for "
            "the requested count. For production use, verify repealed/replaced "
            "criminal-law references and any recent amendments."
        )
        return {
            "response": response + _CLOSING_DISCLAIMER,
            "citations": [
                {
                    "title": "India Code - Central Acts",
                    "source": "Government of India",
                    "snippet": "Reference portal for central legislation.",
                    "retrieved_at": _now_utc().isoformat(),
                }
            ],
            "strategy": "deterministic_indian_acts_list",
            "note": "Returned deterministic list response for explicit Indian Acts count query.",
            "dropped_citation_count": 0,
        }

    if (
        ("divorce" in q or "dissolution" in q)
        and (
            "hindu marriage act" in q
            or "hma" in q
            or ("hindu" in q and "marriage" in q)
        )
    ):
        response = (
            "**Grounds for Divorce Under the Hindu Marriage Act, 1955**\n\n"
            "**Core provision:** Section 13 of the Hindu Marriage Act, 1955 "
            "sets out the principal grounds on which a Hindu marriage may be "
            "dissolved by a decree of divorce.\n\n"
            "**Common grounds under Section 13(1):**\n"
            "1. **Adultery:** voluntary sexual intercourse with a person other "
            "than the spouse after marriage.\n"
            "2. **Cruelty:** physical or mental cruelty making continued "
            "cohabitation unsafe or unreasonable.\n"
            "3. **Desertion:** abandonment for a continuous period of at least "
            "two years immediately before filing the petition.\n"
            "4. **Conversion:** ceasing to be Hindu by conversion to another "
            "religion.\n"
            "5. **Mental disorder:** incurable unsoundness of mind or a mental "
            "disorder of such kind and degree that the petitioner cannot "
            "reasonably be expected to live with the respondent.\n"
            "6. **Virulent and incurable leprosy:** statutory availability must "
            "be checked against current amendments before pleading.\n"
            "7. **Venereal disease in communicable form:** statutory availability "
            "must be checked against current amendments before pleading.\n"
            "8. **Renunciation:** renouncing the world by entering a religious "
            "order.\n"
            "9. **Presumption of death:** not heard of as being alive for seven "
            "years or more by persons who would naturally have heard of the spouse.\n\n"
            "**Additional grounds:** A wife may have additional grounds under "
            "Section 13(2), including situations involving the husband's earlier "
            "marriage, certain sexual offences, non-resumption of cohabitation "
            "after maintenance orders, and repudiation of marriage in specified "
            "circumstances. Divorce by mutual consent is separately available "
            "under Section 13B."
        )
        return {
            "response": response + _CLOSING_DISCLAIMER,
            "citations": [
                {
                    "title": "Hindu Marriage Act, 1955 - Section 13",
                    "source": "India Code / Central Act",
                    "snippet": "Divorce grounds under the Hindu Marriage Act, 1955.",
                    "retrieved_at": _now_utc().isoformat(),
                },
                {
                    "title": "Hindu Marriage Act, 1955 - Section 13B",
                    "source": "India Code / Central Act",
                    "snippet": "Divorce by mutual consent.",
                    "retrieved_at": _now_utc().isoformat(),
                },
            ],
            "strategy": "offline_hindu_marriage_divorce_fallback",
            "note": "Gemini unavailable; returned narrow offline fallback with source caveats.",
            "dropped_citation_count": 0,
        }

    if (
        ("section 138" in q or "cheque bounce" in q or "check bounce" in q)
        and ("limitation" in q or "timeline" in q or "filing" in q or "complaint" in q)
        and ("ni act" in q or "negotiable instruments" in q or "cheque" in q or "check" in q)
    ):
        response = (
            "**Limitation Timeline for a Cheque Bounce Complaint Under Section 138 NI Act**\n\n"
            "**Core provision:** Section 138 read with Section 142(b) of the "
            "Negotiable Instruments Act, 1881.\n\n"
            "**Timeline:**\n"
            "1. **Present the cheque:** within 3 months from the cheque date or "
            "within its validity period, whichever is earlier.\n"
            "2. **Send demand notice:** within 30 days from receiving bank "
            "intimation that the cheque was dishonoured.\n"
            "3. **Wait for payment:** the drawer gets 15 days from receipt of the "
            "demand notice to pay.\n"
            "4. **Cause of action:** arises after the 15-day payment period expires "
            "without payment.\n"
            "5. **File complaint:** within 1 month from the date the cause of "
            "action arises, under Section 142(b).\n\n"
            "**Delay:** The court may take cognizance after the prescribed period "
            "if the complainant shows sufficient cause for delay under the proviso "
            "to Section 142(b).\n\n"
            "**Key authority:** *Econ Antri Ltd. v. Rom Industries Ltd.*, "
            "(2014) 11 SCC 769, on computation of the Section 138/142 timeline."
        )
        return {
            "response": response + _CLOSING_DISCLAIMER,
            "citations": [
                {
                    "title": "Negotiable Instruments Act, 1881 - Section 138",
                    "source": "India Code / Central Act",
                    "snippet": "Cheque dishonour ingredients and statutory notice/payment periods.",
                    "retrieved_at": _now_utc().isoformat(),
                },
                {
                    "title": "Negotiable Instruments Act, 1881 - Section 142(b)",
                    "source": "India Code / Central Act",
                    "snippet": "Complaint within one month from cause of action, with delay condonation proviso.",
                    "retrieved_at": _now_utc().isoformat(),
                },
                {
                    "title": "Econ Antri Ltd. v. Rom Industries Ltd.",
                    "source": "Supreme Court of India",
                    "snippet": "Computation of limitation under Sections 138(c) and 142(b) of the NI Act.",
                    "date": "2014",
                    "retrieved_at": _now_utc().isoformat(),
                },
            ],
            "strategy": "offline_ni_act_138_limitation_fallback",
            "note": "Gemini unavailable; returned narrow offline fallback with source caveats.",
            "dropped_citation_count": 0,
        }

    if (
        ("section 244" in q or "244 companies" in q)
        and ("companies act" in q or "company" in q)
        and (
            "oppression" in q
            or "mismanagement" in q
            or "who can file" in q
            or "eligibility" in q
            or "petition" in q
            or "waiver" in q
        )
    ):
        response = (
            "**Provision / Concept:** Section 244, Companies Act, 2013\n"
            "**Core Rule:** Section 244 specifies who is eligible to apply to the "
            "National Company Law Tribunal (NCLT) for relief against oppression and "
            "mismanagement under Section 241.\n"
            "**Ingredients / Tests:**\n"
            "* **Company having share capital:**\n"
            "  * Not less than 100 members of the company, or not less than one-tenth "
            "of the total number of members, whichever is less; or\n"
            "  * Any member or members holding not less than one-tenth of the issued "
            "share capital, provided all calls and other sums due on their shares "
            "have been paid.\n"
            "* **Company not having share capital:**\n"
            "  * Not less than one-fifth of the total number of its members.\n"
            "* **Waiver:** The NCLT may waive all or any of the Section 244(1) "
            "requirements to enable members to apply under Section 241.\n"
            "**Key Exception:** The Tribunal's waiver power under the proviso to "
            "Section 244(1).\n"
            "**Limitation / Timeline:** Not applicable to filing eligibility.\n"
            "**Key SC Cases:**\n"
            "* *Cyrus Investments Pvt. Ltd. v. Tata Sons Ltd.*, (2017) 1 SCC 777 "
            "- recognised the discretionary waiver route under the proviso to "
            "Section 244(1), to be considered on the facts of the case.\n"
            "* *V.S. Krishnan v. M.S. Krishnan*, (2020) 14 SCC 1 - waiver under "
            "Section 244 is a preliminary issue and must be considered before the "
            "main oppression and mismanagement petition proceeds.\n"
            "**Legal Position:** Settled Law on eligibility thresholds and the "
            "Tribunal's power to waive them."
        )
        return {
            "response": response + _CLOSING_DISCLAIMER,
            "citations": [
                {
                    "title": "Companies Act, 2013 - Section 244",
                    "source": "India Code / Central Act",
                    "snippet": "Right to apply under Section 241 and waiver by the Tribunal.",
                    "retrieved_at": _now_utc().isoformat(),
                },
                {
                    "title": "Cyrus Investments Pvt. Ltd. v. Tata Sons Ltd.",
                    "source": "Supreme Court of India",
                    "snippet": "Waiver under the proviso to Section 244(1).",
                    "date": "2017",
                    "retrieved_at": _now_utc().isoformat(),
                },
                {
                    "title": "V.S. Krishnan v. M.S. Krishnan",
                    "source": "Supreme Court of India",
                    "snippet": "Section 244 waiver as a preliminary issue.",
                    "date": "2020",
                    "retrieved_at": _now_utc().isoformat(),
                },
            ],
            "strategy": "offline_companies_act_244_eligibility_fallback",
            "note": "Gemini unavailable; returned narrow offline fallback with source caveats.",
            "dropped_citation_count": 0,
        }

    if not (
        "quash" in q
        and "fir" in q
        and ("bnss" in q or "bharatiya nagarik suraksha sanhita" in q)
    ):
        return None

    response = (
        "**FIR Quashing Under BNSS - Practical Procedure**\n\n"
        "**Core route:** Move the jurisdictional High Court under **Section 528, "
        "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)**, which preserves the "
        "High Court's inherent powers to prevent abuse of process and secure the "
        "ends of justice. In suitable cases, Article 226 of the Constitution may "
        "also be invoked, especially where the challenge is to illegal or arbitrary "
        "State action.\n\n"
        "**Procedure checklist:**\n"
        "1. Collect the FIR, complaint, notice/summons if any, settlement documents "
        "if applicable, and all documents showing why the allegations are legally "
        "untenable.\n"
        "2. Prepare a criminal petition under BNSS Section 528 before the High Court "
        "with a prayer to quash the FIR and consequential proceedings/investigation.\n"
        "3. Plead the quashing grounds precisely: no offence made out even if the "
        "FIR is accepted at face value, proceedings are mala fide, civil/commercial "
        "dispute is given criminal colour, legal bar to prosecution, or continuation "
        "would be abuse of process.\n"
        "4. Add parties normally including the State/investigating agency and the "
        "informant/complainant. Serve advance copies as required by local High Court "
        "rules.\n"
        "5. Seek interim protection only where justified, such as no coercive steps "
        "or stay of further proceedings. Courts are cautious at the investigation "
        "stage, so the petition must show an exceptional case.\n"
        "6. At hearing, avoid disputed facts and argue from the FIR, admitted "
        "documents, statutory ingredients, and binding quashing principles.\n\n"
        "**Key authorities to verify before filing:**\n"
        "- **BNSS, 2023, Section 528**: inherent powers of High Court.\n"
        "- **State of Haryana v. Bhajan Lal**, 1992 Supp (1) SCC 335: illustrative "
        "categories for quashing criminal proceedings.\n"
        "- **Gian Singh v. State of Punjab**, (2012) 10 SCC 303 and **Narinder "
        "Singh v. State of Punjab**, (2014) 6 SCC 466: quashing on settlement, "
        "subject to offence nature and public interest.\n"
        "- **Neeharika Infrastructure v. State of Maharashtra**, (2021) 19 SCC 401: "
        "High Courts should be cautious in interfering with investigation.\n\n"
        "**Drafting note:** Lead with the exact FIR allegations and map them against "
        "the statutory ingredients of the alleged BNS/other offences. If any ingredient "
        "is missing on the face of the FIR, make that the first ground.\n\n"
        "**Freshness note:** This is an offline fallback because the AI provider did "
        "not return a response. Verify current High Court rules, recent Supreme Court "
        "and local High Court decisions, and any post-2023 BNSS amendments before filing."
    )

    citations = [
        {
            "title": "Bharatiya Nagarik Suraksha Sanhita, 2023 - Section 528",
            "source": "BNSS 2023",
            "snippet": "Saving of inherent powers of High Court.",
            "retrieved_at": _now_utc().isoformat(),
        },
        {
            "title": "State of Haryana v. Bhajan Lal",
            "source": "Supreme Court of India",
            "snippet": "Illustrative categories for quashing criminal proceedings.",
            "date": "1992",
            "retrieved_at": _now_utc().isoformat(),
        },
        {
            "title": "Neeharika Infrastructure v. State of Maharashtra",
            "source": "Supreme Court of India",
            "snippet": "Caution against routine interference with criminal investigation.",
            "date": "2021",
            "retrieved_at": _now_utc().isoformat(),
        },
    ]

    return {
        "response": response + _CLOSING_DISCLAIMER,
        "citations": citations,
        "strategy": "offline_bnss_fir_quashing_fallback",
        "note": "Gemini unavailable; returned narrow offline fallback with source caveats.",
        "dropped_citation_count": 0,
    }


