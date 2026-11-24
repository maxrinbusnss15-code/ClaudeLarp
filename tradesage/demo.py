"""Synthetic, deterministic stand-in for every remote source.

Used by ``--demo`` (to see the full pipeline without network access) and by the tests.
All companies and tickers in the IPO calendar are fictional. NOTHING here is market data.
"""
from __future__ import annotations

import calendar
import hashlib
import json
import math
import random
import re
from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime
from typing import Any
from urllib.parse import parse_qs, unquote_plus, urlparse

from .analytics.blackscholes import delta as bs_delta
from .analytics.blackscholes import price as bs_price

DEMO_EQUITIES = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "GOOGL", "SPY", "QQQ", "DEMO"]

# fictional IPO pipeline: (ticker, company, exchange, low, high, shares_m, status, day_offset, drift)
DEMO_IPOS = [
    ("AURR", "Aurora Robotics Inc.", "NASDAQ Global Select", 18, 20, 25, "upcoming", 6, 0.0),
    ("BLMC", "Bluemarch Capital Corp", "NASDAQ Capital", 4, 5, 2, "upcoming", 9, 0.0),
    ("CIRQ", "Cirqit Semiconductor Ltd", "NYSE", 24, 27, 30, "upcoming", 13, 0.0),
    ("DWNL", "Downline Health Holdings", "NASDAQ Global", 14, 16, 8, "priced", -12, 0.25),
    ("EVRG", "Evergrid Energy Inc.", "NYSE", 21, 23, 40, "priced", -35, 0.18),
    ("FLXO", "Flexo Logistics Corp", "NASDAQ Global Select", 11, 13, 15, "priced", -52, -0.12),
    ("GRVT", "Gravitas Biotech Inc.", "NASDAQ Global", 16, 18, 6, "priced", -70, 0.05),
    ("HELX", "Helix Payments Inc.", "NYSE", 30, 33, 20, "priced", -88, 0.31),
    ("IONQX", "Ionic Quarry Mining Ltd", "NYSE American", 6, 7, 3, "priced", -105, -0.35),
    ("JOLT", "Jolt Mobility Inc.", "NASDAQ Global Select", 19, 21, 18, "priced", -165, 0.08),
]


def _rng(*key: Any) -> random.Random:
    return random.Random(int(hashlib.sha256(repr(key).encode()).hexdigest()[:12], 16))


def _bdays(end: date, n: int) -> list[date]:
    out, d = [], end
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= timedelta(days=1)
    return out[::-1]


