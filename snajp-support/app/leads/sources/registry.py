"""Registerkällorna — båda stubbar, båda med skälet utskrivet.

De finns som stubbar och inte som TODO-kommentarer för att protokollet ska
vara bevisat bärkraftigt av mer än en implementation. En abstraktion med
exakt en implementation är en gissning om framtiden; den här har tre former
att passa, och `search(icp)`-signaturen räcker till alla.

Ingen av dem får implementeras genom att skrapa respektive webbplats. Se
`sources/__init__.py`.
"""

from __future__ import annotations

from typing import Any

from .base import Prospect, ProspectSource


class BolagsverketSource(ProspectSource):
    """Bolagsverkets officiella företagsregister.

    KRÄVER LICENS. Bolagsverket säljer åtkomst till Näringslivsregistret via
    ett avtalat API — det är inte öppna data, och det finns ingen fri
    slutpunkt att peka om den här klassen mot.

    Vad avtalet behöver täcka innan klassen går att skriva:

    * Sökning på SNI-kod och säte/kommun, vilket är exakt det ICP:t frågar
      efter. Kan registret inte filtrera på det måste vi hämta brett och
      filtrera lokalt, och då blir volymen (och priset) en helt annan fråga.
    * Rätt att LAGRA träffarna hos oss. Ett API som bara får läsas i stunden
      går inte att bygga en granskningskö på.
    * Vidareförmedling till våra kunder — det är hyreskunden, inte vi, som
      till slut kontaktar bolaget.

    Kontaktuppgifter ingår INTE i registret. Bolagsverket ger firmanamn,
    org.nr, säte och verksamhetsbeskrivning; e-postadressen måste komma
    någon annanstans ifrån — i praktiken bolagets egen sajt.
    """

    name = "bolagsverket"

    def search(self, icp: dict[str, Any]) -> list[Prospect]:
        raise NotImplementedError(
            "BolagsverketSource kräver ett licensavtal för Näringslivsregistret. "
            "Se klassens docstring för vad avtalet måste täcka. Använd CsvSource "
            "tills avtalet finns."
        )


class AllabolagSource(ProspectSource):
    """Allabolag.se via deras BETALDA API.

    Skillnaden som avgör allt: allabolag.se har ett kommersiellt API, och det
    är lagligt att köpa. Att skrapa samma uppgifter ur deras webbplats är det
    inte — det bryter mot användarvillkoren, och en produkt vars datainsamling
    är ett kontraktsbrott går inte att sälja till ett bolag som gör
    leverantörsgranskning.

    Den här klassen får alltså bara implementeras mot API:t, aldrig mot HTML.

    Vad API:t skulle ge utöver Bolagsverket: omsättning och antal anställda —
    alltså precis `size`-fälten i ICP:t, som CSV-källan i dag bara har när
    någon fyllt i dem för hand.
    """

    name = "allabolag"

    def search(self, icp: dict[str, Any]) -> list[Prospect]:
        raise NotImplementedError(
            "AllabolagSource kräver en abonnemangsnyckel till allabolag.se:s API. "
            "Skrapa ALDRIG webbplatsen som ersättning — det bryter mot deras "
            "användarvillkor. Använd CsvSource tills nyckeln finns."
        )
