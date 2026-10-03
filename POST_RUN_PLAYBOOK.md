# POST_RUN_PLAYBOOK.md — End-to-end submission guide (machine-executable)
### Audience: an AI agent (any capability level) executing the final submission steps for the Samsung PRISM GenAI Hackathon 3.0, Theme 5.
### Read this file top-to-bottom. Execute steps IN ORDER. Never skip a VERIFY. If a VERIFY fails, follow the FIX branch. If no FIX branch matches, STOP and ask the human.

---

## 0. CONTEXT SNAPSHOT (know this before acting)

- Project root: `C:\Users\ASUS\Desktop\PRISM_Z` (Windows, Git Bash shell).
- Python for benchmark work: `C:\Users\ASUS\Desktop\PRISM_Z\.venv-fdb\Scripts\python.exe` (call it `$PY`).
- The submitted agent: `fdb3/v3/prism_agent.py` (final version: recovery layer + verification gate, commit c296aec or later).
- Baseline numbers (for the deck): strict pass **29%** (`results/strict/gemini2_5_pass_rate_report.json`), lenient re-score **81%** (`results/lenient/gemini2_5_pass_rate_report.json`).
- GitHub repo: `https://github.com/hamsavartn/Reflex-AI`, branch `master`, git identity already set repo-locally to `Hamsavarthan <hamsavarthan2211@gmail.com>` — do NOT change it, do NOT use `--global`.
- Deck: `deliverables/AuraStream_Deck.pptx` — exactly 8 slides (limit is 8; never add slides). Slide 5 contains placeholders: `[FINAL_PASS]`, `[FINAL_F1]`, `[FINAL_ARG]`, `[FINAL_LAT]`.
- Video script: `deliverables/VIDEO_SCRIPT.md`. Disclosure draft: `deliverables/AI_DISCLOSURE_DRAFT.md`.
- Release tag name (EXACT, disqualification-grade): `PRISM_GENAI_HACKATHON_Y2026`.

### HARD RULES (violating any = disqualification or lost points)
1. NEVER commit API keys or `.env*` files. Before every push, run the secret scan in Step 6.4.
2. NEVER hardcode answers to specific benchmark scenarios (IDs, expected args) anywhere in code or prompts. All improvements must be general mechanisms.
3. NEVER add a 9th slide to the deck.
4. NEVER force-push over someone else's commits; `--force-with-lease` only, and only when Step 6 says so.
5. NEVER edit files inside `fdb3/` except through the explicit patch steps in this playbook.
6. If any VERIFY fails and no FIX branch resolves it: STOP, report to the human, change nothing else.

---

## 1. PHASE 0 — Detect the Colab run state

Ask/check exactly one of these cases:

