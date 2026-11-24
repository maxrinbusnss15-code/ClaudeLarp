from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

from ..http import Http


@dataclass
class Headline:
    source: str
    title: str
    published: datetime
    link: str


def _parse_rss(source: str, xml_text: str) -> list[Headline]:
    root = ET.fromstring(xml_text)
    out = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        pub = item.findtext("pubDate")
        try:
            when = parsedate_to_datetime(pub) if pub else datetime.now(timezone.utc)
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            when = datetime.now(timezone.utc)
        if title:
            out.append(Headline(source, title, when, item.findtext("link") or ""))
    return out


class RssFeed:
    def __init__(self, name: str, url_template: str, http: Http, ttl: int = 600):
        self.name, self.url_template, self.http, self.ttl = name, url_template, http, ttl

    def headlines(self, symbol: str, query: str) -> list[Headline]:
        url = self.url_template.format(symbol=quote_plus(symbol), query=quote_plus(query))
        return _parse_rss(self.name, self.http.get_text(url, ttl=self.ttl))


def default_feeds(http: Http, ttl: int = 600) -> list[RssFeed]:
    return [
        RssFeed("yahoo_rss", "https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US", http, ttl),
        RssFeed("nasdaq_rss", "https://www.nasdaq.com/feed/rssoutbound?symbol={symbol}", http, ttl),
        RssFeed("google_news", "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en", http, ttl),
    ]
