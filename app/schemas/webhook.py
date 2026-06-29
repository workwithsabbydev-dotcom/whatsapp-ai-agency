from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from app.core.config import settings

class TextMessage(BaseModel):
    body: str
    
    @field_validator("body")
    @classmethod
    def validate_body_length(cls, v: str) -> str:
        if len(v) > settings.MAX_MESSAGE_LENGTH:
            raise ValueError(f"Message body exceeds max length of {settings.MAX_MESSAGE_LENGTH}")
        return v.strip()

class Message(BaseModel):
    model_config = {"populate_by_name": True}
    
    sender: str = Field(alias="from")
    id: str
    timestamp: str
    type: str
    text: Optional[TextMessage] = None

class Metadata(BaseModel):
    display_phone_number: str
    phone_number_id: str

class Value(BaseModel):
    messaging_product: str
    metadata: Metadata
    messages: Optional[List[Message]] = None
    statuses: Optional[List[dict]] = None

class Change(BaseModel):
    value: Value
    field: str

class Entry(BaseModel):
    id: str
    changes: List[Change]

class WebhookPayload(BaseModel):
    object: str
    entry: List[Entry]
