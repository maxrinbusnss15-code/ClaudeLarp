"""Pick an options strategy and concrete contracts from the direction + volatility answers."""
from __future__ import annotations

import math
from datetime import date
from typing import Any

from ..analytics.blackscholes import prob_itm
from ..models import Decision, Side
from ..sources.options import OptionChain, OptionQuote
from .collector import Bundle
from .equity import decide_equity
from .evidence import quote_delta


def choose_strategy(direction: float, vol_view: float, neutral_band: float) -> tuple[Side, str]:
    expensive = vol_view > 0.1
    cheap = vol_view < -0.1
    if abs(direction) < neutral_band:
        return (Side.SELL_VOL, "iron_condor") if not cheap else (Side.BUY_VOL, "long_straddle")
    if direction > 0:
        return Side.LONG, ("bull_put_spread" if expensive else "long_call" if cheap else "bull_call_spread")
    return Side.SHORT, ("bear_call_spread" if expensive else "long_put" if cheap else "bear_put_spread")


def _liquid(qs: list[OptionQuote]) -> list[OptionQuote]:
    good = [q for q in qs if q.bid > 0 and q.ask > 0 and (q.ask - q.bid) / q.mid <= 0.25
            and (q.open_interest >= 50 or q.volume > 0)]
    return good or [q for q in qs if q.ask > 0]


def _pick(qs: list[OptionQuote], target_delta: float, spot: float, today: date) -> OptionQuote | None:
    cands = [(abs((quote_delta(q, spot, today) or 0) - target_delta), q) for q in qs
             if quote_delta(q, spot, today) is not None]
    return min(cands, key=lambda x: x[0])[1] if cands else None


def _expiry(chain: OptionChain, today: date, risk: dict[str, Any]) -> date | None:
    exps = sorted({q.expiry for q in chain.quotes})
    ok = [e for e in exps if risk["min_dte"] <= (e - today).days <= risk["max_dte"]]
    ok = ok or [e for e in exps if (e - today).days >= 7]
    return min(ok, key=lambda e: abs((e - today).days - risk["target_dte"])) if ok else None


def _leg(action: str, q: OptionQuote) -> dict[str, Any]:
    return {"action": action, "contract": q.symbol, "type": "call" if q.is_call else "put",
            "strike": q.strike, "expiry": q.expiry.isoformat(), "bid": q.bid, "ask": q.ask,
            "mid": round(q.mid, 2), "iv": q.iv, "open_interest": q.open_interest}


