import os
import sys
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from run_tool_benchmark import load_asr_model, process_single
from run_tool_benchmark_all_released import load_data_released, discover_inputs_released, _PER_FOLDER_DATA

def main():
    root_dir = Path("fdb_v3_data_released")
    
    print("Loading data...")
    try:
        data = load_data_released()
    except:
        data = {}
        
    print("Loading ASR model...")
    asr_model = load_asr_model()
    
    print("Discovering inputs...")
    inputs = discover_inputs_released(root_dir)
    if _PER_FOLDER_DATA:
        data = {**data, **_PER_FOLDER_DATA}
        
    # We will process all 100 concurrently, max 5 at a time
    print(f"Processing {len(inputs)} files concurrently...")
    
    stats = {"total": 0, "success": 0, "error": 0, "skipped": 0}
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for speaker_id, example_id, input_path in inputs:
            # Skip those that were just completed in the last 10 minutes
            res_file = root_dir / f"{example_id}_{speaker_id}" / "result_gemini2_5.json"
            if res_file.exists() and (time.time() - res_file.stat().st_mtime) < 600:
                print(f"Skipping {example_id} - already ran recently.")
                continue
                
            futures.append(executor.submit(
                process_single, speaker_id, example_id, input_path,
                "gemini2_5", data, asr_model, False, True
            ))
            
        for future in as_completed(futures):
            try:
                res = future.result()
                if res is None:
                    stats["skipped"] += 1
                elif res.get("status") == "completed":
                    stats["success"] += 1
                else:
                    stats["error"] += 1
            except Exception as e:
                print(f"Error: {e}")
                stats["error"] += 1
                
            stats["total"] += 1
            print(f"Progress: {stats['total']}/{len(futures)}")
            
    print(f"Done in {time.time() - start_time:.1f}s")
    print(stats)

if __name__ == "__main__":
    main()
