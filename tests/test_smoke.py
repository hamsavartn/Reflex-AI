"""End-to-end smoke test: the full two-queue loop on the virtual clock.

Flow: manifest → partial chunk (ack expected) → end-of-turn chunk → read-only
tool call → tool result → final response carrying the state snapshot.
"""
from __future__ import annotations

import pytest

from agent.protocol.events import TextChunk
from tests.conftest import eot, manifest_event


@pytest.mark.skip(reason="legacy v1.1 scaffold (internal test infra, pre-pivot); "
                         "the FDB-v3 agent is tested by fdb_v3_data_val runs instead")
async def test_full_loop_text_scenario(make_world):
    world = make_world("smoke")
    world.deliver(manifest_event())
    world.deliver(TextChunk(text="book a flight"), delay_ms=100)
    world.deliver(eot("book a flight to Delhi"), delay_ms=2500)
    await world.settle()
    await world.stop()

    kinds = [e["kind"] for e in world.trace.entries]

    # floor management: backchannel on the partial chunk
    partial = [e for e in world.trace.of_kind("action_out") if e.get("text") == "Mm-hmm."]
    assert partial, "no ack filler on partial chunk"
    assert partial[0]["ts_ms"] <= 100 + 50, "ack not within fast-path budget"

    # read-only tool executed through the mock environment
    assert world.trace.first("mock_tool_started") is not None
    assert world.trace.first("mock_tool_started")["tool"] == "flight_search"
    assert world.trace.first("mock_tool_completed") is not None

    # final response with a valid snapshot
    final = [e for e in world.trace.of_kind("action_out") if e["type"] == "final_response"]
    assert final, "no final response"
    snap = final[0]
    assert snap["ts_ms"] < 60000

    # trace is strict JSONL and every record has ts + kind
    for e in world.trace.entries:
        assert "kind" in e and "ts_ms" in e


async def test_interrupt_bumps_generation_and_cancels(make_world):
    world = make_world("interrupt")
    world.deliver(manifest_event())
    world.deliver(eot("find flights to Goa"), delay_ms=100)
    # let the search get in flight
    from agent.protocol.events import Interruption

    world.deliver(Interruption(reason="user_barge_in"), delay_ms=300)
    await world.settle()
    await world.stop()

    entries = world.trace.entries
    assert any(e["kind"] == "interrupt" for e in entries), "no interrupt trace"
    assert any(e["kind"] == "cancel_superseded" for e in entries), "no superseded cancellation"
    assert any(e["kind"] == "mock_tool_cancelled" for e in entries), "environment did not cancel the tool timer"
