"""Render run results as (a) a command-center HTML dashboard and (b) a Markdown
summary for the GitHub Actions run page. No email — results are pulled from the
repo / the Actions Summary tab.
"""
from __future__ import annotations

# market accents (match the CEO dashboard)
_ACCENT = {"US": "#2563EB", "UK": "#B91C1C", "France": "#0E8C6E"}
_MARKET_ORDER = ["US", "UK", "France"]

_BADGE = {"pass": "#0E8C6E", "fail": "#B91C1C", "error": "#B45309"}
_BADGE_LABEL = {"pass": "PASS", "fail": "FAIL", "error": "ERROR"}
_DOT = {"pass": "#0E8C6E", "fail": "#B91C1C", "error": "#B45309"}
_CHANGE = {
    "fixed":     ("#0E8C6E", "\u2714 FIXED"),
    "regressed": ("#B91C1C", "\u25B2 REGRESSED"),
    "new":       ("#2563EB", "\u2022 NEW"),
    "same":      ("#6B7280", "\u2014"),
}
_MD_CHANGE = {"fixed": "\u2705 fixed", "regressed": "\U0001F534 regressed", "new": "\U0001F195 new", "same": "\u2014"}
_MD_RESULT = {"pass": "\U0001F7E2 pass", "fail": "\U0001F534 fail", "error": "\U0001F7E0 error"}


def _counts(results):
    return {
        "total": len(results),
        "pass": sum(1 for r in results if r["result"] == "pass"),
        "fail": sum(1 for r in results if r["result"] == "fail"),
        "error": sum(1 for r in results if r["result"] == "error"),
        "regressed": sum(1 for r in results if r["change"] == "regressed"),
        "fixed": sum(1 for r in results if r["change"] == "fixed"),
        "new": sum(1 for r in results if r["change"] == "new"),
    }


def _ordered(results):
    return sorted(results, key=lambda r: (r["result"] != "fail", r["change"] != "regressed", r["market"], r["id"]))


# ============================== CSS / JS ==============================
_CSS = """
*{box-sizing:border-box}
body{margin:0;background:#EEF2F8;color:#111827;font-family:'Space Grotesk',system-ui,-apple-system,Arial,sans-serif}
.wt{max-width:1080px;margin:0 auto;padding:20px}
.top{background:#0B1F38;color:#fff;border-radius:14px;padding:20px 24px;display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:12px}
.top h1{margin:0;font-size:22px;font-weight:700;letter-spacing:.04em}
.top .sub{color:#9fb3c8;font-size:13px;margin-top:5px}
.top .ts{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:12px;color:#cdd9e5;text-align:right;line-height:1.5}
.kpis{display:grid;grid-template-columns:1.4fr 1fr 1fr 1fr 1fr;gap:12px;margin-top:16px}
.card{background:#fff;border:1px solid #E5E9F0;border-radius:12px;padding:14px 16px}
.kpi .n{font-size:30px;font-weight:700;line-height:1}
.kpi .l{font-size:11px;color:#6B7280;text-transform:uppercase;letter-spacing:.06em;margin-top:7px}
.health{display:flex;flex-direction:column;justify-content:center}
.health .score{font-size:42px;font-weight:700;line-height:1}
.health .band{align-self:flex-start;margin-top:9px;padding:3px 11px;border-radius:999px;font-size:12px;font-weight:700;color:#fff}
.health .l{font-size:11px;color:#6B7280;text-transform:uppercase;letter-spacing:.06em;margin-top:8px}
.markets{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-top:12px}
.mcard{background:#fff;border:1px solid #E5E9F0;border-top:4px solid #999;border-radius:12px;padding:14px 16px}
.mcard h3{margin:0;font-size:15px;font-weight:700}
.mcard .tally{font-family:'JetBrains Mono',monospace;font-size:12px;color:#6B7280;margin:3px 0 6px}
.mcard .note{font-size:12px;color:#4B5563;font-style:italic;margin:0 0 8px;line-height:1.45}
.mcard ul{margin:0;padding:0;list-style:none}
.mcard li{font-size:12.5px;padding:6px 0;border-top:1px dashed #E5E9F0;display:flex;gap:7px;line-height:1.35}
.mcard li .dot{flex:none;width:7px;height:7px;border-radius:50%;margin-top:5px}
.mcard li .tk{color:#9ca3af;font-family:'JetBrains Mono',monospace;font-size:10.5px}
.mcard .clean{color:#0E8C6E;font-size:12.5px;font-weight:600;padding-top:4px}
.sect{font-size:12px;font-weight:700;color:#6B7280;text-transform:uppercase;letter-spacing:.08em;margin:20px 0 0}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:9px}
.chip{font-size:12px;padding:5px 11px;border-radius:999px;border:1px solid #E5E9F0;background:#fff;color:#374151}
.chip.lead{font-weight:700;color:#fff}
.filterbar{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}
.fbtn{font-size:12px;padding:6px 13px;border-radius:8px;border:1px solid #E5E9F0;background:#fff;cursor:pointer;font-family:inherit}
.fbtn.active{background:#0B1F38;color:#fff;border-color:#0B1F38}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #E5E9F0;border-radius:12px;overflow:hidden}
thead th{background:#F8FAFC;text-align:left;font-size:11px;color:#6B7280;text-transform:uppercase;letter-spacing:.05em;padding:9px 12px}
tbody td{padding:9px 12px;border-top:1px solid #EEF1F6;font-size:13px;vertical-align:top}
.mtag{font-weight:700;font-size:12px}
.badge{color:#fff;border-radius:5px;padding:2px 8px;font-size:11px;font-weight:700;font-family:'JetBrains Mono',monospace;white-space:nowrap}
.chg{font-size:11px;font-weight:700;white-space:nowrap}
.det{color:#6B7280;font-family:'JetBrains Mono',monospace;font-size:11px;margin-top:3px}
.foot{color:#9ca3af;font-size:11px;margin-top:16px;text-align:center;line-height:1.5}
@media(max-width:820px){.kpis{grid-template-columns:1fr 1fr 1fr}.markets{grid-template-columns:1fr}}
"""

