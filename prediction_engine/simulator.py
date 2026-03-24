"""
prediction_engine/simulator.py
Demo scenario generators for SAR Platform.
Generates raw transaction dictionaries to trigger different AML typologies.
"""

from datetime import datetime, timedelta
import random


def _base_raw_transaction(tx_id="TX001"):
    return {
        "transaction_id": tx_id,
        "amount_usd": 5000.0,
        "timestamp": datetime.now().isoformat(),
        "transaction_type": "wire",
        "channel": "online",
        "geography": "US",
        "sender_account_id": "ACC-SENDER-01",
        "receiver_account_id": "ACC-RECEIVER-01",
        "subject_name": "John Doe",
        "bank_name": "Barclays India",
        "bsr_code": "4001234",
        "branch_name": "Pune Tech Hub"
    }


def get_structuring_scenario() -> dict:
    """
    Structuring Scenario: Multiple same-day deposits just under the $10,000 threshold.
    """
    tx_list = []
    base_time = datetime.now() - timedelta(days=5)
    
    # Generate 4 transactions of $9,800 over 4 days
    for i in range(4):
        tx = _base_raw_transaction(f"TX-STRUCT-{i}")
        tx.update({
            "amount_usd": 9800.00,
            "timestamp": (base_time + timedelta(days=i)).isoformat(),
            "transaction_type": "cash_deposit",
            "channel": "branch",
            "geography": "US",
            "subject_name": "Structuring Subject LLC"
        })
        tx_list.append(tx)
        
    return {
        "scenario_type": "structuring",
        "transactions": tx_list,
        "subject_name": "Structuring Subject LLC"
    }


def get_layering_scenario() -> dict:
    """
    Layering Scenario: High-volume international wires to high-risk geographies.
    """
    tx_list = []
    base_time = datetime.now() - timedelta(days=2)
    
    geos = ["Cayman Islands", "Panama", "Malta"]
    
    for i in range(5):
        tx = _base_raw_transaction(f"TX-LAYER-{i}")
        tx.update({
            "amount_usd": 250000.00,
            "timestamp": (base_time + timedelta(hours=i*2)).isoformat(),
            "transaction_type": "wire",
            "channel": "online",
            "geography": random.choice(geos),
            "subject_name": "Layering Shell Corp"
        })
        tx_list.append(tx)
        
    return {
        "scenario_type": "layering",
        "transactions": tx_list,
        "subject_name": "Layering Shell Corp"
    }


def get_smurfing_scenario() -> dict:
    """
    Smurfing Scenario: Multiple different sender accounts sending small amounts
    to the same receiver very quickly.
    """
    tx_list = []
    base_time = datetime.now() - timedelta(hours=12)
    
    for i in range(10):
        tx = _base_raw_transaction(f"TX-SMURF-{i}")
        tx.update({
            "amount_usd": random.uniform(2000.0, 4500.0),
            "timestamp": (base_time + timedelta(minutes=i*30)).isoformat(),
            "transaction_type": "p2p_transfer",
            "channel": "mobile",
            "sender_account_id": f"ACC-SMURF-SENDER-{i}",
            "receiver_account_id": "ACC-SMURF-TARGET",
            "subject_name": "Target Account Owner"
        })
        tx_list.append(tx)
        
    return {
        "scenario_type": "smurfing",
        "transactions": tx_list,
        "subject_name": "Target Account Owner"
    }
