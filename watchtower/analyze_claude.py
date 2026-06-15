"""Optional: ask Claude for a short executive summary per market.

Only runs if ANTHROPIC_API_KEY is set. Degrades silently to {} on any error,
so the pipeline still works (and still emails) without it.
"""
from __future__ import annotations
import os


def summarize(results: list[dict], cfg: dict) -> dict[str, str]:
    if not os.getenv("ANTHROPIC_API_KEY"):
        return {}
    try:
        import anthropic
    except Exception:
        return {}

    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    by_market: dict[str, list[dict]] = {}
    for r in results:
        by_market.setdefault(r["market"], []).append(r)

    out: dict[str, str] = {}
    for market, rows in by_market.items():
        lines = "\n".join(
            f"- [{r['result'].upper()} / change:{r['change']}] {r['label']}"
            f" (task {r.get('task','?')}) — {r['detail']}"
            for r in rows
        )
        prompt = (
            f"You monitor the {market} Phoenix Gravity website (D2C water filters). "
            f"Below are this run's automated check results. Write a 2-3 sentence executive "
            f"summary for the {market} lead: call out anything that REGRESSED, anything newly "
            f"FIXED, and what still needs attention. Be specific and concise; no preamble.\n\n"
            f"{lines}"
        )
        try:
            msg = client.messages.create(
                model=model,
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )
            out[market] = "".join(
                b.text for b in msg.content if getattr(b, "type", None) == "text"
            ).strip()
        except Exception as e:
            out[market] = f"(Claude summary unavailable: {e})"
    return out
