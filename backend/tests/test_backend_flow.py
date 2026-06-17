from __future__ import annotations

import os
from pathlib import Path

os.environ["SMART_TRADE_DATA_MODE"] = "synthetic"
os.environ["SMART_TRADE_DATABASE_URL"] = "sqlite:///./var/test_smart_trade.db"
os.environ["SMART_TRADE_ARTIFACT_DIR"] = "./var/test-models"

from fastapi.testclient import TestClient

from smart_trade.adapters.api.schemas import TrainingRequest
from smart_trade.domain.training_window import calculate_training_window
from smart_trade_api.main import app
from smart_trade_training_worker.main import run_once


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
        assert detail.json()["default_parameters"]["training_rows"] == 8545
        assert detail.json()["default_parameters"]["training_window_policy"]["holdout_rows"] == 864

        run_response = client.post(
            f"/api/strategies/{strategy_id}/training-runs",
            json={"timeframe": "H1", "training_rows": 220, "target_n": 8},
        )
        assert run_response.status_code == 202
        run_payload = run_response.json()
        assert run_payload["status"] == "PENDING"
        assert run_payload["model_id"] is None
        assert run_payload["progress_phase"] == "pending"
        assert run_payload["requested_parameters"]["timeframe"] == "H1"
        assert run_payload["requested_parameters"]["training_rows"] == 632
        assert run_payload["requested_parameters"]["training_window_policy"]["holdout_rows"] == 72
        assert run_payload["requested_parameters"]["training_window_policy"]["ignored_request_overrides"]["training_rows"] == 220

        for _ in range(10):
            run_once("test-worker")
            completed_run = client.get(f"/api/training-runs/{run_payload['id']}")
            assert completed_run.status_code == 200
            run_payload = completed_run.json()
            if run_payload["status"] not in {"PENDING", "RUNNING"}:
                break
        assert run_payload["status"] == "TRAINED"
        assert run_payload["model_id"]
        assert run_payload["progress_phase"] == "trained"
        assert run_payload["progress_pct"] == 1.0

        model_id = run_payload["model_id"]
        model_response = client.get(f"/api/models/{model_id}")
        assert model_response.status_code == 200
        assert model_response.json()["status"] == "TRAINED"

        validation_response = client.post(f"/api/models/{model_id}/validate")
        assert validation_response.status_code == 200
        validated_model = validation_response.json()
        assert validated_model["status"] == "VALIDATED"
        assert validated_model["validation_summary"]["ml_metrics"]["row_count"] > 0
        assert "entry_candidates" in validated_model["validation_summary"]["operational_metrics"]
        assert "walk_forward" in validated_model["validation_summary"]["window_metadata"]
        artifact_path = Path(validated_model["artifact_path"])
        dataset_path = artifact_path.with_suffix(".dataset.npz")
        assert artifact_path.exists()
        assert dataset_path.exists()

        delete_validated = client.request(
            "DELETE",
            f"/api/models/{model_id}",
            json={"operator": "test-user", "confirmed": True, "comments": "cleanup attempt"},
        )
        assert delete_validated.status_code == 409

        rejection_response = client.post(
            f"/api/models/{model_id}/reject",
            json={"operator": "test-user", "comments": "Rejected by backend flow test"},
        )
        assert rejection_response.status_code == 200
        assert rejection_response.json()["status"] == "REJECTED"

        delete_response = client.request(
            "DELETE",
            f"/api/models/{model_id}",
            json={"operator": "test-user", "confirmed": True, "comments": "Remove rejected model"},
        )
        assert delete_response.status_code == 200
        deleted_model = delete_response.json()
        assert deleted_model["model_id"] == model_id
        assert deleted_model["previous_status"] == "REJECTED"
        assert deleted_model["status"] == "DELETED_FROM_OPERATIONAL_VIEWS"
        assert deleted_model["artifact_cleanup"]["artifact_deleted"] is True
        assert deleted_model["artifact_cleanup"]["dataset_deleted"] is True
        assert not artifact_path.exists()
        assert not dataset_path.exists()

        missing_model = client.get(f"/api/models/{model_id}")
        assert missing_model.status_code == 404

        strategy_models = client.get(f"/api/strategies/{strategy_id}/models")
        assert strategy_models.status_code == 200
        assert model_id not in {model["id"] for model in strategy_models.json()}

        events = client.get("/api/audit-events")
        assert events.status_code == 200
        assert len(events.json()) >= 3
        assert any(event["event_type"] == "MODEL_DELETED" for event in events.json())


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


def test_training_request_accepts_deprecated_training_rows_override() -> None:
    request = TrainingRequest(training_rows=25_920)

    assert request.training_rows == 25_920


def test_m5_training_window_is_calculated_from_thirty_day_raw_window() -> None:
    policy = calculate_training_window("M5", target_n=15)

    assert policy["raw_window_rows"] == 8640
    assert policy["usable_rows"] == 8545
    assert policy["holdout_rows"] == 864
    assert policy["train_validation_rows"] == 7681
