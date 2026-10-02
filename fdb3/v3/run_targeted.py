import os
import sys
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from run_tool_benchmark import load_asr_model, process_single
from run_tool_benchmark_all_released import load_data_released, discover_inputs_released, _PER_FOLDER_DATA

def main():
    root_dir = Path("fdb_v3_data_released")
    data = load_data_released()
    asr_model = load_asr_model()
    inputs = discover_inputs_released(root_dir)
    
    # We want to re-run only the specific failed cases from our previous 52 run
    failed_examples = [
        "finance_15", "finance_20", "finance_22", 
        "housing_03", "housing_05", "housing_10",
        "housing_20", "travel_02", "travel_10", "travel_24"
    ]
    
    target_inputs = []
    for speaker_id, example_id, input_path in inputs:
        if example_id in failed_examples:
            target_inputs.append((speaker_id, example_id, input_path))
            
    print(f"Targeting {len(target_inputs)} previously failed samples to verify improvements...")
    
    stats = {"total": 0, "success": 0, "error": 0}
    
    for speaker_id, example_id, input_path in target_inputs:
        print(f"\nProcessing {example_id}...")
        try:
            res = process_single(
                speaker_id, example_id, input_path,
                "gemini2_5", data, asr_model, False, True
            )
            if res and res.get("status") == "completed":
                stats["success"] += 1
            else:
                stats["error"] += 1
        except Exception as e:
            print(f"Error: {e}")
            stats["error"] += 1
            
        stats["total"] += 1
        
    print(f"\nDone re-running {stats['total']} failed samples.")
    print("Now we can re-evaluate these to see if they pass.")

if __name__ == "__main__":
    main()
