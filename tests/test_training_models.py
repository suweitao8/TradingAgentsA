from app.models.training import TrainingAction, TrainingSessionCreate


def test_training_session_defaults_and_fields():
    payload = TrainingSessionCreate(symbol="000001", start_date="2025-01-02")

    assert payload.symbol == "000001"
    assert payload.start_date == "2025-01-02"
    assert payload.initial_cash == 100000
    assert payload.total_days == 30


def test_training_action_fields():
    action = TrainingAction(side="buy", quantity=100, price=10.5)

    assert action.side == "buy"
    assert action.quantity == 100
    assert action.price == 10.5
