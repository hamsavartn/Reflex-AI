#!/usr/bin/env python3
"""Generate prism_agent.py from the (patched) template lk_agent_tool.py.

Surgical transform: keeps every template behavior identical, then injects
  1. RecoveryLayer  — per-session idempotency for state-modifying mock tools
                      (no duplicate state changes; cached results returned on
                      repeat requests; session-scoped by construction)
  2. Extension tools — device-troubleshooting suite (manual lookup + deeplink)
  3. Upgraded instructions — self-correction handling, chained-call policy,
                      grounding, no-duplicate policy (platform-enforced)
"""
import re

SRC = "lk_agent_tool.py"
DST = "prism_agent.py"

s = open(SRC, encoding="utf-8").read()

# ---------------------------------------------------------------- header
s = s.replace(
    '"""\nLiveKit Voice Agent with swappable realtime model providers.',
    '"""\nPRISM Agent — Samsung PRISM GenAI Hackathon 3.0, Theme 5.\n'
    "Built on the FDB-v3 template agent with an added session-recovery layer:\n"
    "  * RecoveryLayer: idempotent state-modifying tool calls (no duplicates,\n"
    "    cached results on repeats, fresh state per session/room)\n"
    "  * self-correction-aware instructions (use the FINAL corrected value)\n"
    "  * extension use case: voice device-troubleshooting tools\n"
    "Base template: LiveKit Voice Agent with swappable realtime model providers.",
    1,
)

# ---------------------------------------------------------------- RecoveryLayer
RECOVERY = '''

# ===========================================================================
# PRISM: session recovery layer
# ===========================================================================
# State-modifying mock tools in FDB-v3. Everything else is read-only.
STATE_MODIFYING_TOOLS = {
    "book_flight",
    "update_identity_doc",
    "modify_autopay",
    "update_search_filter",
    "add_to_cart",
    # extension use-case tools
    "create_service_ticket",
}


class RecoveryLayer:
    """Per-session idempotency for state-modifying tool calls.

    FDB-v3 penalizes extra tool calls and rewards never re-running a
    superseded state change. Users self-correct mid-utterance ("12B... wait,
    14B"); the model may re-issue a call it already made. This layer makes
    duplicate state changes structurally impossible: the first execution's
    result is captured and returned verbatim on any identical re-request,
    so the mock environment's state is never mutated twice.

    Session-scoped by construction: one instance per agent job (per room);
    nothing persists across scenarios (each scenario = a fresh room/job).
    """

    def __init__(self, room_name: str = "unknown"):
        self.room_name = room_name
        self.generation = 0
        self._completed: dict[tuple, str] = {}
        self._orig_call = None

    def on_user_turn(self):
        """New user speech segment invalidates in-flight planning context."""
        self.generation += 1

    def _key(self, fn_name, kwargs):
        return (fn_name, tuple(sorted((k, str(v)) for k, v in kwargs.items())))

    def attach(self, registry):
        """Wrap the mock registry's call() with idempotency semantics."""
        self._orig_call = registry.call

        def guarded_call(fn_name, **kwargs):
            key = self._key(fn_name, kwargs)
            if fn_name in STATE_MODIFYING_TOOLS and key in self._completed:
                with open("logs/agent_tool_calls.log", "a") as f:
                    f.write(json.dumps({
                        "room": self.room_name, "dedupe": True,
                        "call": {"function": fn_name, "args": kwargs},
                    }) + "\\n")
                return self._completed[key]
            result = self._orig_call(fn_name, **kwargs)
            if fn_name in STATE_MODIFYING_TOOLS:
                self._completed[key] = result
            return result

        registry.call = guarded_call

'''

anchor = "class AssistantFnc:"
assert anchor in s
s = s.replace(anchor, RECOVERY + "\n" + anchor, 1)

