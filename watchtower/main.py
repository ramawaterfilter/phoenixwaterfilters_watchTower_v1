"""Phoenix Watchtower entrypoint (no email — results are pulled from the repo / Actions).

Flow:  load config -> run all checks -> diff vs last snapshot
       -> (optional) Claude summary -> write data/last_report.html
       -> write the GitHub Actions run Summary -> save snapshot
       -> (optional) exit non-zero on regression so GitHub notifies you.

Run locally:   python -m watchtower.main
In GitHub:     scheduled 3x/day by .github/workflows/audit.yml
"""
from __future__ import annotations
import os
import sys
import json
import pathlib
import datetime

import yaml

from . import crawl
from . import checks as checkmod
from . import report as reportmod
from . import analyze_claude
from . import audits

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SNAP = DATA / "last_snapshot.json"
REPORT = DATA / "last_report.html"
DASH_DATA = ROOT / "dashboard" / "data.js"


def _load_config() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


def _load_prev() -> dict[str, str]:
    if not SNAP.exists():
        return {}
    try:
        data = json.loads(SNAP.read_text(encoding="utf-8"))
        return {r["id"]: r["result"] for r in data.get("results", [])}
    except Exception:
        return {}


def _write_step_summary(markdown: str) -> None:
    """Append to the GitHub Actions run Summary if running in Actions."""
    path = os.getenv("GITHUB_STEP_SUMMARY")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(markdown)
    except Exception as e:
        print(f"[warn] could not write step summary: {e}")


def main() -> None:
    DATA.mkdir(exist_ok=True)
    cfg = _load_config()
    run = cfg.get("run", {})
    pages = cfg.get("pages", {})
    run_label = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    fetcher = crawl.Fetcher(
        user_agent=run.get("user_agent", "PhoenixWatchtower/1.0"),
        timeout=int(run.get("timeout_seconds", 25)),
    )

    # 1) run every check
    results: list[dict] = []
    for chk in cfg.get("checks", []):
        page_url = pages.get(chk.get("page"))
        status, detail = checkmod.run_check(chk, page_url, fetcher)
        results.append({
            "id": chk["id"],
            "market": chk["market"],
            "label": chk["label"],
            "task": chk.get("task", ""),
            "page": chk.get("page", ""),
            "result": status,
            "detail": detail,
        })

    # 2) diff vs previous snapshot
    prev = _load_prev()
    for r in results:
        was, now = prev.get(r["id"]), r["result"]
        if was is None:
            r["change"] = "new"
        elif was == now:
            r["change"] = "same"
        elif was == "fail" and now == "pass":
            r["change"] = "fixed"
        elif was == "pass" and now == "fail":
            r["change"] = "regressed"
        else:
            r["change"] = "changed"

    # 3) optional Claude per-market summary (no-op without ANTHROPIC_API_KEY)
    try:
        summaries = analyze_claude.summarize(results, cfg)
    except Exception as e:
        print(f"[warn] Claude summary skipped: {e}")
        summaries = {}

    # 4) write outputs
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # 4a) the Command Center dashboard reads this file (dashboard/index.html + app.bundle.js are static)
    slim = [{k: r.get(k) for k in ("id", "market", "label", "task", "result", "change", "detail")} for r in results]
    audit_issues = audits.load_audit_issues(ROOT)   # imported from /audits/*.csv; status managed in GitHub
    payload = {"ts": ts, "generated": run_label, "results": slim, "audit_issues": audit_issues}
    DASH_DATA.parent.mkdir(parents=True, exist_ok=True)
    DASH_DATA.write_text("window.__WATCHTOWER__ = " + json.dumps(payload, ensure_ascii=False) + ";\n", encoding="utf-8")

    # 4b) the GitHub Actions run Summary (Markdown)
    _write_step_summary(reportmod.build_markdown(results, summaries, run_label))

    # 5) persist snapshot for the next run's diff
    SNAP.write_text(json.dumps({"ts": ts, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")

    regressed = [r["id"] for r in results if r["change"] == "regressed"]
    fails = [r["id"] for r in results if r["result"] == "fail"]
    print(f"[summary] {len(results)} checks | failing: {len(fails)} | regressed: {regressed or 'none'}")
    print(f"[output] dashboard data -> {DASH_DATA}")

    # 6) optional: fail the run on regression so GitHub's native notification fires
    if regressed and bool(run.get("fail_on_regression", False)):
        print(f"[fail_on_regression] {len(regressed)} regression(s) — exiting non-zero")
        sys.exit(1)


if __name__ == "__main__":
    main()
