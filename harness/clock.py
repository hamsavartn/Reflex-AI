"""Deterministic virtual clock — the agent never touches wall-clock time.

The harness schedules completions on the clock; `advance_to` fires everything
due in strict (time, insertion) order. Coroutines await `sleep()`, which
resolves when the clock advances past the deadline — a 120 s scenario replays
in milliseconds of real compute (BUILD_PLAN §3.2 decision 6; review §7.1).
"""
from __future__ import annotations

import asyncio
import heapq
import itertools
from typing import Callable, Optional, Tuple


class VirtualClock:
    def __init__(self) -> None:
        self._now = 0
        self._seq = itertools.count()
        # heaps of (due_ms, seq, payload); seq breaks ties FIFO
        self._timers: list[tuple[int, int, Callable[[], None]]] = []
        self._sleepers: list[tuple[int, int, asyncio.Future]] = []

    @property
    def now_ms(self) -> int:
        return self._now

    def schedule(self, delay_ms: int, fn: Callable[[], None]) -> Tuple[int, int]:
        """Run fn at now + delay. Returns a handle usable with cancel()."""
        item = (self._now + delay_ms, next(self._seq), fn)
        heapq.heappush(self._timers, item)
        return item

    def cancel(self, handle: Tuple[int, int]) -> bool:
        """Remove a scheduled timer by its (due_ms, seq) handle. True if removed."""
        for i, item in enumerate(self._timers):
            if item[0] == handle[0] and item[1] == handle[1]:
                del self._timers[i]
                heapq.heapify(self._timers)
                return True
        return False

    async def sleep(self, delay_ms: int) -> None:
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        item = (self._now + delay_ms, next(self._seq), fut)
        heapq.heappush(self._sleepers, item)
        try:
            await fut
        except asyncio.CancelledError:
            self._sleepers = [s for s in self._sleepers if s[2] is not fut]
            heapq.heapify(self._sleepers)
            raise

    def advance_to(self, t_ms: int) -> int:
        """Fire everything due <= t_ms in (time, seq) order. Returns fired count."""
        fired = 0
        while True:
            due: Optional[tuple[int, int]] = None
            if self._timers:
                due = (self._timers[0][0], self._timers[0][1])
            if self._sleepers:
                s = (self._sleepers[0][0], self._sleepers[0][1])
                due = s if due is None or s < due else due
            if due is None or due[0] > t_ms:
                break
            self._now = max(self._now, due[0])
            # fire the single earliest item (timers first at identical seq)
            if self._timers and (self._timers[0][0], self._timers[0][1]) == due:
                _, _, fn = heapq.heappop(self._timers)
                fn()
            else:
                _, _, fut = heapq.heappop(self._sleepers)
                if not fut.done():
                    fut.set_result(None)
            fired += 1
        self._now = max(self._now, t_ms)
        return fired

    def advance_by(self, delta_ms: int) -> int:
        return self.advance_to(self._now + delta_ms)

    def pending(self) -> int:
        """Scheduled-but-unfired timers + unresolved sleepers."""
        return len(self._timers) + len(self._sleepers)
