# Build PRISM_FDB3_Colab_v2.ipynb — hardened end-to-end notebook
import json

def code(src):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": src.splitlines(keepends=True)}

def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src.splitlines(keepends=True)}

cells = []

cells.append(md("""# PRISM Theme 5 — FDB-v3 evaluation (v2, hardened)
Run cells **top to bottom, in order**. Two interaction points only: **cell 4** (paste credentials) and **cell 3** (Google Drive authorization popup).

**Interruption handling built in:**
- Every completed result is **checkpointed to Google Drive every 2 minutes** — a VM death loses nothing.
- The worker runs inside a **supervised restart loop** — crashes cost seconds, not the run.
- Cell 8 **automatically retries empty results** up to 3 passes (rate-limits, worker-death windows).
- Batch is **resumable**: it skips results that already exist.

**If the VM disconnects / you get a new VM:** run cells 2, 3, 4, 5, 6 again in the fresh VM (cell 3 restores your checkpointed results from Drive), then continue from cell 6. Never run two copies of cell 6 at once.
"""))

cells.append(code("""# @title 1. Check GPU + unzip project bundle
!nvidia-smi -L || echo "WARNING: no GPU — Runtime > Change runtime type > T4 GPU"
!unzip -q -o PRISM_Z_Colab.zip -d /content/
!ls /content/colab/prism_colab/v3/"""))

cells.append(code("""# @title 2. Install pinned stack (5–10 min)
!apt-get -qq install -y ffmpeg > /dev/null
%cd /content
!pip install -q "livekit-agents[google]==1.8.3" numpy python-dotenv pydub ffmpeg-python gdown
!pip install -q "nemo_toolkit[asr]"
import subprocess
info = subprocess.run(["pip","show","livekit-agents"], capture_output=True, text=True).stdout
print([l for l in info.splitlines() if l.startswith(("Name","Version"))])
print("stack installed")"""))

cells.append(code("""# @title 3. Unpack code, mount Drive, restore checkpoint, download data
import os, subprocess, glob, shutil
os.chdir("/content")
if not os.path.exists("/content/Full-Duplex-Bench"):
    subprocess.run(["git","clone","--depth","1","https://github.com/DanielLin94144/Full-Duplex-Bench.git"], check=True)
src = "/content/colab/prism_colab/v3"
dst = "/content/Full-Duplex-Bench/v3"
subprocess.run(["cp","-r",src+"/.",dst+"/"], check=True)
from google.colab import drive
drive.mount("/content/drive")
CK = "/content/drive/MyDrive/prism_checkpoint"
os.makedirs(CK, exist_ok=True)
prev = glob.glob(CK + "/fdb_v3_data_released/*/result_prism.json")
if prev:
    for f in prev:
        rel = os.path.relpath(f, CK)
        os.makedirs(os.path.dirname(os.path.join(dst, rel)), exist_ok=True)
        shutil.copy(f, os.path.join(dst, rel))
    print("restored", len(prev), "checkpointed results from Drive")
else:
    print("no checkpoint on Drive — starting fresh")
if not os.path.exists(dst + "/fdb_v3_data_released"):
    subprocess.run(["gdown","1SO_4MTazWQ_jvCx0dtmpQ-t40bdd07yz","-O","/content/fdb_v3_data.zip"], check=True)
    import zipfile
    with zipfile.ZipFile("/content/fdb_v3_data.zip") as z:
        z.extractall(dst)
os.makedirs(dst + "/logs", exist_ok=True)
print("examples on disk:", len(glob.glob(dst + "/fdb_v3_data_released/*/input.wav")))"""))

cells.append(code("""# @title 4. Credentials (pasted interactively, never stored in the notebook)
import getpass, os
os.makedirs("/content/Full-Duplex-Bench/v3/logs", exist_ok=True)
env = f\"\"\"LIVEKIT_URL={getpass.getpass('LIVEKIT_URL (wss://...): ')}
LIVEKIT_API_KEY={getpass.getpass('LIVEKIT_API_KEY: ')}
LIVEKIT_API_SECRET={getpass.getpass('LIVEKIT_API_SECRET: ')}
GOOGLE_API_KEY={getpass.getpass('GOOGLE_API_KEY (Gemini): ')}
\"\"\"
open("/content/Full-Duplex-Bench/v3/.env.local","w").write(env)
# quota sanity check: text API must respond BEFORE we invest 2 hours
import google.genai as genai
c = genai.Client(api_key=os.getenv("GOOGLE_API_KEY") or getpass.getpass("GOOGLE_API_KEY: "))
r = c.models.generate_content(model="gemini-3.8-flash", contents="Reply with the word OK only.")
print("TEXT QUOTA:", r.text.strip()[:20], "✅")"""))

cells.append(code("""# @title 5. Start supervised worker + VERIFY registration
import subprocess, time, os
os.chdir("/content/Full-Duplex-Bench/v3")
env = dict(os.environ, LK_PROVIDER="gemini2_5", HF_HOME="/content/hf", PRISM_GATE="0")
if os.path.exists("STOP_WORKER"): os.remove("STOP_WORKER")
sup = subprocess.Popen(
    'while [ ! -f STOP_WORKER ]; do python -u prism_agent.py start; echo sup_worker_restarted; sleep 3; done',
    shell=True, env=env, stdout=open("/content/worker.log","w"), stderr=subprocess.STDOUT)
time.sleep(35)
log = open("/content/worker.log").read()
if "registered worker" in log:
    print("WORKER REGISTERED: YES ✅")
else:
    print("WORKER REGISTERED: NO ❌ — send the output below to the assistant")
    print(log[-3000:])"""))

