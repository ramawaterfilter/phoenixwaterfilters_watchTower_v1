"""Fetch pages once per run and cache them."""
from __future__ import annotations
import requests


class Fetcher:
    def __init__(self, user_agent: str = "PhoenixWatchtower/1.0", timeout: int = 25):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self._body_cache: dict[str, tuple[int | None, str]] = {}
        self._status_cache: dict[str, int | None] = {}

    def get(self, url: str) -> tuple[int | None, str]:
        """Return (status_code, text) following redirects. Cached per run."""
        if url in self._body_cache:
            return self._body_cache[url]
        try:
            r = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            result = (r.status_code, r.text or "")
        except requests.RequestException as e:
            result = (None, f"__FETCH_ERROR__ {e}")
        self._body_cache[url] = result
        return result

    def status(self, url: str) -> int | None:
        """Return the FIRST status code without following redirects. Cached per run."""
        if url in self._status_cache:
            return self._status_cache[url]
        try:
            r = self.session.get(url, timeout=self.timeout, allow_redirects=False)
            code = r.status_code
        except requests.RequestException:
            code = None
        self._status_cache[url] = code
        return code
