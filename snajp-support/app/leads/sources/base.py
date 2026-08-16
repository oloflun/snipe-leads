"""Protokollet en prospektkälla uppfyller, och posten den lämnar ifrån sig."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class SourceError(RuntimeError):
    """Källan kunde inte svara. Skiljd från 'källan svarade tomt', som är ett
    giltigt utfall och returneras som en tom lista."""


@dataclass(frozen=True)
class Prospect:
    """Ett kandidatbolag, innan agenten researchat det.

    Fälten är medvetet få. En källa som kan fylla i mer ska lägga det i
    `extra` i stället för att utöka den här klassen — annars blir varje ny
    leverantör en ändring i en datastruktur som alla andra källor delar.
    """

    company_name: str
    orgnr: str | None = None
    ort: str | None = None
    postnr: str | None = None
    sni: str | None = None
    website: str | None = None
    contact_email: str | None = None
    anstallda: int | None = None
    omsattning: int | None = None
    #: Varifrån uppgiften kom. Krävs för GDPR art. 14 ("varifrån uppgiften
    #: kom") och för prospect_quality_gate:s krav på källräkning — den är
    #: alltså inte metadata, den är ett produktkrav.
    source_name: str = "okänd"
    source_url: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def epost_ar_personlig(self) -> bool:
        """`fornamn.efternamn@` snarare än `info@`.

        Avgör om GDPR art. 14-texten KRÄVS i mejlet (send_guard regel 4).
        Heuristiken är medvetet försiktig: en punkt i lokaldelen räcker för
        att flagga. Att felaktigt flagga en funktionsadress kostar en extra
        informationsruta i mejlet; att missa en personlig adress kostar ett
        regelbrott.
        """
        if not self.contact_email or "@" not in self.contact_email:
            return False
        lokaldel = self.contact_email.split("@", 1)[0].strip().lower()
        funktionella = {
            "info", "kontakt", "kontor", "order", "kundtjanst", "kundtjänst",
            "support", "hej", "hallo", "mail", "post", "reception", "sales",
            "forsaljning", "försäljning", "ekonomi", "faktura", "bokning",
        }
        if lokaldel in funktionella:
            return False
        return "." in lokaldel or "-" in lokaldel


class ProspectSource(Protocol):
    """En källa är allt som kan svara på 'vilka bolag matchar det här ICP:t'.

    `search` tar HELA ICP:t, inte enskilda parametrar. Skälet: en källa som
    kan filtrera på sin egen sida (ett register med SNI-parameter i API:t)
    ska kunna göra det, medan en som inte kan (en CSV) filtrerar lokalt.
    Hade signaturen varit `search(sni, geo, size)` hade varje nytt ICP-fält
    krävt en ändring i varenda implementation.
    """

    #: Namnet som hamnar i `Prospect.source_name` och i granskningsvyn.
    name: str

    def search(self, icp: dict[str, Any]) -> list[Prospect]: ...