cells.append(code("""# @title 6. Run the 100-example benchmark (checkpointed to Drive every 2 min)
import subprocess, os, glob, shutil, time, threading
os.chdir("/content/Full-Duplex-Bench/v3")
env = dict(os.environ, HF_HOME="/content/hf", PRISM_GATE="0")
CK = "/content/drive/MyDrive/prism_checkpoint"
stop_ckpt = threading.Event()
def checkpointer():
    while not stop_ckpt.is_set():
        for f in glob.glob("fdb_v3_data_released/*/result_prism.json"):
            rel = os.path.relpath(f, ".")
            d = os.path.join(CK, os.path.dirname(rel))
            os.makedirs(d, exist_ok=True)
            shutil.copy(f, os.path.join(CK, rel))
        open("/content/last_checkpoint.txt","w").write(time.strftime("%H:%M:%S"))
        stop_ckpt.wait(120)
threading.Thread(target=checkpointer, daemon=True).start()
total = len(glob.glob("fdb_v3_data_released/*/input.wav"))
!echo "--- already done: $(ls fdb_v3_data_released/*/result_prism.json 2>/dev/null | wc -l)/$total ---"
subprocess.run(["python","-u","run_tool_benchmark_all_released.py","--provider","prism","--root_dir","fdb_v3_data_released"], env=env)
stop_ckpt.set(); time.sleep(2)
done = len(glob.glob("fdb_v3_data_released/*/result_prism.json"))
print(f"=== BATCH COMPLETE: {done}/{total} results (checkpointed to Drive) ===")"""))

cells.append(code("""# @title 6b. EARLY WARNING — run ~5 minutes after cell 6 starts
# If the first completed results have 0 tool calls, STOP and report to the assistant.
import json, glob
fs = sorted(glob.glob("/content/Full-Duplex-Bench/v3/fdb_v3_data_released/*/result_prism.json"), key=lambda p: __import__('os').path.getmtime(p))
if not fs:
    print("no results yet — first example still streaming, check again in 3 min")
else:
    for f in fs[-3:]:
        d = json.load(open(f, encoding="utf-8"))
        print(d.get("example_id"), "| tool calls:", len(d.get("actual_tool_calls", [])))"""))

cells.append(code("""# @title 7. Auto-retry empty results (up to 3 passes — handles rate limits & worker deaths)
import subprocess, os, glob, json
os.chdir("/content/Full-Duplex-Bench/v3")
env = dict(os.environ, HF_HOME="/content/hf", PRISM_GATE="0")
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

cells.append(code("""# @title 8. Evaluate (tool F1, pass rate, latency)
import subprocess, os, json
os.chdir("/content/Full-Duplex-Bench/v3")
B = "--benchmark benchmark_data_v2.json --results-dir fdb_v3_data_released --provider prism"
subprocess.run(f"python evaluate_tool_calls.py {B} --output prism_evaluation_report.json", shell=True)
subprocess.run(f"python evaluate_pass_rate.py {B} --output prism_pass_rate_report.json", shell=True)
subprocess.run(f"python analyze_tool_latency.py --results-dir fdb_v3_data_released --provider prism", shell=True)
r = json.load(open("prism_pass_rate_report.json"))
print("\\n=== STRICT PASS RATE:", r["overall_pass_rate"], f"({r['passed']}/{r['total_scenarios']}) ===")
e = json.load(open("prism_evaluation_report.json"))
print("evaluation report keys:", list(e.keys())[:8])"""))

cells.append(code("""# @title 9. Package, copy to Drive, download
import zipfile, os, glob, shutil
os.chdir("/content/Full-Duplex-Bench/v3")
with zipfile.ZipFile("/content/prism_results.zip","w",zipfile.ZIP_DEFLATED) as z:
    for f in glob.glob("fdb_v3_data_released/*/result_prism.json"):
        z.write(f)
    for f in glob.glob("prism_*.json") + glob.glob("logs/*.log"):
        z.write(f)
shutil.copy("/content/prism_results.zip", "/content/drive/MyDrive/prism_checkpoint/prism_results.zip")
print("size MB:", round(os.path.getsize("/content/prism_results.zip")/1e6, 1), "| also saved to Drive/prism_checkpoint/")
from google.colab import files
files.download("/content/prism_results.zip")"""))

nb = {
    "nbformat": 4,
    "nbformat_minor": 0,
    "metadata": {"accelerator": "GPU", "colab": {"provenance": []},
                 "kernelspec": {"display_name": "Python 3", "name": "python3"},
                 "language_info": {"name": "python"}},
    "cells": cells,
}
json.dump(nb, open("colab/PRISM_FDB3_Colab_v2.ipynb", "w", encoding="utf-8"), indent=1)
print("PRISM_FDB3_Colab_v2.ipynb written:", len(cells), "cells")
