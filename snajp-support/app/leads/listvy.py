"""Leadslistornas läsväg: vad en rad bär, vilka rader som syns, och hur
körningslistan sammanfattas.

Sebbe 2026-11-15: med 4 400 utkast i development laggade Snajp på varje sida.
Uppmätt samma dag hos den största kunden (5 615 prospekt):

- Iris-listan hämtade 9,6 MB i sex anrop efter varandra (~3,5 s), varje rad
  med hela researchen (`score_breakdown`, `lagesbeskrivning`, `jev` …), och
  varje sida läste om kundens alla utkast och hela statusloggen.
- Översikten hämtade samma 9,6 MB för att räkna två munkdiagram.
- Körningslistan var 2,8 MB för 100 körningar, 78 % av det trattens
  bortvalda bolag och 20 % barnjobben, som bara den utfällda raden visar.

Härifrån: listläget (`?lista=1`) bär bara det tabellen visar, fördelningen
räknas på servern, och körningslistan bär antal i stället för listor. Den
fulla raden finns kvar för lådan (`GET /leads/prospects/{id}`) och den fulla
körningen för detaljen (`GET /leads/korningar/{id}`).
"""
from __future__ import annotations

import re
from typing import Any, Iterable

from ..config import DEFAULT_TENANT_ID

#: Kolumnerna listläget läser ur `prospects`. Det tabellen visar per rad, plus
#: det synlighetsfiltret nedan behöver (origin, niva, qualified, arkiverad_at).
#: Researchen (score_breakdown, lagesbeskrivning, jev, signaler) lämnar inte
#: databasen här: den var 75 % av listans vikt och visas bara i lådan.
LISTKOLUMNER: tuple[str, ...] = (
    "id",
    "company_name",
    "contact_name",
    "contact_email",
    "contact_phone",
    "status",
    "origin",
    "niva",
    "qualified",
    "score_total",
    "icp_fit",
    "created_at",
    "website",
    "ort",
    "motivering",
    "disqualifiers",
    "webbrevision",
    "arkiverad_at",
)

#: Det fördelningen (Översiktens munkdiagram) räknar på: status, kontaktväg
#: och synligheten. Inga texter alls.
FORDELNINGSKOLUMNER: tuple[str, ...] = (
    "id",
    "status",
    "origin",
    "niva",
    "qualified",
    "arkiverad_at",
    "contact_email",
    "contact_phone",
)

#: Raden visar motiveringens första mening, avklippt i två rader (LeadsTabell:
#: forstaMening + line-clamp-2). Längre än så syns aldrig.
MENINGSTAK = 300

_MENINGSSLUT = re.compile(r"[.!?](\s|$)")


def forsta_mening(text: Any) -> str | None:
    """Samma regel som LeadsTabell.forstaMening: fram till första punkt,
    utrops- eller frågetecken som följs av blanksteg eller slut, och aldrig
    längre än MENINGSTAK tecken."""
    if text is None:
        return None
    text = str(text)
    traff = _MENINGSSLUT.search(text)
    if traff and traff.start() > 0:
        text = text[: traff.start() + 1]
    return text[:MENINGSTAK]


def synliga(
    prospects: Iterable[dict[str, Any]],
    *,
    tenant_id: str,
    kopplade: set[str],
    arkiverade: bool = False,
    bortvalda: bool = False,
) -> list[dict[str, Any]]:
    """Raderna Iris-listan visar, i samma ordning — regeln som
    GET /leads/prospects alltid haft, på ett ställe så att fördelningen
    räknar exakt samma leads som listan visar:

    - exempelbolag bara hos demotenanten,
    - aldrig ringlistans bolag (origin 'ring', leadsregel 15),
    - aldrig en listas bakgrundsprospekt (migration 110),
    - arkiverade bara på begäran (`arkiverade`), och då alla arkiverade,
    - bortvalda (nivå C eller underkända) bara på begäran (`bortvalda`).
    """
    ut = []
    for p in prospects:
        if tenant_id != DEFAULT_TENANT_ID and p.get("origin") == "example":
            continue
        if p.get("origin") == "ring":
            continue
        if str(p["id"]) in kopplade:
            continue
        if bool(p.get("arkiverad_at")) != arkiverade:
            continue
        if not arkiverade and (p.get("niva") == "C" or p.get("qualified") is False) != bortvalda:
            continue
        ut.append(p)
    return ut


