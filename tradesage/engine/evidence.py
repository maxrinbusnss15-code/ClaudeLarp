"""Turn raw source data into per-source Evidence for each question."""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from ..analytics import indicators as ind
from ..analytics.blackscholes import delta as bs_delta
from ..analytics.sentiment import normalize_title, score_text
from ..models import Evidence
from ..sources.macro import MacroSeries
from ..sources.news import Headline
from ..sources.options import OptionChain
from ..sources.prices import PriceSeries


def _ts(d: date) -> datetime:
    return datetime.combine(d, time(21, 0), tzinfo=timezone.utc)


# ---------------------------------------------------------------- price based
def trend_evidence(ps: PriceSeries, trust: float) -> Evidence:
    c = ps.closes
    parts, notes = [], []
    s50, s200 = ind.sma(c, 50), ind.sma(c, 200)
    if s50:
        parts.append(ind.clamp((c[-1] / s50 - 1) * 10))
        notes.append(f"px/SMA50 {c[-1] / s50 - 1:+.1%}")
    if s200:
        parts.append(ind.clamp((c[-1] / s200 - 1) * 5))
        notes.append(f"px/SMA200 {c[-1] / s200 - 1:+.1%}")
    if s50 and s200:
        parts.append(1.0 if s50 > s200 else -1.0)
        notes.append("golden-cross" if s50 > s200 else "death-cross")
    for n, scale, label in ((63, 5, "3m"), (126, 3, "6m")):
        r = ind.pct_return(c, n)
        if r is not None:
            parts.append(ind.clamp(r * scale))
            notes.append(f"{label} {r:+.1%}")
    r12 = ind.pct_return(c, 231, skip=21)
    if r12 is not None:
        parts.append(ind.clamp(r12 * 2))
        notes.append(f"12-1m {r12:+.1%}")
    sig = sum(parts) / len(parts) if parts else 0.0
    conf = min(1.0, len(c) / 252) if parts else 0.0
    return Evidence("trend", ps.source, trust, sig, conf, _ts(ps.as_of), ", ".join(notes), {"last": c[-1]})


def short_term_evidence(ps: PriceSeries, trust: float) -> Evidence:
    c = ps.closes
    r = ind.rsi(c, 14)
    r5 = ind.pct_return(c, 5)
    vol = ind.realized_vol(c, 20) or 0.3
    parts, notes = [], []
    if r is not None:
        # mean reversion: overbought => bearish tilt, oversold => bullish tilt
        parts.append(ind.clamp((50 - r) / 25))
        notes.append(f"RSI14 {r:.0f}")
    if r5 is not None:
        z = r5 / (vol * (5 / 252) ** 0.5) if vol else 0
        parts.append(ind.clamp(-z / 3))
        notes.append(f"5d {r5:+.1%} (z {z:+.1f})")
    sig = sum(parts) / len(parts) if parts else 0.0
    return Evidence("short_term", ps.source, trust, sig, 0.7 if parts else 0.0, _ts(ps.as_of), ", ".join(notes))


def integrity_check(prices: list[tuple[str, float, date]], max_spread: float, max_stale_days: int,
                    min_sources: int, today: date) -> tuple[bool, str, float | None]:
    """Cross-verify the latest price across independent feeds."""
    fresh = [(s, p, d) for s, p, d in prices if (today - d).days <= max_stale_days and p > 0]
    stale = [s for s, _, d in prices if (today - d).days > max_stale_days]
    if len(fresh) < min_sources:
        msg = f"only {len(fresh)} fresh price source(s) (need {min_sources})"
        if stale:
            msg += f"; stale: {', '.join(stale)}"
        return False, msg, fresh[0][1] if fresh else None
    vals = [p for _, p, _ in fresh]
    med = statistics.median(vals)
    spread = (max(vals) - min(vals)) / med
    detail = ", ".join(f"{s}={p:.2f}" for s, p, _ in fresh)
    if spread > max_spread:
        return False, f"price feeds disagree by {spread:.1%} (> {max_spread:.0%}): {detail}", med
    return True, f"{len(fresh)} feeds agree within {spread:.2%}: {detail}", med


# ------------------------------------------------------------- fundamentals
def _yoy_quarter(series, label: str):
    q = [f for f in series if f.start and 80 <= (f.end - f.start).days <= 100]
    if len(q) < 2:
        return None
    latest = q[-1]
    prior = [f for f in q if abs((latest.end - f.end).days - 365) <= 20]
    if not prior or prior[-1].value == 0:
        return None
    return latest, prior[-1]


