from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from edge_engine.config import ResearchConfig
from edge_engine.fees import maker_rebate, taker_fee
from edge_engine.models import PaperTrade, Snapshot


def _millis(start: str, end: str) -> int:
    left = datetime.fromisoformat(start.replace("Z", "+00:00"))
    right = datetime.fromisoformat(end.replace("Z", "+00:00"))
    return max(0, int((right - left).total_seconds() * 1000))


def _time_remaining(end_at: str, now: str) -> int | None:
    try:
        return _millis(now, end_at)
    except ValueError:
        return None


@dataclass
class OpenPaperOrder:
    strategy: str
    side: str
    entry_price: float
    entry_at: str
    entry_btc: float | None
    entry_spread: float
    opposite_bid: float
    opposite_ask: float
    pair_cost_at_entry: float
    entry_rebate: float


class PaperStrategy:
    def __init__(self, name: str, config: ResearchConfig):
        self.name = name
        self.config = config
        self.market_slug: str | None = None
        self.quote_yes: float | None = None
        self.quote_no: float | None = None
        self.previous_last_trade: float | None = None
        self.open_order: OpenPaperOrder | None = None
        self.bankroll = config.paper_bankroll

    def _reset_market(self, snapshot: Snapshot) -> None:
        self.market_slug = snapshot.market_slug
        self.quote_yes = snapshot.yes_bid
        self.quote_no = snapshot.no_bid
        self.previous_last_trade = snapshot.last_trade
        self.open_order = None

    def _strict_fill(self, side: str, snapshot: Snapshot) -> bool:
        if snapshot.last_trade is None or snapshot.last_trade == self.previous_last_trade:
            return False
        if side == "UP":
            assert self.quote_yes is not None
            return snapshot.last_trade < self.quote_yes
        assert self.quote_no is not None
        return snapshot.last_trade > 1.0 - self.quote_no

    def _first_fill(self, snapshot: Snapshot) -> OpenPaperOrder | None:
        up = self._strict_fill("UP", snapshot)
        down = self._strict_fill("DOWN", snapshot)
        if not up and not down:
            return None
        side = "UP" if up else "DOWN"
        price = self.quote_yes if side == "UP" else self.quote_no
        assert price is not None
        opposite_bid = snapshot.no_bid if side == "UP" else snapshot.yes_bid
        opposite_ask = snapshot.no_ask if side == "UP" else snapshot.yes_ask
        return OpenPaperOrder(
            strategy=self.name,
            side=side,
            entry_price=price,
            entry_at=snapshot.received_at,
            entry_btc=snapshot.btc_price,
            entry_spread=snapshot.spread,
            opposite_bid=opposite_bid,
            opposite_ask=opposite_ask,
            pair_cost_at_entry=price + opposite_bid,
            entry_rebate=maker_rebate(price, self.config.quantity, self.config.maker_rebate_coefficient),
        )

    def _opposite_passive_fill(self, snapshot: Snapshot) -> float | None:
        assert self.open_order is not None
        if self.open_order.side == "UP" and self._strict_fill("DOWN", snapshot):
            return self.quote_no
        if self.open_order.side == "DOWN" and self._strict_fill("UP", snapshot):
            return self.quote_yes
        return None

    def _trade(
        self,
        snapshot: Snapshot,
        *,
        exit_type: str,
        exit_reason: str,
        second_price: float | None,
        gross: float,
        fee: float,
        rebate: float,
    ) -> PaperTrade:
        assert self.open_order is not None
        opened = self.open_order
        delay = _millis(opened.entry_at, snapshot.received_at)
        net = gross - fee + rebate
        self.bankroll += net
        trade = PaperTrade(
            trade_id=str(uuid.uuid4()), experiment_id=self.config.experiment_id,
            data_mode=snapshot.data_mode, fill_model=self.config.fill_model, strategy=self.name,
            market=snapshot.market_slug, market_start=snapshot.market_start, market_end=snapshot.market_end,
            entry_timestamp=opened.entry_at, exit_timestamp=snapshot.received_at,
            first_side=opened.side, first_price=opened.entry_price, quantity=self.config.quantity,
            opposite_bid_at_entry=opened.opposite_bid, opposite_ask_at_entry=opened.opposite_ask,
            pair_cost_at_entry=opened.pair_cost_at_entry,
            second_fill_delay_ms=delay if second_price is not None else None, second_price=second_price,
            exit_type=exit_type, exit_reason=exit_reason, btc_price_entry=opened.entry_btc,
            btc_price_exit=snapshot.btc_price, spread_at_entry=opened.entry_spread,
            time_remaining_ms=_time_remaining(snapshot.market_end, snapshot.received_at),
            gross_profit=round(gross, 6), estimated_fee=round(fee, 6), maker_rebate=round(rebate, 6),
            net_profit=round(net, 6), paper_bankroll=round(self.bankroll, 6),
            assumptions="Strict trade-through fill; full quantity; maker entry; quoted fees; no slippage beyond BBO",
        )
        self.open_order = None
        self.quote_yes = snapshot.yes_bid
        self.quote_no = snapshot.no_bid
        return trade

    def on_snapshot(self, snapshot: Snapshot) -> list[PaperTrade]:
        trades: list[PaperTrade] = []
        if snapshot.market_slug != self.market_slug:
            self._reset_market(snapshot)
            return trades
        if self.open_order is None:
            self.open_order = self._first_fill(snapshot)
            self.previous_last_trade = snapshot.last_trade
            return trades

        opened = self.open_order
        passive_second = self._opposite_passive_fill(snapshot)
        if passive_second is not None:
            gross = (1.0 - opened.entry_price - passive_second) * self.config.quantity
            rebate = opened.entry_rebate + maker_rebate(
                passive_second, self.config.quantity, self.config.maker_rebate_coefficient
            )
            trades.append(self._trade(snapshot, exit_type="MERGE", exit_reason="PASSIVE_PAIR_FILLED",
                                      second_price=passive_second, gross=gross, fee=0.0, rebate=rebate))
            self.previous_last_trade = snapshot.last_trade
            return trades

        opposite_ask = snapshot.no_ask if opened.side == "UP" else snapshot.yes_ask
        pair_profit_per_contract = 1.0 - opened.entry_price - opposite_ask
        if pair_profit_per_contract >= self.config.min_locked_profit_per_contract:
            fee = taker_fee(opposite_ask, self.config.quantity, self.config.taker_fee_coefficient)
            gross = pair_profit_per_contract * self.config.quantity
            trades.append(self._trade(snapshot, exit_type="MERGE", exit_reason="PROFITABLE_TAKER_HEDGE",
                                      second_price=opposite_ask, gross=gross, fee=fee,
                                      rebate=opened.entry_rebate))
            self.previous_last_trade = snapshot.last_trade
            return trades

        elapsed = _millis(opened.entry_at, snapshot.received_at)
        timeout = self.config.fixed_exit_after_ms if self.name == "PAIR_FIXED" else self.config.smart_exit_after_ms
        if elapsed >= timeout:
            original_bid = snapshot.yes_bid if opened.side == "UP" else snapshot.no_bid
            liquidation_gross = (original_bid - opened.entry_price) * self.config.quantity
            liquidation_fee = taker_fee(original_bid, self.config.quantity, self.config.taker_fee_coefficient)
            hedge_gross = pair_profit_per_contract * self.config.quantity
            hedge_fee = taker_fee(opposite_ask, self.config.quantity, self.config.taker_fee_coefficient)
            choose_hedge = self.name == "SMART_EXIT" and (
                pair_profit_per_contract >= -self.config.max_forced_hedge_loss_per_contract
                and hedge_gross - hedge_fee >= liquidation_gross - liquidation_fee
            )
            if choose_hedge:
                trades.append(self._trade(snapshot, exit_type="FORCED_HEDGE", exit_reason="CHEAPEST_PATH_TO_NEUTRAL",
                                          second_price=opposite_ask, gross=hedge_gross, fee=hedge_fee,
                                          rebate=opened.entry_rebate))
            else:
                trades.append(self._trade(snapshot, exit_type="TAKER_EXIT", exit_reason="ORPHAN_TIMEOUT",
                                          second_price=None, gross=liquidation_gross, fee=liquidation_fee,
                                          rebate=opened.entry_rebate))
        self.previous_last_trade = snapshot.last_trade
        return trades


class PaperEngine:
    def __init__(self, config: ResearchConfig):
        self.strategies = [PaperStrategy("PAIR_FIXED", config), PaperStrategy("SMART_EXIT", config)]

    def on_snapshot(self, snapshot: Snapshot) -> list[PaperTrade]:
        return [trade for strategy in self.strategies for trade in strategy.on_snapshot(snapshot)]

