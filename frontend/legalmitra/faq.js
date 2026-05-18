const faqs = [
  {
    category: "getting-started",
    q: "What is LegalMitra?",
    a: "LegalMitra is an AI-powered legal research and drafting platform built for Indian lawyers, CAs, compliance professionals, and law students. It provides instant access to Indian case law, statutes, legal templates, and compliance tracking tools.",
  },
  {
    category: "getting-started",
    q: "Who should use LegalMitra?",
    a: "Lawyers, Chartered Accountants, compliance officers, legal consultants, boutique law firms, corporate legal teams, solo practitioners, and law students studying the Indian legal system.",
  },
  {
    category: "getting-started",
    q: "How do I get started?",
    a: "Sign up free with email. No credit card required. You get instant access to launch-stage LegalMitra features, including basic research, selected templates, and compliance workflow testing.",
  },
  {
    category: "getting-started",
    q: "Is LegalMitra available on mobile?",
    a: "Yes, the responsive web experience works on phones, tablets, and desktops.",
  },
  {
    category: "getting-started",
    q: "Do I need special training to use LegalMitra?",
    a: "No. The interface is designed for lawyers and legal professionals. Most users can start with search, templates, and workflow tools without technical training.",
  },
  {
    category: "getting-started",
    q: "Is there a free trial?",
    a: "Yes. LegalMitra is currently open for 15 days of free launch access while payment gateway integration is completed. No credit card or payment is required during this window.",
  },
  {
    category: "getting-started",
    q: "What's included in each pricing tier?",
    a: "<p><strong>Starter:</strong> 5 AI research queries per day, 5 templates per month, 10 compliance tracker records, GST Rate Finder, and Limitation Calculator.</p><p><strong>Growth:</strong> 50 AI research queries per day, 30 templates per month, 100 compliance tracker records, all Legal Tools, and response save/share/download.</p><p><strong>Professional:</strong> Unlimited AI research, 200 templates per month, unlimited compliance tracker records, official PDF form auto-fill, and priority workflow capacity.</p>",
  },
  {
    category: "getting-started",
    q: "Can I cancel anytime?",
    a: "Yes. Once paid billing is enabled, cancellation and renewal terms should be shown clearly before payment. During local E2E testing, plan prompts are used to verify feature limits before payment collection is enabled.",
  },
  {
    category: "features",
    q: "How accurate is the AI research?",
    a: "<p>LegalMitra is designed to use authentic legal sources, including Supreme Court and High Court material, statutes, official notifications, and verified legal references where available.</p><p><strong>Important:</strong> AI can make mistakes. Always verify citations, amendments, and current legal position before filing, advising a client, or taking final legal action.</p>",
  },
  {
    category: "features",
    q: "Can I rely on LegalMitra research in court?",
    a: "LegalMitra is a research assistant, not a substitute for qualified legal advice. Always verify citations, check for amendments, and review latest judgments before filing.",
  },
  {
    category: "features",
    q: "How does the AI learn Indian law?",
    a: "<p>LegalMitra is structured around Indian legal material, including:</p><ul><li>Indian Constitution and statutes</li><li>Supreme Court and High Court judgments</li><li>BNS, BNSS, and BSA transition material</li><li>IPC, CrPC, and Evidence Act precedents</li><li>Regulatory notifications for GST, labour, and corporate law</li></ul>",
  },
  {
    category: "features",
    q: "Can I search old case law?",
    a: "Yes. Landmark and older cases are useful for historical context and precedent research. Users should still verify citation status and whether a judgment has been overruled, distinguished, or modified.",
  },
  {
    category: "features",
    q: "Does it cover all Indian states?",
    a: "The target coverage includes Supreme Court, High Courts, tribunals, and state-specific rules for GST, labour, and corporate compliance workflows where available.",
  },
  {
    category: "features",
    q: "Can I export research results?",
    a: "Yes. Export and sharing workflows are planned for PDF, document, and copy-ready formats so research can move into pleadings, notes, and client workflows after review.",
  },
  {
    category: "features",
    q: "What templates are available?",
    a: "<p>LegalMitra is moving from a broad placeholder template library to fewer, stronger, clause-driven professional documents. Template areas include:</p><ul><li>Professional Consultancy Agreement</li><li>Software Development Agreement</li><li>Non-Disclosure Agreement</li><li>Employment Agreement</li><li>Website Terms and Privacy Policy bundle</li><li>GST, corporate, criminal, civil, and compliance documents</li></ul>",
  },
  {
    category: "features",
    q: "Can I customize templates?",
    a: "Yes. Templates are intended to be editable through guided inputs such as party details, dates, jurisdiction, fees, scope, and business-specific clauses.",
  },
  {
    category: "features",
    q: "What is Compliance Tracker?",
    a: "<p>The Professional Compliance Tracker helps advocates, Chartered Accountants, company secretaries, consultants, and legal teams manage:</p><ul><li>Court dates and hearings</li><li>Filing deadlines</li><li>Client follow-ups</li><li>Compliance due dates</li><li>Fee and receivable records</li></ul>",
  },
  {
    category: "features",
    q: "Can I share research with clients?",
    a: "Team sharing is planned for the Growth and Professional tiers. During the temporary free-access period, availability may be limited while billing and account controls are finalized.",
  },
  {
    category: "features",
    q: "Does it work offline?",
    a: "Research requires internet access because the system is cloud-based. Downloaded research and exported documents can be reviewed offline.",
  },
  {
    category: "features",
    q: "How often is the database updated?",
    a: "The target operating model is frequent updates for statutes, judgments, notifications, and legal-source indexes. Users should still verify current law before final reliance.",
  },
  {
    category: "pricing",
    q: "Are paid plans active right now?",
    a: "<p>Feature limits are active for E2E clarity even if payment collection is still being finalized. Starter, Growth, and Professional should behave differently so users understand when an upgrade is required.</p>",
  },
  {
    category: "pricing",
    q: "Can I share one account with my team?",
    a: "Starter is intended for individual/light use. Growth is suitable for active professional use. Professional is the correct tier for higher-capacity professional office workflows and future team controls.",
  },
  {
    category: "pricing",
    q: "What's the difference between monthly and yearly billing?",
    a: "Monthly and yearly billing are commercial billing choices. The feature limits remain plan-based: Starter is limited, Growth expands daily/monthly capacity, and Professional unlocks full workflow capacity.",
  },
  {
    category: "pricing",
    q: "Can I upgrade or downgrade mid-month?",
    a: "The product should prompt upgrade immediately when a user clicks a restricted feature. Downgrade behavior should preserve existing records but restrict new usage above the lower plan limit.",
  },
  {
    category: "pricing",
    q: "What payment methods do you accept?",
    a: "Payment collection may remain disabled during E2E testing. When enabled, LegalMitra should support common Indian payment methods through the configured payment gateway.",
  },
  {
    category: "pricing",
    q: "Do you offer corporate or firm discounts?",
    a: "Yes. Contact <strong>legalmitra@sanmitratech.in</strong> for bulk licensing and firm-level access discussions.",
  },
  {
    category: "pricing",
    q: "Is there a refund policy?",
    a: "Refund and cancellation terms should be published with paid plans before payment collection is enabled.",
  },
  {
    category: "legal-compliance",
    q: "Is LegalMitra DPDP compliant?",
    a: "LegalMitra is being prepared with DPDP-aware data handling, encryption, access control, and tenant confidentiality safeguards. Production readiness must be verified before processing sensitive legal documents.",
  },
  {
    category: "legal-compliance",
    q: "How do you protect my case data?",
    a: "The target security model includes HTTPS, tenant isolation, protected APIs, access control, audit discipline, and careful handling of confidential legal documents.",
  },
  {
    category: "legal-compliance",
    q: "Can lawyers maintain privilege with LegalMitra?",
    a: "LegalMitra must be used with professional judgment. Confidential client material should be processed only under proper tenant policy, user authorization, and human review controls.",
  },
  {
    category: "legal-compliance",
    q: "What's your policy on AI-generated content?",
    a: "LegalMitra output is AI-assisted research and drafting support. It should not be treated as final legal advice. Human verification is required before filing, advising, or relying on the output.",
  },
  {
    category: "legal-compliance",
    q: "Can I use LegalMitra for multiple clients?",
    a: "Yes. Professional use cases require client separation, matter-level records, role-based access, and clear retention controls.",
  },
  {
    category: "legal-compliance",
    q: "Do you have malpractice insurance?",
    a: "LegalMitra is a research and workflow tool, not a law firm. Professional users remain responsible for legal advice, filing decisions, and client outcomes.",
  },
  {
    category: "technical-support",
    q: "What if search doesn't find what I need?",
    a: "Try different keywords and procedural framing. For example, instead of only searching 'bail anticipatory', try 'anticipatory bail procedure under BNSS'. Contact <strong>legalmitra@sanmitratech.in</strong> if support is needed.",
  },
  {
    category: "technical-support",
    q: "How do I reset my password?",
    a: "Use the forgot-password flow on the login page when authentication is enabled for your environment.",
  },
  {
    category: "technical-support",
    q: "Can I delete my account?",
    a: "Account deletion and data-retention controls should be handled through account settings or support once production user management is enabled.",
  },
  {
    category: "technical-support",
    q: "What browsers does LegalMitra support?",
    a: "LegalMitra targets modern Chrome, Firefox, Safari, and Edge browsers. Internet Explorer is not supported.",
  },
  {
    category: "technical-support",
    q: "How do I contact support?",
    a: "Email <strong>legalmitra@sanmitratech.in</strong>. During launch testing, support workflows may be handled manually.",
  },
  {
    category: "technical-support",
    q: "Can I export my data?",
    a: "Data export is planned for research, templates, notes, and matter records subject to account permissions and tenant policy.",
  },
  {
    category: "research-accuracy",
    q: "How do you ensure citations are accurate?",
    a: "LegalMitra should cross-check citations against official or reliable sources such as court websites, India Code, statutory material, and verified legal databases where available.",
  },
  {
    category: "research-accuracy",
    q: "What if a judgment is overruled or amended?",
    a: "The target system should flag stale or uncertain legal material and show whether a case or provision may require further verification.",
  },
  {
    category: "research-accuracy",
    q: "Can I cite LegalMitra research directly in court?",
    a: "No. Cite the original legal source, such as the judgment report, statute, notification, or official document. LegalMitra is a research assistant, not the authority being cited.",
  },
  {
    category: "research-accuracy",
    q: "How do you handle conflicting judgments?",
    a: "LegalMitra should surface competing authorities, jurisdictional hierarchy, and practical notes so the user can decide which precedent applies after professional review.",
  },
  {
    category: "research-accuracy",
    q: "What if I find outdated information?",
    a: "Email <strong>legalmitra@sanmitratech.in</strong> with the issue and source details. The content can then be reviewed and corrected.",
  },
  {
    category: "research-accuracy",
    q: "How do you stay updated with new laws?",
    a: "The target update process monitors statutory sources, gazette notifications, court updates, and regulatory materials. Current legal position must still be verified before professional reliance.",
  },
];

