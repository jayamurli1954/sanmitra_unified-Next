from fastapi import APIRouter, Request, Header, HTTPException
from app.core.billing.service import billing_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["billing"])

@router.post("/webhook")
async def razorpay_webhook(request: Request, x_razorpay_signature: str = Header(None)):
    """
    Endpoint for Razorpay Webhooks.
    Handles payment success and subscription updates.
    """
    if not x_razorpay_signature:
        logger.error("Missing Razorpay Signature header")
        raise HTTPException(status_code=400, detail="Missing signature")

    payload = await request.body()
    
    # Verify Signature
    is_valid = await billing_service.verify_webhook_signature(payload, x_razorpay_signature)
    if not is_valid:
        logger.error("Invalid Razorpay Webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        data = await request.json()
        event = data.get("event")
        logger.info(f"Received Razorpay Webhook: {event}")

        if event in ["payment.captured", "subscription.charged", "order.paid"]:
            result = await billing_service.handle_payment_success(data)
            return result
            
        return {"status": "ignored", "event": event}
        
    except Exception as e:
        logger.error(f"Error processing Razorpay webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
