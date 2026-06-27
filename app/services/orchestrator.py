import re
from sqlalchemy.future import select
from cachetools import TTLCache

from app.db.database import AsyncSessionLocal
from app.db.models import Business, RoleEnum, Conversation
from app.services.memory import store_message, get_recent_messages
from app.services.sheets import sheets_service
from app.services.prompt_builder import build_gemini_payload
from app.services.gemini import gemini_client
from app.services.whatsapp import whatsapp_client
from app.core.logging import logger

# In-memory cache for Business configs to avoid hitting the DB on every single message.
# TTL of 300s (5 min) means config changes propagate within 5 minutes.
_business_cache: TTLCache = TTLCache(maxsize=500, ttl=300)

HANDOFF_PATTERNS = [
    re.compile(r"\bhuman\b", re.IGNORECASE),
    re.compile(r"\bagent\b", re.IGNORECASE),
    re.compile(r"\bperson\b", re.IGNORECASE),
    re.compile(r"\bcall me\b", re.IGNORECASE),
    re.compile(r"\btalk to someone\b", re.IGNORECASE),
]

HANDOFF_REPLY = "I'll let the business know you'd like to speak with someone."

async def _get_business(db, phone_number_id: str) -> Business | None:
    """Fetches a Business, using an in-memory cache to avoid repeated DB hits."""
    if phone_number_id in _business_cache:
        return _business_cache[phone_number_id]
    
    result = await db.execute(
        select(Business).where(
            Business.wa_phone_number_id == phone_number_id,
            Business.is_active == True
        )
    )
    business = result.scalars().first()
    if business:
        _business_cache[phone_number_id] = business
    return business

async def process_incoming_message(phone_number_id: str, user_phone: str, message_body: str):
    """
    End-to-End Orchestrator for processing a single WhatsApp message.
    Designed to run as a background task to instantly release the Meta webhook connection.
    
    This function owns the full DB transaction lifecycle.
    """
    logger.info(f"[Orchestrator] Start | User: {user_phone} | Business: {phone_number_id}")
    
    async with AsyncSessionLocal() as db:
        try:
            # 1. Identify business (cached)
            business = await _get_business(db, phone_number_id)
            
            if not business:
                logger.error(f"[Orchestrator] Abort: No active business for phone_number_id={phone_number_id}")
                return
                
            # 2. Save USER message immediately (no data loss if LLM crashes)
            conversation_id, conversation = await store_message(
                db=db, 
                business_id=business.id, 
                phone_number=user_phone, 
                role=RoleEnum.user, 
                content=message_body
            )
            
            # 3. Human handoff check
            if conversation.requires_human:
                logger.info(f"[Orchestrator] Conversation {conversation_id} is in handoff mode. Skipping AI.")
                await db.commit()
                return
                
            if any(p.search(message_body) for p in HANDOFF_PATTERNS):
                logger.info(f"[Orchestrator] Human handoff triggered for {user_phone}.")
                conversation.requires_human = True
                
                await store_message(
                    db=db, 
                    business_id=business.id, 
                    phone_number=user_phone, 
                    role=RoleEnum.assistant, 
                    content=HANDOFF_REPLY
                )
                await db.commit()
                
                await whatsapp_client.send_text_message(
                    phone_number_id=business.wa_phone_number_id,
                    access_token=business.wa_access_token,
                    to_phone=user_phone,
                    message=HANDOFF_REPLY
                )
                return
            
            # 4. Load Sheets knowledge (served from fast cache)
            knowledge_base = ""
            if business.sheets_id:
                knowledge_base = await sheets_service.get_knowledge(business.sheets_id)
                
            # 5. Load chat history (fetch 10 prior messages, excluding the one we just saved)
            history = await get_recent_messages(db, conversation_id, limit=11)
            prior_messages = history[:-1] if history else []
            
            # Commit user message before external API calls
            await db.commit()
            
            # 6. Build prompt
            payload = build_gemini_payload(
                business_instructions=business.system_prompt,
                knowledge_base=knowledge_base,
                recent_messages=prior_messages,
                current_message=message_body
            )
            
            # 7. Call Gemini
            logger.info(f"[Orchestrator] Calling Gemini for {user_phone}...")
            ai_response = await gemini_client.generate_content(payload)
            
            # 8. Save AI message in a NEW transaction (user message is already committed)
            async with AsyncSessionLocal() as db2:
                await store_message(
                    db=db2, 
                    business_id=business.id, 
                    phone_number=user_phone, 
                    role=RoleEnum.assistant, 
                    content=ai_response
                )
                await db2.commit()
            
            # 9. Send WhatsApp reply
            await whatsapp_client.send_text_message(
                phone_number_id=business.wa_phone_number_id,
                access_token=business.wa_access_token,
                to_phone=user_phone,
                message=ai_response
            )
            
            logger.info(f"[Orchestrator] Complete | Replied to {user_phone}")
            
        except Exception as e:
            logger.error(f"[Orchestrator] Fatal error for {user_phone}: {e}", exc_info=True)
