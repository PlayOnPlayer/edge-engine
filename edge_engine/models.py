from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def nested_value(payload: dict[str, Any] | None, default: float | None = None) -> float | None:
    if not payload:
        return default
    value = payload.get("value")
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class MarketInfo:
    slug: str
    question: str
    start_at: str
    end_at: str
    status: str
    market_type: str
    asset_symbol: str
    horizon: str
    price_to_beat: float | None


@dataclass(frozen=True)
class Snapshot:
    received_at: str
    monotonic_ns: int
    data_mode: str
    market_slug: str
    market_start: str
    market_end: str
    market_state: str
    yes_bid: float
    yes_ask: float
    no_bid: float
    no_ask: float
    last_trade: float | None
    btc_price: float | None
    price_to_beat: float | None
    spread: float
    passive_pair_cost: float
    taker_pair_cost: float
    source_latency_ms: float | None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperTrade:
    trade_id: str
    experiment_id: str
    data_mode: str
    fill_model: str
    strategy: str
    market: str
    market_start: str
    market_end: str
    entry_timestamp: str
    exit_timestamp: str
    first_side: str
    first_price: float
    quantity: int
    opposite_bid_at_entry: float
    opposite_ask_at_entry: float
    pair_cost_at_entry: float
    second_fill_delay_ms: int | None
    second_price: float | None
    exit_type: str
    exit_reason: str
    btc_price_entry: float | None
    btc_price_exit: float | None
    spread_at_entry: float
    time_remaining_ms: int | None
    gross_profit: float
    estimated_fee: float
    maker_rebate: float
    net_profit: float
    paper_bankroll: float
    assumptions: str

    def to_row(self) -> dict[str, Any]:
        return asdict(self)

