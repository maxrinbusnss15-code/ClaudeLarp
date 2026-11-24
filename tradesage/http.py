"""HTTP client with on-disk TTL cache and retries, so repeated refreshes stay polite."""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Protocol

import requests

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)


class Http(Protocol):
    def get_text(self, url: str, ttl: int = 300, headers: dict[str, str] | None = None) -> str: ...
    def get_json(self, url: str, ttl: int = 300, headers: dict[str, str] | None = None) -> Any: ...


def sec_user_agent() -> str:
    # SEC fair-access policy requires a descriptive User-Agent with a contact.
    return os.environ.get("TRADESAGE_CONTACT", "TradeSage research tool (set TRADESAGE_CONTACT)")


class HttpClient:
    def __init__(self, cache_dir: Path | None = None, timeout: float = 15.0, retries: int = 2):
        self.cache_dir = cache_dir
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()

    def _cache_path(self, url: str) -> Path | None:
        if not self.cache_dir:
            return None
        return self.cache_dir / (hashlib.sha256(url.encode()).hexdigest() + ".json")

    def get_text(self, url: str, ttl: int = 300, headers: dict[str, str] | None = None) -> str:
        path = self._cache_path(url)
        if path and path.exists() and ttl > 0:
            try:
                cached = json.loads(path.read_text())
                if time.time() - cached["fetched_at"] < ttl:
                    return cached["body"]
            except (ValueError, KeyError):
                pass
        hdrs = {"User-Agent": BROWSER_UA, "Accept": "*/*"}
        if "sec.gov" in url:
            hdrs["User-Agent"] = sec_user_agent()
        hdrs.update(headers or {})
        last_exc: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                resp = self.session.get(url, headers=hdrs, timeout=self.timeout)
                if resp.status_code == 429 or resp.status_code >= 500:
                    raise requests.HTTPError(f"HTTP {resp.status_code}")
                resp.raise_for_status()
                body = resp.text
                if path:
                    path.write_text(json.dumps({"fetched_at": time.time(), "body": body}))
                return body
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < self.retries:
                    time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"GET {url} failed: {last_exc}")

    def get_json(self, url: str, ttl: int = 300, headers: dict[str, str] | None = None) -> Any:
        return json.loads(self.get_text(url, ttl=ttl, headers=headers))
