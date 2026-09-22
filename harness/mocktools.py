"""Mock environment tools with deterministic latency and fault injection.

Guide §4: "Deterministic latency and fault injection for flight search,
booking, ticket creation, and frame-grounded manual lookups." Completions are
scheduled on the virtual clock (never asyncio.sleep) so scenarios replay
deterministically (review §7.1).
"""
from __future__ import annotations

import random
from typing import Any, Callable, Optional

from agent.protocol.events import ToolCall, ToolResult

LATENCY_MS = {
    "flight_search": 1200,
    "book_flight": 2500,
    "create_ticket": 2000,
    "lookup_manual": 900,
}
FAULT_RATE = {  # deterministic seeded injection (0 by default; scenarios opt in)
    "flight_search": 0.0,
    "book_flight": 0.0,
    "create_ticket": 0.0,
    "lookup_manual": 0.0,
}


class MockTools:
    def __init__(
        self,
        clock,
        on_result: Callable[[ToolResult], None],
        trace=None,
        seed: int = 7,
        latency_override: Optional[dict[str, int]] = None,
        fault_rate: Optional[dict[str, float]] = None,
    ) -> None:
        self.clock = clock
        self.on_result = on_result
        self.trace = trace
        self.rng = random.Random(seed)
        self.latency = dict(LATENCY_MS)
        if latency_override:
            self.latency.update(latency_override)
        self.fault_rate = dict(FAULT_RATE)
        if fault_rate:
            self.fault_rate.update(fault_rate)
        self._pending: dict[str, tuple[int, int]] = {}
        self._counter = 0

    def execute(self, call: ToolCall) -> None:
        latency = self.latency.get(call.tool, 800)
        will_fail = self.rng.random() < self.fault_rate.get(call.tool, 0.0)
        handle = self.clock.schedule(latency, lambda: self._complete(call, will_fail))
        self._pending[call.call_id] = handle
        if self.trace:
            self.trace.log(
                "mock_tool_started",
                self.clock.now_ms,
                call_id=call.call_id,
                tool=call.tool,
                generation=call.generation,
                latency_ms=latency,
            )

    def cancel(self, call_id: str, reason: str) -> bool:
        handle = self._pending.pop(call_id, None)
        if handle is not None and self.clock.cancel(handle):
            if self.trace:
                self.trace.log("mock_tool_cancelled", self.clock.now_ms, call_id=call_id, reason=reason)
            return True
        return False

    def _complete(self, call: ToolCall, fail: bool) -> None:
        self._pending.pop(call.call_id, None)
        payload = {} if fail else self._payload(call)
        result = ToolResult(
            call_id=call.call_id,
            generation=call.generation,
            ok=not fail,
            payload=payload,
            error=None if not fail else "injected_fault",
        )
        if self.trace:
            self.trace.log(
                "mock_tool_completed",
                self.clock.now_ms,
                call_id=call.call_id,
                tool=call.tool,
                ok=result.ok,
            )
        self.on_result(result)

    def _payload(self, call: ToolCall) -> dict[str, Any]:
        self._counter += 1
        tool = call.tool
        if tool == "flight_search":
            dest = str(call.args.get("destination", "GOA")).upper()
            return {
                "options": [
                    {"flight_id": f"F{self._counter}01", "airline": "IndiGo", "departure": "06:20", "price": 5480},
                    {"flight_id": f"F{self._counter}02", "airline": "Air India", "departure": "11:45", "price": 7120},
                ],
                "destination": dest,
            }
        if tool == "book_flight":
            return {
                "booking_id": f"BK{1000 + self._counter}",
                "flight_id": call.args.get("flight_id", "F001"),
                "status": "confirmed",
            }
        if tool == "create_ticket":
            return {"ticket_id": f"TK{1000 + self._counter}", "status": "created"}
        if tool == "lookup_manual":
            return {
                "excerpt": "To resolve Wi-Fi drops: Settings > Connections > Wi-Fi > Advanced > Intelligent Wi-Fi off.",
                "topic": call.args.get("topic", "wifi"),
            }
        return {"echo": call.args}
