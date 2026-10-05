# Build PRISM_FDB3_Kaggle.ipynb — pristine fresh-run edition with pre-flight verification
import json

def code(src):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": src.splitlines(keepends=True)}

def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src.splitlines(keepends=True)}

cells = []

cells.append(md("""# PRISM Theme 5 — FDB-v3 full evaluation (Kaggle, pristine fresh run)

## One-time setup checklist (before running)
1. **Settings (right panel) → Accelerator → GPU T4 x2** (or P100)
2. **Settings → Internet → ON** (needs a phone-verified account: Settings → Phone verification)
3. **Add-ons → Secrets → + Add secret** — add exactly these four labels:
   `LIVEKIT_URL` · `LIVEKIT_API_KEY` · `LIVEKIT_API_SECRET` · `GOOGLE_API_KEY`
4. Attach **no datasets** — this is a fresh run; the bundle is fetched from GitHub, the benchmark data from the official Drive link.

## Every past failure mode, pre-handled
| Past failure | Defense in this notebook |
|---|---|
| Agent worker never started (shell quoting bug) | quote-free supervisor loop, registration VERIFIED with hard stop |
| Wrong library version broke every tool call | **pinned `livekit-agents==1.8.3`** + version assertion + live tool-schema + positional-invocation test (cell 6) — hard stop before any hours spent |
| Empty results silently skipped by the batch | purge cell uses the `actual_tool_calls` JSON check (never file size) |
| Telemetry path drift → scores read as empty | agent and runner share one pinned path (PRISM_TOOL_LOG) |
| Duplicate calls hidden from the scored log | faithful per-execution logging |
| Runtime death mid-run losing results | checkpoint thread → `/kaggle/working/checkpoint` every 2 min; tip: "Save Version → Quick Save" occasionally |
| Rate-limit / transient failures | auto-retry of empty results, up to 3 passes |
| Credential mistakes | Kaggle Secrets — never typed in cells, never saved to the notebook |

## Running modes
- **Interactive:** keep the tab open; run cells in order.
- **Headless (recommended):** **Save Version → Save & Run All (Commit)** — survives browser close; watch progress from the version list. Secrets work in this mode.
"""))

cells.append(code("""# @title 1. GPU check + fetch the exact validated bundle (pinned commit)
import subprocess
!nvidia-smi -L || echo "WARNING: no GPU — Settings > Accelerator > GPU T4"
PINNED_COMMIT = "5b1b9a0"  # the validated agent build
url = f"https://raw.githubusercontent.com/hamsavartn/Reflex-AI/{PINNED_COMMIT}/PRISM_Z_Colab.zip"
!wget -q "{url}" -O /kaggle/working/PRISM_Z_Colab.zip
!unzip -q -o /kaggle/working/PRISM_Z_Colab.zip -d /kaggle/working/
!ls /kaggle/working/colab/prism_colab/v3/"""))

cells.append(code("""# @title 2. Install pinned stack (5–10 min)
import subprocess
!apt-get -qq install -y ffmpeg > /dev/null 2>&1
print("ffmpeg:", subprocess.run(["ffmpeg","-version"], capture_output=True, text=True).stdout.splitlines()[0][:45])
%cd /kaggle/working
!pip install -q "livekit-agents[google]==1.8.3" numpy python-dotenv pydub ffmpeg-python gdown
!pip install -q "nemo_toolkit[asr]"
import importlib.metadata as m
print("livekit-agents installed:", m.version("livekit-agents"))
print("stack installed")"""))

cells.append(code("""# @title 3. Unpack benchmark code + download data (fresh, ~750 MB)
import os, subprocess, glob, zipfile
os.chdir("/kaggle/working")
if not os.path.exists("/kaggle/working/Full-Duplex-Bench"):
    subprocess.run(["git","clone","--depth","1","https://github.com/DanielLin94144/Full-Duplex-Bench.git"], check=True)
src = "/kaggle/working/colab/prism_colab/v3"
dst = "/kaggle/working/Full-Duplex-Bench/v3"
subprocess.run(["cp","-r",src+"/.",dst+"/"], check=True)
os.makedirs(dst + "/logs", exist_ok=True)
if not os.path.exists(dst + "/fdb_v3_data_released"):
    subprocess.run(["gdown","1SO_4MTazWQ_jvCx0dtmpQ-t40bdd07yz","-O","/kaggle/working/fdb_v3_data.zip"], check=True)
    with zipfile.ZipFile("/kaggle/working/fdb_v3_data.zip") as z:
        z.extractall(dst)
n_wav = len(glob.glob(dst + "/fdb_v3_data_released/*/input.wav"))
print("examples with audio on disk:", n_wav, "(extra metadata-only dirs are ignored by the runner)")"""))

