# Freebuff Review — PRISM_Z Project Audit

**Author:** Buffy (Freebuff agent) · **Date:** 2026-10-02 · **Method:** full checkout of every doc, the complete git history, all source directories, untracked artifacts, and a claim-by-claim chain of verification against what is actually on disk.

---

## 1. What this project is

Samsung PRISM GenAI Hackathon 3.0 — **Theme 5: Interruptible Real-Time Agents**.

- The operative rulebook is `Theme05_Participant_Guide_UPDATED_FBD.docx` (29 Sep 2026), which **superseded** the original Theme 5 evaluation (old two-queue/JSON protocol, 9-scenario kit, 40/35/15/10 scoring). Documented in `CONSTRAINTS_AND_REQUIREMENTS.md` §6B.
- The scored surface is now the public **FDB-v3 benchmark** (NTU; NVIDIA advisory; arXiv 2604.04847) run against a **LiveKit voice agent** built from the benchmark's provided templates.
- **Round 1 scoring:** 60% × normalized benchmark score (organizers re-run via the submission's repro script — only their re-run counts; non-reproducing = 0 after one contact attempt) + 20% × one extension use case + 20% × documentation/video. Ties break on strict pass rate.
- **Hard rules:** no hardcoding/memorizing test items (DQ, "they check"); no own servers at evaluation; no cross-scenario caching; API keys never in the repo; one-command repro; pin seeds/versions; video 3–5 min single takes; deck ≤ 8 slides; Google Form, last upload counts.
- **Operative deadline on disk:** `FIXES_NOTES.md` header says **Oct 4** (2 days out). Earlier docs say "unknown"; old 25 Sep date has passed. The user should treat Oct 4 as real until organizers say otherwise.

The team name/branding is **AuraStream** (formerly Reflex-AI) per `README.md`; the extension use case is **Samsung-flavored device troubleshooting** (camera-frame grounding + manual lookup + settings deeplink) — 3 extra tools on top of the benchmark's 12.

---

## 2. Timeline (git history, 11 commits on `master`)

| Commit | Date | What happened |
|---|---|---|
| `0588ec1` | 2026-09-22 | Theme 5 **v1.1 scaffold** for the OLD spec: protocol layer (`agent/protocol/`), virtual-clock harness (`harness/`), review-hardened executor (`agent/tools/executor.py`), dual-process agent, invariant + smoke tests. Claim: 7/7 green (see §6 — no longer true). |
| `662f634` | 2026-09-29 | **v2.0 pivot docs** — FDB-v3/LiveKit supersedes the old kit; `CONSTRAINTS_AND_REQUIREMENTS.md` + `BUILD_PLAN.md` rewritten with verified facts (83/83 + 54/54 verification scripts in `extracted/`). |
| `f9a6b57` | 2026-10-01 | Benchmark scripts + documentation added. |
| `49733fa` | 2026-10-01 | README added; unwanted docs untracked. |
| `924b317` | 2026-10-01 | Idempotent interruption + sub-second tool execution patches; AuraStream README naming. |
| `7c149c6` | 2026-10-01 | **Vendored FDB-v3** (`fdb3/`), depth-1 clone. 5,061 files — mostly upstream `node_modules` from `v1_v1.5/` (bloat, see §6). Data dirs are gitignored. |
| `8c43520` | 2026-10-02 | **Shadow Agent architecture** — Gemini-text "second brain" that parses transcripts and fires tool calls the realtime model missed. |
| `c760180` | 2026-10-02 | Shadow model pinned to `gemini-3.8-flash`. |
| `295b531` | 2026-10-02 | UTF-8 encoding fixes. |
| `f4c0b9e` | 2026-10-02 | ASR swapped: NeMo Parakeet → **HuggingFace Whisper**. |
| `2f5e15f` | 2026-10-02 | **Fixes 1–6** (see §4) + Colab bundle + `FIXES_NOTES.md`. |

**Uncommitted right now:** `fdb3/v3/prism_agent.py` + `fdb3/v3/run_tool_benchmark.py` modified (this is the Fixes 1–6 content synced back into `fdb3/v3/` — byte-identical to the copies already committed under `colab/prism_colab/v3/`, so no content is at risk; it just needs a commit). Untracked: `.freebuff/`, `Benchmark_Results.zip` (old 948 MB one), `diff.txt` (UTF-16 diff of template→prism agent), `fdb3/v3/fdb_v3_data_val/`, loose scripts (`fix_indent.py`, `lenient_test.py`, `rewrite*.py`, `scratch.py`), root `gemini2_5_pass_rate_report.json`.

---

## 3. The deliverable — `fdb3/v3/prism_agent.py`

Fork of the benchmark template `lk_agent_tool.py` with the PRISM recovery layer. It is the single most important file in the repo (worth the 60%).

**Recovery layer (ported from the v1.1 scaffold):**
- `LatencyTracker.generation` — bumped on every user speech start; in-flight tool calls from older generations abort during their deliberation window.
- `state_registry` — idempotency registry with **registry-before-yield**: state-modifying tools record `SENT` before executing, `DONE` (cached result) or `PENDING_CONFIRMATION` (transmitted-but-cancelled, still blocks duplicates) after. `asyncio.shield` protects execution from cancellation.
- Deliberation window: 0.3 s read tools, **0.5 s** state tools (was 1.0 s; Fix 5).
- **Shadow agent** (`shadow_agent_predict`) — after Fix 6 it is a *recovery net*, not a parallel actor: waits 6 s quiet window, stands down if the primary produced any tool activity (`last_tool_at` gate), executes **read-only lookups only** (state-modifying calls skipped), gated on `is_final` transcripts (Fix 1), parsed via `gemini-3.8-flash` JSON mode.
- 15 tools total: the benchmark's 12 (`mock_apis.py`) + 3 Samsung extension tools (`lookup_manual_section`, `diagnose_from_frame`, `resolve_deeplink`).
- Instructions (Fix 5): **immediacy first**, final-value rule for self-corrections, chain-of-verification ("you cannot book without a tool call"), argument-format rules (natural-language dates, concatenated IDs, underscore doc types, capitalized booleans).

**Fixes 1–6 (from `FIXES_NOTES.md`, all verified present in the working tree):**

| Fix | What | Verified? |
|---|---|---|
| 1 | `is_final` gate on `user_input_transcribed` before any shadow work (E1: shadow executed tools on partial/retracted intents) | ✅ in file |
| 2 | Telemetry path pinned: `PRISM_TOOL_LOG` env else `<script dir>/logs/agent_tool_calls.log`, identical in agent and runner (E2: CWD-dependent path could read empty on organizers' machine) | ✅ both sides |
| 3 | `log_tool_call` logs every execution, no dedupe (E3: dedupe hid extra calls from the scored log); `last_tool_at` added | ✅ |
| 5 | Deliberation 1.0 s → 0.5 s; immediacy instructions restored; final-value rule (E4: "wait for final intent" wording conflicted with benchmark immediacy) | ✅ |
| 6 | Shadow → quiet-window recovery net, read-only only (E5: shadow double-executed read tools) | ✅ |
| — | Colab zip rebuilt, integrity-verified (E6); `Benchmark_Results.zip` rebuilt results-only (E7 — **see §6, not true on disk**) | zip ✅ / E7 ❌ |

**Runner patches (P1–P3)** in the vendored benchmark: Windows-safe log paths; `model.cuda()` → CPU fallback; eager plugin import at module load (livekit-agents ≥1.8 registers plugins on the main thread).

---

## 4. Results currently on disk (all verified by reading the JSONs)

| Report | Provider | Strict pass | Failure breakdown | Note |
|---|---|---|---|---|
| `fdb3/v3/gemini2_5_pass_rate_report.json` (17:20 Oct 2) | gemini2_5 | **29/100** | 56 wrong-tools, 15 wrong-args | **The honest baseline.** Matches FIXES_NOTES §4. |
| `fdb3/v3/gemini2_5_pass_rate_report_v2.json` (15:02) | gemini2_5 | 21/100 | 63 wrong-tools | Earlier eval of same/similar run. |
| root `gemini2_5_pass_rate_report.json` (13:36) | gemini2_5 | 81/100 | 0 wrong-tools, 19 wrong-args | **Lenient re-score** by `lenient_test.py` (recall + substring arg matching). Not comparable to strict. |
| `fdb3/v3/gemini3_6_pass_rate_report.json` | gemini3_6 | 0/100 | 100 wrong-tools | Dead run — 100/100 "no response"; `evaluation_report.json` confirms zero turn-taking. Not a meaningful baseline. |
| `fdb3/v3/gpt_realtime_pass_rate_report.json` | gpt_realtime | 0 scenarios | — | Empty report (run never populated). |

**PRISM (fixed agent) full 100-run: NOT DONE.** Zero `result_prism.json` in `fdb_v3_data_released/`. The plan is the Colab GPU notebook.

**Validation set** (`fdb3/v3/fdb_v3_data_val/`, built by `fixes/make_val_set.py`: the 5 hardest cases — difficulty 3 + `state_rollback_test` + SELF_CORRECTION — plus the easy control ecommerce_01):

| Case | Difficulty | Expected | gemini2_5 baseline | prism (fixed) |
|---|---|---|---|---|
| ecommerce_01 | easy | `track_order(ABC123)` | ✅ pass | ✅ **pass** |
| finance_23 | hard, rollback, FALSE_START+SELF_CORRECTION | `modify_autopay(mortgage, savings)` | ✅ pass | ❌ **zero tool calls** |
| housing_19 | hard, rollback | `calculate_commute(my house → the gym, driving)` | ❌ zero calls | ⚠️ run interrupted; the logged call was **correct** (`eval-6d3f5442` in tool log) but no result JSON exists |
| housing_21 | hard, rollback, chained | `search_apartments` → `calculate_commute($RESULT_0...)` | partial (1 of 2) | not run |
| housing_25 | hard, rollback, 3 calls | 2× `update_search_filter` + `search_apartments` | ❌ zero calls | not run |
| travel_19 | hard, rollback | `search_flights(Milan, June 3)` | ❌ wrong date format (`2026-06-03` vs `June 3`) | not run |

**FIXES_NOTES §3's success criterion ("fixed agent passes ≥3/5 hard cases") is currently unmet/incomplete: 0 of 5 hard cases confirmed passing, 2 never run, 1 interrupted.** This is the single most important open item — the fixes have not been validated yet.

Also notable: the current `fdb3/v3/logs/agent_tool_calls.log` holds only 2 lines (both from the Oct 2 evening val run) — the 100-run telemetry was cleared; it survives only inside the eval reports. The heartbeat log confirms the prism worker *did* join the finance_23 room (`eval-5a0dfc3a`, 18:48:23) — the agent was up, it just never called a tool.

---

## 5. What checks out (verified true)

1. **Chain-of-verification scripts pass:** `extracted/verify.py` → 83/83; `extracted/verify_plan.py` → 54/54 (both re-run during this audit).
2. **Fixes 1–6 content is committed** — `colab/prism_colab/v3/prism_agent.py` and `run_tool_benchmark.py` at HEAD are byte-identical to the working-tree `fdb3/v3/` copies (diffed). Only the `fdb3/v3/` sync-back is uncommitted.
3. **`PRISM_Z_Colab.zip` integrity clean** (testzip None, 9 entries, ~38 KB) — E6 verified.
4. **Keys hygiene:** `.env`, `.env.local`, `fdb3/v3/.env.local` all gitignored (checked with `git check-ignore`); only variable names exist on disk (GEMINI_API_KEY / GOOGLE_API_KEY alias + LIVEKIT_URL/API_KEY/API_SECRET); no keys in any tracked file.
5. **Benchmark data:** 100 example dirs in `fdb_v3_data_released/`, each with 48 kHz `input.wav` + `metadata.json`; 100 baseline `result_gemini2_5.json`. Vendored README matches the guide's claims (79 unique scenarios, 12 speakers, 4 domains, 3 difficulties).
6. **Tool counts:** 12 mock APIs + 3 extension = 15 (E8's "12 APIs vs 15 tools" note is accurate and the instructions no longer hardcode a count).
7. **Git repo:** 11 commits, clean narrative, no secrets committed, no pushes; remote `origin/master` exists at same HEAD.

---

## 6. Discrepancies found (documentation vs. actuality)

| # | Claim (source) | Reality on disk | Severity |
|---|---|---|---|
| D-1 | FIXES_NOTES §3: validation criterion "≥3/5 hard cases passing" | 0/5 confirmed, 2 never run, 1 interrupted. **Fixes are unvalidated.** | 🔴 critical |
| D-2 | finance_23 prism result: agent joined room, produced **zero tool calls**; old baseline passed this exact case | Confirmed via heartbeat + empty tool log + `actual_tool_calls: []` | 🔴 critical — unexplained regression vs baseline; must be root-caused before the 100-run |
| D-3 | FIXES_NOTES E7: "Benchmark_Results.zip rebuilt as results-only" | Root zip is still the old **948 MB** archive (dated Oct 1) with 303 WAVs (1.6 GB uncompressed) + 300 JSONs | 🟡 |
| D-4 | HANDOFF/BUILD_PLAN: scaffold tests "7/7 green" | **6/7** — `tests/test_smoke.py::test_full_loop_text_scenario` fails (`mock_tool_started` never fires) | 🟡 |
| D-5 | Root `gemini2_5_pass_rate_report.json` shows 81% | It is the lenient re-score; strict = 29%. Two files same name in different dirs invite conflation in the deck | 🟡 |
| D-6 | Vendored benchmark commit `7c149c6` | 5,061 files, mostly `fdb3/v1_v1.5/.../node_modules/` — bloat that will ride into the judged release tag | 🟡 |
| D-7 | `fdb3/v3/prism_agent.py` + `run_tool_benchmark.py` fixes | Uncommitted (content safe in `colab/` copy) | 🟡 |
| D-8 | `eval_*.txt` reports | UTF-16/mojibake artifacts (written via a UTF-16-redirecting shell) — cosmetic (E8 acknowledged) | 🟢 |
| D-9 | Tool log truncated to 2 lines after the 100-run | Raw telemetry for the 29% baseline no longer on disk (only in reports) | 🟢 |
| D-10 | `extracted/` says "gitignored" | True, but the verification scripts are then absent from any fresh clone — repro docs should inline the key facts they prove | 🟢 |

---

## 7. Suggested fixes (priority order)

### P0 — before any full run (blocks everything)
1. **Root-cause the finance_23 zero-call failure** (D-2). Leading hypotheses, in order:
   - The **generation-bump abort loop**: user speaks in multiple segments ("check the balance… never mind… set autopay from checking… no, savings"). Every segment start bumps `generation`; if the model issues `modify_autopay(checking)` and the user's correction arrives within the 0.5 s window, the call aborts with an error string — and if the model doesn't re-issue (it often just apologizes), nothing executes. The 6 s shadow recovery **cannot help here by design** (it skips state-modifying tools). Consider: on a generation-bump abort, immediately re-parse the *latest final transcript* and re-issue with corrected args once, instead of returning an error to the model.
   - The primary model simply didn't call (instructions still say "DO NOT ask clarifying questions" but the utterance is genuinely ambiguous mid-stream).
   - A worker/session fault — check whether LiveKit job died mid-room (heartbeat shows join, nothing after).
   Concretely: re-run finance_23 alone against the fixed agent with `PRISM_HEARTBEAT_LOG`/`PRISM_TOOL_LOG` redirected to fresh files, and diff the worker stdout log.
2. **Complete the val run — all 6 examples with prism** (D-1), then record the pass/fail table vs baseline in FIXES_NOTES. Only if ≥3/5 hard cases pass should the Colab 100-run be trusted as the final numbers.
3. **Commit the `fdb3/v3/` sync-back** (D-7) so agent, runner, and Colab bundle are provably the same version.

### P1 — before packaging (judged artifacts)
4. **Rebuild `Benchmark_Results.zip` results-only** (D-3) or delete it and let the Colab notebook's step 8 produce it — do not submit 948 MB of audio the organizers already have.
5. **Prune `fdb3/v1_v1.5/**/node_modules` from the repo** (D-6) before tagging `PRISM_GENAI_HACKATHON_Y2026` — the tagged commit is what gets judged, and a 5k-file vendored `node_modules` obscures the diff and the provenance story. (Add to `.gitignore`, `git rm -r --cached`, document that node_modules come from the upstream clone.)
6. **Rename/de-clutter the eval reports** (D-5): keep strict reports under `results/strict/`, move the lenient one to `results/lenient/` with a README line explaining the difference; update FIXES_NOTES §4 to point at both explicitly.
7. **Fix or quarantine the legacy smoke test** (D-4): either repair `agent/` dispatch so `mock_tool_started` fires again, or mark it `@pytest.mark.legacy` and update HANDOFF's "7/7" claim — the scaffold is internal test infra only, so a stale failing test is noise in CI.

### P2 — polish
8. Re-run the three eval scripts from a UTF-8 shell so `eval_*.txt` are readable (D-8).
9. Preserve raw telemetry going forward: append room-scoped per-example tool-call records next to each `result_*.json` instead of one shared global log that gets cleared (D-9).
10. Inline the headline verified facts (rules, scoring, baseline) into the main README so a fresh clone without `extracted/` still tells the story (D-10).

### P3 — submission readiness (the remaining 40%)
11. Extension use case end-to-end demo path (camera frame → `diagnose_from_frame` → `lookup_manual_section` → `resolve_deeplink`) — currently only tool stubs exist; needs a runnable scenario for the video.
12. `reproduce.sh` validation on a clean machine (the script exists but checks `GEMINI_API_KEY` while the Colab path asks for `GOOGLE_API_KEY` — reconcile the one name).
13. Deck ≤ 8 slides + 3–5 min single-take video + AI disclosure form; release tag `PRISM_GENAI_HACKATHON_Y2026` on the final commit.

---

## 8. Honest expectations (from FIXES_NOTES §4, endorsed by this audit)

The user's 90–95% target is not achievable legitimately on FDB-v3 (no published system is near it; strict pass requires every expected call with exact/semantic args and zero extras on disfluent human audio). Baseline = 29%. The fixes plausibly move strict pass into the **40–60% band** by removing wrong-tool penalties (E1/E5) and fixing rollback behavior. Tailoring to known test items = automatic DQ. The strong, defensible story is baseline-vs-final delta + failure-mode analysis — the deck should be built around that.

---

*Every claim in this file was checked against the repository on 2026-10-02; re-verify before relying on it after further changes.*
