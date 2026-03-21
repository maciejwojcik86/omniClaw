"""Async client helpers for OmniClaw's LiteLLM proxy integration.

This module wraps the small subset of LiteLLM proxy endpoints that OmniClaw
currently depends on:
- virtual key creation during agent provisioning
- user spend lookup during budget reconciliation
- user budget updates when OmniClaw changes spending caps

Primary call sites:
- `src/omniclaw/provisioning/service.py` generates a virtual key for a newly
  provisioned agent and stores that key in the node budget record.
- `src/omniclaw/budgets/service.py` and `src/omniclaw/budgets/engine.py`
  query spend and push budget-cap updates back into LiteLLM so provider-side
  enforcement stays aligned with OmniClaw's internal budget model.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class LiteLLMClient:
    """Small async wrapper around the LiteLLM proxy management API.

    Why this exists:
    OmniClaw should not scatter raw HTTP calls, auth header setup, timeout
    policy, and endpoint paths across provisioning and budget modules. This
    class gives the rest of the codebase one focused client for the operations
    OmniClaw currently needs from LiteLLM.

    Important behavior:
    the client talks to administrative LiteLLM endpoints using the configured
    master key, not an agent's virtual key. Callers are responsible for closing
    the underlying `httpx.AsyncClient` by awaiting `close()`.
    """

    def __init__(self, proxy_url: str, master_key: str):
        """Create a client bound to one LiteLLM proxy instance.

        Args:
            proxy_url: Base URL of the LiteLLM proxy, for example
                `http://127.0.0.1:4000`.
            master_key: Administrative bearer token accepted by LiteLLM's
                management endpoints.

        Where it is used:
        budget and provisioning services instantiate this class from values in
        OmniClaw settings when they need to manage provider-side user records.
        """
        self.proxy_url = proxy_url.rstrip("/")
        self.master_key = master_key
        self.headers = {
            "Authorization": f"Bearer {self.master_key}",
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(headers=self.headers, timeout=10.0)

    async def generate_virtual_key(
        self,
        user_id: str,
        models: list[str] | None = None,
        max_budget: float | None = None,
    ) -> dict[str, Any]:
        """Create a LiteLLM virtual key for one OmniClaw-managed user.

        Why this exists:
        OmniClaw provisions one LiteLLM "user" per agent/node. The returned
        virtual key is what that agent later uses to send model traffic through
        the proxy without exposing the master key.

        Where it is used:
        `src/omniclaw/provisioning/service.py` calls this while provisioning an
        agent and stores the returned key in the associated budget record.

        Args:
            user_id: OmniClaw's stable identifier for the LiteLLM user. In
                current call sites this is usually the node name.
            models: Optional allow-list of model identifiers that LiteLLM should
                permit for this key.
            max_budget: Optional provider-side budget cap to attach at creation
                time.

        Returns:
            The JSON response from LiteLLM, which typically includes the newly
            generated virtual key and related metadata.
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
        """Fetch LiteLLM's current view of one user's usage and limits.

        Why this exists:
        OmniClaw tracks budget state in its own database, but LiteLLM is the
        component that meters real proxy usage. This method lets OmniClaw pull
        spend and cap data back from the provider-facing system.

        Where it is used:
        `src/omniclaw/budgets/service.py` uses it to sync spend for one node or
        all active nodes.

        Returns:
            The JSON response from LiteLLM's `/user/info` endpoint. Current
            callers care most about fields like `spend` and `max_budget`.
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
        """Push an updated provider-side budget cap to LiteLLM.

        Why this exists:
        OmniClaw computes and stores budget allocations locally, but LiteLLM
        needs the same cap so it can enforce the limit while requests are
        flowing through the proxy.

        Where it is used:
        `src/omniclaw/budgets/service.py` and `src/omniclaw/budgets/engine.py`
        call this when budget cycles run or an operator explicitly changes a
        node's allowance.
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

    async def close(self) -> None:
        """Close the underlying HTTP client and release network resources.

        Why this exists:
        `httpx.AsyncClient` keeps connection pools open. Callers that create a
        `LiteLLMClient` are expected to close it when their operation finishes.

        Where it is used:
        provisioning and budget services call this in their cleanup paths.
        """
        await self.client.aclose()
