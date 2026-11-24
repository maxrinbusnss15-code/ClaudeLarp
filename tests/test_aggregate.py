from tradesage.engine.aggregate import aggregate
from tradesage.models import Evidence

from .conftest import NOW


def ev(src, sig, trust=1.0, conf=1.0, q="trend"):
    return Evidence(q, src, trust, sig, conf, NOW, "x")


def test_quorum_not_met():
    a = aggregate("trend", [ev("a", 0.8)], quorum=2, half_life_hours=24, now=NOW)
    assert not a.answered and "unanswered" in a.text


def test_trust_weighted_consensus_and_dissent():
    a = aggregate("trend", [ev("regulator", 0.8, trust=1.0), ev("blog", -0.8, trust=0.25)], 2, 24, NOW)
    assert a.answered
    assert 0.4 < a.consensus < 0.6
    assert a.agreement < 0.5
    assert "blog" in a.text  # dissent is reported


def test_stale_evidence_decays():
    from datetime import timedelta
    old = Evidence("sentiment", "old", 1.0, -1.0, 1.0, NOW - timedelta(days=10), "x")
    new = Evidence("sentiment", "new", 1.0, 1.0, 1.0, NOW, "x")
    a = aggregate("sentiment", [old, new], 2, 24, NOW)
    assert a.consensus > 0.9
