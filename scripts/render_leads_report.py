"""Renderar den fullständiga leads-rapporten ur en live-körnings JSON.

    python scripts/render_leads_report.py docs/live-tests/leads-<stamp>.json

Separat från run_live_tests.py så att rapporten kan byggas om utan att köra
72 skarpa API-anrop igen. Rapporten innehåller VARJE stegs kompletta utdata i
båda thinking-lägena — det var det uttryckliga kravet, och sammanfattningar
skulle göra hela jämförelsen omöjlig att granska.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "snajp-support"))

MODES = ("disabled", "enabled")
MODE_LABEL = {"disabled": "AV", "enabled": "PÅ"}


def _fence(text: str, lang: str = "") -> list[str]:
    """Kodstaket som tål att innehållet självt innehåller ```."""
    body = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False, indent=2)
    ticks = "```"
    while ticks in body:
        ticks += "`"
    return [f"{ticks}{lang}", body.rstrip(), ticks, ""]


def _phase(record: dict, phase: str) -> dict | None:
    return record.get(phase) if isinstance(record.get(phase), dict) else None


def _totals(record: dict) -> dict:
    out = {"tokens_in": 0, "tokens_out": 0, "reasoning": 0, "ms": 0, "steps": 0, "retries": 0}
    for phase in ("research", "draft"):
        data = _phase(record, phase)
        if not data:
            continue
        out["tokens_in"] += data.get("tokens_in", 0)
        out["tokens_out"] += data.get("tokens_out", 0)
        out["reasoning"] += data.get("reasoning_tokens", 0)
        out["ms"] += data.get("latency_ms", 0)
        out["steps"] += len(data.get("step_log", []))
        out["retries"] += sum(1 for s in data.get("step_log", []) if s.get("attempts", 1) > 1)
    return out


def _errors(record: dict) -> list[str]:
    return [record[k] for k in ("research_error", "draft_error") if k in record]


