"""Mätning: tre skopor för sa:draft-outreach i V2:s första-mejlssteg.

Planen 2026-10-06 (iris-sanning-malgrupp-instruktioner), Fas 4 punkt 4.

  a  före 2026-10-06: skopan med "§ Cold Outreach (No Prior Relationship)",
     utan radändringar (skopan ur 45c1098~1)
  b  snäv: dagens skopa minus de sektioner radändringarna rör (Step 2,
     Step 4, Email Style Guidelines, Example + Notion-exemplet), utan
     radändringar
  c  dagens: skopa + radändringar (oförändrad kod)

Varianten byts genom dataclasses.replace på playbook-steget i DET HÄR
skriptet. Källfilerna och skillfilerna rörs inte (INV-SKILL-005).

Researchen körs EN gång per fixture och delas av de tre varianterna, så att
skillnaden mellan utkasten bara är skopan. Riktiga kodvägar mot
MemoryStorage, syntetiska fixtures (snajp-support/fixtures/leads_benchmark),
LLM via produktionens egen klient (LLM_PROVIDER=gemini, nyckeln läses av
Settings ur snajp-support/.env och skrivs aldrig ut).

    python scripts/mat_skillvarianter.py
    python scripts/mat_skillvarianter.py --max-fixtures 1   # röktest

Utdata: var/skillvarianter/resultat.json och tabell.md.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROT / "snajp-support"))
sys.path.insert(0, str(ROT / "scripts"))

from benchmark_leads_kedja import (  # noqa: E402
    FIXTURES,
    GEMINI_KR_IN,
    GEMINI_KR_UT,
    TENANT,
    _fake_scrape,
)

UTKATALOG = ROT / "var" / "skillvarianter"
# Produktionens Vertex-modell (europe-west1 har inte gemini-3.6-flash: 404).
MODELL = "gemini-2.5-flash"

SKOPA_A = (
    "§ Execution Flow",
    "§ Cold Outreach (No Prior Relationship)",
    "§ Email Style Guidelines",
    "§ What NOT to Do",
    "§ Example",
    "§ Outreach Draft: David Tibbitts @ Notion",
)
# Radändringarna sitter i Step 2 och Step 4 (under Execution Flow), i Email
# Style Guidelines och i Notion-exemplet. Snävast möjliga hela sektioner:
# Execution Flow behåller Step 1, 3 och 5.
SKOPA_B = (
    "§ Step 1: Parse Request",
    "§ Step 3: Identify Hook",
    "§ Step 5: Create Email Draft",
    "§ What NOT to Do",
)

FALLBACK_CASE_RE = re.compile(
    r"(?i)liknande (?:företag|bolag)|vi har hjälpt|ett annat (?:\w+)?(?:företag|bolag)"
    r"|hjälpte nyligen|similar compan(?:y|ies)|we helped"
)
_ORD = re.compile(r"[0-9a-zåäöéü]+(?:-[0-9a-zåäöéü]+)*")
_HALSNING = re.compile(r"^(hej|hejsan|hi|hello|god (morgon|dag))\b", re.IGNORECASE)
_VILKA_VI = re.compile(
    r"\bsnajps?\b|\bvi (?:är|på|har byggt|bygger|har utvecklat|utvecklar|hjälper)\b", re.IGNORECASE
)
_PRODUKT = re.compile(r"agent|ai-support|chatt", re.IGNORECASE)


def varianter(outreach_v2):
    steg0 = outreach_v2.steps[0]
    return {
        "a": replace(outreach_v2, steps=(replace(steg0, scope=SKOPA_A, radandringar=()), *outreach_v2.steps[1:])),
        "b": replace(outreach_v2, steps=(replace(steg0, scope=SKOPA_B, radandringar=()), *outreach_v2.steps[1:])),
        "c": outreach_v2,
    }


# -- Mätningar (ren kod) ----------------------------------------------------


def ord_(text: str) -> list[str]:
    return _ORD.findall(text.lower())


def ordagranna_fraser(utkast: str, kalla: str, n: int = 5) -> list[str]:
    """Maximala ordsekvenser (>= n ord) ur källan som står ordagrant i utkastet."""
    k = ord_(kalla)
    kallgram = {tuple(k[i : i + n]) for i in range(len(k) - n + 1)}
    u = ord_(utkast)
    traff = [tuple(u[i : i + n]) in kallgram for i in range(len(u) - n + 1)]
    fraser, i = [], 0
    while i < len(traff):
        if traff[i]:
            j = i
            while j + 1 < len(traff) and traff[j + 1]:
                j += 1
            fraser.append(" ".join(u[i : j + n]))
            i = j + 1
        else:
            i += 1
    return fraser


def forsta_meningen(body: str) -> str:
    rader = [r.strip() for r in body.strip().splitlines() if r.strip()]
    if rader and _HALSNING.match(rader[0]) and len(rader[0]) < 40:
        rader = rader[1:]
    text = " ".join(rader)
    m = re.search(r"[.!?](\s|$)", text)
    return text[: m.end()].strip() if m else text


def namnord(company_name: str) -> list[str]:
    return [w for w in ord_(company_name) if w != "ab"]


def har_observation(mening: str, material: str, company_name: str) -> bool:
    """En konkret observation = en tregram ur materialet som inte bara är
    bolagsnamnet, eller ett tal som står i materialet."""
    namn = set(namnord(company_name))
    m = ord_(material)
    tregram = {tuple(m[i : i + 3]) for i in range(len(m) - 2)}
    u = ord_(mening)
    for i in range(len(u) - 2):
        g = tuple(u[i : i + 3])
        if g in tregram and not set(g) <= namn:
            return True
    tal_mat = set(re.findall(r"\d+", material))
    return any(t in tal_mat for t in re.findall(r"\d+", mening))


def har_bolagsnamn(text: str, company_name: str) -> bool:
    forsta = namnord(company_name)[0]
    return forsta[:5] in text.lower()


def mat(subject: str, body: str, *, fixture: dict, citat: list[str], facts) -> dict[str, Any]:
    from app.leads.grounding_gate import check_grounding

    material = fixture["material"]
    kalla = material + "\n" + "\n".join(citat)
    dom = check_grounding(f"{subject}\n\n{body}", facts)
    case_fynd = [c.describe() for c in dom.unsupported if c.kind in ("unnamed_case", "named_customer")]
    regex_fynd = [m.group(0) for m in FALLBACK_CASE_RE.finditer(f"{subject}\n{body}")]
    mening = forsta_meningen(body)
    fraser = ordagranna_fraser(body, kalla)
    rader = [r.strip() for r in body.splitlines() if r.strip()]
    namn = set(namnord(fixture["company_name"]))
    amnesord = {w for w in ord_(subject) if len(w) >= 5 and w not in namn}
    struktur = {
        "amne_observation": bool(amnesord & set(ord_(material))),
        "halsning": bool(rader) and bool(_HALSNING.match(rader[0])),
        "observation": har_observation(mening, material, fixture["company_name"]),
        "vilka_vi_ar": bool(_VILKA_VI.search(body)),
        "produkt": bool(_PRODUKT.search(body)),
        "uppmaning": any("?" in r for r in rader[-4:]),
    }
    return {
        "pahittade_case_grind": case_fynd,
        "pahittade_case_regex": regex_fynd,
        "pahittade_case": len(case_fynd) + len(regex_fynd),
        "ordagranna_fraser": fraser,
        "antal_fraser": len(fraser),
        "forsta_meningen": mening,
        "forsta_namn_och_observation": har_bolagsnamn(mening, fixture["company_name"])
        and har_observation(mening, material, fixture["company_name"]),
        "ord": len(ord_(body)),
        # Oifyllda mallplatshållare, t.ex. "Hej [VD:ns förnamn]".
        "platshallare": re.findall(r"\[[^\]\n]{2,60}\]", f"{subject}\n{body}"),
        # Förnamn i hälsningen som inte står i källan (grinden ser inte detta).
        "pahittat_tilltal": [
            n for n in re.findall(r"^(?:hej|hejsan|hi|hello)\s+([A-ZÅÄÖ][a-zåäöé]+)", body.strip(), re.IGNORECASE)
            if n.lower() not in ord_(kalla)
        ],
        "struktur": struktur,
        "struktur_poang": sum(struktur.values()),
    }


def _ra_utkast(utkast: dict) -> tuple[str, str]:
    """Steg 1:s utdata före humanizer och grundningscykel."""
    for steg in utkast.get("step_outputs") or []:
        if steg.get("skill") == "sa:draft-outreach":
            out = steg.get("output") or {}
            if isinstance(out, str):
                try:
                    out = json.loads(out)
                except ValueError:
                    return "", out
            return str(out.get("subject") or ""), str(out.get("body") or "")
    return "", ""


# -- Körning ----------------------------------------------------------------


async def research_for(fixture: dict) -> tuple[Any, dict, dict]:
    from app.agent.leads_research_v2 import run_research_step_v2
    from app.storage.memory import MemoryStorage

    storage = MemoryStorage()
    await storage.save_context_doc(
        TENANT, kind="product_marketing", content=fixture["context_pack"], source="skillvarianter"
    )
    prospect = await storage.create_prospect(
        TENANT, company_name=fixture["company_name"], profil={"website": fixture["website"]}
    )
    await storage.create_prospect_source(
        TENANT,
        prospect_id=prospect["id"],
        source_url=fixture["website"],
        source_type="company_website",
        lawful_basis="berättigat intresse (B2B)",
    )
    with patch(
        "app.agent.leads_agent._scrape_registered_source_impl", new=_fake_scrape(fixture["material"])
    ):
        research = await run_research_step_v2(
            storage,
            TENANT,
            prospect_id=prospect["id"],
            tenant_name="Snajp",
            context_pack=fixture["context_pack"],
            brief="",
            is_test=True,
        )
    return storage, prospect, research


async def utkast_for(storage, prospect: dict, fixture: dict, research: dict, playbook) -> dict:
    from app.agent import leads_research_v2 as v2

    rad = await storage.get_prospect(TENANT, prospect["id"]) or {}
    domain = fixture["website"].split("//", 1)[-1].strip("/")
    epost = rad.get("contact_email") or fixture["facit"].get("contact_email") or f"vd@{domain}"
    thread = await storage.ensure_outreach_thread(TENANT, prospect_id=prospect["id"])
    with (
        patch.object(v2, "OUTREACH_V2", playbook),
        patch("app.agent.leads_agent._scrape_registered_source_impl", new=_fake_scrape(fixture["material"])),
    ):
        try:
            return await v2.run_outreach_draft_v2(
                storage,
                TENANT,
                thread_id=thread["id"],
                prospect_email=epost,
                tenant_name="Snajp",
                company_name=fixture["company_name"],
                offer_summary=research.get("offer_summary") or "",
                context_pack=fixture["context_pack"],
                brief="",
                research_summary=research.get("final_output") or "",
                research_evidence=tuple(research.get("research_evidence") or ()),
                is_test=True,
            )
        except Exception as fel:  # noqa: BLE001 — ett fällt utkast är ett mätvärde
            return {"fel": f"{type(fel).__name__}: {fel}"}


def _citat(research: dict) -> list[str]:
    try:
        fynd = json.loads(research.get("final_output") or "{}")
    except (TypeError, ValueError):
        return []
    c = fynd.get("citat") if isinstance(fynd, dict) else None
    return [str(x.get("text") if isinstance(x, dict) else x) for x in (c or [])]


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-fixtures", type=int, default=0)
    args = ap.parse_args()

    os.environ["LLM_PROVIDER"] = "gemini"
    os.environ["MODEL"] = MODELL
    from app.config import get_settings

    get_settings.cache_clear()
    if not get_settings().gemini_api_key:
        sys.exit("GEMINI_API_KEY saknas i snajp-support/.env.")
    if get_settings().llm_provider != "gemini":
        sys.exit("LLM_PROVIDER blev inte gemini — avbryter (DeepSeek får inte köras här).")

    from app.leads.grounding_gate import build_permitted_facts
    from app.leads.outreach_playbook import OUTREACH_V2

    pb = varianter(OUTREACH_V2)
    # Självkontroll: varianterna renderar det de påstår.
    rend = {k: p.steps[0].render() for k, p in pb.items()}
    assert "Cold Outreach (No Prior Relationship)" in rend["a"]
    assert "similar company result" in rend["a"] and "similar company result" not in rend["c"]
    assert "Research First" not in rend["b"] and "Email Style Guidelines" not in rend["b"]
    assert "Identify Hook" in rend["b"] and "What NOT to Do" in rend["b"]
    assert "Cold Outreach (No Prior" not in rend["c"]
    skopa_tecken = {k: len(v) for k, v in rend.items()}

    fixtures = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(FIXTURES.glob("*.json"))]
    if args.max_fixtures:
        fixtures = fixtures[: args.max_fixtures]

    rader: list[dict[str, Any]] = []
    research_tokens = {"in": 0, "ut": 0}
    for fx in fixtures:
        print(f"[research] {fx['company_name']} ...", flush=True)
        storage, prospect, research = await research_for(fx)
        research_tokens["in"] += int(research.get("tokens_in") or 0)
        research_tokens["ut"] += int(research.get("tokens_out") or 0)
        citat = _citat(research)
        facts = build_permitted_facts(
            context_pack=fx["context_pack"],
            research_evidence=tuple(research.get("research_evidence") or ()),
            offer_summary=research.get("offer_summary") or "",
            brief="",
            tenant_name="Snajp",
            company_name=fx["company_name"],
        )
        for namn, playbook in pb.items():
            print(f"[utkast {namn}] {fx['company_name']} ...", flush=True)
            u = await utkast_for(storage, prospect, fx, research, playbook)
            ra_subj, ra_body = _ra_utkast(u)
            rader.append(
                {
                    "fixture": fx["company_name"],
                    "variant": namn,
                    "research_qualified": research.get("qualified"),
                    "research_stopped_early": research.get("stopped_early"),
                    "fel": u.get("fel"),
                    "subject": u.get("subject"),
                    "body": u.get("body"),
                    "ra_subject": ra_subj,
                    "ra_body": ra_body,
                    "grounding": u.get("grounding"),
                    "queued": u.get("queued"),
                    "tokens_in": int(u.get("tokens_in") or 0),
                    "tokens_out": int(u.get("tokens_out") or 0),
                    "anrop": len(u.get("step_log") or []),
                    "matt_slutligt": mat(u.get("subject") or "", u.get("body") or "", fixture=fx, citat=citat, facts=facts)
                    if u.get("body")
                    else None,
                    "matt_ra": mat(ra_subj, ra_body, fixture=fx, citat=citat, facts=facts) if ra_body else None,
                }
            )

    # -- Rapport -------------------------------------------------------------
    def kr(t_in: int, t_ut: int) -> float:
        return round(t_in / 1e6 * GEMINI_KR_IN + t_ut / 1e6 * GEMINI_KR_UT, 4)

    md = [
        f"# Skopvarianter för sa:draft-outreach (V2 steg 1), {MODELL}\n",
        "Påhittade case = grindens unnamed_case/named_customer + fallback-regex. "
        "Rå = steg 1 före humanizer och grundningscykel; slutligt = det som köas.\n",
        "| Fixture | Var. | Case rå | Case slutligt | Fraser ≥5 ord | Namn+obs i 1:a meningen | Ord | Struktur /6 | Platshållare | Grind ok | Tokens in/ut |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rader:
        s, ra = r["matt_slutligt"] or {}, r["matt_ra"] or {}
        if r["fel"] or not s:
            md.append(f"| {r['fixture']} | {r['variant']} | – | – | – | – | – | – | – | – | fel: {r['fel']} |")
            continue
        md.append(
            f"| {r['fixture']} | {r['variant']} | {ra.get('pahittade_case', '–')} | {s['pahittade_case']} "
            f"| {s['antal_fraser']} | {'ja' if s['forsta_namn_och_observation'] else 'nej'} | {s['ord']} "
            f"| {s['struktur_poang']} | {len(s['platshallare'])} | {(r['grounding'] or {}).get('ok')} | {r['tokens_in']:,}/{r['tokens_out']:,} |"
        )
    md += [
        "",
        "| Variant | Skopa (tecken, steg 1) | Case rå (summa) | Case slutligt (summa) | Fraser (summa) | Namn+obs (antal) | Ord (snitt) | Struktur (snitt) | Platshållare (summa) | Tokens in/ut | ~kr |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    sammanfattning = {}
    for namn in pb:
        rr = [r for r in rader if r["variant"] == namn and r["matt_slutligt"]]
        n = max(len(rr), 1)
        t_in = sum(r["tokens_in"] for r in rader if r["variant"] == namn)
        t_ut = sum(r["tokens_out"] for r in rader if r["variant"] == namn)
        s = {
            "utkast": len(rr),
            "skopa_tecken": skopa_tecken[namn],
            "case_ra": sum((r["matt_ra"] or {}).get("pahittade_case", 0) for r in rr),
            "case_slutligt": sum(r["matt_slutligt"]["pahittade_case"] for r in rr),
            "fraser": sum(r["matt_slutligt"]["antal_fraser"] for r in rr),
            "namn_obs": sum(1 for r in rr if r["matt_slutligt"]["forsta_namn_och_observation"]),
            "ord_snitt": round(sum(r["matt_slutligt"]["ord"] for r in rr) / n, 1),
            "struktur_snitt": round(sum(r["matt_slutligt"]["struktur_poang"] for r in rr) / n, 2),
            "platshallare": sum(len(r["matt_slutligt"]["platshallare"]) for r in rr),
            "tokens_in": t_in,
            "tokens_out": t_ut,
            "kr": kr(t_in, t_ut),
        }
        sammanfattning[namn] = s
        md.append(
            f"| {namn} | {s['skopa_tecken']:,} | {s['case_ra']} | {s['case_slutligt']} | {s['fraser']} "
            f"| {s['namn_obs']}/{s['utkast']} | {s['ord_snitt']} | {s['struktur_snitt']} | {s['platshallare']} "
            f"| {t_in:,}/{t_ut:,} | {s['kr']} |"
        )
    md.append(
        f"\nResearch (en gång per fixture, delad): {research_tokens['in']:,} in / "
        f"{research_tokens['ut']:,} ut, ~{kr(research_tokens['in'], research_tokens['ut'])} kr."
    )
    tabell = "\n".join(md) + "\n"
    print("\n" + tabell)

    UTKATALOG.mkdir(parents=True, exist_ok=True)
    (UTKATALOG / "tabell.md").write_bytes(tabell.encode("utf-8"))
    (UTKATALOG / "resultat.json").write_bytes(
        json.dumps(
            {
                "modell": MODELL,
                "skopor": {"a": SKOPA_A, "b": SKOPA_B, "c": list(OUTREACH_V2.steps[0].scope)},
                "sammanfattning": sammanfattning,
                "research_tokens": research_tokens,
                "utkast": rader,
            },
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        + b"\n"
    )
    print(f"Sparat: {UTKATALOG}")


if __name__ == "__main__":
    asyncio.run(main())
