import json

from tradesage.cli import main
from tradesage.engine.equity import decide_equity
from tradesage.engine.options import choose_strategy, decide_options
from tradesage.models import Side

from .conftest import FailingHttp


def test_bull_scenario_goes_long(make_collector, cfg):
    d = decide_equity(make_collector("bull").equity_bundle("NVDA"), cfg)
    assert d.side == Side.LONG
    assert all(a.answered for a in d.answers)
    assert d.action["stop_loss"] < d.action["reference_price"] < d.action["take_profit"]


def test_bear_scenario_goes_short(make_collector, cfg):
    d = decide_equity(make_collector("bear").equity_bundle("NVDA"), cfg)
    assert d.side == Side.SHORT
    assert d.action["stop_loss"] > d.action["reference_price"]


def test_refuses_without_cross_verified_price(make_collector, cfg):
    http = FailingHttp(("stooq", "cboe.com/api/global/delayed_quotes/options"))
    d = decide_equity(make_collector(http=http).equity_bundle("AAPL"), cfg)
    assert d.side == Side.NO_DECISION
    assert "data_integrity" in d.rationale[0]
    assert {f.source for f in d.failures} >= {"stooq", "cboe"}


def test_refuses_when_feeds_disagree(make_collector, cfg):
    class Bad(FailingHttp):
        def get_text(self, url, ttl=0, headers=None):
            body = super().get_text(url, ttl, headers)
            if "stooq" in url:  # corrupt one vendor's prices by +10 %
                lines = body.splitlines()
                last = lines[-1].split(",")
                last[4] = f"{float(last[4]) * 1.1:.4f}"
                lines[-1] = ",".join(last)
                body = "\n".join(lines)
            return body

    d = decide_equity(make_collector(http=Bad(())).equity_bundle("AAPL"), cfg)
    assert d.side == Side.NO_DECISION
    assert "disagree" in d.answers[0].text


def test_survives_news_and_macro_outage(make_collector, cfg):
    http = FailingHttp(("rss", "news.google", "fred", "quotes/_VIX"))
    d = decide_equity(make_collector(http=http).equity_bundle("AAPL"), cfg)
    assert d.side in (Side.LONG, Side.SHORT)  # still decides on what is verifiable
    answers = {a.question: a for a in d.answers}
    assert not answers["macro"].answered and not answers["sentiment"].answered


def test_strategy_matrix():
    assert choose_strategy(0.4, 0.5, 0.1) == (Side.LONG, "bull_put_spread")
    assert choose_strategy(0.4, -0.5, 0.1) == (Side.LONG, "long_call")
    assert choose_strategy(0.4, 0.0, 0.1) == (Side.LONG, "bull_call_spread")
    assert choose_strategy(-0.4, 0.5, 0.1) == (Side.SHORT, "bear_call_spread")
    assert choose_strategy(-0.4, -0.5, 0.1) == (Side.SHORT, "long_put")
    assert choose_strategy(0.02, 0.5, 0.1) == (Side.SELL_VOL, "iron_condor")
    assert choose_strategy(0.02, -0.5, 0.1) == (Side.BUY_VOL, "long_straddle")


def test_options_trade_is_consistent(make_collector, cfg):
    for scen in ("bull", "bear", "mixed"):
        for sym in ("AAPL", "SPY", "MSFT"):
            d = decide_options(make_collector(scen).equity_bundle(sym), cfg)
            assert d.side != Side.NO_DECISION, d.rationale[:2]
            t = d.action
            assert t["max_loss_per_contract"] > 0
            assert 0 <= t["prob_of_profit_est"] <= 1
            assert t["total_risk"] <= cfg["risk"]["account_equity"] * cfg["risk"]["risk_per_trade"] + 1e-6
            if t["strategy"] in ("bull_put_spread", "bear_call_spread"):
                sell, buy = t["legs"]
                assert sell["action"] == "SELL" and buy["action"] == "BUY"
                # the protective leg is further out of the money
                assert (buy["strike"] < sell["strike"]) == (t["strategy"] == "bull_put_spread")


def test_cli_json(capsys):
    assert main(["analyze", "AAPL", "--demo", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["side"] in ("LONG", "SHORT") and out["kind"] == "equity"
