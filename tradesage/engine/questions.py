"""The questions that must be answered before any decision is taken."""

QUESTIONS: dict[str, str] = {
    "data_integrity": "Do independent price feeds agree on the current price, and is the data fresh?",
    "trend": "What is the medium/long-term price trend (moving averages, 3-12 month momentum)?",
    "short_term": "Is the price stretched short-term (overbought / oversold)?",
    "fundamentals": "Are the company's reported financials (SEC filings) improving or deteriorating?",
    "sentiment": "What is the tone of recent news across independent outlets?",
    "macro": "Is the market-wide regime risk-on or risk-off (VIX, yield curve, credit spreads)?",
    "positioning": "How are options traders positioned (put/call ratios, skew)?",
    "volatility": "Is option-implied volatility cheap or expensive versus realized volatility?",
    "ipo_regulator": "Is the offering confirmed by a regulatory filing (SEC S-1/F-1/424B)?",
    "ipo_deal": "Is the deal itself attractive (size, exchange, price, pricing vs. range, amendments)?",
    "ipo_climate": "How have recent IPOs traded versus their offer price (hot or cold IPO market)?",
    "ipo_aftermarket": "For already-listed IPOs: how is it trading, and is a lock-up expiry near?",
}