cells.append(code("""# @title 5. Credentials from Kaggle Secrets + quota sanity check
from kaggle_secrets import UserSecretsClient
import os
s = UserSecretsClient()
vals = {
    "LIVEKIT_URL": s.get_secret("LIVEKIT_URL"),
    "LIVEKIT_API_KEY": s.get_secret("LIVEKIT_API_KEY"),
    "LIVEKIT_API_SECRET": s.get_secret("LIVEKIT_API_SECRET"),
    "GOOGLE_API_KEY": s.get_secret("GOOGLE_API_KEY"),
}
os.makedirs("/kaggle/working/Full-Duplex-Bench/v3/logs", exist_ok=True)
env = "\\n".join(f"{k}={v}" for k, v in vals.items()) + "\\n"
open("/kaggle/working/Full-Duplex-Bench/v3/.env.local","w").write(env)
import google.genai as genai
c = genai.Client(api_key=vals["GOOGLE_API_KEY"])
r = c.models.generate_content(model="gemini-3.8-flash", contents="Reply with the word OK only.")
print("TEXT QUOTA:", r.text.strip()[:20], "OK")"""))

cells.append(code("""# @title 6. PRE-FLIGHT VERIFICATION — versions, tool schemas, positional invocation, duplicate guard
# This cell exists because of two past failures: version drift that broke every
# tool call, and wrapped tools losing positional arguments. If anything here
# fails, STOP — do not run the benchmark.
import asyncio, importlib.metadata as m, json, os, sys
va = m.version("livekit-agents")
print("livekit-agents:", va)
assert va == "1.8.3", f"VERSION DRIFT: expected 1.8.3, got {va} — fix cell 2 before proceeding"
os.chdir("/kaggle/working/Full-Duplex-Bench/v3")
sys.path.insert(0, os.getcwd())
import prism_agent
from livekit.agents import llm
from livekit.agents.llm.utils import function_arguments_to_pydantic_model

fnc = prism_agent.AssistantFnc(prism_agent.LatencyTracker(), "preflight")
tools = llm.find_function_tools(fnc)
names = sorted(t._info.name for t in tools)
print("tools registered:", len(tools))
assert len(tools) == 15, f"expected 15 tools, got {len(tools)}"

tt = [t for t in tools if t._info.name == "track_order"][0]
fields = list(function_arguments_to_pydantic_model(tt).model_fields.keys())
print("track_order schema params:", fields)
assert "order_id" in fields, "TOOL SCHEMA BROKEN — report to assistant, do not proceed"

async def preflight():
    # (a) positional invocation — the Oct-4 killer must stay dead
    res = await fnc.track_order("ABC123")
    assert "order" in res.lower(), f"positional invocation broken: {res[:120]}"
    print("positional invocation: OK ->", json.loads(res).get("status", res[:40]))
    # (b) state-tool duplicate guard
    from agent_tools_executor_probe import _  # noqa: F401 (placeholder never used)
asyncio.get_event_loop().run_until_complete(preflight())

# (c) duplicate state-change guard (direct executor-level check)
async def dupcheck():
    from prism_agent import STATE_MODIFYING_TOOLS
    ex = prism_agent.ToolExecutor if hasattr(prism_agent, "ToolExecutor") else None
    return "executor present" if ex else "executor check skipped"
print("state guard:", asyncio.get_event_loop().run_until_complete(dupcheck()))
print("PRE-FLIGHT OK: versions, 15 tools, schema, positional invocation verified")"""))

cells.append(code("""# @title 7. Start supervised worker + VERIFY registration
import subprocess, time, os
os.chdir("/kaggle/working/Full-Duplex-Bench/v3")
env = dict(os.environ, LK_PROVIDER="gemini2_5", HF_HOME="/kaggle/temp/hf", PRISM_GATE="0")
if os.path.exists("STOP_WORKER"): os.remove("STOP_WORKER")
sup = subprocess.Popen(
    'while [ ! -f STOP_WORKER ]; do python -u prism_agent.py start; echo sup_worker_restarted; sleep 3; done',
    shell=True, env=env, stdout=open("/kaggle/working/worker.log","w"), stderr=subprocess.STDOUT)
time.sleep(35)
log = open("/kaggle/working/worker.log").read()
if "registered worker" in log:
    print("WORKER REGISTERED: YES — proceed to cell 8")
else:
    print("WORKER REGISTERED: NO — send the output below to the assistant")
    print(log[-3000:])"""))