def fundamentals_evidence(facts: dict, trust: float, edgar) -> list[Evidence]:
    out: list[Evidence] = []
    rev = edgar.series(facts, ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"])
    ni = edgar.series(facts, ["NetIncomeLoss", "ProfitLoss"])
    pair = _yoy_quarter(rev, "revenue")
    if pair:
        cur, old = pair
        g = cur.value / old.value - 1
        out.append(Evidence("fundamentals", "sec_edgar", trust, ind.clamp(g * 4), 0.9, _ts(cur.filed),
                            f"revenue YoY {g:+.1%} (Q ending {cur.end})", {"revenue_growth": g}))
        ni_pair = _yoy_quarter(ni, "ni")
        if ni_pair:
            ncur, nold = ni_pair
            m_now, m_then = ncur.value / cur.value, nold.value / old.value
            sig = ind.clamp(m_now * 3) * 0.5 + ind.clamp((m_now - m_then) * 10) * 0.5
            out.append(Evidence("fundamentals", "sec_edgar", trust, sig, 0.8, _ts(ncur.filed),
                                f"net margin {m_now:.1%} vs {m_then:.1%} a year ago",
                                {"net_margin": m_now, "net_margin_prev": m_then}))
    shares = edgar.series(facts, ["EntityCommonStockSharesOutstanding"], unit="shares", taxonomy="dei")
    if len(shares) >= 2:
        cur = shares[-1]
        prev = [s for s in shares if (cur.end - s.end).days >= 300]
        if prev and prev[-1].value:
            dil = cur.value / prev[-1].value - 1
            out.append(Evidence("fundamentals", "sec_edgar", trust, ind.clamp(-dil * 10), 0.6, _ts(cur.filed),
                                f"share count {dil:+.1%} YoY ({'buybacks' if dil < 0 else 'dilution'})",
                                {"share_change": dil}))
    return out


# ---------------------------------------------------------------- sentiment
def sentiment_evidence(by_feed: dict[str, list[Headline]], trust: dict[str, float], now: datetime,
                       half_life_hours: float, max_age_days: int = 14) -> list[Evidence]:
    """One Evidence per feed. Syndicated duplicates only count for the most trusted feed."""
    seen: set[str] = set()
    out = []
    for feed in sorted(by_feed, key=lambda f: -trust.get(f, 0.5)):
        scored, wsum, total = [], 0.0, 0.0
        for h in by_feed[feed]:
            if (now - h.published).days > max_age_days:
                continue
            key = normalize_title(h.title)
            if key in seen:
                continue
            seen.add(key)
            s, hits = score_text(h.title)
            age_h = max(0.0, (now - h.published).total_seconds() / 3600)
            w = 0.5 ** (age_h / half_life_hours)
            wsum += w
            total += w * s
            if hits:
                scored.append((s, h.title))
        if wsum == 0:
            continue
        n = sum(1 for h in by_feed[feed] if (now - h.published).days <= max_age_days)
        sig = total / wsum
        conf = min(1.0, len(scored) / 5) * 0.8 + 0.2 * min(1.0, n / 10)
        top = sorted(scored, key=lambda x: -abs(x[0]))[:2]
        summary = f"{n} headlines, {len(scored)} with signal" + (
            "; e.g. " + " | ".join(t[:70] for _, t in top) if top else "")
        newest = max(h.published for h in by_feed[feed])
        out.append(Evidence("sentiment", feed, trust.get(feed, 0.5), sig, conf, newest, summary))
    return out


# -------------------------------------------------------------------- macro
def macro_evidence(series: dict[str, MacroSeries], trust: float, cboe_vix: float | None, cboe_trust: float,
                   today: date) -> list[Evidence]:
    out = []
    vix = series.get("VIXCLS")
    if vix:
        v = vix.values[-1]
        avg = statistics.mean(vix.values[-20:])
        sig = ind.clamp((20 - v) / 10) * 0.7 + ind.clamp((avg - v) / 5) * 0.3
        out.append(Evidence("macro", "fred", trust, sig, 0.9, _ts(vix.dates[-1]),
                            f"VIX {v:.1f} (20d avg {avg:.1f})", {"vix": v}))
    if cboe_vix:
        sig = ind.clamp((20 - cboe_vix) / 10)
        out.append(Evidence("macro", "cboe", cboe_trust, sig, 0.9, datetime.now(timezone.utc),
                            f"VIX live {cboe_vix:.1f}", {"vix": cboe_vix}))
    yc = series.get("T10Y2Y")
    if yc:
        v = yc.values[-1]
        chg = v - yc.values[-63] if len(yc.values) > 63 else 0
        sig = ind.clamp(v * 0.5) * 0.6 + ind.clamp(chg) * 0.4
        out.append(Evidence("macro", "fred", trust, sig, 0.5, _ts(yc.dates[-1]),
                            f"10y-2y {v:+.2f}pp (3m chg {chg:+.2f})"))
    hy = series.get("BAMLH0A0HYM2")
    if hy and len(hy.values) > 30:
        v = hy.values[-1]
        med = statistics.median(hy.values[-250:])
        sig = ind.clamp((med - v) / 1.0)
        out.append(Evidence("macro", "fred", trust, sig, 0.8, _ts(hy.dates[-1]),
                            f"HY spread {v:.2f}% vs 1y median {med:.2f}%"))
    return out


# ------------------------------------------------------------------ options
def _near_expiry(chain: OptionChain, today: date, lo: int = 20, hi: int = 60, target: int = 30) -> date | None:
    exps = sorted({q.expiry for q in chain.quotes})
    cands = [e for e in exps if lo <= (e - today).days <= hi] or [e for e in exps if (e - today).days >= 7]
    if not cands:
        return None
    return min(cands, key=lambda e: abs((e - today).days - target))


def quote_delta(q, spot: float, today: date, r: float = 0.04) -> float | None:
    if q.delta is not None:
        return q.delta
    if q.iv:
        t = max((q.expiry - today).days, 1) / 365
        return bs_delta(spot, q.strike, t, r, q.iv, q.is_call)
    return None


def atm_iv(chain: OptionChain, today: date) -> float | None:
    exp = _near_expiry(chain, today)
    if not exp:
        return chain.iv30
    qs = [q for q in chain.quotes if q.expiry == exp and q.iv]
    if not qs:
        return chain.iv30
    k = min({q.strike for q in qs}, key=lambda s: abs(s - chain.spot))
    ivs = [q.iv for q in qs if q.strike == k]
    return sum(ivs) / len(ivs)


def positioning_evidence(chain: OptionChain, trust: float, today: date) -> list[Evidence]:
    out = []
    cv = sum(q.volume for q in chain.quotes if q.is_call)
    pv = sum(q.volume for q in chain.quotes if not q.is_call)
    co = sum(q.open_interest for q in chain.quotes if q.is_call)
    po = sum(q.open_interest for q in chain.quotes if not q.is_call)
    now = datetime.now(timezone.utc)
    if cv + pv > 0 and cv:
        pcr = pv / cv
        # contrarian at extremes, trend-following in the middle
        sig = ind.clamp((0.9 - pcr) * 1.5) if pcr < 1.5 else ind.clamp((pcr - 1.5))
        out.append(Evidence("positioning", chain.source, trust, sig, min(1.0, (cv + pv) / 20000) * 0.6 + 0.2,
                            now, f"put/call volume {pcr:.2f}", {"pcr_volume": pcr}))
    if co and po:
        pcr_oi = po / co
        out.append(Evidence("positioning", chain.source, trust, ind.clamp((1.0 - pcr_oi)), 0.5, now,
                            f"put/call open interest {pcr_oi:.2f}", {"pcr_oi": pcr_oi}))
    exp = _near_expiry(chain, today)
    if exp:
        qs = [q for q in chain.quotes if q.expiry == exp and q.iv]
        puts = [(abs((quote_delta(q, chain.spot, today) or 0) + 0.25), q.iv) for q in qs if not q.is_call]
        calls = [(abs((quote_delta(q, chain.spot, today) or 0) - 0.25), q.iv) for q in qs if q.is_call]
        if puts and calls:
            skew = min(puts)[1] - min(calls)[1]
            out.append(Evidence("positioning", chain.source, trust, ind.clamp(-(skew - 0.03) * 10), 0.5, now,
                                f"25-delta skew {skew * 100:+.1f} vol pts", {"skew": skew}))
    return out


def volatility_evidence(chain: OptionChain, prices: list[PriceSeries], trust: dict[str, float],
                        today: date) -> list[Evidence]:
    iv = atm_iv(chain, today)
    if not iv:
        return []
    out = []
    for ps in prices:
        rv = ind.realized_vol(ps.closes, 30)
        rv10 = ind.realized_vol(ps.closes, 10)
        if not rv:
            continue
        ratio = iv / rv
        sig = ind.clamp((ratio - 1.1) / 0.4)
        out.append(Evidence("volatility", f"{chain.source}+{ps.source}", min(trust.get(chain.source, 0.9),
                            trust.get(ps.source, 0.7)), sig, 0.8, _ts(ps.as_of),
                            f"ATM IV {iv:.1%} vs 30d RV {rv:.1%} (10d {rv10 or 0:.1%}), ratio {ratio:.2f}",
                            {"iv": iv, "rv30": rv, "ratio": ratio}))
    return out


def group_headlines(headlines: list[Headline]) -> dict[str, list[Headline]]:
    d: dict[str, list[Headline]] = defaultdict(list)
    for h in headlines:
        d[h.source].append(h)
    return d


def days_between(a: date, b: date) -> int:
    return (b - a).days


