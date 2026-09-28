from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable


SNAPSHOT_FIELDS = [
    "received_at", "monotonic_ns", "data_mode", "market_slug", "market_start", "market_end",
    "market_state", "yes_bid", "yes_ask", "no_bid", "no_ask", "last_trade", "btc_price",
    "price_to_beat", "spread", "passive_pair_cost", "taker_pair_cost", "source_latency_ms",
]

TRADE_FIELDS = [
    "trade_id", "experiment_id", "data_mode", "fill_model", "strategy", "market", "market_start",
    "market_end", "entry_timestamp", "exit_timestamp", "first_side", "first_price", "quantity",
    "opposite_bid_at_entry", "opposite_ask_at_entry", "pair_cost_at_entry", "second_fill_delay_ms",
    "second_price", "exit_type", "exit_reason", "btc_price_entry", "btc_price_exit",
    "spread_at_entry", "time_remaining_ms", "gross_profit", "estimated_fee", "maker_rebate",
    "net_profit", "paper_bankroll", "assumptions",
]


def ensure_layout() -> None:
    for path in (Path("data/raw"), Path("data/normalized"), Path("reports")):
        path.mkdir(parents=True, exist_ok=True)


def append_jsonl(path: str | Path, record: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n")


def append_csv(path: str | Path, row: dict[str, Any], fields: list[str]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    is_new = not target.exists() or target.stat().st_size == 0
    with target.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def read_csv(path: str | Path) -> list[dict[str, str]]:
    target = Path(path)
    if not target.exists() or target.stat().st_size == 0:
        return []
    with target.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: str | Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

