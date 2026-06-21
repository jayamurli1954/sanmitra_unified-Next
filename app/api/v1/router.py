from fastapi import APIRouter
from app.core.audit.router import router as audit_router
from app.core.billing.router import router as billing_router
from app.modules.blog.router import router as blog_router
from app.modules.business.router import router as business_router

from app.api.gruhamitra_compat_router import router as gruhamitra_compat_router
from app.accounting.report_alias_router import router as accounting_report_alias_router
from app.accounting.router import router as accounting_router
from app.core.auth.router import router as auth_router
from app.core.email_delivery.router import router as email_delivery_router
from app.core.modules.router import router as modules_router
from app.core.onboarding.router import router as onboarding_router
from app.core.platform_owner.router import router as platform_owner_router
from app.core.tenants.router import router as tenants_router
from app.core.users.router import router as users_router
from app.modules.housing.router import router as housing_router
from app.modules.housing_compat.router import router as housing_compat_router
from app.modules.legal.router import router as legal_router
from app.modules.legal_compat.router import router as legal_compat_router
from app.modules.mandir_compat.router import router as mandir_compat_router
from app.modules.mitrabooks_compat.router import router as mitrabooks_compat_router
from app.modules.rag.router import router as rag_router
from app.modules.temple.router import router as temple_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(email_delivery_router)
api_router.include_router(onboarding_router)
api_router.include_router(platform_owner_router)
api_router.include_router(tenants_router)
api_router.include_router(users_router)
api_router.include_router(modules_router)
api_router.include_router(audit_router)
api_router.include_router(accounting_router)
api_router.include_router(accounting_report_alias_router)
api_router.include_router(gruhamitra_compat_router)
api_router.include_router(temple_router)
api_router.include_router(housing_router)
api_router.include_router(housing_compat_router)
api_router.include_router(legal_router)
api_router.include_router(legal_compat_router)
api_router.include_router(mandir_compat_router)
api_router.include_router(mitrabooks_compat_router)
# InvestMitra is excluded from the unified backend scope — investment routes are
# intentionally not mounted here. See chore/disable-investmitra-unified-scope.
api_router.include_router(rag_router)
api_router.include_router(billing_router)
api_router.include_router(business_router)
api_router.include_router(blog_router)
