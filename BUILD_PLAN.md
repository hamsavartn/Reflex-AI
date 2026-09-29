# BUILD PLAN — Theme 5: Interruptible Real-Time Agents
### Samsung PRISM GenAI Hackathon 3.0 · v2.0 PIVOT (29 Sep 2026)

> **🚨 v2.0 PIVOT — the target changed.** `Theme05_Participant_Guide_UPDATED_FBD.docx` supersedes the old evaluation: the scored surface is now the **public FDB-v3 benchmark** (github.com/DanielLin94144/Full-Duplex-Bench, `v3/`, arXiv 2604.04847 — verified real) running against a **LiveKit voice agent** built from the two provided templates. Round 1 = 60% organizer-re-run benchmark score + 20% one extension use case + 20% docs/video. Video 3–5 min; deck ≤ 8 slides; one-command repro script; no keys in repo; no test-item memorization (DQ); no own servers; no cross-scenario caching.
> **What carries over (v1.1 work):** the generation-numbered interruption-recovery executor, idempotency registry (no duplicate state-changing calls), pending-confirmation semantics, and the virtual-clock test rig — these port into the custom LiveKit agent's tool-session layer and remain our differentiator, since the guide states **self-correction handling and multi-step tool chains are where scores are lost**. The old two-queue protocol/9-scenario kit is no longer the scored surface; keep it as internal deterministic unit tests only.
> **New critical path:** (1) clone FDB-v3 → (2) baseline template run (needs LiveKit Cloud + provider keys) → (3) custom agent with our recovery layer → (4) iterate on self-corrections + chained calls → (5) extension use case (device troubleshooting with camera frame — Samsung-relevant) → (6) repro script + logs → (7) video + 8-slide deck.
> **New blockers (user):** free LiveKit Cloud account; provider API key(s) — one OpenAI key covers realtime agent + gpt-4o judge + TTS; **confirm the new deadline** (old 25 Sep has passed; updated guide states none).
> History: v1.1 (external review integrated, old-spec scaffold 7/7 green, commit 0588ec1) · v1.0 (original plan vs old guide).

> **Verification status:** 83/83 general claims (`extracted/verify.py`) + 54/54 plan-critical claims (`extracted/verify_plan.py`) mechanically re-checked against extracted source text. Both scripts re-runnable.

> **Purpose of this document:** a self-contained handoff — full context, verified fact base, architecture, reasoning, verification evidence, and risk analysis. Written to be fed verbatim to any reasoning/research agent with zero prior knowledge of this conversation.
> **v1.1 — External review integrated:** a 14-page independent architectural review (user-provided) **validated** the generation-numbered cancellation model, virtual-clock harness, and speculation design, and mandated hardening for: (a) asyncio cancellation safety (`asyncio.shield`, registry-before-yield, pending-confirmation semantics), (b) safe/unsafe speculation gating (read-only speculative; state-modifying strictly serialized behind end-of-turn + validation), (c) a VAD-first audio pipeline (Silero VAD → distilled Whisper INT8, `condition_on_previous_text=False`, hardcoded language, chunked processing). All remediations are folded into §3.2 (decision 9), §3.3 (new invariant tests) and Part 8. One reviewer claim was softened: the guide's interface contract delivers audio as **discrete WAV clip events**, not a continuous mic stream — the "acoustic bottleneck" is therefore bounded, but every mitigation is still implemented because clips can contain silence, pauses, and long segments.

---

## PART 1 — FULL CONTEXT

### 1.1 The competition
- **Samsung PRISM GenAI Hackathon, 3rd Edition (2026–27)**, by the Language AI Team & PRISM Team, Samsung R&D Institute India. PRISM = "Preparing and Inspiring Student Minds".
- **One round**: a working multimodal/agentic prototype — no ideation stage. Submit: public/shared GitHub repo (+ README with Docker, release tag `PRISM_GENAI_HACKATHON_Y2026` on the judged commit), demo video ≤ 5 min, PPT (12-slide template provided), one Google Form submission. **Violating the submission guideline = direct disqualification** (stated twice in the deck).
- **Overall rubric**: Working prototype & functionality 30% · Technical depth & feasibility 25% · Innovation & originality 20% · Relevance to theme 15% · Presentation & documentation 10%.
- **Timeline**: launch 11 Sep · registration closed 16 Sep · **final submission 25 Sep 11:59 PM** · top 15 announced 9 Oct · final demo 15 Oct · results 24 Oct. As of 20 Sep: **5 days left**.
- Team rules: ≤ 4 members, single college, one theme, one submission.

