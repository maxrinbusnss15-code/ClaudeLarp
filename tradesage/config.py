"""Source trust levels, question weights and risk settings.

Override any value with a TOML file (``tradesage.toml`` in the working directory,
or the path in ``TRADESAGE_CONFIG``), e.g.::

    [trust]
    yahoo = 0.6

    [risk]
    account_equity = 50000
"""
from __future__ import annotations

import os
import tomllib
from copy import deepcopy
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    # 0..1: how much each source is trusted. Regulators / exchanges / central banks
    # rank highest, commercial aggregators lower, news aggregators lowest.
    "trust": {
        "sec_edgar": 1.0,        # US regulator, primary filings
        "fred": 0.95,            # Federal Reserve Bank of St. Louis
        "cboe": 0.9,             # exchange: options chains, VIX
        "nasdaq": 0.85,          # exchange: IPO calendar
        "stooq": 0.7,            # independent price vendor
        "yahoo": 0.7,            # commercial price vendor
        "yahoo_rss": 0.55,
        "nasdaq_rss": 0.55,
        "google_news": 0.5,      # aggregator, many publishers of varying quality
    },
    # minimum number of DISTINCT sources needed before a question counts as answered
    "quorum": {
        "trend": 2,
        "short_term": 2,
        "fundamentals": 1,       # SEC is the primary authority; 1 is enough
        "sentiment": 2,
        "macro": 2,
        "positioning": 1,
        "volatility": 1,
        "ipo_regulator": 1,
        "ipo_deal": 1,
        "ipo_climate": 2,
        "ipo_aftermarket": 2,
    },
    # weights of each question in the directional score
    "weights": {
        "equity": {
            "trend": 0.30,
            "short_term": 0.10,
            "fundamentals": 0.20,
            "sentiment": 0.15,
            "macro": 0.15,
            "positioning": 0.10,
        },
        "ipo": {
            "ipo_deal": 0.30,
            "ipo_climate": 0.25,
            "macro": 0.20,
            "sentiment": 0.15,
            "ipo_aftermarket": 0.10,
        },
    },
    # questions that MUST be answered or the engine refuses to pick a side
    "required": {
        "equity": ["data_integrity", "trend"],
        "ipo": ["ipo_regulator", "ipo_deal"],
    },
    "data_integrity": {
        "max_price_spread": 0.02,   # independent price feeds must agree within 2 %
        "max_staleness_days": 5,
        "min_price_sources": 2,
    },
    "freshness_half_life_hours": {
        "sentiment": 36,
        "default": 24 * 30,
    },
    "risk": {
        "account_equity": 100_000.0,
        "risk_per_trade": 0.01,      # max 1 % of equity at risk at full conviction
        "neutral_band": 0.10,        # |score| below this => direction-neutral for options
        "target_dte": 35,
        "min_dte": 20,
        "max_dte": 60,
    },
    "cache_ttl_seconds": {
        "prices": 15 * 60,
        "options": 5 * 60,
        "news": 10 * 60,
        "macro": 6 * 3600,
        "filings": 3600,
        "ipo": 3600,
    },
}


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    candidate = path or os.environ.get("TRADESAGE_CONFIG") or "tradesage.toml"
    p = Path(candidate)
    if p.is_file():
        with p.open("rb") as fh:
            return _merge(DEFAULTS, tomllib.load(fh))
    return deepcopy(DEFAULTS)


def home_dir() -> Path:
    d = Path(os.environ.get("TRADESAGE_HOME", Path.home() / ".tradesage"))
    d.mkdir(parents=True, exist_ok=True)
    return d
