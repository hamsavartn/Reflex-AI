# HANDOFF.md — Complete Project State & Continuation Guide
### Samsung PRISM GenAI Hackathon 3.0 · Theme 5: Interruptible Real-Time Agents
**Last updated:** 2026-09-30 ~19:10 IST · **Author:** ZCode build session · **Purpose:** any AI agent (or human) can continue exactly where this leaves off, with full intent and zero re-discovery.

---

## 0. ONE-PARAGRAPH SUMMARY

We are building a **LiveKit voice agent** scored on the public **FDB-v3 benchmark** (Round 1 = 60% organizer-re-run benchmark + 20% one extension use case + 20% docs/video). The pipeline is **fully working end-to-end on this machine** (Windows, CPU-only): benchmark cloned, 100-example data extracted, LiveKit+NeMo installed in a project venv, Gemini agent worker registers with LiveKit Cloud, a single example ran through inference+ASR successfully after fixing **two real bugs in the vendored benchmark code** (CPU-only `.cuda()` crash; livekit-agents 1.8 "Plugins must be registered on the main thread" crash). Remaining work: full 100-example baseline, custom agent with our interruption-recovery layer (the differentiator), extension use case, repro script, video, 8-slide deck. **Deadline is still UNKNOWN — user must confirm from the email/portal that delivered the updated guide.**

---

## 1. GOVERNING DOCUMENTS (read in this order)

