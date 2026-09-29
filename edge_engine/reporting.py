from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from edge_engine.models import PaperTrade
from edge_engine.storage import TRADE_FIELDS, append_csv, read_csv, write_csv


def record_trades(trades: list[PaperTrade], path: str | Path = "reports/paper_trades.csv") -> None:
    for trade in trades:
        append_csv(path, trade.to_row(), TRADE_FIELDS)


def _float(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, 0) or 0)
    except ValueError:
        return 0.0


def _max_drawdown(profits: list[float]) -> float:
    running = peak = 0.0
    drawdown = 0.0
    for value in profits:
        running += value
        peak = max(peak, running)
        drawdown = min(drawdown, running - peak)
    return drawdown


def summarize(
    path: str | Path = "reports/paper_trades.csv",
    *,
    output_dir: str | Path = "reports",
    output_prefix: str = "",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = read_csv(path)
    by_strategy: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_day: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_strategy[row.get("strategy", "UNKNOWN")].append(row)
        day = row.get("exit_timestamp", "")[:10]
        by_day[(day, row.get("strategy", "UNKNOWN"))].append(row)

    comparison: list[dict[str, Any]] = []
    for strategy, items in sorted(by_strategy.items()):
        profits = [_float(item, "net_profit") for item in items]
        gross = sum(_float(item, "gross_profit") for item in items)
        fees = sum(_float(item, "estimated_fee") for item in items)
        rebates = sum(_float(item, "maker_rebate") for item in items)
        volume = sum(_float(item, "quantity") * (_float(item, "first_price") + _float(item, "second_price")) for item in items)
        pairs = sum(item.get("exit_type") == "MERGE" for item in items)
        orphans = len(items) - pairs
        comparison.append({
            "strategy": strategy, "trades": len(items), "completed_pairs": pairs,
            "pair_completion_pct": pairs / len(items) if items else 0.0,
            "orphans": orphans, "gross_profit": round(gross, 6), "fees": round(fees, 6),
            "maker_rebates": round(rebates, 6), "net_profit": round(sum(profits), 6),
            "max_drawdown": round(_max_drawdown(profits), 6),
            "profit_per_1000_volume": round(sum(profits) / volume * 1000, 6) if volume else 0.0,
            "avg_net_per_trade": round(sum(profits) / len(items), 6) if items else 0.0,
        })

    daily: list[dict[str, Any]] = []
    for (day, strategy), items in sorted(by_day.items()):
        daily.append({
            "date": day, "strategy": strategy, "trades": len(items),
            "net_profit": round(sum(_float(item, "net_profit") for item in items), 6),
            "fees": round(sum(_float(item, "estimated_fee") for item in items), 6),
            "maker_rebates": round(sum(_float(item, "maker_rebate") for item in items), 6),
            "completed_pairs": sum(item.get("exit_type") == "MERGE" for item in items),
            "orphans": sum(item.get("exit_type") != "MERGE" for item in items),
        })

    output_dir = Path(output_dir)
    write_csv(output_dir / f"{output_prefix}strategy_comparison.csv", comparison, [
        "strategy", "trades", "completed_pairs", "pair_completion_pct", "orphans", "gross_profit",
        "fees", "maker_rebates", "net_profit", "max_drawdown", "profit_per_1000_volume", "avg_net_per_trade",
    ])
    write_csv(output_dir / f"{output_prefix}daily_summary.csv", daily, [
        "date", "strategy", "trades", "net_profit", "fees", "maker_rebates", "completed_pairs", "orphans",
    ])
    return comparison, daily
