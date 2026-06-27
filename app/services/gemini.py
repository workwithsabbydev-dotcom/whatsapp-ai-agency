import asyncio
import httpx
from typing import Dict, Any
from app.core.logging import logger
from app.core.config import settings

class GeminiClient:
    """
    Handles asynchronous communication with the Gemini REST API.
    Implements robust networking: timeouts, retries, and rate limit handling.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Defaulting to gemini-1.5-flash for general fast automated replies
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        # 30 seconds for reading, 10 seconds for connecting
        self.timeout = httpx.Timeout(30.0, connect=10.0)
        self.max_retries = 3

    async def generate_content(self, payload: Dict[str, Any]) -> str:
        """
        Executes an async HTTP POST to Gemini.
        Returns ONLY the plain text string response.
        """
        headers = {"Content-Type": "application/json"}
        
        for attempt in range(1, self.max_retries + 1):
            try:
                # AsyncClient is instantiated here to ensure it binds to the current running event loop safely
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(self.url, json=payload, headers=headers)
                    
                    # --- Rate Limit Handling (HTTP 429) ---
                    if response.status_code == 429:
                        wait_time = 2 ** attempt
                        logger.warning(f"Gemini API rate limited (429). Retrying in {wait_time}s... (Attempt {attempt}/{self.max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                        
                    # --- Server Error Handling (HTTP 500+) ---
                    if response.status_code >= 500:
                        wait_time = 2 ** attempt
                        logger.warning(f"Gemini API server error ({response.status_code}). Retrying in {wait_time}s... (Attempt {attempt}/{self.max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                        
                    # Raise exception for 4xx errors (e.g. 400 Bad Request, 401 Unauthorized)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    # --- Extract Plain Text ---
                    try:
                        text_response = data["candidates"][0]["content"]["parts"][0]["text"]
                        return text_response.strip()
                    except (KeyError, IndexError) as e:
                        logger.error(f"Failed to parse Gemini response. Raw output: {data}")
                        raise ValueError("Unexpected response format from Gemini API") from e

            # --- Timeout Handling ---
            except httpx.TimeoutException:
                logger.warning(f"Gemini API request timed out. (Attempt {attempt}/{self.max_retries})")
                if attempt == self.max_retries:
                    logger.error("Gemini API max retries reached due to timeouts.")
                    raise
                await asyncio.sleep(2 ** attempt)
                
            # --- Network / Transport Error Handling ---
            except httpx.RequestError as e:
                logger.error(f"Gemini API network request error: {e}")
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)

        raise Exception("Gemini API failed after max retries.")

# Instantiate the client using the agency's master key
gemini_client = GeminiClient(api_key=settings.GEMINI_API_KEY)
