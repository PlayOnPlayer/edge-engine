from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from edge_engine.collector import collect
from edge_engine.config import ResearchConfig
from edge_engine.demo import demo_snapshots
from edge_engine.discovery import discover_markets
from edge_engine.models import Snapshot
from edge_engine.paper import PaperEngine
from edge_engine.reporting import record_trades, summarize
from edge_engine.storage import SNAPSHOT_FIELDS, TRADE_FIELDS, ensure_layout, read_csv, write_csv


def _snapshot_from_row(row: dict[str, str]) -> Snapshot:
    optional = lambda key: float(row[key]) if row.get(key) not in (None, "") else None
    return Snapshot(
        received_at=row["received_at"], monotonic_ns=int(row["monotonic_ns"]), data_mode=row["data_mode"],
        market_slug=row["market_slug"], market_start=row["market_start"], market_end=row["market_end"],
        market_state=row["market_state"], yes_bid=float(row["yes_bid"]), yes_ask=float(row["yes_ask"]),
        no_bid=float(row["no_bid"]), no_ask=float(row["no_ask"]), last_trade=optional("last_trade"),
        btc_price=optional("btc_price"), price_to_beat=optional("price_to_beat"), spread=float(row["spread"]),
        passive_pair_cost=float(row["passive_pair_cost"]), taker_pair_cost=float(row["taker_pair_cost"]),
        source_latency_ms=optional("source_latency_ms"),
    )


def run_engine(snapshots: list[Snapshot], config: ResearchConfig, *, replace: bool = False) -> int:
    ensure_layout()
    if replace:
        write_csv("reports/paper_trades.csv", [], TRADE_FIELDS)
    engine = PaperEngine(config)
    count = 0
    for snapshot in snapshots:
        trades = engine.on_snapshot(snapshot)
        record_trades(trades)
        count += len(trades)
    summarize()
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only Polymarket US paper-trading laboratory")
    parser.add_argument("--config", default="config/research.json")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("discover", help="List active and upcoming target markets")
    run = commands.add_parser("run", help="Collect public data and paper trade")
    run.add_argument("--minutes", type=float, default=None)
    run.add_argument("--interval", type=float, default=None)
    run.add_argument("--once", action="store_true")
    replay = commands.add_parser("replay", help="Replay a normalized snapshots CSV")
    replay.add_argument("path", nargs="?", default="data/normalized/snapshots.csv")
    replay.add_argument("--replace", action="store_true")
    commands.add_parser("demo", help="Run an offline deterministic demonstration")
    commands.add_parser("summarize", help="Regenerate summary CSVs")
    args = parser.parse_args()
    config = ResearchConfig.load(args.config)

    if args.command == "discover":
        markets, latency = discover_markets(config)
        payload = {"latency_ms": round(latency, 3), "markets": [m.__dict__ for m in markets]}
        if not markets:
            payload["status"] = "TARGET_NOT_IN_PRODUCTION"
            payload["message"] = (
                "No production BTC 15-minute Up/Down market was found. "
                "The 2026-09-21 Polymarket US changelog lists the family as pre-production."
            )
        print(json.dumps(payload, indent=2))
        return
    if args.command == "demo":
        count = run_engine(demo_snapshots(), config, replace=True)
        print(f"Demo complete: {count} simulated trades written to reports/paper_trades.csv")
        return
    if args.command == "replay":
        snapshots = [_snapshot_from_row(row) for row in read_csv(args.path)]
        count = run_engine(snapshots, config, replace=args.replace)
        print(f"Replay complete: {count} simulated trades")
        return
    if args.command == "summarize":
        comparison, daily = summarize()
        print(f"Wrote {len(comparison)} strategy rows and {len(daily)} daily rows")
        return
    if args.command == "run":
        if args.interval is not None:
            config = ResearchConfig(**{**config.__dict__, "poll_interval_seconds": args.interval})
        engine = PaperEngine(config)
        observed = completed = 0
        try:
            for snapshot in collect(config, minutes=args.minutes, once=args.once):
                observed += 1
                trades = engine.on_snapshot(snapshot)
                record_trades(trades)
                completed += len(trades)
                print(f"{snapshot.received_at} {snapshot.market_slug} YES {snapshot.yes_bid:.3f}/{snapshot.yes_ask:.3f} BTC {snapshot.btc_price or 0:.2f} trades={completed}")
        except RuntimeError as error:
            parser.error(str(error))
        summarize()
        print(f"Collection complete: {observed} snapshots, {completed} simulated trades")
