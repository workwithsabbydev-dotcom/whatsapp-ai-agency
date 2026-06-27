import httpx
from typing import Dict, Any
from app.core.logging import logger

class WhatsAppClient:
    """
    Handles sending outbound messages via the WhatsApp Cloud API.
    """
    def __init__(self):
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        self.timeout = httpx.Timeout(20.0, connect=10.0)

    async def send_text_message(self, phone_number_id: str, access_token: str, to_phone: str, message: str) -> Dict[str, Any]:
        """
        Sends a plain text message to a WhatsApp user on behalf of a specific business tenant.
        Requires the tenant's specific phone_number_id and access_token.
        """
        url = f"{self.base_url}/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                # Check for API Errors
                if response.status_code >= 400:
                    logger.error(f"WhatsApp API Error [{response.status_code}]: {response.text}")
                    response.raise_for_status()
                    
                return response.json()
                
        except httpx.RequestError as e:
            logger.error(f"WhatsApp network request failed: {e}")
            raise

whatsapp_client = WhatsAppClient()
