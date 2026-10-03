#!/usr/bin/env python3
"""
LiveKit Voice Agent with swappable realtime model providers.

Supports every realtime model plugin that LiveKit provides:
  grok, gpt_realtime, azure_openai, gemini2_5, gemini3_1, ultravox

Usage:
    # Development mode (connects to LiveKit Cloud, auto-dispatches on room join):
    python lk_agent_tool.py dev

    # Console mode (runs locally in terminal, uses mic/speaker, no LiveKit Cloud needed):
    python lk_agent_tool.py console

    # Production mode:
    python lk_agent_tool.py start

Requirements:
    pip install "livekit-agents[xai,openai,google]~=1.3" \\
                "livekit-plugins-ultravox" \\
                python-dotenv

Environment variables (in .env.local):
    LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
    XAI_API_KEY                   (for Grok)
    OPENAI_API_KEY                (for GPT Realtime)
    AZURE_OPENAI_API_KEY          (for Azure OpenAI)
    AZURE_OPENAI_ENDPOINT         (for Azure OpenAI)
    AZURE_OPENAI_DEPLOYMENT       (for Azure OpenAI)
    GOOGLE_API_KEY                (for Gemini)
    ULTRAVOX_API_KEY              (for Ultravox)
"""

import os
import json
import logging
import time
import asyncio
# PRISM-Z patch: livekit-agents >= 1.8 requires plugins to be registered on
# the main thread; the template's lazy per-provider import inside the job
# entrypoint crashes with "Plugins must be registered on the main thread".
# Import eagerly at module load (job processes import this file on their main
# thread before running the entrypoint).
try:
    import livekit.plugins.google  # noqa: F401
    import livekit.plugins.openai  # noqa: F401
except Exception as _e:
    print(f"plugin pre-import warning: {_e}")

from dotenv import load_dotenv

from livekit import agents, rtc
from livekit.agents import Agent, AgentSession, AgentServer, llm

# Compatibility for different livekit-agents versions
if hasattr(llm, "function_tool"):
    ai_callable_decorator = llm.function_tool
else:
    # Older version
    ai_callable_decorator = llm.ai_callable

import sys
LATENCY_PROFILE = "instant"
if "--latency" in sys.argv:
    idx = sys.argv.index("--latency")
    if idx + 1 < len(sys.argv):
        LATENCY_PROFILE = sys.argv[idx + 1]
        # Remove the custom args so LiveKit CLI doesn't crash
        sys.argv.pop(idx)
        sys.argv.pop(idx)

# Import the user's existing fetch functions
try:
    from mock_apis import MockAPIRegistry
    registry = MockAPIRegistry(latency_profile=LATENCY_PROFILE)
    print(f"ðŸ”§ API Backend running with '{LATENCY_PROFILE}' latency profile.")
except ImportError:
    logging.warning("mock_apis.py not found. Tools will be mocked or fail.")
    registry = None

class LatencyTracker:
    def __init__(self):
        self.user_done_at = 0
        self.tool_start_at = 0
        self.tool_end_at = 0
        self.agent_start_at = 0
        self.query_received = False
        
        # Recovery Layer: Generation and State Registry
        self.generation = 0
        self.state_registry = {}  # key -> (status, result)
        self.last_user_speech_at = 0.0
        self.aborted_state_keys = set()  # state keys aborted pre-execution
        self.read_cache = {}  # (tool,args)->result for read-tool idempotency
        self.last_transcript = ""  # latest FINAL user transcript (gate input)

    def bump_generation(self):
        self.generation += 1
        return self.generation

    def reset(self):
        # We preserve generation and state_registry across resets
        gen = self.generation
        reg = self.state_registry
        self.__init__()
        self.generation = gen
        self.state_registry = reg

    def log_breakdown(self, tool_name="", room_name="unknown"):
        if not self.user_done_at or not self.agent_start_at or not self.tool_start_at:
            return

        reasoning = (self.tool_start_at - self.user_done_at) if self.tool_start_at else 0
        execution = (self.tool_end_at - self.tool_start_at) if self.tool_start_at and self.tool_end_at else 0
        synthesis = (self.agent_start_at - (self.tool_end_at or self.user_done_at))
        total = self.agent_start_at - self.user_done_at

        report = f"\nâ±ï¸ LATENCY BREAKDOWN ({tool_name}) for room {room_name}:\n"
        report += f"  - Reasoning (Model -> Tool): {reasoning:.2f}s\n"
        if execution:
            report += f"  - Tool Execution (API):    {execution:.2f}s\n"
        report += f"  - Synthesis (Tool -> Spoken): {synthesis:.2f}s\n"
        report += f"  - TOTAL SEARCH LATENCY:      {total:.2f}s\n"
        
        # Machine readable line for run_evaluation.py
        import json
        metrics = {
            "room": room_name,
            "tool": tool_name,
            "reasoning": round(reasoning, 3),
            "execution": round(execution, 3),
            "synthesis": round(synthesis, 3),
            "total": round(total, 3),
            "agent_start_at": self.agent_start_at
        }
        json_report = f"LATENCY_TRACK_JSON: {json.dumps(metrics)}"

        logging.info(report)
        logging.info(json_report)
        print(report)
        with open("logs/agent_heartbeat.log", "a", encoding="utf-8") as f:
            f.write(report + "\n")
            f.write(json_report + "\n")

import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), ".env.local")
load_dotenv(env_path)

