from __future__ import annotations

import math
import statistics
from typing import Sequence


def clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def sma(values: Sequence[float], n: int) -> float | None:
    if len(values) < n:
        return None
    return sum(values[-n:]) / n


def pct_return(values: Sequence[float], n: int, skip: int = 0) -> float | None:
    if len(values) < n + skip + 1:
        return None
    end = values[-1 - skip]
    start = values[-1 - skip - n]
    return end / start - 1.0 if start else None


def rsi(values: Sequence[float], n: int = 14) -> float | None:
    if len(values) < n + 1:
        return None
    gains, losses = 0.0, 0.0
    # Wilder smoothing over the whole series for stability
    diffs = [values[i] - values[i - 1] for i in range(1, len(values))]
    avg_g = sum(max(d, 0) for d in diffs[:n]) / n
    avg_l = sum(max(-d, 0) for d in diffs[:n]) / n
    for d in diffs[n:]:
        gains, losses = max(d, 0), max(-d, 0)
        avg_g = (avg_g * (n - 1) + gains) / n
        avg_l = (avg_l * (n - 1) + losses) / n
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return 100 - 100 / (1 + rs)


def log_returns(values: Sequence[float]) -> list[float]:
    return [math.log(values[i] / values[i - 1]) for i in range(1, len(values)) if values[i - 1] > 0 and values[i] > 0]


def realized_vol(values: Sequence[float], n: int = 30) -> float | None:
    """Annualised close-to-close volatility over the last n returns."""
    r = log_returns(values[-(n + 1):])
    if len(r) < max(5, n // 2):
        return None
    return statistics.pstdev(r) * math.sqrt(252)


def max_drawdown(values: Sequence[float]) -> float:
    peak, mdd = -math.inf, 0.0
    for v in values:
        peak = max(peak, v)
        if peak > 0:
            mdd = min(mdd, v / peak - 1)
    return mdd
