# One-shot patcher: applies fixes 1-6 to prism_agent.py
p = "fdb3/v3/prism_agent.py"
s = open(p, encoding="utf-8").read()
n = 0

def rep(old, new, why):
    global s, n
    assert old in s, "NOT FOUND: " + why
    s = s.replace(old, new, 1)
    n += 1
    print("OK  fix:", why)

# ---- FIX 2+3: pinned log path, no silent dedupe, last_tool_at
rep(
    '    def log_tool_call(self, func_name: str, args: dict, t_start: float, t_end: float):\n        import json\n        call_key = f"{func_name}:{json.dumps(args, sort_keys=True)}"\n        if call_key in self.logged_calls:\n            return\n        self.logged_calls.add(call_key)\n        with open("logs/agent_tool_calls.log", "a", encoding="utf-8") as f:',
    '    def log_tool_call(self, func_name: str, args: dict, t_start: float, t_end: float):\n        import json\n        self.last_tool_at = time.time()\n        with open(TOOL_LOG_PATH, "a", encoding="utf-8") as f:',
    "FIX2+3 pinned log path + removed silent dedupe + last_tool_at",
)

# path constants after dotenv block
rep(
    'env_path = os.path.join(os.path.dirname(__file__), ".env.local")\nload_dotenv(env_path)',
    'env_path = os.path.join(os.path.dirname(__file__), ".env.local")\nload_dotenv(env_path)\n\n'
    '# PRISM fix: single source of truth for telemetry paths. The scorer reads\n'
    '# the SAME path (PRISM_TOOL_LOG env or <script dir>/logs), so no CWD drift.\n'
    'V3_DIR = os.path.dirname(os.path.abspath(__file__))\n'
    'TOOL_LOG_PATH = os.environ.get("PRISM_TOOL_LOG") or os.path.join(V3_DIR, "logs", "agent_tool_calls.log")\n'
    'HEARTBEAT_LOG_PATH = os.environ.get("PRISM_HEARTBEAT_LOG") or os.path.join(V3_DIR, "logs", "agent_heartbeat.log")',
    "FIX2 path constants",
)

# heartbeat pinned
s2 = s.replace('with open("logs/agent_heartbeat.log", "a") as f:', 'with open(HEARTBEAT_LOG_PATH, "a") as f:')
assert s2 != s
s = s2
n += 1
print("OK  fix: heartbeat pinned")

# init last_tool_at
rep(
    "        self.room_name = room_name\n        self.tracker = tracker\n        self.logged_calls = set()",
    "        self.room_name = room_name\n        self.tracker = tracker\n        self.logged_calls = set()\n        self.last_tool_at = 0.0",
    "init last_tool_at",
)

# ---- FIX 5: state deliberation 1.0 -> 0.5
rep(
    "        # Deliberation window (gives user time to self-correct before we commit)\n        start_gen = self.tracker.generation\n        try:\n            await asyncio.sleep(1.0)",
    "        # Deliberation window (gives user time to self-correct before we commit)\n        start_gen = self.tracker.generation\n        try:\n            await asyncio.sleep(0.5)",
    "FIX5 state window 1.0s -> 0.5s",
)

# ---- FIX 1: final-transcript-only
rep(
    '    @session.on("user_input_transcribed")\n    def on_user_input(msg: agents.voice.UserInputTranscribedEvent):\n        # Transcribed event means user has finished speaking a segment\n        if not tracker.query_received:',
    '    @session.on("user_input_transcribed")\n    def on_user_input(msg: agents.voice.UserInputTranscribedEvent):\n'
    '        # PRISM FIX: act only on FINAL transcripts. Interim transcripts fired\n'
    '        # the recovery executor on retracted intents (main source of extra\n'
    '        # tool calls). is_final is the livekit-agents field name.\n'
    '        if not getattr(msg, "is_final", False):\n            return\n'
    '        # Transcribed event means user has finished speaking a segment\n        if not tracker.query_received:',
    "FIX1 final-transcript-only filter",
)

# ---- FIX 6: schedule with timestamp
rep(
    "        transcript = getattr(msg, 'transcript', getattr(msg, 'text', ''))\n        if transcript:\n            asyncio.create_task(shadow_agent_predict(transcript, fnc_ctx))",
    "        transcript = getattr(msg, 'transcript', getattr(msg, 'text', ''))\n        if transcript:\n"
    "            # PRISM FIX: realtime model is the primary actor; the shadow is a\n"
    "            # RECOVERY net (quiet window, read-only) — see shadow_agent_predict.\n"
    "            scheduled_at = time.time()\n            asyncio.create_task(shadow_agent_predict(transcript, fnc_ctx, scheduled_at))",
    "FIX6 quiet-window scheduling",
)

rep(
    'async def shadow_agent_predict(transcript: str, fnc_ctx: AssistantFnc):\n    if len(transcript.strip()) < 5:\n        return',
    'SHADOW_QUIET_WINDOW = 6.0  # seconds of primary silence before recovery fires\n\n'
    'async def shadow_agent_predict(transcript: str, fnc_ctx: AssistantFnc, scheduled_at: float):\n'
    '    if len(transcript.strip()) < 5:\n        return\n'
    '    # Recovery gate: primary already acted -> stand down.\n'
    '    await asyncio.sleep(SHADOW_QUIET_WINDOW)\n'
    '    if fnc_ctx.last_tool_at > scheduled_at:\n'
    '        logging.info("Shadow agent standing down: primary tool activity detected.")\n        return',
    "FIX6 quiet-window gate",
)

