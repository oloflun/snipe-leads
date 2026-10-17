"""Skapa om bara utkastet: underlaget ur leadets sparade research.

"Skapa om utkast" körde hela research_and_draft igen, och en ny research är
en ny bedömning: 23 av 104 leads föll till nivå C när Snajps utkast skrevs om
2026-10-16 (docs/UTKASTKEDJAN-REFERENS-2026-10-16.md, avsnitt 8.5). Ett lead
som redan är bedömt ska bara få ett nytt mejl. Därför läses utkastets
underlag ur bolagets senaste researchkörning (`agent_runs`, agent_type
`leads_research`) i stället för att researchas om.

Två källor, i ordning:

1. Posten `underlag:utkast` i körningens step_log. Researchsteget skriver den
   sedan 2026-10-17 (`underlagspost`) med exakt de fält utkastet läser.
2. Äldre körningar saknar posten. Då byggs underlaget ur researchstegets egen
   utdata (`raw_output`) och dess källmaterial (`user_message`): citaten
   verifieras ordagrant mot materialet med samma kontroll som researchen,
   och bedömningen (motivering, lägesbeskrivning, uppfyllda kriterier) läses
   ur prospektraden där den sparades.

Ingen ny sidhämtning, inget researchanrop och ingen ny bedömning. Finns ingen
körning returneras None, och anroparen får säga det i stället för att gissa.
"""
from __future__ import annotations

import json
from typing import Any

#: Nyckeln på posten i step_log ("step" som kodgrindarna, inte "skill").
UNDERLAGSSTEG = "underlag:utkast"

#: Fälten ur researchens resultat som utkastet läser (api/leads.py,
#: `_run_batch_prospect`). Inget annat sparas: posten ska vara underlaget,
#: inte en andra kopia av körningen.
UNDERLAGSFALT = (
    "company_summary",
    "qualified",
    "icp_fit",
    "likely_pains",
    "trigger_events",
    "motivering",
    "vinklar",
    "uppfyllda_kriterier",
    "webbsignaler",
    "citat",
    "lagesbeskrivning",
    "produkt",
    "offer_summary",
    "research_evidence",
    "disqualifiers",
)


def underlagspost(resultat: dict[str, Any]) -> dict[str, Any]:
    """Posten researchsteget lägger i sin step_log."""
    return {"step": UNDERLAGSSTEG, **{f: resultat.get(f) for f in UNDERLAGSFALT}}


def _hitta(logg: list[Any], nyckel: str) -> dict[str, Any] | None:
    return next((p for p in logg if isinstance(p, dict) and p.get("step") == nyckel), None)


def _logg(run: dict[str, Any]) -> list[Any]:
    logg = run.get("step_log") or []
    if isinstance(logg, str):
        try:
            logg = json.loads(logg)
        except ValueError:
            return []
    return logg if isinstance(logg, list) else []


def _ur_aldre_korning(
    logg: list[Any], prospekt: dict[str, Any], produkter: list[dict[str, str]], vinklar: list[Any]
) -> dict[str, Any] | None:
    """Underlaget ur en körning från före `underlag:utkast` (se modulens punkt 2)."""
    from ..agent.leads_research_v2 import _vald_produkt
    from .bedomning import verifierade_belagg

    steg = next((p for p in logg if isinstance(p, dict) and p.get("skill") and p.get("raw_output")), None)
    if steg is None:
        return None
    try:
        fynd = json.loads(steg["raw_output"])
    except (TypeError, ValueError):
        return None
    if not isinstance(fynd, dict):
        return None
    material = str(steg.get("user_message") or "")
    bedomningscitat = [
        b
        for rad in fynd.get("bedomningar") or []
        if isinstance(rad, dict)
        for b in rad.get("belagg") or []
        if isinstance(b, dict)
    ]
    citat = list(
        dict.fromkeys(
            c["citat"]
            for c in verifierade_belagg(
                [{"citat": str(e)} for e in fynd.get("evidence") or []] + bedomningscitat, material
            )
        )
    )
    offer = fynd.get("offer") if isinstance(fynd.get("offer"), dict) else {}
    rader = prospekt.get("score_breakdown") or []
    return {
        "company_summary": fynd.get("company_summary"),
        "qualified": prospekt.get("qualified"),
        "icp_fit": prospekt.get("icp_fit"),
        "likely_pains": fynd.get("likely_pains"),
        "trigger_events": fynd.get("trigger_events"),
        "motivering": prospekt.get("motivering"),
        "vinklar": vinklar,
        "uppfyllda_kriterier": [
            r.get("etikett") for r in rader if isinstance(r, dict) and r.get("utfall") == "träff"
        ],
        "webbsignaler": [],
        "citat": citat,
        "lagesbeskrivning": prospekt.get("lagesbeskrivning") or fynd.get("lagesbeskrivning"),
        "produkt": _vald_produkt(fynd, produkter) if produkter else None,
        "offer_summary": " · ".join(str(offer.get(k)) for k in ("name", "promise", "cta") if offer.get(k))
        or "(inget erbjudande formulerat)",
        "research_evidence": [
            str(x)
            for x in (*(fynd.get("evidence") or []), *(fynd.get("likely_pains") or []),
                      *(fynd.get("trigger_events") or []))
            if str(x).strip()
        ],
        "disqualifiers": prospekt.get("disqualifiers") or [],
    }


async def las(storage, tenant_id: str, prospect_id: str) -> dict[str, Any] | None:
    """Utkastets underlag ur bolagets senaste research, eller None om bolaget
    aldrig researchats (eller körningen inte går att läsa).

    Bedömningen (qualified, icp_fit, disqualifiers) tas alltid ur prospektraden:
    den är leadets gällande bedömning, även om någon ändrat den efter körningen."""
    runs = await storage.list_agent_runs_all(
        tenant_id=tenant_id, agent_type="leads_research", prospect_id=prospect_id, limit=1
    )
    if not runs:
        return None
    logg = _logg(runs[0])
    prospekt = await storage.get_prospect(tenant_id, prospect_id) or {}
    post = _hitta(logg, UNDERLAGSSTEG)
    if post is not None:
        underlag = {f: post.get(f) for f in UNDERLAGSFALT}
    else:
        from ..agent.leads_research_v2 import las_produkter
        from .profil import sakerstall_profil

        produkter = las_produkter(await storage.get_agent_settings(tenant_id, agent_type="leads"))
        profil = await sakerstall_profil(storage, tenant_id)
        underlag = _ur_aldre_korning(logg, prospekt, produkter, list(profil.get("vinklar") or []))
        if underlag is None:
            return None
    for falt in ("qualified", "icp_fit", "disqualifiers", "lagesbeskrivning"):
        if prospekt.get(falt) is not None:
            underlag[falt] = prospekt[falt]
    underlag["sparad_research"] = True
    return underlag
