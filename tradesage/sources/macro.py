from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date

from ..http import Http


@dataclass
class MacroSeries:
    source: str
    series_id: str
    dates: list[date]
    values: list[float]


class Fred:
    """FRED public CSV endpoint (no API key needed)."""

    name = "fred"
    SERIES = {
        "VIXCLS": "CBOE Volatility Index",
        "T10Y2Y": "10y-2y Treasury spread",
        "BAMLH0A0HYM2": "US high-yield option-adjusted spread",
        "DGS10": "10y Treasury yield",
    }

    def __init__(self, http: Http, ttl: int = 6 * 3600):
        self.http, self.ttl = http, ttl

    def series(self, series_id: str) -> MacroSeries:
        text = self.http.get_text(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}", ttl=self.ttl)
        reader = csv.reader(io.StringIO(text))
        next(reader, None)
        dates, vals = [], []
        for row in reader:
            if len(row) < 2 or row[1] in (".", ""):
                continue
            dates.append(date.fromisoformat(row[0]))
            vals.append(float(row[1]))
        if not vals:
            raise ValueError(f"FRED {series_id} empty")
        return MacroSeries(self.name, series_id, dates[-400:], vals[-400:])
