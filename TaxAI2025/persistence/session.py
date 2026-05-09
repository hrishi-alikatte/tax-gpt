"""Per-session persistence contracts.

The deployed path can swap `InMemorySessionStore` for `SupabaseSessionStore`
without changing UI state semantics. The Supabase class is intentionally thin:
schema ownership lives in `infra/supabase/migrations/0001_init.sql`.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


class SessionSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_uuid: str
    profile: dict[str, Any] | None = None
    documents: list[dict[str, Any]] = Field(default_factory=list)
    tax_facts: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    interview_answers: list[dict[str, Any]] = Field(default_factory=list)
    audit_log: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None


class SessionStore(Protocol):
    def create(self, session_uuid: str) -> SessionSnapshot:
        ...

    def get(self, session_uuid: str) -> SessionSnapshot | None:
        ...

    def save(self, snapshot: SessionSnapshot) -> None:
        ...

    def wipe(self, session_uuid: str) -> bool:
        ...


class InMemorySessionStore:
    def __init__(self, ttl_days: int = 30) -> None:
        self.ttl_days = ttl_days
        self._sessions: dict[str, SessionSnapshot] = {}

    def create(self, session_uuid: str) -> SessionSnapshot:
        now = datetime.utcnow()
        snapshot = SessionSnapshot(
            session_uuid=session_uuid,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(days=self.ttl_days),
        )
        self._sessions[session_uuid] = snapshot
        return snapshot

    def get(self, session_uuid: str) -> SessionSnapshot | None:
        snapshot = self._sessions.get(session_uuid)
        if snapshot is None:
            return None
        if snapshot.expires_at is not None and snapshot.expires_at < datetime.utcnow():
            self._sessions.pop(session_uuid, None)
            return None
        return snapshot

    def save(self, snapshot: SessionSnapshot) -> None:
        self._sessions[snapshot.session_uuid] = snapshot.model_copy(
            update={"updated_at": datetime.utcnow()}
        )

    def wipe(self, session_uuid: str) -> bool:
        return self._sessions.pop(session_uuid, None) is not None


class SupabaseSessionStore:
    """Supabase-backed store adapter.

    This adapter defers importing the optional `supabase` SDK until runtime so
    local tests and desktop demo flows do not gain a hard dependency.
    """

    def __init__(self, url: str, service_role_key: str) -> None:
        self.url = url
        self.service_role_key = service_role_key
        self._client: Any | None = None

    def _supabase(self) -> Any:
        if self._client is None:
            try:
                from supabase import create_client
            except ImportError as exc:  # pragma: no cover - optional deploy dep
                raise RuntimeError(
                    "SupabaseSessionStore requires the optional 'supabase' package."
                ) from exc
            self._client = create_client(self.url, self.service_role_key)
        return self._client

    def create(self, session_uuid: str) -> SessionSnapshot:
        snapshot = SessionSnapshot(session_uuid=session_uuid)
        self.save(snapshot)
        return snapshot

    def get(self, session_uuid: str) -> SessionSnapshot | None:
        row = (
            self._supabase()
            .table("sessions")
            .select("*")
            .eq("session_uuid", session_uuid)
            .maybe_single()
            .execute()
            .data
        )
        if not row:
            return None
        return SessionSnapshot(**row["snapshot"])

    def save(self, snapshot: SessionSnapshot) -> None:
        payload = {
            "session_uuid": snapshot.session_uuid,
            "snapshot": snapshot.model_dump(mode="json"),
            "updated_at": snapshot.updated_at.isoformat(),
            "expires_at": snapshot.expires_at.isoformat() if snapshot.expires_at else None,
        }
        self._supabase().table("sessions").upsert(payload).execute()

    def wipe(self, session_uuid: str) -> bool:
        self._supabase().table("sessions").delete().eq(
            "session_uuid", session_uuid
        ).execute()
        return True


__all__ = [
    "InMemorySessionStore",
    "SessionSnapshot",
    "SessionStore",
    "SupabaseSessionStore",
]
