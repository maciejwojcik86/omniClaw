import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class LiteLLMClient:
    """Wrapper for interacting with the LiteLLM proxy virtual keys API."""
    def __init__(self, proxy_url: str, master_key: str):
        self.proxy_url = proxy_url.rstrip("/")
        self.master_key = master_key
        self.headers = {
            "Authorization": f"Bearer {self.master_key}",
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(headers=self.headers, timeout=10.0)

    async def generate_virtual_key(self, user_id: str, models: list[str] | None = None, max_budget: float | None = None) -> dict[str, Any]:
        """
        Generates a virtual key for the given user_id.
        Optionally configures max budget and allowed models.
        """
        url = f"{self.proxy_url}/key/generate"
        payload = {"user_id": user_id}
        if models:
            payload["models"] = models
        if max_budget is not None:
            payload["max_budget"] = max_budget
            
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data
        except httpx.HTTPError as e:
            logger.error(f"Failed to generate virtual key for user {user_id}: {e}")
            raise

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        """
        Fetches usage info for a specific user ID from the LiteLLM proxy.
        """
        url = f"{self.proxy_url}/user/info?user_id={user_id}"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            return data
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch info for user {user_id}: {e}")
            raise

    async def update_user_budget(self, user_id: str, max_budget: float) -> dict[str, Any]:
        """
        Updates the max budget for a user inside LiteLLM proxy.
        """
        url = f"{self.proxy_url}/user/update"
        payload = {"user_id": user_id, "max_budget": max_budget}
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to update budget for user {user_id}: {e}")
            raise

    async def close(self):
        await self.client.aclose()
