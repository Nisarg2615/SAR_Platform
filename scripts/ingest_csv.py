import asyncio
import csv
import json
import os
import sys
import time
from datetime import datetime
import httpx

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "suspicious-activity-reports-sar.csv")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "batch_results.json")

async def process_transaction(client: httpx.AsyncClient, txn: dict, idx: int, total: int) -> dict | None:
    txn_id = txn.get("transaction_id", f"txn-{idx}")
    try:
        # Step 1: Submit transaction
        resp = await client.post(f"{API_BASE}/submit-transaction", json=txn, timeout=30)
        resp.raise_for_status()
        case_id = resp.json().get("case_id")
        if not case_id:
            return None

        # Step 2: Run pipeline
        resp2 = await client.post(f"{API_BASE}/case/{case_id}/run-pipeline", timeout=120)
        resp2.raise_for_status()

        # Step 3: Get final state
        resp3 = await client.get(f"{API_BASE}/case/{case_id}", timeout=30)
        resp3.raise_for_status()
        case_data = resp3.json()

        tier = (case_data.get("risk_assessment") or {}).get("risk_tier", "unknown")
        print(f"  [{idx:>3}/{total}] {txn_id} → {case_id} | tier={tier.upper():8}")
        return case_data
    except Exception as e:
        print(f"  [{idx:>3}/{total}] {txn_id} → ERROR: {e}")
        return None

async def main():
    print(f"\n{'='*60}")
    print(f"  SAR CSV BATCH INGESTION")
    print(f"  File: {CSV_PATH}")
    print(f"{'='*60}\n")

    # Read CSV
    transactions = []
    try:
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                txn = dict(row)
                txn["sender_account_id"] = row.get("subject_id", "Unknown")
                txn["receiver_account_id"] = "External-Unknown"
                txn["amount_usd"] = float(row.get("transaction_amount", 0.0))
                # Add time part if only date
                ts = row.get("transaction_date", datetime.now().isoformat())
                if len(ts) == 10:
                    ts += "T12:00:00"
                txn["timestamp"] = ts
                txn["geography"] = row.get("subject_address_country", "Unknown")
                transactions.append(txn)
    except FileNotFoundError:
        print("CSV file not found!")
        return

    # To avoid Groq rate limits (30 RPM, approx 7.5 cases/min since each uses 4 calls)
    # We add an 8-second delay after each transaction.
    total = len(transactions)
    print(f"Total transactions to process: {total}")
    print("Warning: Processing sequentially with 8-second delay to evade Rate Limits on Groq free tier.")
    
    results = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r") as f:
                results = json.load(f)
        except Exception:
            pass

    async with httpx.AsyncClient() as client:
        for idx, txn in enumerate(transactions, start=1):
            start = time.time()
            case_data = await process_transaction(client, txn, idx, total)
            if case_data:
                case_id = case_data.get("case_id")
                results[case_id] = case_data
            
                # Save incrementally
                with open(OUTPUT_FILE, "w") as f:
                    json.dump(results, f, indent=2, default=str)
            
            elapsed = time.time() - start
            tier = (case_data.get("risk_assessment") or {}).get("risk_tier", "unknown") if case_data else "unknown"
            
            # Rate limit is only hit if narrative agent (Groq) was triggered
            if tier in ("red", "amber", "critical"):
                wait_time = max(0, 8.5 - elapsed)
                await asyncio.sleep(wait_time)
            else:
                await asyncio.sleep(0.1)

    print("\nBatch CSV ingestion completed.")

if __name__ == "__main__":
    asyncio.run(main())
