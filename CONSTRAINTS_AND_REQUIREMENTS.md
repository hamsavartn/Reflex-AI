# Samsung PRISM GenAI Hackathon 3.0 (2026–27) — Constraints & Requirements

> ⚠️ **SUPERSESSION NOTICE (29 Sep 2026):** `Theme05_Participant_Guide_UPDATED_FBD.docx` **replaces the Theme 5 evaluation model** in `Theme 5_Guide.pdf` (v1.0.0). Theme 5 is now scored via the public **FDB-v3 (Full-Duplex-Bench v3)** benchmark on **LiveKit agents** — not the custom two-queue harness/virtual-clock kit described in the old PDF §4–6. See §6B for the verified new requirements. The old guide remains useful as theme background (problem framing, dual-process concepts) but its interface contract, 9-scenario kit, 40/35/15/10 scoring, Python 3.10–3.12/120 s caps are **no longer the scored surface**. Deadline: the updated guide states none — the old 25 Sep date has passed; **confirm the new deadline with organizers**.

> **Compiled:** 2026-09-20 · **Verification:** 83/83 claims mechanically re-checked against extracted source text (chain-of-verification), plus raw-OOXML cross-checks for PPTX/DOCX and full page coverage of all PDFs.
> **Reproduce:** `extracted/verify.py` (run with `.venv/Scripts/python.exe extracted/verify.py`) re-checks every fact below against `extracted/*.txt`.

## Verification legend

