from datetime import timedelta

from tradesage.engine.ipo import IpoAnalyzer, short_name
from tradesage.journal import Journal
from tradesage.models import Side
from tradesage.sources.ipo import IpoDeal

from .conftest import TODAY, FailingHttp


def test_short_name():
    assert short_name("Aurora Robotics Inc.") == "Aurora Robotics"
    assert short_name("Cirqit Semiconductor Ltd") == "Cirqit Semiconductor"


def test_scan_decides_every_deal(make_collector, tmp_path):
    an = IpoAnalyzer(make_collector(), tmp_path / "state.json")
    decisions = an.scan()
    assert len(decisions) >= 8
    assert all(d.side in (Side.LONG, Side.SHORT) for d in decisions)
    blmc = next(d for d in decisions if d.subject.startswith("BLMC"))
    assert blmc.side == Side.SHORT  # tiny deal, sub-$5, Capital Market
    assert (tmp_path / "state.json").exists()


def test_pricing_vs_remembered_range(make_collector, tmp_path):
    an = IpoAnalyzer(make_collector(), tmp_path / "s.json")
    an.state = {"ZZZ": {"company": "Zed", "ranges": [{"seen": "2026-11-01", "range": [10, 12]}]}}
    above = IpoDeal("priced", "Zed Inc", "ZZZ", "NYSE", 14, 14, 1e7, 1.4e8, TODAY - timedelta(days=2))
    below = IpoDeal("priced", "Zed Inc", "ZZZ", "NYSE", 8, 8, 1e7, 8e7, TODAY - timedelta(days=2))
    assert any(e.signal > 0.5 and "ABOVE" in e.summary for e in an.deal_evidence(above))
    assert any(e.signal < -0.5 and "BELOW" in e.summary for e in an.deal_evidence(below))


def test_lockup_expiry_is_bearish(make_collector):
    an = IpoAnalyzer(make_collector())
    jolt = next(d for d in an.deals() if d.ticker == "JOLT")
    ev = an.aftermarket_evidence(jolt)
    assert ev and all("lock-up" in e.summary for e in ev)


def test_no_decision_without_regulator(make_collector):
    an = IpoAnalyzer(make_collector(http=FailingHttp(("browse-edgar",))))
    d = an.scan(limit=1)[0]
    assert d.side == Side.NO_DECISION
    assert "ipo_regulator" in d.rationale[0]


def test_journal_detects_flip(make_collector, cfg, tmp_path):
    from tradesage.engine.equity import decide_equity

    j = Journal(tmp_path / "j.jsonl")
    assert j.append(decide_equity(make_collector("bull").equity_bundle("NVDA"), cfg)) is None
    flip = j.append(decide_equity(make_collector("bear").equity_bundle("NVDA"), cfg))
    assert flip and "LONG -> SHORT" in flip
