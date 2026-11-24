"""Black-Scholes pricing, greeks and implied volatility (no external deps)."""
from __future__ import annotations

import math


def norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def _d1_d2(s: float, k: float, t: float, r: float, sigma: float, q: float = 0.0) -> tuple[float, float]:
    vt = sigma * math.sqrt(t)
    d1 = (math.log(s / k) + (r - q + 0.5 * sigma * sigma) * t) / vt
    return d1, d1 - vt


def price(s: float, k: float, t: float, r: float, sigma: float, is_call: bool, q: float = 0.0) -> float:
    if t <= 0 or sigma <= 0:
        return max(0.0, (s - k) if is_call else (k - s))
    d1, d2 = _d1_d2(s, k, t, r, sigma, q)
    if is_call:
        return s * math.exp(-q * t) * norm_cdf(d1) - k * math.exp(-r * t) * norm_cdf(d2)
    return k * math.exp(-r * t) * norm_cdf(-d2) - s * math.exp(-q * t) * norm_cdf(-d1)


def delta(s: float, k: float, t: float, r: float, sigma: float, is_call: bool, q: float = 0.0) -> float:
    if t <= 0 or sigma <= 0:
        itm = s > k if is_call else s < k
        return (1.0 if is_call else -1.0) if itm else 0.0
    d1, _ = _d1_d2(s, k, t, r, sigma, q)
    return math.exp(-q * t) * (norm_cdf(d1) if is_call else norm_cdf(d1) - 1)


def prob_itm(s: float, k: float, t: float, r: float, sigma: float, is_call: bool) -> float:
    """Risk-neutral probability of finishing in the money (N(d2))."""
    if t <= 0 or sigma <= 0:
        return 1.0 if (s > k if is_call else s < k) else 0.0
    _, d2 = _d1_d2(s, k, t, r, sigma)
    return norm_cdf(d2) if is_call else norm_cdf(-d2)


def implied_vol(target: float, s: float, k: float, t: float, r: float, is_call: bool) -> float | None:
    intrinsic = max(0.0, (s - k) if is_call else (k - s))
    if target <= intrinsic or t <= 0:
        return None
    lo, hi = 1e-4, 5.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if price(s, k, t, r, mid, is_call) > target:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)