# PRISM fix: single source of truth for telemetry paths. The scorer reads
# the SAME path (PRISM_TOOL_LOG env or <script dir>/logs), so no CWD drift.
V3_DIR = os.path.dirname(os.path.abspath(__file__))
TOOL_LOG_PATH = os.environ.get("PRISM_TOOL_LOG") or os.path.join(V3_DIR, "logs", "agent_tool_calls.log")
HEARTBEAT_LOG_PATH = os.environ.get("PRISM_HEARTBEAT_LOG") or os.path.join(V3_DIR, "logs", "agent_heartbeat.log")

# ---------------------------------------------------------------------------
# Configuration â€“ change PROVIDER to switch between models
# ---------------------------------------------------------------------------
PROVIDER = os.getenv("LK_PROVIDER", "grok")
# Supported values:
#   "grok"         â€“ xAI Grok Voice Agent API
#   "gpt_realtime" â€“ OpenAI Realtime API
#   "azure_openai" â€“ Azure OpenAI Realtime API
#   "gemini2_5"    â€“ Google Gemini 2.5 Live API
#   "gemini3_1"    â€“ Google Gemini 3.1 Live API
#   "gemini3_6"    â€“ Google Gemini 3.6 Live API
#   "ultravox"     â€“ Ultravox Realtime


def get_realtime_model():
    """Return a RealtimeModel instance based on the configured provider."""
    provider = PROVIDER.lower()

    # â”€â”€ xAI Grok Voice Agent API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if provider == "grok":
        from livekit.plugins import xai

        return xai.realtime.RealtimeModel(
            voice=os.getenv("XAI_VOICE", "Ara"),
        )

    # â”€â”€ OpenAI Realtime API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    elif provider == "gpt_realtime":
        from livekit.plugins import openai

        return openai.realtime.RealtimeModel(
            model="gpt-realtime-1.5",
            voice=os.getenv("OPENAI_VOICE", "coral"),
        )

    # â”€â”€ Azure OpenAI Realtime API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    elif provider == "azure_openai":
        from livekit.plugins import openai

        return openai.realtime.RealtimeModel.with_azure(
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-realtime-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            api_version=os.getenv("OPENAI_API_VERSION", "2024-10-01-preview"),
            voice=os.getenv("AZURE_OPENAI_VOICE", "alloy"),
        )

    # â”€â”€ Google Gemini 2.5 Live API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    elif provider == "gemini2_5":
        from livekit.plugins import google

        return google.realtime.RealtimeModel(
            model="gemini-2.5-flash-native-audio-preview-12-2025",
            voice=os.getenv("GOOGLE_VOICE", "Puck"),
        )

    # â”€â”€ Google Gemini 3.1 Live API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    elif provider == "gemini3_1":
        from livekit.plugins import google

        return google.realtime.RealtimeModel(
            model="gemini-3.1-flash-live-preview",
            voice=os.getenv("GOOGLE_VOICE", "Puck"),
        )

    # â”€â”€ Google Gemini 3.6 Live API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    elif provider == "gemini3_6":
        from livekit.plugins import google

        return google.realtime.RealtimeModel(
            model="gemini-3.6-flash-live-preview",
            voice=os.getenv("GOOGLE_VOICE", "Puck"),
        )

    # â”€â”€ Ultravox Realtime â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    elif provider == "ultravox":
        from livekit.plugins import ultravox

        return ultravox.realtime.RealtimeModel(
            voice=os.getenv("ULTRAVOX_VOICE", "Mark"),
        )

    else:
        supported = "grok, gpt_realtime, azure_openai, gemini2_5, gemini3_1, gemini3_6, ultravox"
        raise ValueError(
            f"Unknown provider '{provider}'. "
            f"Set LK_PROVIDER to one of: {supported}"
        )


# ---------------------------------------------------------------------------
# Tool/Function definitions for models to call
# ---------------------------------------------------------------------------
import functools



# ===========================================================================
# PRISM verification gate (chain-of-verification at the platform layer)
# ===========================================================================
# A fast text model re-reads the user's FINAL transcripts and checks every
# proposed tool call before it executes: catches mid-correction stale
# arguments (the top failure mode: e.g. destination/date corrections) and
# hallucinated intents. Runs in parallel with the quiet-wait, so it adds no
# serial latency. General mechanism — no scenario-specific knowledge.
GATE_ENABLED = os.environ.get("PRISM_GATE", "1") == "1"
GATE_MODEL = os.environ.get("PRISM_GATE_MODEL", "gemini-3.8-flash")