| File | What it is |
|---|---|
| `CONSTRAINTS_AND_REQUIREMENTS.md` | Verified facts of the competition. §6B = **the current operative requirements** (supersedes old Theme 5 PDF evaluation). |
| `BUILD_PLAN.md` | v2.0 pivot banner + original v1.1 plan (architecture reasoning, devil's advocate, review integration). |
| `extracted/theme5_updated.txt` | Full extracted text of `Theme05_Participant_Guide_UPDATED_FBD.docx` — **the rulebook**. |
| `extracted/verify.py`, `extracted/verify_plan.py` | Chain-of-verification scripts (83/83 + 54/54 claims pass). |
| `fdb3/v3/README.md` | The benchmark's own README (setup, providers, metrics). |

### Hard rules from the guide (violating = DQ or lost points)
- **NO hardcoding/memorizing/fine-tuning on benchmark test items** — they check.
- **NO your-own servers at evaluation** — all agent logic in the submission.
- **NO cross-scenario caching.**
- **API keys never in the repo** (`.env.local` is gitignored; document needed keys in README instead).
- One-command repro script must work on a clean machine (organizers re-run it; non-reproducing = 0 for the 60% portion after one contact attempt).
- Pin seeds and versions.
- Video 3–5 min unedited single takes; deck **≤ 8 slides**; submit via Google Form; last upload counts.

---

## 2. DIRECTORY MAP (everything project-local; NOTHING global was touched)

```
C:\Users\ASUS\Desktop\PRISM_Z\
├── .env                      # USER'S KEYS (gitignored): GEMINI_API_KEY, LIVEKIT_API_KEY/SECRET/URL
├── .venv\                    # py3.12 venv — original two-queue scaffold work (tests: 7/7 green)
├── .venv-fdb\                # py3.12 venv — FDB-v3 stack: livekit-agents[google]≈1.8.3, livekit 1.1.18,
│                            #   nemo_toolkit 3.0 + torch 2.14 (CPU), silero plugin, pydub, gdown
├── hf-cache\                 # HF_HOME (project-local): nvidia/parakeet-tdt-0.6b-v2 (~2.4 GB)
├── agent\ harness\ tests\    # ORIGINAL v1.1 scaffold (old spec) — kept as internal test infra:
│                            #   generation-numbered executor, idempotency registry, virtual clock.
│                            #   PORT THESE CONCEPTS into the custom LiveKit agent. 7/7 tests green.
├── fdb3\                     # vendored Full-Duplex-Bench clone (depth-1). HAS OUR PATCHES (see §4)
│   └── v3\
│       ├── .env.local        # generated from ../.env (names: GOOGLE_API_KEY + LIVEKIT_*)
│       ├── lk_agent_tool.py        # native realtime agent template (PATCHED ×2)
│       ├── run_tool_benchmark.py   # core runner (PATCHED ×1)
│       ├── run_tool_benchmark_all_released.py  # batch CLI
│       ├── livekit_inference.py    # headless LiveKit client
│       ├── evaluate_tool_calls.py / evaluate_pass_rate.py / analyze_tool_latency.py
│       ├── mock_apis.py, latency_injector.py, benchmark_data_v2.json
│       ├── fdb_v3_data_released\   # 100 examples (input.wav 48kHz + metadata.json) — EXTRACTED
│       ├── fdb_v3_data_test\       # 1 example copy (ecommerce_01) for smoke tests
│       └── logs\                   # agent_tool_calls.log / agent_heartbeat.log (patched paths)
├── CONSTRAINTS_AND_REQUIREMENTS.md · BUILD_PLAN.md · HANDOFF.md (this file)
├── extracted\                # text extractions + verification scripts (gitignored)
├── CollegeName_TeamName_Submission.pptx  # 12-slide OLD template — superseded by ≤8-slide rule!
├── LangAI3.0_AI_Disclosure.docx          # AI disclosure form (still required, submit route TBD)
└── Theme05_Participant_Guide_UPDATED_FBD.docx  # THE rulebook
```

Git: initialized in `PRISM_Z\`; commits `0588ec1` (old-spec scaffold) → `662f634` (pivot docs). fdb3/ + .envs are gitignored. **No pushes yet; no global git config set** (commits use inline `-c user.name/email`).

---

## 3. ENVIRONMENT & KEYS

- Windows 10, Git Bash shell, **CPU-only** (no CUDA — this is why patches were needed).
- Pythons available: `py -3.12` (used for both venvs). msys64 python exists but **do not use it** (breaks C wheels — known).
- Keys (all in `.env`, mapped into `fdb3/v3/.env.local`): `GEMINI_API_KEY` (Google AI Studio free tier — the agent brain; also `GOOGLE_API_KEY` alias), `LIVEKIT_URL/API_KEY/API_SECRET` (cloud.livekit.io free tier, region auto → India South).
- HF_HOME must point to `C:\Users\ASUS\Desktop\PRISM_Z\hf-cache` on every command that loads models (keeps model cache project-local).
- ffmpeg 9.0.1 present. Node 24 present.

---

## 4. PATCHES APPLIED TO THE VENDORED BENCHMARK (each verified necessary)

| # | File | Patch | Why |
|---|---|---|---|
| P1 | `lk_agent_tool.py`, `livekit_inference.py`, `run_tool_benchmark.py` | `/tmp/agent_*.log` → `logs/agent_*.log` (+ created `v3/logs/`) | Linux-only paths crash on Windows |
| P2 | `run_tool_benchmark.py::load_asr_model` | `model.cuda()` → try CUDA, fallback `model.cpu()` | Machine has no GPU; benchmark hard-coded CUDA |
| P3 | `lk_agent_tool.py` (top, after dotenv import) | Eager `import livekit.plugins.google` + `openai` at module load | livekit-agents 1.8 registers plugins on import; the template's lazy import inside the job entrypoint runs off-main-thread → `RuntimeError: Plugins must be registered on the main thread` → agent job dies silently (room joins, then nothing). **This was the root cause of the first failed smoke test** (45.8s "latency", empty transcript, zero tool calls). |

Keep P1–P3 when pulling upstream changes; they must be re-applied if `git pull` inside fdb3 (we cloned depth-1; prefer no pulls).

---

## 5. EXACT COMMANDS (the working loop)

All from `C:\Users\ASUS\Desktop\PRISM_Z\fdb3\v3`, with `PY=C:\Users\ASUS\Desktop\PRISM_Z\.venv-fdb\Scripts\python.exe`:

```bash
# Terminal A — start the agent worker (keep running):
LK_PROVIDER=gemini2_5 HF_HOME="C:\Users\ASUS\Desktop\PRISM_Z\hf-cache" $PY lk_agent_tool.py start
# providers: gemini2_5 (default choice), gemini3_1, gpt_realtime, grok, ultravox

# Terminal B — batch inference (single-example smoke):
HF_HOME=... $PY run_tool_benchmark_all_released.py --provider gemini2_5 --root_dir fdb_v3_data_test --force
# full run: --root_dir fdb_v3_data_released   (skip existing unless --force)

# Evaluation (no LiveKit needed):
$PY evaluate_tool_calls.py --benchmark benchmark_data_v2.json --results-dir fdb_v3_data_released \
    --provider gemini2_5 --output gemini2_5_evaluation_report.json        # add --use-llm ONLY if judge key available (gpt-4o; we have none — exact-match mode)
$PY evaluate_pass_rate.py --benchmark benchmark_data_v2.json --results-dir fdb_v3_data_released \
    --provider gemini2_5 --output gemini2_5_pass_rate_report.json
$PY analyze_tool_latency.py --results-dir fdb_v3_data_released --provider gemini2_5
```

**Known harmless noise:** `multiprocess.resource_tracker AttributeError '_thread.RLock' object has no attribute '_recursion_count'` at exit — ignore. NeMo warns "CUDA not available" — expected.

**Cost/quota notes:** each example = 1 LiveKit room + 1 Gemini native-audio session (~1–2 min audio). Free-tier RPM limits may throttle a full 100 run — if 429s appear, the batch script can be resumed (it skips existing result_*.json unless --force). Run overnight if needed.

---

## 6. STATE AS OF THIS HANDOFF

1. ✅ Worker (gemini2_5) registers with LiveKit Cloud.
2. ✅ Single-example pipeline completes: inference → agent audio captured → Parakeet ASR (CPU, ~12s/clip) → `result_gemini2_5.json` saved with input transcript + timestamps.
3. ⏳ **IN FLIGHT RIGHT NOW:** re-run of the single example AFTER patch P3. First run failed (agent job crashed pre-P3: empty transcript, `actual_tool_calls: []`, first_speech = whole 45.8s window). Check `fdb_v3_data_test/ecommerce_01_65e8cf8f4c7424fa062e54a3/result_gemini2_5.json`: success criteria = `transcript` non-empty, `actual_tool_calls` contains `track_order(order_id="ABC123")`, `latency.first_speech_s` in single-digit seconds, and `v3/logs/agent_tool_calls.log` has a matching entry.
4. If the smoke passes → **launch the full 100-example baseline** (same command, `--root_dir fdb_v3_data_released`, no `--force`), then run the three eval scripts (exact-match mode) → record baseline numbers in a results table (`results/` dir).

---

## 7. THE BUILD — WHAT AND WHY (design intent, not just steps)

### 7.1 Baseline first (doing now)
Run the unmodified template to get honest Gemini-2.5-native-audio numbers (tool F1, arg accuracy, strict pass rate, latency). The guide says published baselines exist; our own run is required for the results section and calibrates every improvement. **Why:** you cannot claim improvement without a baseline, and the repro script must reproduce the *final* agent.

### 7.2 Custom agent = `prism_agent.py` (THE core deliverable, worth the 60%)
Fork `lk_agent_tool.py` and wrap the model with our recovery layer. **Why:** the guide states *self-correction handling and multi-step tool chains are where scores are lost across all published systems* — that is exactly what our layer targets.

Architecture (port from `agent/` v1.1 scaffold, concepts already tested 7/7 green):

1. **Generation-numbered tool calls.** Every user speech segment start/interuption bump `generation`. In-flight function calls from older generations are cancelled (`CancelCalls` equivalent: in LiveKit, drop/supersede via the session's tool queue). Prevents stale re-runs (a scored failure mode: "state_rollback_test": true examples exist in metadata!).
2. **Idempotency registry (registry-before-yield + pending-confirmation)** — port `agent/tools/executor.py` semantics directly: state-modifying mock tools are `book_flight`, `update_identity_doc`, `modify_autopay`, `update_search_filter`, `add_to_cart` (others are read-only). Same (tool, normalized args) → return cached result, never re-execute. **Why:** FDB-v3 penalizes extra tool calls (precision) and double state-changes; metadata's `state_rollback_test` scenarios specifically reward NOT re-running a superseded state change and re-issuing with corrected args.
3. **Session slot state with localized corrections.** Track latest values per argument (destination/date/amount/ids) across the multi-utterance dialogue; on self-correction ("wait, make that 500"), patch only the changed slot and re-issue the chain from the affected tool onward (using `$RESULT_i` dynamic refs already supported by the eval).
4. **Speech-parallel planning.** On `user_input_transcribed` interim events, pre-resolve likely tools/args so the final call fires the moment end-of-speech lands (first-speech + tool-call latency are scored).
5. **Prompt engineering on VoiceAgent.instructions** — keep the template's anti-refusal and "call tools immediately" directives (they matter: descriptions literally say MANDATORY/NEVER refuse), add: never batch, re-issue corrected calls after user corrections, keep answers grounded in tool output.

Test loop: change → re-run a **10-example subset** (mix difficulties + `state_rollback_test:true`) → compare eval numbers → only then full 100.

### 7.3 Extension use case (20%): **Camera-frame device troubleshooting** (Samsung-flavored)
Reuse the LiveKit agent + add 2–3 tools: `lookup_manual_section(topic)`, `diagnose_from_frame(frame_desc)`, `resolve_deeplink(setting)`. User shows a device/setting via camera (or plays a pre-recorded video in the room) and asks "why does my wifi keep dropping" → agent grounds answer in frame + manual, walks fix steps. **Why:** matches the theme's own listed use case ("Field & Consumer Troubleshooting: grounding device queries in camera frames and manuals"), is demoable on camera in one take, and runs fully local (mock manual DB — no external services at eval time). Must appear end-to-end in the video.

### 7.4 Repro script (gate for the 60%)
`reproduce.sh`: checks .env vars → creates venv → pip install pinned `requirements-fdb.txt` (freeze from .venv-fdb) → downloads benchmark data via gdown → starts worker → runs batch → runs evals → prints/collects reports. **Test on a clean machine/profile.** Document: needs GOOGLE_API_KEY + LIVEKIT_* keys, ffmpeg; GPU optional (CPU fallback P2 included).

### 7.5 Docs/video (20%)
- README: architecture diagram (dual-process + generation numbers), setup, provider declaration (Gemini 2.5 Flash Native Audio), extension clearly marked, honest limitations.
- Video 3–5 min, single takes: (a) benchmark interruption/self-correction scenario handled live, (b) extension use case.
- Deck ≤ 8 slides: problem, architecture, benchmark results (table vs baseline), next steps. **Ignore the 12-slide PPT template — superseded.**
- AI disclosure DOCX: fill feature-origin table (AI-generated code via ZCode, etc.).

### 7.6 GPU note (user offered Kaggle/Colab)
Local machine is CPU-only. **Agents are hosted (Gemini/LiveKit) → no GPU needed for inference.** The only GPU-hungry step is Parakeet ASR during evaluation (~12s/clip on CPU ≈ 20 min per 100 — acceptable). OPTIONAL speedup: run `--asr-only` batch eval on Colab GPU with the same venv spec; results are plain JSONs — copy back. Do NOT bother porting the agent itself to Colab (LiveKit Cloud does the heavy lifting).

---

## 8. RISKS / OPEN ITEMS

| # | Item | Mitigation |
|---|---|---|
| R1 | **Deadline unknown** (old 25 Sep passed; updated guide silent) | USER: find date from the email/portal/WhatsApp that delivered the DOCX. All scheduling depends on it. |
| R2 | Gemini free-tier RPM may throttle 100-example run | Resume-capable batch (no --force); run overnight; retry 429s. |
| R3 | `--use-llm` judge needs OpenAI key (we have none) | Local tuning uses exact-match mode (stricter). Organizer re-run uses THEIR pinned judge — fine. Optionally ask user for $5 OpenAI credit later for closer-to-official local numbers. |
| R4 | Repro script must run on clean machine | Freeze requirements; test in a fresh Windows user profile / (ideally) Linux box or GitHub Actions. |
| R5 | We patched vendored code (P1–P3) — keep them; do not `git pull` in fdb3 | Documented in §4; upstream has no Windows fixes as of 2026-09-30. |
| R6 | LiveKit Cloud free tier concurrency = few rooms | Batch runs sequentially; fine. |

## 9. DEFINITION OF DONE

1. Baseline table (gemini2_5 template) on all 100 examples recorded.
2. `prism_agent.py` beats baseline on tool F1 + strict pass rate (especially `state_rollback_test` and difficulty-3 chains); improvements documented per change.
3. Extension use case runs live and is captured in the 3–5 min video.
4. `reproduce.sh` validated on a clean environment; README + 8-slide deck + disclosure complete.
5. User pushes to GitHub (public), submits Google Form with video+deck links.

**Next concrete action for the continuing agent:** check the in-flight smoke test result (§6.3); if green → full baseline (§6.4); if red → worker log at `C:\Users\ASUS\.zcode\cli\exec\sess_ecc406de-be1f-4eb0-bed6-8382c43eb250\call_e3cd73ebfee04c099ceab386-stdout.log` (current worker) for the next exception; iterate patches the same way P3 was found (worker log "unhandled exception while running the job task" lines are gold).
