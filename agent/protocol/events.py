"""Wire-format models for the two-queue interface contract.

Theme 5 guide v1.0.0 §3 (verified word-for-word in extracted/verify_plan.py):
  INPUTS  (agent consumes, timestamped): transcribed text chunks (with
  end-of-turn markers), raw audio clips (WAV), video frames (PNG),
  interruption signals, asynchronous tool results, scenario tool manifests.
  OUTPUTS (agent emits): spoken fillers, non-blocking tool calls (explicit
  call_id), cancellations, clarification requests, final responses carrying
  structured State Snapshots (intent and slot values).
"""
from __future__ import annotations

import uuid
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


# ---------------------------------------------------------------- inputs


class Event(BaseModel):
    """Anything arriving on the agent's input queue."""

    type: str
    ts_ms: int = 0


class TextChunk(Event):
    type: Literal["text_chunk"] = "text_chunk"
    turn_id: str = Field(default_factory=lambda: new_id("turn"))
    text: str
    end_of_turn: bool = False


class AudioClip(Event):
    type: Literal["audio_clip"] = "audio_clip"
    turn_id: str = Field(default_factory=lambda: new_id("turn"))
    wav_path: str  # loaded lazily by the ASR worker (Phase 3)
    end_of_turn: bool = False


class VideoFrame(Event):
    type: Literal["video_frame"] = "video_frame"
    turn_id: str = Field(default_factory=lambda: new_id("turn"))
    png_path: str


class Interruption(Event):
    type: Literal["interruption"] = "interruption"
    reason: str = "user_barge_in"


class ToolResult(Event):
    type: Literal["tool_result"] = "tool_result"
    call_id: str
    generation: int
    ok: bool
    payload: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class ToolManifest(Event):
    type: Literal["tool_manifest"] = "tool_manifest"
    tools: list[dict[str, Any]] = Field(default_factory=list)


EVENT_TYPES: dict[str, type[Event]] = {
    c.model_fields["type"].default: c  # type: ignore[index]
    for c in (TextChunk, AudioClip, VideoFrame, Interruption, ToolResult, ToolManifest)
}


def parse_event(raw: dict[str, Any]) -> Event:
    cls = EVENT_TYPES.get(raw.get("type", ""))
    if cls is None:
        raise ValueError(f"unknown input event type: {raw.get('type')!r}")
    return cls.model_validate(raw)


# ---------------------------------------------------------------- outputs


class Action(BaseModel):
    """Anything the agent emits on its output queue."""

    type: str
    ts_ms: int = 0


class Filler(Action):
    """Fast-path conversational glue: acknowledgments / progress narration.

    Rule-based emissions only — no LLM in the hot path (latency 15%)."""

    type: Literal["filler"] = "filler"
    text: str
    kind: Literal["ack", "progress"] = "ack"


class ClarificationRequest(Action):
    type: Literal["clarification"] = "clarification"
    text: str
    options: list[str] = Field(default_factory=list)


class ToolCall(Action):
    type: Literal["tool_call"] = "tool_call"
    call_id: str = Field(default_factory=lambda: new_id("call"))
    tool: str
    args: dict[str, Any]
    generation: int


class CancelCalls(Action):
    type: Literal["cancel_calls"] = "cancel_calls"
    call_ids: list[str]
    reason: str


class FinalResponse(Action):
    type: Literal["final_response"] = "final_response"
    text: str
    snapshot: dict[str, Any]  # StateSnapshot.model_dump() — intent + slot values
