import asyncio
from datetime import datetime, timezone
from uuid import uuid4
import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.db.mongo import init_mongo, get_collection, close_mongo

BLOG_COLLECTION = "legal_blog_posts"
APP_KEY = "legalmitra"

DPDP_ARTICLE = {
    "title": "Navigating the DPDP Act 2023: A Comprehensive Compliance Guide for Indian Enterprises",
    "slug": "dpdp-act-2023-compliance-guide",
    "summary": "An in-depth analysis of the Digital Personal Data Protection Act 2023, its impact on business operations, and a step-by-step roadmap for legal compliance in India.",
    "author": "LegalMitra Editorial Team",
    "image_url": "https://images.unsplash.com/photo-1507925921958-8a62f3d1a50d",
    "tags": ["Data Protection", "Privacy", "Compliance", "DPDP Act"],
    "is_published": True,
    "content": """# Navigating the DPDP Act 2023: A Comprehensive Compliance Guide for Indian Enterprises

## Introduction

The Digital Personal Data Protection (DPDP) Act, 2023, represents a watershed moment in India's legal landscape. For businesses operating in India, this isn't just another regulation—it's a fundamental shift in how digital personal data must be handled, stored, and protected.

---

## 💡 Why This Matters for SaaS Founders and Startups

If you are building a platform like **LegalMitra**, **InvestMitra**, or any AI-driven SaaS, the DPDP Act is now a core part of your technical infrastructure. It is no longer just a legal "extra"—it is a requirement for growth, trust, and avoiding massive penalties.

### Compliance is your Competitive Advantage
In the new digital economy, users will flock to platforms that respect their privacy. By being DPDP-ready on Day 1, you aren't just following the law; you are building a brand that customers can trust with their most sensitive information.

---

## 1. The Core Philosophy: Consent and Purpose Limitation

At the heart of the DPDP Act lies the principle of 'Notice and Consent'. Unlike the previous 'tick-the-box' approach, the Act mandates that consent must be:
- **Free and Specific**: Linked to the specific purpose.
- **Informed**: Provided in simple, accessible language.
- **Clear Affirmative Action**: No more pre-ticked boxes.

---

## 2. Key Obligations of Data Fiduciaries

Enterprises must now adhere to several statutory obligations:
- **Accuracy and Completeness**: Ensuring data is correct when used for decisions.
- **Storage Limitation**: Data should not be stored longer than necessary.
- **Security Safeguards**: Implementing 'reasonable security' (encryption, access controls).
- **Breach Notification**: You must notify the Data Protection Board and affected users of any breach.

---

## ✅ The DPDP Compliance Checklist for Businesses

Use this checklist to gauge your current readiness:
- [ ] **Data Discovery**: Do you know exactly where all your user data is stored?
- [ ] **Privacy Notice**: Is your notice available in simple language (and regional languages if needed)?
- [ ] **Consent Logs**: Do you have a technical log of when and how every user gave consent?
- [ ] **Deletion Mechanism**: Can a user delete their data with a single click?
- [ ] **DPO Appointed**: Have you designated a point of contact for data queries?

---

## ❓ Frequently Asked Questions (FAQs)

**Q: Does the DPDP Act apply to small startups?**
A: Yes. The Act applies to all Data Fiduciaries processing digital personal data within India, regardless of the company size.

**Q: What are the penalties for non-compliance?**
A: Penalties can go as high as ₹250 Crores for failing to implement security safeguards.

**Q: Can a user withdraw consent at any time?**
A: Yes, the Act grants Data Principals the right to withdraw consent easily, and the Fiduciary must stop processing that data immediately.

---

## 🚀 Take Action with LegalMitra

Don't let compliance slow down your innovation. **LegalMitra** is designed to help you navigate these complex laws instantly.

- **Generate DPDP-Compliant Notices**: Draft professional legal notices and privacy policies in seconds.
- **Research Case Precedents**: Search for Supreme Court rulings on privacy and data rights.
- **Check Your Compliance**: Use our AI-powered Compliance Checker to identify gaps in your current setup.

**[Try the LegalMitra Assistant Now →](index.html)**

---

## Sources and Verification

1. **Official Gazette of India**: [The Digital Personal Data Protection Act, 2023](https://www.meity.gov.in/writereaddata/files/The%20Digital%20Personal%20Data%20Protection%20Act%202023.pdf)
2. **MeitY Notifications**: [Official MeitY Website](https://www.meity.gov.in/)

*Disclaimer: This article is for informational purposes only and does not constitute legal advice. Please consult with a qualified legal professional for specific compliance requirements for your organization.*
ation.*
"""
}

async def seed_blog():
    await init_mongo()
    collection = get_collection(BLOG_COLLECTION)
    
    # 1. Remove the old short article if it exists
    await collection.delete_many({"app_key": APP_KEY, "slug": DPDP_ARTICLE["slug"]})
    
    # 2. Insert the new professional article
    now = datetime.now(timezone.utc)
    post = DPDP_ARTICLE.copy()
    post["id"] = str(uuid4())
    post["app_key"] = APP_KEY
    post["created_at"] = now
    post["updated_at"] = now
    post["published_at"] = now
    
    await collection.insert_one(post)
    print(f"Successfully seeded professional article: {post['title']}")
    
    await close_mongo()

if __name__ == "__main__":
    asyncio.run(seed_blog())
