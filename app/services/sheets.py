import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Optional
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from app.core.config import settings
from app.core.logging import logger

class SheetsCacheEntry:
    def __init__(self, data: str):
        self.data = data
        self.last_updated = datetime.now()

class SheetsService:
    """
    Handles fetching and caching Q/A knowledge from Google Sheets.
    Implements an auto-refreshing background loop every 60 seconds.
    """
    def __init__(self):
        self.cache: Dict[str, SheetsCacheEntry] = {}
        self.ttl_seconds = 60
        self.scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        self.credentials = self._load_credentials()
        self._refresh_task = None
        
    def _load_credentials(self) -> Optional[Credentials]:
        creds_var = settings.GOOGLE_CREDENTIALS_JSON
        if not creds_var:
            logger.warning("GOOGLE_CREDENTIALS_JSON is not set. Sheets integration disabled.")
            return None
        
        try:
            if os.path.exists(creds_var):
                return Credentials.from_service_account_file(creds_var, scopes=self.scopes)
            else:
                creds_info = json.loads(creds_var)
                return Credentials.from_service_account_info(creds_info, scopes=self.scopes)
        except Exception as e:
            logger.error(f"Failed to load Google Service Account credentials: {e}")
            return None

    def _fetch_sheet_data_sync(self, sheet_id: str, range_name: str = "Sheet1!A:B") -> str:
        if not self.credentials:
            raise ValueError("Google credentials are not configured.")
            
        service = build("sheets", "v4", credentials=self.credentials, cache_discovery=False)
        sheet = service.spreadsheets()
        
        # Read the Q/A rows
        result = sheet.values().get(spreadsheetId=sheet_id, range=range_name).execute()
        values = result.get("values", [])
        
        if not values:
            return "No knowledge base data found."
            
        # Convert into knowledge format for AI
        knowledge_text = "Business Knowledge Base / FAQs:\n"
        for row in values:
            if len(row) >= 2:
                q, a = row[0].strip(), row[1].strip()
                knowledge_text += f"Q: {q}\nA: {a}\n\n"
            elif len(row) == 1:
                knowledge_text += f"- {row[0].strip()}\n"
                
        return knowledge_text.strip()

    def start_background_refresh(self):
        """Starts the auto-refresh loop on app startup."""
        if not self._refresh_task and self.credentials:
            self._refresh_task = asyncio.create_task(self._auto_refresh_loop())
            logger.info("Google Sheets auto-refresh background task started.")
            
    async def _auto_refresh_loop(self):
        """Runs in the background every 60 seconds to update all cached sheets."""
        while True:
            await asyncio.sleep(self.ttl_seconds)
            # Copy keys to avoid runtime error if dict changes size
            for sheet_id in list(self.cache.keys()):
                try:
                    logger.debug(f"Auto-refreshing cache for sheet: {sheet_id}")
                    knowledge = await asyncio.to_thread(self._fetch_sheet_data_sync, sheet_id)
                    self.cache[sheet_id].data = knowledge
                    self.cache[sheet_id].last_updated = datetime.now()
                except Exception as e:
                    logger.error(f"Auto-refresh failed for sheet {sheet_id}: {e}")

    async def get_knowledge(self, sheet_id: str) -> str:
        """
        Retrieves formatted knowledge base. Uses cache if available and fresh.
        """
        if not sheet_id or not self.credentials:
            return ""
            
        # If cache exists, use it (auto-refresh loop keeps it up to date)
        if sheet_id in self.cache:
            entry = self.cache[sheet_id]
            # Serve if it's not extremely stale (e.g. background task crashed)
            if (datetime.now() - entry.last_updated).total_seconds() < (self.ttl_seconds * 2):
                logger.debug(f"Cache hit for sheet_id: {sheet_id}")
                return entry.data
                
        logger.info(f"Cache miss (or stale) for sheet_id: {sheet_id}. Fetching directly...")
        try:
            knowledge = await asyncio.to_thread(self._fetch_sheet_data_sync, sheet_id)
            self.cache[sheet_id] = SheetsCacheEntry(knowledge)
            return knowledge
        except Exception as e:
            logger.error(f"Error fetching data from Google Sheets ({sheet_id}): {e}", exc_info=True)
            return self.cache[sheet_id].data if sheet_id in self.cache else ""

sheets_service = SheetsService()
