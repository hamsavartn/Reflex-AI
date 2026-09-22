"""LLM adapter interface — the slow-path brain sits behind this seam so the
hosted/local/mock choice is swappable (BUILD_PLAN §3.2, D3). Phase 3 fills
the implementations; tests always use the deterministic mock."""
from __future__ import annotations

from typing import Any, Optional, Protocol

from pydantic import BaseModel, Field


class Plan(BaseModel):
    """What the slow path decided for the current turn."""

    intent: Optional[str] = None
    slots: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)  # {tool, args}
    spoken: str = ""
    clarify: bool = False


class LLMAdapter(Protocol):
    async def plan(
        self,
        transcript: str,
        snapshot: dict[str, Any],
        tools: list[dict[str, Any]],
    ) -> Plan: ...


class MockLLM:
    """Deterministic planner for tests — mirrors the Phase-0 stub rules."""

    async def plan(self, transcript: str, snapshot: dict, tools: list) -> Plan:
        low = transcript.lower()
        if "flight" in low or "fly" in low:
            import re

            m = re.search(r"\bto\s+([a-z][a-z ]{2,20})", low)
            return Plan(intent="flight_search", slots={"destination": (m.group(1).strip().title() if m else "Goa")})
        return Plan(intent="unknown")
