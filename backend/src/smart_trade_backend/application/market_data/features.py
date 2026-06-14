from math import isfinite, log
from statistics import fmean, pstdev

from smart_trade_backend.application.market_data.ports import FeatureCalculatorPort
from smart_trade_backend.domain.market_data import Candle, FeatureRow, FeatureSchema

B3_FEATURE_SCHEMA_ID = "b3-talib-basic-v1"
B3_FEATURE_NAMES = (
    "rsi_14",
    "bb_upper_20_2",
    "bb_middle_20",
    "bb_lower_20_2",
    "return_1",
    "log_return_1",
    "volume_change_1",
    "atr_14",
    "body_pct",
)


class PythonFallbackFeatureCalculator(FeatureCalculatorPort):
    """Deterministic indicator calculator used when TA-Lib is unavailable.

    The production boundary remains the same as the TA-Lib adapter. This fallback keeps tests and
    local API startup independent from native TA-Lib availability.
    """

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
                "calculator": "python-fallback",
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
        rows: list[FeatureRow] = []
        schema = self.feature_schema(timeframe)
        closes = [float(candle.close) for candle in candles]
        highs = [float(candle.high) for candle in candles]
        lows = [float(candle.low) for candle in candles]
        volumes = [float(candle.volume) for candle in candles]

        for index, candle in enumerate(candles):
            values = {
                "rsi_14": _rsi(closes, index, period=14),
                "bb_upper_20_2": _bbands(closes, index, period=20, stddev=2)[0],
                "bb_middle_20": _bbands(closes, index, period=20, stddev=2)[1],
                "bb_lower_20_2": _bbands(closes, index, period=20, stddev=2)[2],
                "return_1": _return_1(closes, index),
                "log_return_1": _log_return_1(closes, index),
                "volume_change_1": _return_1(volumes, index),
                "atr_14": _atr(highs, lows, closes, index, period=14),
                "body_pct": _body_pct(candle),
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


def _return_1(values: list[float], index: int) -> float | None:
    if index == 0 or values[index - 1] == 0:
        return None
    return (values[index] - values[index - 1]) / values[index - 1]


def _log_return_1(values: list[float], index: int) -> float | None:
    if index == 0 or values[index - 1] <= 0 or values[index] <= 0:
        return None
    return log(values[index] / values[index - 1])


def _rsi(closes: list[float], index: int, *, period: int) -> float | None:
    if index < period:
        return None
    gains = []
    losses = []
    for cursor in range(index - period + 1, index + 1):
        delta = closes[cursor] - closes[cursor - 1]
        gains.append(max(delta, 0))
        losses.append(abs(min(delta, 0)))
    average_gain = fmean(gains)
    average_loss = fmean(losses)
    if average_loss == 0:
        return 100.0
    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))


def _bbands(
    closes: list[float], index: int, *, period: int, stddev: float
) -> tuple[float | None, float | None, float | None]:
    if index + 1 < period:
        return None, None, None
    window = closes[index - period + 1 : index + 1]
    middle = fmean(window)
    deviation = pstdev(window)
    return middle + stddev * deviation, middle, middle - stddev * deviation


def _atr(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    index: int,
    *,
    period: int,
) -> float | None:
    if index < period:
        return None
    true_ranges = []
    for cursor in range(index - period + 1, index + 1):
        previous_close = closes[cursor - 1]
        true_ranges.append(
            max(
                highs[cursor] - lows[cursor],
                abs(highs[cursor] - previous_close),
                abs(lows[cursor] - previous_close),
            )
        )
    return fmean(true_ranges)


def _body_pct(candle: Candle) -> float | None:
    high = float(candle.high)
    low = float(candle.low)
    if high == low:
        return None
    return (float(candle.close) - float(candle.open)) / (high - low)
