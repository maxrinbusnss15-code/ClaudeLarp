"""Compare evidence from several sources and turn it into one answer."""
from __future__ import annotations

import math
from datetime import datetime

from ..models import Answer, Evidence
from .questions import QUESTIONS


def freshness(observed_at: datetime, now: datetime, half_life_hours: float) -> float:
    age_h = max(0.0, (now - observed_at).total_seconds() / 3600)
    return 0.5 ** (age_h / half_life_hours) if half_life_hours > 0 else 1.0


def aggregate(question: str, evidence: list[Evidence], quorum: int, half_life_hours: float, now: datetime) -> Answer:
    ev = [e for e in evidence if e.question == question]
    prompt = QUESTIONS.get(question, question)
    weights = [e.trust * e.confidence * freshness(e.observed_at, now, half_life_hours) for e in ev]
    wsum = sum(weights)
    sources = sorted({e.source for e in ev})
    if wsum <= 1e-9:
        return Answer(question, prompt, 0.0, 0.0, sources, False,
                      "unanswered: no usable evidence" if not ev else "unanswered: evidence has no weight", ev)

    consensus = sum(w * e.signal for w, e in zip(weights, ev)) / wsum
    dispersion = math.sqrt(sum(w * (e.signal - consensus) ** 2 for w, e in zip(weights, ev)) / wsum)
    agreement = max(0.0, 1.0 - dispersion)
    # sources pointing the opposite way of the consensus
    per_src: dict[str, list[float]] = {}
    for w, e in zip(weights, ev):
        per_src.setdefault(e.source, [0.0, 0.0])
        per_src[e.source][0] += w * e.signal
        per_src[e.source][1] += w
    dissent = sorted(s for s, (num, den) in per_src.items()
                     if den > 0 and (num / den) * consensus < 0 and abs(num / den) > 0.1)
    quorum_met = len(sources) >= quorum

    lean = "bullish" if consensus > 0.1 else "bearish" if consensus < -0.1 else "neutral"
    if question == "volatility":
        lean = "expensive" if consensus > 0.1 else "cheap" if consensus < -0.1 else "fair"
    if question.startswith("ipo_") and question != "ipo_aftermarket":
        lean = "favourable" if consensus > 0.1 else "unfavourable" if consensus < -0.1 else "mixed"
    text = f"{lean} ({consensus:+.2f}), agreement {agreement:.0%}, {len(sources)} source(s)"
    if dissent:
        text += f"; dissent: {', '.join(dissent)}"
    if not quorum_met:
        text = f"unanswered: only {len(sources)}/{quorum} required sources — " + text
    return Answer(question, prompt, consensus, agreement, sources, quorum_met, text, ev)