- **Case A (normal):** the human hands you `prism_results.zip`, now at `C:\Users\ASUS\Desktop\PRISM_Z\prism_results.zip`. → Go to Phase 1.
- **Case B (browser renamed it):** a file like `prism_results (1).zip` exists in `C:\Users\ASUS\Downloads\`. → Rename (move) it to `C:\Users\ASUS\Desktop\PRISM_Z\prism_results.zip`, then Phase 1.
- **Case C (no zip, run still going):** Colab cell 6 still counting. → Wait. Do nothing else.
- **Case D (Colab failed/interrupted):** the human reports a traceback or fewer than 100 results. → Fix branches in Phase 1 VERIFY-2.

---

## 2. PHASE 1 — Ingest and validate results

### Step 1.1 — Integrity check
```bash
cd "C:\Users\ASUS\Desktop\PRISM_Z"
"C:\Users\ASUS\Desktop\PRISM_Z\.venv-fdb\Scripts\python.exe" -c "import zipfile; z=zipfile.ZipFile('prism_results.zip'); print('entries:', len(z.namelist()), '| corrupt:', z.testzip() is not None)"
```
**VERIFY:** `corrupt: True` must be False and entries ≥ 100.
**FIX:** if corrupt → the download truncated; re-download from Colab (cell 8 again) or ask the human to re-download from the browser. If the Colab VM is gone, see Phase 1 VERIFY-2 FIX.

### Step 1.2 — Extract into the benchmark tree (eval scripts need this layout)
```bash
"C:\Users\ASUS\Desktop\PRISM_Z\.venv-fdb\Scripts\python.exe" -c "import zipfile; zipfile.ZipFile('prism_results.zip').extractall('fdb3/v3')"
```
This places `fdb_v3_data_released/*/result_prism.json`, `prism_*_report.json`, and `logs/*.log` under `fdb3/v3/`.

### Step 1.3 — Count results
```bash
ls fdb3/v3/fdb_v3_data_released/*/result_prism.json | wc -l
```
**VERIFY:** exactly **100**.
**FIX (Case D):** if fewer → the Colab run was incomplete. Instructions to the human: re-open the SAME Colab VM (do NOT let it reset), re-run cell 6 (it resumes), then cell 8, and re-deliver the zip. If the VM is gone, the full notebook must be re-run (cells 1→8). Do NOT proceed with a partial set unless the human explicitly orders it.

### Step 1.4 — Count healthy results (no silent agent failures)
```bash
"C:\Users\ASUS\Desktop\PRISM_Z\.venv-fdb\Scripts\python.exe" -c "
import json, glob
empty = [f for f in glob.glob('fdb3/v3/fdb_v3_data_released/*/result_prism.json')
         if not json.load(open(f, encoding='utf-8')).get('actual_tool_calls')]
print('healthy:', 100 - len(empty), '| empty:', len(empty))"
```
**VERIFY:** `empty` ≤ 10.
**FIX:** if `empty` > 10 → the worker underperformed on Colab too. Report the number to the human with the list of example IDs; recommend re-running cell 6 with `--force` omitted so only empties are retried (delete those result files first: `rm fdb3/v3/fdb_v3_data_released/<empty_dirs>/result_prism.json`), then re-download the zip and restart this phase.

---

## 3. PHASE 2 — Cross-validate the numbers locally (never trust, always verify)

Run from `fdb3/v3` (evaluation needs no LiveKit, no GPU, no model download):

```bash
cd "C:\Users\ASUS\Desktop\PRISM_Z\fdb3\v3"
B="--benchmark benchmark_data_v2.json --results-dir fdb_v3_data_released --provider prism"
"C:\Users\ASUS\Desktop\PRISM_Z\.venv-fdb\Scripts\python.exe" evaluate_tool_calls.py $B --output prism_evaluation_report_local.json
"C:\Users\ASUS\Desktop\PRISM_Z\.venv-fdb\Scripts\python.exe" evaluate_pass_rate.py $B --output prism_pass_rate_report_local.json
"C:\Users\ASUS\Desktop\PRISM_Z\.venv-fdb\Scripts\python.exe" analyze_tool_latency.py --results-dir fdb_v3_data_released --provider prism
```

**VERIFY:** `prism_pass_rate_report_local.json` exists and `total_scenarios == 100`.
**FIX:** if a script errors with a missing-file path → the extraction in Step 1.2 went to the wrong place; re-run Step 1.2 exactly.

**RECORD these four numbers** (read from `prism_pass_rate_report_local.json` and `prism_evaluation_report_local.json`):
`overall_pass_rate`, `passed`, plus from the evaluation report: tool-selection **F1** and **argument accuracy** (keys: look for `tool_selection_f1`/`f1` and `argument_accuracy`/`argument_acc` — print the whole JSON if key names differ and read the values directly).

**COMPARE to baseline:** baseline strict pass = 0.29 (29%). Expected: the final number is meaningfully higher. Report baseline→final delta to the human.

---

## 4. PHASE 3 — Copy evidence into the repo (tracked area)

`fdb3/` contains gitignored paths, so evidence must ALSO live under `results/`:

```bash
cd "C:\Users\ASUS\Desktop\PRISM_Z"
mkdir -p results/prism
cp fdb3/v3/prism_evaluation_report_local.json results/prism/
cp fdb3/v3/prism_pass_rate_report_local.json results/prism/
cp fdb3/v3/prism_*.json results/prism/ 2>/dev/null
"C:\Users\ASUS\Desktop\PRISM_Z\.venv-fdb\Scripts\python.exe" -c "
import zipfile, glob, os
with zipfile.ZipFile('results/prism/prism_results_archive.zip','w',zipfile.ZIP_DEFLATED) as z:
    for f in glob.glob('fdb3/v3/fdb_v3_data_released/*/result_prism.json'): z.write(f)
