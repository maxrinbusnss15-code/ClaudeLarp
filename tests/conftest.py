from datetime import date, datetime, timezone

import pytest

from tradesage.config import load_config
from tradesage.demo import DemoHttp
from tradesage.engine.collector import Collector

TODAY = date(2026, 11, 24)
NOW = datetime(2026, 11, 24, 18, 0, tzinfo=timezone.utc)


@pytest.fixture
def cfg():
    return load_config("/nonexistent.toml")


@pytest.fixture
def make_collector(cfg):
    def _make(scenario="mixed", http=None):
        return Collector(http or DemoHttp(today=TODAY, scenario=scenario), cfg, now=NOW)
    return _make


class FailingHttp(DemoHttp):
    """DemoHttp that fails for any URL containing one of the given fragments."""

    def __init__(self, fail: tuple[str, ...], **kw):
        super().__init__(today=TODAY, **kw)
        self.fail = fail

    def get_text(self, url, ttl=0, headers=None):
        if any(f in url for f in self.fail):
            raise RuntimeError("simulated outage")
        return super().get_text(url, ttl, headers)