const labels = {
  "getting-started": "Getting Started",
  features: "Features",
  pricing: "Pricing",
  "legal-compliance": "Legal & Compliance",
  "technical-support": "Technical Support",
  "research-accuracy": "Research & Accuracy",
};

let activeCategory = "getting-started";

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function stripHtml(value) {
  return String(value || "").replace(/<[^>]*>/g, " ");
}

function renderFaqs() {
  const query = document.getElementById("faq-search")?.value.trim().toLowerCase() || "";
  const target = document.getElementById("faq-results");
  if (!target) return;

  const filtered = faqs.filter((item) => {
    const matchesCategory = item.category === activeCategory;
    const searchable = `${item.q} ${stripHtml(item.a)} ${labels[item.category]}`.toLowerCase();
    const matchesQuery = !query || searchable.includes(query);
    return matchesCategory && matchesQuery;
  });

  target.innerHTML = filtered.length
    ? filtered.map((item, index) => `
      <details ${index === 0 ? "open" : ""}>
        <summary>Q: ${escapeHtml(item.q)}</summary>
        <div>${item.a}</div>
      </details>
    `).join("")
    : `<p class="legal-faq-empty">No FAQ matched this search in ${escapeHtml(labels[activeCategory])}.</p>`;
}

document.querySelectorAll("[data-faq-category]").forEach((button) => {
  button.addEventListener("click", () => {
    activeCategory = button.getAttribute("data-faq-category");
    document.querySelectorAll("[data-faq-category]").forEach((item) => {
      item.classList.toggle("active", item === button);
    });
    renderFaqs();
  });
});

document.getElementById("faq-search")?.addEventListener("input", renderFaqs);

renderFaqs();
