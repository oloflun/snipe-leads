"""Bolagsnyheter via RSS som signalkälla — pressmeddelandet är triggern.

RSS är ett publiceringsformat AVSETT för maskinell läsning: den som lägger
ut ett flöde ber omvärlden prenumerera på det. TOS-bedömningen (jfr
modulregeln i sources/__init__.py om vad som inte får bli en källa): att
läsa ett publikt RSS-flöde är inte skrapning och bryter inga villkor —
till skillnad från att skrapa sajternas HTML. Flödes-URL:erna är
konfigurerbara (env LEADS_NYHETS_RSS, kommaseparerad) så att ett byte av
leverantör eller ett ändrat URL-mönster aldrig är en kodändring.

Default är MyNewsdesk:s publika söka-i-pressrum-flöde: svenska SMB använder
MyNewsdesk brett, och ett pressmeddelande om expansion/nyetablering/ny
tjänst är exakt den trigger_event-signal research-steget vill grunda mejlet
i. Källan ger BOLAGSNAMN + signal — aldrig personuppgifter; kontaktpersonen
hämtas som alltid från bolagets egen webbplats i research-steget.

Parsningen är stdlib (xml.etree) — inga nya beroenden för ett RSS-flöde.
"""

from __future__ import annotations

import logging
import os
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from .base import Prospect, ProspectSource, SourceError

logger = logging.getLogger("snajp-support.leads.sources.nyheter")

#: %s ersätts med den URL-kodade söktermen (bransch/geografi ur ICP:t).
_DEFAULT_FEEDS = "https://www.mynewsdesk.com/se/search/rss?query=%s"

#: Nyhetsord som utgör en KÖPSIGNAL (expansion = växtvärk = kundfrågor).
_SIGNALORD = ("expander", "nyetabl", "nytt kontor", "rekryter", "växer", "lanser", "förvärv")


class NyhetsSource(ProspectSource):
    name = "nyheter"

    def __init__(self, *, timeout: float = 10.0, max_poster: int = 40) -> None:
        self._timeout = timeout
        self._max = max_poster
        self._feed_mallar = [
            u.strip()
            for u in (os.environ.get("LEADS_NYHETS_RSS") or _DEFAULT_FEEDS).split(",")
            if u.strip()
        ]

    def search(self, icp: dict[str, Any]) -> list[Prospect]:
        from urllib.parse import quote

        branscher = [str(b).strip() for b in (icp.get("industries") or []) if str(b).strip()]
        geografi = str(icp.get("geography") or "").strip()
        termer = [f"{b} {geografi}".strip() for b in branscher[:2]] or ([geografi] if geografi else [])
        if not termer:
            return []

        prospekt: dict[str, Prospect] = {}
        try:
            with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
                for mall in self._feed_mallar:
                    for term in termer:
                        url = mall.replace("%s", quote(term)) if "%s" in mall else mall
                        svar = client.get(url, headers={"accept": "application/rss+xml"})
                        svar.raise_for_status()
                        for p in self._parsa_feed(svar.text):
                            if p.company_name.casefold() not in prospekt:
                                prospekt[p.company_name.casefold()] = p
        except httpx.HTTPError as fel:
            if prospekt:
                logger.warning("Nyhetsflödet föll halvvägs: %s", fel)
                return list(prospekt.values())
            raise SourceError(f"Nyhetsflödet svarade inte: {fel}") from fel
        return list(prospekt.values())

    def _parsa_feed(self, xml_text: str) -> list[Prospect]:
        """RSS-items -> Prospect. Bolagsnamnet tas ur dc:creator (MyNewsdesk
        sätter pressrummets namn där) med titeln som fallback-heuristik.
        Poster utan signalord filtreras — en produktnyhet utan växtsignal är
        brus, inte en trigger."""
        try:
            rot = ET.fromstring(xml_text)
        except ET.ParseError:
            logger.warning("Nyhetsflödet gick inte att tolka som XML.")
            return []
        ns = {"dc": "http://purl.org/dc/elements/1.1/"}
        resultat: list[Prospect] = []
        for item in rot.iter("item"):
            titel = (item.findtext("title") or "").strip()
            lank = (item.findtext("link") or "").strip() or None
            skapare = (item.findtext("dc:creator", namespaces=ns) or "").strip()
            text = f"{titel} {(item.findtext('description') or '')}".lower()
            if not any(ord in text for ord in _SIGNALORD):
                continue
            namn = skapare or None
            if not namn:
                continue
            resultat.append(
                Prospect(
                    company_name=namn,
                    source_name="nyheter",
                    source_url=lank,
                    extra={"signal": "bolagsnyhet", "nyhet_titel": titel},
                )
            )
            if len(resultat) >= self._max:
                break
        return resultat
