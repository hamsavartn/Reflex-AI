"""Shared fixtures: a wired agent + environment + virtual clock + trace."""
from __future__ import annotations

import asyncio

import pytest

from agent.core.agent import Agent
from agent.protocol.events import TextChunk, ToolManifest
from agent.protocol.manifests import Manifest
from harness.clock import VirtualClock
from harness.environment import Environment
from harness.trace import Trace

MANIFEST = {
    "tools": [
        {"name": "flight_search", "description": "Search flights", "mutates_state": False},
        {"name": "book_flight", "description": "Book a flight", "mutates_state": True},
        {"name": "create_ticket", "description": "Create support ticket", "mutates_state": True},
        {"name": "lookup_manual", "description": "Manual lookup", "mutates_state": False},
    ]
}


@pytest.fixture
def clock() -> VirtualClock:
    return VirtualClock()


@pytest.fixture
def make_world(tmp_path):
    """Factory: (world) with agent, environment, queues, trace wired together."""

    def _make(trace_name: str = "trace"):
        in_q: asyncio.Queue = asyncio.Queue()
        out_q: asyncio.Queue = asyncio.Queue()
        trace = Trace(tmp_path / f"{trace_name}.jsonl")
        clock = VirtualClock()
        manifest = Manifest.from_list(MANIFEST["tools"])
        agent = Agent(manifest, in_q, out_q, trace, clock=clock)
        env = Environment(in_q, out_q, clock, trace)
        tasks = [
            asyncio.get_running_loop().create_task(agent.run()),
            asyncio.get_running_loop().create_task(env.run()),
        ]
        return SimpleWorld(clock, in_q, out_q, trace, tasks, agent)

    return _make


class SimpleWorld:
    def __init__(self, clock, in_q, out_q, trace, tasks, agent) -> None:
        self.clock = clock
        self.in_q = in_q
        self.out_q = out_q
        self.trace = trace
        self.tasks = tasks
        self.agent = agent

    def deliver(self, event, delay_ms: int = 0) -> None:
        # schedule on the virtual clock so the agent processes each event at
        # its true virtual time (interleaved with tool completions)
        self.clock.schedule(delay_ms, lambda e=event: self.in_q.put_nowait(e))

    async def settle(self, max_ms: int = 60000, step_ms: int = 25) -> None:
        """Advance the virtual clock until quiet: nothing fires, queues empty."""
        while self.clock.now_ms < max_ms:
            fired = self.clock.advance_by(step_ms)
            for _ in range(4):
                await asyncio.sleep(0)  # yield to agent + env tasks
            if (
                fired == 0
                and self.in_q.empty()
                and self.out_q.empty()
                and self.clock.pending() == 0
            ):
                break

    async def stop(self) -> None:
        self.in_q.put_nowait(None)
        self.out_q.put_nowait(None)
        for t in self.tasks:
            try:
                await asyncio.wait_for(t, timeout=2)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                t.cancel()


def manifest_event() -> ToolManifest:
    return ToolManifest(tools=MANIFEST["tools"])


def eot(text: str, turn: str | None = None) -> TextChunk:
    return TextChunk(text=text, end_of_turn=True, turn_id=turn) if turn else TextChunk(text=text, end_of_turn=True)
