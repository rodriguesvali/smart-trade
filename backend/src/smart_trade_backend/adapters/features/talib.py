from math import isfinite, log

from smart_trade_backend.application.market_data.features import (
    B3_FEATURE_NAMES,
    B3_FEATURE_SCHEMA_ID,
)
from smart_trade_backend.application.market_data.ports import FeatureCalculatorPort
from smart_trade_backend.domain.market_data import Candle, FeatureRow, FeatureSchema


class TalibUnavailableError(RuntimeError):
    pass


class TalibFeatureCalculator(FeatureCalculatorPort):
    def feature_schema(self, timeframe: str) -> FeatureSchema:
        return FeatureSchema(
            schema_id=B3_FEATURE_SCHEMA_ID,
            name="b3_basic_features",
            version="1",
            timeframe=timeframe,
            features=B3_FEATURE_NAMES,
            parameters={
                "rsi_period": 14,
                "bbands_period": 20,
                "bbands_stddev": 2,
                "atr_period": 14,
                "calculator": "ta-lib",
            },
        )

    def calculate(
        self,
        *,
        exchange: str,
        symbol: str,
        timeframe: str,
        candles: list[Candle],
    ) -> list[FeatureRow]:
        try:
            import numpy as np
            import talib
        except ImportError as exc:
            raise TalibUnavailableError(
                "TA-Lib feature generation requires the backend training dependency group."
            ) from exc

        schema = self.feature_schema(timeframe)
        close = np.array([float(candle.close) for candle in candles], dtype=float)
        high = np.array([float(candle.high) for candle in candles], dtype=float)
        low = np.array([float(candle.low) for candle in candles], dtype=float)
        volume = np.array([float(candle.volume) for candle in candles], dtype=float)
        open_ = np.array([float(candle.open) for candle in candles], dtype=float)

        rsi = talib.RSI(close, timeperiod=14)
        bb_upper, bb_middle, bb_lower = talib.BBANDS(
            close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
        )
        atr = talib.ATR(high, low, close, timeperiod=14)

        rows: list[FeatureRow] = []
        for index, candle in enumerate(candles):
            previous_close = close[index - 1] if index > 0 else np.nan
            previous_volume = volume[index - 1] if index > 0 else np.nan
            candle_range = high[index] - low[index]
            values = {
                "rsi_14": _to_float(rsi[index]),
                "bb_upper_20_2": _to_float(bb_upper[index]),
                "bb_middle_20": _to_float(bb_middle[index]),
                "bb_lower_20_2": _to_float(bb_lower[index]),
                "return_1": _ratio_change(close[index], previous_close),
                "log_return_1": _log_ratio(close[index], previous_close),
                "volume_change_1": _ratio_change(volume[index], previous_volume),
                "atr_14": _to_float(atr[index]),
                "body_pct": _to_float((close[index] - open_[index]) / candle_range)
                if candle_range != 0
                else None,
            }
            if all(value is not None and isfinite(value) for value in values.values()):
                rows.append(
                    FeatureRow(
                        exchange=exchange,
                        symbol=symbol,
                        timeframe=timeframe,
                        feature_schema_id=schema.schema_id,
                        open_time_ms=candle.open_time_ms,
                        candle_opened_at=candle.opened_at,
                        values={key: round(value, 12) for key, value in values.items()},
                    )
                )
        return rows


def _to_float(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(result):
        return None
    return result


def _ratio_change(current: float, previous: float) -> float | None:
    if not isfinite(current) or not isfinite(previous) or previous == 0:
        return None
    return (current - previous) / previous


def _log_ratio(current: float, previous: float) -> float | None:
    if not isfinite(current) or not isfinite(previous) or current <= 0 or previous <= 0:
        return None
    return log(current / previous)
