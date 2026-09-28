from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ResearchConfig:
    experiment_id: str = "E001_REST_BASELINE"
    paper_bankroll: float = 10_000.0
    quantity: int = 25
    poll_interval_seconds: float = 1.0
    market_refresh_seconds: float = 30.0
    request_timeout_seconds: float = 8.0
    fill_model: str = "REALISTIC_TRADE_THROUGH"
    min_locked_profit_per_contract: float = 0.005
    fixed_exit_after_ms: int = 2_500
    smart_exit_after_ms: int = 1_500
    max_forced_hedge_loss_per_contract: float = 0.04
    taker_fee_coefficient: float = 0.0695
    maker_rebate_coefficient: float = 0.0125
    price_tick: float = 0.01
    market_category: str = "crypto"
    asset_symbol: str = "btc"
    market_horizon: str = "15m"

    @classmethod
    def load(cls, path: str | Path = "config/research.json") -> "ResearchConfig":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**payload)

