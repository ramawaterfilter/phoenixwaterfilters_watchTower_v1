# Phoenix Gravity — Watchtower

Automated site monitor for the three Phoenix Gravity storefronts (US · UK · France).
It **crawls your live sites 3× a day**, compares each run against the previous one,
and reports what **regressed / got fixed / is new** — with **no email and no stored
credentials**. Results are surfaced two ways:

1. **The Actions run Summary** — a results table + change list right on the workflow
   run page (Actions tab → latest run).
2. **`data/last_report.html`** — a command-center dashboard (navy / market-accent, matching your CEO dashboard) committed back each run;
   open it on GitHub or download it.

Built to deploy on **GitHub Actions** (free, no server, no secrets required).

---

## What it does each run
1. Fetches the pages in `config.yaml`.
2. Runs deterministic checks tied to the audits — e.g. UK `£0.00` price gone on each PDP,
   France translator's note removed, GDPR/consent banner present, Product schema present,
   policy-typo / EN-duplicate URLs returning 301/404, robots blocking `/cart`, every PDP
   returning 200, etc.
3. Diffs against the last run → flags **FIXED / REGRESSED / NEW**.
4. *(Optional)* asks Claude for a 2–3 sentence summary per market.
5. Writes the run Summary + `data/last_report.html`, and commits the snapshot so the next
   run can diff.

## Schedule (3× daily, IST)
Set in `.github/workflows/audit.yml`. GitHub cron runs in **UTC** and is **best-effort**
(can start a few minutes late):

| You want (IST) | UTC cron |
|---|---|
| 10:00 | `30 4 * * *` |
| 13:00 | `30 7 * * *` |
| 19:00 | `30 13 * * *` |

You can also trigger a run any time from the **Actions** tab (`workflow_dispatch`).

---

## Deploy (≈5 minutes, no secrets)
1. Create a **private** GitHub repo and upload this folder (or `git push`).
   Keep it private — the report + snapshot list real, unfixed issues on your sites.
2. **Actions** tab → enable workflows → run **Phoenix Watchtower** via *Run workflow*.
3. Open the run → read the **Summary**. The styled `data/last_report.html` is committed
   back to the repo on each run.

No secrets are required. **Optional:** add `ANTHROPIC_API_KEY` (and `ANTHROPIC_MODEL`,
default `claude-sonnet-4-5`) as repo secrets to include the Claude-written per-market
summary.

### Want to be actively notified (still no email creds)?
Set `fail_on_regression: true` in `config.yaml`. When a check **regresses**, the run exits
non-zero and GitHub's own *workflow-failure* notification reaches you (GitHub emails the
repo actor / watchers natively — nothing stored in this project).

---

## Editing checks (no code needed)
Everything lives in `config.yaml`:
- **`pages:`** the URLs to fetch.
- **`checks:`** one line each. Supported `type`s:
  `text_absent`, `text_present`, `regex_absent`, `regex_present`,
  `url_status` (with `expect_status: [...]`), `jsonld_type` (with `value: Product`).
  Each check carries a `task:` id so an alert maps straight back to the tracker.

## Run locally
```bash
pip install -r requirements.txt
python -m watchtower.main          # writes data/last_report.html (open it in a browser)
# optional: export ANTHROPIC_API_KEY=... first to include the Claude summary
```

---

## Honest limits
- Deterministic checks on page HTML (+ optional Claude summary). **Not** a full human audit;
  it won't catch everything a person would.
- Can't measure field metrics like Core Web Vitals / INP (those need real-user data or a
  Lighthouse run) — keep those manual.
- Results are **pull-based**: you read them on the Actions tab / in the repo (or turn on
  `fail_on_regression` for a push notification via GitHub). There is no outbound email.
- GitHub cron is UTC and best-effort; exact 10:00 / 13:00 / 19:00 may drift a few minutes.
- Only checks the URLs in `config.yaml` — if a product slug 404s on the first run, fix that
  line.

---

## Command Center dashboard (two tabs)
`dashboard/index.html` is a single screen with two tabs, branded with the Phoenix Gravity / RAMA Group logo:

- **Execution Tracker** — your CEO task dashboard (all markets, leaderboard, discipline matrix, per-task status / %-complete / Done / remarks editing). Edits save in the browser (localStorage), per device.
- **Site Watchtower** — this monitor: a **Last Crawl Status** badge (Crawled ✓ / Stale / Not yet crawled, with the last crawl date-time in IST), KPI strip, market cards, and the filterable checks table.

**How the live data flows:** the 3×/day Action rewrites `dashboard/data.js` each run (the crawl results + timestamp) and commits it. `dashboard/index.html` and `dashboard/app.bundle.js` are static — so the Watchtower tab and Last Crawl Status stay current without a rebuild.

**Open it:** download the repo and open `dashboard/index.html` (it loads `data.js` + `app.bundle.js` from the same folder). For an always-on shared screen, serve the `dashboard/` folder from a **private** host — avoid public GitHub Pages, since the data names real unfixed issues.

© 2026 RAMA Group of Companies. All rights reserved.
