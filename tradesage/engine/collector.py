"""Fetch from every configured source in parallel and turn the results into evidence."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Callable

from ..http import Http
from ..models import Evidence, SourceFailure
from ..sources.macro import Fred
from ..sources.news import Headline, default_feeds
from ..sources.options import CboeOptions, OptionChain
from ..sources.prices import PriceSeries, StooqPrices, YahooPrices
from ..sources.sec import SecEdgar
from . import evidence as E


@dataclass
class Bundle:
    symbol: str
    now: datetime
    company: dict | None = None
    prices: list[PriceSeries] = field(default_factory=list)
    chain: OptionChain | None = None
    evidence: list[Evidence] = field(default_factory=list)
    failures: list[SourceFailure] = field(default_factory=list)
    integrity: tuple[bool, str, float | None] = (False, "not checked", None)

    @property
    def today(self) -> date:
        return self.now.date()


class Collector:
    def __init__(self, http: Http, cfg: dict[str, Any], now: datetime | None = None):
        self.http, self.cfg = http, cfg
        self.now = now or datetime.now(timezone.utc)
        ttl = cfg["cache_ttl_seconds"]
        self.trust = cfg["trust"]
        self.price_feeds = [YahooPrices(http, ttl["prices"]), StooqPrices(http, ttl["prices"])]
        self.cboe = CboeOptions(http, ttl["options"])
        self.fred = Fred(http, ttl["macro"])
        self.edgar = SecEdgar(http, ttl["filings"])
        self.news = default_feeds(http, ttl["news"])
        self._macro_cache: tuple[list[Evidence], list[SourceFailure]] | None = None

    # ------------------------------------------------------------ helpers
    @staticmethod
    def _run(jobs: dict[str, Callable[[], Any]]) -> tuple[dict[str, Any], list[SourceFailure]]:
        results, failures = {}, []
        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = {name: pool.submit(fn) for name, fn in jobs.items()}
            for name, fut in futs.items():
                try:
                    results[name] = fut.result()
                except Exception as exc:  # noqa: BLE001 - any source may fail; we record and continue
                    failures.append(SourceFailure(name, f"{type(exc).__name__}: {exc}"[:200]))
        return results, failures

    def macro(self) -> tuple[list[Evidence], list[SourceFailure]]:
        if self._macro_cache is None:
            jobs: dict[str, Callable[[], Any]] = {f"fred:{s}": (lambda s=s: self.fred.series(s))
                                                  for s in ("VIXCLS", "T10Y2Y", "BAMLH0A0HYM2")}
            jobs["cboe:VIX"] = lambda: self.cboe.index_quote("VIX")
            res, fails = self._run(jobs)
            series = {k.split(":")[1]: v for k, v in res.items() if k.startswith("fred:")}
            ev = E.macro_evidence(series, self.trust["fred"], res.get("cboe:VIX"), self.trust["cboe"], self.now.date())
            self._macro_cache = (ev, fails)
        return self._macro_cache

    def headlines(self, symbol: str, query: str) -> tuple[list[Evidence], list[SourceFailure]]:
        jobs = {f.name: (lambda f=f: f.headlines(symbol, query)) for f in self.news}
        res, fails = self._run(jobs)
        by_feed: dict[str, list[Headline]] = {k: v for k, v in res.items() if v}
        hl = self.cfg["freshness_half_life_hours"]["sentiment"]
        return E.sentiment_evidence(by_feed, self.trust, self.now, hl), fails

    # ------------------------------------------------------------- equity
    def equity_bundle(self, symbol: str, with_options: bool = True) -> Bundle:
        symbol = symbol.upper()
        b = Bundle(symbol, self.now)
        jobs: dict[str, Callable[[], Any]] = {f.name: (lambda f=f: f.history(symbol)) for f in self.price_feeds}
        jobs["sec_edgar"] = lambda: self._sec(symbol)
        if with_options:
            jobs["cboe"] = lambda: self.cboe.chain(symbol)
        res, fails = self._run(jobs)
        b.failures += fails
        b.prices = [res[f.name] for f in self.price_feeds if f.name in res]
        b.chain = res.get("cboe")
        company, facts = res.get("sec_edgar", (None, None))
        b.company = company

        for ps in b.prices:
            t = self.trust.get(ps.source, 0.6)
            b.evidence.append(E.trend_evidence(ps, t))
            b.evidence.append(E.short_term_evidence(ps, t))
        if facts:
            b.evidence += E.fundamentals_evidence(facts, self.trust["sec_edgar"], self.edgar)
        if b.chain:
            b.evidence += E.positioning_evidence(b.chain, self.trust["cboe"], b.today)
            b.evidence += E.volatility_evidence(b.chain, b.prices, self.trust, b.today)

        query = f"{company['title']} stock" if company else f"{symbol} stock"
        news_ev, news_fail = self.headlines(symbol, query)
        macro_ev, macro_fail = self.macro()
        b.evidence += news_ev + macro_ev
        b.failures += news_fail + macro_fail

        di = self.cfg["data_integrity"]
        quotes = [(ps.source, ps.last, ps.as_of) for ps in b.prices]
        if b.chain:
            quotes.append(("cboe", b.chain.spot, b.today))
        b.integrity = E.integrity_check(quotes, di["max_price_spread"], di["max_staleness_days"],
                                        di["min_price_sources"], b.today)
        return b

    def _sec(self, symbol: str):
        company = self.edgar.company(symbol)
        if not company:
            return None, None  # ETFs / foreign listings: no SEC company facts
        return company, self.edgar.facts(int(company["cik_str"]))
