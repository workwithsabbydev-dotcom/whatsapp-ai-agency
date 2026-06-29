import hashlib
import hmac
from fastapi import Request, HTTPException
from app.core.config import settings
from app.core.logging import logger

async def verify_webhook_signature(request: Request) -> bytes:
    """
    Validates the X-Hub-Signature-256 header on incoming Meta webhooks.
    This prevents attackers from spoofing fake WhatsApp messages to your endpoint.
    Must be called BEFORE parsing the JSON body.
    """
    logger.info(f"Webhook POST received from {request.client.host if request.client else 'unknown'}")
    
    signature_header = request.headers.get("X-Hub-Signature-256")
    body = await request.body()
    
    # Treat common placeholder values as "not configured"
    _placeholder_values = {"", "your_meta_app_secret", "your-meta-app-secret", "changeme", "none"}
    app_secret = (settings.META_APP_SECRET or "").strip()
    
    if not app_secret or app_secret.lower() in _placeholder_values:
        # If no real app secret is configured, skip validation (dev mode only)
        logger.warning("META_APP_SECRET is not set (or is a placeholder). Skipping webhook signature verification.")
        return body
    
    if not signature_header:
        logger.warning("Missing X-Hub-Signature-256 header on webhook POST.")
        raise HTTPException(status_code=401, detail="Missing signature header")
    
    expected_signature = "sha256=" + hmac.new(
        app_secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(expected_signature, signature_header):
        logger.warning("Invalid webhook signature. Possible spoofing attempt.")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    logger.debug("Webhook signature verified successfully.")
    return body
