"""
Batch Pipeline Runner — processes all 160 transactions from the dataset
through the full 6-agent SAR pipeline one at a time.

Usage:
    python scripts/run_batch_pipeline.py

Output:
    data/batch_results.json — all SARCase objects (dict form)
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime

import httpx

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.transactions_dataset import TRANSACTIONS

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "batch_results.json")


async def process_transaction(client: httpx.AsyncClient, txn: dict, idx: int, total: int) -> dict | None:
    """Process a single transaction through the pipeline. Returns final SARCase dict."""
    txn_id = txn["transaction_id"]
    try:
        # Step 1: Submit transaction → get case_id
        resp = await client.post(f"{API_BASE}/submit-transaction", json=txn, timeout=30)
        resp.raise_for_status()
        case_id = resp.json().get("case_id")
        if not case_id:
            print(f"  [{idx}/{total}] {txn_id} — No case_id returned. Skipping.")
            return None

        # Step 2: Run full 6-agent pipeline
        resp2 = await client.post(f"{API_BASE}/case/{case_id}/run-pipeline", timeout=60)
        resp2.raise_for_status()

        # Step 3: Get final state
        resp3 = await client.get(f"{API_BASE}/case/{case_id}", timeout=30)
        resp3.raise_for_status()
        case_data = resp3.json()

        tier = (case_data.get("risk_assessment") or {}).get("risk_tier", "unknown")
        score = (case_data.get("risk_assessment") or {}).get("risk_score", 0.0)
        status = case_data.get("status", "unknown")
        sar_required = tier in ("red", "critical")

        print(f"  [{idx:>3}/{total}] {txn_id} → {case_id} | tier={tier.upper():8} score={score:.3f} | sar={sar_required}")
        return case_data

    except Exception as e:
        print(f"  [{idx:>3}/{total}] {txn_id} → ERROR: {e}")
        return None


async def main():
    print(f"\n{'='*60}")
    print(f"  SAR BATCH PIPELINE RUNNER")
    print(f"  Dataset: {len(TRANSACTIONS)} transactions")
    print(f"  API: {API_BASE}")
    print(f"  Output: {OUTPUT_FILE}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Check API is reachable
    try:
        async with httpx.AsyncClient() as probe:
            r = await probe.get(f"{API_BASE}/health", timeout=5)
            r.raise_for_status()
        print("  ✅ API is reachable\n")
    except Exception as e:
        print(f"  ❌ API not reachable at {API_BASE}: {e}")
        print("  Please start the FastAPI server first: uvicorn main:app --reload --port 8000")
        return

    results: dict[str, dict] = {}
    total = len(TRANSACTIONS)
    sar_required = 0
    dismissed = 0
    errors = 0
    start = time.time()

    async with httpx.AsyncClient() as client:
        for idx, txn in enumerate(TRANSACTIONS, start=1):
            case_data = await process_transaction(client, txn, idx, total)
            if case_data is None:
                errors += 1
                continue
            case_id = case_data.get("case_id", f"UNKNOWN-{idx}")
            results[case_id] = case_data
            tier = (case_data.get("risk_assessment") or {}).get("risk_tier", "green")
            if tier in ("red", "critical"):
                sar_required += 1
            else:
                dismissed += 1
            # Small delay to avoid overwhelming the server
            await asyncio.sleep(0.1)

    # Write results
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2, default=str)

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"  BATCH COMPLETE")
    print(f"  Processed : {total}")
    print(f"  SAR Filed : {sar_required}")
    print(f"  Clean     : {dismissed}")
    print(f"  Errors    : {errors}")
    print(f"  Time      : {elapsed:.1f}s")
    print(f"  Output    : {OUTPUT_FILE}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
