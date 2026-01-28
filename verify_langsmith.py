import asyncio
import os
import sys
from pprint import pprint

# Add the project root to sys.path to import app
sys.path.append(os.getcwd())

from app.services.langsmith_service import LangSmithService

async def verify_langsmith_service():
    print("Testing LangSmithService...")
    service = LangSmithService()
    
    # 1. Test get_stats
    print("\n--- Testing get_stats ---")
    try:
        stats = await service.get_stats()
        pprint(stats)
        if "total_traces" in stats:
            print("[PASS] get_stats successful")
        else:
            print("[FAIL] get_stats failed: missing fields")
    except Exception as e:
        print(f"[FAIL] get_stats failed with error: {e}")

    # 2. Test get_runs
    print("\n--- Testing get_runs ---")
    try:
        runs = await service.get_runs(limit=5)
        if isinstance(runs, list) and len(runs) > 0:
            print(f"[PASS] get_runs successful, returned {len(runs)} runs")
            print("Keys in the first run:")
            print(runs[0].keys())
            print("Latency value in first run:", runs[0].get("latency"))
            print("Start time:", runs[0].get("start_time"))
            print("End time:", runs[0].get("end_time"))
            
            run_id = runs[0]["id"]
            # 3. Test get_run_details for run_id
            print(f"\n--- Testing get_run_details for {run_id} ---")
            details = await service.get_run_details(run_id)
            print("Full Details Keys:", details.keys())
            print("Latency in details:", details.get("latency"))
            print("Start Time in details:", details.get("start_time"))
            print("End Time in details:", details.get("end_time"))
            
            children = details.get("children", [])
            print(f"Children Count: {len(children)}")
            if children:
                print("First Child Latency:", children[0].get("latency"))
            
            print("[PASS] get_run_details successful")
        else:
            print("[FAIL] get_runs failed: result is not a list or empty")
    except Exception as e:
        import traceback
        print(f"[FAIL] get_runs/details failed with error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_langsmith_service())
