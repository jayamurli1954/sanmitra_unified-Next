from dataclasses import dataclass
from typing import Iterable, Literal


OrganizationType = Literal[
    "HOUSING",
    "TEMPLE",
    "BUSINESS",
    "PROFESSIONAL",
    "LEGAL",
    "INVESTMENT",
]

VALID_ORGANIZATION_TYPES: set[str] = {
    "HOUSING",
    "TEMPLE",
    "BUSINESS",
    "PROFESSIONAL",
    "LEGAL",
    "INVESTMENT",
}

APP_KEY_TO_ORG_TYPE: dict[str, str] = {
    "gruhamitra": "HOUSING",
    "mandirmitra": "TEMPLE",
    "mitrabooks": "BUSINESS",
    "legalmitra": "LEGAL",
    "investmitra": "INVESTMENT",
}

DEFAULT_MODULES_BY_ORG_TYPE: dict[str, tuple[str, ...]] = {
    "HOUSING": ("housing", "accounting", "audit"),
    "TEMPLE": ("temple", "accounting", "audit"),
    "BUSINESS": ("business", "accounting", "gst", "inventory", "audit"),
    "PROFESSIONAL": ("professional", "accounting", "billing", "audit"),
    "LEGAL": ("legal", "rag", "compliance", "audit"),
    "INVESTMENT": ("investment", "portfolio", "audit"),
}

MODULE_API_PREFIXES: dict[str, str] = {
    "accounting": "/api/v1/accounting",
    "audit": "/api/v1/audit",
    "housing": "/api/v1/housing",
    "temple": "/api/v1/temple",
    "business": "/api/v1/business",
    "professional": "/api/v1/professional",
    "gst": "/api/v1/accounting",
    "inventory": "/api/v1/inventory",
    "billing": "/api/v1/billing",
    "legal": "/api/v1/legal",
    "rag": "/api/v1/rag",
    "compliance": "/api/v1/legal",
    "investment": "/api/v1/investment",
    "portfolio": "/api/v1/investment",
    "investment_research": "/api/v1/investment/research",
    "broker_research": "/api/v1/investment/broker-research",
    "legal_ai": "/api/v1/legal/ai",
}

MODULE_FRONTEND_PATHS: dict[str, str] = {
    "accounting": "/accounting",
    "audit": "/audit",
    "housing": "/housing",
    "temple": "/temple",
    "business": "/business",
    "professional": "/professional",
    "gst": "/gst",
    "inventory": "/inventory",
    "billing": "/billing",
    "legal": "/legal",
    "rag": "/legal/research",
    "compliance": "/legal/compliance",
    "investment": "/investment",
    "portfolio": "/investment/portfolio",
    "investment_research": "/investment/research",
    "broker_research": "/investment/broker-research",
    "legal_ai": "/legal/assistant",
}

MODULE_NAV_GROUPS: dict[str, str] = {
    "accounting": "Finance",
    "audit": "Administration",
    "housing": "Operations",
    "temple": "Operations",
    "business": "Operations",
    "professional": "Operations",
    "gst": "Compliance",
    "inventory": "Operations",
    "billing": "Finance",
    "legal": "Legal",
    "rag": "Legal",
    "compliance": "Compliance",
    "investment": "Portfolio",
    "portfolio": "Portfolio",
    "investment_research": "Research",
    "broker_research": "Research",
    "legal_ai": "AI Assistant",
}

NAV_GROUP_ORDER: tuple[str, ...] = (
    "Operations",
    "Portfolio",
    "Finance",
    "Compliance",
    "Legal",
    "Research",
    "AI Assistant",
    "Administration",
)


@dataclass(frozen=True)
class ModuleDefinition:
    module_key: str
    display_name: str
    allowed_organization_types: frozenset[str]
    allowed_app_keys: frozenset[str]
    minimum_plan: str = "free"
    default_enabled: bool = True
    features: tuple[str, ...] = ()