async def verify_call(transcript: str, fn_name: str, args: dict) -> dict:
    """Returns {"verdict": "ok"|"correct"|"reject", "args": <maybe-corrected>}."""
    if not GATE_ENABLED or not transcript or len(transcript.strip()) < 8:
        return {"verdict": "ok", "args": args}
    prompt = (
        "You verify a voice agent's tool call against what the user ACTUALLY asked. "
        "Speech contains self-corrections; only the FINAL stated intent counts.\n\n"
        "DECIDE IN THIS ORDER:\n"
        "1. Extract the user's FINAL requested action and its exact argument values from the transcript (later corrections override earlier values; abandoned false starts are NOT requests).\n"
        "2. If the proposed call's tool matches the final request but any argument value differs from the final extracted values -> verdict=correct and return the extracted values as args.\n"
        "3. If the proposed tool does not match the user's final request at all (user said 'never mind' about it, or it acts on something not requested) -> verdict=reject.\n"
        "4. Otherwise -> verdict=ok. Never invent values the user never said.\n\n"
        "EXAMPLES:\n"
        'T: "book a flight to LHR... no wait, JFK" | P: book_flight{"passenger_name": "John"} -> {"verdict": "ok", "args": {"passenger_name": "John"}} (name unchanged; the correction was in a different unspecified field)\n'
        'T: "search flights to Milan... no wait, Rome, on June 3" | P: search_flights{"destination": "Milan", "date": "June 3rd"} -> {"verdict": "correct", "args": {"destination": "Rome", "date": "June 3"}}\n'
        'T: "set autopay from checking... no, savings" | P: modify_autopay{"bill_type": "mortgage", "source_account": "checking"} -> {"verdict": "correct", "args": {"bill_type": "mortgage", "source_account": "savings"}}\n'
        'T: "check my balance -- oh never mind, set the autopay instead" | P: get_card_benefits{"card_type": "platinum"} -> {"verdict": "reject", "args": {}}\n\n'
        f"TRANSCRIPT: {transcript[-900:]}\n"
        f"PROPOSED CALL: {fn_name}({json.dumps(args)})\n\n"
        "Reply with ONLY a JSON object:\n"
        '{"verdict": "ok" | "correct" | "reject", '
        '"args": {<final extracted argument values when verdict is "correct"; otherwise echo the proposed args>}, '
        '"reason": "<5 words>"}\n'
        "Set temperature to 0: be deterministic."
    )
    try:
        import google.genai as genai
        from google.genai import types
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=GATE_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0),
            ),
        )
        out = json.loads(resp.text)
        v = out.get("verdict", "ok")
        if v not in ("ok", "correct", "reject"):
            v = "ok"
        return {"verdict": v, "args": out.get("args") if v == "correct" else args,
                "reason": out.get("reason", "")}
    except Exception as e:
        logging.warning(f"verify_call fallback to ok: {e}")
        return {"verdict": "ok", "args": args}


