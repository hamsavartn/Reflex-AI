"""Environment glue: plays the mock-environment side of the two-queue contract.

Reads the agent's actions from the output queue, executes tool calls via
MockTools (virtual-clock completions, cancellation-aware), and feeds tool
results back into the agent's input queue — mirroring the official kit's
"asynchronous mock tool responses" and "complete event/action trace logging"
(BUILD_PLAN Part 1, guide §4).
"""
from __future__ import annotations

import asyncio

from agent.protocol.events import CancelCalls, ToolCall
from harness.mocktools import MockTools


class Environment:
    def __init__(self, in_q: asyncio.Queue, out_q: asyncio.Queue, clock, trace, seed: int = 7) -> None:
        self.in_q = in_q
        self.out_q = out_q
        self.clock = clock
        self.trace = trace
        self.tools = MockTools(clock, on_result=lambda r: self.in_q.put_nowait(r), trace=trace, seed=seed)

    async def run(self) -> None:
        while True:
            action = await self.out_q.get()
            if action is None:  # poison pill
                break
            if isinstance(action, ToolCall):
                self.tools.execute(action)
            elif isinstance(action, CancelCalls):
                for cid in action.call_ids:
                    self.tools.cancel(cid, action.reason)
            # fillers / clarifications / final responses are agent-side outputs;
            # the agent already traced them. Nothing for the environment to do.
