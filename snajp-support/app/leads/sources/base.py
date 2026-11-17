"""Protokollet en prospektkälla uppfyller, och posten den lämnar ifrån sig."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


#: Lokaldelar som är en funktion och inte en person (gemener, utan diakriter).
#: Den avgörande listan för sidfoten: en lokaldel som inte står här, eller i
#: discovery.AVDELNINGSORD, räknas som personlig (se epost_ar_personlig).
FUNKTIONSADRESSER = frozenset(
    {
        "info", "kontakt", "kontor", "kontoret", "order", "orders", "kundtjanst", "kundservice",
        "customerservice", "support", "service", "hej", "hallo", "hello", "hi", "mail", "post",
        "reception", "sales", "salj", "forsaljning", "ekonomi", "faktura", "billing", "invoice",
        "bokning", "booking", "admin", "office", "butik", "butiken", "shop", "store", "team",
        # vd@ och ceo@ står med flit INTE här: de når en enskild, utpekbar
        # person och får därför den fullständiga foten.
        "marknad", "marketing", "press", "contact", "enquiries", "inquiries",
        "noreply", "no-reply", "donotreply", "do-not-reply", "webmaster", "postmaster",
    }
)


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

    def _lokaldel(self) -> str:
        if not self.contact_email or "@" not in self.contact_email:
            return ""
        return self.contact_email.split("@", 1)[0].strip().lower()

    @property
    def epost_ar_personlig(self) -> bool:
        """`anna@`, `andersson@` och `anna.andersson@` snarare än `info@`.

        Avgör sidfoten (utskicksfot.bygg_fot) och om GDPR art. 14-texten och
        policylänken KRÄVS i mejlet (send_guard regel 2 och 4). Heuristiken
        är medvetet försiktig: varje lokaldel som inte är en känd
        funktionsadress (FUNKTIONSADRESSER, discovery.AVDELNINGSORD) räknas
        som personlig. Att felaktigt flagga en funktionsadress kostar en extra
        informationsruta i mejlet; att missa en personlig adress kostar ett
        regelbrott. Förut krävdes en punkt eller ett bindestreck, så att
        anna@ fick den korta foten (rättat 2026-11-17).
        """
        import unicodedata

        from ..discovery import AVDELNINGSORD  # lokalt: discovery är tung och importerar källorna

        lokaldel = "".join(
            t for t in unicodedata.normalize("NFKD", self._lokaldel()) if not unicodedata.combining(t)
        )
        return bool(lokaldel) and lokaldel not in FUNKTIONSADRESSER and lokaldel not in AVDELNINGSORD

    @property
    def epost_bar_namnform(self) -> bool:
        """`fornamn.efternamn@`: en punkt eller ett bindestreck i lokaldelen.

        Det gamla avgörandet (före 2026-11-17), kvar för det som inte är
        sidfot: poängsättningens kontaktväg (scoring) och rollkopplingsflaggan
        (rollkoppling). Sidfoten och spärrarna läser epost_ar_personlig."""
        lokaldel = self._lokaldel()
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