_JS = """
var btns=document.querySelectorAll('.fbtn');
var rows=document.querySelectorAll('tbody tr');
function applyFilter(f){
  for(var i=0;i<rows.length;i++){
    var r=rows[i],show=true;
    if(f==='fail'){show=(r.getAttribute('data-result')==='fail'||r.getAttribute('data-result')==='error');}
    else if(f==='regressed'){show=(r.getAttribute('data-change')==='regressed');}
    else if(f!=='all'){show=(r.getAttribute('data-market')===f);}
    r.style.display=show?'':'none';
  }
}
for(var i=0;i<btns.length;i++){
  btns[i].addEventListener('click',function(){
    for(var j=0;j<btns.length;j++){btns[j].classList.remove('active');}
    this.classList.add('active');
    applyFilter(this.getAttribute('data-filter'));
  });
}
"""


# ============================== HTML builders ==============================
def _market_card(market, results, summaries):
    accent = _ACCENT.get(market, "#334155")
    mrows = [r for r in results if r["market"] == market]
    p = sum(1 for r in mrows if r["result"] == "pass")
    issues = [r for r in mrows if r["result"] in ("fail", "error")]
    issues.sort(key=lambda r: r["result"] != "fail")
    note = (summaries or {}).get(market, "")
    note_html = f'<p class="note">{note}</p>' if note else ""
    if issues:
        items = "\n".join(
            f'<li><span class="dot" style="background:{_DOT.get(r["result"],"#999")}"></span>'
            f'<span>{r["label"]} <span class="tk">{r.get("task","")}</span></span></li>'
            for r in issues
        )
        body = f"<ul>{items}</ul>"
    else:
        body = f'<div class="clean">\u2714 all {len(mrows)} checks passing</div>'
    return (
        f'<div class="mcard" style="border-top-color:{accent}">'
        f'<h3 style="color:{accent}">{market}</h3>'
        f'<div class="tally">{p}/{len(mrows)} passing \u00b7 {len(issues)} need attention</div>'
        f"{note_html}{body}</div>"
    )


def _change_chips(results):
    c = _counts(results)
    chips = []
    if c["regressed"]:
        chips.append(f'<span class="chip lead" style="background:#B91C1C">\u25B2 {c["regressed"]} regressed</span>')
    if c["fixed"]:
        chips.append(f'<span class="chip lead" style="background:#0E8C6E">\u2714 {c["fixed"]} fixed</span>')
    if c["new"]:
        chips.append(f'<span class="chip lead" style="background:#2563EB">\u2022 {c["new"]} new</span>')
    # name the regressed + fixed items
    for r in _ordered(results):
        if r["change"] == "regressed":
            chips.append(f'<span class="chip" style="border-color:#FBC4C4">\u25B2 {r["market"]} \u00b7 {r["label"]}</span>')
    for r in results:
        if r["change"] == "fixed":
            chips.append(f'<span class="chip" style="border-color:#B7E3D3">\u2714 {r["market"]} \u00b7 {r["label"]}</span>')
    if not (c["regressed"] or c["fixed"] or c["new"]):
        chips.append('<span class="chip">No changes since the last run</span>')
    return '<div class="chips">' + "".join(chips) + "</div>"


def _table_rows(results):
    out = []
    for r in _ordered(results):
        bcol = _BADGE.get(r["result"], "#6B7280")
        blab = _BADGE_LABEL.get(r["result"], r["result"].upper())
        ccol, clab = _CHANGE.get(r["change"], ("#6B7280", r["change"]))
        acc = _ACCENT.get(r["market"], "#334155")
        out.append(
            f'<tr data-market="{r["market"]}" data-result="{r["result"]}" data-change="{r["change"]}">'
            f'<td><span class="mtag" style="color:{acc}">{r["market"]}</span></td>'
            f'<td>{r["label"]}<div class="det">{r.get("task","")} \u00b7 {r["detail"]}</div></td>'
            f'<td><span class="badge" style="background:{bcol}">{blab}</span></td>'
            f'<td><span class="chg" style="color:{ccol}">{clab}</span></td>'
            "</tr>"
        )
    return "\n".join(out)


