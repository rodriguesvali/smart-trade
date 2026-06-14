from decimal import Decimal

from smart_trade_backend.application.market_data.ports import HistoricalMarketDataPort
from smart_trade_backend.domain.market_data import Candle, utc_datetime_from_ms


class CcxtUnavailableError(RuntimeError):
    pass


class CcxtPublicMarketDataAdapter(HistoricalMarketDataPort):
    def __init__(self, *, exchange_id: str):
        try:
            import ccxt
        except ImportError as exc:
            raise CcxtUnavailableError(
                "CCXT historical ingestion requires the backend exchange dependency group."
            ) from exc

        try:
            exchange_class = getattr(ccxt, exchange_id)
        except AttributeError as exc:
            raise ValueError(f"Unsupported CCXT exchange: {exchange_id}") from exc

        self.exchange_id = exchange_id
        self.exchange = exchange_class(
            {
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
            }
        )
        self.exchange.load_markets()
        if not self.exchange.has.get("fetchOHLCV"):
            raise ValueError(f"Exchange {exchange_id} does not support fetchOHLCV.")

    def fetch_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        since_ms: int | None,
        limit: int,
    ) -> list[Candle]:
        rows = self.exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=limit)
        candles: list[Candle] = []
        for row in rows:
            timestamp_ms, open_, high, low, close, volume = row[:6]
            candles.append(
                Candle(
                    exchange=self.exchange_id,
                    symbol=symbol,
                    timeframe=timeframe,
                    open_time_ms=int(timestamp_ms),
                    opened_at=utc_datetime_from_ms(int(timestamp_ms)),
                    open=Decimal(str(open_)),
                    high=Decimal(str(high)),
                    low=Decimal(str(low)),
                    close=Decimal(str(close)),
                    volume=Decimal(str(volume)),
                    source="ccxt",
                    is_closed=True,
                    raw_payload=list(row),
                )
            )
        return candles
