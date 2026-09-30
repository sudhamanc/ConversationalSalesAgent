"""PostgreSQL-backed ADK memory service.

ADK 2.10 ships no SQL memory service (InMemory, Vertex Memory Bank, Vertex RAG,
Firestore only), so this implements ``BaseMemoryService`` over the
``adk_memories`` table (migration ``003_platform.sql``) using PostgreSQL full-text
search. Memories are always scoped by ``(app_name, user_id)``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Sequence

from google.adk.memory import BaseMemoryService
from google.adk.memory.base_memory_service import SearchMemoryResponse
from google.adk.memory.memory_entry import MemoryEntry
from google.genai import types
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

logger = logging.getLogger("sales_common.memory")

MAX_RESULTS = 5
MAX_TEXT_CHARS = 4000


def _event_text(event) -> str:
    content = getattr(event, "content", None)
    if not content or not content.parts:
        return ""
    return " ".join(p.text for p in content.parts if getattr(p, "text", None)).strip()


class PostgresMemoryService(BaseMemoryService):
    """Full-text-search memory over PostgreSQL."""

    def __init__(self, db_url: Optional[str] = None, *, engine: Optional[AsyncEngine] = None):
        if engine is None and not db_url:
            raise ValueError("db_url or engine is required")
        self._engine = engine or create_async_engine(db_url, pool_pre_ping=True)

    async def add_session_to_memory(self, session) -> None:
        rows = []
        for event in session.events or []:
            if getattr(event, "partial", False):
                continue
            body = _event_text(event)
            if not body:
                continue
            rows.append(
                {
                    "app_name": session.app_name,
                    "user_id": session.user_id,
                    "session_id": session.id,
                    "event_id": event.id,
                    "author": event.author,
                    "text": body[:MAX_TEXT_CHARS],
                }
            )
        await self._insert(rows)

    async def add_events_to_memory(self, *, app_name, user_id, events, session_id=None, custom_metadata=None) -> None:
        rows = [
            {
                "app_name": app_name,
                "user_id": user_id,
                "session_id": session_id,
                "event_id": e.id,
                "author": e.author,
                "text": _event_text(e)[:MAX_TEXT_CHARS],
            }
            for e in events
            if _event_text(e)
        ]
        await self._insert(rows)

    async def add_memory(self, *, app_name, user_id, memories: Sequence[MemoryEntry], custom_metadata=None) -> None:
        rows = []
        for m in memories:
            body = " ".join(p.text for p in (m.content.parts or []) if p.text) if m.content else ""
            if body:
                rows.append(
                    {
                        "app_name": app_name,
                        "user_id": user_id,
                        "session_id": None,
                        "event_id": m.id,
                        "author": m.author,
                        "text": body[:MAX_TEXT_CHARS],
                    }
                )
        await self._insert(rows)

    async def _insert(self, rows: list[dict]) -> None:
        if not rows:
            return
        async with self._engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO adk_memories (app_name, user_id, session_id, event_id, author, text) "
                    "VALUES (:app_name, :user_id, :session_id, :event_id, :author, :text) "
                    "ON CONFLICT (app_name, user_id, event_id) WHERE event_id IS NOT NULL DO NOTHING"
                ),
                rows,
            )

    async def search_memory(self, *, app_name: str, user_id: str, query: str) -> SearchMemoryResponse:
        query = (query or "").strip()
        if not query:
            return SearchMemoryResponse(memories=[])
        async with self._engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT event_id, author, text, created_at, "
                    "ts_rank(tsv, websearch_to_tsquery('english', :q)) AS rank "
                    "FROM adk_memories "
                    "WHERE app_name = :app AND user_id = :uid "
                    "AND tsv @@ websearch_to_tsquery('english', :q) "
                    "ORDER BY rank DESC, created_at DESC LIMIT :lim"
                ),
                {"q": query, "app": app_name, "uid": user_id, "lim": MAX_RESULTS},
            )
            rows = result.mappings().all()
            if not rows:
                # websearch_to_tsquery ANDs terms; fall back to OR-matching any term
                terms = [t for t in "".join(c if c.isalnum() else " " for c in query).split() if len(t) > 2]
                if terms:
                    result = await conn.execute(
                        text(
                            "SELECT event_id, author, text, created_at, "
                            "ts_rank(tsv, to_tsquery('english', :q)) AS rank "
                            "FROM adk_memories WHERE app_name = :app AND user_id = :uid "
                            "AND tsv @@ to_tsquery('english', :q) "
                            "ORDER BY rank DESC, created_at DESC LIMIT :lim"
                        ),
                        {"q": " | ".join(terms), "app": app_name, "uid": user_id, "lim": MAX_RESULTS},
                    )
                    rows = result.mappings().all()
        memories = []
        for row in rows:
            created = row["created_at"]
            memories.append(
                MemoryEntry(
                    id=row["event_id"],
                    author=row["author"],
                    content=types.Content(role="user", parts=[types.Part(text=row["text"])]),
                    timestamp=(created or datetime.now(timezone.utc)).isoformat(),
                )
            )
        return SearchMemoryResponse(memories=memories)

    async def close(self) -> None:
        await self._engine.dispose()
