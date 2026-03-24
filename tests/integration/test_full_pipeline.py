import pytest
from httpx import AsyncClient, ASGITransport
from main import app

pytestmark = pytest.mark.asyncio

async def test_full_structuring_pipeline():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        data = {"amount_usd": 9800, "transaction_type": "wire", "geography": "offshore", "sender_account_id": "ACC001"}
        resp1 = await ac.post("/submit-transaction", json=data)
        assert resp1.status_code == 200
        case_id = resp1.json()["case_id"]
        
        resp_case = await ac.get(f"/case/{case_id}")
        assert resp_case.status_code == 200
        
        resp2 = await ac.post(f"/case/{case_id}/run-pipeline")
        assert resp2.status_code == 200
        
        resp_case2 = await ac.get(f"/case/{case_id}")
        case = resp_case2.json()
        assert case["risk_assessment"] is not None
        assert case["narrative"] is not None
        assert case["compliance"] is not None
        assert case["audit"] is not None
        
        resp3 = await ac.post(f"/case/{case_id}/approve", params={"analyst_name": "TestAnalyst"})
        assert resp3.status_code == 200
        
        resp_case3 = await ac.get(f"/case/{case_id}")
        assert resp_case3.json()["status"] == "filed"
