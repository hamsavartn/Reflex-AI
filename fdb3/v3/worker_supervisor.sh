#!/bin/bash
# PRISM worker supervisor: restarts the agent worker whenever the soxr assert
# kills it, until STOP file appears. Run the benchmark runner in a second shell.
cd "$(dirname "$0")"
LIFE=0
while [ ! -f STOP_WORKER ]; do
  LIFE=$((LIFE+1))
  echo "[supervisor] worker life $LIFE starting $(date +%T)"
  LK_PROVIDER="${LK_PROVIDER:-gemini2_5}" HF_HOME="C:/Users/ASUS/Desktop/PRISM_Z/hf-cache" \
    "C:/Users/ASUS/Desktop/PRISM_Z/.venv-fdb/Scripts/python.exe" -u prism_agent.py start
  echo "[supervisor] worker exited code=$? at $(date +%T); restarting in 5s"
  sleep 5
done
echo "[supervisor] STOP_WORKER found; exiting"
