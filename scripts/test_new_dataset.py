import asyncio
import csv
import json
import os
import httpx
from datetime import datetime

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "suspicious-activity-reports-sar.csv")

async def main():
    print(f"\n{'='*60}")
    print(f"  TESTING PARTIAL DATASET PROPERLY")
    print(f"{'='*60}\n")

    transactions = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 3:  # Only test first 3 transactions
                break
            txn = dict(row)
            txn["sender_account_id"] = row.get("subject_id", "Unknown")
            txn["receiver_account_id"] = "External-Unknown"
            txn["amount_usd"] = float(row.get("transaction_amount", 0.0))
            ts = row.get("transaction_date", datetime.now().isoformat())
            if len(ts) == 10:
                ts += "T12:00:00"
            txn["timestamp"] = ts
            txn["geography"] = row.get("subject_address_country", "Unknown")
            transactions.append(txn)

    async with httpx.AsyncClient() as client:
        for idx, txn in enumerate(transactions, start=1):
            txn_id = txn.get("transaction_id", f"txn-{idx}")
            
            # Step 1: Submit transaction
            resp = await client.post(f"{API_BASE}/submit-transaction", json=txn, timeout=30)
            resp.raise_for_status()
            case_id = resp.json().get("case_id")
            
            print(f"[{idx}/3] {txn_id} → Submitted as {case_id}")
            
            # Step 2: Run pipeline
            resp2 = await client.post(f"{API_BASE}/case/{case_id}/run-pipeline", timeout=120)
            resp2.raise_for_status()
            
            # Step 3: Get final state
            resp3 = await client.get(f"{API_BASE}/case/{case_id}", timeout=30)
            resp3.raise_for_status()
            case_data = resp3.json()
            
            tier = (case_data.get("risk_assessment") or {}).get("risk_tier", "unknown")
            score = (case_data.get("risk_assessment") or {}).get("risk_score", 0.0)
            typology = (case_data.get("risk_assessment") or {}).get("matched_typology", "none")
            
            narrative = case_data.get("narrative") or "Missing"
            narr_len = len(narrative)
            compliance = case_data.get("compliance", "Missing")
            
            print(f"      Tier      : {tier.upper()} (Score: {score:.3f})")
            print(f"      Typology  : {typology}")
            print(f"      Narrative : {narr_len} chars generated")
            if compliance != "Missing":
                print(f"      Compliance: {len(compliance.get('flags', []))} flags, Status: {compliance.get('recommendation')}")
            else:
                print(f"      Compliance: Missing")
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())
