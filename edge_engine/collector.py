from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from edge_engine.config import ResearchConfig
from edge_engine.discovery import discover_markets
from edge_engine.http import get_json
from edge_engine.models import MarketInfo, Snapshot, nested_value, utc_now_iso
from edge_engine.storage import SNAPSHOT_FIELDS, append_csv, append_jsonl, ensure_layout


COINBASE_TRADES_URL = "https://api.exchange.coinbase.com/products/BTC-USD/trades"
POLYMARKET_BBO = "https://gateway.polymarket.us/v1/markets/{slug}/bbo"


def _remaining_ms(end_at: str, received_at: str) -> int | None:
    try:
        end = datetime.fromisoformat(end_at.replace("Z", "+00:00"))
        received = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
        return max(0, int((end - received).total_seconds() * 1000))
    except (ValueError, TypeError):
        return None


def parse_snapshot(
    market: MarketInfo,
    market_payload: dict[str, Any],
    btc_payload: Any,
    *,
    received_at: str,
    monotonic_ns: int,
    latency_ms: float,
    data_mode: str = "REST_POLL",
) -> Snapshot:
    data = market_payload.get("marketData", market_payload)
    yes_bid = nested_value(data.get("bestBid"))
    yes_ask = nested_value(data.get("bestAsk"))
    if yes_bid is None or yes_ask is None:
        raise ValueError(f"Missing BBO for {market.slug}")
    if not (0.0 <= yes_bid <= yes_ask <= 1.0):
        raise ValueError(f"Invalid BBO for {market.slug}: {yes_bid}/{yes_ask}")
    btc_price = None
    if isinstance(btc_payload, list) and btc_payload:
        try:
            btc_price = float(btc_payload[0]["price"])
        except (KeyError, TypeError, ValueError):
            pass
    no_bid = round(1.0 - yes_ask, 6)
    no_ask = round(1.0 - yes_bid, 6)
    spread = round(yes_ask - yes_bid, 6)
    return Snapshot(
        received_at=received_at,
        monotonic_ns=monotonic_ns,
        data_mode=data_mode,
        market_slug=market.slug,
        market_start=market.start_at,
        market_end=market.end_at,
        market_state=str(data.get("state", market.status)),
        yes_bid=yes_bid,
        yes_ask=yes_ask,
        no_bid=no_bid,
        no_ask=no_ask,
        last_trade=nested_value(data.get("lastTradePx") or data.get("currentPx")),
        btc_price=btc_price,
        price_to_beat=market.price_to_beat,
        spread=spread,
        passive_pair_cost=round(yes_bid + no_bid, 6),
        taker_pair_cost=round(yes_ask + no_ask, 6),
        source_latency_ms=round(latency_ms, 3),
    )


def fetch_snapshot(market: MarketInfo, config: ResearchConfig) -> Snapshot:
    wall = utc_now_iso()
    mono = time.monotonic_ns()
    market_payload, market_latency = get_json(
        POLYMARKET_BBO.format(slug=market.slug), timeout=config.request_timeout_seconds
    )
    btc_payload, btc_latency = get_json(
        COINBASE_TRADES_URL, params={"limit": 1}, timeout=config.request_timeout_seconds
    )
    append_jsonl("data/raw/events.jsonl", {
        "received_at": wall,
        "monotonic_ns": mono,
        "source": "polymarket_us_bbo",
        "market_slug": market.slug,
        "latency_ms": market_latency,
        "payload": market_payload,
    })
    append_jsonl("data/raw/events.jsonl", {
        "received_at": wall,
        "monotonic_ns": mono,
        "source": "coinbase_btc_usd_trades",
        "latency_ms": btc_latency,
        "payload": btc_payload,
    })
    snapshot = parse_snapshot(
        market, market_payload, btc_payload, received_at=wall, monotonic_ns=mono,
        latency_ms=market_latency + btc_latency,
    )
    append_csv("data/normalized/snapshots.csv", snapshot.to_row(), SNAPSHOT_FIELDS)
    return snapshot


def active_market(markets: list[MarketInfo]) -> MarketInfo | None:
    now = datetime.now(timezone.utc)
    current: list[MarketInfo] = []
    future: list[MarketInfo] = []
    for market in markets:
        try:
            start = datetime.fromisoformat(market.start_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(market.end_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        if start <= now < end:
            current.append(market)
        elif now < end:
            future.append(market)
    return (current or future or [None])[0]


def collect(config: ResearchConfig, *, minutes: float | None, once: bool = False):
    ensure_layout()
    deadline = None if minutes is None else time.monotonic() + minutes * 60
    chosen: MarketInfo | None = None
    last_discovery = 0.0
    while True:
        if chosen is None or time.monotonic() - last_discovery >= config.market_refresh_seconds:
            markets, latency = discover_markets(config)
            append_jsonl("data/raw/events.jsonl", {
                "received_at": utc_now_iso(), "monotonic_ns": time.monotonic_ns(),
                "source": "polymarket_us_discovery", "latency_ms": latency,
                "target_count": len(markets), "markets": [market.__dict__ for market in markets],
            })
            chosen = active_market(markets)
            last_discovery = time.monotonic()
        if chosen is None:
            raise RuntimeError(
                "No production BTC 15-minute Up/Down market is currently available. "
                "Polymarket US documented these markets in pre-production on 2026-09-21; "
                "check https://docs.polymarket.us/changelog for a production launch announcement."
            )
        yield fetch_snapshot(chosen, config)
        if once or (deadline is not None and time.monotonic() >= deadline):
            break
        time.sleep(config.poll_interval_seconds)
