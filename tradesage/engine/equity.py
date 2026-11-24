"""Answer every question, then commit to a side for the underlying."""
from __future__ import annotations

from typing import Any

from ..analytics import indicators as ind
from ..models import Answer, Decision, Side
from .aggregate import aggregate
from .collector import Bundle
from .questions import QUESTIONS


def answer_all(bundle: Bundle, cfg: dict[str, Any], questions: list[str]) -> dict[str, Answer]:
    hl = cfg["freshness_half_life_hours"]
    out = {}
    for q in questions:
        out[q] = aggregate(q, bundle.evidence, cfg["quorum"].get(q, 1), hl.get(q, hl["default"]), bundle.now)
    return out


def integrity_answer(bundle: Bundle) -> Answer:
    ok, msg, _ = bundle.integrity
    srcs = [ps.source for ps in bundle.prices] + (["cboe"] if bundle.chain else [])
    return Answer("data_integrity", QUESTIONS["data_integrity"], 0.0, 1.0 if ok else 0.0, srcs, ok,
                  ("verified: " if ok else "FAILED: ") + msg)


def composite(answers: dict[str, Answer], weights: dict[str, float]) -> tuple[float, float]:
    """Return (score, coverage). Each answered question contributes consensus x agreement."""
    num = den = 0.0
    for q, w in weights.items():
        a = answers.get(q)
        if a and a.answered:
            num += w * a.consensus * (0.5 + 0.5 * a.agreement)
            den += w
    total = sum(weights.values())
    return (num / den if den else 0.0), (den / total if total else 0.0)


def decide_equity(bundle: Bundle, cfg: dict[str, Any]) -> Decision:
    weights = cfg["weights"]["equity"]
    answers = answer_all(bundle, cfg, list(weights) + ["volatility"])
    answers = {"data_integrity": integrity_answer(bundle), **answers}
    ordered = [answers[q] for q in ["data_integrity", *weights, "volatility"]]

    missing = [q for q in cfg["required"]["equity"] if not answers[q].answered]
    score, coverage = composite(answers, weights)
    rationale = [f"{a.question}: {a.text}" for a in ordered]

    if missing:
        return Decision("equity", bundle.symbol, Side.NO_DECISION, score, 0.0, ordered,
                        [f"Refusing to choose a side: required question(s) unanswered: {', '.join(missing)}"] + rationale,
                        {"instruction": "Do not trade. Fix data sources and re-run."}, bundle.failures, bundle.now)

    if abs(score) < 1e-6:  # exact tie: defer to the trend
        score = 1e-6 if answers["trend"].consensus >= 0 else -1e-6
    side = Side.LONG if score > 0 else Side.SHORT
    agreement = sum(a.agreement for a in ordered if a.answered and a.question in weights) / max(
        1, sum(1 for a in ordered if a.answered and a.question in weights))
    conviction = min(1.0, abs(score) * 2) * coverage * (0.5 + 0.5 * agreement)

    action = _equity_action(bundle, side, conviction, cfg)
    head = (f"{side.value} {bundle.symbol}: score {score:+.2f}, conviction {conviction:.0%} "
            f"({coverage:.0%} of weighted questions answered)")
    agree = [q for q in weights if answers[q].answered and answers[q].consensus * score > 0]
    against = [q for q in weights if answers[q].answered and answers[q].consensus * score < 0]
    return Decision("equity", bundle.symbol, side, score, conviction, ordered,
                    [head, f"supporting: {', '.join(agree) or '-'}; opposing: {', '.join(against) or '-'}"] + rationale,
                    action, bundle.failures, bundle.now)


def _equity_action(bundle: Bundle, side: Side, conviction: float, cfg: dict[str, Any]) -> dict[str, Any]:
    risk = cfg["risk"]
    price = bundle.integrity[2] or (bundle.prices[0].last if bundle.prices else 0)
    vols = [v for v in (ind.realized_vol(ps.closes, 20) for ps in bundle.prices) if v]
    vol = sum(vols) / len(vols) if vols else 0.3
    stop_dist = 2.0 * vol * (5 / 252) ** 0.5 * price  # ~2 sigma weekly move
    risk_budget = risk["account_equity"] * risk["risk_per_trade"] * min(1.0, conviction / 0.5)
    qty = int(risk_budget // stop_dist) if stop_dist > 0 else 0
    sgn = 1 if side == Side.LONG else -1
    tier = "high" if conviction >= 0.5 else "medium" if conviction >= 0.25 else "low"
    return {
        "instruction": f"{'BUY' if sgn > 0 else 'SELL SHORT'} {qty} shares (paper)",
        "reference_price": round(price, 2),
        "stop_loss": round(price - sgn * stop_dist, 2),
        "take_profit": round(price + sgn * 2 * stop_dist, 2),
        "risk_budget": round(risk_budget, 2),
        "conviction_tier": tier,
        "realized_vol_20d": round(vol, 4),
    }
