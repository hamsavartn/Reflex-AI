"""Schema-driven, generation-numbered, cancellation-safe tool executor.

This is the heart of Interruption Recovery (35%) and Safety & Protocol (10%).
Hardening per external review, BUILD_PLAN Part 8:

  §8.2.1  registry-before-yield — the intent is recorded synchronously,
          BEFORE the first await that transmits the call.
  §8.2.2  state-modifying records survive cancellation as PENDING_CONFIRMATION
          and keep blocking duplicates (no double-booking on resume).
  §8.2.3  DONE records act as an idempotent result cache.
  §8.2.4  read-only records are dropped on cancellation (no side effects).
  §8.1    registry mutations contain no `await` — atomic under the event loop.
"""
from __future__ import annotations

import asyncio
import json
from enum import Enum
from typing import Any, Optional

from agent.protocol.events import CancelCalls, ToolCall, ToolResult, new_id
from agent.protocol.manifests import Manifest


class RecordState(str, Enum):
    SENT = "sent"
    DONE = "done"
    FAILED = "failed"
    PENDING_CONFIRMATION = "pending_confirmation"


class DuplicateStateCall(RuntimeError):
    """A state-modifying call with identical intent+params is already
    in-flight, done, or pending confirmation. Safety 10% invariant."""


def norm_key(tool: str, args: dict[str, Any]) -> str:
    return tool + ":" + json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)


class Record:
    __slots__ = ("tool", "key", "call_id", "generation", "state_modifying", "state", "result", "future")

    def __init__(self, tool: str, key: str, call_id: str, generation: int, state_modifying: bool) -> None:
        self.tool = tool
        self.key = key
        self.call_id = call_id
        self.generation = generation
        self.state_modifying = state_modifying
        self.state = RecordState.SENT
        self.result: Optional[ToolResult] = None
        self.future: Optional[asyncio.Future] = None


class ToolExecutor:
    def __init__(self, manifest: Manifest, out_q: asyncio.Queue, trace=None, clock=None) -> None:
        self.manifest = manifest
        self.out_q = out_q
        self.trace = trace
        self.clock = clock
        self._records: dict[str, Record] = {}  # call_id -> Record
        self._by_key: dict[str, Record] = {}   # normalized intent key -> Record

    def _now(self) -> int:
        return self.clock.now_ms if self.clock is not None else 0

    # ---------------------------------------------------------- registry (sync-only)

    def _register(self, tool: str, args: dict[str, Any], generation: int) -> Record:
        """Sync critical section: no await between entry and record creation."""
        spec = self.manifest.spec(tool)  # raises UnknownTool for unseen tools
        key = norm_key(tool, args)
        prev = self._by_key.get(key)
        if spec.state_modifying and prev is not None and prev.state in (
            RecordState.SENT,
            RecordState.DONE,
            RecordState.PENDING_CONFIRMATION,
        ):
            if self.trace:
                self.trace.log(
                    "duplicate_state_call_blocked", self._now(), tool=tool, key=key, prior_state=prev.state.value
                )
            raise DuplicateStateCall(f"{tool} {key} already {prev.state.value}")
        rec = Record(tool, key, new_id("call"), generation, spec.state_modifying)
        self._records[rec.call_id] = rec
        self._by_key[key] = rec
        if self.trace:
            self.trace.log(
                "registry_record",
                self._now(),
                call_id=rec.call_id,
                tool=tool,
                key=key,
                state_modifying=spec.state_modifying,
                generation=generation,
            )
        return rec

    # ---------------------------------------------------------- call path

    async def call(self, tool: str, args: dict[str, Any], generation: int) -> ToolResult:
        rec = self._register(tool, args, generation)  # sync — before any yield
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        rec.future = fut
        self.out_q.put_nowait(  # unbounded queue: no yield between register + transmit
            ToolCall(call_id=rec.call_id, tool=tool, args=args, generation=generation)
        )
        try:
            return await fut  # cancellation lands here
        except asyncio.CancelledError:
            self._on_cancelled(rec)
            raise

    def _on_cancelled(self, rec: Record) -> None:
        """Sync critical section (§8.1/§8.2)."""
        rec.future = None
        if rec.state_modifying and rec.state is RecordState.SENT:
            # transmitted, unconfirmed: external side effect may have happened.
            rec.state = RecordState.PENDING_CONFIRMATION
            self._log(rec, "record_pending_confirmation")
        else:
            # read-only: safe to drop entirely (§8.2.4)
            self._records.pop(rec.call_id, None)
            if self._by_key.get(rec.key) is rec:
                self._by_key.pop(rec.key, None)
            self._log(rec, "record_dropped_readonly")

    # ---------------------------------------------------------- result path

    def handle_result(self, result: ToolResult) -> None:
        """Called by the agent pump for every ToolResult event. Late results for
        cancelled calls are recognized as stale and never wake anything (§8.2)."""
        rec = self._records.get(result.call_id)
        if rec is None:
            self._log(None, "stale_result_dropped", call_id=result.call_id, generation=result.generation)
            return
        fut = rec.future
        if fut is not None and not fut.done():
            fut.set_result(result)
        rec.result = result
        rec.future = None
        rec.state = RecordState.DONE if result.ok else RecordState.FAILED
        self._log(rec, "record_resolved", ok=result.ok)

    # ---------------------------------------------------------- interruption

    def in_flight_before(self, generation: int) -> list[Record]:
        return [
            r
            for r in self._records.values()
            if r.state is RecordState.SENT and r.generation < generation
        ]

    def cancel_superseded(self, generation: int, reason: str) -> list[str]:
        """Sync emission + cancellation of every in-flight call older than the
        new generation (guide: 'promptly cancel superseded in-flight tool
        calls'). Cancelled state calls become PENDING_CONFIRMATION via the
        CancelledError path."""
        stale = self.in_flight_before(generation)
        if not stale:
            return []
        ids = [r.call_id for r in stale]
        self.out_q.put_nowait(CancelCalls(call_ids=ids, reason=reason))
        for r in stale:
            if r.future is not None and not r.future.done():
                r.future.cancel()
        self._log(None, "cancel_superseded", call_ids=ids, reason=reason, new_generation=generation)
        return ids

    # ---------------------------------------------------------- planner helpers

    def cached_result(self, tool: str, args: dict[str, Any]) -> Optional[ToolResult]:
        rec = self._by_key.get(norm_key(tool, args))
        if rec is not None and rec.state is RecordState.DONE and rec.result is not None:
            return rec.result
        return None

    def has_pending_state_call(self, tool: str, args: dict[str, Any]) -> bool:
        rec = self._by_key.get(norm_key(tool, args))
        return rec is not None and rec.state in (RecordState.SENT, RecordState.PENDING_CONFIRMATION)

    # ---------------------------------------------------------- misc

    def _log(self, rec: Optional[Record], kind: str, **fields: Any) -> None:
        if self.trace:
            self.trace.log(kind, self._now(), call_id=rec.call_id if rec else None, **fields)
