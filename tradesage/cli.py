"""tradesage command line.

    tradesage analyze AAPL MSFT        # equity: LONG / SHORT
    tradesage options NVDA             # options: strategy + concrete contracts
    tradesage ipo                      # every upcoming / recent IPO: PARTICIPATE / AVOID
    tradesage watch AAPL --every 15    # keep decisions up to date, alert on side flips
    tradesage sources                  # list sources and check which ones are reachable

Add --demo to run the whole pipeline on synthetic data (no network needed).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone

from . import __version__
from .config import home_dir, load_config
from .engine.collector import Collector
from .engine.equity import decide_equity
from .engine.ipo import IpoAnalyzer
from .engine.options import decide_options
from .http import HttpClient
from .journal import Journal
from .models import Decision
from .report import render

DISCLAIMER = ("Paper-trading research tool. Not investment advice. Sources can be delayed or wrong; "
              "verify before acting with real money.")


def _http(args):
    if args.demo:
        from .demo import DemoHttp
        return DemoHttp(scenario=args.scenario)
    return HttpClient(cache_dir=home_dir() / "cache")


def _emit(args, decisions: list[Decision], journal: Journal | None) -> None:
    for d in decisions:
        flip = journal.append(d) if journal else None
        if args.json:
            print(json.dumps(d.to_dict(), indent=1))
        else:
            print(render(d, verbose=args.verbose, color=sys.stdout.isatty() and not args.no_color))
            print()
        if flip:
            print(f"\a*** {flip} ***", file=sys.stderr)


def run_once(args, cfg, journal) -> list[Decision]:
    collector = Collector(_http(args), cfg)
    out: list[Decision] = []
    if args.cmd in ("analyze", "options", "watch"):
        for sym in args.symbols:
            want_opts = args.cmd == "options" or getattr(args, "options", False)
            bundle = collector.equity_bundle(sym, with_options=True)
            out.append(decide_options(bundle, cfg) if want_opts else decide_equity(bundle, cfg))
    if args.cmd == "ipo" or getattr(args, "ipo", False):
        state = None if args.demo else home_dir() / "ipo_state.json"
        out += IpoAnalyzer(collector, state).scan(include_priced=not getattr(args, "upcoming_only", False),
                                                   limit=getattr(args, "limit", 20))
    return out


def cmd_sources(args, cfg) -> int:
    http = _http(args)
    c = Collector(http, cfg)
    checks = {
        "yahoo": lambda: c.price_feeds[0].history("SPY"),
        "stooq": lambda: c.price_feeds[1].history("SPY"),
        "cboe": lambda: c.cboe.index_quote("VIX"),
        "fred": lambda: c.fred.series("VIXCLS"),
        "sec_edgar": lambda: c.edgar.company("AAPL"),
        "nasdaq": lambda: IpoAnalyzer(c).calendar.month(c.now.year, c.now.month),
        **{f.name: (lambda f=f: f.headlines("SPY", "stock market")) for f in c.news},
    }
    res, fails = Collector._run(checks)
    failed = {f.source: f.error for f in fails}
    for name in checks:
        status = "OK " if name in res else "ERR"
        print(f"  [{status}] {name:<12} trust {cfg['trust'].get(name, 0):.2f}  {failed.get(name, '')}")
    return 0 if not fails else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="tradesage", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=__version__)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--demo", action="store_true", help="use synthetic offline data")
    common.add_argument("--scenario", default="mixed", choices=["mixed", "bull", "bear"], help="demo scenario")
    common.add_argument("--config", help="TOML config overriding trust/weights/risk")
    common.add_argument("--json", action="store_true")
    common.add_argument("-v", "--verbose", action="store_true", help="show every piece of evidence")
    common.add_argument("--no-color", action="store_true")
    common.add_argument("--no-journal", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("analyze", "options"):
        sp = sub.add_parser(name, parents=[common])
        sp.add_argument("symbols", nargs="+")
    ip = sub.add_parser("ipo", parents=[common])
    ip.add_argument("--upcoming-only", action="store_true")
    ip.add_argument("--limit", type=int, default=20)
    w = sub.add_parser("watch", parents=[common])
    w.add_argument("symbols", nargs="*")
    w.add_argument("--every", type=float, default=15, help="minutes between refreshes")
    w.add_argument("--iterations", type=int, default=0, help="0 = forever")
    w.add_argument("--options", action="store_true")
    w.add_argument("--ipo", action="store_true")
    sub.add_parser("sources", parents=[common])
    args = p.parse_args(argv)

    cfg = load_config(args.config)
    if args.cmd == "sources":
        return cmd_sources(args, cfg)
    if not args.json:
        print(DISCLAIMER + "\n", file=sys.stderr)
    journal = None if args.no_journal or args.demo else Journal(home_dir() / "journal.jsonl")

    if args.cmd != "watch":
        decisions = run_once(args, cfg, journal)
        _emit(args, decisions, journal)
        return 0

    if not args.symbols and not args.ipo:
        p.error("watch needs symbols and/or --ipo")
    i = 0
    while True:
        i += 1
        print(f"--- refresh #{i} at {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC ---", file=sys.stderr)
        try:
            _emit(args, run_once(args, cfg, journal), journal)
        except Exception as exc:  # noqa: BLE001 - keep watching through transient failures
            print(f"refresh failed: {exc}", file=sys.stderr)
        if args.iterations and i >= args.iterations:
            return 0
        time.sleep(max(1.0, args.every * 60))


if __name__ == "__main__":
    raise SystemExit(main())
