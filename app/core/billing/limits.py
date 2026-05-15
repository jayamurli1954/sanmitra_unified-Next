from typing import Dict, Any

# Tier Names
FREE = "free"
BASIC = "basic"
GROWTH = "growth"
PRO = "pro"
POPULAR = "popular" # Alias for Pro

TIER_LIMITS = {
    FREE: {
        "daily_research_queries": 5,
        "monthly_templates": 5,
        "max_compliance_records": 10,
        "tools_access": ["gst_finder", "limitation_calc"],
        "ai_model": "gemini-1.5-flash",
        "can_upload_official_forms": False,
    },
    BASIC: {
        "daily_research_queries": 50,
        "monthly_templates": 30,
        "max_compliance_records": 100,
        "tools_access": "all",
        "ai_model": "gemini-1.5-pro",
        "can_upload_official_forms": False,
    },
    GROWTH: {
        "daily_research_queries": 50,
        "monthly_templates": 30,
        "max_compliance_records": 100,
        "tools_access": "all",
        "ai_model": "gemini-1.5-pro",
        "can_upload_official_forms": False,
    },
    PRO: {
        "daily_research_queries": None,
        "monthly_templates": 200,
        "max_compliance_records": None,
        "tools_access": "all",
        "ai_model": "gemini-1.5-pro",
        "can_upload_official_forms": True,
    },
    POPULAR: {
        "daily_research_queries": None,
        "monthly_templates": 200,
        "max_compliance_records": None,
        "tools_access": "all",
        "ai_model": "gemini-1.5-pro",
        "can_upload_official_forms": True,
    }
}

def get_tier_limits(tier: str) -> Dict[str, Any]:
    return TIER_LIMITS.get(tier.lower(), TIER_LIMITS[FREE])