### 1.2 The chosen theme — Theme 5: Interruptible Real-Time Agents (guide v1.0.0, 3 pp, fully read)

**Problem.** Standard assistants are half-duplex (listen → think → speak) and fail in full-duplex conversations where users interrupt, re-plan, or correct themselves mid-sentence. Technically a concurrency + state-consistency challenge: perception, reasoning, tool execution, and speech must run concurrently on a unified timeline.

**Required architecture (dual-process):**
- **Fast Path** — responsiveness within a few hundred milliseconds: acknowledgments, clarification, progress narration.
- **Slow Path** — asynchronous tools, multimodal processing, complex reasoning.
- **Coordination Layer** — non-blocking execution, call cancellation, state-snapshot updates, idempotency for state-modifying actions.

**Interface contract (§3):** the agent communicates over **two asynchronous queues** (timestamped events in; actions out).
- **Inputs:** transcribed text chunks (with end-of-turn markers), raw audio clips (WAV), video frames (PNG), interruption signals, asynchronous tool results, scenario tool manifests.
- **Outputs:** spoken fillers, non-blocking tool calls (explicit `call_id`), cancellations, clarification requests, final responses carrying structured **State Snapshots** (intent + slot values).

**Six core technical objectives (§3.2):**
1. Floor management — fast meaningful responses; **no false completion claims**; no excessive fillers.
2. Interruption recovery — promptly **cancel superseded in-flight tool calls (few-ms grace period)**, update snapshots, re-plan cleanly.
3. Session slot tracking — session-scoped slot state across multi-turn; localized slot corrections.
4. Schema-driven tools — parse dynamic tool definitions (**read-only vs state-modifying**) from manifests; **strictly avoid duplicate state-changing calls**.
5. Multimodal grounding — process raw audio/frames **behind** conversational acknowledgments; clarify ambiguous perceptions.
6. Protocol compliance — well-formed JSON payloads with valid snapshots/identifiers.

**Evaluation (§4–5):** scored **0–100 per scenario, strictly from trace logs**: Task Completion **40%** (correct tool execution, valid argument extraction, snapshot accuracy, final-response grounding) · Interruption Recovery **35%** (prompt cancellation of invalidated calls, **absence of stale re-runs**, updated snapshots) · Response Latency **15%** (time to **first substantive spoken action** after user input or interruption) · Safety & Protocol **10%** (zero duplicate state-changing calls, schema adherence, valid payloads). × quality multiplier **0.80–1.20** (transcript naturalness, truthfulness, relevance). Hidden multimodal scenarios × **1.5**. **Public suite: 9 canonical scenarios** (50% text / 30% audio / 20% visual) covering interruptions, chained calls, retries, clarifications, unseen tools. **Hidden set: ~60 scenarios** with edge cases and adversarial timing.

**Runtime constraints (§6):** **Python 3.10–3.12**, **120 s wall-clock cap per scenario**, **300 s setup/warm-up hook**, session-scoped memory only (no cross-session caching). Out of scope: wake-word detection, voice synthesis tuning, UI design. Focus areas: async event-loop orchestration, **speculative execution**, latency hiding, multimodal intent grounding.

**Mock environment (§4):** deterministic latency/fault injection for flight search, booking, ticket creation, frame-grounded manual lookups.

### 1.3 Verified environment facts
- Project `.venv` = Python 3.12 ✓ (within 3.10–3.12). Docker 29.7.2 ✓, Git 2.54.0 ✓, ffmpeg 9.0.1 ✓, Node 24 ✓.
- 291 skills installed in `.agents/skills/`; MCPs connected: context7 (+ built-in web_reader, node_repl). playwright/fetch/filesystem/desktop-commander configured but not surfaced this session — **not needed**.
- **Official evaluation kit NOT received** (released post-registration; not in folder, user searching). Mitigation in Part 4.

---

## PART 2 — DIRECT ANSWER: WHAT CAN WE BUILD WITHOUT THE OFFICIAL KIT?

**~90–95% of the entire system.** The kit is a *test rig*, not a dependency of the product. The guide (v1.0.0) specifies the interface contract precisely enough to build everything, including our own replica of the harness. Only **final protocol validation against the official harness** must wait for the kit.

