"""Load manually-imported audit issues from audits/*.csv.

The fix workflow lives in GitHub: edit a row's `status` cell (Open -> Fixed) and
commit; the next crawl run reflects it on the dashboard. No admin UI, no login.

Tolerant parser: only an issue/title column is required. Common header names are
mapped automatically (case-insensitive); unknown columns are ignored. Files whose
name starts with "_" (e.g. _TEMPLATE.csv) are skipped.
"""
from __future__ import annotations
import csv
import glob
import os
import pathlib
import re

# canonical field -> accepted header aliases (normalised: lowercase, alnum+spaces)
ALIASES = {
    "id":       ["id", "ref", "key"],
    "market":   ["market", "region", "country", "site"],
    "area":     ["area", "category", "type", "section", "department", "dept"],
    "issue":    ["issue", "title", "problem", "finding", "summary", "name", "check"],
    "detail":   ["detail", "details", "description", "desc", "recommendation", "page", "url"],
    "severity": ["severity", "priority", "sev", "impact"],
    "source":   ["source", "audit", "origin"],
    "owner":    ["owner", "assignee", "responsible"],
    "status":   ["status", "state", "fix", "fixed"],
    "note":     ["note", "notes", "comment", "resolution", "remarks"],
    "updated":  ["updated", "date", "last update", "lastupdate"],
}

STATUS_MAP = {
    "": "open", "open": "open", "new": "open", "todo": "open",
    "in progress": "in_progress", "inprogress": "in_progress", "wip": "in_progress",
    "doing": "in_progress", "started": "in_progress",
    "fixed": "fixed", "done": "fixed", "resolved": "fixed", "closed": "fixed",
    "complete": "fixed", "completed": "fixed", "yes": "fixed",
    "wontfix": "wontfix", "wont fix": "wontfix", "ignore": "wontfix", "ignored": "wontfix",
    "muted": "muted", "mute": "muted", "na": "muted",
}


def _norm(h: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", (h or "").strip().lower())


def _build_map(headers):
    nh = {_norm(h): h for h in headers}
    m = {}
    for canon, aliases in ALIASES.items():
        for a in aliases:
            if a in nh:
                m[canon] = nh[a]
                break
    return m


def _norm_status(v: str) -> str:
    return STATUS_MAP.get(_norm(v), "open")


def load_audit_issues(root) -> list[dict]:
    folder = pathlib.Path(root) / "audits"
    out: list[dict] = []
    if not folder.exists():
        return out
    for fp in sorted(glob.glob(str(folder / "*.csv"))):
        fname = os.path.basename(fp)
        if fname.startswith("_"):
            continue
        try:
            with open(fp, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    continue
                m = _build_map(reader.fieldnames)
                if "issue" not in m:
                    print(f"[warn] {fname}: no recognizable issue/title column — skipped")
                    continue
                stem = re.sub(r"[^A-Za-z0-9]+", "-", fname.rsplit(".", 1)[0]).strip("-")[:18]
                for i, row in enumerate(reader, start=1):
                    def g(canon, default=""):
                        col = m.get(canon)
                        return (row.get(col) or "").strip() if col else default
                    issue = g("issue")
                    if not issue:
                        continue
                    out.append({
                        "id": g("id") or f"{stem}-{i:03d}",
                        "market": g("market") or "\u2014",
                        "area": g("area"),
                        "issue": issue,
                        "detail": g("detail"),
                        "severity": g("severity").upper(),
                        "source": g("source") or fname,
                        "owner": g("owner"),
                        "status": _norm_status(g("status")),
                        "note": g("note"),
                        "updated": g("updated"),
                        "file": fname,
                    })
        except Exception as e:
            print(f"[warn] could not parse {fname}: {e}")
    return out
