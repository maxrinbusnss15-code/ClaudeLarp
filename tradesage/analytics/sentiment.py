"""Small finance-specific headline lexicon (in the spirit of Loughran-McDonald).

Deliberately transparent: every score can be traced back to the words that drove it.
"""
from __future__ import annotations

import re

POSITIVE = {
    "beat", "beats", "beating", "surge", "surges", "soar", "soars", "jump", "jumps", "rally", "rallies",
    "record", "upgrade", "upgrades", "upgraded", "outperform", "buy", "bullish", "growth", "grows",
    "strong", "stronger", "profit", "profits", "profitable", "raises", "raised", "boost", "boosts",
    "gain", "gains", "tops", "exceeds", "exceeded", "expands", "expansion", "approval", "approved",
    "wins", "win", "breakthrough", "partnership", "dividend", "buyback", "optimistic", "upbeat",
    "accelerates", "oversubscribed", "upsized", "rebound", "rebounds", "climbs", "higher",
}
NEGATIVE = {
    "miss", "misses", "missed", "plunge", "plunges", "plummet", "plummets", "drop", "drops", "fall",
    "falls", "slump", "slumps", "downgrade", "downgrades", "downgraded", "underperform", "sell",
    "bearish", "loss", "losses", "weak", "weaker", "cut", "cuts", "lowers", "lowered", "lawsuit",
    "probe", "investigation", "fraud", "recall", "warning", "warns", "decline", "declines", "layoffs",
    "bankruptcy", "default", "delay", "delays", "delayed", "postpones", "postponed", "withdrawn",
    "downsized", "slashes", "tumble", "tumbles", "sinks", "lower", "concern", "concerns", "risk",
    "subpoena", "halt", "halted", "dilution", "shortfall",
}
NEGATORS = {"not", "no", "never", "without", "fails", "failed"}

_WORD = re.compile(r"[a-z']+")


def score_text(text: str) -> tuple[float, list[str]]:
    """Return (score in -1..1, matched words)."""
    words = _WORD.findall(text.lower())
    total, hits = 0, []
    for i, w in enumerate(words):
        val = 1 if w in POSITIVE else -1 if w in NEGATIVE else 0
        if not val:
            continue
        if i > 0 and words[i - 1] in NEGATORS:
            val = -val
        total += val
        hits.append(w)
    if not hits:
        return 0.0, []
    return max(-1.0, min(1.0, total / max(2, len(hits)))), hits


def normalize_title(title: str) -> str:
    """For de-duplicating syndicated stories across feeds."""
    t = title.lower().split(" - ")[0]
    return " ".join(_WORD.findall(t))[:80]
