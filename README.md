# TradeSage

A decision engine for **stocks, options and IPOs**. It compares several trusted sources, answers a fixed set of questions, and only then **chooses a side**.

> ⚠️ Paper-trading research tool. It never sends orders to a broker. Free data sources can be delayed, rate-limited or wrong. Not investment advice.

## How a decision is made

```
 sources (fetched in parallel, cached)  ──►  evidence per question per source
                                                │  trust × confidence × freshness
                                                ▼
                     questions answered by trust-weighted consensus
                     (quorum of distinct sources, agreement and dissent reported)
                                                ▼
          required questions answered?  ── no ──►  NO_DECISION (says what's missing)
                                                │ yes
                                                ▼
           weighted score  ──►  side (LONG / SHORT / BUY_VOL / SELL_VOL)
                                + conviction, sizing, stops / concrete option legs
```

### Sources and default trust

| Source | Trust | Used for |
|---|---|---|
| SEC EDGAR (XBRL company facts, S-1/F-1/424B4 filings) | 1.00 | fundamentals, IPO confirmation, amendments, pricing |
| FRED (St. Louis Fed): VIX, 10y–2y curve, high-yield spread | 0.95 | macro regime |
| CBOE delayed quotes: full option chains, live VIX | 0.90 | positioning, implied vol, contract selection, price check |
| Nasdaq IPO calendar | 0.85 | upcoming / priced / filed deals |
| Yahoo Finance, Stooq price history (two independent vendors) | 0.70 | trend, short-term, realized vol, IPO aftermarket |
| Yahoo Finance RSS, Nasdaq RSS, Google News RSS | 0.50–0.55 | news sentiment (syndicated duplicates counted once) |

Trust, quorum, question weights and risk settings are in `tradesage/config.py` and can be overridden with a TOML file (see `tradesage.example.toml`). New sources plug in by returning `Evidence` objects for an existing question.

### Questions

| Question | Asked for | Required? |
|---|---|---|
| `data_integrity` – do ≥2 independent price feeds agree within 2 % and is data fresh? | equity, options | **yes** |
| `trend` – SMA50/200, 3/6/12-1 month momentum (from each price vendor) | equity, options | **yes** |
| `short_term` – RSI, 5-day z-score (mean reversion) | equity, options | |
| `fundamentals` – revenue YoY, net-margin trend, dilution/buybacks (SEC) | equity, options | |
| `sentiment` – headline tone across feeds, time-decayed | all | |
| `macro` – VIX level/trend (FRED and CBOE), yield curve, credit spreads | all | |
| `positioning` – put/call volume and OI, 25-delta skew | equity, options | |
| `volatility` – ATM implied vol vs 30-day realized vol | options | **yes for options** |
| `ipo_regulator` – S-1/F-1 on file, 424B4 final prospectus | IPO | **yes** |
| `ipo_deal` – size, venue, price, range width, pricing vs. remembered range, range revisions, amendment count | IPO | **yes** |
| `ipo_climate` – how the last ~15 IPOs trade vs. offer, checked on two price vendors | IPO | |
| `ipo_aftermarket` – return vs. offer, recent trend, 180-day lock-up expiry | priced IPOs | |

If a required question can't be answered, for example because the price feeds disagree or there isn't a regulatory filing, the engine returns **NO_DECISION** and says why. Otherwise it **always picks a side**, and conviction shows how strong the case is.

### Options strategy selection

| Direction \ Implied vol | cheap | fair | expensive |
|---|---|---|---|
| bullish | long call (Δ≈0.60) | bull call spread | bull put credit spread (short Δ≈0.30) |
| bearish | long put | bear put spread | bear call credit spread |
| neutral (\|score\| < 0.10) | long straddle (`BUY_VOL`) | iron condor | iron condor (`SELL_VOL`) |

Contracts come from the real chain. The engine targets about 35 DTE (20 to 60 allowed) and filters for liquidity (OI or volume, bid/ask ≤25 % of mid). Each trade shows max loss, max profit, breakevens, an estimated probability of profit, and a contract count sized to the risk budget (1 % of equity × conviction by default).

## Usage

```bash
pip install -e .            # or: python -m tradesage ...
export TRADESAGE_CONTACT="Your Name your@email"   # SEC requires a contact in the User-Agent

tradesage sources                    # which sources are reachable right now
tradesage analyze AAPL MSFT -v       # equity decision, -v shows every piece of evidence
tradesage options NVDA               # options strategy + legs
tradesage ipo                        # every upcoming / recently priced IPO
tradesage watch AAPL NVDA --options --ipo --every 15   # stay up to date; alerts on side flips
tradesage analyze AAPL --json        # machine-readable
```

Try it without network access by running on synthetic data:

```bash
python -m tradesage analyze NVDA --demo --scenario bull -v
python -m tradesage options SPY --demo --scenario bear
python -m tradesage ipo --demo
```

### Staying up to date

- Responses are cached on disk with per-type TTLs: options 5 min, prices 15 min, news 10 min, filings and IPOs 1 h, macro 6 h. Each refresh therefore gets fresh data without hammering the sources.
- `watch` re-runs on an interval. You can also schedule `tradesage ipo` and `tradesage analyze …` with cron.
- Every decision goes to `~/.tradesage/journal.jsonl` (set `TRADESAGE_HOME` to change it). A side change since the last run prints a `SIDE FLIP` alert.
- Every IPO price range seen is saved to `~/.tradesage/ipo_state.json`. When a deal prices, the engine checks whether it priced **above, within or below the original range**, a strong demand signal that no single snapshot shows. Range revisions while a deal is still upcoming are tracked the same way.

## Tests

```bash
python -m pytest -q
```

The tests run fully offline against the deterministic demo data. They cover pricing math, consensus and quorum, the integrity gate (vendor outage, corrupted vendor), graceful handling of news and macro outages, strategy selection and leg consistency, IPO range tracking, lock-up detection, the regulator gate, and journal flip detection.

## Limitations

- "All trusted sources in the world" isn't reachable for free. This uses free public endpoints, which can change format or block automated clients. Paid feeds (Polygon, Refinitiv, Bloomberg, OPRA) can be added as more sources.
- The signals are transparent heuristics, not a backtested model. Paper-trade it and check the journal before trusting it.