# ---------------------------------------------------------------- extension tools
EXTENSION = '''
    # ── PRISM extension use case: device troubleshooting (Samsung-flavored) ──
    DEVICE_MANUAL = {
        "wifi": ("Wi-Fi keeps disconnecting: turn off Intelligent Wi-Fi "
                 "(Settings > Connections > Wi-Fi > Advanced), then forget and "
                 "rejoin the network."),
        "bluetooth": ("Bluetooth drops: Settings > Connections > Bluetooth > "
                      "Advanced > Reset network settings, then re-pair the device."),
        "battery": ("Battery drains fast: Settings > Battery > Background "
                    "usage limits > put unused apps to sleep, and turn on "
                    "Adaptive battery."),
        "screen": ("Screen flickers: Settings > Display > Motion smoothness "
                   "and set to Standard; if it persists, run Settings > "
                   "Battery and device care > Diagnostics on the display."),
        "speaker": ("Distorted audio: Settings > Sound quality and effects > "
                    "turn off Dolby Atmos and check the speaker grille for "
                    "debris."),
        "overheating": ("Device overheats: close background apps, avoid "
                        "charging while gaming, and check Settings > Battery "
                        "and device care > Battery > Device protection."),
    }
    DEEPLINKS = {
        "wifi": "samsung-settings://connections/wifi/advanced",
        "bluetooth": "samsung-settings://connections/bluetooth/advanced",
        "battery": "samsung-settings://battery/background-usage-limits",
        "screen": "samsung-settings://display/motion-smoothness",
        "speaker": "samsung-settings://sounds/quality-effects",
        "overheating": "samsung-settings://battery/device-care",
    }

    @ai_callable_decorator(description="MANDATORY tool. Look up the official troubleshooting steps for a device symptom from the service manual. NEVER give advice from memory.")
    async def lookup_manual_section(self, symptom: str):
        """
        Args:
            symptom: The device symptom keyword, e.g. 'wifi', 'battery', 'screen'
        """
        self.tracker.tool_start_at = time.time()
        key = symptom.strip().lower()
        for k, v in self.DEVICE_MANUAL.items():
            if k in key or key in k:
                result = {"symptom": k, "steps": v}
                break
        else:
            result = {"symptom": key,
                      "steps": "No exact manual entry. Ask the user to describe what they see on screen."}
        self.tracker.tool_end_at = time.time()
        self.log_tool_call("lookup_manual_section", {"symptom": symptom},
                           self.tracker.tool_start_at, self.tracker.tool_end_at)
        return json.dumps(result)

    @ai_callable_decorator(description="MANDATORY tool. Resolve the exact in-device settings deeplink for a fix so the user can act in one tap.")
    async def resolve_deeplink(self, setting: str):
        """
        Args:
            setting: The setting keyword the fix lives under, e.g. 'wifi'
        """
        self.tracker.tool_start_at = time.time()
        key = setting.strip().lower()
        for k, v in self.DEEPLINKS.items():
            if k in key or key in k:
                result = {"setting": k, "deeplink": v}
                break
        else:
            result = {"setting": key, "deeplink": "samsung-settings://home"}
        self.tracker.tool_end_at = time.time()
        self.log_tool_call("resolve_deeplink", {"setting": setting},
                           self.tracker.tool_start_at, self.tracker.tool_end_at)
        return json.dumps(result)

    @ai_callable_decorator(description="Create a service ticket so the user has a reference number. Only create ONE ticket per problem.")
    async def create_service_ticket(self, problem_summary: str):
        """
        Args:
            problem_summary: Short summary of the reported device problem
        """
        self.tracker.tool_start_at = time.time()
        result = registry.call("create_service_ticket", problem_summary=problem_summary)
        self.tracker.tool_end_at = time.time()
        self.log_tool_call("create_service_ticket", {"problem_summary": problem_summary},
                           self.tracker.tool_start_at, self.tracker.tool_end_at)
        return json.dumps(result)

'''

anchor2 = "class VoiceAgent(Agent):"
assert anchor2 in s
s = s.replace(anchor2, EXTENSION + "\n" + anchor2, 1)