print('archived', len(z.namelist()) if False else 'results into results/prism/prism_results_archive.zip')"
```

**VERIFY:** `results/prism/` contains at least 3 files including the archive.

---

## 5. PHASE 4 — Fill the deck placeholders

```bash
cd "C:\Users\ASUS\Desktop\PRISM_Z"
".venv\Scripts\python.exe" - <<'PYEOF'
from pptx import Presentation
import json
r = json.load(open('results/prism/prism_pass_rate_report_local.json', encoding='utf-8'))
e = json.load(open('results/prism/prism_evaluation_report_local.json', encoding='utf-8'))
def find(d, keys, default='[TBD]'):
    for k in keys:
        if k in d: return d[k]
    for v in d.values():
        if isinstance(v, dict):
            f = find(v, keys, default)
            if f != default: return f
    return default
pass_rate = find(r, ['overall_pass_rate','pass_rate'])
passed = find(r, ['passed'])
total = find(r, ['total_scenarios'])
f1 = find(e, ['tool_selection_f1','f1','macro_f1'])
arg = find(e, ['argument_accuracy','argument_acc','avg_argument_accuracy'])
prs = Presentation('deliverables/AuraStream_Deck.pptx')
repl = {'[FINAL_PASS]': f"{pass_rate*100:.0f}% ({passed}/{total})" if isinstance(pass_rate,(int,float)) and pass_rate<=1 else f"{pass_rate}",
        '[FINAL_F1]': f"{f1*100:.0f}%" if isinstance(f1,(int,float)) and f1 is not None and f1<=1 else str(f1),
        '[FINAL_ARG]': f"{arg*100:.0f}%" if isinstance(arg,(int,float)) and arg is not None and arg<=1 else str(arg),
        '[FINAL_LAT]': str(find(e, ['first_response_latency','median_first_response','latency'], 'see latency report'))}
n = 0
for slide in prs.slides:
    for shape in slide.shapes:
        if not shape.has_text_frame: continue
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                for k, v in repl.items():
                    if k in run.text:
                        run.text = run.text.replace(k, v); n += 1
