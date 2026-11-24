from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Side(str, Enum):
    LONG = "LONG"            # buy / bullish / participate
    SHORT = "SHORT"          # sell / bearish / avoid-or-short
    BUY_VOL = "BUY_VOL"      # options: direction-neutral, long volatility
    SELL_VOL = "SELL_VOL"    # options: direction-neutral, short volatility
    NO_DECISION = "NO_DECISION"


@dataclass
class Evidence:
    """One source's answer to one question.

    signal:     -1 (bearish / vol cheap / avoid) .. +1 (bullish / vol expensive / participate)
    confidence: 0..1, how strongly the source's own data supports the signal
    trust:      0..1, how much we trust the source itself (from config)
    """

    question: str
    source: str
    trust: float
    signal: float
    confidence: float
    observed_at: datetime
    summary: str
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.signal = max(-1.0, min(1.0, float(self.signal)))
        self.confidence = max(0.0, min(1.0, float(self.confidence)))
        self.trust = max(0.0, min(1.0, float(self.trust)))


@dataclass
class SourceFailure:
    source: str
    error: str


@dataclass
class Answer:
    question: str
    prompt: str
    consensus: float          # trust-weighted signal, -1..1
    agreement: float          # 0..1, 1 = all sources agree
    sources: list[str]
    quorum_met: bool
    text: str
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def answered(self) -> bool:
        return self.quorum_met


@dataclass
class Decision:
    kind: str                 # "equity" | "options" | "ipo"
    subject: str
    side: Side
    score: float              # signed composite, -1..1
    conviction: float         # 0..1
    answers: list[Answer]
    rationale: list[str]
    action: dict[str, Any]
    failures: list[SourceFailure] = field(default_factory=list)
    generated_at: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        def conv(o: Any) -> Any:
            if isinstance(o, datetime):
                return o.isoformat()
            if isinstance(o, Enum):
                return o.value
            if isinstance(o, dict):
                return {k: conv(v) for k, v in o.items()}
            if isinstance(o, (list, tuple)):
                return [conv(v) for v in o]
            return o

        return conv(asdict(self))
