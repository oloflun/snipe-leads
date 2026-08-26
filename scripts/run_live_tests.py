"""Live-testkörning: support + leads, thinking PÅ vs AV, fulla outputs.

    python "C:\\Users\\Anton L\\snipe-leads\\scripts\\run_live_tests.py" --support
    python .../run_live_tests.py --leads
    python .../run_live_tests.py --skill-audit

Skriver ALLT till docs/live-tests/ (JSON + markdown) så inget går förlorat
och hela kedjan kan granskas i efterhand. Varje körning loggas dessutom till
agent_runs.step_log via den vanliga kodvägen (G10).

Verifierar per steg:
  - att skillen injicerades KOMPLETT (SKILL.md + alla references/) — jämförs
    mot agentcore.registry.load_full_skill:s egen längd
  - sources_used / context_refs (utdatakontraktet, Del C p.4)
  - reasoning_tokens (thinking PÅ vs AV)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "snajp-support"))

# Harnessen kör ENBART MemoryStorage — den öppnar aldrig databasen. En
# DATABASE_URL ur .env pekar dock ofta på en fjärrdatabas, och då fäller
# har_riktig_kunddata() DeepSeek-körningen trots att ingen kunddata kan nås
# härifrån. Blankas därför i DEN HÄR processen, innan settings byggs. Spärren
# själv rörs inte — den gör rätt; det är harnessens miljö som var fel.
import os  # noqa: E402

os.environ["DATABASE_URL"] = ""

OUT_DIR = ROOT / "docs" / "live-tests"
TENANT = "00000000-0000-4000-a000-000000000001"  # Nordlys Handel (seedad KB)

# Fem ärenden med medveten variation i ton och eskaleringsgrund.
SUPPORT_SCENARIOS = [
    {
        "id": "S1-neutral-fraga",
        "beskrivning": "Neutral faktafråga som KB täcker — ska INTE eskalera",
        "message": "Hej! Vilka betalsätt kan jag använda när jag handlar hos er?",
        "subject": "Fråga om betalsätt",
    },
    {
        "id": "S2-irriterad-leverans",
        "beskrivning": "Irriterad men saklig — leveransfråga",
        "message": "Mitt paket skulle kommit för tre dagar sedan och ingen har hört av sig. Var är det?",
        "subject": "Försenad leverans",
    },
    {
        "id": "S3-arg-aterbetalning",
        "beskrivning": "Arg + återbetalningskrav — MÅSTE eskalera",
        "message": "Det här är helt oacceptabelt!! Produkten gick sönder efter två dagar och jag KRÄVER pengarna tillbaka omedelbart.",
        "subject": "Kräver återbetalning",
    },
    {
        "id": "S4-uppsagning-ultimatum",
        "beskrivning": "Uppsägningshot/ultimatum — ska trigga retention-skillen OCH eskalera",
        "message": "Om ni inte löser det här idag så säger jag upp allt och byter leverantör. Tredje gången samma fel.",
        "subject": "Sista varningen",
    },
    {
        "id": "S5-gdpr",
        "beskrivning": "GDPR-radering — MÅSTE eskalera oavsett ton",
        "message": "Hej, jag skulle vilja att ni raderar all min persondata enligt GDPR. Tack på förhand!",
        "subject": "Radering av persondata",
    },
]


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


async def _run_support_scenario(scenario: dict, mode: str) -> dict:
    from app.agent.support_agent import run_support_agent
    from app.config import get_settings
    from app.storage.memory import MemoryStorage

    get_settings.cache_clear()
    import os

    os.environ["THINKING_MODE"] = mode
    get_settings.cache_clear()

    storage = MemoryStorage()
    started = time.monotonic()
    try:
        result = await run_support_agent(
            storage,
            TENANT,
            message=scenario["message"],
            subject=scenario["subject"],
            channel="web",
            customer_email=f"{scenario['id'].lower()}@example.com",
            customer_name="Test Kund",
            attachments=[],
        )
        result["_ok"] = True
    except Exception as error:  # noqa: BLE001 — en trasig körning ska rapporteras, inte döljas
        result = {"_ok": False, "_error": f"{type(error).__name__}: {error}"}
    result["_wall_ms"] = int((time.monotonic() - started) * 1000)
    result["_scenario"] = scenario
    result["_thinking_mode"] = mode
    return result


async def run_support(modes: list[str]) -> dict:
    from app.agentcore.registry import load_full_skill

    results = {}
    for mode in modes:
        for scenario in SUPPORT_SCENARIOS:
            key = f"{scenario['id']}::{mode}"
            print(f"  kör {key} ...", flush=True)
            results[key] = await _run_support_scenario(scenario, mode)

    # Skill-integritet: jämför injicerad längd mot registrets egen fulla längd.
    integrity = {}
    for result in results.values():
        for entry in result.get("step_log", []):
            skill = entry["skill"]
            expected = len(load_full_skill(skill))
            integrity[skill] = {
                "expected_full_chars": expected,
                "injected_chars": entry["injected_chars"],
                "complete": entry["injected_chars"] == expected,
            }
    return {"results": results, "skill_integrity": integrity}


async def run_skill_audit() -> dict:
    """Bevisar att varje skill i varje playbook laddas KOMPLETT — SKILL.md
    plus varje fil under references/ — och listar exakt vilka filer."""
    from app.agentcore.registry import SKILLS_ROOT, load_full_skill, load_skill_md, parse_skill_name
    from app.agent.support_playbook import SUPPORT_V1
    from app.leads.onboarding_playbook import ONBOARDING_V1
    from app.leads.outreach_playbook import OUTREACH_V1
    from app.leads.research_playbook import RESEARCH_V1

    audit = {}
    for playbook in (SUPPORT_V1, ONBOARDING_V1, RESEARCH_V1, OUTREACH_V1):
        steps = []
        for step in playbook.steps:
            ref = parse_skill_name(step.skill)
            references_dir = ref.dir / "references"
            reference_files = (
                sorted(
                    p.relative_to(ref.dir).as_posix()
                    for p in references_dir.rglob("*")
                    if p.is_file() and p.suffix in (".md", ".csv", ".txt")
                )
                if references_dir.is_dir()
                else []
            )
            rendered = step.render()
            steps.append(
                {
                    "skill": step.skill,
                    "requires": list(step.requires),
                    "scoped": bool(step.scope),
                    "scope": list(step.scope),
                    "rationale": step.rationale,
                    "skill_md_chars": len(load_skill_md(step.skill)),
                    "full_chars": len(load_full_skill(step.skill)),
                    "rendered_chars": len(rendered),
                    "reference_files": reference_files,
                    "reference_count": len(reference_files),
                    # Oskopat steg MÅSTE rendera hela skillen inkl. references.
                    "renders_complete": (
                        len(rendered) == len(load_full_skill(step.skill))
                        if not step.scope
                        else None
                    ),
                    "all_references_present_in_render": (
                        all(name in rendered for name in reference_files)
                        if not step.scope and reference_files
                        else None
                    ),
                }
            )
        audit[playbook.name] = steps
    return audit


def render_support_markdown(payload: dict) -> str:
    results, integrity = payload["results"], payload["skill_integrity"]
    lines = ["# Support: live-körningar, thinking PÅ vs AV", ""]

    lines += ["## Sammanfattning per scenario", "",
              "| Scenario | Läge | Eskalerad | Kategori | Steg | out-tok | reasoning-tok | ms |",
              "|---|---|---|---|---|---|---|---|"]
    for key in sorted(results):
        r = results[key]
        if not r.get("_ok"):
            lines.append(f"| {key} | — | FEL | {r.get('_error','')[:40]} | — | — | — | — |")
            continue
        steps = r.get("step_log", [])
        out_tok = sum(s["tokens_out"] for s in steps)
        rea_tok = sum(s["reasoning_tokens"] for s in steps)
        lines.append(
            f"| {r['_scenario']['id']} | {r['_thinking_mode']} | "
            f"{'JA' if r['escalated'] else 'nej'} | {r['category']} | {len(steps)} | "
            f"{out_tok} | {rea_tok} | {r['_wall_ms']} |"
        )

    lines += ["", "## Skill-integritet (injicerades hela skillen?)", "",
              "| Skill | Förväntat (tecken) | Injicerat | Komplett |", "|---|---|---|---|"]
    for skill, data in sorted(integrity.items()):
        lines.append(
            f"| `{skill}` | {data['expected_full_chars']} | {data['injected_chars']} | "
            f"{'JA' if data['complete'] else 'NEJ'} |"
        )

    for key in sorted(results):
        r = results[key]
        lines += ["", "---", "", f"## {key}", "",
                  f"**{r['_scenario']['beskrivning']}**", "",
                  f"> {r['_scenario']['message']}", ""]
        if not r.get("_ok"):
            lines += [f"**FEL:** `{r.get('_error')}`", ""]
            continue
        lines += [
            f"- Eskalerad: **{r['escalated']}** ({r.get('escalation_reason') or '—'})",
            f"- Kategori: `{r['category']}` · sentiment {r['sentiment']}",
            f"- Uppsägningsrisk: {r['cancellation_risk']}",
            f"- KB-träffar: {[s['title'] for s in r['kb_sources']]}",
            f"- Skills: {' -> '.join(r['skills_used'])}",
            "", "### Slutligt svar till kund", "", "```", r["reply"], "```", "",
            "### Steg för steg", "",
            "| # | Skill | försök | esk | in | ut | reason | injicerat | sources_used | context_refs |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
        for i, s in enumerate(r["step_log"], 1):
            lines.append(
                f"| {i} | `{s['skill']}` | {s['attempts']} | {'JA' if s['escalated'] else '-'} | "
                f"{s['tokens_in']} | {s['tokens_out']} | {s['reasoning_tokens']} | "
                f"{s['injected_chars']} | {s['sources_used']} | {s['context_refs']} |"
            )
    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--support", action="store_true")
    parser.add_argument("--leads", action="store_true")
    parser.add_argument("--skill-audit", action="store_true")
    parser.add_argument("--modes", default="enabled,disabled")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _now_stamp()
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]

    if args.skill_audit:
        audit = await run_skill_audit()
        _write(OUT_DIR / f"skill-audit-{stamp}.json", json.dumps(audit, indent=2, ensure_ascii=False))
        print(json.dumps(audit, indent=2, ensure_ascii=False))

    if args.support:
        print(f"Support: {len(SUPPORT_SCENARIOS)} scenarier x {len(modes)} lägen")
        payload = await run_support(modes)
        _write(OUT_DIR / f"support-{stamp}.json", json.dumps(payload, indent=2, ensure_ascii=False))
        _write(OUT_DIR / f"support-{stamp}.md", render_support_markdown(payload))
        print(f"\nSkrev docs/live-tests/support-{stamp}.md")

    if args.leads:
        from render_leads_report import render as render_leads_markdown
        from run_live_leads import run_leads  # separata moduler, se filerna

        payload = await run_leads(modes)
        _write(OUT_DIR / f"leads-{stamp}.json", json.dumps(payload, indent=2, ensure_ascii=False))
        _write(ROOT / "docs" / "LEADS_THINKING_COMPARISON.md", render_leads_markdown(payload))
        print(f"\nSkrev docs/live-tests/leads-{stamp}.json + docs/LEADS_THINKING_COMPARISON.md")


if __name__ == "__main__":
    asyncio.run(main())
