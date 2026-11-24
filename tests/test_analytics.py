import math

from tradesage.analytics import blackscholes as bs
from tradesage.analytics import indicators as ind
from tradesage.analytics.sentiment import normalize_title, score_text


def test_put_call_parity():
    s, k, t, r, v = 100, 105, 0.5, 0.04, 0.3
    c, p = bs.price(s, k, t, r, v, True), bs.price(s, k, t, r, v, False)
    assert math.isclose(c - p, s - k * math.exp(-r * t), rel_tol=1e-9)


def test_implied_vol_roundtrip():
    target = bs.price(250, 240, 40 / 365, 0.04, 0.37, False)
    assert math.isclose(bs.implied_vol(target, 250, 240, 40 / 365, 0.04, False), 0.37, abs_tol=1e-4)


def test_delta_bounds():
    assert 0.5 < bs.delta(100, 95, 0.1, 0.04, 0.2, True) < 1
    assert -1 < bs.delta(100, 95, 0.1, 0.04, 0.2, False) < 0


def test_indicators():
    up = [100 * 1.01 ** i for i in range(300)]
    assert ind.rsi(up) == 100.0
    assert ind.sma(up, 50) < up[-1]
    assert ind.pct_return(up, 10) > 0.1
    assert ind.realized_vol(up) < 1e-6
    assert ind.max_drawdown([1, 2, 1, 3]) == -0.5


def test_sentiment_and_negation():
    assert score_text("Company beats estimates, shares surge")[0] > 0
    assert score_text("Company misses estimates and cuts guidance")[0] < 0
    assert score_text("Regulator did not approve drug... not approved")[0] < 0
    assert score_text("CEO to speak at conference") == (0.0, [])
    assert normalize_title("X beats - Reuters") == normalize_title("X Beats - Yahoo")
