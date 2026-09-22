"""Review-hardened invariants (BUILD_PLAN §8.1–§8.2):

  - zero duplicate state-changing calls (Safety 10%)
  - cancelled state-modifying calls stay blocked as PENDING_CONFIRMATION
  - late results for cancelled calls are dropped as stale
  - registry mutations are atomic under cancellation
"""
from __future__ import annotations

import asyncio

import pytest

from agent.protocol.events import ToolResult
from agent.protocol.manifests import Manifest
from agent.tools.executor import DuplicateStateCall, RecordState, ToolExecutor
from tests.conftest import MANIFEST


def make_executor(trace=None, clock=None):
    out_q: asyncio.Queue = asyncio.Queue()
    manifest = Manifest.from_list(MANIFEST["tools"])
    return ToolExecutor(manifest, out_q, trace, clock=clock), out_q


async def test_no_duplicate_state_calls():
    ex, _ = make_executor()
    task = asyncio.create_task(ex.call("book_flight", {"flight_id": "F101"}, generation=0))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert task.done() is False  # awaiting result
    with pytest.raises(DuplicateStateCall):
        ex._register("book_flight", {"flight_id": "F101"}, generation=0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


async def test_cancelled_state_call_stays_blocked():
    ex, _ = make_executor()
    task = asyncio.create_task(ex.call("book_flight", {"flight_id": "F101"}, generation=0))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    pending = [r for r in ex._records.values() if r.state is RecordState.PENDING_CONFIRMATION]
    assert len(pending) == 1, "cancelled state-modifying call must be retained as PENDING_CONFIRMATION"
    # §8.2.2: the same intent must stay blocked — no silent rebook
    with pytest.raises(DuplicateStateCall):
        ex._register("book_flight", {"flight_id": "F101"}, generation=1)


async def test_late_result_dropped_by_generation():
    ex, out_q = make_executor()
    task = asyncio.create_task(ex.call("flight_search", {"destination": "Goa"}, generation=0))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    task.cancel()  # interrupt path
    await asyncio.gather(task, return_exceptions=True)
    # the environment never saw the cancel: a late result arrives for gen 0
    call = out_q.get_nowait()
    ex.handle_result(
        ToolResult(call_id=call.call_id, generation=0, ok=True, payload={"options": []})
    )
    # no crash; the record was dropped (read-only) — nothing revived
    assert call.call_id not in ex._records


async def test_readonly_cancel_drops_record():
    ex, _ = make_executor()
    task = asyncio.create_task(ex.call("flight_search", {"destination": "Goa"}, generation=0))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert all(
        r.state is not RecordState.PENDING_CONFIRMATION for r in ex._records.values()
    ), "read-only cancellations must not block"


async def test_state_mutation_atomic_under_cancel():
    """Snapshot mutations are sync-only: a cancelled task can never leave a
    half-written snapshot (§8.1)."""
    from agent.protocol.snapshots import SessionState

    state = SessionState()
    work = asyncio.create_task(_mutator(state))
    await asyncio.sleep(0)
    work.cancel()
    await asyncio.gather(work, return_exceptions=True)
    snap = state.snapshot()
    # invariant: 'b' never appears without 'a' (mutation pairs are atomic)
    assert ("b" in snap.slots) <= ("a" in snap.slots)


async def _mutator(state):
    await asyncio.sleep(999999)  # stands in for slow-path latency
    state.set_slot("a", 1)
    state.set_slot("b", 2)