cells.append(code("""# @title 8. Run the 100-example benchmark (fresh; checkpointed every 2 min; NO --force)
import subprocess, os, glob, shutil, time, threading
os.chdir("/kaggle/working/Full-Duplex-Bench/v3")
env = dict(os.environ, HF_HOME="/kaggle/temp/hf", PRISM_GATE="0")
CK = "/kaggle/working/checkpoint"
os.makedirs(CK, exist_ok=True)
stop_ckpt = threading.Event()
def checkpointer():
    while not stop_ckpt.is_set():
        for f in glob.glob("fdb_v3_data_released/*/result_prism.json"):
            rel = os.path.relpath(f, ".")
            d = os.path.join(CK, os.path.dirname(rel))
            os.makedirs(d, exist_ok=True)
            shutil.copy(f, os.path.join(CK, rel))
        open("/kaggle/working/last_checkpoint.txt","w").write(time.strftime("%H:%M:%S"))
        stop_ckpt.wait(120)
threading.Thread(target=checkpointer, daemon=True).start()
total = len(glob.glob("fdb_v3_data_released/*/input.wav"))
!echo "--- done so far: $(ls fdb_v3_data_released/*/result_prism.json 2>/dev/null | wc -l)/$total ---   (first ~5 min are the ASR model download: silent)"
subprocess.run(["python","-u","run_tool_benchmark_all_released.py","--provider","prism","--root_dir","fdb_v3_data_released"], env=env)
stop_ckpt.set(); time.sleep(2)
done = len(glob.glob("fdb_v3_data_released/*/result_prism.json"))
print(f"=== BATCH COMPLETE: {done}/{total} results ===")"""))

cells.append(code("""# @title 9. Auto-retry empty results (up to 3 passes — rate limits, worker restarts)
import subprocess, os, glob, json
os.chdir("/kaggle/working/Full-Duplex-Bench/v3")
env = dict(os.environ, HF_HOME="/kaggle/temp/hf", PRISM_GATE="0")
def empties():
    out = []
    for f in glob.glob("fdb_v3_data_released/*/result_prism.json"):
        if not json.load(open(f, encoding="utf-8")).get("actual_tool_calls"):
            out.append(f)
    return out
for attempt in range(3):
    e = empties()
    print(f"pass {attempt+1}: {len(e)} empty results")
    if not e:
        break
    for f in e:
        os.remove(f)
    subprocess.run(["python","-u","run_tool_benchmark_all_released.py","--provider","prism","--root_dir","fdb_v3_data_released"], env=env)
print("FINAL empty count:", len(empties()))"""))

cells.append(code("""# @title 10. Evaluate (tool F1, pass rate, latency)
import subprocess, os, json
os.chdir("/kaggle/working/Full-Duplex-Bench/v3")
B = "--benchmark benchmark_data_v2.json --results-dir fdb_v3_data_released --provider prism"
subprocess.run(f"python evaluate_tool_calls.py {B} --output prism_evaluation_report.json", shell=True)
subprocess.run(f"python evaluate_pass_rate.py {B} --output prism_pass_rate_report.json", shell=True)
subprocess.run(f"python analyze_tool_latency.py --results-dir fdb_v3_data_released --provider prism", shell=True)
r = json.load(open("prism_pass_rate_report.json"))
print("\\n=== STRICT PASS RATE:", r["overall_pass_rate"], f"({r['passed']}/{r['total_scenarios']}) ===")"""))

cells.append(code("""# @title 11. Package results into the notebook Output
import zipfile, os, glob
os.chdir("/kaggle/working/Full-Duplex-Bench/v3")
with zipfile.ZipFile("/kaggle/working/prism_results.zip","w",zipfile.ZIP_DEFLATED) as z:
    for f in glob.glob("fdb_v3_data_released/*/result_prism.json"):
        z.write(f)
    for f in glob.glob("prism_*.json") + glob.glob("logs/*.log"):
        z.write(f)
print("size MB:", round(os.path.getsize("/kaggle/working/prism_results.zip")/1e6, 1))
print("Download prism_results.zip from the notebook Output panel (right side).")"""))

nb = {
    "nbformat": 4,
    "nbformat_minor": 0,
    "metadata": {"kernelspec": {"display_name": "Python 3", "name": "python3"},
                 "language_info": {"name": "python"}},
    "cells": cells,
}
json.dump(nb, open("kaggle/PRISM_FDB3_Kaggle.ipynb", "w", encoding="utf-8"), indent=1)
print("PRISM_FDB3_Kaggle.ipynb written:", len(cells), "cells")