MODULE_REGISTRY: dict[str, ModuleDefinition] = {
    "accounting": ModuleDefinition(
        module_key="accounting",
        display_name="MitraBooks Accounting Engine",
        allowed_organization_types=frozenset({"HOUSING", "TEMPLE", "BUSINESS", "PROFESSIONAL"}),
        allowed_app_keys=frozenset({"gruhamitra", "mandirmitra", "mitrabooks"}),
        features=("coa", "journal", "ledger", "reports"),
    ),
    "audit": ModuleDefinition(
        module_key="audit",
        display_name="Audit Log",
        allowed_organization_types=frozenset(VALID_ORGANIZATION_TYPES),
        allowed_app_keys=frozenset({"gruhamitra", "mandirmitra", "mitrabooks", "legalmitra", "investmitra"}),
        features=("audit_log",),
    ),
    "housing": ModuleDefinition(
        module_key="housing",
        display_name="GruhaMitra Housing Operations",
        allowed_organization_types=frozenset({"HOUSING"}),
        allowed_app_keys=frozenset({"gruhamitra", "mitrabooks"}),
        features=("flats", "residents", "maintenance", "complaints"),
    ),
    "temple": ModuleDefinition(
        module_key="temple",
        display_name="MandirMitra Temple Operations",
        allowed_organization_types=frozenset({"TEMPLE"}),
        allowed_app_keys=frozenset({"mandirmitra", "mitrabooks"}),
        features=("donations", "sevas", "hundi", "festivals"),
    ),
    "business": ModuleDefinition(
        module_key="business",
        display_name="MitraBooks Business Operations",
        allowed_organization_types=frozenset({"BUSINESS"}),
        allowed_app_keys=frozenset({"mitrabooks"}),
        features=("customers", "vendors", "invoices"),
    ),
    "professional": ModuleDefinition(
        module_key="professional",
        display_name="MitraBooks Professional Services",
        allowed_organization_types=frozenset({"PROFESSIONAL"}),
        allowed_app_keys=frozenset({"mitrabooks"}),
        features=("clients", "billing", "appointments"),
    ),
    "gst": ModuleDefinition(
        module_key="gst",
        display_name="GST Compliance",
        allowed_organization_types=frozenset({"BUSINESS"}),
        allowed_app_keys=frozenset({"mitrabooks"}),
        minimum_plan="pro",
        features=("gst_returns", "gst_reports"),
    ),
    "inventory": ModuleDefinition(
        module_key="inventory",
        display_name="Inventory",
        allowed_organization_types=frozenset({"BUSINESS"}),
        allowed_app_keys=frozenset({"mitrabooks"}),
        minimum_plan="pro",
        features=("stock_items", "stock_movements"),
    ),
    "billing": ModuleDefinition(
        module_key="billing",
        display_name="Billing",
        allowed_organization_types=frozenset({"PROFESSIONAL"}),
        allowed_app_keys=frozenset({"mitrabooks"}),
        features=("professional_billing",),
    ),
    "legal": ModuleDefinition(
        module_key="legal",
        display_name="LegalMitra Legal Workflow",
        allowed_organization_types=frozenset({"LEGAL"}),
        allowed_app_keys=frozenset({"legalmitra"}),
        features=("cases", "documents", "workflow"),
    ),
    "rag": ModuleDefinition(
        module_key="rag",
        display_name="Legal Research RAG",
        allowed_organization_types=frozenset({"LEGAL"}),
        allowed_app_keys=frozenset({"legalmitra"}),
        minimum_plan="pro",
        features=("legal_research", "citations"),
    ),
    "compliance": ModuleDefinition(
        module_key="compliance",
        display_name="Compliance Calendar",
        allowed_organization_types=frozenset({"LEGAL"}),
        allowed_app_keys=frozenset({"legalmitra"}),
        features=("deadlines", "reminders"),
    ),
    "investment": ModuleDefinition(
        module_key="investment",
        display_name="InvestMitra Portfolio",
        allowed_organization_types=frozenset({"INVESTMENT"}),
        allowed_app_keys=frozenset({"investmitra"}),
        features=("holdings", "asset_classes"),
    ),
    "portfolio": ModuleDefinition(
        module_key="portfolio",
        display_name="Portfolio Analytics",
        allowed_organization_types=frozenset({"INVESTMENT"}),
        allowed_app_keys=frozenset({"investmitra"}),
        features=("xirr", "pnl", "allocation"),
    ),
    "investment_research": ModuleDefinition(
        module_key="investment_research",
        display_name="InvestMitra Research Integrations",
        allowed_organization_types=frozenset({"INVESTMENT"}),
        allowed_app_keys=frozenset({"investmitra"}),
        minimum_plan="pro",
        default_enabled=False,
        features=("fincept_terminal", "research_reports"),
    ),
    "broker_research": ModuleDefinition(
        module_key="broker_research",
        display_name="Read-Only Broker Research Context",
        allowed_organization_types=frozenset({"INVESTMENT"}),
        allowed_app_keys=frozenset({"investmitra"}),
        minimum_plan="pro",
        default_enabled=False,
        features=("zerodha_kite_mcp_read_only",),
    ),
    "legal_ai": ModuleDefinition(
        module_key="legal_ai",
        display_name="Legal AI Assistant",
        allowed_organization_types=frozenset({"LEGAL"}),
        allowed_app_keys=frozenset({"legalmitra"}),
        minimum_plan="elite",
        default_enabled=False,
        features=("claude_for_legal",),
    ),
}


class ModuleAccessError(ValueError):
    pass