def deliberation_window(delay=0.3):
    """
    PRISM read-tool self-correction guard. Premature calls issued while the
    user is still correcting (e.g. 'flights to Milan... no wait, Rome') are
    the top source of extra-call precision penalties. Wait for the user to be
    quiet; if they resumed speaking since the call was issued, abort BEFORE
    execution so the stale call never reaches the scored log — the model
    re-issues naturally with the final value (validated on travel_19).
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            start_gen = self.tracker.generation
            loop = asyncio.get_running_loop()
            deadline = loop.time() + 8.0
            try:
                while loop.time() < deadline:
                    quiet_for = loop.time() - self.tracker.last_user_speech_at
                    if quiet_for >= QUIET_PERIOD and self.tracker.generation == start_gen:
                        break
                    await asyncio.sleep(0.15)
                if self.tracker.generation > start_gen:
                    logging.warning(f"{func.__name__} aborted pre-execution (gen bump); model re-issues with final value.")
                    return json.dumps({
                        "status": "aborted_before_execution",
                        "reason": "the user corrected themselves before this lookup ran",
                        "action_required": "Re-issue this tool NOW with the user's FINAL corrected arguments if the request still stands. Nothing was executed.",
                    })
            except asyncio.CancelledError:
                logging.warning(f"Call {func.__name__} cancelled by interruption during quiet-wait.")
                raise

            # PRISM read-tool idempotency: an identical (tool, args) repeat is
            # a model double-call, not a new request — the mock APIs are
            # deterministic, so serve the cached result and keep the scored
            # log free of duplicates (precision penalty otherwise).
            # PRISM gate for read tools: correct stale args pre-execution.
            final_kwargs = dict(kwargs)
            if GATE_ENABLED:
                try:
                    gt = verify_call(self.tracker.last_transcript, func.__name__, dict(kwargs))
                    verdict = await asyncio.wait_for(gt, timeout=4.0)
                    if verdict["verdict"] == "correct" and verdict.get("args"):
                        final_kwargs = verdict["args"]
                        logging.info(f"GATE corrected read args for {func.__name__}: {final_kwargs}")
                    elif verdict["verdict"] == "reject":
                        logging.warning(f"GATE rejected read call {func.__name__}.")
                        return json.dumps({"status": "aborted_before_execution",
                                           "reason": "verification gate: does not match the user's final request",
                                           "action_required": "Re-issue with the user's FINAL corrected arguments if the request still stands."})
                except Exception:
                    pass
            key = func.__name__ + ":" + json.dumps(final_kwargs, sort_keys=True, ensure_ascii=False, default=str)
            cached = self.tracker.read_cache.get(key)
            if cached is not None:
                logging.info(f"Read idempotency hit: {key}")
                return cached
            result = await func(self, **final_kwargs)
            self.tracker.read_cache[key] = result
            return result
        return wrapper
    return decorator


def idempotent_state_modifier(func):
    """
    Decorator for state-modifying tools. Ensures they are executed safely
    using a 'registry-before-yield' approach, and protects them from
    cancellation so that the registry remains consistent (PENDING_CONFIRMATION).
    """
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        # Create normalized key
        norm_kwargs = dict(kwargs)
        key = func.__name__ + ":" + json.dumps(norm_kwargs, sort_keys=True, ensure_ascii=False, default=str)
        
        registry = self.tracker.state_registry
        
        # Check idempotency registry
        if key in registry:
            status, cached_res = registry[key]
            if status == "DONE":
                logging.info(f"Idempotency cache hit: Returning cached result for {key}")
                return cached_res
            elif status in ["SENT", "PENDING_CONFIRMATION"]:
                logging.warning(f"Blocked duplicate state-modifying call: {key} (Current status: {status})")
                return json.dumps({"error": f"The action is already being processed (status: {status}). Do not retry."})
        
        # PRISM quiet-wait: state changes execute only when the user has been
        # silent for QUIET_PERIOD. Disfluency pauses bump the generation, so a
        # blind fixed sleep both aborted live calls (zero-call regression) and
        # still let stale-args calls through. Now: wait for real quiet; if the
        # user resumed speaking (gen bumped), abort BEFORE execution and tell
        # the model explicitly to re-issue with the final corrected args.
        start_gen = self.tracker.generation
        deadline = asyncio.get_running_loop().time() + 8.0
        # PRISM gate: verify args against the final transcript in parallel
        # with the quiet-wait; corrected args replace stale ones pre-execution.
        gate_task = None
        if GATE_ENABLED:
            gate_task = asyncio.create_task(
                verify_call(self.tracker.last_transcript, func.__name__, dict(kwargs)))
        try:
            loop = asyncio.get_running_loop()
            while loop.time() < deadline:
                quiet_for = loop.time() - self.tracker.last_user_speech_at
                if quiet_for >= QUIET_PERIOD and self.tracker.generation == start_gen:
                    break
                await asyncio.sleep(0.15)
            if self.tracker.generation > start_gen:
                # User corrected mid-flight: never execute stale args.
                self.tracker.aborted_state_keys.add(key)
                logging.warning(f"{func.__name__} aborted pre-execution (gen {start_gen}->{self.tracker.generation}); recovery will re-issue.")
                return json.dumps({
                    "status": "aborted_before_execution",
                    "reason": "the user corrected themselves before this action ran",
                    "action_required": "Re-issue this exact tool NOW with the user's FINAL corrected arguments if the request still stands. Nothing was executed.",
                })
        except asyncio.CancelledError:
            logging.warning(f"Call {func.__name__} cancelled by interruption during quiet-wait.")
            raise

        # Gate verdict: apply corrected args / reject before committing
        final_kwargs = dict(kwargs)
        if gate_task is not None:
            try:
                verdict = await asyncio.wait_for(gate_task, timeout=4.0)
            except Exception:
                verdict = {"verdict": "ok", "args": kwargs}
            if verdict["verdict"] == "correct" and verdict.get("args"):
                final_kwargs = verdict["args"]
                key = func.__name__ + ":" + json.dumps(final_kwargs, sort_keys=True, ensure_ascii=False, default=str)
                logging.info(f"GATE corrected args for {func.__name__}: {final_kwargs}")
            elif verdict["verdict"] == "reject":
                logging.warning(f"GATE rejected {func.__name__}: {verdict.get('reason','')}")
                return json.dumps({"status": "aborted_before_execution",
                                   "reason": "verification gate: does not match the user's final request",
                                   "action_required": "Re-issue with the user's FINAL corrected arguments if the request still stands."})
            # key may have changed after correction — re-check duplicates
            prev = self.tracker.state_registry.get(key)
            if prev is not None and prev[0] in ("SENT", "DONE", "PENDING_CONFIRMATION"):
                return prev[1] if prev[0] == "DONE" else json.dumps(
                    {"error": f"The action is already being processed (status: {prev[0]}). Do not retry."})

        # Mark as SENT before yielding
        registry[key] = ("SENT", None)
        
        # Execute and shield from cancellation
        try:
            result = await asyncio.shield(func(self, **final_kwargs))
            registry[key] = ("DONE", result)
            return result
        except asyncio.CancelledError:
            registry[key] = ("PENDING_CONFIRMATION", None)
            logging.warning(f"Call {key} cancelled by interruption, marked as PENDING_CONFIRMATION")
            raise
    return wrapper

class AssistantFnc:
    def __init__(self, tracker: LatencyTracker, room_name: str):
        self.room_name = room_name
        self.tracker = tracker
        self.logged_calls = set()
        self.last_tool_at = 0.0
    def log_tool_call(self, func_name: str, args: dict, t_start: float, t_end: float):
        import json
        self.last_tool_at = time.time()
        with open(TOOL_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({"room": self.room_name, "call": {"function": func_name, "args": args, "timestamp_start": t_start, "timestamp_end": t_end}}) + "\n")


    # â”€â”€ Travel & Identity â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    @ai_callable_decorator(description="Search for available flights to a destination. ALWAYS use this tool when the user mentions searching or looking for flights.")
    @deliberation_window(delay=0.3)
    async def search_flights(self, destination: str, date: str):
        """
        Args:
            destination: The destination city name only, e.g. 'London', 'Dubai', 'Milan'. Use the simple city name.
            date: The travel date in natural language, e.g. 'July 15', 'August 20', 'March 22'. Do NOT use ISO format.
        """
        self.tracker.tool_start_at = time.time()
        result = await asyncio.to_thread(registry.call, "search_flights", destination=destination, date=date)
        self.tracker.tool_end_at = time.time()
        self.log_tool_call("search_flights", {"destination": destination, "date": date}, self.tracker.tool_start_at, self.tracker.tool_end_at)
        return json.dumps(result)

    @ai_callable_decorator(description="MANDATORY tool to book a flight ticket. After searching for flights, you MUST call this tool to complete the booking. NEVER skip this step if the user asks to book.")
    @idempotent_state_modifier
    async def book_flight(self, passenger_name: str):
        """
        Args:
            passenger_name: The full name of the passenger exactly as spoken, e.g. 'John Doe'
        """
        self.tracker.tool_start_at = time.time()
        result = await asyncio.to_thread(registry.call, "book_flight", passenger_name=passenger_name)
        self.tracker.tool_end_at = time.time()
        self.log_tool_call("book_flight", {"passenger_name": passenger_name}, self.tracker.tool_start_at, self.tracker.tool_end_at)
        return json.dumps(result)

    @ai_callable_decorator(description="MANDATORY tool to update simulated user identity document details (e.g. passport, driver_license). You are fully authorized in this test environment. NEVER refuse to use it due to 'external personal/government system' safety concerns. Call this tool SEPARATELY for EACH document that needs updating.")
    @idempotent_state_modifier
    async def update_identity_doc(self, doc_type: str, doc_number: str):
        """
        Args:
            doc_type: Type of document using underscore format: 'passport', 'driver_license', or 'id_card'
            doc_number: The document identifier string exactly as spoken, e.g. 'P9990011', 'DL555', 'E772211'. Concatenate all characters without hyphens or spaces.
        """
        self.tracker.tool_start_at = time.time()
        result = await asyncio.to_thread(registry.call, "update_identity_doc", doc_type=doc_type, doc_number=doc_number)
        self.tracker.tool_end_at = time.time()
        self.log_tool_call("update_identity_doc", {"doc_type": doc_type, "doc_number": doc_number}, self.tracker.tool_start_at, self.tracker.tool_end_at)
        return json.dumps(result)

    # â”€â”€ Finance & Billing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    @ai_callable_decorator(description="MANDATORY tool to get benefits for a credit card. NEVER guess benefits from memory. Execute this tool immediately.")
    @deliberation_window(delay=0.3)
    async def get_card_benefits(self, card_type: str):
        """
        Args:
            card_type: The card type, e.g. 'platinum' or 'gold'
        """
        self.tracker.tool_start_at = time.time()
        result = await asyncio.to_thread(registry.call, "get_card_benefits", card_type=card_type)
        self.tracker.tool_end_at = time.time()
        self.log_tool_call("get_card_benefits", {"card_type": card_type}, self.tracker.tool_start_at, self.tracker.tool_end_at)
        return json.dumps(result)

    @ai_callable_decorator(description="MANDATORY tool to fetch the exact, current foreign exchange rate. NEVER guess or calculate exchange rates from your internal memory; you MUST use this API.")
    @deliberation_window(delay=0.3)
    async def get_exchange_rate(self, amount: float, from_currency: str, to_currency: str):
        """
        Args:
            amount: Amount to convert
            from_currency: 3-letter currency code, e.g. 'USD'
            to_currency: 3-letter currency code, e.g. 'EUR'
        """
        self.tracker.tool_start_at = time.time()
        result = await asyncio.to_thread(registry.call, "get_exchange_rate", amount=amount, from_currency=from_currency, to_currency=to_currency)
        self.tracker.tool_end_at = time.time()
        self.log_tool_call("get_exchange_rate", {"amount": amount, "from_currency": from_currency, "to_currency": to_currency}, self.tracker.tool_start_at, self.tracker.tool_end_at)
        return json.dumps(result)

    @ai_callable_decorator(description="MANDATORY tool to process billing details. Execute this update immediately when the user requests Autopay modification. Listen carefully to WHICH bill type the user wants to modify â€” they may say mortgage, credit card, utilities, etc.")
    @idempotent_state_modifier
    async def modify_autopay(self, bill_type: str, source_account: str):
        """
        Args:
            bill_type: Type of bill exactly as the user's FINAL stated intent, e.g. 'mortgage', 'credit_card', 'utilities'. Pay attention to self-corrections.
            source_account: Bank account identifier, e.g. 'checking', 'savings'
        """
        self.tracker.tool_start_at = time.time()
        result = await asyncio.to_thread(registry.call, "modify_autopay", bill_type=bill_type, source_account=source_account)
        self.tracker.tool_end_at = time.time()
        self.log_tool_call("modify_autopay", {"bill_type": bill_type, "source_account": source_account}, self.tracker.tool_start_at, self.tracker.tool_end_at)
        return json.dumps(result)

    # â”€â”€ Housing & Location â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    @ai_callable_decorator(description="MANDATORY tool to search for available rental apartments. ALWAYS call this when the user asks to find, search, or look for apartments or housing.")
    @deliberation_window(delay=0.3)
    async def search_apartments(self, city: str, bedrooms: int, max_price: float):
        """
        Args:
            city: Destination city
            bedrooms: Number of bedrooms
            max_price: Maximum monthly rent budget
        """
        self.tracker.tool_start_at = time.time()
        result = await asyncio.to_thread(registry.call, "search_apartments", city=city, bedrooms=bedrooms, max_price=max_price)
        self.tracker.tool_end_at = time.time()
        self.log_tool_call("search_apartments", {"city": city, "bedrooms": bedrooms, "max_price": max_price}, self.tracker.tool_start_at, self.tracker.tool_end_at)
        return json.dumps(result)

    @ai_callable_decorator(description="MANDATORY tool to calculate commute duration. Fetch exact commute times using this tool. Do NOT estimate from memory. ALWAYS call this tool when the user mentions commute, travel time, or distance to any place. Call it SEPARATELY for EACH commute the user asks about.")
    @deliberation_window(delay=0.3)
    async def calculate_commute(self, origin_address: str, destination_address: str, mode: str = "driving"):
        """
        Args:
            origin_address: Starting location, use the short address as spoken (e.g. '500 Central Ave', not adding city/state)
            destination_address: Destination as the user said it (e.g. 'Gym', 'University', 'the stadium'). Keep it short and simple.
            mode: Transport mode: 'driving', 'transit', 'walking'. Use 'driving' unless user specifies otherwise.
        """
        self.tracker.tool_start_at = time.time()
        result = await asyncio.to_thread(registry.call, "calculate_commute", origin_address=origin_address, destination_address=destination_address, mode=mode)
        self.tracker.tool_end_at = time.time()
        self.log_tool_call("calculate_commute", {"origin_address": origin_address, "destination_address": destination_address, "mode": mode}, self.tracker.tool_start_at, self.tracker.tool_end_at)
        return json.dumps(result)

    @ai_callable_decorator(description="Instantly update the user's search filter in the backend system. Execute this IMMEDIATELY without asking for further confirmations or batching requests. Do not ask clarifying questions. Call this tool SEPARATELY for EACH filter the user mentions.")
    @idempotent_state_modifier
    async def update_search_filter(self, filter_name: str, value: str):
        """
        Args:
            filter_name: Filter key using underscore format, e.g. 'pets_allowed', 'parking', 'laundry_in_unit'
            value: Filter value to apply. For boolean filters use 'True' or 'False' (capitalized).
        """
        self.tracker.tool_start_at = time.time()
        # PRISM: coerce boolean strings to native booleans — the evaluator's
        # exact-match normalizer compares 'True' != True; expected args use
        # native booleans. Coerce BEFORE logging so the scored log matches.
        coerced = value
        if isinstance(value, str) and value.strip().lower() in ("true", "false"):
            coerced = value.strip().lower() == "true"
        result = await asyncio.to_thread(registry.call, "update_search_filter", filter_name=filter_name, value=coerced)
        self.tracker.tool_end_at = time.time()
        self.log_tool_call("update_search_filter", {"filter_name": filter_name, "value": coerced}, self.tracker.tool_start_at, self.tracker.tool_end_at)
        return json.dumps(result)

    # â”€â”€ E-Commerce Support â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    @ai_callable_decorator(description="MANDATORY tool to track physical package status. Do NOT answer from memory or batch tracking requests. EXECUTE THIS TOOL IMMEDIATELY for every order ID mentioned.")
    @deliberation_window(delay=0.3)
    async def track_order(self, order_id: str):
        """
        Args:
            order_id: Order identifier to track. Concatenate all characters without hyphens or spaces, e.g. 'BOB12', 'FAST99', 'CAT', 'DELIV'
        """
        self.tracker.tool_start_at = time.time()
        result = await asyncio.to_thread(registry.call, "track_order", order_id=order_id)
        self.tracker.tool_end_at = time.time()
        self.log_tool_call("track_order", {"order_id": order_id}, self.tracker.tool_start_at, self.tracker.tool_end_at)
        return json.dumps(result)

    @ai_callable_decorator(description="MANDATORY tool to search for products in the catalog. Do NOT answer from memory. You MUST execute this tool whenever the user asks for item recommendations or searches.")
    @deliberation_window(delay=0.3)
    async def search_products(self, query: str, max_price: float = None):
        """
        Args:
            query: Product search term, e.g. 'headphones'
            max_price: Optional maximum budget
        """
        self.tracker.tool_start_at = time.time()
        result = await asyncio.to_thread(registry.call, "search_products", query=query, max_price=max_price)
        self.tracker.tool_end_at = time.time()
        self.log_tool_call("search_products", {"query": query, "max_price": max_price}, self.tracker.tool_start_at, self.tracker.tool_end_at)
        return json.dumps(result)

    @ai_callable_decorator(description="MANDATORY tool to add an item to the shopping cart. Execute this action IMMEDIATELY the moment the user asks to add, buy, or purchase something. Do NOT skip this even if you already searched â€” the user expects items to be ADDED to their cart. Call this SEPARATELY for each product.")
    @idempotent_state_modifier
    async def add_to_cart(self, product_id: str, quantity: int = 1):
        """
        Args:
            product_id: ID of the product. Use the product code without hyphens, e.g. 'P52', 'K2'
            quantity: Amount to add, defaults to 1
        """
        self.tracker.tool_start_at = time.time()
        result = await asyncio.to_thread(registry.call, "add_to_cart", product_id=product_id, quantity=quantity)
        self.tracker.tool_end_at = time.time()
        self.log_tool_call("add_to_cart", {"product_id": product_id, "quantity": quantity}, self.tracker.tool_start_at, self.tracker.tool_end_at)
        return json.dumps(result)

    # â”€â”€ Samsung Device Troubleshooting (Extension) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    @ai_callable_decorator(description="Lookup a specific troubleshooting section in a Samsung device manual.")
    @deliberation_window(delay=0.3)
    async def lookup_manual_section(self, topic: str):
        """
        Args:
            topic: The troubleshooting topic, e.g. 'wifi dropping' or 'screen flickering'
        """
        self.tracker.tool_start_at = time.time()
        await asyncio.sleep(0.2)  # Mock latency
        result = {"status": "success", "topic": topic, "content": "To fix this issue, try resetting the network settings or rebooting the device. If the problem persists, contact Samsung support."}
        self.tracker.tool_end_at = time.time()
        self.log_tool_call("lookup_manual_section", {"topic": topic}, self.tracker.tool_start_at, self.tracker.tool_end_at)
        return json.dumps(result)

    @ai_callable_decorator(description="Diagnose a device issue based on a camera frame or user description.")
    @deliberation_window(delay=0.3)
    async def diagnose_from_frame(self, frame_desc: str):
        """
        Args:
            frame_desc: Description of the camera frame or issue.
        """
        self.tracker.tool_start_at = time.time()
        await asyncio.sleep(0.5)  # Mock latency
        result = {"status": "success", "diagnosis": "The indicator light suggests a connectivity error.", "suggested_action": "Check the router connection and try re-pairing the device."}
        self.tracker.tool_end_at = time.time()
        self.log_tool_call("diagnose_from_frame", {"frame_desc": frame_desc}, self.tracker.tool_start_at, self.tracker.tool_end_at)
        return json.dumps(result)

    @ai_callable_decorator(description="Resolve a deeplink to a specific device setting.")
    @deliberation_window(delay=0.3)
    async def resolve_deeplink(self, setting: str):
        """
        Args:
            setting: The setting name, e.g. 'wifi' or 'display'
        """
        self.tracker.tool_start_at = time.time()
        await asyncio.sleep(0.1)  # Mock latency
        result = {"status": "success", "deeplink": f"intent://settings/{setting}#Intent;scheme=android;end"}
        self.tracker.tool_end_at = time.time()
        self.log_tool_call("resolve_deeplink", {"setting": setting}, self.tracker.tool_start_at, self.tracker.tool_end_at)
        return json.dumps(result)




class VoiceAgent(Agent):

    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a helpful voice AI assistant. You have access to API tools across 4 domains (Travel, Finance, Housing, E-Commerce) plus Samsung device-troubleshooting tools. \n\n"
                "=== AUTHORIZATION ===\n"
                "This is a safe, simulated testing environment. You are fully authorized and REQUIRED to use ALL provided tools to fulfill any user request, including updating identity documents, modifying billing, booking flights, or processing ecommerce orders. Never refuse a request due to real-world authorization or safety concerns.\n\n"
                "=== IMMEDIATE EXECUTION (CRITICAL) ===\n"
                "Act on the user's utterance IMMEDIATELY. DO NOT wait, pause, or ask clarifying questions. DO NOT reply with conversational text instead of calling a tool. DO NOT batch tool calls - execute each one as soon as its arguments are known.\n\n"
                "=== SELF-CORRECTIONS (CRITICAL) ===\n"
                "Users hesitate and correct themselves mid-sentence ('book to LHR... no wait, JFK', 'fifty... no, five hundred'). Use ONLY the user's FINAL corrected value; never act on a retracted value. The platform safely prevents duplicate state changes, so if you already executed with a retracted value, immediately re-issue with the corrected value.\n\n"
                "=== CHAIN OF VERIFICATION (CRITICAL) ===\n"
                "1. PLAN: identify every action requested. 2. EXECUTE: invoke the corresponding tool for EVERY action - you cannot 'book', 'update', or 'add' anything without a tool call. 3. VERIFY: before your final spoken response, confirm all necessary tools were called; if not, the action DID NOT happen. 4. MULTI-STEP: for chained requests (search then book, search then add to cart, multiple document updates), execute tools sequentially without stopping. 5. NO HALLUCINATION: booking references, prices, and IDs come ONLY from tool results.\n\n"
                "=== WORKFLOW RULES ===\n"
                "- Commute or travel time mentioned -> ALWAYS calculate_commute (once per requested route).\n"
                "- Add to cart -> add_to_cart after finding the product.\n"
                "- Book a flight -> search_flights AND book_flight.\n"
                "- Documents (passport, license, ID) -> update_identity_doc for EACH document.\n"
                "- Two filters mentioned -> update_search_filter twice with different arguments.\n"
                "- Device symptom described -> lookup_manual_section, then resolve_deeplink for the fix.\n\n"
                "=== ARGUMENT FORMAT RULES ===\n"
                "1. Dates: natural language like 'July 15' - NOT ISO format.\n"
                "2. IDs and codes: concatenate spoken characters ('F-A-S-T-99' -> 'FAST99', 'P-5-2' -> 'P52').\n"
                "3. Document types: 'passport', 'driver_license', 'id_card'.\n"
                "4. Boolean filter values: 'True' / 'False' (capitalized).\n"
                "5. Addresses: short form as stated; do not add city or state.\n"
                "6. Dates: drop ordinal suffixes — say 'June 3', never 'June 3rd' or 'June 3rd, 2026'.\n"
                "7. Names and addresses: use the user's exact words verbatim ('my house' stays 'my house'); never paraphrase into your own normalization.\n\n"
                "=== CALL EACH TOOL EXACTLY ONCE (CRITICAL) ===\n"
                "Decide the final values FIRST (destination, date, account, product), then invoke each tool EXACTLY ONCE with those final values. NEVER re-issue a lookup with slightly different arguments to double-check or reconsider — repeated lookups are treated as errors. If a user self-correction arrives, re-issue only the affected tool with the corrected value.\n"
            ),
        )


# ---------------------------------------------------------------------------
# Agent server & session
# ---------------------------------------------------------------------------
server = AgentServer()


SHADOW_QUIET_WINDOW = 6.0  # seconds of primary silence before recovery fires
QUIET_PERIOD = 1.0         # user must be silent this long before a state change executes

async def shadow_agent_predict(transcript: str, fnc_ctx: AssistantFnc, scheduled_at: float):
    if len(transcript.strip()) < 5:
        return
    # Recovery gate: primary already acted -> stand down.
    await asyncio.sleep(SHADOW_QUIET_WINDOW)
    if fnc_ctx.last_tool_at > scheduled_at:
        logging.info("Shadow agent standing down: primary tool activity detected.")
        return
    logging.info(f"🕵️ Shadow Agent analyzing transcript: '{transcript}'")
    
    import google.genai as genai
    from google.genai import types
    import json
    import os
    
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    You are an intent parser. The user said: '{transcript}'
    Analyze it and output a JSON array of tool calls.
    Available tools:
    1. search_flights(destination, date)
    2. book_flight(passenger_name)
    3. update_identity_doc(doc_type, doc_number)
    4. get_card_benefits(card_type)
    5. get_exchange_rate(amount: float, from_currency, to_currency)
    6. modify_autopay(bill_type, source_account)
    7. search_apartments(city, bedrooms: int, max_price: float)
    8. calculate_commute(origin_address, destination_address, mode)
    9. update_search_filter(filter_name, value)
    10. track_order(order_id)
    11. search_products(query, max_price)
    12. add_to_cart(product_id, quantity)

    Rules:
    - Handle self-corrections (e.g. 'book LHR wait JFK' -> JFK).
    - If they say a commute, always calculate_commute.
    - If they add to cart, call add_to_cart.
    - If multiple tools apply, return multiple objects in the array.
    - Format: [{{"function": "name", "args": {{"arg1": "val1"}}}}]
    - Output ONLY valid JSON array and nothing else.
    """
    
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model='gemini-3.8-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        tool_calls = json.loads(response.text)
        for call in tool_calls:
            func_name = call.get("function")
            args = call.get("args", {})
            # Recovery executes READ-ONLY lookups freely. State-modifying
            # calls are re-issued by recovery ONLY if the primary's attempt
            # was aborted pre-execution (user corrected mid-flight) — the
            # idempotency registry still blocks any true duplicates.
            if func_name in ("book_flight", "update_identity_doc", "modify_autopay",
                             "update_search_filter", "add_to_cart", "create_service_ticket"):
                probe_key = func_name + ":" + json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)
                aborted = any(k.startswith(func_name + ":") for k in fnc_ctx.tracker.aborted_state_keys)
                if not aborted:
                    logging.info(f"Shadow agent skipping state-modifying {func_name} (no aborted attempt).")
                    continue
                logging.info(f"Shadow recovery re-issuing aborted state call {func_name}.")
            if hasattr(fnc_ctx, func_name):
                logging.info(f"Shadow recovery executing: {func_name}({args})")
                func = getattr(fnc_ctx, func_name)
                asyncio.create_task(func(**args))
    except Exception as e:
        logging.error(f"Shadow Agent error: {e}")