| Mark | Meaning |
|---|---|
| ✅ | Verified — mechanical string match against the cited source page |
| ✅✅ | Cross-verified — same fact found in 2+ sources |
| ⚠️ | Conflict/ambiguity between sources — see Flags section (F#) |
| ❓ | Not specified anywhere in the kit — ask organizers (open question, Q#) |

**Source shorthand:** `[DECK p.N]` = Samsung PRISM_Y2026_GenAI_Hackathon_3rd_Edition.V2(2).pdf (15 pp) · `[T1G p.N]` = theme1_guidelines.pdf (4 pp) · `[T5G p.N]` = Theme 5_Guide.pdf (3 pp, v1.0.0) · `[PPT s.N]` = CollegeName_TeamName_Submission.pptx (12 slides) · `[DISC §N]` = LangAI3.0_AI_Disclosure.docx · `[INVITE]` = Gen AI 3.0_Invite.png

---

## 1. Sources read (coverage — everything in the folder)

| File | Read coverage | Status |
|---|---|---|
| Samsung PRISM_Y2026_GenAI_Hackathon_3rd_Edition.V2(2).pdf | 15/15 pages | ✅ read in full |
| theme1_guidelines.pdf | 4/4 pages | ✅ read in full |
| Theme 5_Guide.pdf | 3/3 pages | ✅ read in full |
| CollegeName_TeamName_Submission.pptx | 12/12 slides + 2 notes slides; raw XML cross-check found no missed text | ✅ read in full |
| LangAI3.0_AI_Disclosure.docx | 41/41 paragraphs; raw XML cross-check found no missed text | ✅ read in full |
| Gen AI 3.0_Invite.png | viewed (launch poster) | ✅ read |
| skills-lock.json | read — agent-tooling lock file, **not hackathon material** | ignored |
| .kilo/.gitignore | read — editor config, **not hackathon material** | ignored |

No other documents exist in the folder. ⚠️ The DECK shows embedded-attachment labels for extra guides ("SmartGuided Troubleshooting PDF", "Adobe Acrobat Document" for Theme 3, "Streaming RAG Guide" for Theme 4) that are **not present** in this folder — see F5.

---

## 2. Hard deadlines (all dates 2026) ✅

| Date | Milestone | Source |
|---|---|---|
| 11 Sep | Launch — themes & problem statements live; team registration opens; launch event 12 Noon, online | DECK p.1, p.9 ✅✅ + INVITE ✅ |
| 16 Sep, 11:59 PM | **Registration closes**; Final Submission Link opens the same day | DECK p.9, p.12 ✅ |
| — | Final Submission Link is **ONLY** shared with teams that completed registration | DECK p.9 ✅ |
| **25 Sep, 11:59 PM** | **Final submission closes** — prototype code, 5-min demo video, deck | DECK p.1, p.9, p.11, p.12 ✅✅ |
| 9 Oct | Top 15 announced | DECK p.9, p.11 ✅ |
| 15 Oct | Final demo round (top 15 present live to Samsung R&D jury) | DECK p.9, p.11, p.14 ✅ |
| 24 Oct | Final results & awards | DECK p.1, p.9, p.11, p.14 ✅ |

- All dates "tentative and may shift slightly" ✅ [DECK p.9, p.14].
- Build window is 11–25 Sep ("2 weeks"), evaluation 25 Sep–9 Oct, final demo 15 Oct ✅ [DECK p.9].
- **⏰ As of today (20 Sep) there are 5 days left to submit.** Registration (16 Sep) has already closed — if your team did not register, you cannot get the submission link (see Q6).

---

## 3. Team & eligibility rules

- Up to **max 4 members per team, single college** ✅ [DECK p.12; PPT s.1 has exactly 4 member lines ✅✅].
- Registration collects per member: **name, email, phone, year & branch** ✅ [DECK p.12].
- Team name format: **`CollegeName_TeamName`** ✅ [DECK p.12].
- **One theme per team; one submission per team** ✅ [DECK p.12].
- "Open to all students" ✅ [INVITE].
- Registration form: `https://forms.gle/NxN6TWXLpcXmTnv66` ✅ [DECK p.14] (character-exact verified).

---

## 4. Submission requirements — violating these = **direct disqualification** ⚠️→✅

The DECK states twice: "**Teams NOT following the submission guideline would lead to direct disqualification**" ✅ [DECK p.12, p.13].

**Required deliverables (all due 25 Sep 11:59 PM):**

1. **Working prototype code** — public **or shared** GitHub repo ✅ [DECK p.11, p.12, p.13].
2. **README** with reproducible setup instructions, **Docker files**, and other requirements ✅ [DECK p.11, p.13].
3. **Demo video, max 5 minutes** (YouTube or Drive link) ✅ [DECK p.11, p.12].
4. **Presentation file (PPT or PDF)** — naming: DECK p.12 says `CollegeName_TeamName`, p.13 says "Refer to the CollegeName_TeamName_Submission_ppt", template file is `CollegeName_TeamName_Submission.pptx` ⚠️ use `CollegeName_TeamName_Submission.pptx` (F6).
5. **One submission per team via the Google Form** ✅ [DECK p.11, p.12].
6. There is **no separate ideation submission** — Round 1 requires a working prototype from day one ✅ [DECK p.11, p.12].

**GitHub-specific rules:**

- Create a **release tag named `PRISM_GENAI_HACKATHON_Y2026`** on your final commit — **the tagged commit is what gets judged** ✅ [DECK p.13].
- Everything referenced in the submission (PPT, demo video, documentation, etc.) must be **present in the tagged commit** ✅ [DECK p.13].
- Theme 1 additionally requires uploading the evaluation-results file as a GitHub **Release** artifact ✅ [T1G p.2–3] — see F10 for reconciliation.

**PPT template structure (12 slides)** ✅ [PPT]:

1. Title — SAMSUNG PRISM GenAI Hackathon, 3rd Ed. 2026–27; fields: Theme ID, Team Name, College Name, Member Name & Email ×4, **Submission GitHub link**
2. Theme
3. Existing Solutions & Gaps
4. Our Solutions & Architecture Diagram
5. Demo & Product Walkthrough
6. Tools and tech stack used
7. Impact & Use case
8. Innovation highlights, results and limitations
9. What's next
10. "Brownie points slide (differentiation)"
11. Checklist — Updated on Public GitHub: working prototype code public/shared repo (Y/N), README reproducible setup (Y/N), demo video ≤5 min (link), presentation file (Y/N)
12. Thank you

DECK p.13 requires the deck to cover: Theme ID, project title, team details, problem statement in your own words, solution & architecture diagram, tools/tech stack, innovation highlights, results, limitations ✅.

**AI Usage Disclosure form** exists (`LangAI3.0_AI_Disclosure.docx`): team details; Yes/No AI usage; purpose breakdown (idea gen, code gen, UI/UX, content, data analysis, testing/debugging, other); per-feature origin classification (Self-Generated / AI-Generated / Both + tools, prompts, output summary, modifications); compliance confirmations ("AI usage complies with guidelines and policies" — Yes; "No proprietary or copyrighted data misused" — I Agree); sign-off (representative name, role, signature, date) ✅ [DISC §1–6]. ⚠️ **The DECK's submission checklist never mentions this form** — where to submit it is unspecified (F4, Q2).

---

## 5. Evaluation

**Overall rubric (final judging)** ✅ [DECK p.11] — sums to 100 ✅:

| Criterion | Weight |
|---|---|
| Working prototype & functionality | 30% |
| Technical depth & feasibility | 25% |
| Innovation & originality | 20% |
| Relevance to theme | 15% |
| Presentation & documentation | 10% |

**Format:** one build round + one final demo (top 15 only: live presentation, prototype walkthrough, Q&A on design decisions & trade-offs) ✅ [DECK p.11].

**What the jury looks for** ✅ [DECK p.11]: Does the prototype actually work? Is the technical approach sound? Would a real user want this? Can it be taken further as a worklet?

**Theme-level screening/evaluation is separate and quantitative** (T1: NDCG@10/MRR on a dataset; T5: 0–100 per-scenario trace scoring). ❓ How theme-level scores combine with the overall rubric is not stated (Q3).

---

## 6. Theme requirement sheets

### Theme 01 — Agentic Code Intelligence

⚠️ **Scope conflict between DECK p.4 and T1G — the guide is the operational spec (F1).**

**Per the guide (controls):** the core problem is **code retrieval** — given a code library and a natural-language query, return a ranking of relevant code snippets (example: query "How is the input preprocessed before going to the main function?" → expected ranking Code#1 > Code#2 > Code#3) ✅ [T1G p.1]. Thousands of snippets; lengths vary ✅ [T1G p.1]. **Anything after retrieval — answer generation, explanation — is explicitly OUT OF SCOPE** ✅ [T1G p.1]. LLM-only ranking is ruled out: too many/long snippets for any context window; retrieval must be faster than generation ✅ [T1G p.2].

- **Submission goals (in importance order)** ✅ [T1G p.1–2]: **P0** Retrieval Accuracy → **P1** Retrieval across versions (rebuild indexes/caches per version in reasonable time) → **Bonus** Evolutionary Retrieval (retrieve across all versions; near-duplicate snippets make ranking hard).
- Improvement levers suggested: query categorization, query pre-processing, snippet categorization, pre/post-processing of snippets, multiple retrieval passes ✅ [T1G p.1].
- **Screening:** run inference on the **test split of the CoIR apps dataset** (`huggingface.co/datasets/CoIR-Retrieval/apps`); metrics **NDCG@10 and MRR**; competitive screening, top submissions go to hands-on ✅ [T1G p.2].
- **Tooling:** use the **MTEB** library; task **`AppsRetrieval`** (example uses `SentenceTransformer`-style `AbsEncoder` subclass, `encode_kwargs={"batch_size": 64}`); output **`appsretrieval_results.json`**; upload as a **GitHub Release** ✅ [T1G p.2–3]. ⚠️ p.2 also says "submit a csv file" once — contradicts the JSON everywhere else (F2).
- **Hands-on:** organizers run your code on similar queries; P1 + Bonus evaluated here ✅ [T1G p.3].
- **Have ready:** (1) JSON inference results, (2) PPT, (3) GitHub repo runnable from its instructions ✅ [T1G p.3].
- **Demo:** must show the solution live — responses per query and speed, not just numbers ✅ [T1G p.4].
- **PPT:** show approach details (pre/post-processing, embedding model) and a tough query's results ✅ [T1G p.4].

**Per the DECK (p.4):** plain-English question → snippets with file/line locations; structural queries ("which files call tool XYZ before tool ABC?"); usage queries ("where is the Bluetooth-settings deeplink used?"); agentic plan/search/read/refine beyond context window; bonus = optimisation suggestions; **single language: JavaScript** ✅; **must run on CPU, minimal GPU** ✅✅ [DECK p.4 + T1G p.1]; sample open-source codebase provided with the problem statement ✅ [DECK p.4]; report **precision@k, recall, latency, indexing cost** ✅ [DECK p.4]. ⚠️ Deck's "structural queries / bonus optimisations" framing conflicts with the guide's retrieval-only scope and evolutionary-retrieval bonus (F1).

### Theme 02 — Smart Guided Troubleshooting Engine ✅ [DECK p.5]

- Pipeline: **query enrichment** (vague complaint → technical query) → **two-stage LLM engine** returning clean, **ordered troubleshooting steps as JSON** → each step mapped to the exact **in-app Settings deeplink** (fix one tap away) → **fast-path cache** serving pre-validated answers in **< 300 ms**.
- **Deliverable is a REST API returning structured JSON**; output JSON must include **all actions, steps and associated deeplinks**; deeplinks must logically resolve to the action steps.
- Mapping must stay **reusable — production target 10k+ scenarios**.
- Report: **step accuracy, latency, cost per query**. Model choice is open.
- ⚠️ A "SmartGuided Troubleshooting PDF" attachment is referenced but absent from the folder (F5).

### Theme 03 — Teachable Voice Automation ✅ [DECK p.6]

- Let a user speak a command and **record on-screen steps once**; **generalise** the recording into a reusable flow (not brittle tap replay); match later utterances incl. **paraphrases and changed values**; replay reliably when screens change; **ask the user only when genuinely stuck**.
- **Constraints:** **Android**; **UI automation or accessibility services — not app-specific APIs**; **2–3 third-party apps** is enough; **at least one parameterised slot** (item, quantity, address); **no credential capture — pause for payment and authentication**.
- Report: **learn success, replay success across sessions, paraphrase match accuracy**. Tech: speech-to-intent, UI-tree understanding, flow synthesis from one demonstration.
- ⚠️ An "Adobe Acrobat Document" attachment is referenced but absent (F5).

### Theme 04 — Streaming Live RAG ✅ [DECK p.7]

- **Full-duplex: begin retrieving before the utterance ends**; intent understanding (does this utterance need retrieval at all?); **decompose** one natural command into its implied sub-queries; **fuse and rerank** across sub-queries into one grounded answer; supplementary detail must **sharpen the previous answer, not restart**.
- **Constraints:** **corpus provided**; voice input may be **simulated from transcripts**; **session-scoped memory only** — no cross-session user profile; **"simple and cheap beats a heavy agent orchestration stack"**.
- Report: **retrieval recall, answer groundedness, time-to-first-token, cost per turn**. Tech: query decomposition, multi-query retrieval, rank fusion, reranking.
- ⚠️ A "Streaming RAG Guide" attachment is referenced but absent (F5).

### Theme 05 — Interruptible Real-Time Agents

> ⚠️ **§6B SUPERSEDES THE OLD EVALUATION BELOW for Theme 5.** The old v1.0.0 description is retained for background only.

#### §6B — UPDATED evaluation (per `Theme05_Participant_Guide_UPDATED_FBD.docx`, all facts verified against the docx text and the live FDB-v3 repo README, 29 Sep 2026)

**What to build (§3):** a **LiveKit voice agent** (any architecture inside that wrapper — realtime speech APIs, cascaded ASR+LLM+TTS, open checkpoints, or custom), started from the benchmark's **two provided templates** (native realtime models / cascaded STT+LLM+TTS). Clone FDB-v3, create a **free LiveKit Cloud account**, download the benchmark data, run it against your agent, iterate on failure modes (**self-correction handling + multi-step tool chains are where scores are lost**), and **extend to one new use case** beyond the benchmark domains (must run end-to-end and appear in the video — e.g., device troubleshooting with a camera frame, in-car destination change).

**The benchmark (§2, verified vs repo):** FDB-v3 — public, NTU (NVIDIA advisory), `github.com/DanielLin94144/Full-Duplex-Bench` (use `v3/`; paper arXiv 2604.04847). 100 real human recordings (79 unique scenarios, 12 speakers) with 5 annotated disfluency types (fillers, pauses, hesitations, false starts, self-corrections), chained calls against 12 mock tools across 4 domains (travel, finance, housing, e-commerce), difficulty 1–3 chained calls. Data via Google Drive → `v3/fdb_v3_data_released/` (each example: `input.wav` 48 kHz + `metadata.json`). Deterministic mock outputs; LLM judge (single pinned) for semantic argument matching + response quality. Metrics: **tool-selection F1, argument accuracy, strict pass rate, latency**. Batch: `run_tool_benchmark_all_released.py --provider X`; eval: `evaluate_tool_calls.py`, `evaluate_pass_rate.py`, `analyze_tool_latency.py`; response accuracy needs `--use-llm` (gpt-4o judge). Templates: `lk_agent_tool.py` (GPT Realtime gpt-realtime-1.5, Gemini 2.5 Flash native audio, Gemini 3.1 Flash Live, Grok Voice, Ultravox — via `LK_PROVIDER`) and `cascaded_agent.py` (Silero VAD + Whisper STT + gpt-4o + OpenAI TTS). Env: conda py3.10, `livekit-agents[openai,google,xai]~=1.3`, `livekit[crypto]~=1.0`, ffmpeg (present ✓). `.env.local` = LiveKit Cloud creds + provider keys; **inference needs LiveKit Cloud; evaluation does not**. Published baselines exist for GPT-Realtime, Gemini Live, cascaded Whisper→LLM.

**Submission (§4):** repo + README (architecture diagram, exact setup/run steps, extension clearly marked); **one-command reproduction script** (install→configure→evaluate) + declaration of model provider/custom agent; **benchmark results + run logs** (scores, seeds, config) from own best run; **demo video 3–5 min** (real interruption handled on the benchmark, then the extension use case; unedited single takes preferred); **slide deck ≤ 8 slides** (problem, architecture, benchmark results, what's next). Submit via Google Form. Document required API keys + where they go; **never include the keys themselves**. One submission per team; the last upload counts.

**Scoring (§5):** Round 1 = **0.6 × normalized benchmark score** (organizers re-run FDB-v3 via your repro script on a standard machine — single 48 GB NVIDIA GPU, CUDA 12.x/13.x — or your declared hosted APIs; **only their re-run counts**; non-reproducing script scores zero after one contact) **+ 0.2 × use-case extension** (relevance, runs end-to-end, shown working in video) **+ 0.2 × documentation/architecture/video**. Ties break on strict pass rate. Round 2 (shortlisted): live jury demo — agent interrupted live + design Q&A; winners decided there.

**Dos & don'ts (§6):** DO use public checkpoints/hosted APIs and cite them; pin seeds/versions; test the repro script on a machine that isn't yours; keep the extension honest. **DON'T hardcode/memorize/fine-tune on benchmark test items (public answers — pattern-matching = disqualification, and they check); DON'T call your own servers at evaluation time (all agent logic in the submission); DON'T cache anything across scenarios.**

**Implications for the team:** local GPU not required if using hosted APIs (organizers re-run on their hardware); OpenAI key alone covers realtime agent + gpt-4o judge + TTS; **new deadline unknown — confirm with organizers**; the old two-queue/JSON protocol, 9-scenario kit, 40/35/15/10 scoring, 120 s cap are no longer the scored surface.



⚠️ DECK p.8 constraints are copy-pasted from Theme 4 (retrieval/corpus bullets); **the v1.0.0 guide is the operative spec** (F3).

**Per the guide ✅ [T5G]:**

- **Architecture:** dual-process — **Fast Path** (responsiveness within a few hundred ms: acknowledgments, clarification, progress narration), **Slow Path** (async tools, multimodal processing, complex reasoning), **Coordination Layer** (non-blocking execution, call cancellation, state-snapshot updates, idempotency for state-modifying actions).
- **Interface contract:** agent talks over **two asynchronous queues** (timestamped events in; actions out). **Inputs:** transcribed text chunks (with end-of-turn markers), raw audio clips (**WAV**), video frames (**PNG**), interruption signals, async tool results, scenario tool manifests. **Outputs:** spoken fillers, non-blocking tool calls (explicit `call_id`), cancellations, clarification requests, final responses carrying structured **State Snapshots** (intent + slot values).
- **Six core objectives:** (1) floor management — fast meaningful responses, no false completion claims, no excessive fillers; (2) interruption recovery — cancel superseded in-flight calls within a **few-ms grace period**, update snapshots, re-plan cleanly; (3) session slot tracking with localized corrections; (4) schema-driven tools — parse read-only vs state-modifying from manifests, **strictly no duplicate state-changing calls**; (5) multimodal grounding behind acknowledgments; (6) protocol compliance — well-formed JSON, valid snapshots/IDs.
- **Evaluation kit** (mirrors hidden environment; **released post-registration**): Virtual Clock Streaming Harness (deterministic replay, async mock tools, full trace logging); mock environment (flight search, booking, ticket creation, frame-grounded manual lookups, with latency/fault injection); **9 public canonical scenarios**; **~60 hidden scenarios**; mix **50% text / 30% audio / 20% visual** covering interruptions, chained calls, retries, clarifications, unseen tools.
- **Scoring (0–100 per scenario, strictly from trace logs):** Task Completion **40%** · Interruption Recovery **35%** · Response Latency **15%** · Safety & Protocol **10%**; × **quality multiplier 0.80–1.20** (naturalness, truthfulness, relevance); hidden multimodal scenarios × **1.5**.
- **Hard runtime constraints:** **Python 3.10–3.12**, **120 s wall-clock cap per scenario**, **300 s setup/warm-up hook**; **session-scoped memory only** ✅✅ (matches DECK p.8); out of scope: wake-word detection, voice-synthesis tuning, UI design ✅✅ (DECK p.8 wording: speech synthesis quality, wake-word detection, UI polish); focus areas: async event-loop orchestration, speculative execution, latency hiding, multimodal intent grounding.

---

## 7. Prizes & benefits

| Benefit | Terms | Source |
|---|---|---|
| Prizes worth **₹1.5 L** for top teams | Awarded 24 Oct; split ❓ unspecified (Q4) | DECK p.10 ✅ |
| **2-month summer internship**, Samsung R&D | For **selected students**; may have to appear for **MAGPIE coding test**; Edition 1: both interns converted to PPOs | DECK p.2, p.10 ✅ |
| **IEEE publications** | Edition 1 winners produced 5 IEEE conference/journal publications | DECK p.2, p.10 ✅ |
| **PRISM worklet** | Winning teams get the opportunity, with a Samsung mentor; **subject to availability of mentors, students & problem statement** | DECK p.10 ✅ |
| **Mentorship** | Kick-off + ongoing guidance from Samsung Language AI and Tech Strategy engineers | DECK p.10 ✅ |
| **Certificates** | Every **shortlisted** team (= teams appearing for the final demo): participation certificate; winners: merit certificate | DECK p.10 ✅ |

**Organisers:** Language AI Team & PRISM Team, Samsung R&D Institute India ✅ [DECK p.14, PPT s.12] · PRISM = "Preparing and Inspiring Student Minds" ✅ [INVITE] · **Queries:** `prism@samsung.com` ✅ [DECK p.14, INVITE].

---

## 8. Pre-submission checklist (actionable)

- [ ] Repo: prototype code, README with reproducible setup, Docker files
- [ ] Repo: **release tag `PRISM_GENAI_HACKATHON_Y2026`** on final commit; PPT/video/docs all inside the tagged commit
- [ ] Demo video ≤ 5 min, uploaded (YouTube/Drive), link ready
- [ ] Deck: fill `CollegeName_TeamName_Submission.pptx` — all 12 slides, esp. Theme ID, member emails, **Submission GitHub link** (slide 1), architecture diagram (slide 4), results & limitations (slide 8), brownie/differentiation (slide 10), Y/N checklist (slide 11)
- [ ] Theme-specific artifact: **T1 → `appsretrieval_results.json`** (MTEB `AppsRetrieval` on CoIR apps test split) uploaded as a GitHub Release ⚠️ CSV-vs-JSON (F2); **T5 → build against the two-queue interface + eval kit (Python 3.10–3.12, 120 s/scenario)**
- [ ] Submit once via the Google Form (link opens only for registered teams) before **25 Sep 11:59 PM**
- [ ] Fill the **AI Usage Disclosure** doc — submission route ❓ (F4/Q2)

---

## 9. Flags — problems found while reading (ask before acting on the risky ones)

| # | Severity | Problem |
|---|---|---|
| **F1** | **HIGH** | **Theme 1 scope conflict.** DECK p.4 describes agentic Q&A over a codebase (structural/usage queries, bonus = optimisation suggestions, metrics precision@k/recall/latency/indexing cost); T1G narrows it to **retrieval-ranking only** (generation explicitly out of scope, bonus = Evolutionary Retrieval, metrics NDCG@10/MRR on CoIR apps via MTEB). Build to the **guide** (it defines the actual screening) but confirm with organizers that deck items like structural queries aren't also expected at hands-on (Q1). |
| **F2** | MEDIUM | **T1G contradicts itself on file format:** p.2 says "submit a **csv** file with the responses", but everything else (incl. the MTEB code writing `appsretrieval_results.json` and the "json file" checklist) says **JSON**. MTEB emits JSON — go with JSON, confirm (Q1). |
| **F3** | MEDIUM | **Theme 5 DECK constraints are copy-pasted from Theme 4** ("full-duplex: begin retrieving…", "corpus provided") and don't match the T5 interface contract. T5G v1.0.0 (two async queues, tool manifests, Python 3.10–3.12, 120 s cap) is the operative spec. |
| **F4** | MEDIUM | **AI Usage Disclosure form is orphaned** — it exists in the folder but no document says where/how to submit it (Google Form? repo? email?). (Q2) |
| **F5** | MEDIUM | **Missing theme guides:** DECK carries attachment labels for a Theme 2 PDF ("SmartGuided Troubleshooting PDF"), a Theme 3 attachment ("Adobe Acrobat Document"), and a "Streaming RAG Guide" (Theme 4) — none are in this folder. Only Themes 1 and 5 have detailed guides. Request them (Q5). |
| **F6** | LOW | **Deck naming ambiguity:** p.12 says presentation named `CollegeName_TeamName`; p.13 + the template file say `CollegeName_TeamName_Submission.pptx`. Use the latter. |
| **F7** | LOW | DECK p.3 says "**Four** themes are confirmed below; the rest follow before launch" yet lists **five** — stale pre-launch text; all five themes are fully specified on pp. 4–8. |
| **F8** | LOW | Recurring typos in official docs ("loosing" ×2, "nomeclature", "extention", "expected on run") — docs are informal drafts; trust the dates/numbers, not proofreading. |
| **F9** | LOW | DECK p.9 header says "Six weeks, **five** milestones" but six dated milestones are listed. Cosmetic. |
| **F10** | INFO | **T1 release reconciliation:** DECK requires release **tag** `PRISM_GENAI_HACKATHON_Y2026` (the judged commit); T1G requires a GitHub **Release** carrying the MTEB JSON. Safest: create the required tag release **and attach the JSON as a release asset** — satisfies both readings (Q1). |
| **F11** | INFO | **Clock check:** today is 20 Sep → 5 days to the 25 Sep deadline; registration window (closed 16 Sep) has passed. The T5 evaluation kit ("released post registrations") should already be in your hands — if not, chase it now. |

## 10. Open questions for organizers (`prism@samsung.com`)

1. **Theme 1:** JSON or CSV for the screening file? Does the deck's structural-query/agentic scope still apply at hands-on, or is the guide's retrieval-only scope final? Should the MTEB JSON be attached to the `PRISM_GENAI_HACKATHON_Y2026` release?
2. **Where is the AI Usage Disclosure form submitted?**
3. How do theme-level quantitative scores (T1 dataset metrics / T5 scenario scores) combine with the 30/25/20/15/10 rubric?
4. How is the ₹1.5 L prize pool split?
5. Are there detailed guides for Themes 2/3/4 (the DECK's attachment labels suggest yes)? Please share.
6. Is late team registration possible for students who missed the 16 Sep deadline?
