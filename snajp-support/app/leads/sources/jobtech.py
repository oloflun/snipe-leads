"""JobTech/Platsbanken som prospektkälla — jobbannonsen ÄR köpsignalen.

Arbetsförmedlingens JobSearch-API (jobsearch.api.jobtechdev.se) är öppna
myndighetsdata: gratis, nyckellöst för sökning, och uttryckligen publicerat
för maskinell användning (JobTech Dev). TOS-bedömning: publik API-yta med
öppen licens — ingen skrapning, inga användarvillkor bryts (jfr modulens
__init__-regel om allabolag/hitta/ratsit).

Varför jobbannonser: ett bolag som rekryterar kundtjänst/innesälj berättar
själv att volymen växer — det är den starkaste gratis köpsignalen som finns
för svensk SMB, och den ersätter det breda Gemini-sökandet i stället för
att komplettera det (kostnadsarbetet 2026-09-02). Annonsen ger dessutom
arbetsgivarnamn, ort och ofta webbadress.

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

#: Yrkesord som signalerar att bolaget drunknar i kundfrågor — det är DE
#: annonserna som är köpsignal för en supportagent, inte vilken rekrytering
#: som helst. Ordlistan är en startpunkt; ICP:ns roles läggs ovanpå.
_SIGNALROLLER = ("kundtjänst", "kundservice", "innesälj", "kundsupport", "ordermottagning")


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
        geografi = str(icp.get("geography") or "").strip()
        roller = [str(r).strip() for r in (icp.get("roles") or []) if str(r).strip()]
        termer = list(dict.fromkeys([*_SIGNALROLLER[:3], *roller[:2]]))

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
