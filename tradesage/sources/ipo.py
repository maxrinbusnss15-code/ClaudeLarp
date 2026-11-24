from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from ..http import Http


def _num(s) -> float | None:
    if s in (None, "", "N/A"):
        return None
    try:
        return float(str(s).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def _date(s) -> date | None:
    if not s:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.strptime(str(s).strip(), fmt).date()
        except ValueError:
            pass
    return None


@dataclass
class IpoDeal:
    status: str                   # "upcoming" | "priced" | "filed"
    company: str
    ticker: str
    exchange: str
    price_low: float | None
    price_high: float | None
    shares: float | None
    deal_size: float | None       # USD
    event_date: date | None       # expected / priced / filed date
    raw: dict = field(default_factory=dict)

    @property
    def mid_price(self) -> float | None:
        if self.price_low and self.price_high:
            return (self.price_low + self.price_high) / 2
        return self.price_low or self.price_high


def _parse_price(s) -> tuple[float | None, float | None]:
    if not s:
        return None, None
    parts = [p for p in str(s).replace("$", "").split("-") if p.strip()]
    vals = [_num(p) for p in parts]
    vals = [v for v in vals if v]
    if not vals:
        return None, None
    return min(vals), max(vals)


class NasdaqIpoCalendar:
    name = "nasdaq"
    HEADERS = {"Accept": "application/json, text/plain, */*", "Origin": "https://www.nasdaq.com", "Referer": "https://www.nasdaq.com/"}

    def __init__(self, http: Http, ttl: int = 3600):
        self.http, self.ttl = http, ttl

    def month(self, year: int, month: int) -> list[IpoDeal]:
        js = self.http.get_json(f"https://api.nasdaq.com/api/ipo/calendar?date={year}-{month:02d}", ttl=self.ttl, headers=self.HEADERS)
        data = js.get("data") or {}
        deals: list[IpoDeal] = []

        def rows(section, *path):
            node = data.get(section) or {}
            for p in path:
                node = (node or {}).get(p) or {}
            return node.get("rows") or [] if isinstance(node, dict) else []

        for r in rows("priced"):
            lo, hi = _parse_price(r.get("proposedSharePrice"))
            deals.append(IpoDeal("priced", r.get("companyName", ""), r.get("proposedTickerSymbol", ""),
                                 r.get("proposedExchange", ""), lo, hi, _num(r.get("sharesOffered")),
                                 _num(r.get("dollarValueOfSharesOffered")), _date(r.get("pricedDate")), r))
        for r in rows("upcoming", "upcomingTable"):
            lo, hi = _parse_price(r.get("proposedSharePrice"))
            deals.append(IpoDeal("upcoming", r.get("companyName", ""), r.get("proposedTickerSymbol", ""),
                                 r.get("proposedExchange", ""), lo, hi, _num(r.get("sharesOffered")),
                                 _num(r.get("dollarValueOfSharesOffered")), _date(r.get("expectedPriceDate")), r))
        for r in rows("filed"):
            deals.append(IpoDeal("filed", r.get("companyName", ""), r.get("proposedTickerSymbol", ""), "",
                                 None, None, None, _num(r.get("dollarValueOfSharesOffered")), _date(r.get("filedDate")), r))
        return deals
