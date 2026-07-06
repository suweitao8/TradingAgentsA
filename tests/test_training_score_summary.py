import pytest

from app.services.training_service import TrainingService


def _bar(trade_date: str, close: float) -> dict:
    return {
        "trade_date": trade_date,
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": 1000,
    }


def test_build_report_calculates_linear_score_from_excess_return() -> None:
    service = TrainingService()
    report = service.build_report(
        {
            "session_id": "train_test",
            "symbol": "001309",
            "start_date": "2026-05-01",
            "end_date": "2026-05-02",
            "initial_cash": 100000,
            "cash": 90000,
            "final_cash": 90000,
            "total_equity": 90000,
            "realized_pnl": 0,
            "unrealized_pnl": 0,
            "trade_count": 1,
        },
        [],
        [_bar("2026-05-01", 100.0), _bar("2026-05-02", 100.0)],
    )

    assert report["active_return"] == -0.1
    assert report["buy_and_hold_return"] == pytest.approx(-0.0003, rel=1e-6)
    assert report["excess_return"] == pytest.approx(-0.0997, rel=1e-6)
    assert report["score"] == pytest.approx(90.03, rel=1e-6)


def test_session_summary_includes_report_score() -> None:
    report = {
        "active_return": -0.1,
        "buy_and_hold_return": 0.0,
        "excess_return": -0.1,
        "score": 90.0,
    }
    summary = TrainingService._build_session_summary(
        {
            "session_id": "train_test",
            "symbol": "001309",
            "start_date": "2026-05-01",
            "end_date": "2026-05-02",
            "current_step": 2,
            "total_days": 30,
            "initial_cash": 100000,
            "cash": 90000,
            "total_equity": 90000,
            "trade_count": 1,
            "status": "finished",
            "note": "浏览器验证",
            "report": report,
        }
    )

    assert summary.active_return == -0.1
    assert summary.buy_and_hold_return == 0.0
    assert summary.excess_return == -0.1
    assert summary.score == 90.0
