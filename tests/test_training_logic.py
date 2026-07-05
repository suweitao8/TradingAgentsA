from __future__ import annotations

import asyncio
from datetime import date, timedelta

from app.models.training import TrainingSessionCreate
from app.services.training_service import TrainingService


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


def test_rule_advice_reflects_trend_and_volume():
    service = TrainingService()

    advice = service.generate_rule_advice(
        closes=[10.0, 10.2, 10.5],
        volumes=[1000, 1200, 1500],
        current_index=2,
    )

    assert advice.trend_strength in {"强", "中", "弱"}
    assert advice.volume_change in {"放量", "平量", "缩量"}
    assert advice.reason


def test_training_flow_uses_visible_market_data():
    service = TrainingService(historical_loader=lambda *_args: build_price_series())

    async def _run() -> dict:
        session = await service.create_session(
            TrainingSessionCreate(symbol="000001", start_date="2025-01-02", initial_cash=100000, total_days=30)
        )
        step = await service.get_current_step(session.session_id)
        assert len(step.visible_bars) == 1
        assert step.current_price is not None
        assert step.advice is not None

        updated = await service.submit_action(
            session.session_id,
            {"side": "buy", "quantity": 100, "price": 10.0},
        )
        assert updated.positions[0].quantity == 100
        assert updated.cash < 100000

        next_step = await service.advance_session(session.session_id)
        assert next_step.bar_index == 1

        report = await service.finish_session(session.session_id)
        return report

    report = asyncio.run(_run())
    assert "buy_and_hold_return" in report
    assert "excess_return" in report
    assert "max_drawdown" in report


def test_build_report_contains_hold_benchmark_and_drawdown():
    service = TrainingService()

    report = service.build_report(
        session={
            "session_id": "session-1",
            "symbol": "000001",
            "start_date": "2025-01-02",
            "end_date": "2025-02-14",
            "initial_cash": 100000,
            "final_cash": 98000,
            "final_equity": 102000,
            "realized_pnl": 2000,
            "unrealized_pnl": 0,
            "trade_count": 4,
        },
        trades=[
            {"side": "buy", "quantity": 100, "price": 10.0, "trade_date": "2025-01-03"},
            {"side": "sell", "quantity": 100, "price": 11.0, "trade_date": "2025-01-10"},
        ],
        price_series=[
            {"trade_date": "2025-01-02", "close": 10.0},
            {"trade_date": "2025-01-03", "close": 10.5},
            {"trade_date": "2025-01-04", "close": 11.0},
            {"trade_date": "2025-01-05", "close": 10.8},
        ],
    )

    assert report["session_id"] == "session-1"
    assert "active_return" in report
    assert "buy_and_hold_return" in report
    assert "excess_return" in report
    assert "max_drawdown" in report
    assert report["trade_count"] == 4