| Component | Buildable without kit? | Depends on |
|---|---|---|
| Protocol layer (all event models, snapshots, manifests) | ✅ Yes | Guide §3 only |
| Dual-process agent core (fast/slow/coordination) | ✅ Yes | — |
| Interruption recovery engine + invariants | ✅ Yes | — |
| Session slot store | ✅ Yes | — |
| Schema-driven tool executor + idempotency | ✅ Yes | Guide §3.2.4 |
| Replica harness (virtual clock, replay, mock tools, trace, scorer) | ✅ Yes | Guide §4–5 |
| Synthetic scenarios + WAV/PNG assets | ✅ Yes | Windows TTS + ffmpeg + PIL |
| ASR (faster-whisper CPU) + frame grounding | ✅ Yes | pip install |
| LLM adapters (hosted/local, swappable) | ✅ Yes | User's key (optional to start) |
| Docker, README, PPT, disclosure, demo script | ✅ Yes | Template files in folder |
| **Official-kit adapter validation** | ⏳ Only when kit arrives | Organizers |

---

## PART 3 — WHAT WE BUILD, AND WHY (design decisions mapped to scoring)

### 3.1 Component list

```
PRISM_Z/
├── agent/                      # THE DELIVERABLE
│   ├── main.py                 # entrypoint: wires queues, boots agent (300s warm-up hook lives here)
│   ├── protocol/
│   │   ├── events.py           # pydantic models: every input/output event type
│   │   ├── snapshots.py        # StateSnapshot (intent + slot values), validators
│   │   └── manifests.py        # tool-manifest parser; read-only vs state-modifying classification
│   ├── core/
│   │   ├── agent.py            # top-level orchestrator: consumes input queue, fans out paths
│   │   ├── fast_path.py        # acks/fillers/progress narration (rule-based, ~200 ms virtual)
│   │   ├── slow_path.py        # LLM planning, tool orchestration, speculative execution
│   │   ├── coordinator.py      # cancellation registry, generation numbers, idempotency
│   │   ├── interruption.py     # grace-period logic, re-plan on interrupt
│   │   └── slots.py            # session slot state, localized corrections
│   ├── llm/
│   │   ├── base.py             # LLMAdapter interface (swap hosted/local/mock freely)
│   │   ├── hosted.py           # hosted API adapter (user key; async client)
│   │   └── local.py            # CPU local-model adapter (fallback)
│   ├── tools/
│   │   └── executor.py         # schema-driven async executor + idempotency guard
│   └── multimodal/
│       ├── asr.py              # faster-whisper (CPU) WAV → text, runs behind acks
│       └── frames.py           # PNG frame grounding (VLM adapter or heuristics)
├── harness/                    # REPLICA EVAL KIT (test rig — our quality gate)
│   ├── clock.py                # virtual clock: deterministic time, no wall-clock in agent
│   ├── player.py               # scenario replay → input queue (timestamped events)
│   ├── mocktools/              # flight search, booking, tickets, manual lookup (+latency/fault injection)
│   ├── trace.py                # complete event/action trace logging (JSONL)
│   ├── scorer.py               # 40/35/15/10 rubric + quality + multimodal multipliers
│   └── scenarios/              # ≥9 synthetic scenarios (JSON + WAV + PNG assets)
├── tests/                      # TDD invariant suite (see 3.3)
├── Dockerfile + docker-compose.yml + requirements.txt
├── README.md                   # reproducible setup (submission requirement)
└── deliverables/               # PPT fill, AI-disclosure fill, demo script, architecture diagram
```

### 3.2 Key design decisions — each one earns points

