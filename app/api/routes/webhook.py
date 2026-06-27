import json
from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks
from app.core.config import settings
from app.core.logging import logger
from app.core.security import verify_webhook_signature
from app.schemas.webhook import WebhookPayload
from app.services.orchestrator import process_incoming_message
from cachetools import TTLCache

router = APIRouter()

# Deduplication cache: stores processed message IDs for 5 minutes (300s)
processed_messages: TTLCache = TTLCache(maxsize=10000, ttl=300)

@router.get("/webhook")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge")
):
    """
    Handles Meta's initial webhook verification ping.
    """
    if mode == "subscribe" and token == settings.WEBHOOK_VERIFY_TOKEN:
        logger.info("WhatsApp Webhook verified successfully!")
        return int(challenge)
    
    logger.warning("Failed webhook verification attempt.")
    raise HTTPException(status_code=403, detail="Invalid verification token")

@router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks): 
    """
    Receives and processes incoming WhatsApp messages.
    Uses raw Request to validate HMAC signature BEFORE parsing JSON.
    """
    # 1. Verify webhook signature (security)
    body = await verify_webhook_signature(request)
    
    # 2. Parse and validate payload
    try:
        raw_payload = json.loads(body)
        data = WebhookPayload(**raw_payload)
    except Exception as e:
        logger.error(f"Invalid Webhook Payload: {e}")
        return {"status": "ok"}
        
    if data.object != "whatsapp_business_account":
        return {"status": "ok"}

    for entry in data.entry:
        for change in entry.changes:
            value = change.value
            phone_number_id = value.metadata.phone_number_id
            
            if not value.messages:
                continue 
                
            for msg in value.messages:
                # Deduplicate
                if msg.id in processed_messages:
                    logger.debug(f"Duplicate message ignored: {msg.id}")
                    continue
                processed_messages[msg.id] = True
                
                user_phone = msg.sender
                
                if msg.type != "text" or not msg.text:
                    logger.info(f"Ignored non-text message type: {msg.type} from {user_phone}")
                    continue
                    
                message_body = msg.text.body
                
                logger.info(f"Received message from {user_phone} for business {phone_number_id}")
                
                background_tasks.add_task(
                    process_incoming_message,
                    phone_number_id=phone_number_id,
                    user_phone=user_phone,
                    message_body=message_body
                )
                
    return {"status": "ok"}
