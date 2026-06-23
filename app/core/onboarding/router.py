from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.core.auth.dependencies import get_current_user
from app.core.onboarding.schemas import (
    OnboardingApproveRequest,
    OnboardingApproveResponse,
    OnboardingPaymentUpdateRequest,
    OnboardingRejectRequest,
    OnboardingRejectResponse,
    OnboardingRequestCreate,
    OnboardingRequestItem,
    OnboardingRequestResponse,
    OnboardingResendRequest,
    OnboardingVerificationUpdateRequest,
)
from app.core.onboarding.service import (
    approve_onboarding_request,
    create_onboarding_request,
    get_onboarding_request,
    list_onboarding_requests,
    normalize_public_onboarding_app_key,
    record_onboarding_payment,
    record_onboarding_verification,
    reject_onboarding_request,
    resend_onboarding_credentials,
)

router = APIRouter(prefix="/onboarding-requests", tags=["onboarding"])


def _require_super_admin(current_user: dict) -> None:
    if str(current_user.get("role") or "").strip() != "super_admin":
        raise HTTPException(status_code=403, detail="Only super admins can manage onboarding requests")


@router.post("/register", response_model=OnboardingRequestResponse)
async def register_onboarding_request(
    payload: OnboardingRequestCreate,
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    try:
        return await create_onboarding_request(payload, app_key=x_app_key)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        if "X-App-Key" in str(exc):
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("")
@router.get("/")
async def list_onboarding_requests_endpoint(
    status: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    current_user: dict = Depends(get_current_user),
):
    """List onboarding requests for one explicit product app context."""
    _require_super_admin(current_user)
    try:
        rows = await list_onboarding_requests(
            status=status,
            app_key=normalize_public_onboarding_app_key(x_app_key),
            limit=limit,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return [OnboardingRequestItem(**row) for row in rows]


@router.get("/{request_id}", response_model=OnboardingRequestItem)
async def get_onboarding_request_endpoint(
    request_id: str,
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    current_user: dict = Depends(get_current_user),
):
    """Get an onboarding request only within one explicit product app context."""
    _require_super_admin(current_user)
    try:
        requested_app_key = normalize_public_onboarding_app_key(x_app_key)
        row = await get_onboarding_request(request_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not row or str(row.get("app_key") or "").strip().lower() != requested_app_key:
        raise HTTPException(status_code=404, detail="Onboarding request not found")
    return OnboardingRequestItem(**row)


@router.patch("/{request_id}/payment", response_model=OnboardingRequestItem)
async def record_onboarding_payment_endpoint(
    request_id: str,
    payload: OnboardingPaymentUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    _require_super_admin(current_user)
    try:
        row = await record_onboarding_payment(
            request_id=request_id,
            updated_by=str(current_user.get("sub") or "system"),
            payload=payload,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0] if exc.args else exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return OnboardingRequestItem(**row)


@router.patch("/{request_id}/verification", response_model=OnboardingRequestItem)
async def record_onboarding_verification_endpoint(
    request_id: str,
    payload: OnboardingVerificationUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    _require_super_admin(current_user)
    try:
        row = await record_onboarding_verification(
            request_id=request_id,
            updated_by=str(current_user.get("sub") or "system"),
            payload=payload,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0] if exc.args else exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return OnboardingRequestItem(**row)


@router.post("/{request_id}/approve", response_model=OnboardingApproveResponse)
async def approve_onboarding_request_endpoint(
    request_id: str,
    payload: OnboardingApproveRequest,
    current_user: dict = Depends(get_current_user),
):
    _require_super_admin(current_user)

    try:
        row = await approve_onboarding_request(
            request_id=request_id,
            approved_by=str(current_user.get("sub") or "system"),
            payload=payload,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0] if exc.args else exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return OnboardingApproveResponse(**row)


@router.post("/{request_id}/reject", response_model=OnboardingRejectResponse)
async def reject_onboarding_request_endpoint(
    request_id: str,
    payload: OnboardingRejectRequest,
    current_user: dict = Depends(get_current_user),
):
    _require_super_admin(current_user)

    try:
        row = await reject_onboarding_request(
            request_id=request_id,
            rejected_by=str(current_user.get("sub") or "system"),
            payload=payload,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0] if exc.args else exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return OnboardingRejectResponse(**row)


@router.post("/{request_id}/resend-credentials", response_model=OnboardingApproveResponse)
async def resend_onboarding_credentials_endpoint(
    request_id: str,
    payload: OnboardingResendRequest,
    current_user: dict = Depends(get_current_user),
):
    _require_super_admin(current_user)

    try:
        row = await resend_onboarding_credentials(
            request_id=request_id,
            resent_by=str(current_user.get("sub") or "system"),
            payload=payload,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0] if exc.args else exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return OnboardingApproveResponse(**row)
