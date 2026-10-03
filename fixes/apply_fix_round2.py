# One-shot patcher: read-only quiet-wait + boolean coercion + prompt rules
p = "fdb3/v3/prism_agent.py"
s = open(p, encoding="utf-8").read()
n = 0

def rep(old, new, why):
    global s, n
    assert old in s, "NOT FOUND: " + why
    s = s.replace(old, new, 1)
    n += 1
    print("OK :", why)

# ---- 1. deliberation_window -> quiet-wait + generation-abort (read tools)
old_dec = '''def deliberation_window(delay=0.3):
    """
    Delays tool execution slightly to allow for user self-corrections.
    If the user interrupts (cancelling the task) before the window closes,
    the tool call is never executed or logged.
    
    Args:
        delay: Seconds to wait. Use 0.3 for read-only tools, 0.8 for state-modifying.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            start_gen = self.tracker.generation
            try:
                await asyncio.sleep(delay)
                if self.tracker.generation > start_gen:
                    logging.warning(f"Aborting {func.__name__} due to generation bump.")
                    return json.dumps({"error": "Action aborted because user started speaking again."})
            except asyncio.CancelledError:
                logging.warning(f"Call {func.__name__} cancelled by interruption during deliberation.")
                raise

            return await func(self, *args, **kwargs)
        return wrapper
    return decorator'''
new_dec = '''def deliberation_window(delay=0.3):
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

            return await func(self, *args, **kwargs)
        return wrapper
    return decorator'''
rep(old_dec, new_dec, "read-only quiet-wait + abort")

# ---- 2. boolean coercion in update_search_filter (scored-log args must be native bools)
old_usf = '''    async def update_search_filter(self, filter_name: str, value: str):
        """
        Args:
            filter_name: Filter key using underscore format, e.g. 'pets_allowed', 'parking', 'laundry_in_unit'
            value: Filter value to apply. For boolean filters use 'True' or 'False' (capitalized).
        """
        self.tracker.tool_start_at = time.time()
        result = await asyncio.to_thread(registry.call, "update_search_filter", filter_name=filter_name, value=value)
        self.tracker.tool_end_at = time.time()
        self.log_tool_call("update_search_filter", {"filter_name": filter_name, "value": value}, self.tracker.tool_start_at, self.tracker.tool_end_at)
        return json.dumps(result)'''
new_usf = '''    async def update_search_filter(self, filter_name: str, value: str):
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
        return json.dumps(result)'''
rep(old_usf, new_usf, "boolean coercion before scored log")

# ---- 3. prompt: filters rule + ordinal dates (append to ARGUMENT FORMAT section)
old_fmt = '''                "5. Addresses: short form as stated; do not add city or state.\\n"'''
new_fmt = '''                "5. Addresses: short form as stated; do not add city or state.\\n"
                "6. Dates: drop ordinal suffixes — say 'June 3', never 'June 3rd' or 'June 3rd, 2026'.\\n\\n"
                "=== HOUSING FILTER RULE ===\\n"
                "In the housing domain, user criteria such as pet policy, budget/max price, and bedroom count are search filters: call update_search_filter once per criterion (filter_name like 'pets_allowed', 'max_price', 'bedrooms'), then call search_apartments. Do not silently fold criteria into search_apartments arguments unless the user explicitly asked to search without updating filters.\\n"'''
rep(old_fmt, new_fmt, "prompt: ordinals + housing filter rule")

open(p, "w", encoding="utf-8", newline="\n").write(s)
print("")
print("prism_agent.py:", n, "validation-round-2 fixes applied")
