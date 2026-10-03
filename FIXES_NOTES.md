# FIXES_NOTES.md — Errors Found, Fixes Applied, and Honest Accuracy Targets
**Date:** 2026-10-02 · **Applies to:** `fdb3/v3/prism_agent.py`, `fdb3/v3/run_tool_benchmark.py` · **Deadline: Oct 4**

---

## 1. Errors found in the post-handoff work (audit of user + prior-agent changes)

### E1 — Shadow agent executed tools on PARTIAL transcripts 🔴 (fixed)
`user_input_transcribed` fires for every interim transcript. Without an
`is_final` gate, the shadow agent parsed half-finished utterances and
**executed tools for retracted intents** ("book LHR… [pause]… no wait, JFK"
→ booked LHR mid-pause). Direct cause of a large share of the **56
wrong-tool failures** in the 100-run report.
**Fix:** `if not getattr(msg, "is_final", False): return` before any shadow
work. (Verified: the event's field is `is_final`, not `interim`.)

### E2 — Telemetry path could silently mismatch between agent and scorer 🔴 (fixed)
The runner had been changed to read `parent.parent.parent/logs/…` (project
root) while the agent writes CWD-relative `logs/…`. It worked only because
the worker happened to be launched from one specific directory on this
machine. On the organizers' clean-machine re-run, any CWD difference →
`actual_tool_calls` read as empty → **benchmark portion ≈ 0**.
**Fix (Fix 2):** both sides now resolve the same path: `PRISM_TOOL_LOG` env
var, else `<benchmark script dir>/logs/agent_tool_calls.log`. Agent and
scorer cannot disagree anymore, on any machine, any CWD.

### E3 — `log_tool_call` silently deduplicated the scored log 🔴 (fixed)
A `logged_calls` set suppressed the second occurrence of an identical
(function, args) call. The benchmark's ground truth ("what actually ran")
no longer matched reality — extra calls (a scored penalty) became invisible.
**Fix:** every execution is logged. Also added `last_tool_at` timestamp used
by the recovery gate.

### E4 — Instructions conflicted: "MUST wait for final intent" vs benchmark immediacy 🟡 (fixed)
The rewrite told the model to *wait* before acting while the benchmark
rewards immediate execution; combined with a fixed 1.0 s pre-execution sleep
on state tools this encouraged hesitation → missed/extra calls.
**Fix (Fix 5):** immediacy restored as the primary directive; self-correction
is handled by (a) "use ONLY the final corrected value, re-issue if you acted
on a retracted one" and (b) the (now 0.5 s) deliberation window — the
platform, not model hesitation, provides the safety.

### E5 — Shadow agent double-executed read-only tools 🟡 (fixed)
Both the realtime model and the shadow could call the same read tool
(together with E3's dedupe, this hid the duplicate from the log).
**Fix (Fix 6):** the shadow is now a **recovery net**, not a parallel actor:
it waits a 6 s quiet window, stands down if the primary produced any tool
activity, and executes **read-only lookups only** — state-modifying calls are
never its job. This is the dual-process pattern from BUILD_PLAN §8.3.

### E6 — `PRISM_Z_Colab.zip` was corrupt 🔴 (fixed)
`BadZipFile` on open. **Fix:** rebuilt from the bundle directory; integrity
tested (`testzip()` clean, 9 entries, 0.04 MB).

### E7 — `Benchmark_Results.zip` shipped ~700 MB of WAVs 🟡 (fixed)
Organizers already have the public audio; shipping it back is noise.
**Fix:** rebuilt as results-only (JSONs + reports + logs). See §3.

### E8 — Cosmetic 🟢 (noted, not blocking)
Mojibake characters in source comments; instructions said "12 APIs" while 15
tools exist; `tracker.tool_start_at` is shared across concurrent calls
(latency breakdown can race — cosmetic only; the scored timestamps in the
tool log are per-call and correct); `run_concurrent.py` shares one ASR model
across threads — dev-only tool, the official sequential runner is used for
all reported numbers.

---

## 2. Fixes applied (all in `prism_agent.py` unless noted) — compile-checked

| Fix | What | Where |
|---|---|---|
| 1 | Final-transcript-only gate | shadow handler |
| 2 | Pinned telemetry path (env `PRISM_TOOL_LOG` / script dir) both sides | agent + `run_tool_benchmark.py` |
| 3 | Faithful per-execution logging; `last_tool_at` added | `log_tool_call` |
| 5 | State deliberation window 1.0 s → 0.5 s; immediacy instructions restored; final-value rule added | `idempotent_state_modifier`, instructions |
| 6 | Shadow → quiet-window (6 s) recovery net, read-only only, stands down on primary activity | shadow agent |

Kept unchanged (they were correct): idempotency registry with
registry-before-yield (`SENT` → shield → `DONE` / `PENDING_CONFIRMATION`),
generation bump on user speech start, `asyncio.to_thread` for mock API calls,
extension tools, argument-format rules in the prompt.

---

## 3. Validation & next steps

- **Validation set** (`fdb_v3_data_val/`): the 5 hardest cases — hard
  difficulty + `state_rollback_test:true` + SELF_CORRECTION (where the
  baseline scored 6–17%) — plus the known-good ecommerce_01. Baseline on
  these specific cases is expected ≤ ~20%; if the fixed agent passes ≥ 3/5
  hard cases, the fixes are working.
- **Full 100-sample run:** user-requested on **Colab GPU** via
  `PRISM_FDB3_Colab.ipynb` + fresh `PRISM_Z_Colab.zip` (integrity-verified).
  The notebook is resumable (skips existing `result_prism.json`) and packages
  results-only JSONs for download.
- **Old `Benchmark_Results.zip`:** superseded — regenerate as results-only
  after the 100-run (the notebook's step 8 produces exactly this).

## 4. Honest accuracy statement (read before quoting numbers)

The user's target is 90–95% strict pass. **No published system on FDB-v3 is
near that; the strict metric requires every expected call with exact/semantic
arguments and zero extras, on disfluent human audio.** Our own 100-run
baseline (pre-fixes) = **29%**. What the fixes legitimately target:
removing the wrong-tool penalty (E1/E5), correct rollback behavior on
self-corrections, and argument-format discipline already in the prompt —
plausibly moving strict pass into the **40–60% band** and tool-F1 higher.
**Chasing 90+ by tailoring to known test items would violate the
benchmark's explicit no-memorization rule (automatic disqualification, "we
check").** We report what the fixed agent honestly scores; the deck should
present baseline-vs-final delta and failure-mode analysis — that is the
strong, defensible story.

## 5. Reproducibility notes for the official re-run

- One-command path: Colab notebook (or `reproduce.sh` equivalent locally).
- Requirements pinned from `.venv-fdb` (freeze before submission).
- Patches to the vendored benchmark are explicit files in `fixes/` +
  documented in `colab/README_COLAB.md` (upstream is CC BY-NC — we vendor
  with attribution and disclose every modification).
- Keys: LiveKit + Gemini only; declared in README, never committed.

---

## 6. Addendum (Oct 3): the soxr assert saga — root cause of the "silent agent"

**Symptom chain:** agent joins rooms but produces no transcripts/speech/tool
calls; worker exits code 3 / 4294967295; "job executor is unresponsive".

**Root cause (confirmed by on-screen dialog):** `livekit_ffi.dll` raises a CRT
assert — `soxr-sys/src/fftf4g_cache.h:13 LSX_FFT_BR == NULL` — a thread-race
in the soxr FFT cache when a worker's SECOND audio stream initializes. While
the Windows modal is up, the process is frozen (looks like silence). Outcome
is timing-dependent: fresh worker + 1 job = fine (Oct 2 smoke); 2nd job =
crash; jobs dispatched to a dead worker are answered by the next worker
joining after the user audio ended → babble, zero calls.

**Mitigations applied (Windows local):**
- `fixes/auto_ignore_assert.ps1` — UIAutomation watcher clicks **Ignore**
  (safe: benign double-init) whenever the dialog appears.
- `fdb3/v3/worker_supervisor.sh` — restarts the worker on any death until
  `STOP_WORKER` exists; the batch runner resumes (skips completed results).
- `.venv-fdb/.../sitecustomize.py` — best-effort CRT-assert→stderr routing
  (the DLL links its own CRT, so the modal can still appear; the watcher
  covers that).

**Decision:** the **100-sample run runs on Colab/Linux** (user's plan) — no
Windows modal there; the notebook now starts the worker inside a supervised
restart loop, and the batch is resumable. Expect ~1 restart per worker
lifetime on Linux if the race fires there; cost ≈ seconds per example.

**Honest status of the local val runs:** 2 examples completed but with empty
agent behavior (worker-death timing), so the P0 fixes remain unvalidated
locally. Validation will be read from the Colab run's first results instead
(benchmark `ecommerce_01` + a self-correction case are early in the set).