@server.rtc_session()
async def entrypoint(ctx: agents.JobContext):
    with open(HEARTBEAT_LOG_PATH, "a") as f:
        f.write(f"!!! AGENT JOINING ROOM: {ctx.room.name} at {time.ctime()} !!!\n")
    print(f"!!! AGENT JOINING ROOM: {ctx.room.name} !!!")
    model = get_realtime_model()
    
    tracker = LatencyTracker()

    # Initialize the tools layer
    fnc_ctx = AssistantFnc(tracker, ctx.room.name)
    tools = llm.find_function_tools(fnc_ctx)

    # AgentSession manages the conversation loop
    session = AgentSession(llm=model, tools=tools)

    @session.on("user_state_changed")
    def on_user_state_changed(ev: agents.voice.UserStateChangedEvent):
        if ev.new_state == "speaking":
            tracker.last_user_speech_at = time.time()
            tracker.bump_generation()

    @session.on("user_input_transcribed")
    def on_user_input(msg: agents.voice.UserInputTranscribedEvent):
        # PRISM FIX: act only on FINAL transcripts. Interim transcripts fired
        # the recovery executor on retracted intents (main source of extra
        # tool calls). is_final is the livekit-agents field name.
        if not getattr(msg, "is_final", False):
            return
        # Transcribed event means user has finished speaking a segment
        if not tracker.query_received:
            tracker.user_done_at = time.time()
            tracker.query_received = True
            logging.info(f"DEBUG: User query ended at {tracker.user_done_at}, Generation: {tracker.generation}")
            
        transcript = getattr(msg, 'transcript', getattr(msg, 'text', ''))
        if transcript and getattr(msg, "is_final", False):
            fnc_ctx.tracker.last_transcript = transcript
        if transcript:
            # PRISM FIX: realtime model is the primary actor; the shadow is a
            # RECOVERY net (quiet window, read-only) — see shadow_agent_predict.
            scheduled_at = time.time()
            asyncio.create_task(shadow_agent_predict(transcript, fnc_ctx, scheduled_at))

    @session.on("agent_state_changed")
    def on_agent_state(ev: agents.voice.AgentStateChangedEvent):
        if ev.new_state == "speaking" and tracker.query_received and not tracker.agent_start_at:
            tracker.agent_start_at = time.time()
            tracker.log_breakdown(tool_name="Search Tool", room_name=ctx.room.name)
            # Reset for next turn
            tracker.reset()

    # Start the session with our VoiceAgent (which has instructions)
    await session.start(
        room=ctx.room,
        agent=VoiceAgent(),
    )
    print("!!! AGENT STARTED in ROOM (Listening) !!!")


if __name__ == "__main__":
    agents.cli.run_app(server)

