from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime, timezone

from ..http import Http


@dataclass
class PriceSeries:
    source: str
    symbol: str
    dates: list[date]
    closes: list[float]

    @property
    def last(self) -> float:
        return self.closes[-1]

    @property
    def as_of(self) -> date:
        return self.dates[-1]


class YahooPrices:
    name = "yahoo"

    def __init__(self, http: Http, ttl: int = 900):
        self.http, self.ttl = http, ttl

    def history(self, symbol: str) -> PriceSeries:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=2y&interval=1d"
        js = self.http.get_json(url, ttl=self.ttl)
        res = js["chart"]["result"][0]
        ts = res["timestamp"]
        closes = res["indicators"]["quote"][0]["close"]
        dates, vals = [], []
        for t, c in zip(ts, closes):
            if c is not None:
                dates.append(datetime.fromtimestamp(t, tz=timezone.utc).date())
                vals.append(float(c))
        live = res.get("meta", {}).get("regularMarketPrice")
        if live and dates:
            vals[-1] = float(live)
        if len(vals) < 2:
            raise ValueError("yahoo returned too little history")
        return PriceSeries(self.name, symbol, dates, vals)


class StooqPrices:
    name = "stooq"

    def __init__(self, http: Http, ttl: int = 900):
        self.http, self.ttl = http, ttl

    def history(self, symbol: str) -> PriceSeries:
        sym = symbol.lower().replace(".", "-")
        if "." not in sym and not sym.startswith("^"):
            sym += ".us"
        text = self.http.get_text(f"https://stooq.com/q/d/l/?s={sym}&i=d", ttl=self.ttl)
        rows = list(csv.DictReader(io.StringIO(text)))
        if not rows or "Close" not in rows[0]:
            raise ValueError("stooq returned no data")
        rows = rows[-520:]
        dates = [date.fromisoformat(r["Date"]) for r in rows]
        closes = [float(r["Close"]) for r in rows]
        return PriceSeries(self.name, symbol, dates, closes)
