# PRISM_Z_Colab — bundle contents

Upload this zip to Colab next to `PRISM_FDB3_Colab.ipynb` and Run all. The
notebook clones the upstream benchmark fresh, copies these patched files over
it, downloads the public data, and runs the 100-sample evaluation.

## Why a fresh clone + file overlay?

The upstream repo is CC BY-NC (attribution required, non-commercial). The
submission must make every modification explicit and reproducible. This bundle
contains ONLY our additions/patches, applied onto a pristine upstream clone:

| File | Origin | Purpose |
|---|---|---|
| `v3/prism_agent.py` | ours (template + fixes 1–6 + recovery layer + extension tools) | the submitted agent |
| `v3/run_tool_benchmark.py` | upstream + PRISM patches P2 (CPU fallback), Fix 2 (telemetry path) | runner |
| `v3/lk_agent_tool.py` | upstream + PRISM patches P1, P2, P3 | template (baseline reference) |
| `v3/livekit_inference.py` | upstream + P1 | client |
| `v3/make_prism_agent.py` | ours | provenance: how prism_agent.py derives from the template (documentation of our diff) |
| `fixes/` | ours | one-shot patch scripts (audit trail) |

## Keys needed when the notebook asks

- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` — free at cloud.livekit.io
- `GOOGLE_API_KEY` — Gemini key from aistudio.google.com

Keys go to `v3/.env.local` (gitignored upstream), are never printed, and are
NEVER included in the results zip.

## Results you get back

`prism_results.zip` = 100 × `result_prism.json` + the three evaluation reports
+ agent logs. Drop it into the project folder — the evaluation is reproducible
from these JSONs alone.
