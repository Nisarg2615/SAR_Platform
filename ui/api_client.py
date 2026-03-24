import httpx
from typing import Optional

BASE_URL = "http://localhost:8000"

def _safe_request(method: str, endpoint: str, **kwargs):
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.request(method, f"{BASE_URL}{endpoint}", **kwargs)
            response.raise_for_status()
            return response.json()
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        print(f"API Error: {e}")
        return None

def submit_transaction(payload: dict) -> Optional[dict]:
    return _safe_request("POST", "/submit-transaction", json=payload)

def get_cases() -> Optional[list]:
    return _safe_request("GET", "/cases")

def get_case(case_id: str) -> Optional[dict]:
    return _safe_request("GET", f"/case/{case_id}")

def run_pipeline(case_id: str) -> Optional[dict]:
    return _safe_request("POST", f"/case/{case_id}/run-pipeline")

def get_pipeline_status(case_id: str) -> Optional[list]:
    return _safe_request("GET", f"/case/{case_id}/pipeline-status")

def generate_narrative(case_id: str) -> Optional[dict]:
    return _safe_request("POST", f"/case/{case_id}/generate-narrative")

def approve_case(case_id: str, analyst_name: str) -> Optional[dict]:
    return _safe_request("POST", f"/case/{case_id}/approve", json={"analyst_name": analyst_name})

def dismiss_case(case_id: str) -> Optional[dict]:
    return _safe_request("POST", f"/case/{case_id}/dismiss")

def get_graph(case_id: str) -> Optional[dict]:
    return _safe_request("GET", f"/case/{case_id}/graph")

def check_health() -> Optional[dict]:
    return _safe_request("GET", "/health")

def simulate_scenario(scenario: str) -> Optional[dict]:
    return _safe_request("POST", f"/demo/simulate/{scenario}")
