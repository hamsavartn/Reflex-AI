# One-shot patcher: quiet-wait + re-issue recovery for state tools (P0 fix)
# Root cause (finance_23 zero-call regression): generation bumps fire on
# disfluency pauses; a call issued mid-utterance gets aborted with a generic
# error string; the model apologizes instead of re-issuing; shadow skips
# state tools -> ZERO calls. Baseline passed this case.
p = "fdb3/v3/prism_agent.py"
s = open(p, encoding="utf-8").read()
n = 0

def rep(old, new, why):
    global s, n
    assert old in s, "NOT FOUND: " + why
    s = s.replace(old, new, 1)
    n += 1
    print("OK :", why)

# ---- 1. tracker: user-speech timestamp + aborted-state-keys set
rep(
    """        # Recovery Layer: Generation and State Registry
        self.generation = 0
        self.state_registry = {}  # key -> (status, result)""",
    """        # Recovery Layer: Generation and State Registry
        self.generation = 0
        self.state_registry = {}  # key -> (status, result)
        self.last_user_speech_at = 0.0
        self.aborted_state_keys = set()  # state keys aborted pre-execution""",
    "tracker: speech timestamp + aborted keys",
)

# ---- 2. replace the wait/abort block with quiet-wait + explicit re-issue
# the real current text (0.5s fixed window, gen check)
old_block = """        # Deliberation window (gives user time to self-correct before we commit)
        start_gen = self.tracker.generation
        try:
            await asyncio.sleep(0.5)
            if self.tracker.generation > start_gen:
                logging.warning(f"Aborting {func.__name__} due to generation bump.")
                return json.dumps({"error": "Action aborted because user started speaking again."})
        except asyncio.CancelledError:
            logging.warning(f"Call {func.__name__} cancelled by interruption during deliberation.")
            raise"""
new_block = """        # PRISM quiet-wait: state changes execute only when the user has been
        # silent for QUIET_PERIOD. Disfluency pauses bump the generation, so a
        # blind fixed sleep both aborted live calls (zero-call regression) and
        # still let stale-args calls through. Now: wait for real quiet; if the
        # user resumed speaking (gen bumped), abort BEFORE execution and tell
        # the model explicitly to re-issue with the final corrected args.
        start_gen = self.tracker.generation
        deadline = asyncio.get_running_loop().time() + 8.0
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
            raise"""
rep(old_block, new_block, "quiet-wait + explicit re-issue instruction")

# ---- 3. constants for the quiet period (module level, near shadow window)
rep(
    'SHADOW_QUIET_WINDOW = 6.0  # seconds of primary silence before recovery fires',
    'SHADOW_QUIET_WINDOW = 6.0  # seconds of primary silence before recovery fires\n'
    'QUIET_PERIOD = 1.0         # user must be silent this long before a state change executes',
    "QUIET_PERIOD constant",
)

# ---- 4. shadow recovery may re-issue ABORTED state calls only
rep(
    '            # Recovery executes READ-ONLY lookups only; state changes belong\n'
    '            # to the primary path (prevents duplicate state mutations).\n'
    '            if func_name in ("book_flight", "update_identity_doc", "modify_autopay",\n'
    '                             "update_search_filter", "add_to_cart", "create_service_ticket"):\n'
    '                logging.info(f"Shadow agent skipping state-modifying {func_name}.")\n                continue\n',
    '            # Recovery executes READ-ONLY lookups freely. State-modifying\n'
    '            # calls are re-issued by recovery ONLY if the primary\'s attempt\n'
    '            # was aborted pre-execution (user corrected mid-flight) — the\n'
    '            # idempotency registry still blocks any true duplicates.\n'
    '            if func_name in ("book_flight", "update_identity_doc", "modify_autopay",\n'
    '                             "update_search_filter", "add_to_cart", "create_service_ticket"):\n'
    '                probe_key = func_name + ":" + json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)\n'
    '                aborted = any(k.startswith(func_name + ":") for k in fnc_ctx.tracker.aborted_state_keys)\n'
    '                if not aborted:\n'
    '                    logging.info(f"Shadow agent skipping state-modifying {func_name} (no aborted attempt).")\n'
    '                    continue\n'
    '                logging.info(f"Shadow recovery re-issuing aborted state call {func_name}.")\n',
    "shadow may re-issue aborted state calls",
)

# ---- 5. entrypoint: record last_user_speech_at on every speaking event
rep(
    '    @session.on("user_state_changed")\n    def on_user_state_changed(ev: agents.voice.UserStateChangedEvent):\n        if ev.new_state == "speaking":\n            tracker.bump_generation()',
    '    @session.on("user_state_changed")\n    def on_user_state_changed(ev: agents.voice.UserStateChangedEvent):\n        if ev.new_state == "speaking":\n            tracker.last_user_speech_at = time.time()\n            tracker.bump_generation()',
    "track last_user_speech_at",
)

open(p, "w", encoding="utf-8", newline="\n").write(s)
print("")
print("prism_agent.py:", n, "P0 fixes applied")
