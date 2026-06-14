from __future__ import annotations

from decimal import Decimal
from typing import Any

from smart_trade_backend.application.live.execution import (
    ExchangeMarketRules,
    ExchangeOrderResult,
    SpotExchangePort,
)
from smart_trade_backend.config import Settings


class CcxtPrivateExchangeError(RuntimeError):
    pass


class CcxtPrivateSpotExchangeAdapter(SpotExchangePort):
    def __init__(self, *, settings: Settings):
        if settings.exchange != "bybit":
            raise CcxtPrivateExchangeError("B8 live execution supports only Bybit spot.")
        try:
            import ccxt
        except ImportError as exc:
            raise CcxtPrivateExchangeError(
                "CCXT live execution requires the backend exchange dependency group."
            ) from exc

        self._ccxt = ccxt
        self.exchange = ccxt.bybit(
            {
                "apiKey": settings.exchange_api_key,
                "secret": settings.exchange_api_secret,
                "password": settings.exchange_api_password,
                "enableRateLimit": True,
                "options": {
                    "defaultType": "spot",
                    "createMarketBuyOrderRequiresPrice": False,
                },
            }
        )
        self.exchange.load_markets()

    def validate_market(self, symbol: str) -> ExchangeMarketRules:
        try:
            market = self.exchange.market(symbol)
        except Exception as exc:
            raise CcxtPrivateExchangeError(f"Configured symbol is unavailable: {symbol}") from exc

        limits = market.get("limits") or {}
        amount_limits = limits.get("amount") or {}
        cost_limits = limits.get("cost") or {}
        precision = market.get("precision") or {}
        return ExchangeMarketRules(
            symbol=str(market.get("symbol") or symbol),
            base=str(market.get("base") or symbol.split("/")[0]),
            quote=str(market.get("quote") or symbol.split("/")[-1]),
            spot=bool(market.get("spot") or market.get("type") == "spot"),
            active=market.get("active") is not False,
            min_amount=_decimal_or_none(amount_limits.get("min")),
            max_amount=_decimal_or_none(amount_limits.get("max")),
            min_cost=_decimal_or_none(cost_limits.get("min")),
            max_cost=_decimal_or_none(cost_limits.get("max")),
            amount_precision=_int_or_none(precision.get("amount")),
            price_precision=_int_or_none(precision.get("price")),
            taker_fee_rate=_decimal_or_none(market.get("taker")),
        )

    def fetch_balance(self) -> dict[str, Decimal]:
        try:
            balance = self.exchange.fetch_balance()
        except Exception as exc:
            raise CcxtPrivateExchangeError("Unable to fetch live spot balance.") from exc
        free = balance.get("free") or {}
        return {
            str(asset): Decimal(str(amount))
            for asset, amount in free.items()
            if amount is not None
        }

    def create_market_buy_order(
        self, *, symbol: str, quote_amount: Decimal, client_order_id: str
    ) -> ExchangeOrderResult:
        try:
            amount = self.exchange.cost_to_precision(symbol, float(quote_amount))
            response = self.exchange.create_order(
                symbol,
                "market",
                "buy",
                amount,
                None,
                {"clientOrderId": client_order_id},
            )
        except Exception as exc:
            raise CcxtPrivateExchangeError("Bybit spot market buy submission failed.") from exc
        return _order_result(response)

    def create_market_sell_order(
        self, *, symbol: str, base_amount: Decimal, client_order_id: str
    ) -> ExchangeOrderResult:
        try:
            amount = self.exchange.amount_to_precision(symbol, float(base_amount))
            response = self.exchange.create_market_sell_order(
                symbol,
                amount,
                {"clientOrderId": client_order_id},
            )
        except Exception as exc:
            raise CcxtPrivateExchangeError("Bybit spot market sell submission failed.") from exc
        return _order_result(response)


def _order_result(response: dict[str, Any]) -> ExchangeOrderResult:
    fee = response.get("fee") or {}
    return ExchangeOrderResult(
        exchange_order_id=str(response["id"]) if response.get("id") is not None else None,
        status=str(response.get("status") or "open"),
        filled_quantity=_decimal_or_zero(response.get("filled") or response.get("amount")),
        average_price=_decimal_or_none(response.get("average") or response.get("price")),
        fee_amount=_decimal_or_none(fee.get("cost")),
        fee_asset=str(fee["currency"]) if fee.get("currency") else None,
        raw_response=response,
    )


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def _decimal_or_zero(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
