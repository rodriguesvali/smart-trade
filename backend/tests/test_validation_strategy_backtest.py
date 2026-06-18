from __future__ import annotations

import numpy as np

from smart_trade.adapters.ml.pipeline import (
    DatasetBundle,
    _simulate_strategy_backtest,
    generate_dataset,
    train_xgboost,
    validate_model,
)


def test_strategy_backtest_enforces_single_open_position() -> None:
    dataset = DatasetBundle(
        features=np.array(
            [
                [20.0, 0.0, 1.0, 1.0],
                [20.0, 0.0, 1.0, 1.0],
                [20.0, 0.0, 1.0, 1.0],
                [20.0, 0.0, 1.0, 1.0],
                [20.0, 0.0, 1.0, 1.0],
                [20.0, 0.0, 1.0, 1.0],
            ],
            dtype=float,
        ),
        labels=np.zeros(6, dtype=int),
        future_returns=np.zeros(6, dtype=float),
        close_prices=np.full(9, 100.0, dtype=float),
        high_prices=np.full(9, 100.0, dtype=float),
        low_prices=np.full(9, 100.0, dtype=float),
        split_indices={"train": (0, 2), "validation": (2, 4), "holdout": (4, 6)},
        feature_metadata={"feature_names": ["rsi_14", "open_interest_roc", "long_short_ratio", "taker_buy_sell_ratio"]},
    )

    metrics = _simulate_strategy_backtest(
        dataset=dataset,
        probabilities=np.ones(6, dtype=float),
        start_index=0,
        probability_threshold=0.5,
        target_n=3,
        take_profit_pct=0.01,
        stop_loss_pct=0.01,
        trailing_stop_enabled=True,
        trailing_activation_pct=0.01,
        trailing_distance_pct=0.01,
        entry_rsi_threshold=30.0,
        fee_pct=0.0,
        slippage_pct=0.0,
    )

    assert metrics["signals_generated"] == 6
    assert metrics["entry_candidates"] == 6
    assert metrics["simulated_trades"] == 2
    assert metrics["blocked_by_open_position"] == 4
    assert metrics["exit_reasons"]["time_exit"] == 2


def test_strategy_backtest_uses_high_low_and_treats_same_candle_as_stop_first() -> None:
    dataset = DatasetBundle(
        features=np.array([[20.0, 0.0, 1.0, 1.0]], dtype=float),
        labels=np.zeros(1, dtype=int),
        future_returns=np.zeros(1, dtype=float),
        close_prices=np.array([100.0, 100.0, 100.0], dtype=float),
        high_prices=np.array([100.0, 102.0, 100.0], dtype=float),
        low_prices=np.array([100.0, 98.0, 100.0], dtype=float),
        split_indices={"train": (0, 0), "validation": (0, 0), "holdout": (0, 1)},
        feature_metadata={"feature_names": ["rsi_14", "open_interest_roc", "long_short_ratio", "taker_buy_sell_ratio"]},
    )

    metrics = _simulate_strategy_backtest(
        dataset=dataset,
        probabilities=np.ones(1, dtype=float),
        start_index=0,
        probability_threshold=0.5,
        target_n=2,
        take_profit_pct=0.01,
        stop_loss_pct=0.01,
        trailing_stop_enabled=True,
        trailing_activation_pct=0.01,
        trailing_distance_pct=0.01,
        entry_rsi_threshold=30.0,
        fee_pct=0.0,
        slippage_pct=0.0,
    )

    assert metrics["simulated_trades"] == 1
    assert metrics["net_result"] == -0.01
    assert metrics["exit_reasons"]["stop_loss"] == 1


def test_strategy_backtest_exits_with_trailing_stop_after_favorable_move() -> None:
    dataset = DatasetBundle(
        features=np.array([[20.0, 0.0, 1.0, 1.0]], dtype=float),
        labels=np.zeros(1, dtype=int),
        future_returns=np.zeros(1, dtype=float),
        close_prices=np.array([100.0, 100.8, 100.4], dtype=float),
        high_prices=np.array([100.0, 101.0, 100.5], dtype=float),
        low_prices=np.array([100.0, 100.7, 100.4], dtype=float),
        split_indices={"train": (0, 0), "validation": (0, 0), "holdout": (0, 1)},
        feature_metadata={"feature_names": ["rsi_14", "open_interest_roc", "long_short_ratio", "taker_buy_sell_ratio"]},
    )

    metrics = _simulate_strategy_backtest(
        dataset=dataset,
        probabilities=np.ones(1, dtype=float),
        start_index=0,
        probability_threshold=0.5,
        target_n=2,
        take_profit_pct=0.02,
        stop_loss_pct=0.01,
        trailing_stop_enabled=True,
        trailing_activation_pct=0.005,
        trailing_distance_pct=0.005,
        entry_rsi_threshold=30.0,
        fee_pct=0.0,
        slippage_pct=0.0,
    )

    assert metrics["simulated_trades"] == 1
    assert round(metrics["net_result"], 6) == 0.00495
    assert metrics["exit_reasons"]["trailing_stop"] == 1


def test_validation_includes_walk_forward_evidence(tmp_path) -> None:
    dataset = generate_dataset(
        rows=360,
        target_n=8,
        validation_ratio=0.2,
        holdout_ratio=0.2,
        random_seed=7,
        rsi_oversold_threshold=100.0,
    )
    artifact_path = tmp_path / "model.json"
    parameters = {
        "target_n": 8,
        "take_profit_pct": 0.001,
        "stop_loss_pct": 0.001,
        "trailing_stop_enabled": True,
        "trailing_activation_pct": 0.001,
        "trailing_distance_pct": 0.001,
        "probability_threshold": 0.5,
        "entry_rsi_threshold": 100.0,
        "walk_forward_folds": 3,
        "walk_forward_embargo_rows": 8,
        "global_random_seed": 7,
        "xgboost": {"max_depth": 2, "learning_rate": 0.1, "n_estimators": 20},
    }

    train_xgboost(
        dataset=dataset,
        artifact_path=artifact_path,
        random_seed=7,
        xgboost_params=parameters["xgboost"],
    )
    result = validate_model(
        dataset=dataset,
        artifact_path=artifact_path,
        probability_threshold=0.5,
        parameters=parameters,
    )

    walk_forward = result["window_metadata"]["walk_forward"]
    threshold_analysis = result["window_metadata"]["threshold_analysis"]
    assert result["operational_metrics"]["backtest_rules"] == [
        "closed_candle_features",
        "rsi_entry_gate",
        "model_confirmation",
        "single_open_position",
        "high_low_path_tp_sl",
        "trailing_stop_after_favorable_move",
        "conservative_same_candle_stop_first",
        "round_trip_costs",
    ]
    assert walk_forward["requested_folds"] == 3
    assert walk_forward["embargo_rows"] == 8
    assert walk_forward["completed_folds"] > 0
    assert walk_forward["folds"][0]["train_end_index"] <= walk_forward["folds"][0]["validation_start_index"] - 8
    assert "mean_net_result" in walk_forward["aggregate"]
    assert {row["probability_threshold"] for row in threshold_analysis["thresholds"]} >= {0.7, 0.75}
    assert "recommended_probability_threshold" in threshold_analysis
    assert threshold_analysis["minimum_trades"] == 10