1. **Protocol-first, pydantic everywhere** → *Safety & Protocol 10% + Task 40%.* Every event in/out is a validated model; invalid payloads are structurally impossible to emit. Exact adherence to guide §3 wording because a format mismatch against the hidden harness = zero score.
2. **Generation-numbered tool calls** → *Interruption Recovery 35% (the biggest lever).* Every in-flight tool call carries the state-generation number that spawned it. An interruption bumps the generation; the coordinator cancels all calls whose generation < current within the few-ms grace window; late results from cancelled calls are detected by generation mismatch and dropped — mechanically guaranteeing "absence of stale re-runs" and "prompt cancellation of invalidated calls".
3. **Idempotency registry** → *Safety 10% ("zero duplicate state-changing calls").* Before emitting any state-modifying call, the registry is checked for the same (intent + normalized params) in-flight or completed. This is a testable invariant, not a hope.
4. **Rule-based fast path, LLM only in slow path** → *Latency 15%.* Fillers/acks are template emissions (~few ms of compute), guaranteeing "first substantive spoken action" lands in the few-hundred-ms budget without waiting on any model. LLM latency never blocks the voice.
5. **Speculative execution on partial transcripts** → *Latency 15% + focus area.* The slow path begins planning on text chunks *before* the end-of-turn marker; the plan is revised as chunks arrive. This is the guide's own listed focus area.
6. **Injected virtual time** → *Testability + determinism.* The agent never reads wall-clock; time is an injected dependency. The 120 s/scenario budget becomes a testable property, and our harness replays scenarios deterministically.
7. **Trace-first with reason codes** → *Quality multiplier 0.80–1.20 + our debugging.* Every decision logs why (e.g., `FILLER_ACK`, `CANCEL_GEN_MISMATCH`, `CLARIFY_SLOT_CONFLICT`). Truthful narration = no false completion claims; the trace is our audit trail.
8. **Thin protocol adapter** → *Drift insurance.* All wire-format knowledge lives in `protocol/` + a `kit_adapter.py` seam. When the official kit arrives, only the adapter changes; core logic is untouched.
9. **ASR = VAD-first distilled Whisper on CPU** → *30% of scenarios are audio + the 1.5× hidden multimodal multiplier.* Pipeline per incoming WAV clip: **Silero VAD gatekeeper** (faster-whisper's built-in `vad_filter=True`) strips silence/non-speech — Whisper is documented to hallucinate blocks of phantom text on silence, which would poison the speculative planner and slot tracker — then **`Systran/faster-distil-whisper-large-v3` with INT8 quantization** (≈6× faster than large; minimal accuracy tradeoff on short conversational audio; keeps RTF well inside the 120 s budget on CPU), with **`condition_on_previous_text=False`** per independent chunk (blocks hallucination-loop traps; app-level sliding-window stitching at the orchestration layer preserves cross-chunk context) and **`language="en"` hardcoded** (removes the per-chunk auto-detect latency tax; configurable). Frames: pluggable VLM adapter; heuristics fallback so multimodal paths never hard-fail.
10. **Session-scoped store, nothing persistent** → *Constraint compliance.* No cross-session caching anywhere by construction.

### 3.3 Scoring → feature → test traceability

| Scoring criterion (weight) | Feature | Test that proves it |
|---|---|---|
| Task completion (40%) | Manifest-driven planner, argument extraction, snapshot validator | Per-scenario golden traces: correct tool, args, final snapshot |
| Interruption recovery (35%) | Generation numbers, cancellation registry, stale-drop | `test_cancel_within_grace`, `test_no_stale_rerun`, `test_snapshot_updated_after_interrupt` |
| Response latency (15%) | Rule-based fast path, speculative slow path | `test_first_spoken_action_under_budget` (virtual clock) |
| Safety & protocol (10%) | Pydantic gates, idempotency registry | `test_zero_duplicate_state_calls` (property: across N interrupts), schema round-trip tests |
| Quality ×0.80–1.20 | Filler etiquette, no false completion, clarifications | `test_no_completion_claim_before_tool_done`, filler-rate ceiling test |
| Multimodal ×1.5 | ASR + frame paths behind acks | Audio-scenario + frame-scenario end-to-end |
| Interruption recovery (35%) — cancellation safety | Registry-before-yield; state-modifying records survive cancellation as `PENDING_CONFIRMATION` | `test_cancelled_state_call_stays_blocked`, `test_late_result_dropped_by_generation` |
| Safety (10%) — race hardening | Synchronous-only critical sections (+ `asyncio.shield` where awaits are unavoidable) around snapshot/registry mutations | `test_state_mutation_atomic_under_cancel` |
| 120 s cap / warm-up | Injected clock, warm-up hook | Budget test on longest scenario |

### 3.4 Build phases (20 → 25 Sep)

- **Phase 0 (today):** repo init + `.gitignore`, install libs into `.venv` (pydantic, pytest-asyncio, faster-whisper, numpy, soundfile, Pillow), protocol models v0, LLM adapter interface. *No kit needed.*
- **Phase 1 (today–21st):** replica harness core: virtual clock, scenario player, 4 mock tools with latency/fault injection, JSONL trace. 3 text scenarios. *This is our TDD rig.*
- **Phase 2 (21–22nd):** agent core with invariant TDD: fast path, coordinator, interruption engine, slots. LLM behind a mock adapter so tests stay deterministic.
- **Phase 3 (22–23rd):** real LLM adapter (user key) + schema-driven executor + idempotency; ASR + frame grounding; audio/visual scenarios (Windows SAPI TTS → WAVs, PIL → PNGs).
- **Phase 4 (23–24th):** scorer implementation, full 9-scenario run + adversarial-timing suite (double-interrupt, interrupt-during-tool, unseen tool, mid-plan goal switch); Docker, README, architecture diagram.
- **Phase 5 (24–25th):** official-kit swap-in when it arrives; polish; PPT via pptx skill, disclosure fill, demo script, release tag `PRISM_GENAI_HACKATHON_Y2026`, video, Google Form.
- **Parallel (user):** chase kit, provide LLM key, GitHub push, record video, submit form.

---

## PART 4 — CHAIN OF VERIFICATION & DEVIL'S ADVOCATE

### 4.1 Verification evidence (chain of verification)
- Full-file reads: deck 15/15 pp, T1 guide 4/4, T5 guide 3/3, PPT 12/12 slides + notes, DOCX 41/41 ¶, invite PNG. Raw-OOXML cross-checks found nothing missed.
- **83/83** general factual claims mechanically verified (`extracted/verify.py`).
- **54/54** plan-critical claims re-verified immediately before writing this plan (`extracted/verify_plan.py`) — interface contract, invariants, scoring weights, runtime caps, kit description, deck cross-checks.
- Notably verified: "scored 0–100 based strictly on trace logs"; "within few ms grace period"; "strictly avoid duplicate state-changing calls"; "time to first substantive spoken action"; "Python 3.10 3.12"; "120s wall-clock cap per scenario, 300s setup/warm-up hook"; "nine canonical scenarios"; "~60 scenarios".

### 4.2 Devil's advocate (criticisms taken seriously)

| # | Criticism | Response / mitigation |
|---|---|---|
| D1 | "Your replica will drift from the official kit; everything tuned to the wrong harness." | Real risk. Mitigations: (a) protocol layer mirrors guide §3 *word-for-word*; (b) thin `kit_adapter.py` seam isolates wire-format knowledge; (c) core logic + invariants are format-agnostic; (d) Phase 5 exists solely for swap-in. Worst case, we lose tuning time, not correctness. |
| D2 | "Building a replica harness is wasted effort if the kit arrives tomorrow." | No — the replica is the TDD rig regardless (you cannot write invariant tests without a clock+mocks), it implements the scorer so we self-evaluate, and it doubles as the innovation/demo story. Even organizers expect you to test locally. |
| D3 | "The agent's quality hinges on an LLM key you don't have yet." | The LLM sits behind an adapter. Phases 0–2 run fully on a deterministic mock adapter. Key plugs in Phase 3. Worst-case fallback: CPU local model (weaker naturalness ×0.80–1.20, but Task/Interruption/Safety are LLM-light). |
| D4 | "ASR on CPU may mis-transcribe scenario WAVs." | faster-whisper `small` is adequate for command-style utterances; scenarios are synthetic or kit-provided (likely clean). The 30% audio share makes this worth it; kit WAVs may even ship with transcripts. |
| D5 | "5 days is tight for this scope." | Priorities are scoring-ordered: invariants (75% of trace score) first, multimodal (multiplier) second, polish last. Phases 0–2 deliver the point-winning core. PPT/video are 10%-rubric items with fixed templates — scheduled but capped. |
| D6 | "The real scorer may weight differently than the published rubric." | The weights are published in the guide; invariants like zero-duplicates and prompt cancellation are unambiguous regardless. We optimize the published rubric — it's the only defensible target. |
| D7 | "Over-engineering: a full dual-process system in 5 days?" | Scope is bounded by the mock domain (4 tool types, session-scoped state). No memory systems, no wake-word, no TTS tuning — explicitly out of scope by the guide. The complexity budget goes to concurrency correctness, which is exactly what's scored. |
| D8 | "Hidden scenarios test *unseen tools* — your executor might choke." | By design: manifests are parsed dynamically at runtime (§3.2.4), tools are executed schema-driven, and scenarios include unseen-tool cases in our replica suite. Unseen tool handling is a first-class test, not an afterthought. |
| D9 | "Session-scoped only — but evaluators may restart scenarios to probe leakage." | No cross-session state exists by construction (store created per session object; nothing written to disk). |
| D10 | "Why not just use a heavy agent framework (LangGraph etc.)?" | Guide says simple-and-cheap beats heavy orchestration (Theme 4's principle, and T5's focus is *our own* async orchestration). Frameworks also add nondeterminism we can't control inside a 120 s budget. Hand-rolled asyncio is the differentiator. |

### 4.3 Residual risks (honest)
1. Official kit arrives late/never → we submit on the replica-validated agent with the adapter seam (documented in README as design for adaptability). Score risk on format mismatch exists but is minimized by §3-word-for-word protocol.
2. Quality multiplier is partially subjective → mitigated by conservative, truthful narration style and no-false-claims invariant.
3. Frame grounding without a VLM key may underperform on 20% visual scenarios → pluggable adapter; recommend user provides hosted key to cover it.

---

## PART 5 — SKILLS / MCP / TOOLING UTILIZATION MAP

| Phase | Skills invoked (.agents/skills, 291 installed) | MCP/tools |
|---|---|---|
| Protocol + architecture | `agent-harness-construction`, `autonomous-agent-harness`, `hexagonal-architecture`, `error-handling` | context7 (pydantic/asyncio docs) |
| Harness + scoring | `eval-harness`, `agent-eval`, `benchmark-methodology` | — |
| Core + invariants | `tdd-workflow`, `python-testing`, `async-jobs`, `latency-critical-systems`, `verification-loop` | context7 |
| Debugging | `systematic-debugging`, `agent-introspection-debugging` | — |
| Multimodal | `pytorch-patterns` (faster-whisper deps), `python-patterns` | context7 |
| Delivery | `docker-patterns`, `deployment-patterns`, `presentations:pptx` (skill), `documents:docx` (disclosure), `verification-before-completion` | node_repl (optional: browser-driven demo clips) |
| Final gate | `verification-before-completion`, `delivery-gate` | — |

**New MCPs needed: none. External skills needed: none.** Everything required is already installed; the only external items are runtime credentials (LLM key, GitHub) and the kit.

---

## PART 6 — WHAT ONLY THE USER CAN PROVIDE (unchanged, priority order)

1. 🔴 **Official evaluation kit** (email `prism@samsung.com` if not found — draft email already provided in chat).
2. 🔴 **LLM API key** + hosted-vs-local decision (hosted recommended for the quality multiplier & visual grounding).
3. 🔴 GitHub push + release creation (I prepare everything locally).
4. 🔴 Record 5-min demo video (I provide script; OBS/Game Bar).
5. 🔴 Google Form submission by **25 Sep 11:59 PM** (+ confirm registration was completed by 16 Sep).
6. ✅ Already in place: Docker, Git, ffmpeg, Node, Python 3.12 venv, all skills/MCPs, templates.

---

## PART 7 — SUCCESS CRITERIA (definition of done)

1. All 9 replica scenarios pass with self-scored ≥ 90/100 pre-multiplier on our scorer, including the adversarial-timing suite.
2. Invariant tests green: zero duplicate state-changing calls; zero stale re-runs; cancellation within grace; no completion claims before tool completion; first-substantive-action under latency budget.
3. Agent runs end-to-end in Docker on CPU within 120 s virtual per scenario; warm-up < 300 s.
4. README enables clone→docker-run→replay a scenario in ≤ 3 commands.
5. Release tag `PRISM_GENAI_HACKATHON_Y2026` contains code + PPT + docs; video ≤ 5 min; form submitted before deadline.
6. If the official kit arrives: adapter validated against it and all 9 official scenarios replayed locally before submission.

---

## PART 8 — v1.1 EXTERNAL REVIEW INTEGRATION (remediation spec)

The independent review's verdict: architecture is "structurally sound, highly innovative"; generation-numbered calls are "a mathematically verifiable defense against stale state re-runs"; the virtual-clock harness is methodologically superior to wall-clock testing. It demanded the following hardening, all now normative for this build:

### 8.1 asyncio cancellation safety (review §4.2)
- **Problem:** `CancelledError` is injected at the coroutine's next `await` point, not preemptively. If it lands inside a critical state mutation (slot-store dict update, idempotency-registry write), state is left partially mutated → snapshot corruption → lost points in Task (40%), Interruption (35%), and Safety (10%) simultaneously.
- **Rules (normative):**
  1. Critical sections that mutate session state or the registry contain **no `await`** — they run synchronously to completion (dict/set operations only), making them atomic by construction under the single-threaded event loop.
  2. Where an unavoidable `await` sits near a mutation (e.g., async cleanup), the mutation is wrapped in **`asyncio.shield()`** and the cleanup runs in a finally-block that re-checks generation before applying.
  3. All tool-boundary waits are cancellation scopes: on interrupt, the coordinator cancels the *task*, releases resources immediately, and never blocks the loop waiting for a defunct network response.
  4. Tests assert the invariant: a `CancelledError` delivered at any interleaving leaves the snapshot either fully-old or fully-new, never mixed (property-style test with randomized interruption points).

### 8.2 Idempotency registry — registry-before-yield + pending-confirmation (review §4.3)
- **Problem:** the race — user interrupts *after* a state-modifying call is transmitted to the environment but *before* its response returns. External state has mutated; the agent's tracking task is cancelled. A naive registry loses the record → the agent may double-book when the user resumes the same intent.
- **Rules (normative):**
  1. The registry records intent + normalized params **synchronously, before the first `await`** that transmits the call (registry-before-yield).
  2. On cancellation of a state-modifying call, the record is **retained** and marked `PENDING_CONFIRMATION` (transmitted, unconfirmed). It blocks duplicate emits for the same (tool, normalized-params) key until a tool result or timeout resolves it.
  3. `DONE` records serve as an idempotent cache: re-requesting the exact same intent+params returns the recorded result instead of re-emitting (prevents double-booking on resume).
  4. Read-only calls: cancellation simply drops the record (no external side effects).
  5. Tests: `test_cancelled_state_call_stays_blocked`, `test_no_duplicate_state_calls`, `test_late_result_dropped_by_generation`.

### 8.3 Safe vs unsafe speculation gating (review §5.2)
- **Rule:** read-only tools (search/lookup/get per manifest classification) may execute **speculatively on partial transcripts**; results are used only when they exactly match the finalized authoritative request, else discarded as an unused branch (lossless).
- State-modifying tools are **never** speculative: gated behind the definitive end-of-turn marker, a validated final snapshot, and cleared safety invariants; serialized (one in-flight state mutation per session at a time).

### 8.4 VAD-first audio pipeline (review §6 — the "critical flaw", adopted with one nuance)
- **Nuance (our correction to the reviewer):** the contract delivers audio as **discrete WAV clip events** (`raw audio clips (WAV)` in §3), not an unbounded mic stream — so the 30-second-window pathology is bounded. Nonetheless clips contain silence/pauses/long segments, so every mitigation applies:
  1. **Silero VAD** before Whisper (faster-whisper `vad_filter=True`) — no transcription of silence → no hallucination poisoning of planner/slots, no wasted 120 s budget.
  2. **Distilled model + INT8**: `Systran/faster-distil-whisper-large-v3`, `compute_type="int8"` — ≈6× faster than large; large models on CPU at RTF≈0.5 would burn 60 s of the 120 s budget on 30 s of audio; distil+INT8 keeps the whole pipeline comfortably inside budget.
  3. **`condition_on_previous_text=False`** for each independently-processed speech segment; **app-level sliding-window stitching** at the orchestration layer re-joins segment transcripts without importing Whisper's hallucination-loop failure mode.
  4. **`language="en"` hardcoded** (configurable) — avoids the ~50 ms/chunk auto-detect penalty.
  5. HuggingFace model downloads will be directed to a **project-local cache dir** (respecting the workspace-only rule).
- Tests: silence-only clip yields zero text events; multi-segment clip yields stitched transcript; chunk latency bounded (virtual clock).

### 8.5 Reviewer claims cross-checked
| Review claim | Our verdict |
|---|---|
| Whisper hallucinates on silence/non-speech | ✅ Correct, well documented — adopted |
| `condition_on_previous_text` default True can trap streaming in hallucination loops | ✅ Correct — adopted (False + app stitching) |
| Distil-large-v3 INT8 required for CPU RTF | ✅ Correct — adopted |
| asyncio.shield for state mutations | ✅ Adopted, tightened: sync-only critical sections preferred |
| Registry must retain transmitted-but-cancelled state calls | ✅ Correct classic distributed-systems race — adopted (8.2) |
| "Continuous raw audio streams" premise | ⚠️ Softened: contract delivers discrete WAV clip events; mitigations still adopted |
| Read-only tools may speculate; state-modifying never | ✅ Matches guide's read-only vs state-modifying split — adopted |
