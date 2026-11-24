from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from ..http import Http

_OCC = re.compile(r"^(?P<root>[A-Z.]+?)(?P<y>\d{2})(?P<m>\d{2})(?P<d>\d{2})(?P<cp>[CP])(?P<k>\d{8})$")


@dataclass
class OptionQuote:
    symbol: str
    expiry: date
    is_call: bool
    strike: float
    bid: float
    ask: float
    iv: float | None
    delta: float | None
    open_interest: int
    volume: int

    @property
    def mid(self) -> float:
        if self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2
        return max(self.bid, self.ask)


@dataclass
class OptionChain:
    source: str
    underlying: str
    spot: float
    quotes: list[OptionQuote]
    iv30: float | None = None


def parse_occ(sym: str) -> tuple[date, bool, float] | None:
    m = _OCC.match(sym.replace(" ", ""))
    if not m:
        return None
    exp = date(2000 + int(m["y"]), int(m["m"]), int(m["d"]))
    return exp, m["cp"] == "C", int(m["k"]) / 1000.0


class CboeOptions:
    """CBOE delayed (15 min) quotes, public JSON."""

    name = "cboe"

    def __init__(self, http: Http, ttl: int = 300):
        self.http, self.ttl = http, ttl

    def chain(self, symbol: str) -> OptionChain:
        sym = symbol.upper()
        if sym in {"SPX", "VIX", "NDX", "RUT", "XSP"}:
            sym = "_" + sym
        js = self.http.get_json(f"https://cdn.cboe.com/api/global/delayed_quotes/options/{sym}.json", ttl=self.ttl)
        data = js["data"]
        quotes: list[OptionQuote] = []
        for o in data.get("options", []):
            parsed = parse_occ(o.get("option", ""))
            if not parsed:
                continue
            exp, is_call, k = parsed
            iv = o.get("iv")
            quotes.append(OptionQuote(
                symbol=o["option"], expiry=exp, is_call=is_call, strike=k,
                bid=float(o.get("bid") or 0), ask=float(o.get("ask") or 0),
                iv=float(iv) if iv else None,
                delta=float(o["delta"]) if o.get("delta") not in (None, "") else None,
                open_interest=int(o.get("open_interest") or 0), volume=int(o.get("volume") or 0),
            ))
        spot = float(data.get("current_price") or data.get("close") or 0)
        if not spot or not quotes:
            raise ValueError("CBOE chain empty")
        iv30 = data.get("iv30")
        return OptionChain(self.name, symbol.upper(), spot, quotes, float(iv30) / 100 if iv30 else None)

    def index_quote(self, index: str = "VIX") -> float:
        js = self.http.get_json(f"https://cdn.cboe.com/api/global/delayed_quotes/quotes/_{index}.json", ttl=self.ttl)
        return float(js["data"]["current_price"])
