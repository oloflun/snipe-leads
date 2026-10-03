"""Jev-kaskaden: TypeSafe `jev-1.13.0` som billig beslutsmodell runt Iris.

## Vad Jev är, och vad den inte är

En beslutsmodell: typade frågor (score/noul/choice) in, sannolikheter ut,
~0,3 s per anrop, ~0,00004 kr per lead. Den skriver INGEN motivering — och
motiveringen är det kunden köper (INV-LEADS-SCORE-001). Jev ersätter därför
aldrig kvalificeringen; den sitter runt den (IMP-015 i valvet, Antons mätning
2026-09-27: "förfilter i kaskad, inte ersättare").

## Två platser i flödet

1. **Triage** (`triage`), före det dyra researchanropet: en direkt noul per
   MÅSTE-kriterium och per uteslutning, en helhetspoäng och en choice som
   pekar ut stödraden i utdraget. I läge "pa" fäller den UPPENBARA missar
   (hög säkerhet) — den godkänner aldrig något, samma regel som
   kvalificeringsgrinden. Fällningen bär stödraden som belägg.
2. **Klassning** (`klassa`), efter researchen: en kalibrerad sannolikhet för
   "bra lead" och en trafikpolisnivå (hög/mellan/låg). Sparas bredvid kodens
   nivå A/B/C så att de två går att jämföra (`scripts/iris_jev_eval.py`).

## Data

Jev ser bara PROSPEKTETS publika bolagsuppgifter — namn, ort, webbplatsens
mätta signaler och ett utdrag ur bolagets egen publika sida — plus kundens
kriterier. Aldrig kundens egna data (kundmejl, ärenden) och aldrig
personnamn eller e-postadresser (`_utan_personuppgifter`). Beslut Anton
2026-09-30.

## Lägen (IRIS_JEV)

off = inga anrop. skugga = anropen görs och loggas, inget fälls.
pa = triagen fäller. Anropsfel fäller aldrig: faller Jev går kandidaten
vidare till researchen (fail open — Jev är en besparing, inte en grind).
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from ..config import get_settings

logger = logging.getLogger("snajp-support.leads.jev")

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODELL = "jev-1.13.0"
TIMEOUT_S = 20.0
#: Choice-frågans tak på alternativ (TypeSafe api.md).
MAX_RADER = 255

#: τ — hur säker Jev måste vara för att få fälla. En noul ≤ NEJ_GRANS på ett
#: måste-kriterium eller ≥ JA_GRANS på en uteslutning räknas som säker.
#: Satt strängt: arXiv 2609.26550 accepterar vid ≥0,9 och eskalerar resten.
NEJ_GRANS = 0.08
JA_GRANS = 0.92

_EPOST = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_TELEFON = re.compile(r"(?:\+46|0)[\d -]{7,}\d")


def lage() -> str:
    varde = (get_settings().iris_jev or "off").strip().lower()
    return varde if varde in ("off", "skugga", "pa") else "off"


def aktiv() -> bool:
    return lage() != "off" and bool(get_settings().typesafe_api_key)


def _utan_personuppgifter(text: str) -> str:
    return _TELEFON.sub("[telefon]", _EPOST.sub("[e-post]", text or ""))


def _rader(utdrag: str) -> list[str]:
    return [r.strip() for r in (utdrag or "").splitlines() if len(r.strip()) >= 3][:MAX_RADER]


async def fraga(state: dict[str, Any], fragor: dict[str, Any]) -> dict[str, Any]:
    """Ett anrop. Kastar vid fel — anroparen avgör vad ett fel betyder."""
    nyckel = get_settings().typesafe_api_key
    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        svar = await client.post(
            ENDPOINT,
            json={"state": state, "model": MODELL, "questions": fragor},
            headers={"Authorization": f"Bearer {nyckel}"},
        )
    svar.raise_for_status()
    return svar.json().get("answers") or {}


def _state(profil: dict[str, Any], kandidat: dict[str, Any], rader: list[str], signaler: list[str]) -> dict:
    return {
        "seller_offer": profil.get("erbjudande") or "",
        "target_group": profil.get("malgrupp") or "",
        "company": {
            "name": kandidat.get("company_name"),
            "city": kandidat.get("ort"),
            "website": kandidat.get("website"),
            "employees": kandidat.get("anstallda"),
            "measured_website_signals": signaler,
        },
        "excerpt": "\n".join(f"L{i:03d}| {r}" for i, r in enumerate(rader)),
    }


def _fragor(profil: dict[str, Any], rader: list[str]) -> dict[str, Any]:
    # En direkt fråga per bedömning — Antons mätning: tvåstegsfrågor
    # diskriminerar inte, en enda direkt fråga gör det.
    fragor: dict[str, Any] = {
        "fit": {
            "type": "score",
            "instructions": (
                "How well does this company match the seller's target group, judged only "
                "on the company data and excerpt? Target group: "
                + (profil.get("malgrupp") or "see seller_offer")
            ),
            "criteria": [
                "Clearly outside the target group.",
                "Probably outside the target group.",
                "Probably inside the target group.",
                "Clearly inside the target group.",
            ],
        }
    }
    for k in profil.get("kriterier") or []:
        if k.get("krav") == "maste":
            fragor[f"krav_{k['id']}"] = {
                "type": "noul",
                "instructions": f"Does this company meet this requirement: {k['text']}",
            }
    for i, u in enumerate(profil.get("uteslut") or [], start=1):
        fragor[f"uteslut_u{i}"] = {
            "type": "noul",
            "instructions": f"Is this company {u['text']}?",
        }
    if rader:
        fragor["stodrad"] = {
            "type": "choice",
            "instructions": "Which excerpt line best supports your judgement of the company's fit?",
            "criteria": {f"L{i:03d}": None for i in range(len(rader))},
        }
    return fragor


def _tolka(profil: dict[str, Any], svar: dict[str, Any], rader: list[str]) -> dict[str, Any]:
    fit = svar.get("fit") or {}
    stod = None
    val = (svar.get("stodrad") or {}).get("choice")
    if isinstance(val, str) and val[1:].isdigit() and int(val[1:]) < len(rader):
        stod = rader[int(val[1:])]
    skal: list[str] = []
    for k in profil.get("kriterier") or []:
        p = (svar.get(f"krav_{k['id']}") or {}).get("noul")
        if isinstance(p, (int, float)) and p <= NEJ_GRANS:
            skal.append(f"{k['text']} (Jev: {p:.2f})")
    for i, u in enumerate(profil.get("uteslut") or [], start=1):
        p = (svar.get(f"uteslut_u{i}") or {}).get("noul")
        if isinstance(p, (int, float)) and p >= JA_GRANS:
            skal.append(f"Uteslut: {u['text']} (Jev: {p:.2f})")
    return {
        "fit": fit.get("score"),
        "fit_konfidens": fit.get("confidence"),
        "svar": {n: {k: v for k, v in a.items() if k in ("noul", "score", "choice", "confidence")}
                 for n, a in svar.items() if isinstance(a, dict)},
        "stodrad": stod,
        "fall_skal": skal,
    }


async def triage(profil: dict[str, Any], kandidat: dict[str, Any], *, utdrag: str,
                 signaler: list[str]) -> dict[str, Any] | None:
    """Jevs förbedömning av en kandidat. None när Jev är av eller svarade fel.

    `beslut` = "fall" bara i läge pa och bara med ett säkert skäl; i
    skuggläge räknas samma beslut ut men står som `skulle_falla`."""
    if not aktiv():
        return None
    rader = _rader(_utan_personuppgifter(utdrag))
    try:
        svar = await fraga(_state(profil, kandidat, rader, signaler), _fragor(profil, rader))
    except Exception as fel:  # noqa: BLE001 — fail open, se modulens docstring
        logger.warning("Jev-triagen svarade inte (%s) — kandidaten går vidare.", type(fel).__name__)
        return {"lage": lage(), "fel": type(fel).__name__, "beslut": "vidare"}
    tolkat = _tolka(profil, svar, rader)
    skulle_falla = bool(tolkat["fall_skal"])
    return {
        "lage": lage(),
        **tolkat,
        "skulle_falla": skulle_falla,
        # jev_bortval (app/leads/automation.py) False: kunden vill se allt Jev
        # skulle ha fällt — bedömningen sparas, men kandidaten går vidare.
        "beslut": (
            "fall"
            if skulle_falla and lage() == "pa" and profil.get("jev_bortval", True) is not False
            else "vidare"
        ),
    }


async def klassa(profil: dict[str, Any], kandidat: dict[str, Any], *, sammanfattning: str,
                 signaler: list[str]) -> dict[str, Any] | None:
    """Kalibrerad bedömning EFTER researchen — trafikpolisens nivå.

    hög = människan bör se det nu, mellan = AI-utkast räcker, låg = lägg
    undan. Påverkar aldrig kodens nivå; sparas för jämförelse och visning."""
    if not aktiv():
        return None
    rader = _rader(_utan_personuppgifter(sammanfattning))
    fragor = {
        "bra_lead": {
            "type": "noul",
            "instructions": "Is this company a good sales lead for the seller, given the target group and the research summary?",
        },
        "insats": {
            "type": "choice",
            "instructions": "How much sales effort is this lead likely to need?",
            "criteria": {"lag": "Ready: clear fit and clear need", "mellan": "Needs convincing", "hog": "Unclear fit or need"},
        },
    }
    try:
        svar = await fraga(_state(profil, kandidat, rader, signaler), fragor)
    except Exception as fel:  # noqa: BLE001
        logger.warning("Jev-klassningen svarade inte (%s).", type(fel).__name__)
        return {"lage": lage(), "fel": type(fel).__name__}
    p = (svar.get("bra_lead") or {}).get("noul")
    niva = None
    if isinstance(p, (int, float)):
        niva = "hög" if p >= 0.75 else "mellan" if p >= 0.4 else "låg"
    return {"lage": lage(), "sannolikhet": p, "trafikniva": niva,
            "insats": (svar.get("insats") or {}).get("choice")}


def statistik(prospekt: list[dict[str, Any]]) -> dict[str, Any]:
    """Jev mot kodens bedömning, över kundens researchade bolag.

    Det här är mätningen som avgör om läge "pa" är säkert (plan fas 3):
    ett FALSKT BORTVAL är ett bolag Jev hade fällt men som researchen
    kvalificerade (nivå A/B) — det enda felet som kostar kunden ett lead."""
    triagerade = [p for p in prospekt if isinstance((p.get("jev") or {}).get("triage"), dict)]
    bedomda = [p for p in triagerade if p.get("niva")]
    skulle_falla = [p for p in bedomda if p["jev"]["triage"].get("skulle_falla")]
    falska = [p for p in skulle_falla if p["niva"] in ("A", "B")]
    klassade = [
        p for p in prospekt
        if p.get("niva") and isinstance((p.get("jev") or {}).get("klassning"), dict)
        and p["jev"]["klassning"].get("trafikniva")
    ]
    overens = [
        p for p in klassade
        if (p["jev"]["klassning"]["trafikniva"] == "hög") == (p["niva"] == "A")
        and (p["jev"]["klassning"]["trafikniva"] == "låg") == (p["niva"] == "C")
    ]
    return {
        "lage": lage(),
        "triagerade": len(triagerade),
        "bedomda_efter_triage": len(bedomda),
        "jev_skulle_falla": len(skulle_falla),
        "falska_bortval": len(falska),
        "falska_bortval_andel": round(len(falska) / len(skulle_falla), 3) if skulle_falla else None,
        "klassade": len(klassade),
        "klassning_overens_med_niva": round(len(overens) / len(klassade), 3) if klassade else None,
        "falska_bortval_bolag": [p.get("company_name") for p in falska][:20],
    }


def demo() -> None:
    profil = {
        "malgrupp": "Småbolag i Göteborg",
        "kriterier": [{"id": "k1", "text": "Has an old website", "krav": "maste"}],
        "uteslut": [{"text": "a staffing agency"}],
    }
    rader = ["Välkommen", "© 2012 Bolaget"]
    f = _fragor(profil, rader)
    assert set(f) == {"fit", "krav_k1", "uteslut_u1", "stodrad"}
    t = _tolka(profil, {"krav_k1": {"noul": 0.03}, "stodrad": {"choice": "L001"}, "fit": {"score": 0.4}}, rader)
    assert t["fall_skal"] and t["stodrad"] == "© 2012 Bolaget"
    assert "[e-post]" in _utan_personuppgifter("maila anna@bolag.se")
    assert _utan_personuppgifter("Ring 031-123 45 67\n© 2011") == "Ring [telefon]\n© 2011"
    print("jev: ok")


if __name__ == "__main__":
    demo()
