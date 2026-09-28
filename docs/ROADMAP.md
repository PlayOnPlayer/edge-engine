# Edge Engine research roadmap

## Objective

Determine whether small-scale, execution-first market making in Polymarket US BTC Up/Down markets remains positive after realistic fills, fees, rebates, latency, adverse selection, inventory risk, and pessimistic slippage.

The objective is research evidence, not a simulated equity curve.

## Current status — September 28, 2026

The V1 laboratory is implemented and verified offline:

- typed market discovery
- read-only public endpoint client
- append-only raw event storage
- synchronized normalized snapshots
- strict trade-through paper fills
- current US taker fee and maker rebate formulas
- fixed orphan exit and cheapest-path-to-neutral strategies
- deterministic replay
- CSV summaries and a formatted review workbook

Production collection is intentionally gated. The September 21 Polymarket US changelog says automated 15-minute and 60-minute BTC Up/Down markets are in pre-production and will reach production on a schedule announced in the changelog. A live production query on September 28 returned no markets with the required typed `assetPriceTerms` fields.

## Stage 1 — Production launch watcher

Run `python3 -m edge_engine discover` periodically. Start live recording only after a production market satisfies all typed checks:

- `assetPriceTerms.asset.symbol == btc`
- market type is Up/Down
- horizon is 15 minutes
- window start and end are present
- market state is open or pre-open

Do not identify the market by parsing its slug.

## Stage 2 — Authenticated market-data streaming

Public REST polling proves connectivity but cannot support execution claims. Obtain a Polymarket US API key with the minimum access needed for market data, then add:

- full order-book WebSocket subscription
- trade subscription
- reconnect and sequence-gap handling
- local receive timestamps from a monotonic clock
- raw message persistence before normalization
- staleness alarms

No order-submission permission is needed for this stage.

## Stage 3 — Queue-aware replay

Replace the V1 strict trade-through proxy with three fill tracks:

1. Optimistic: touch may fill.
2. Realistic: displayed volume ahead must trade before our quantity fills.
3. Pessimistic: additional queue and latency penalties.

Track partial fills, cancels, price changes, stale quotes, and fill markouts at 100 ms, 250 ms, 500 ms, 1 s, 2 s, and 5 s.

Reject any strategy that is profitable only under the optimistic track.

## Stage 4 — Establish the baseline

Run the passive pair maker without predictive signals. Measure:

- pair completion rate
- time between legs
- gross pair edge
- maker rebates
- taker exit fees
- orphan rate and loss distribution
- adverse markout
- profit per $1,000 of notional
- capacity at displayed depth

The US venue uses a single instrument with long and short directions. At BBO, selling an existing long and buying the short direction have equivalent gross economics. Any smart-exit improvement must therefore come from depth, queue, partial-fill, margin, or fee effects—not from relabeling the same top-of-book transaction.

## Stage 5 — Settlement-aware fair value

Add the BRTI asset-price feed when licensed and available through the venue API. Model the contract's actual settlement statistic:

- 60 one-second BRTI observations for the opening value
- 60 one-second BRTI observations for the closing value
- ties settle Up

Estimate the remaining average required to flip the outcome during the final minute. Validate the model against official settlement values before using it to quote.

## Stage 6 — Toxic-fill avoidance

Use Coinbase and other permitted external feeds primarily to cancel stale quotes, not to predict settlement direction. Test whether external price movement predicts negative post-fill markout out of sample.

Every experiment receives a new ID and fixed hypothesis. Use training, validation, untouched test, and walk-forward periods.

## Stage 7 — Live-readiness gate

Do not add order submission until all conditions hold:

- at least 10,000 simulated executions
- positive realistic and pessimistic P&L after all fees
- positive results across multiple volatility regimes
- modeled edge remains positive after 20–30% degradation
- no unexplained sequence gaps or stale-book fills
- hard exposure, slippage, loss, and data-staleness limits designed and tested

If these conditions fail, stop or revise the hypothesis. Paper profitability alone is insufficient.

## Primary sources

- https://docs.polymarket.us/changelog
- https://docs.polymarket.us/getting-started/quickstart
- https://docs.polymarket.us/api-reference/websocket/markets
- https://docs.polymarket.us/faqs/crypto-faqs
- https://docs.polymarket.us/fees
- https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-trades