prs.save('deliverables/AuraStream_Deck.pptx')
print('replacements:', n, repl)
PYEOF
```
**VERIFY:** `replacements:` is 4 (or 3 if the latency placeholder was already free-form).
**FIX:** if `replacements: 0` → the placeholders were already filled (idempotent re-run) — acceptable.
**FIX:** if a metric key was not found (`[TBD]` appears) → print the report JSON fully, locate the correct key manually, and redo the replacement for that placeholder only. Do not guess numbers.

---

## 6. PHASE 5 — README, commit, tag, release

### Step 6.1 — README checklist (open `README.md`; each line must be true, add if missing)
- [ ] What the project is (Theme 5 agent, one sentence)
- [ ] Architecture summary + the three mechanisms
- [ ] Exact setup steps (keys required: `GOOGLE_API_KEY`, `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` — names only, no values)
- [ ] "Model provider declaration: Gemini 2.5 Flash Native Audio via LiveKit (+ gemini-3.8-flash for the verification gate)"
- [ ] The extension use case clearly marked: "Device troubleshooting (manual lookup + deeplink)"
- [ ] Benchmark results (the numbers from Phase 2) + baseline comparison
- [ ] One-command reproduction: point to `reproduce.sh` AND `colab/PRISM_FDB3_Colab.ipynb`
- [ ] Honest limitations paragraph

### Step 6.2 — Commit everything
```bash
cd "C:\Users\ASUS\Desktop\PRISM_Z"
git add -A
git commit -m "Final submission: results, filled deck, README"
```

### Step 6.3 — Secret scan (MANDATORY before push)
```bash
git grep -lE "AQ\.Ab8|APIC9Q|AIzaSy|sk-[A-Za-z0-9]{20}|LIVEKIT_API_SECRET=[A-Za-z0-9]" -- . | grep -vE "README|reproduce|\.ipynb" 
```
**VERIFY:** output is empty (template variable NAMES in README/reproduce/notebook are allowed; VALUES are not).
**FIX:** if any real value appears → `git rm --cached <file>`, add the file to `.gitignore`, commit, and re-scan. Never push a key.

### Step 6.4 — Push and tag
```bash
git push origin master
git tag -a PRISM_GENAI_HACKATHON_Y2026 -m "Final submission — Samsung PRISM GenAI Hackathon 3.0, Theme 5"
git push origin PRISM_GENAI_HACKATHON_Y2026
```
**VERIFY:** `git tag -l` shows the tag; the push output lists it.

### Step 6.5 — GitHub Release (web UI; `gh` CLI is not installed)
1. Open `https://github.com/hamsavartn/Reflex-AI/releases/new`
2. "Choose a tag" → select `PRISM_GENAI_HACKATHON_Y2026`
3. Title: `Final submission — Theme 5`; Description: 3 lines (agent, results, repro pointer)
4. Attach `results/prism/prism_results_archive.zip` as a binary asset
5. **Publish release**
**VERIFY:** the release page lists the tag and the asset. Report the release URL to the human.

---

## 7. PHASE 6 — Human-only steps (agent must NOT do these; hand over this checklist)

1. **Record the video** per `deliverables/VIDEO_SCRIPT.md` (≤ 5:00, single takes). Upload YouTube-unlisted or Drive. TEST the link in an incognito window.
2. **AI disclosure:** copy `deliverables/AI_DISCLOSURE_DRAFT.md` content into `LangAI3.0_AI_Disclosure.docx`, fill name/college/date, sign.
3. **Deck export:** optionally also export `AuraStream_Deck.pptx` to PDF for the form.
4. **Google Form:** fill once — repo link (after Step 6.4), video link (after upload), deck attached/named `CollegeName_TeamName_Submission.pptx`. Screenshot the confirmation. Last upload counts; submit only when every link is tested.
5. Confirm the deadline time with organizers; do not submit a known-broken link because of deadline panic — a resubmission before the deadline is allowed (last upload counts).

---

## 8. FAILURE DECISION TREE (quick reference)

| Symptom | Action |
|---|---|
| `prism_results.zip` corrupt | re-download from Colab cell 8; if VM gone → full notebook re-run |
| results < 100 | re-run Colab cell 6 (same VM), then cells 7–8, new zip |
| empty agent results > 10 | delete those `result_prism.json`, re-run cell 6, new zip |
| eval script path error | re-run Phase 1 Step 1.2 extraction |
| metric key not found in report | print the JSON, read values manually, never guess |
| secret scan positive | untrack file, gitignore, re-commit, re-scan |
| push rejected (non-fast-forward) | `git pull --rebase origin master`, resolve, push again; never plain force-push |
| anything unmapped | STOP, report to human |

## 9. DEFINITION OF DONE (all must be true)

- [ ] `results/prism/prism_pass_rate_report_local.json` with 100 scenarios
- [ ] Deck has zero `[FINAL_` placeholders
- [ ] README checklist (Step 6.1) fully checked
- [ ] Tag `PRISM_GENAI_HACKATHON_Y2026` pushed and visible on GitHub
- [ ] GitHub Release published with the results asset
- [ ] Secret scan clean
- [ ] Human has: video link (tested), signed disclosure, form submitted, confirmation screenshot
