from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN


def bankers_round_cents(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN))


def taker_fee(price: float, quantity: int, coefficient: float = 0.0695) -> float:
    raw = coefficient * quantity * price * (1.0 - price)
    return bankers_round_cents(raw)


def maker_rebate(price: float, quantity: int, coefficient: float = 0.0125) -> float:
    raw = coefficient * quantity * price * (1.0 - price)
    return bankers_round_cents(raw)

