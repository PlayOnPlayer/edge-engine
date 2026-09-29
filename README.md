# Edge Engine

Edge Engine is a read-only research system for Polymarket US Bitcoin Up/Down markets. It records public market data alongside Coinbase BTC prices, runs conservative paper-fill models, and exports every simulated trade to CSV and Excel-friendly reports.

It cannot place trades. This repository contains no order-submission code, wallet integration, or trading credentials.

## What V1 does

- Discovers active Polymarket US BTC 15-minute Up/Down markets from typed API fields.
- Polls public Polymarket BBO data and Coinbase BTC trades.
- Stores immutable raw JSONL events with wall-clock and monotonic receive timestamps.
- Normalizes synchronized snapshots to CSV.
- Runs two paper strategies against the same observations:
  - `PAIR_FIXED`: passive pair attempt followed by a fixed-time liquidation.
  - `SMART_EXIT`: passive pair attempt followed by the cheaper of an opposite-side hedge or liquidation.
- Models maker rebates, taker fees, and conservative trade-through fills.
- Writes `reports/paper_trades.csv`, `reports/daily_summary.csv`, and `reports/strategy_comparison.csv`.

## Quick start

Python 3.9 or newer is sufficient. V1 uses only the standard library.

```bash
python3 -m edge_engine demo
python3 -m edge_engine test
python3 -m edge_engine discover
python3 -m edge_engine run --minutes 30
```

The `demo` command is deterministic and offline. It proves the recorder, fill logic, fee model, exits, and reports without contacting any external service. Demo rows are explicitly labeled `DEMO`.

Run the free two-direction test harness with `python3 -m edge_engine test`. It makes one read-only forward production probe, then replays any normalized snapshots already collected. If no snapshots exist, it runs the deterministic demo as an explicitly labeled smoke-test fallback. Results go to `reports/test_run.json`, `reports/test_paper_trades.csv`, `reports/test_strategy_comparison.csv`, and `reports/test_daily_summary.csv`.

The live collector uses public read-only endpoints and no credentials:

- Polymarket US: `https://gateway.polymarket.us/v1/markets`
- Coinbase Exchange: `https://api.exchange.coinbase.com/products/BTC-USD/trades`

## Review the results

Open these files directly in Numbers, Excel, or Google Sheets:

- `reports/edge_engine_review.xlsx` — formatted overview and trade ledger.
- `reports/paper_trades.csv` — one row per completed simulated trade.
- `reports/strategy_comparison.csv` — strategy-level P&L and risk comparison.
- `reports/daily_summary.csv` — daily rollup.

Regenerate the workbook after collecting new data:

```bash
npm run workbook
```

## Current venue status

The Polymarket US changelog still describes the automated BTC 15-minute family as a staged rollout, but the production public API returned one matching typed market during the September 29, 2026 free forward probe. Availability may change while the rollout is in progress, so discovery remains a hard gate and the system still refuses to substitute an unrelated Bitcoin contract.

The offline demo, replay engine, fee model, reports, and workbook are usable now. Live collection becomes usable when the target market appears on the production API, without changing strategy logic.

Source: https://docs.polymarket.us/changelog

## Important interpretation limits

REST polling is suitable for proving the data pipeline, but not for claiming a latency edge. Polymarket US WebSocket market data requires API-key authentication. Until streaming data is enabled, every result is labeled `REST_POLL` and the default fill model requires a strict trade-through rather than assuming a touch fills.

Paper P&L is not live P&L. Queue position, partial fills, network delay, exchange rules, price improvement, settlement behavior, and fee rounding can all make live results worse.

## Commands

```bash
python3 -m edge_engine discover
python3 -m edge_engine run --minutes 60 --interval 1.0
python3 -m edge_engine replay data/normalized/snapshots.csv
python3 -m edge_engine test
python3 -m edge_engine summarize
python3 -m unittest discover -s tests -v
```

Configuration lives in [`config/research.json`](config/research.json). Every output row includes the experiment ID and fill-model assumption.

## Data layout

```text
data/raw/          append-only source events
data/normalized/   replayable synchronized snapshots
reports/           human-readable CSV and XLSX outputs
```

## Sources

- Polymarket US API quickstart: https://docs.polymarket.us/getting-started/quickstart
- Polymarket US crypto market rules: https://docs.polymarket.us/faqs/crypto-faqs
- Polymarket US fee schedule: https://docs.polymarket.us/fees
- Polymarket US changelog and BTC market launch status: https://docs.polymarket.us/changelog
- Coinbase public trades endpoint: https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-trades
