from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from edge_engine.config import ResearchConfig
from edge_engine.http import get_json
from edge_engine.models import MarketInfo, nested_value


MARKETS_URL = "https://gateway.polymarket.us/v1/markets"


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def market_from_payload(payload: dict[str, Any]) -> MarketInfo:
    terms = payload.get("assetPriceTerms") or {}
    asset = terms.get("asset") or {}
    return MarketInfo(
        slug=_text(payload.get("slug")),
        question=_text(payload.get("question") or payload.get("title")),
        start_at=_text(terms.get("windowStart") or payload.get("startDate")),
        end_at=_text(terms.get("windowEnd") or payload.get("endDate")),
        status=_text(payload.get("status")),
        market_type=_text(terms.get("marketType") or payload.get("marketType")),
        asset_symbol=_text(asset.get("symbol")).lower(),
        horizon=_text(terms.get("horizon")).lower(),
        price_to_beat=nested_value(terms.get("priceToBeat")),
    )


def _parse_time(value: str) -> datetime:
    if not value:
        return datetime.max.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def is_target_market(market: MarketInfo, config: ResearchConfig) -> bool:
    market_type = market.market_type.lower().replace("_", "-")
    horizon = market.horizon.replace(" ", "")
    is_up_down = "up-down" in market_type or "updown" in market_type
    is_15m = horizon in {"15m", "15min", "15minutes"} or "15" in horizon
    return (
        market.asset_symbol == config.asset_symbol.lower()
        and is_up_down
        and (is_15m if config.market_horizon == "15m" else horizon == config.market_horizon)
        and bool(market.slug)
    )


def select_markets(payloads: Iterable[dict[str, Any]], config: ResearchConfig) -> list[MarketInfo]:
    markets = [market_from_payload(item) for item in payloads]
    targets = [market for market in markets if is_target_market(market, config)]
    return sorted(targets, key=lambda market: _parse_time(market.end_at))


def discover_markets(config: ResearchConfig) -> tuple[list[MarketInfo], float]:
    payload, latency_ms = get_json(
        MARKETS_URL,
        params={"categories": config.market_category, "closed": "false", "active": "true", "limit": 200},
        timeout=config.request_timeout_seconds,
    )
    return select_markets(payload.get("markets", []), config), latency_ms