def normalize_organization_type(value: str | None, *, app_key: str | None = None) -> str:
    raw = str(value or "").strip().upper()
    aliases = {
        "GRUHAMITRA": "HOUSING",
        "GHARMITRA": "HOUSING",
        "MANDIRMITRA": "TEMPLE",
        "MITRABOOKS": "BUSINESS",
        "LEGALMITRA": "LEGAL",
        "INVESTMITRA": "INVESTMENT",
        "SOCIETY": "HOUSING",
        "TEMPLE_TRUST": "TEMPLE",
    }
    normalized = aliases.get(raw, raw)
    if normalized in VALID_ORGANIZATION_TYPES:
        return normalized

    app_based = APP_KEY_TO_ORG_TYPE.get(str(app_key or "").strip().lower())
    if app_based:
        return app_based

    return "BUSINESS"


def _normalize_modules(values: Iterable[str] | None) -> list[str]:
    seen: set[str] = set()
    modules: list[str] = []
    for value in values or ():
        key = str(value or "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            modules.append(key)
    return modules


def get_default_modules_for_org_type(organization_type: str | None) -> list[str]:
    normalized = normalize_organization_type(organization_type)
    return list(DEFAULT_MODULES_BY_ORG_TYPE[normalized])


def get_module_definition(module_key: str) -> ModuleDefinition | None:
    return MODULE_REGISTRY.get(str(module_key or "").strip().lower())


def derive_enabled_modules(
    *,
    organization_type: str | None,
    explicit_modules: Iterable[str] | None = None,
) -> list[str]:
    modules = _normalize_modules(explicit_modules)
    if modules:
        return modules
    return get_default_modules_for_org_type(organization_type)


def require_module_access(
    *,
    module_key: str,
    organization_type: str | None,
    enabled_modules: Iterable[str] | None,
    app_key: str | None,
) -> ModuleDefinition:
    key = str(module_key or "").strip().lower()
    definition = get_module_definition(key)
    if definition is None:
        raise ModuleAccessError(f"Unknown module: {key}")

    normalized_org_type = normalize_organization_type(organization_type, app_key=app_key)
    normalized_app_key = str(app_key or "").strip().lower()
    normalized_modules = set(_normalize_modules(enabled_modules))

    if normalized_org_type not in definition.allowed_organization_types:
        raise ModuleAccessError(f"Module {key} is not available for organization_type={normalized_org_type}")
    if normalized_app_key not in definition.allowed_app_keys:
        raise ModuleAccessError(f"Module {key} is not available for app_key={normalized_app_key}")
    if key not in normalized_modules:
        raise ModuleAccessError(f"Module {key} is not enabled for this tenant")

    return definition


def serialize_module_definition(module_key: str, *, enabled: bool) -> dict:
    key = str(module_key or "").strip().lower()
    definition = get_module_definition(key)
    if definition is None:
        raise ModuleAccessError(f"Unknown module: {key}")

    return {
        "module_key": definition.module_key,
        "display_name": definition.display_name,
        "enabled": enabled,
        "minimum_plan": definition.minimum_plan,
        "default_enabled": definition.default_enabled,
        "features": list(definition.features),
        "api_prefix": MODULE_API_PREFIXES.get(definition.module_key),
        "frontend_path": MODULE_FRONTEND_PATHS.get(definition.module_key),
        "nav_group": MODULE_NAV_GROUPS.get(definition.module_key, "Other"),
    }


def get_module_context_for_tenant(
    *,
    organization_type: str | None,
    enabled_modules: Iterable[str] | None,
    app_key: str | None,
    include_available: bool = True,
) -> dict:
    normalized_org_type = normalize_organization_type(organization_type, app_key=app_key)
    normalized_app_key = str(app_key or "").strip().lower()
    enabled_keys = set(_normalize_modules(enabled_modules))

    enabled: list[dict] = []
    available: list[dict] = []
    for module_key, definition in MODULE_REGISTRY.items():
        if normalized_org_type not in definition.allowed_organization_types:
            continue
        if normalized_app_key not in definition.allowed_app_keys:
            continue

        if module_key in enabled_keys:
            enabled.append(serialize_module_definition(module_key, enabled=True))
        elif include_available:
            available.append(serialize_module_definition(module_key, enabled=False))

    return {
        "organization_type": normalized_org_type,
        "app_key": normalized_app_key,
        "enabled_modules": sorted(enabled, key=lambda item: item["module_key"]),
        "available_modules": sorted(available, key=lambda item: item["module_key"]),
    }


def build_navigation_groups(modules: Iterable[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for module in modules:
        group = str(module.get("nav_group") or "Other")
        grouped.setdefault(group, []).append(module)

    order = {name: index for index, name in enumerate(NAV_GROUP_ORDER)}
    result: list[dict] = []
    for group_name, items in grouped.items():
        sorted_items = sorted(items, key=lambda item: str(item.get("display_name") or item.get("module_key") or ""))
        result.append(
            {
                "group_key": group_name.lower().replace(" ", "_"),
                "display_name": group_name,
                "items": sorted_items,
            }
        )

    return sorted(result, key=lambda group: (order.get(group["display_name"], 999), group["display_name"]))
