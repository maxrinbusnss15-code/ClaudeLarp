"""IPO pipeline: confirm with the regulator, judge the deal and the IPO climate, then pick a side."""
from __future__ import annotations

import json
import re
import statistics
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from ..analytics import indicators as ind
from ..models import Answer, Decision, Evidence, Side, SourceFailure
from ..sources.ipo import IpoDeal, NasdaqIpoCalendar
from .aggregate import aggregate
from .collector import Collector
from .equity import composite
from .evidence import _ts

_SUFFIX = re.compile(r"\b(inc|corp|corporation|co|ltd|limited|plc|holdings?|group|sa|nv|ag|llc|lp)\b\.?", re.I)


def short_name(company: str) -> str:
    name = _SUFFIX.sub("", re.sub(r"[^\w\s&-]", " ", company))
    words = name.split()
    return " ".join(words[:2]) if words else company


class IpoAnalyzer:
    def __init__(self, collector: Collector, state_path: Path | None = None):
        self.c = collector
        self.cfg = collector.cfg
        self.calendar = NasdaqIpoCalendar(collector.http, self.cfg["cache_ttl_seconds"]["ipo"])
        self.state_path = state_path
        self.state: dict[str, Any] = {}
        if state_path and state_path.exists():
            try:
                self.state = json.loads(state_path.read_text())
            except ValueError:
                self.state = {}
        self.failures: list[SourceFailure] = []
        self.cal_failures: list[SourceFailure] = []
        self._climate: list[Evidence] | None = None

    # -------------------------------------------------------------- data
    def deals(self) -> list[IpoDeal]:
        today = self.c.now.date()
        months = []
        y, m = today.year, today.month
        for delta in range(1, -8, -1):  # next month .. 7 months back (covers 180-day lock-ups)
            mm, yy = m + delta, y
            while mm < 1:
                mm, yy = mm + 12, yy - 1
            while mm > 12:
                mm, yy = mm - 12, yy + 1
            months.append((yy, mm))
        jobs = {f"nasdaq:{yy}-{mm:02d}": (lambda yy=yy, mm=mm: self.calendar.month(yy, mm)) for yy, mm in months}
        res, fails = self.c._run(jobs)
        self.cal_failures += fails
        seen, out = set(), []
        for deals in res.values():
            for d in deals:
                key = (d.status, d.ticker or d.company)
                if key not in seen:
                    seen.add(key)
                    out.append(d)
        self._snapshot(out)
        return out

    def _snapshot(self, deals: list[IpoDeal]) -> None:
        """Remember every price range we see so later pricing can be judged against it."""
        today = self.c.now.date().isoformat()
        for d in deals:
            if d.status != "upcoming" or not d.ticker or not d.price_low:
                continue
            rec = self.state.setdefault(d.ticker, {"company": d.company, "ranges": []})
            rng = [d.price_low, d.price_high]
            if not rec["ranges"] or rec["ranges"][-1]["range"] != rng:
                rec["ranges"].append({"seen": today, "range": rng, "shares": d.shares})
        if self.state_path:
            self.state_path.write_text(json.dumps(self.state, indent=1))

    # ---------------------------------------------------------- evidence
    def regulator_evidence(self, deal: IpoDeal) -> list[Evidence]:
        name = short_name(deal.company)
        jobs = {f"sec_edgar:{form}": (lambda form=form: self.c.edgar.filings_by_company(name, form))
                for form in ("S-1", "F-1", "424B4")}
        res, fails = self.c._run(jobs)
        self.failures += fails
        trust = self.cfg["trust"]["sec_edgar"]
        out = []
        regs = res.get("sec_edgar:S-1", []) + res.get("sec_edgar:F-1", [])
        finals = res.get("sec_edgar:424B4", [])
        if regs:
            amends = sum(1 for f in regs if f.form.endswith("/A"))
            first = min(f.filed for f in regs)
            out.append(Evidence("ipo_regulator", "sec_edgar", trust, 0.6, 1.0, _ts(max(f.filed for f in regs)),
                                f"{len(regs)} registration filing(s) since {first} ({amends} amendment(s))",
                                {"amendments": amends, "first_filed": first.isoformat()}))
            age = (self.c.now.date() - first).days
            sig = -0.4 if amends > 8 or age > 540 else 0.1
            out.append(Evidence("ipo_deal", "sec_edgar", trust, sig, 0.5, _ts(max(f.filed for f in regs)),
                                f"{amends} S-1/F-1 amendments, on file for {age} days"
                                + (" (long/troubled registration)" if sig < 0 else "")))
        if finals:
            out.append(Evidence("ipo_regulator", "sec_edgar", trust, 1.0, 1.0, _ts(max(f.filed for f in finals)),
                                "final prospectus (424B4) filed — deal priced"))
        return out

    def deal_evidence(self, deal: IpoDeal) -> list[Evidence]:
        trust = self.cfg["trust"]["nasdaq"]
        when = _ts(deal.event_date or self.c.now.date())
        out = []

        def add(sig, conf, text, **data):
            out.append(Evidence("ipo_deal", "nasdaq", trust, sig, conf, when, text, data))

        size = deal.deal_size or ((deal.shares or 0) * (deal.mid_price or 0)) or None
        if size:
            sig = 0.5 if size >= 500e6 else 0.2 if size >= 100e6 else -0.2 if size >= 25e6 else -0.7
            add(sig, 0.7, f"deal size ${size / 1e6:,.0f}M", deal_size=size)
        ex = (deal.exchange or "").upper()
        if ex:
            sig = 0.3 if ("NYSE" in ex and "AMERICAN" not in ex) or "GLOBAL SELECT" in ex else -0.3 if (
                "CAPITAL" in ex or "AMERICAN" in ex or "OTC" in ex) else 0.0
            add(sig, 0.5, f"listing venue {deal.exchange}")
        px = deal.mid_price
        if px:
            add(0.2 if px >= 10 else -0.2 if px >= 5 else -0.7, 0.5, f"price ${px:.2f}")
        if deal.price_low and deal.price_high and deal.price_high > deal.price_low:
            width = (deal.price_high - deal.price_low) / deal.mid_price
            if width > 0.25:
                add(-0.2, 0.4, f"wide price range ({width:.0%}) signals uncertain demand")

        hist = self.state.get(deal.ticker, {}).get("ranges", [])
        if hist:
            lo0, hi0 = hist[0]["range"]
            if deal.status == "priced" and px:
                if px > hi0:
                    add(0.8, 0.9, f"priced ${px:.2f} ABOVE original range ${lo0}-{hi0} (strong demand)")
                elif px < lo0:
                    add(-0.7, 0.9, f"priced ${px:.2f} BELOW original range ${lo0}-{hi0} (weak demand)")
                else:
                    add(0.1, 0.6, f"priced ${px:.2f} within original range ${lo0}-{hi0}")
            elif deal.status == "upcoming" and len(hist) > 1:
                mid0, mid1 = (lo0 + hi0) / 2, sum(hist[-1]["range"]) / 2
                if mid1 != mid0:
                    chg = mid1 / mid0 - 1
                    add(ind.clamp(chg * 5), 0.8, f"range revised {'up' if chg > 0 else 'down'} {chg:+.0%} since {hist[0]['seen']}")
        return out

    def climate_evidence(self, deals: list[IpoDeal]) -> list[Evidence]:
        """How are the last ~90 days of IPOs trading versus their offer price, per price source?"""
        if self._climate is not None:
            return self._climate
        today = self.c.now.date()
        recent = [d for d in deals if d.status == "priced" and d.ticker and d.mid_price and d.event_date
                  and 3 <= (today - d.event_date).days <= 120]
        recent = sorted(recent, key=lambda d: d.event_date, reverse=True)[:15]
        jobs = {f"{f.name}:{d.ticker}": (lambda f=f, d=d: f.history(d.ticker))
                for d in recent for f in self.c.price_feeds}
        res, fails = self.c._run(jobs)
        self.cal_failures += fails
        out = []
        for feed in self.c.price_feeds:
            rets = []
            for d in recent:
                ps = res.get(f"{feed.name}:{d.ticker}")
                if ps:
                    rets.append(ps.last / d.mid_price - 1)
            if len(rets) < 3:
                continue
            med = statistics.median(rets)
            above = sum(r > 0 for r in rets) / len(rets)
            sig = ind.clamp(med * 3) * 0.6 + ind.clamp((above - 0.5) * 2) * 0.4
            out.append(Evidence("ipo_climate", feed.name, self.cfg["trust"].get(feed.name, 0.7), sig,
                                min(1.0, len(rets) / 8), self.c.now,
                                f"{len(rets)} recent IPOs: median {med:+.1%} vs offer, {above:.0%} above offer",
                                {"median_return": med, "pct_above": above}))
        self._climate = out
        return out

    def aftermarket_evidence(self, deal: IpoDeal) -> list[Evidence]:
        if deal.status != "priced" or not deal.ticker or not deal.mid_price or not deal.event_date:
            return []
        jobs = {f.name: (lambda f=f: f.history(deal.ticker)) for f in self.c.price_feeds}
        res, fails = self.c._run(jobs)
        self.failures += fails
        days = (self.c.now.date() - deal.event_date).days
        lockup = deal.event_date + timedelta(days=180)
        out = []
        for name, ps in res.items():
            r = ps.last / deal.mid_price - 1
            r20 = ind.pct_return(ps.closes, min(20, len(ps.closes) - 1)) or 0
            sig = ind.clamp(r * 2) * 0.5 + ind.clamp(r20 * 4) * 0.5
            note = f"{r:+.1%} vs offer, {r20:+.1%} last {min(20, len(ps.closes) - 1)}d"
            if 150 <= days <= 185:
                sig = sig * 0.5 - 0.5
                note += f"; lock-up expiry ~{lockup} (insider supply)"
            out.append(Evidence("ipo_aftermarket", name, self.cfg["trust"].get(name, 0.7), sig, 0.7,
                                _ts(ps.as_of), note, {"return_vs_offer": r}))
        return out

    # ------------------------------------------------------------ decide
    def decide(self, deal: IpoDeal, all_deals: list[IpoDeal]) -> Decision:
        now = self.c.now
        self.failures = []
        ev: list[Evidence] = []
        ev += self.regulator_evidence(deal)
        ev += self.deal_evidence(deal)
        ev += self.climate_evidence(all_deals)
        ev += self.aftermarket_evidence(deal)
        news, nf = self.c.headlines(deal.ticker or short_name(deal.company), f"\"{short_name(deal.company)}\" IPO")
        macro, mf = self.c.macro()
        ev += news + macro
        failures = self.cal_failures + self.failures + nf + mf

        weights = dict(self.cfg["weights"]["ipo"])
        if deal.status != "priced":
            weights.pop("ipo_aftermarket", None)
        hl = self.cfg["freshness_half_life_hours"]
        answers: dict[str, Answer] = {}
        for q in ["ipo_regulator", *weights]:
            answers[q] = aggregate(q, ev, self.cfg["quorum"].get(q, 1), hl.get(q, hl["default"]), now)
        ordered = list(answers.values())
        subject = f"{deal.ticker or '?'} ({deal.company}) [{deal.status}]"
        rationale = [f"{a.question}: {a.text}" for a in ordered]

        missing = [q for q in self.cfg["required"]["ipo"] if not answers[q].answered]
        score, coverage = composite(answers, weights)
        if missing:
            return Decision("ipo", subject, Side.NO_DECISION, score, 0.0, ordered,
                            [f"Refusing to choose a side: unanswered {', '.join(missing)}"] + rationale,
                            {"instruction": "Wait: offering not yet verifiable."}, failures, now)

        side = Side.LONG if score > 0 else Side.SHORT
        conviction = min(1.0, abs(score) * 2) * coverage
        if deal.status == "priced":
            instr = ("BUY shares in the aftermarket (paper)" if side == Side.LONG
                     else "SELL / avoid; consider short only if borrow is available (paper)")
        else:
            instr = ("PARTICIPATE: request allocation or buy at open below "
                     f"${(deal.price_high or deal.mid_price or 0) * 1.25:.2f} (paper)" if side == Side.LONG
                     else "AVOID: do not request allocation, do not chase at open")
        action = {"instruction": instr, "expected_or_priced": deal.event_date.isoformat() if deal.event_date else None,
                  "price_range": [deal.price_low, deal.price_high], "exchange": deal.exchange}
        head = f"{side.value} {subject}: score {score:+.2f}, conviction {conviction:.0%}"
        return Decision("ipo", subject, side, score, conviction, ordered, [head] + rationale, action, failures, now)

    def scan(self, include_priced: bool = True, limit: int = 20) -> list[Decision]:
        deals = self.deals()
        today = self.c.now.date()
        targets = [d for d in deals if d.status == "upcoming"]
        if include_priced:
            targets += [d for d in deals if d.status == "priced" and d.event_date and (today - d.event_date).days <= 200]
        targets = targets[:limit]
        return [self.decide(d, deals) for d in targets]