def build_trade(strategy: str, chain: OptionChain, today: date, risk: dict[str, Any], budget: float) -> dict[str, Any]:
    exp = _expiry(chain, today, risk)
    if not exp:
        return {"error": "no suitable expiry in chain"}
    t = max((exp - today).days, 1) / 365
    s = chain.spot
    calls = _liquid([q for q in chain.quotes if q.expiry == exp and q.is_call])
    puts = _liquid([q for q in chain.quotes if q.expiry == exp and not q.is_call])
    legs: list[dict[str, Any]] = []

    def pop_above(k, iv):  # P(S_T > k)
        return prob_itm(s, k, t, 0.04, iv or 0.3, True)

    if strategy in ("long_call", "long_put"):
        q = _pick(calls if strategy == "long_call" else puts, 0.6 if strategy == "long_call" else -0.6, s, today)
        if not q:
            return {"error": "no contract near target delta"}
        legs = [_leg("BUY", q)]
        debit = q.mid
        max_loss, max_profit = debit, math.inf
        be = q.strike + debit if q.is_call else q.strike - debit
        pop = pop_above(be, q.iv) if q.is_call else 1 - pop_above(be, q.iv)
    elif strategy in ("bull_call_spread", "bear_put_spread"):
        side = calls if strategy == "bull_call_spread" else puts
        sgn = 1 if strategy == "bull_call_spread" else -1
        long_q, short_q = _pick(side, 0.55 * sgn, s, today), _pick(side, 0.25 * sgn, s, today)
        if not long_q or not short_q or long_q.strike == short_q.strike:
            return {"error": "could not build debit spread"}
        legs = [_leg("BUY", long_q), _leg("SELL", short_q)]
        debit = long_q.mid - short_q.mid
        width = abs(short_q.strike - long_q.strike)
        max_loss, max_profit = debit, width - debit
        be = long_q.strike + sgn * debit
        pop = pop_above(be, long_q.iv) if sgn > 0 else 1 - pop_above(be, long_q.iv)
    elif strategy in ("bull_put_spread", "bear_call_spread"):
        side = puts if strategy == "bull_put_spread" else calls
        sgn = -1 if strategy == "bull_put_spread" else 1
        short_q, long_q = _pick(side, 0.30 * sgn, s, today), _pick(side, 0.15 * sgn, s, today)
        if not long_q or not short_q or long_q.strike == short_q.strike:
            return {"error": "could not build credit spread"}
        legs = [_leg("SELL", short_q), _leg("BUY", long_q)]
        credit = short_q.mid - long_q.mid
        width = abs(short_q.strike - long_q.strike)
        max_loss, max_profit = width - credit, credit
        be = short_q.strike - credit if sgn < 0 else short_q.strike + credit
        pop = pop_above(be, short_q.iv) if sgn < 0 else 1 - pop_above(be, short_q.iv)
    elif strategy == "iron_condor":
        sp, lp = _pick(puts, -0.20, s, today), _pick(puts, -0.10, s, today)
        sc, lc = _pick(calls, 0.20, s, today), _pick(calls, 0.10, s, today)
        if not all((sp, lp, sc, lc)) or sp.strike == lp.strike or sc.strike == lc.strike:
            return {"error": "could not build iron condor"}
        legs = [_leg("SELL", sp), _leg("BUY", lp), _leg("SELL", sc), _leg("BUY", lc)]
        credit = sp.mid - lp.mid + sc.mid - lc.mid
        width = max(sp.strike - lp.strike, lc.strike - sc.strike)
        max_loss, max_profit = width - credit, credit
        lo_be, hi_be = sp.strike - credit, sc.strike + credit
        be = [round(lo_be, 2), round(hi_be, 2)]
        pop = pop_above(lo_be, sp.iv) - pop_above(hi_be, sc.iv)
    elif strategy == "long_straddle":
        c = _pick(calls, 0.5, s, today)
        p = min((q for q in puts if c and q.strike == c.strike), key=lambda q: q.mid, default=None) if c else None
        if not c or not p:
            return {"error": "could not build straddle"}
        legs = [_leg("BUY", c), _leg("BUY", p)]
        debit = c.mid + p.mid
        max_loss, max_profit = debit, math.inf
        be = [round(c.strike - debit, 2), round(c.strike + debit, 2)]
        pop = 1 - pop_above(c.strike - debit, c.iv) + pop_above(c.strike + debit, c.iv)
    else:
        return {"error": f"unknown strategy {strategy}"}

    if max_loss <= 0:
        return {"error": "pricing produced non-positive max loss (stale quotes?)", "legs": legs}
    contracts = max(0, int(budget // (max_loss * 100)))
    return {
        "strategy": strategy,
        "expiry": exp.isoformat(),
        "dte": (exp - today).days,
        "legs": legs,
        "contracts": contracts,
        "max_loss_per_contract": round(max_loss * 100, 2),
        "max_profit_per_contract": None if math.isinf(max_profit) else round(max_profit * 100, 2),
        "breakeven": be if isinstance(be, list) else round(be, 2),
        "prob_of_profit_est": round(max(0.0, min(1.0, pop)), 3),
        "total_risk": round(contracts * max_loss * 100, 2),
        "instruction": (f"Open {contracts}x {strategy.replace('_', ' ')} exp {exp} (paper)" if contracts else
                        f"{strategy.replace('_', ' ')} exp {exp}: 1 contract risks ${max_loss * 100:,.0f}, above the "
                        f"${budget:,.0f} risk budget - skip, or raise risk.account_equity / risk_per_trade"),
    }


def decide_options(bundle: Bundle, cfg: dict[str, Any]) -> Decision:
    eq = decide_equity(bundle, cfg)
    answers = {a.question: a for a in eq.answers}
    vol = answers.get("volatility")
    risk = cfg["risk"]
    rationale = list(eq.rationale)

    if eq.side == Side.NO_DECISION:
        return Decision("options", bundle.symbol, Side.NO_DECISION, eq.score, 0.0, eq.answers,
                        rationale, eq.action, eq.failures, eq.generated_at)
    if not bundle.chain or not vol or not vol.answered:
        rationale.insert(0, "Refusing to pick an options trade: no option chain / volatility question unanswered")
        return Decision("options", bundle.symbol, Side.NO_DECISION, eq.score, 0.0, eq.answers,
                        rationale, {"instruction": "Do not trade options."}, eq.failures, eq.generated_at)

    side, strategy = choose_strategy(eq.score, vol.consensus, risk["neutral_band"])
    conviction = eq.conviction if side in (Side.LONG, Side.SHORT) else (abs(vol.consensus) * vol.agreement)
    budget = risk["account_equity"] * risk["risk_per_trade"] * min(1.0, max(conviction, 0.1) / 0.5)
    trade = build_trade(strategy, bundle.chain, bundle.today, risk, budget)
    vol_txt = "expensive" if vol.consensus > 0.1 else "cheap" if vol.consensus < -0.1 else "fair"
    rationale.insert(0, f"{side.value} via {strategy}: direction score {eq.score:+.2f}, implied vol {vol_txt} "
                        f"({vol.consensus:+.2f}) => "
                        + ("sell premium" if strategy in ("bull_put_spread", "bear_call_spread", "iron_condor")
                           else "buy premium"))
    if "error" in trade:
        rationale.insert(0, f"Could not build contracts: {trade['error']}")
        side = Side.NO_DECISION
    return Decision("options", bundle.symbol, side, eq.score, conviction, eq.answers, rationale, trade,
                    eq.failures, eq.generated_at)
