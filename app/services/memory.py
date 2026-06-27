import uuid
from typing import List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from app.db.models import Customer, Conversation, Message, RoleEnum
from app.core.logging import logger

async def get_or_create_customer(db: AsyncSession, business_id: uuid.UUID, phone_number: str) -> Customer:
    """Finds an existing customer for a business or creates a new one."""
    result = await db.execute(
        select(Customer).where(
            Customer.business_id == business_id,
            Customer.phone_number == phone_number
        )
    )
    customer = result.scalars().first()
    
    if not customer:
        logger.info(f"Creating new customer record for phone {phone_number} (Business: {business_id})")
        customer = Customer(business_id=business_id, phone_number=phone_number)
        db.add(customer)
        await db.flush()
        
    return customer

async def get_or_create_conversation(db: AsyncSession, customer_id: uuid.UUID) -> Conversation:
    """Finds the most recent conversation or creates a new one."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.customer_id == customer_id)
        .order_by(desc(Conversation.last_interaction_at))
    )
    conversation = result.scalars().first()
    
    if not conversation:
        logger.info(f"Starting new conversation session for Customer: {customer_id}")
        conversation = Conversation(customer_id=customer_id)
        db.add(conversation)
        await db.flush()
    else:
        conversation.last_interaction_at = datetime.now(timezone.utc)
        await db.flush()
        
    return conversation

async def store_message(
    db: AsyncSession, 
    business_id: uuid.UUID, 
    phone_number: str, 
    role: RoleEnum, 
    content: str
) -> Tuple[uuid.UUID, Conversation]:
    """
    High-level entrypoint to persist a message.
    Returns (conversation_id, conversation) to avoid redundant DB lookups downstream.
    """
    # 1. Resolve Customer
    customer = await get_or_create_customer(db, business_id, phone_number)
    
    # 2. Resolve Session
    conversation = await get_or_create_conversation(db, customer.id)
    
    # 3. Insert Message
    logger.debug(f"Storing '{role.value}' message in conversation {conversation.id}")
    message = Message(
        conversation_id=conversation.id,
        role=role,
        content=content
    )
    db.add(message)
    await db.flush()
    
    return conversation.id, conversation

async def get_recent_messages(db: AsyncSession, conversation_id: uuid.UUID, limit: int = 10) -> List[Message]:
    """
    Fetches the last N messages for a conversation, returned in chronological order 
    (oldest first) so they can be injected directly into the Gemini context window.
    """
    logger.debug(f"Fetching last {limit} messages for Context (Conversation: {conversation_id})")
    
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(desc(Message.created_at))
        .limit(limit)
    )
    
    messages = result.scalars().all()
    
    # Reverse to chronological order: [Oldest ... Newest]
    return list(reversed(messages))
