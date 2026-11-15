"""Minimal Langfuse public REST client (scores).

Services export traces over OTLP (``sales_common.telemetry``); the only REST
call they need is creating scores (gateway user feedback). ``POST
/api/public/scores`` takes a JSON array of score objects and answers 202, or
207 when some scores were rejected. A score is updated by sending it again
with the same ``id`` **and** ``timestamp``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from .config import env_str
from .telemetry import langfuse_host

logger = logging.getLogger("sales_common.langfuse_api")

SCORES_PATH = "/api/public/scores"


class LangfuseApiError(RuntimeError):
    """Langfuse rejected a request (non-2xx, or 207 with rejected items)."""


@dataclass(frozen=True)
class LangfuseClient:
    host: str
    public_key: str
    secret_key: str
    timeout: float = 10.0
    transport: Optional[httpx.AsyncBaseTransport] = None

    @classmethod
    def from_env(cls) -> Optional["LangfuseClient"]:
        """Client from ``LANGFUSE_BASE_URL`` (or ``LANGFUSE_HOST``) and the key pair; ``None`` without keys."""
        public_key = env_str("LANGFUSE_PUBLIC_KEY", "")
        secret_key = env_str("LANGFUSE_SECRET_KEY", "")
        if not (public_key and secret_key):
            return None
        return cls(langfuse_host(), public_key, secret_key)

    async def _post(self, path: str, payload: Any) -> httpx.Response:
        async with httpx.AsyncClient(
            base_url=self.host,
            auth=(self.public_key, self.secret_key),
            timeout=self.timeout,
            transport=self.transport,
        ) as client:
            response = await client.post(path, json=payload)
        if response.status_code >= 300 or response.status_code == 207:
            raise LangfuseApiError(f"POST {path} -> {response.status_code}: {response.text[:300]}")
        return response

    async def create_score(
        self,
        *,
        name: str,
        value: float | str,
        trace_id: Optional[str] = None,
        session_id: Optional[str] = None,
        score_id: Optional[str] = None,
        data_type: str = "NUMERIC",
        comment: Optional[str] = None,
        environment: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Create (or, with the same ``score_id`` and ``timestamp``, update) one score."""
        if timestamp is not None and timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        score = {
            "id": score_id,
            "traceId": trace_id,
            "sessionId": session_id,
            "name": name,
            "value": float(value) if isinstance(value, (bool, int)) else value,
            "dataType": data_type,
            "comment": comment,
            "environment": environment,
            "timestamp": timestamp.isoformat() if timestamp else None,
            "metadata": metadata,
        }
        await self._post(SCORES_PATH, [{k: v for k, v in score.items() if v is not None}])
