#!/bin/bash
set -e

echo "==================================================="
echo " PRISM GenAI 3.0 - Theme 5 Reproducibility Script"
echo "==================================================="

# 1. Environment Verification
echo "[1/4] Checking environment..."
if [ ! -f .env ]; then
    echo "❌ ERROR: .env file missing!"
    echo "Please create a .env file in this directory with:"
    echo "  GEMINI_API_KEY=your_key"
    echo "  LIVEKIT_URL=your_url"
    echo "  LIVEKIT_API_KEY=your_key"
    echo "  LIVEKIT_API_SECRET=your_secret"
    exit 1
fi
echo "✅ .env file found."

# 2. Setup Virtual Environment
echo "[2/4] Setting up Python environment..."
python -m venv .venv-repro
# Handle Windows Git Bash paths vs Linux paths
if [ -d ".venv-repro/Scripts" ]; then
    source .venv-repro/Scripts/activate
else
    source .venv-repro/bin/activate
fi

echo "Installing required packages..."
# Installing livekit and nemo dependencies (as pinned for FDB-v3)
pip install -q "livekit-agents[google]~=1.8.3" livekit~=1.1.18 python-dotenv pydub

# 3. Start the LiveKit Agent Worker
echo "[3/4] Starting the Custom LiveKit Agent Worker..."
export LK_PROVIDER=gemini3_6
export HF_HOME="./hf-cache"
python fdb3/v3/prism_agent.py start &
WORKER_PID=$!

echo "Waiting 10 seconds for worker to initialize and connect to LiveKit cloud..."
sleep 10

# 4. Run Benchmark & Evaluation
echo "[4/4] Executing 100-Example Benchmark..."
# Force flag overwrites previous cached results
python fdb3/v3/run_tool_benchmark_all_released.py --provider gemini3_6 --root_dir fdb3/v3/fdb_v3_data_released --force

echo "Generating Evaluation Reports..."
mkdir -p results
python fdb3/v3/evaluate_tool_calls.py --benchmark fdb3/v3/benchmark_data_v2.json --results-dir fdb3/v3/fdb_v3_data_released --provider gemini3_6 --output results/repro_tool_calls.json
python fdb3/v3/evaluate_pass_rate.py --benchmark fdb3/v3/benchmark_data_v2.json --results-dir fdb3/v3/fdb_v3_data_released --provider gemini3_6 --output results/repro_pass_rate.json
python fdb3/v3/analyze_tool_latency.py --results-dir fdb3/v3/fdb_v3_data_released --provider gemini3_6 > results/repro_latency.txt

echo "==================================================="
echo "✅ Reproduction Complete!"
echo "Results have been saved to the 'results/' directory."
echo "Killing background agent worker (PID: $WORKER_PID)..."
kill $WORKER_PID
