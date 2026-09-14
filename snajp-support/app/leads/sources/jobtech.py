"""JobTech/Platsbanken som prospektkälla — jobbannonsen ÄR köpsignalen.

Arbetsförmedlingens JobSearch-API (jobsearch.api.jobtechdev.se) är öppna
myndighetsdata: gratis, nyckellöst för sökning, och uttryckligen publicerat
för maskinell användning (JobTech Dev). TOS-bedömning: publik API-yta med
öppen licens — ingen skrapning, inga användarvillkor bryts (jfr modulens
__init__-regel om allabolag/hitta/ratsit).

Varför jobbannonser: ett bolag i kundens målbransch som rekryterar berättar
själv att det växer — den starkaste gratis köpsignalen som finns för svensk
SMB, och den ersätter det breda Gemini-sökandet i stället för att
komplettera det (kostnadsarbetet 2026-09-02). Annonsen ger dessutom
arbetsgivarnamn, ort och ofta webbadress. Sökorden är kundens, se
`sokord_for`.

GDPR (INV-DATA-001): posterna är BOLAGSDATA (arbetsgivare, ort, annons-URL).
Kontaktpersoner ur annonser tas medvetet INTE med — kontaktpersonen hämtas
alltid från bolagets egen webbplats i research-steget, precis som förr.
`source_url` pekar på annonsen så art. 14-frågan "varifrån kom uppgiften"
alltid kan besvaras.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .base import Prospect, ProspectSource, SourceError

logger = logging.getLogger("snajp-support.leads.sources.jobtech")

API_URL = "https://jobsearch.api.jobtechdev.se/search"

#: Sökorden kommer ur KUNDENS målgrupp, aldrig ur en fast lista.
#:
#: Fram till 2026-09-15 sökte källan alltid på "kundtjänst", "kundservice"
#: och "innesälj" — Snajps EGEN köpsignal (ett bolag som rekryterar
#: kundtjänst behöver en supportagent) — plus ICP:ns roller, och branscherna
#: lästes aldrig. Uppmätt som kunden Nordform Kontor (säljer skrivbord,
#: branscher IT-konsulter/redovisningsbyråer, Stockholm/Göteborg): alla fem
#: bolagen kom från frågan "kundtjänst Stockholm Göteborg" — SafeTeam,
#: PitchPoint, CHUOMO SERVICE — och fyllde körningen, så Gemini-utfyllnaden
#: som faktiskt ser branscherna kördes aldrig. Roller används inte heller:
#: "VD Stockholm" ger rekryteringsfirmor och storbolag som söker en VD.
#:
#: Fritext ur "Signaler som krävs" (leadslistornas titel hamnar där) används
#: bara när den är kort nog att vara ett sökord. En hel mening som fråga ger
#: slumpträffar; då är ingen källträff bättre, och Gemini tolkar fritexten.
_MAX_ORD_I_FRITEXT = 3

#: Annonsören är inte alltid arbetsgivaren: bemannings- och rekryteringsbolag
#: annonserar åt sina kunder, och en branschsökning ("redovisningsbyrå
#: Stockholm") ger dem överst. De är aldrig bolaget som annonsen handlar om.
_FORMEDLARORD = ("rekryter", "bemanning", "recruit", "staffing")
_FORMEDLARE = (
    "academic work",
    "randstad",
    "manpower",
    "adecco",
    "experis",
    "poolia",
    "proffice",
    "studentconsulting",
    "uniflex",
    "lernia",
)


def ar_formedlare(namn: str) -> bool:
    """True för bemannings- och rekryteringsbolag som annonserar åt andra."""
    rent = namn.casefold()
    return any(ord in rent for ord in (*_FORMEDLARORD, *_FORMEDLARE))


def sokord_for(icp: dict[str, Any]) -> list[str]:
    """Sökorden för en målgrupp: branscher först, annars korta nischord.

    Tom lista betyder att målgruppen inte går att ställa som annonsfråga —
    källan ska då inte söka alls, inte falla tillbaka på en fast ordlista.
    """
    branscher = [str(b).strip() for b in (icp.get("industries") or []) if str(b).strip()]
    if branscher:
        return list(dict.fromkeys(branscher[:2]))
    nisch = [
        str(n).strip()
        for n in (icp.get("must_have") or [])
        if str(n).strip() and len(str(n).split()) <= _MAX_ORD_I_FRITEXT
    ]
    return list(dict.fromkeys(nisch[:2]))


class JobTechSource(ProspectSource):
    name = "jobtech"

    def __init__(self, *, timeout: float = 10.0, max_per_sokning: int = 25) -> None:
        self._timeout = timeout
        self._max = max_per_sokning

    def search(self, icp: dict[str, Any]) -> list[Prospect]:
        """En sökning per signalroll-term (cappad), dedup på arbetsgivare.

        `q` är fritext och `municipality`-koder undviks med flit — ICP:ns
        geografi läggs i frågesträngen i stället, så en ny ort aldrig kräver
        en kodtabell. Fel mot API:t blir SourceError (federation hoppar
        vidare); tomt svar är ett giltigt utfall och ger tom lista.
        """
        # geography är en LISTA i ICP:n (se api/leads.py: icp["geography"][0],
        # exempelbolag.py: or []). str() på listan gav "['Umeå']" rakt in i
        # frågesträngen — uppmätt i development 2026-09-06: sökningen blev
        # "Inköpschef ['Umeå']" och träffarna hade inget med branschen att
        # göra. En sträng accepteras också, för anropare som redan joinat.
        geo_ra = icp.get("geography") or ""
        if isinstance(geo_ra, (list, tuple, set)):
            geografi = " ".join(str(g).strip() for g in geo_ra if str(g).strip())
        else:
            geografi = str(geo_ra).strip()
        termer = sokord_for(icp)
        if not termer:
            return []

        prospekt: dict[str, Prospect] = {}
        try:
            with httpx.Client(timeout=self._timeout) as client:
                for term in termer:
                    fraga = f"{term} {geografi}".strip()
                    svar = client.get(
                        API_URL,
                        params={"q": fraga, "limit": self._max, "offset": 0},
                        headers={"accept": "application/json"},
                    )
                    svar.raise_for_status()
                    for hit in (svar.json() or {}).get("hits", []):
                        p = self._till_prospekt(hit)
                        if p and p.company_name.casefold() not in prospekt:
                            prospekt[p.company_name.casefold()] = p
        except httpx.HTTPError as fel:
            if prospekt:
                # Delresultat är bättre än inget — logga och leverera det vi fick.
                logger.warning("JobTech-sökningen föll halvvägs: %s", fel)
                return list(prospekt.values())
            raise SourceError(f"JobTech-API:t svarade inte: {fel}") from fel
        return list(prospekt.values())

    @staticmethod
    def _till_prospekt(hit: dict[str, Any]) -> Prospect | None:
        arbetsgivare = (hit.get("employer") or {}).get("name")
        if not arbetsgivare or not str(arbetsgivare).strip():
            return None
        namn = str(arbetsgivare).strip()
        # Offentlig sektor är aldrig ett leads-prospekt för SMB-produkten.
        if any(ord in namn.lower() for ord in ("kommun", "region ", "myndighet", "landsting")):
            return None
        if ar_formedlare(namn):
            return None
        adress = hit.get("workplace_address") or {}
        webb = (hit.get("employer") or {}).get("url") or None
        annons_url = hit.get("webpage_url") or None
        return Prospect(
            company_name=namn,
            ort=(adress.get("municipality") or None),
            website=str(webb).strip() if webb else None,
            source_name="jobtech",
            source_url=str(annons_url) if annons_url else None,
            extra={
                "signal": "rekryterar",
                "annons_titel": hit.get("headline"),
                # Annonsens yrke — låter kvalificeringen se VAD de rekryterar.
                "yrke": ((hit.get("occupation") or {}).get("label")),
            },
        )
