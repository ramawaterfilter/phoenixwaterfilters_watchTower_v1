"""Run a single config-defined check against a fetched page.

Returns (status, detail) where status is one of: "pass", "fail", "error".
"""
from __future__ import annotations
import json
import re
from bs4 import BeautifulSoup


def _jsonld_has_type(html: str, wanted: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    wanted_l = wanted.lower()
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.get_text() or ""
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except Exception:
            # crude fallback: the type token appears in the raw block
            if f'"@type"' in raw and wanted_l in raw.lower():
                return True
            continue
        for node in _iter_nodes(data):
            t = node.get("@type") if isinstance(node, dict) else None
            if isinstance(t, str) and t.lower() == wanted_l:
                return True
            if isinstance(t, list) and any(str(x).lower() == wanted_l for x in t):
                return True
    return False


def _iter_nodes(data):
    """Yield dict nodes from arbitrary JSON-LD (handles @graph and lists)."""
    if isinstance(data, dict):
        yield data
        if "@graph" in data and isinstance(data["@graph"], list):
            for item in data["@graph"]:
                yield from _iter_nodes(item)
    elif isinstance(data, list):
        for item in data:
            yield from _iter_nodes(item)


def run_check(chk: dict, page_url: str | None, fetcher) -> tuple[str, str]:
    t = chk.get("type")
    if not page_url:
        return "error", "no page URL configured for this check"

    # status-only check (does NOT follow redirects)
    if t == "url_status":
        st = fetcher.status(page_url)
        expect = chk.get("expect_status", [200])
        if st is None:
            return "error", "request failed (no response)"
        return ("pass" if st in expect else "fail", f"HTTP {st} (expected {expect})")

    # content checks (follow redirects, need a body)
    code, text = fetcher.get(page_url)
    if code is None:
        return "error", text.replace("__FETCH_ERROR__", "fetch error:").strip()
    if code >= 400:
        return "error", f"HTTP {code} while fetching page"

    low = text.lower()

    if t == "text_absent":
        needle = chk["needle"]
        return ("pass" if needle.lower() not in low else "fail",
                f"'{needle}' {'absent' if needle.lower() not in low else 'STILL PRESENT'}")

    if t == "text_present":
        needle = chk["needle"]
        return ("pass" if needle.lower() in low else "fail",
                f"'{needle}' {'present' if needle.lower() in low else 'NOT FOUND'}")

    if t == "regex_absent":
        hit = re.search(chk["pattern"], text, re.I)
        return ("pass" if not hit else "fail",
                "pattern absent" if not hit else f"matched: {hit.group(0)[:60]!r}")

    if t == "regex_present":
        hit = re.search(chk["pattern"], text, re.I)
        return ("pass" if hit else "fail",
                f"matched: {hit.group(0)[:60]!r}" if hit else "pattern NOT FOUND")

    if t == "jsonld_type":
        ok = _jsonld_has_type(text, chk["value"])
        return ("pass" if ok else "fail",
                f"JSON-LD @type={chk['value']} {'found' if ok else 'MISSING'}")

    return "error", f"unknown check type: {t}"
