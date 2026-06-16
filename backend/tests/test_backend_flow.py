from __future__ import annotations

import os

os.environ["SMART_TRADE_DATA_MODE"] = "synthetic"

from fastapi.testclient import TestClient

from app.main import app


def test_training_and_validation_flow() -> None:
    with TestClient(app) as client:
        strategies = client.get("/api/strategies")
        assert strategies.status_code == 200
        assert len(strategies.json()) == 1
        strategy_id = strategies.json()[0]["id"]

        detail = client.get(f"/api/strategies/{strategy_id}")
        assert detail.status_code == 200
        assert detail.json()["name"] == "RSI Sentiment XGBoost"
        assert "timeframe" not in detail.json()
        assert detail.json()["default_parameters"]["timeframe"] == "M5"

        run_response = client.post(
            f"/api/strategies/{strategy_id}/training-runs",
            json={"timeframe": "M5", "training_rows": 220, "target_n": 8},
        )
        assert run_response.status_code == 200
        run_payload = run_response.json()
        assert run_payload["status"] == "TRAINED"
        assert run_payload["model_id"]
        assert run_payload["requested_parameters"]["timeframe"] == "M5"

        model_id = run_payload["model_id"]
        model_response = client.get(f"/api/models/{model_id}")
        assert model_response.status_code == 200
        assert model_response.json()["status"] == "TRAINED"

        validation_response = client.post(f"/api/models/{model_id}/validate")
        assert validation_response.status_code == 200
        validated_model = validation_response.json()
        assert validated_model["status"] == "VALIDATED"
        assert validated_model["validation_summary"]["ml_metrics"]["row_count"] > 0

        events = client.get("/api/audit-events")
        assert events.status_code == 200
        assert len(events.json()) >= 3


def test_training_rejects_whole_number_percentages() -> None:
    with TestClient(app) as client:
        strategy_id = client.get("/api/strategies").json()[0]["id"]

        response = client.post(
            f"/api/strategies/{strategy_id}/training-runs",
            json={
                "timeframe": "M5",
                "training_rows": 180,
                "target_n": 2,
                "take_profit_pct": 1,
                "stop_loss_pct": 1,
            },
        )

        assert response.status_code == 422
        assert "Input should be less than 1" in response.text