def build_html(results, summaries, run_label):
    c = _counts(results)
    total = c["total"] or 1
    passed = c["pass"]
    health = round(100 * passed / total)
    if health >= 90:
        band_l, band_c = "HEALTHY", "#0E8C6E"
    elif health >= 75:
        band_l, band_c = "WATCH", "#B45309"
    else:
        band_l, band_c = "AT RISK", "#B91C1C"

    kpis = (
        f'<div class="card health"><div class="score" style="color:{band_c}">{health}<span style="font-size:18px;color:#9ca3af">%</span></div>'
        f'<span class="band" style="background:{band_c}">{band_l}</span><div class="l">Checks passing</div></div>'
        f'<div class="card kpi"><div class="n">{c["total"]}</div><div class="l">Total checks</div></div>'
        f'<div class="card kpi"><div class="n" style="color:#B91C1C">{c["fail"]}</div><div class="l">Failing</div></div>'
        f'<div class="card kpi"><div class="n" style="color:#B45309">{c["error"]}</div><div class="l">Errors</div></div>'
        f'<div class="card kpi"><div class="n" style="color:#B91C1C">{c["regressed"]}</div><div class="l">Regressed</div></div>'
    )
    markets = "".join(_market_card(m, results, summaries) for m in _MARKET_ORDER if any(r["market"] == m for r in results))
    # include any markets not in the default order
    for m in sorted({r["market"] for r in results}):
        if m not in _MARKET_ORDER:
            markets += _market_card(m, results, summaries)

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Phoenix Watchtower</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=JetBrains+Mono:wght@400;600&display=swap">
<style>{_CSS}</style>
</head><body>
<div class="wt">
  <header class="top">
    <div><h1>PHOENIX WATCHTOWER</h1>
    <div class="sub">Automated site monitor &middot; US &middot; UK &middot; France &middot; 3&times;/day</div></div>
    <div class="ts">{run_label}<br>{c['total']} checks &middot; {c['fail']} failing &middot; {c['error']} errors</div>
  </header>
  <section class="kpis">{kpis}</section>
  <section class="markets">{markets}</section>
  <div class="sect">Changes since last run</div>
  {_change_chips(results)}
  <div class="sect">All checks</div>
  <div class="filterbar">
    <button class="fbtn active" data-filter="all">All</button>
    <button class="fbtn" data-filter="fail">Failing / errors</button>
    <button class="fbtn" data-filter="regressed">Regressed</button>
    <button class="fbtn" data-filter="US">US</button>
    <button class="fbtn" data-filter="UK">UK</button>
    <button class="fbtn" data-filter="France">France</button>
  </div>
  <table>
    <thead><tr><th>Market</th><th>Check</th><th>Status</th><th>Vs last</th></tr></thead>
    <tbody>{_table_rows(results)}</tbody>
  </table>
  <div class="foot">Automated deterministic checks on the live sites, 3&times;/day (10:00 / 13:00 / 19:00 IST).<br>
  A strong early-warning net &mdash; not a substitute for a full human audit.</div>
</div>
<script>{_JS}</script>
</body></html>"""


# ============================== Markdown (Actions summary) ==============================
def build_markdown(results, summaries, run_label):
    c = _counts(results)
    lines = [
        f"## Phoenix Watchtower \u2014 {run_label}",
        "",
        f"**{c['total']} checks** \u00b7 \U0001F534 {c['fail']} failing \u00b7 \U0001F7E0 {c['error']} errors \u00b7 "
        f"\u25B2 {c['regressed']} regressed \u00b7 \u2705 {c['fixed']} fixed \u00b7 \U0001F195 {c['new']} new",
        "",
    ]
    changed = [r for r in results if r["change"] in ("regressed", "new", "fixed")]
    if changed:
        lines.append("### Changes since last run")
        for r in sorted(changed, key=lambda r: r["change"]):
            lines.append(f"- {_MD_CHANGE[r['change']]} \u2014 **{r['market']}** \u00b7 {r['label']} (`{r.get('task','')}`)")
        lines.append("")
    if summaries:
        lines.append("### Notes")
        for m in sorted(summaries):
            if summaries[m]:
                lines.append(f"- **{m}:** {summaries[m]}")
        lines.append("")
    lines.append("### All checks")
    lines.append("| Market | Check | Status | Vs last | Detail |")
    lines.append("|---|---|---|---|---|")
    for r in _ordered(results):
        detail = r["detail"].replace("|", "\\|")
        lines.append(
            f"| {r['market']} | {r['label']} | {_MD_RESULT.get(r['result'], r['result'])} "
            f"| {_MD_CHANGE.get(r['change'], r['change'])} | {detail} |"
        )
    return "\n".join(lines) + "\n"
