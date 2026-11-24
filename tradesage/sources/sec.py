from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import quote_plus

from ..http import Http

ATOM = "{http://www.w3.org/2005/Atom}"


@dataclass
class Fact:
    start: date | None
    end: date
    value: float
    filed: date
    form: str


@dataclass
class Filing:
    form: str
    company: str
    filed: date
    link: str


class SecEdgar:
    name = "sec_edgar"

    def __init__(self, http: Http, ttl: int = 3600):
        self.http, self.ttl = http, ttl
        self._tickers: dict[str, dict] | None = None

    def company(self, ticker: str) -> dict | None:
        if self._tickers is None:
            js = self.http.get_json("https://www.sec.gov/files/company_tickers.json", ttl=24 * 3600)
            self._tickers = {v["ticker"].upper(): v for v in js.values()}
        return self._tickers.get(ticker.upper())

    def facts(self, cik: int) -> dict:
        return self.http.get_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json", ttl=self.ttl)

    @staticmethod
    def series(facts: dict, concepts: list[str], unit: str = "USD", taxonomy: str = "us-gaap") -> list[Fact]:
        """First concept that has data wins; duplicates keep the latest filing."""
        tx = facts.get("facts", {}).get(taxonomy, {})
        for c in concepts:
            units = tx.get(c, {}).get("units", {}).get(unit)
            if not units:
                continue
            best: dict[tuple, Fact] = {}
            for u in units:
                f = Fact(
                    start=date.fromisoformat(u["start"]) if u.get("start") else None,
                    end=date.fromisoformat(u["end"]),
                    value=float(u["val"]),
                    filed=date.fromisoformat(u["filed"]),
                    form=u.get("form", ""),
                )
                key = (f.start, f.end)
                if key not in best or f.filed > best[key].filed:
                    best[key] = f
            return sorted(best.values(), key=lambda f: f.end)
        return []

    def filings_by_company(self, name: str, form: str) -> list[Filing]:
        url = (
            "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
            f"&company={quote_plus(name)}&type={quote_plus(form)}&dateb=&owner=include&count=40&output=atom"
        )
        return self._parse_atom(self.http.get_text(url, ttl=self.ttl), name)

    def current_filings(self, form: str) -> list[Filing]:
        url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type={quote_plus(form)}&owner=include&count=100&output=atom"
        return self._parse_atom(self.http.get_text(url, ttl=self.ttl), "")

    @staticmethod
    def _parse_atom(text: str, company: str) -> list[Filing]:
        root = ET.fromstring(text)
        feed_company = root.findtext(f"{ATOM}company-info/{ATOM}conformed-name") or company
        out = []
        for e in root.iter(f"{ATOM}entry"):
            title = e.findtext(f"{ATOM}title") or ""
            cat = e.find(f"{ATOM}category")
            form = cat.get("term") if cat is not None else title.split(" - ")[0]
            updated = e.findtext(f"{ATOM}updated") or e.findtext(f"{ATOM}content/{ATOM}filing-date") or ""
            try:
                filed = datetime.fromisoformat(updated.replace("Z", "+00:00")).date()
            except ValueError:
                try:
                    filed = date.fromisoformat(updated[:10])
                except ValueError:
                    continue
            link_el = e.find(f"{ATOM}link")
            name = title.split(" - ", 1)[1].split(" (")[0] if " - " in title else feed_company
            out.append(Filing(form or "", name or feed_company, filed, link_el.get("href") if link_el is not None else ""))
        return out