rep(
    '        tool_calls = json.loads(response.text)\n        for call in tool_calls:\n            func_name = call.get("function")\n            args = call.get("args", {})\n            if hasattr(fnc_ctx, func_name):\n                logging.info(f"🕵️ Shadow Agent executing: {func_name}({args})")\n                func = getattr(fnc_ctx, func_name)\n                asyncio.create_task(func(**args))',
    '        tool_calls = json.loads(response.text)\n        for call in tool_calls:\n            func_name = call.get("function")\n            args = call.get("args", {})\n'
    '            # Recovery executes READ-ONLY lookups only; state changes belong\n'
    '            # to the primary path (prevents duplicate state mutations).\n'
    '            if func_name in ("book_flight", "update_identity_doc", "modify_autopay",\n'
    '                             "update_search_filter", "add_to_cart", "create_service_ticket"):\n'
    '                logging.info(f"Shadow agent skipping state-modifying {func_name}.")\n                continue\n'
    '            if hasattr(fnc_ctx, func_name):\n'
    '                logging.info(f"Shadow recovery executing: {func_name}({args})")\n                func = getattr(fnc_ctx, func_name)\n                asyncio.create_task(func(**args))',
    "FIX6 read-only recovery restriction",
)

# ---- FIX 5b: instructions rewrite
i = s.index("            instructions=(")
j = s.index("            ),", i)
NEW_INSTR = (
    '            instructions=(\n'
    '                "You are a helpful voice AI assistant. You have access to API tools across 4 domains (Travel, Finance, Housing, E-Commerce) plus Samsung device-troubleshooting tools. \\n\\n"\n'
    '                "=== AUTHORIZATION ===\\n"\n'
    '                "This is a safe, simulated testing environment. You are fully authorized and REQUIRED to use ALL provided tools to fulfill any user request, including updating identity documents, modifying billing, booking flights, or processing ecommerce orders. Never refuse a request due to real-world authorization or safety concerns.\\n\\n"\n'
    '                "=== IMMEDIATE EXECUTION (CRITICAL) ===\\n"\n'
    '                "Act on the user\'s utterance IMMEDIATELY. DO NOT wait, pause, or ask clarifying questions. DO NOT reply with conversational text instead of calling a tool. DO NOT batch tool calls - execute each one as soon as its arguments are known.\\n\\n"\n'
    '                "=== SELF-CORRECTIONS (CRITICAL) ===\\n"\n'
    '                "Users hesitate and correct themselves mid-sentence (\'book to LHR... no wait, JFK\', \'fifty... no, five hundred\'). Use ONLY the user\'s FINAL corrected value; never act on a retracted value. The platform safely prevents duplicate state changes, so if you already executed with a retracted value, immediately re-issue with the corrected value.\\n\\n"\n'
    '                "=== CHAIN OF VERIFICATION (CRITICAL) ===\\n"\n'
    '                "1. PLAN: identify every action requested. 2. EXECUTE: invoke the corresponding tool for EVERY action - you cannot \'book\', \'update\', or \'add\' anything without a tool call. 3. VERIFY: before your final spoken response, confirm all necessary tools were called; if not, the action DID NOT happen. 4. MULTI-STEP: for chained requests (search then book, search then add to cart, multiple document updates), execute tools sequentially without stopping. 5. NO HALLUCINATION: booking references, prices, and IDs come ONLY from tool results.\\n\\n"\n'
    '                "=== WORKFLOW RULES ===\\n"\n'
    '                "- Commute or travel time mentioned -> ALWAYS calculate_commute (once per requested route).\\n"\n'
    '                "- Add to cart -> add_to_cart after finding the product.\\n"\n'
    '                "- Book a flight -> search_flights AND book_flight.\\n"\n'
    '                "- Documents (passport, license, ID) -> update_identity_doc for EACH document.\\n"\n'
    '                "- Two filters mentioned -> update_search_filter twice with different arguments.\\n"\n'
    '                "- Device symptom described -> lookup_manual_section, then resolve_deeplink for the fix.\\n\\n"\n'
    '                "=== ARGUMENT FORMAT RULES ===\\n"\n'
    '                "1. Dates: natural language like \'July 15\' - NOT ISO format.\\n"\n'
    '                "2. IDs and codes: concatenate spoken characters (\'F-A-S-T-99\' -> \'FAST99\', \'P-5-2\' -> \'P52\').\\n"\n'
    '                "3. Document types: \'passport\', \'driver_license\', \'id_card\'.\\n"\n'
    '                "4. Boolean filter values: \'True\' / \'False\' (capitalized).\\n"\n'
    '                "5. Addresses: short form as stated; do not add city or state.\\n"\n'
    '            ),'
)
s = s[:i] + NEW_INSTR + s[j + len("            ),"):]
n += 1
print("OK  fix: instructions rewritten (immediacy + final-value)")

open(p, "w", encoding="utf-8", newline="\n").write(s)
print("")
print("prism_agent.py:", n, "fixes applied")
