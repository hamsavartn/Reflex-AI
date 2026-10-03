# One-shot patcher: verification gate (text-LLM validates/corrects tool calls)
# Informed by aggregate failure mining of our own 100-sample baseline:
#   45 scenarios MISSING_ONLY (model answered with words, never acted)
#   31 EXTRA+missing (premature stale call, corrected call never landed)
#   search_flights.destination/date wrong in 15
# Gate design: while the quiet-wait runs, a fast text model checks the
# proposed call against the user's final transcripts; stale args are
# corrected before execution; inconsistent calls are aborted pre-execution.
p = "fdb3/v3/prism_agent.py"
s = open(p, encoding="utf-8").read()
n = 0

def rep(old, new, why):
    global s, n
    assert old in s, "NOT FOUND: " + why
    s = s.replace(old, new, 1)
    n += 1
    print("OK :", why)

# ---- 1. the gate function (module level, before the decorators)
GATE = '''

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
        "You verify voice-agent tool calls. The user's spoken request transcript "
        "may contain self-corrections; the FINAL stated intent is what counts.\\n"
        f"TRANSCRIPT: {transcript[-900:]}\\n"
        f"PROPOSED CALL: {fn_name}({json.dumps(args)})\\n\\n"
        "Reply with ONLY a JSON object:\\n"
        '{"verdict": "ok" | "correct" | "reject", '
        '"args": {<corrected arguments if verdict is "correct", else unchanged>}, '
        '"reason": "<5 words>"}\\n'
        "Rules: verdict=correct when any argument value is a retracted value the user "
        "overrode (use the final value); verdict=reject when the tool does not match "
        "the user's final request at all; verdict=ok otherwise. Never invent new "
        "arguments that the user never said."
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
                config=types.GenerateContentConfig(response_mime_type="application/json"),
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

'''
anchor = "def deliberation_window(delay=0.3):"
assert anchor in s
s = s.replace(anchor, GATE + "\n" + anchor, 1)
n += 1
print("OK : verification gate function")

# ---- 2. wire the gate into the state-tool decorator (before SENT)
old_state = """        start_gen = self.tracker.generation
        deadline = asyncio.get_running_loop().time() + 8.0
        try:
            loop = asyncio.get_running_loop()
            while loop.time() < deadline:"""
new_state = """        start_gen = self.tracker.generation
        deadline = asyncio.get_running_loop().time() + 8.0
        # PRISM gate: verify args against the final transcript in parallel
        # with the quiet-wait; corrected args replace stale ones pre-execution.
        gate_task = None
        if GATE_ENABLED:
            gate_task = asyncio.create_task(
                verify_call(self.tracker.last_transcript, func.__name__, dict(kwargs)))
        try:
            loop = asyncio.get_running_loop()
            while loop.time() < deadline:"""
rep(old_state, new_state, "gate wired into state decorator (pre-SENT)")

old_exec = """        # Mark as SENT before yielding
        registry[key] = ("SENT", None)
        
        # Execute and shield from cancellation
        try:
            result = await asyncio.shield(func(self, *args, **kwargs))"""
new_exec = """        # Gate verdict: apply corrected args / reject before committing
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
            result = await asyncio.shield(func(self, *final_kwargs, **{}))"""
rep(old_exec, new_exec, "gate verdict applied pre-execution (state tools)")

# the state tool body reads kwargs from *args/**kwargs of the inner func call:
# asyncio.shield(func(self, *final_kwargs, **{})) — wrong; must pass final_kwargs as kwargs.
rep(
    "            result = await asyncio.shield(func(self, *final_kwargs, **{}))",
    "            result = await asyncio.shield(func(self, **final_kwargs))",
    "final_kwargs passed correctly",
)

# ---- 3. wire the gate into the read-tool decorator (current text)
old_read = """            key = func.__name__ + ":" + json.dumps(kwargs, sort_keys=True, ensure_ascii=False, default=str)
            cached = self.tracker.read_cache.get(key)
            if cached is not None:
                logging.info(f"Read idempotency hit: {key}")
                return cached
            result = await func(self, *args, **kwargs)
            self.tracker.read_cache[key] = result
            return result"""
new_read = """            # PRISM gate for read tools: correct stale args pre-execution.
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
    return decorator"""
rep(old_read, new_read, "gate wired into read decorator")

# ---- 4. tracker.last_transcript: keep the latest FINAL transcript
rep(
    """        self.last_user_speech_at = 0.0
        self.aborted_state_keys = set()  # state keys aborted pre-execution
        self.read_cache = {}  # (tool,args)->result for read-tool idempotency""",
    """        self.last_user_speech_at = 0.0
        self.aborted_state_keys = set()  # state keys aborted pre-execution
        self.read_cache = {}  # (tool,args)->result for read-tool idempotency
        self.last_transcript = ""  # latest FINAL user transcript (gate input)""",
    "tracker.last_transcript",
)
rep(
    '''        transcript = getattr(msg, 'transcript', getattr(msg, 'text', ''))
        if transcript:''',
    '''        transcript = getattr(msg, 'transcript', getattr(msg, 'text', ''))
        if transcript and getattr(msg, "is_final", False):
            fnc_ctx.tracker.last_transcript = transcript
        if transcript:''',
    "record last_transcript on final transcripts",
)

open(p, "w", encoding="utf-8", newline="\n").write(s)
print("")
print("prism_agent.py:", n, "verification-gate patches applied")
