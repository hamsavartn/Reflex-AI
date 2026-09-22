"""Session-scoped state: the slot store and state snapshots.

Guide §6: "Session-scoped memory only (no cross-session caching)" — one store
per session object, nothing persisted. Snapshot/slot mutations contain no
`await`, so they are atomic under the single-threaded event loop even when a
task is cancelled mid-flight (BUILD_PLAN §8.1, external review §4.2).
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class StateSnapshot(BaseModel):
    generation: int
    turn_id: Optional[str] = None
    intent: Optional[str] = None
    slots: dict[str, Any] = Field(default_factory=dict)


class SessionState:
    """The single mutable session store. Sync-only critical sections."""

    def __init__(self) -> None:
        self.generation: int = 0
        self.intent: Optional[str] = None
        self.slots: dict[str, Any] = {}

    def bump_generation(self, reason: str = "interrupt") -> int:
        # sync-only: atomic; no await can land inside
        self.generation += 1
        return self.generation

    def set_intent(self, intent: Optional[str]) -> None:
        self.intent = intent

    def set_slot(self, key: str, value: Any) -> None:
        self.slots[key] = value

    def clear_slot(self, key: str) -> None:
        self.slots.pop(key, None)

    def snapshot(self, turn_id: Optional[str] = None) -> StateSnapshot:
        # dict(self.slots) — copy taken synchronously, never a half-mutated view
        return StateSnapshot(
            generation=self.generation,
            turn_id=turn_id,
            intent=self.intent,
            slots=dict(self.slots),
        )
