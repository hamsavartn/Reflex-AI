"""Dual-process agent orchestrator (Phase-0/1 scaffold with a deterministic
stub planner; the real LLM adapter lands in Phase 3).

Fast path  : rule-based ack fillers on every user chunk — no LLM in the hot
             path (latency 15%, guide: "responsiveness within a few hundred
             milliseconds").
Slow path  : stub intent/slot extraction → executor calls → final response
             with StateSnapshot. Speculative read-only planning hooks are
             marked for §8.3.
Coordination: generation numbers; interrupts bump the generation and cancel
             superseded in-flight calls (guide §3.2.2; plan §3.2.2).
"""
from __future__ import annotations

import asyncio
import re
from typing import Optional

from agent.protocol.events import (
    AudioClip,
    Event,
    Filler,
    FinalResponse,
    Interruption,
    TextChunk,
    ToolManifest,
    ToolResult,
    VideoFrame,
)
from agent.protocol.manifests import Manifest
from agent.protocol.snapshots import SessionState
from agent.tools.executor import DuplicateStateCall, ToolExecutor


class Agent:
    def __init__(self, manifest: Manifest, in_q: asyncio.Queue, out_q: asyncio.Queue, trace, clock=None) -> None:
        self.manifest = manifest
        self.in_q = in_q
        self.out_q = out_q
        self.trace = trace
        self.clock = clock
        self.state = SessionState()
        self.executor = ToolExecutor(manifest, out_q, trace, clock=clock)
        self._last_turn: Optional[str] = None
        # slow-path tasks by generation: the run loop must stay free to read
        # the input queue (a blocking slow path deadlocks on its own result)
        self._slow_tasks: list[tuple[int, asyncio.Task]] = []

    def _now(self) -> int:
        return self.clock.now_ms if self.clock is not None else 0

    async def _emit(self, action) -> None:
        action.ts_ms = self._now()
        if self.trace:
            self.trace.log("action_out", action.ts_ms, type=action.type, **_summarize(action))
        self.out_q.put_nowait(action)

    async def run(self) -> None:
        while True:
            event: Event = await self.in_q.get()
            if event is None:
                break
            if self.trace:
                self.trace.log("event_in", self._now(), type=event.type, **_summarize(event))
            if isinstance(event, ToolManifest):
                self.manifest = Manifest.from_list(event.tools)
                self.executor.manifest = self.manifest
            elif isinstance(event, TextChunk):
                await self._on_text(event)
            elif isinstance(event, Interruption):
                await self._on_interrupt(event)
            elif isinstance(event, ToolResult):
                self.executor.handle_result(event)
            elif isinstance(event, (AudioClip, VideoFrame)):
                # multimodal grounding runs BEHIND an acknowledgment (guide §3.2.5)
                await self._emit(Filler(text="One moment — taking a look at that.", kind="ack"))
            else:
                await self._emit(
                    Filler(text="Sorry, I didn't catch that — could you repeat?", kind="ack")
                )

    # ------------------------------------------------------------ fast path

    async def _on_text(self, event: TextChunk) -> None:
        self._last_turn = event.turn_id
        if not event.end_of_turn:
            # floor management: immediate backchannel while the user speaks
            await self._emit(Filler(text="Mm-hmm.", kind="ack"))
            # §8.3 hook: speculative READ-ONLY planning may start here
            return
        await self._emit(Filler(text="Got it — one moment.", kind="ack"))
        task = asyncio.create_task(self._slow_path(event))
        self._slow_tasks.append((self.state.generation, task))

    # ------------------------------------------------------------ slow path (stub)

    async def _slow_path(self, event: TextChunk) -> None:
        try:
            await self._slow_path_inner(event)
        except asyncio.CancelledError:
            if self.trace:
                self.trace.log("slow_path_cancelled", self._now(), turn_id=event.turn_id)

    async def _slow_path_inner(self, event: TextChunk) -> None:
        text = event.text.strip()
        intent, slots = _stub_extract(text)
        self.state.set_intent(intent)
        for k, v in slots.items():
            self.state.set_slot(k, v)

        if intent == "flight_search":
            args = {"destination": slots.get("destination", "GOA")}
            try:
                result = await self.executor.call("flight_search", args, generation=self.state.generation)
            except DuplicateStateCall:
                cached = self.executor.cached_result("flight_search", args)
                if cached is None:
                    await self._emit(Filler(text="Still working on that search.", kind="progress"))
                    return
                result = cached
            options = result.payload.get("options", []) if result.ok else []
            if not result.ok:
                await self._emit(
                    FinalResponse(
                        text="The search failed — sorry about that.",
                        snapshot=self.state.snapshot(event.turn_id).model_dump(),
                    )
                )
                return
            first = options[0] if options else {}
            await self._emit(
                FinalResponse(
                    text=f"Cheapest to {args['destination']}: {first.get('airline', '?')} at "
                    f"{first.get('departure', '?')} for ₹{first.get('price', '?')}.",
                    snapshot=self.state.snapshot(event.turn_id).model_dump(),
                )
            )
        else:
            await self._emit(
                FinalResponse(
                    text="I can help search flights right now — what would you like to do?",
                    snapshot=self.state.snapshot(event.turn_id).model_dump(),
                )
            )

    # ------------------------------------------------------------ interruption

    async def _on_interrupt(self, event: Interruption) -> None:
        gen = self.state.bump_generation(event.reason)  # sync, atomic
        # cancel superseded slow-path tasks (their executor calls become
        # PENDING_CONFIRMATION / dropped via the CancelledError path §8.2)
        for tgen, task in list(self._slow_tasks):
            if tgen < gen and not task.done():
                task.cancel()
        self._slow_tasks = [(g, t) for g, t in self._slow_tasks if not t.done()]
        cancelled = self.executor.cancel_superseded(gen, event.reason)
        if self.trace:
            self.trace.log("interrupt", self._now(), new_generation=gen, superseded=cancelled)
        await self._emit(Filler(text="Okay — stopped that. What would you like?", kind="ack"))

    # ------------------------------------------------------------ speculative (reserved)

    def on_partial_chunk(self, text: str) -> None:
        """Reserved for §8.3: speculate read-only calls on partial transcripts.
        State-modifying tools are NEVER speculative (plan §8.3)."""
        raise NotImplementedError


def _stub_extract(text: str) -> tuple[str, dict]:
    low = text.lower()
    if "flight" in low or "fly" in low:
        m = re.search(r"\bto\s+([a-z][a-z ]{2,20})", low)
        dest = m.group(1).strip() if m else "GOA"
        return "flight_search", {"destination": dest.title()}
    return "unknown", {}


def _summarize(event) -> dict:
    if isinstance(event, TextChunk):
        return {"text": event.text, "end_of_turn": event.end_of_turn}
    if isinstance(event, (Filler, FinalResponse)):
        return {"text": event.text}
    if isinstance(event, ToolResult):
        return {"call_id": event.call_id, "generation": event.generation, "ok": event.ok}
    if isinstance(event, ToolManifest):
        return {"tools": [t.get("name") for t in event.tools]}
    return {}