class DemoHttp:
    def __init__(self, today: date | None = None, scenario: str = "mixed"):
        self.today = today or datetime.now(timezone.utc).date()
        self.scenario = scenario
        self.calls: list[str] = []

    # ----------------------------------------------------------- dispatch
    def get_json(self, url: str, ttl: int = 0, headers: dict | None = None) -> Any:
        return json.loads(self.get_text(url, ttl, headers))

    def get_text(self, url: str, ttl: int = 0, headers: dict | None = None) -> str:
        self.calls.append(url)
        u = urlparse(url)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if "finance.yahoo.com/v8" in url:
            return json.dumps(self._yahoo(u.path.rsplit("/", 1)[-1]))
        if "stooq.com" in url:
            return self._stooq(q["s"].split(".")[0].upper())
        if "cboe.com" in url and "/options/" in url:
            return json.dumps(self._chain(u.path.rsplit("/", 1)[-1].replace(".json", "").lstrip("_")))
        if "cboe.com" in url and "/quotes/" in url:
            return json.dumps({"data": {"current_price": self._fred_vals("VIXCLS")[-1] * 1.01}})
        if "fred.stlouisfed.org" in url:
            return self._fred(q["id"])
        if "company_tickers.json" in url:
            syms = DEMO_EQUITIES + [t[0] for t in DEMO_IPOS]
            return json.dumps({str(i): {"cik_str": 1000 + i, "ticker": s, "title": f"{s} Demo Holdings Inc."}
                               for i, s in enumerate(syms)})
        if "companyfacts" in url:
            cik = int(re.search(r"CIK(\d+)", url).group(1))
            return json.dumps(self._facts(cik))
        if "browse-edgar" in url:
            return self._edgar(q.get("company", ""), q.get("type", ""))
        if "api.nasdaq.com/api/ipo" in url:
            return json.dumps(self._ipo_month(q["date"]))
        if "rss" in url or "news.google" in url:
            sym = q.get("s") or q.get("symbol") or unquote_plus(q.get("q", "X")).split()[0].strip('"')
            return self._rss(urlparse(url).netloc, sym.upper())
        raise RuntimeError(f"demo has no data for {url}")

    # ----------------------------------------------------------- prices
    def _path(self, sym: str) -> tuple[list[date], list[float]]:
        ipo = next((t for t in DEMO_IPOS if t[0] == sym), None)
        if ipo:
            start = self.today + timedelta(days=ipo[7])
            n = max(2, sum(1 for i in range((self.today - start).days + 1)
                           if (start + timedelta(days=i)).weekday() < 5))
            drift_total, p0 = ipo[8], (ipo[3] + ipo[4]) / 2
        else:
            n, p0 = 504, 50 + _rng(sym).random() * 400
            drift_total = {"bull": 0.9, "bear": -0.5}.get(self.scenario, _rng(sym, "d").uniform(-0.4, 0.7))
        r = _rng(sym, "path", self.scenario)
        vol = (0.28 if self.scenario == "mixed" else 0.16) / math.sqrt(252)
        mu = math.log(1 + drift_total) / n
        dates = _bdays(self.today, n)
        px, vals = p0, []
        for _ in dates:
            px *= math.exp(mu + r.gauss(0, vol))
            vals.append(round(px, 4))
        return dates, vals

    def _yahoo(self, sym: str) -> dict:
        dates, vals = self._path(sym)
        ts = [int(datetime(d.year, d.month, d.day, 20, tzinfo=timezone.utc).timestamp()) for d in dates]
        return {"chart": {"result": [{"meta": {"regularMarketPrice": vals[-1]}, "timestamp": ts,
                                      "indicators": {"quote": [{"close": vals}]}}]}}

    def _stooq(self, sym: str) -> str:
        dates, vals = self._path(sym)
        r = _rng(sym, "stooq")
        lines = ["Date,Open,High,Low,Close,Volume"]
        for d, v in zip(dates, vals):
            c = v * (1 + r.uniform(-0.002, 0.002))  # independent vendor, slightly different prints
            lines.append(f"{d},{c:.4f},{c:.4f},{c:.4f},{c:.4f},1000000")
        return "\n".join(lines)

    def _chain(self, sym: str) -> dict:
        _, vals = self._path(sym)
        spot = vals[-1]
        r = _rng(sym, "chain")
        lr = [math.log(vals[i] / vals[i - 1]) for i in range(len(vals) - 30, len(vals))]
        m = sum(lr) / len(lr)
        rv = math.sqrt(sum((x - m) ** 2 for x in lr) / len(lr) * 252)
        iv_mult = {"bull": 0.85, "bear": 1.5}.get(self.scenario, r.uniform(0.8, 1.5))
        base_iv = rv * iv_mult
        fridays = [self.today + timedelta(days=i) for i in range(7, 100) if (self.today + timedelta(days=i)).weekday() == 4]
        exps = fridays[::2][:6]
        step = max(0.5, round(spot * 0.025 / 0.5) * 0.5)
        strikes = [round((spot // step) * step + i * step, 2) for i in range(-12, 13)]
        opts = []
        for e in exps:
            t = (e - self.today).days / 365
            for k in strikes:
                if k <= 0:
                    continue
                for cp in "CP":
                    mny = math.log(k / spot)
                    iv = max(0.05, base_iv + (-0.25 * mny if cp == "P" or mny < 0 else -0.1 * mny))
                    p = bs_price(spot, k, t, 0.04, iv, cp == "C")
                    spr = max(0.01, p * 0.04)
                    oi = int(r.uniform(50, 5000) * math.exp(-abs(mny) * 5))
                    vol = int(oi * r.uniform(0.05, 0.4) * (1.3 if cp == "P" and self.scenario == "bear" else 1))
                    opts.append({
                        "option": f"{sym}{e:%y%m%d}{cp}{int(round(k * 1000)):08d}",
                        "bid": round(max(0.0, p - spr), 2), "ask": round(p + spr, 2), "iv": round(iv, 4),
                        "delta": round(bs_delta(spot, k, t, 0.04, iv, cp == "C"), 4),
                        "open_interest": oi, "volume": vol,
                    })
        return {"data": {"symbol": sym, "current_price": round(spot * 1.0005, 2), "iv30": round(base_iv * 100, 2),
                         "options": opts}}

    # ------------------------------------------------------------ macro
    def _fred_vals(self, sid: str) -> list[float]:
        r = _rng(sid, self.scenario)
        base = {"VIXCLS": {"bull": 13.5, "bear": 29.0}.get(self.scenario, 17.0), "T10Y2Y": 0.45,
                "BAMLH0A0HYM2": {"bear": 5.2}.get(self.scenario, 3.1), "DGS10": 4.2}[sid]
        vals, v = [], base
        for _ in range(300):
            v = v + (base - v) * 0.05 + r.gauss(0, base * 0.02)
            vals.append(round(v, 2))
        return vals

    def _fred(self, sid: str) -> str:
        vals = self._fred_vals(sid)
        dates = _bdays(self.today - timedelta(days=1), len(vals))
        return "observation_date," + sid + "\n" + "\n".join(f"{d},{v}" for d, v in zip(dates, vals))

    # ------------------------------------------------------- fundamentals
    def _facts(self, cik: int) -> dict:
        r = _rng(cik, self.scenario)
        g = {"bull": 0.18, "bear": -0.08}.get(self.scenario, r.uniform(-0.05, 0.25))
        margin = {"bull": 0.22, "bear": -0.03}.get(self.scenario, r.uniform(0.02, 0.25))
        rev, ni, shares = [], [], []
        y, q = self.today.year, (self.today.month - 1) // 3
        q_ends = []
        for _ in range(9):
            q -= 1
            if q < 0:
                q, y = q + 4, y - 1
            mo = q * 3 + 3
            q_ends.append(date(y, mo, calendar.monthrange(y, mo)[1]))
        q_ends.reverse()
        base = 1e9 * (1 + r.random() * 20)
        for i, e in enumerate(q_ends):
            start = date(e.year, e.month - 2, 1)
            filed = min(e + timedelta(days=35), self.today - timedelta(days=1))
            v = base * (1 + g) ** (i / 4)
            m = margin - (0.02 if self.scenario == "bear" else -0.01) * (i - 8) / 8
            rev.append({"start": start.isoformat(), "end": e.isoformat(), "val": v, "filed": filed.isoformat(), "form": "10-Q"})
            ni.append({"start": start.isoformat(), "end": e.isoformat(), "val": v * m, "filed": filed.isoformat(), "form": "10-Q"})
            shares.append({"end": filed.isoformat(), "val": 1e9 * (1 - 0.01 * i / 4), "filed": filed.isoformat(), "form": "10-Q"})
        return {"facts": {"us-gaap": {"Revenues": {"units": {"USD": rev}}, "NetIncomeLoss": {"units": {"USD": ni}}},
                          "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": shares}}}}}

    # --------------------------------------------------------------- news
    POS = ["{s} beats estimates as revenue surges", "Analysts upgrade {s}, cite strong growth",
           "{s} shares climb after record quarter", "{s} announces buyback, raises dividend"]
    NEG = ["{s} shares fall after guidance cut", "{s} faces probe over accounting concerns",
           "Analyst downgrades {s} on weak demand", "{s} misses estimates, warns on margins"]
    NEU = ["What to watch for {s} this week", "{s} CEO to speak at industry conference", "{s} stock: key levels"]

    def _rss(self, host: str, sym: str) -> str:
        r = _rng(sym, host, self.scenario)
        bias = {"bull": 0.7, "bear": 0.25}.get(self.scenario, _rng(sym, "bias").uniform(0.3, 0.7))
        now = datetime.combine(self.today, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=15)
        items = []
        for i in range(8):
            x = r.random()
            pool = self.NEU if x < 0.3 else self.POS if r.random() < bias else self.NEG
            title = r.choice(pool).format(s=sym)
            when = now - timedelta(hours=r.uniform(1, 24 * 6))
            items.append(f"<item><title>{title} - DemoWire</title><pubDate>{format_datetime(when)}</pubDate>"
                         f"<link>https://example.invalid/{sym}/{i}</link></item>")
        return f"<?xml version='1.0'?><rss><channel><title>{host}</title>{''.join(items)}</channel></rss>"

    # ---------------------------------------------------------------- IPO
    def _ipo_month(self, ym: str) -> dict:
        y, m = map(int, ym.split("-"))
        priced, upcoming = [], []
        for t, name, ex, lo, hi, sh, status, off, drift in DEMO_IPOS:
            d = self.today + timedelta(days=off)
            if (d.year, d.month) != (y, m):
                continue
            row = {"proposedTickerSymbol": t, "companyName": name, "proposedExchange": ex,
                   "sharesOffered": f"{sh * 1_000_000:,}", "dollarValueOfSharesOffered": f"${sh * 1e6 * (lo + hi) / 2:,.0f}"}
            if status == "priced":
                final = hi + 1 if drift > 0.2 else lo - 1 if drift < -0.2 else (lo + hi) / 2
                priced.append({**row, "proposedSharePrice": f"{final:.2f}", "pricedDate": d.strftime("%m/%d/%Y")})
            else:
                upcoming.append({**row, "proposedSharePrice": f"{lo:.2f}-{hi:.2f}", "expectedPriceDate": d.strftime("%m/%d/%Y")})
        return {"data": {"priced": {"rows": priced}, "upcoming": {"upcomingTable": {"rows": upcoming}}, "filed": {"rows": []}}}

    def _edgar(self, company: str, form: str) -> str:
        match = next((t for t in DEMO_IPOS if t[1].lower().startswith(company.lower().split()[0])), None) if company else None
        entries = []
        if match and form in ("S-1", "424B4"):
            t, name, *_ , status, off, _d = match
            if form == "424B4" and status != "priced":
                match = None
            else:
                forms = ["424B4"] if form == "424B4" else ["S-1", "S-1/A", "S-1/A"]
                for i, f in enumerate(forms):
                    d = self.today + timedelta(days=off - 60 + i * 20) if f != "424B4" else self.today + timedelta(days=off + 1)
                    entries.append(f"<entry><title>{f} - {name}</title><category term='{f}'/>"
                                   f"<updated>{d.isoformat()}T12:00:00-04:00</updated>"
                                   f"<link href='https://example.invalid/edgar/{t}/{i}'/></entry>")
        return ("<?xml version='1.0'?><feed xmlns='http://www.w3.org/2005/Atom'>"
                + "".join(entries) + "</feed>")