def render(payload: dict) -> str:
    runs = payload["snajp"]
    prospects = payload["prospects"]
    modes = [m for m in MODES if m in payload["modes"]]

    L: list[str] = [
        "# Leads: thinking PÅ vs AV — fullständig jämförelse",
        "",
        f"Tenant: **{payload['tenant']}** · Prospekt: **{', '.join(prospects)}** · "
        f"Lägen: **{', '.join(MODE_LABEL[m] for m in modes)}**",
        "",
        f"Onboarding saknas: `{payload['onboarding_missing'] or 'inget'}` · "
        f"kontextpaket {payload['context_pack_chars']} tecken",
        "",
        "Varje körning = 8 research-steg + 4 outreach-steg, ett LLM-anrop per steg.",
        "",
        "> **Detta dokument är GENERERAT rådata** — det skrivs över av nästa körning.",
        "> Slutsatserna, och de två kundvända fynden körningen avslöjade, står i",
        "> [`THINKING_MODE_COMPARISON.md` §8](THINKING_MODE_COMPARISON.md).",
        "> Analys och rådata hålls isär med flit: förra rundans slutsatser fick",
        "> korrigeras två gånger, och då ska rätt fil vara den som ändras.",
        "",
        "---",
        "",
        "## 1. Sammanfattning per körning",
        "",
        "| Prospekt | Thinking | Steg | Omförsök | in-tok | ut-tok | reasoning-tok | Latens | Kvalificerad | ICP | Köad |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for prospect in prospects:
        for mode in modes:
            record = runs.get(f"{prospect}::{mode}")
            if not record:
                continue
            errs = _errors(record)
            if errs:
                L.append(f"| {prospect} | {MODE_LABEL[mode]} | FEL | — | — | — | — | — | — | — | {errs[0][:40]} |")
                continue
            t = _totals(record)
            research, draft = _phase(record, "research") or {}, _phase(record, "draft") or {}
            L.append(
                f"| {prospect} | {MODE_LABEL[mode]} | {t['steps']} | {t['retries']} | "
                f"{t['tokens_in']} | {t['tokens_out']} | {t['reasoning']} | {t['ms'] / 1000:.0f}s | "
                f"{'JA' if research.get('qualified') else 'nej'} | {research.get('icp_fit', '—')} | "
                f"{'JA' if draft.get('queued') else 'NEJ'} |"
            )

    # -- Aggregat per läge -------------------------------------------------
    L += ["", "## 2. Aggregat per läge", "",
          "| Läge | Körningar | in-tok | ut-tok | reasoning-tok | Latens totalt | Latens/körning |",
          "|---|---|---|---|---|---|---|"]
    agg = {}
    for mode in modes:
        rows = [runs[f"{p}::{mode}"] for p in prospects if f"{p}::{mode}" in runs and not _errors(runs[f"{p}::{mode}"])]
        totals = [_totals(r) for r in rows]
        agg[mode] = {
            "n": len(rows),
            "tokens_in": sum(t["tokens_in"] for t in totals),
            "tokens_out": sum(t["tokens_out"] for t in totals),
            "reasoning": sum(t["reasoning"] for t in totals),
            "ms": sum(t["ms"] for t in totals),
        }
        a = agg[mode]
        L.append(
            f"| {MODE_LABEL[mode]} | {a['n']} | {a['tokens_in']} | {a['tokens_out']} | "
            f"{a['reasoning']} | {a['ms'] / 1000:.0f}s | "
            f"{a['ms'] / 1000 / max(a['n'], 1):.0f}s |"
        )

    if len(modes) == 2 and agg["disabled"]["n"] and agg["enabled"]["n"]:
        d, e = agg["disabled"], agg["enabled"]
        def _x(a, b):
            return f"{b / a:.1f}x" if a else "—"
        L += ["", f"**PÅ vs AV:** ut-tokens {_x(d['tokens_out'], e['tokens_out'])}, "
                  f"latens {_x(d['ms'], e['ms'])}, "
                  f"reasoning-tokens {e['reasoning']} mot {d['reasoning']} "
                  f"(AV ska vara exakt 0 — annars bet toggeln inte).", ""]

    # -- Per steg ----------------------------------------------------------
    L += ["", "## 3. Per skill-steg — kostnad och läge", "",
          "Bevisar att thinking-läget nådde VARJE anrop (kolumnen `läge`) och att "
          "hela skillen injicerades (`injicerat`, jämför skill-audit).", ""]
    for prospect in prospects:
        L += [f"### {prospect}", "",
              "| # | Skill | Läge | Försök | in | ut | reasoning | injicerat | ms | Eskalerad |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for mode in modes:
            record = runs.get(f"{prospect}::{mode}")
            if not record or _errors(record):
                continue
            index = 0
            for phase in ("research", "draft"):
                data = _phase(record, phase)
                for entry in (data or {}).get("step_log", []):
                    index += 1
                    L.append(
                        f"| {index} | `{entry['skill']}` | {MODE_LABEL[entry['thinking_mode']]} | "
                        f"{entry['attempts']} | {entry['tokens_in']} | {entry['tokens_out']} | "
                        f"{entry['reasoning_tokens']} | {entry['injected_chars']} | "
                        f"{entry['latency_ms']} | {'JA' if entry['escalated'] else '-'} |"
                    )
        L.append("")

    # -- Beslutsskillnader -------------------------------------------------
    L += ["---", "", "## 3b. Skiljde lägena sig i BESLUT, inte bara i kostnad?", "",
          "Den avgörande frågan. Kostar thinking mer OCH ger ett annat svar, eller "
          "kostar det bara mer? Fälten nedan är de beslut research-kedjan faktiskt fattar.", "",
          "| Prospekt | Fält | AV | PÅ | Skiljer |", "|---|---|---|---|---|"]

    def _pick(record):
        research = _phase(record or {}, "research") or {}
        outputs = {e["skill"]: e.get("output", {}) for e in research.get("step_outputs", [])}
        offer = (outputs.get("mk:offers") or {}).get("offer") or {}
        draft = _phase(record or {}, "draft") or {}
        return {
            "qualified": research.get("qualified"),
            "icp_fit": research.get("icp_fit"),
            "erbjudandenamn": offer.get("name"),
            "cta": offer.get("cta"),
            "svagaste spak": (outputs.get("mk:offers") or {}).get("weakest_lever"),
            "offer_confidence": (outputs.get("mk:ab-testing") or {}).get("offer_confidence"),
            "ämnesrad": draft.get("subject"),
            "utkast tecken": len(draft.get("body") or ""),
        }

    for prospect in prospects:
        left = _pick(runs.get(f"{prospect}::disabled"))
        right = _pick(runs.get(f"{prospect}::enabled"))
        for field in left:
            a, b = left[field], right[field]
            same = "=" if str(a) == str(b) else "**JA**"
            L.append(
                f"| {prospect} | {field} | {str(a)[:90]} | {str(b)[:90]} | {same} |"
            )
    L.append("")

    # -- Slutliga utkast sida vid sida -------------------------------------
    L += ["---", "", "## 4. Slutliga mejlutkast — sida vid sida", ""]
    for prospect in prospects:
        L += [f"### {prospect}", ""]
        for mode in modes:
            record = runs.get(f"{prospect}::{mode}")
            draft = _phase(record or {}, "draft")
            L += [f"**Thinking {MODE_LABEL[mode]}**", ""]
            if not draft:
                L += [f"_Ingen utdata: {(_errors(record or {}) or ['okänt fel'])[0]}_", ""]
                continue
            L += [f"Ämne: `{draft.get('subject', '')}`", ""]
            L += _fence(draft.get("body", ""))
            L += [
                f"Köad: **{draft.get('queued')}** · eskalerad: **{draft.get('escalated')}**"
                + (f" ({draft.get('escalation_reason')})" if draft.get("escalated") else ""),
                "",
            ]

    # -- Fullständig utdata per steg ---------------------------------------
    L += ["---", "", "## 5. Fullständig utdata — varje steg, varje läge", "",
          "Ingenting är sammanfattat här. Detta är rådatan.", ""]
    for prospect in prospects:
        L += [f"## {prospect}", ""]
        for mode in modes:
            record = runs.get(f"{prospect}::{mode}")
            if not record:
                continue
            L += [f"### {prospect} — thinking {MODE_LABEL[mode]}", ""]
            if _errors(record):
                L += [f"**FEL:** `{_errors(record)[0]}`", ""]
                continue
            research = _phase(record, "research")
            if research:
                L += [
                    f"Källor: `{research.get('scraped_sources')}` · "
                    f"{research.get('source_chars')} tecken · fel: `{research.get('scrape_errors')}`",
                    "",
                ]
            for phase, title in (("research", "Fas B — research"), ("draft", "Fas C — outreach")):
                data = _phase(record, phase)
                if not data:
                    continue
                L += [f"#### {title}", ""]
                for i, entry in enumerate(data.get("step_outputs", []), 1):
                    L += [
                        f"##### {i}. `{entry['skill']}` (thinking {MODE_LABEL[entry['thinking_mode']]}, "
                        f"{entry['tokens_out']} ut-tok, {entry['reasoning_tokens']} reasoning-tok, "
                        f"{entry['latency_ms']} ms, försök {entry['attempts']}, "
                        f"{entry['injected_chars']} tecken skill injicerat)",
                        "",
                        f"`sources_used`: {entry.get('sources_used')} · "
                        f"`context_refs`: {entry.get('context_refs')}",
                        "",
                    ]
                    L += _fence(entry.get("output", {}), "json")
                    if entry.get("reasoning_content"):
                        L += ["<details><summary>reasoning_content</summary>", ""]
                        L += _fence(entry["reasoning_content"])
                        L += ["</details>", ""]
    return "\n".join(L)


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not source:
        candidates = sorted((ROOT / "docs" / "live-tests").glob("leads-2*.json"))
        source = candidates[-1] if candidates else None
    if not source or not source.is_file():
        raise SystemExit("Hittade ingen leads-JSON. Ange sökväg som argument.")

    payload = json.loads(source.read_text(encoding="utf-8"))
    target = ROOT / "docs" / "LEADS_THINKING_COMPARISON.md"
    target.write_text(render(payload), encoding="utf-8")
    print(f"Skrev {target.relative_to(ROOT)} ({target.stat().st_size} byte) från {source.name}")


if __name__ == "__main__":
    main()
