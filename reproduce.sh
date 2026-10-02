#!/bin/bash
# reproduce.sh - Repro script for Samsung PRISM GenAI Hackathon 3.0 Theme 5
# This script sets up the environment and runs the evaluation pipeline.

echo "========================================================="
echo " Samsung PRISM GenAI Hackathon 3.0 - Theme 5"
echo " LiveKit Interruptible Real-Time Agent - Reproduce Script"
echo "========================================================="

# 1. Check for API keys
if [ ! -f "fdb3/v3/.env.local" ]; then
    echo "ERROR: fdb3/v3/.env.local not found!"
    echo "Please create it and add:"
    echo "GEMINI_API_KEY=your_gemini_key"
    echo "LIVEKIT_URL=your_livekit_url"
    echo "LIVEKIT_API_KEY=your_livekit_api_key"
    echo "LIVEKIT_API_SECRET=your_livekit_api_secret"
    exit 1
fi

echo "[1/6] Checking system requirements..."
python3 -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'" || exit 1
ffmpeg -version >/dev/null 2>&1 || { echo "ffmpeg not found. Please install ffmpeg first."; exit 1; }

echo "[2/6] Creating virtual environment..."
python3 -m venv .venv-repro
source .venv-repro/bin/activate

echo "[3/6] Installing dependencies..."
pip install --upgrade pip
pip install -r requirements-fdb.txt

echo "[4/6] Extracting benchmark data..."
# Assuming data is provided or download steps are here
# For this script we assume data is in fdb3/v3/fdb_v3_data_released

echo "[5/6] Starting Agent Worker in background..."
export PYTHONIOENCODING="utf-8"
export LK_PROVIDER="gemini2_5"
export HF_HOME="./hf-cache"

python fdb3/v3/prism_agent.py start > logs/agent_repro.log 2>&1 &
AGENT_PID=$!
echo "Agent started with PID $AGENT_PID. Waiting 10 seconds for it to register..."
sleep 10

echo "[6/6] Running Benchmark & Evaluations..."
cd fdb3/v3
python run_tool_benchmark_all_released.py --provider gemini2_5 --root_dir fdb_v3_data_released

echo "Running evaluation scripts..."
python evaluate_pass_rate.py --benchmark benchmark_data_v2.json --results-dir fdb_v3_data_released --provider gemini2_5 --output gemini2_5_pass_rate_report.json
python analyze_tool_latency.py --results-dir fdb_v3_data_released --provider gemini2_5

echo "Stopping Agent Worker..."
kill $AGENT_PID

echo "========================================================="
echo " DONE! Results are saved in fdb3/v3/gemini2_5_pass_rate_report.json"
echo "========================================================="