def listrad(rad: dict[str, Any]) -> dict[str, Any]:
    """En rad i listläget: det tabellen visar och inget mer.

    - Motiveringen som sin första mening, och underkännandets första skäl
      (Bortvalda visar det; raden faller tillbaka på det, LeadsTabell.forstaMening).
    - Webbrevisionen som betyget och den första bristen; den finns bara kvar
      här om kunden får se den (webbpool.dolj körs före).
    - Fält utan värde utelämnas: en tom nyckel per rad och fält var en
      tredjedel av listans vikt, och vyn läser dem som saknade ändå.
    """
    ut: dict[str, Any] = {}
    for falt, varde in rad.items():
        if falt in ("motivering", "disqualifiers", "webbrevision", "qualified", "tenant_id"):
            continue
        if varde is None:
            continue
        ut[falt] = varde
    ut.setdefault("company_name", rad.get("company_name") or "")
    ut.setdefault("status", rad.get("status") or "new")
    motivering = rad.get("motivering")
    if motivering is not None:
        ut["motivering"] = forsta_mening(motivering)
    # Det första skälet till underkännandet, helt: Bortvalda-panelen visar det
    # före motiveringen, och raden faller tillbaka på det utan motivering.
    skal = rad.get("disqualifiers")
    if isinstance(skal, (list, tuple)) and skal:
        ut["disqualifiers"] = [str(skal[0])[:MENINGSTAK]]
    webb = rad.get("webbrevision")
    if isinstance(webb, dict):
        brister = webb.get("brister")
        ut["webbrevision"] = {
            "modernitet": webb.get("modernitet"),
            "brister": list(brister[:1]) if isinstance(brister, (list, tuple)) else [],
        }
    return ut


def kontaktvag(rad: dict[str, Any]) -> str:
    """Samma uppdelning som lib/leads/suite.ts:kontaktvagAv."""
    tel = bool(str(rad.get("contact_phone") or "").strip())
    mejl = bool(str(rad.get("contact_email") or "").strip())
    return "bada" if tel and mejl else "telefon" if tel else "mejl" if mejl else "saknas"


def fordelning(rader: Iterable[dict[str, Any]], i_research: set[str]) -> dict[str, Any]:
    """Antal per status och per kontaktväg för de synliga raderna. Status
    'researching' härleds som i listan: ett Ny-bolag vars researchjobb är köat
    eller körs."""
    per_status: dict[str, int] = {}
    per_vag: dict[str, int] = {"bada": 0, "telefon": 0, "mejl": 0, "saknas": 0}
    antal = 0
    for p in rader:
        antal += 1
        status = p.get("status") or "new"
        if status == "new" and str(p["id"]) in i_research:
            status = "researching"
        per_status[status] = per_status.get(status, 0) + 1
        per_vag[kontaktvag(p)] += 1
    return {"antal": antal, "status": per_status, "kontaktvag": per_vag}


#: Körningens listor som bara den utfällda raden visar. I listan står de som
#: antal (`tratt_antal`, `jobs_antal`); hela listorna ger GET /leads/korningar/{id}.
SAMMANDRAG_BORT = ("tratt", "jobs")


def korning_sammandrag(korning: Any) -> Any:
    """Körningens tillstånd utan trattens och barnjobbens listor, med antalet
    kvar. Samma form som Postgres bygger i SQL (storage.postgres:
    _KORNING_SQL_SAMMANDRAG), så att båda lagringarna svarar likadant."""
    if not isinstance(korning, dict):
        return korning
    ut = {f: v for f, v in korning.items() if f not in SAMMANDRAG_BORT}
    for falt in SAMMANDRAG_BORT:
        lista = korning.get(falt)
        ut[f"{falt}_antal"] = len(lista) if isinstance(lista, list) else 0
    return ut
