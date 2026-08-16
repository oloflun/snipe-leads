"""CSV-källan — den enda som är påkopplad.

Vår egen lista, manuellt sammanställd ur bolagens egna publika sajter. Den
finns för att hela kedjan (ICP → urval → scoring → utkast) ska gå att köra och
granska utan att någon extern leverantör är inkopplad, och för att den
körningen ska vara reproducerbar: samma fil ger samma lista, varje gång.

Kolumnnamnen är svenska och matchar `fixtures/prospects-*.csv`. Okända
kolumner hamnar i `Prospect.extra` i stället för att kastas — en källa som
lägger till ett fält ska inte tvinga fram en kodändring här.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from ..scoring import score_prospect
from .base import Prospect, ProspectSource, SourceError

#: CSV-kolumn → fält på Prospect. Allt utanför den här mappningen följer med
#: som `extra`.
KOLUMNER = {
    "foretagsnamn": "company_name",
    "orgnr": "orgnr",
    "ort": "ort",
    "postnr": "postnr",
    "sni": "sni",
    "hemsida": "website",
    "kontaktadress": "contact_email",
    "anstallda": "anstallda",
    "omsattning": "omsattning",
    "kalla": "source_url",
}

HELTALSFALT = {"anstallda", "omsattning"}


class CsvSource(ProspectSource):
    """Läser prospekt ur en lokal CSV och filtrerar dem mot ett ICP."""

    def __init__(self, path: str | Path, *, name: str | None = None) -> None:
        self.path = Path(path)
        self.name = name or f"csv:{self.path.name}"

    def search(self, icp: dict[str, Any]) -> list[Prospect]:
        """Returnerar de prospekt som PASSERAR ICP:t, bäst först.

        Diskvalificerade bolag returneras INTE. De är inte sämre träffar, de
        är fel träffar — och en lista där de ligger kvar längst ner är en
        lista någon förr eller senare mejlar hela.

        Motiveringen för varje bortval finns kvar i `search_med_bortval` för
        granskningsvyn. Att kasta bort den hade gjort ett för snävt ICP
        omöjligt att felsöka: kunden hade sett en tom lista utan att veta att
        det var det egna postnummerfiltret som tömde den.
        """
        traffar, _ = self.search_med_bortval(icp)
        return traffar

    def search_med_bortval(
        self, icp: dict[str, Any]
    ) -> tuple[list[Prospect], list[tuple[Prospect, dict[str, Any]]]]:
        rader = self._las()

        traffar: list[tuple[int, Prospect, dict[str, Any]]] = []
        bortvalda: list[tuple[Prospect, dict[str, Any]]] = []

        for prospect in rader:
            score = score_prospect(prospect, icp)
            if score.diskvalificerad:
                bortvalda.append((prospect, score.as_dict()))
                continue
            traffar.append((score.total, prospect, score.as_dict()))

        # Högst poäng först. Vid lika poäng avgör bolagsnamnet, så att två
        # körningar på samma fil ger samma ordning — en ostabil sortering hade
        # gjort "de tre bästa utkasten" till olika bolag mellan körningarna.
        traffar.sort(key=lambda rad: (-rad[0], rad[1].company_name.casefold()))

        tak = icp.get("max_prospects_per_run") or len(traffar)
        valda = [
            _med_score(prospect, score) for _, prospect, score in traffar[: int(tak)]
        ]
        return valda, bortvalda

    def _las(self) -> list[Prospect]:
        if not self.path.exists():
            raise SourceError(
                f"Prospektfilen {self.path} finns inte. CSV-källan läser en fil vi "
                "själva underhåller — kontrollera sökvägen i körningens konfiguration."
            )

        try:
            text = self.path.read_text(encoding="utf-8-sig")
        except OSError as error:
            raise SourceError(f"Kunde inte läsa {self.path}: {error}") from error

        läsare = csv.DictReader(text.splitlines())
        if not läsare.fieldnames:
            raise SourceError(f"{self.path} saknar rubrikrad.")

        saknade = {"foretagsnamn"} - {f.strip().lower() for f in läsare.fieldnames}
        if saknade:
            raise SourceError(
                f"{self.path} saknar kolumnen 'foretagsnamn'. Utan bolagsnamn finns "
                "inget prospekt att skapa."
            )

        prospekt: list[Prospect] = []
        for radnr, rad in enumerate(läsare, start=2):
            prospect = self._rad_till_prospect(rad, radnr)
            if prospect is not None:
                prospekt.append(prospect)
        return prospekt

    def _rad_till_prospect(self, rad: dict[str, Any], radnr: int) -> Prospect | None:
        värden: dict[str, Any] = {}
        extra: dict[str, Any] = {"radnr": radnr}

        for rå_kolumn, rå_värde in rad.items():
            if rå_kolumn is None:
                continue
            kolumn = rå_kolumn.strip().lower()
            värde = (rå_värde or "").strip()
            fält = KOLUMNER.get(kolumn)
            if fält is None:
                if värde:
                    extra[kolumn] = värde
                continue
            if fält in HELTALSFALT:
                värden[fält] = _som_heltal(värde)
            else:
                värden[fält] = värde or None

        namn = (värden.pop("company_name", None) or "").strip()
        if not namn:
            # En tom rad i en handunderhållen fil är ett skrivfel, inte ett
            # bolag. Att tyst hoppa över den är rätt; att skapa ett prospekt
            # utan namn hade gett ett mejl adresserat till ingenting.
            return None

        return Prospect(
            company_name=namn,
            source_name=self.name,
            extra=extra,
            **värden,
        )


def _med_score(prospect: Prospect, score: dict[str, Any]) -> Prospect:
    """Scoren följer med prospektet i `extra`, inte som ett eget fält.

    Skälet står i `base.Prospect`: en källa som kan mer ska inte tvinga fram
    en ändring i datastrukturen alla källor delar. Scoringen är dessutom
    ICP-beroende — samma bolag har olika poäng för två kunder, och ett fält
    på prospektet hade antytt att poängen hör till bolaget.
    """
    return Prospect(
        company_name=prospect.company_name,
        orgnr=prospect.orgnr,
        ort=prospect.ort,
        postnr=prospect.postnr,
        sni=prospect.sni,
        website=prospect.website,
        contact_email=prospect.contact_email,
        anstallda=prospect.anstallda,
        omsattning=prospect.omsattning,
        source_name=prospect.source_name,
        source_url=prospect.source_url,
        extra={**prospect.extra, **score},
    )


def _som_heltal(värde: str) -> int | None:
    siffror = "".join(t for t in värde if t.isdigit())
    if not siffror:
        return None
    try:
        return int(siffror)
    except ValueError:  # pragma: no cover
        return None
