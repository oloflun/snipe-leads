"""Verktygen bokföringschatten får, och ingenting mer.

## Formen: vitlistade dataset, inte fri fråga

Modellen VÄLJER vilket verktyg och vilken period. Den formulerar svaret i ord.
Den skriver aldrig en fråga, aldrig ett filter vi inte känner igen, och aldrig
ett tal den räknat själv.

Formen är läst ur lambda-erp:s `api/chat.py`, som löser samma problem för en
ERP-chatt: modellen får `query_dataset` över ett par fördefinierade dataset med
en sluten uppsättning tillåtna operatorer, aldrig SQL, och all aggregering sker
serversidan. Deras formulering är "semantic datasets, not free SQL". Det är
samma avvägning vi redan gjort i `leads_tools.py` med andra ord: modellen väljer
VAD, koden gör.

Fyra dataset räcker för de frågor chatten faktiskt får:

    hamta_periodrapport   "hur mycket moms har jag i augusti?"
    lista_underlag        "vilka kvitton saknar belopp?"
    sla_upp_konto         "vilket konto hamnar drivmedel på?"
    sla_upp_kunskap       "vad gäller för representation?"

## Tenanten kommer ALDRIG från ett argument

INV-SEC-002, samma som `leads_tools.py` och `tools.py`. Den läses ur kontexten,
satt av servern ur `require_tenant`. Ett tenant-argument hade varit ett fält
modellen kan fylla i, och därmed en fråga en kund kan ställa om en annan kunds
bokföring.

## Varför varje resultat SPARAS i kontexten

INV-BOOK-003 jämför svarets belopp mot turens verktygsresultat
(`bookkeeping/beloppsgrind.py`). Grinden kan bara göra det om resultaten finns
kvar när svaret är skrivet — därför lägger varje verktyg sitt svar i
`context.resultat` innan det returneras. Missas det i ett nytt verktyg blir
grinden strängare än den ska vara: sanna siffror från just det verktyget fälls.

## Varför funktionen heter `sla_upp_konto` och inte `slå_upp_konto`

Verktygsnamnet går vidare till modell-API:t, som kräver `^[a-zA-Z0-9_-]{1,64}$`.
Ett å i namnet hade avvisats vid anropet, inte vid importen — alltså i drift och
inte i CI. Beskrivningen är på svenska, som för de andra verktygen.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from agents import RunContextWrapper, function_tool

from ..bookkeeping.kontoplan import KONTOPLAN, KOSTNADSKATEGORIER, foresla_konto
from ..bookkeeping.kunskap import KUNSKAP, sok_amne
from ..bookkeeping.period import berakna_period
from ..bookkeeping.verifieringsgrind import STATUS_GRANSKA, STATUS_KLAR
from ..storage.base import Storage

#: Vitlistade statusfilter för `lista_underlag`. Allt annat avvisas med ett
#: svar modellen kan agera på, inte med ett kast.
TILLATNA_STATUS = (STATUS_KLAR, STATUS_GRANSKA)

#: Tak per svar. Ett verktyg som lämnar tvåhundra rader till modellen kostar
#: tokens utan att svara bättre — och gör dessutom INV-BOOK-003 mer generös än
#: den behöver vara, eftersom varje tal i resultatet blir ett grundat tal.
MAX_RADER = 50


@dataclass
class BokforingChattContext:
    """Körningskontext för ett chattsvar.

    `resultat` är turens verktygssvar i den ordning de gjordes. Den listan är
    hela indata till INV-BOOK-003 — se modulens docstring.
    """

    storage: Storage
    tenant_id: str
    resultat: list[str] = field(default_factory=list)

    def spara(self, nyttolast: dict[str, Any]) -> str:
        text = json.dumps(nyttolast, ensure_ascii=False, default=str)
        self.resultat.append(text)
        return text


def _datum(rat: str) -> date | None:
    try:
        return date.fromisoformat(rat.strip())
    except (ValueError, AttributeError):
        return None


# -- Dataset 1: periodrapporten -------------------------------------------


async def _hamta_periodrapport_impl(ctx: BokforingChattContext, fran: str, till: str) -> str:
    f, t = _datum(fran), _datum(till)
    if f is None or t is None:
        return ctx.spara({"fel": "Datum ska skrivas som ÅÅÅÅ-MM-DD."})
    if t < f:
        return ctx.spara({"fel": "Slutdatumet ligger före startdatumet."})

    rapport = await berakna_period(ctx.storage, ctx.tenant_id, f, t)
    # Verifikatlistan är rå indata till SIE-exporten och hör inte hemma i ett
    # chattsvar: den är lång, den bär inga nya belopp, och varje tal i den blir
    # ett grundat tal i INV-BOOK-003.
    rapport.pop("_verifikat", None)
    return ctx.spara(rapport)


@function_tool
async def hamta_periodrapport(
    ctx: RunContextWrapper[BokforingChattContext], fran: str, till: str
) -> str:
    """Summorna för en period: intäkter, kostnader, moms och resultat.

    Samma uträkning som periodvyn i produkten använder. Går perioden inte ihop
    svarar den med brister i stället för summor, och då ska du säga det.

    Args:
        fran: Första dagen i perioden, ÅÅÅÅ-MM-DD.
        till: Sista dagen i perioden, ÅÅÅÅ-MM-DD.
    """
    return await _hamta_periodrapport_impl(ctx.context, fran, till)


# -- Dataset 2: underlagen -------------------------------------------------


async def _lista_underlag_impl(
    ctx: BokforingChattContext, fran: str, till: str, status: str | None = None
) -> str:
    f, t = _datum(fran), _datum(till)
    if f is None or t is None:
        return ctx.spara({"fel": "Datum ska skrivas som ÅÅÅÅ-MM-DD."})
    if status is not None and status not in TILLATNA_STATUS:
        return ctx.spara(
            {"fel": f"Okänd status {status!r}. Tillåtna: {', '.join(TILLATNA_STATUS)}."}
        )

    rader = await ctx.storage.list_bk_underlag(ctx.tenant_id, fran=f, till=t)
    if status is not None:
        rader = [r for r in rader if r.get("status") == status]

    # Bara fälten en fråga om underlag kan handla om. Att skicka hela raden hade
    # lämnat ut sha256 och filnamn till modellen utan att svara bättre.
    smalt = [
        {
            "id": r.get("id"),
            "datum": r.get("datum"),
            "motpart": r.get("motpart"),
            "brutto": None if r.get("brutto") is None else f"{r['brutto']:f}",
            "momssats": None if r.get("momssats") is None else f"{r['momssats']:f}",
            "riktning": r.get("riktning"),
            "kategori": r.get("kategori"),
            "status": r.get("status"),
            "anmarkning": r.get("anmarkning"),
        }
        for r in rader[:MAX_RADER]
    ]
    return ctx.spara(
        {"antal": len(rader), "visade": len(smalt), "underlag": smalt}
    )


@function_tool
async def lista_underlag(
    ctx: RunContextWrapper[BokforingChattContext],
    fran: str,
    till: str,
    status: str | None = None,
) -> str:
    """Underlagen i en period, med status och eventuell anmärkning.

    Args:
        fran: Första dagen, ÅÅÅÅ-MM-DD.
        till: Sista dagen, ÅÅÅÅ-MM-DD.
        status: Valfritt filter. Antingen "klar" eller "granska_manuellt".
    """
    return await _lista_underlag_impl(ctx.context, fran, till, status)


# -- Dataset 3: kontoplanen ------------------------------------------------


async def _sla_upp_konto_impl(ctx: BokforingChattContext, nummer_eller_kategori: str) -> str:
    fraga = (nummer_eller_kategori or "").strip().lower()
    if not fraga:
        return ctx.spara({"fel": "Ange ett kontonummer eller en kategori."})

    konto = KONTOPLAN.get(fraga)
    if konto is not None:
        return ctx.spara({"nummer": konto.nummer, "namn": konto.namn, "typ": konto.typ})

    nummer = foresla_konto(fraga)
    if nummer is not None:
        träff = KONTOPLAN[nummer]
        return ctx.spara(
            {
                "kategori": fraga,
                "nummer": träff.nummer,
                "namn": träff.namn,
                "typ": träff.typ,
            }
        )

    # None och inte en gissning — samma regel som `foresla_konto` följer.
    # Kontoplanen är en delmängd av BAS med flit, och ett närliggande konto är
    # fel konto.
    return ctx.spara(
        {
            "hittades": False,
            "fraga": fraga,
            "kanda_kategorier": sorted(KOSTNADSKATEGORIER),
        }
    )


@function_tool
async def sla_upp_konto(
    ctx: RunContextWrapper[BokforingChattContext], nummer_eller_kategori: str
) -> str:
    """Slå upp ett konto i BAS-kontoplanen, på nummer eller kategori.

    Hittas inget svarar verktyget med de kända kategorierna. Gissa aldrig ett
    konto som inte kom härifrån.

    Args:
        nummer_eller_kategori: Till exempel "5611" eller "drivmedel".
    """
    return await _sla_upp_konto_impl(ctx.context, nummer_eller_kategori)


# -- Dataset 4: kunskapsbasen ----------------------------------------------


async def _sla_upp_kunskap_impl(ctx: BokforingChattContext, amne: str) -> str:
    """Texten ur `bookkeeping/kunskap.py`, aldrig modellens minne.

    Läser ingen kunddata alls — kontexten tas emot bara för att svaret ska
    sparas i `ctx.resultat`, så att talen i texten (300 kr-taket och liknande)
    räknas som hämtade under INV-BOOK-003.
    """
    träff = sok_amne(amne)
    if träff is None:
        return ctx.spara(
            {
                "hittades": False,
                "fraga": (amne or "").strip(),
                "kanda_amnen": sorted(KUNSKAP),
            }
        )
    return ctx.spara({"amne": träff.id, "rubrik": träff.rubrik, "text": träff.text})


@function_tool
async def sla_upp_kunskap(ctx: RunContextWrapper[BokforingChattContext], amne: str) -> str:
    """Slå upp en förklaring i Snajps bokföringskunskap: moms, periodisering,
    representation, avdrag, fakturakrav, bokföringslagen, EU-handel, K-regelverk
    med mera.

    Svara ur texten du får tillbaka, inte ur minnet. Hittas inget ämne svarar
    verktyget med de kända ämnena — säg då att ämnet inte finns i kunskapen.

    Args:
        amne: Ämnet eller frågan, till exempel "representation" eller
            "vad gäller vid import".
    """
    return await _sla_upp_kunskap_impl(ctx.context, amne)


#: Verktygsuppsättningen. Ingen av dem skriver, ingen av dem räknar, och ingen
#: av dem tar emot en tenant.
BOKFORING_CHATT_TOOLS = [hamta_periodrapport, lista_underlag, sla_upp_konto, sla_upp_kunskap]
