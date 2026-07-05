from __future__ import annotations

from datetime import date, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.training import router as training_router, training_service


def build_price_series(count: int = 40):
    start = date(2025, 1, 2)
    rows = []
    for index in range(count):
        close = 10 + index * 0.2
        rows.append(
            {
                "trade_date": (start + timedelta(days=index)).isoformat(),
                "open": round(close - 0.1, 2),
                "high": round(close + 0.2, 2),
                "low": round(close - 0.3, 2),
                "close": round(close, 2),
                "volume": 1000 + index * 50,
                "amount": 10000 + index * 300,
            }
        )
    return rows


training_service._historical_loader = lambda *_args: build_price_series()

app = FastAPI()
app.include_router(training_router)
client = TestClient(app)


def test_create_training_session_and_fetch_step():
    response = client.post(
        "/api/training/sessions",
        json={
            "symbol": "000001",
            "start_date": "2025-01-02",
            "initial_cash": 100000,
            "total_days": 30,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True

    session_id = payload["data"]["session_id"]
    step_response = client.get(f"/api/training/sessions/{session_id}/step")

    assert step_response.status_code == 200
    step_payload = step_response.json()
    assert step_payload["success"] is True
    assert "visible_bars" in step_payload["data"]
    assert step_payload["data"]["current_price"] is not None


def test_submit_action_advance_and_finish_session():
    create_response = client.post(
        "/api/training/sessions",
        json={
            "symbol": "000001",
            "start_date": "2025-01-02",
            "initial_cash": 100000,
            "total_days": 30,
        },
    )
    session_id = create_response.json()["data"]["session_id"]

    action_response = client.post(
        f"/api/training/sessions/{session_id}/actions",
        json={"side": "buy", "quantity": 100, "price": 10.0},
    )
    assert action_response.status_code == 200
    action_payload = action_response.json()
    assert action_payload["success"] is True
    assert action_payload["data"]["positions"][0]["quantity"] == 100
    assert action_payload["data"]["cash"] < 100000

    advance_response = client.post(f"/api/training/sessions/{session_id}/advance")
    assert advance_response.status_code == 200
    assert advance_response.json()["data"]["bar_index"] == 1

    finish_response = client.post(f"/api/training/sessions/{session_id}/finish")
    assert finish_response.status_code == 200
    report_payload = finish_response.json()
    assert report_payload["success"] is True
    assert "buy_and_hold_return" in report_payload["data"]
    assert "excess_return" in report_payload["data"]
    assert "max_drawdown" in report_payload["data"]

    report_response = client.get(f"/api/training/sessions/{session_id}/report")
    assert report_response.status_code == 200
    assert report_response.json()["data"]["session_id"] == session_id
