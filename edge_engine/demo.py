from __future__ import annotations

from datetime import datetime, timedelta, timezone

from edge_engine.models import Snapshot


def demo_snapshots() -> list[Snapshot]:
    start = datetime(2026, 9, 28, 16, 0, tzinfo=timezone.utc)
    market_end = (start + timedelta(minutes=15)).isoformat().replace("+00:00", "Z")
    prices = [
        (0, .49, .51, .50, 70_000.0),
        (1, .49, .51, .48, 69_998.0),
        (2, .47, .49, .48, 69_995.0),
        (3, .50, .52, .53, 70_010.0),
        (4, .50, .52, .53, 70_012.0),
        (6, .45, .47, .44, 69_970.0),
        (7, .44, .46, .43, 69_960.0),
        (9, .37, .39, .38, 69_920.0),
        (10, .38, .40, .41, 69_930.0),
    ]
    rows: list[Snapshot] = []
    for seconds, bid, ask, last, btc in prices:
        received = (start + timedelta(seconds=seconds)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        no_bid = round(1 - ask, 6)
        no_ask = round(1 - bid, 6)
        rows.append(Snapshot(
            received_at=received, monotonic_ns=seconds * 1_000_000_000, data_mode="DEMO",
            market_slug="demo-btc-updown-15m", market_start=start.isoformat().replace("+00:00", "Z"),
            market_end=market_end, market_state="MARKET_STATE_OPEN", yes_bid=bid, yes_ask=ask,
            no_bid=no_bid, no_ask=no_ask, last_trade=last, btc_price=btc, price_to_beat=70_000.0,
            spread=round(ask-bid, 6), passive_pair_cost=round(bid+no_bid, 6),
            taker_pair_cost=round(ask+no_ask, 6), source_latency_ms=5.0,
        ))
    return rows

