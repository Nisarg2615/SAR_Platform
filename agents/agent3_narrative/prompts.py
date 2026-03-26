"""
Agent 3 — Narrative Generation
Prompt templates for MiniMax-Text-2.5.
RULE: No prompts in node.py — always import from here.
"""

from __future__ import annotations
from typing import TYPE_CHECKING
import json

if TYPE_CHECKING:
    from agents.shared.schemas import SARCase

SYSTEM_PROMPT = """You are a Principal Officer at an Indian banking company filing a Suspicious Transaction Report (STR) to the Financial Intelligence Unit-India (FIU-IND).

REQUIREMENTS:
- Output your response STRICTLY as a valid JSON object. No markdown, no preamble.
- The JSON must contain the following 8 top-level keys matching the FIU-IND SBA01-04 form:
    "part1_report_details": {"date_of_sending": "YYYY-MM-DD", "is_replacement": false, "date_of_original_report": null}
    "part2_principal_officer": {"bank_name": "...", "bsr_code": "...", "fiu_id": "FIU001", "bank_category": "A", "officer_name": "...", "designation": "PO", "address": "...", "city_town_district": "...", "state_country": "...", "pin_code": "...", "telephone": "...", "email": "..."}
    "part3_reporting_branch": {"branch_name": "...", "bsr_code": "...", "fiu_id": "FIU001", "address": "...", "city_town_district": "...", "state_country": "...", "pin_code": "...", "telephone": "...", "email": "..."}
    "part4_linked_individuals": [{"name": "...", "customer_id": "..."}]
    "part5_linked_entities": []
    "part6_linked_accounts": [{"account_number": "...", "account_holder_name": "..."}]
    "part7_suspicion_details": {"reasons_for_suspicion": ["Value of transaction", "Activity in account"], "grounds_of_suspicion": "WRITE A HIGHLY DETAILED, MULTI-PARAGRAPH EXPLANATION HERE. Break down exactly why the transaction is suspicious, how it maps to known AML typologies, the subject's background, the geographical risk, and chronological sequence of events. Do not use bullet points—use lush, descriptive paragraphs like an official legal filing."}
    "part8_action_taken": {"under_investigation": false, "agency_details": ""}
- Be factual. Use the data provided. Use dummy addresses if not provided.
"""

def build_user_prompt(state: "SARCase") -> str:
    case_id = state.case_id
    
    bank_name = "Mock Bank of India"
    bsr_code = "1234567"
    branch_name = "Main Branch"
    if state.raw_transaction:
        bank_name = state.raw_transaction.get("bank_name", bank_name)
        bsr_code = state.raw_transaction.get("bsr_code", bsr_code)
        branch_name = state.raw_transaction.get("branch_name", branch_name)

    subject_name = "Unknown"
    account_ids = []
    total_amount = 0.0
    date_start = "N/A"
    
    if state.normalized:
        subject_name = state.normalized.subject_name
        account_ids = state.normalized.subject_account_ids
        total_amount = state.normalized.total_amount_usd
        date_start = state.normalized.date_range_start.strftime("%Y-%m-%d")

    risk_score = 0.0
    typology = "Unknown"
    signals_text = "None identified."

    if state.risk_assessment:
        risk_score = state.risk_assessment.risk_score
        typology = state.risk_assessment.matched_typology
        if state.risk_assessment.signals:
            signals_text = ", ".join(s.description for s in state.risk_assessment.signals)

    return f"""Draft the FIU-IND STR JSON for the following case.
CASE ID: {case_id}
BANK: {bank_name} (BSR: {bsr_code})
BRANCH: {branch_name}
SUBJECT NAME: {subject_name}
ACCOUNT ID(S): {", ".join(account_ids)}
TOTAL AMOUNT: ${total_amount:,.2f}
DATE: {date_start}
ML RISK SCORE: {risk_score:.3f}
MATCHED TYPOLOGY: {typology}
RISK SIGNALS DETECTED: {signals_text}

Output the JSON now.
"""
