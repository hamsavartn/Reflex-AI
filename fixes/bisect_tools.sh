#!/bin/bash
# Bisect: find the commit that broke tool calls, by live-running one example
# against each historical prism_agent.py. Restores the current file at the end.
ROOT=/c/Users/ASUS/Desktop/PRISM_Z
V3=$ROOT/fdb3/v3
PY=$ROOT/.venv-fdb/Scripts/python.exe
cd "$V3"
powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force" 2>/dev/null
sleep 2
git -C "$ROOT" show 2f5e15f:fdb3/v3/prism_agent.py > /c/Users/ASUS/Desktop/PRISM_Z/tmp_bisect/r1.py 2>/dev/null
for CMT in 2f5e15f 20eb4fe 2d7088a fb6ac24 c296aec; do
  LABEL=$(git -C "$ROOT" log --format="%h %s" -1 $CMT | cut -c1-60)
  git -C "$ROOT" show $CMT:fdb3/v3/prism_agent.py > "$V3/prism_agent.py" 2>/dev/null || { echo "$CMT: git show failed"; continue; }
  rm -f logs/agent_tool_calls.log
  echo "===================== testing $LABEL"
  (LK_PROVIDER=gemini2_5 PRISM_GATE=0 HF_HOME="/c/Users/ASUS/Desktop/PRISM_Z/hf-cache" "$PY" -u prism_agent.py start > /c/Users/ASUS/Desktop/PRISM_Z/worker_bisect.log 2>&1 &)
  sleep 30
  (cd "$V3" && HF_HOME="/c/Users/ASUS/Desktop/PRISM_Z/hf-cache" "$PY" run_tool_benchmark_all_released.py --provider prism --root_dir fdb_v3_data_test --force > /c/Users/ASUS/Desktop/PRISM_Z/runner_bisect.log 2>&1)
  CALLS=$(grep -c '"function"' logs/agent_tool_calls.log 2>/dev/null || echo 0)
  TR=$("$PY" -c "
import json, glob
for f in glob.glob('fdb_v3_data_test/*/result_prism.json'):
    d = json.load(open(f, encoding='utf-8'))
    print(repr((d.get('transcript') or '')[:90]))" 2>/dev/null | head -1)
  echo ">>> $CMT | tool-call lines: $CALLS | last transcript: $TR"
  powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force" 2>/dev/null
  sleep 3
done
cp /c/Users/ASUS/Desktop/PRISM_Z/tmp_bisect/prism_agent_cur.py "$V3/prism_agent.py"
echo "current file restored"