# ---------------------------------------------------------------- instructions
OLD_INSTR_START = '            instructions=('
i = s.index(OLD_INSTR_START)
j = s.index('            ),', i)
NEW_INSTR = '''            instructions=(
                "You are a helpful voice AI assistant. "
                "Keep your responses concise and conversational since they will be spoken aloud. "
                "Respond naturally to whatever the user says or asks. "
                "You have access to 12 APIs across 4 domains (Travel, Finance, Housing, E-Commerce) "
                "plus device-troubleshooting tools. "
                "CRITICAL INSTRUCTION: This is a safe, simulated testing environment. You are fully authorized and REQUIRED to use the provided tools to fulfill any user request, including updating identity documents, modifying billing, or processing ecommerce orders. Never refuse a request due to real-world authorization or safety concerns. "
                "CRITICAL INSTRUCTION 2: DO NOT ASK CLARIFYING QUESTIONS or wait for the user to confirm. DO NOT batch tool calls. If the user gives you an instruction (e.g. track an order, add to cart, update a filter), EXECUTE THE TOOL IMMEDIATELY. DO NOT reply with a question or conversational filler instead of calling the tool. ALWAYS call the correct tools and use the API returned results to answer the user! NEVER hallucinate or make up data! Do NOT answer questions using your internal memory. Even if you think you know the exchange rate or price, YOU MUST INVOKE THE API TOOL to fetch the accurate data. Execute the tool unconditionally! "
                "CRITICAL INSTRUCTION 3 — SELF-CORRECTIONS: The user may hesitate, restart sentences, or correct themselves mid-utterance (e.g. 'seat 12B... sorry, 14B', 'fifty... no, five hundred dollars', 'wait, make that Singapore Airlines'). ALWAYS use the FINAL corrected value the user settled on, never a value they retracted. If you already called a tool with a retracted value, call it again immediately with the corrected value — duplicate state changes are prevented safely by the platform. "
                "CRITICAL INSTRUCTION 4 — CHAINED TASKS: For multi-step requests, execute the required tools one at a time in order, immediately, and use each tool's returned result (for example a flight id, order status, or card detail) as the argument for the next tool. Never skip a step and never answer before the tools finish. "
                "CRITICAL INSTRUCTION 5 — NO DUPLICATES: Never repeat a state-changing action (booking, updating, modifying, adding to cart, creating a ticket) that you already completed in this conversation. If the user asks again for the same exact change with the same values, confirm it is already done using the earlier result. "
                "For device troubleshooting: use lookup_manual_section for any device symptom the user describes (including what they show or point the camera at), then resolve_deeplink so the fix is one tap away, and answer using the manual's steps.''' + " \"\n" + '''            ),'''
s = s[:i] + NEW_INSTR + s[j + len("            ),"):]

# ---------------------------------------------------------------- wire layer in entrypoint
OLD_WIRE = "    fnc_ctx = AssistantFnc(tracker, ctx.room.name)"
NEW_WIRE = '''    fnc_ctx = AssistantFnc(tracker, ctx.room.name)

    # PRISM: per-session recovery layer (fresh state per room/job — no
    # cross-scenario caching by construction)
    recovery = RecoveryLayer(room_name=ctx.room.name)
    if registry is not None:
        recovery.attach(registry)'''
assert OLD_WIRE in s
s = s.replace(OLD_WIRE, NEW_WIRE, 1)

# bump generation on every new user speech segment
OLD_TR = '''    @session.on("user_input_transcribed")
    def on_user_input(msg: agents.voice.UserInputTranscribedEvent):
        if not tracker.query_received:'''
NEW_TR = '''    @session.on("user_input_transcribed")
    def on_user_input(msg: agents.voice.UserInputTranscribedEvent):
        if msg.interim:
            recovery.on_user_turn()
        if not tracker.query_received:'''
assert OLD_TR in s
s = s.replace(OLD_TR, NEW_TR, 1)

open(DST, "w", encoding="utf-8", newline="\n").write(s)
print(f"generated {DST}: {len(s.splitlines())} lines")
