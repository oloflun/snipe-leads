"""Relevansscoring som MOTIVERAR sig.

En användare som ser "84/100" utan att veta varför litar inte på listan, och
gör den inte det är listan värdelös oavsett hur bra siffran är. Därför bär
varje prospekt ett `score_breakdown`: ett kriterium per rad, med utfall och
en mening om varför.

## Hårda filter kontra poäng

Två sorters kriterier, och skillnaden är inte kosmetisk:

* **Hårda** — geografi, branschkod, storleksspann, uteslutningar. Kunden har
  sagt "småföretag inom X i Umeå". Ett bolag i Malmö är inte ett sämre
  prospekt, det är fel prospekt — och ett bolag med 240 anställda är inte ett
  småföretag. De diskvalificerar, och ett diskvalificerat bolag får poäng 0
  oavsett hur bra det matchar i övrigt.
* **Mjuka** — kontaktbarhet. Gör ett prospekt mer eller mindre lovande inom
  det urval som redan är rätt.

## Okänd uppgift behandlas OLIKA för olika kriterier, och det är avsiktligt

För geografi och branschkod diskvalificerar en okänd uppgift. De finns i varje
register och i vår egen CSV — saknas de är posten trasig, och "vet inte" får
aldrig betyda "släpp igenom" i ett urvalsfilter.

För antal anställda och omsättning gör den det INTE. De uppgifterna saknas
rutinmässigt även i bra källor (Bolagsverkets register har dem inte alls). Att
diskvalificera på dem hade tömt listan på allt utom de bolag som råkade ha
fyllt i en extra kolumn, vilket säger något om vår datainsamling och ingenting
om prospektet.

Ett KÄNT värde utanför spannet diskvalificerar däremot. Skillnaden går mellan
"vi vet inte" och "vi vet, och det stämmer inte".

## Nämnaren räknas på det som FAKTISKT är satt

Ett ICP med bara geografi ska kunna ge 100, inte 30. Kriterier kunden inte
konfigurerat räknas varken i täljaren eller nämnaren — annars hade en
minimal men helt uppfylld ICP sett ut som en dålig träff, och kunden hade
lagt till kriterier för att jaga en siffra i stället för för att träffa rätt.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from .geo import beskriv_region, matchar_region
from .icp import normalize_icp
from .sni import beskriv_kod, matchar_sni, normalisera_kod

if TYPE_CHECKING:
    # Bara för typerna. En riktig import hade blivit cirkulär: csv_source
    # importerar scoring, och sources/__init__ importerar csv_source.
    # Riktningen är avsiktlig — scoringen känner till prospektets FORM, men
    # ska inte vara beroende av var prospekt kommer ifrån.
    from .sources.base import Prospect

#: Vikterna. Geografi och bransch väger tyngst eftersom de ÄR nischen;
#: storlek och kontaktbarhet skiljer bra från bättre inom den.
VIKT_GEO = 30
VIKT_SNI = 30
VIKT_ANSTALLDA = 20
VIKT_OMSATTNING = 10
VIKT_KONTAKT = 10

TRAFF = "träff"
MISS = "miss"
EJ_SATT = "ej_satt"
OKAND = "okänd"


@dataclass(frozen=True)
class Kriterium:
    nyckel: str
    etikett: str
    vikt: int
    utfall: str
    motivering: str
    #: Hårda kriterier diskvalificerar vid miss. Mjuka drar bara ner poängen.
    hart: bool = False

    @property
    def raknas(self) -> bool:
        """Kriterier kunden inte satt, och sådana vi saknar data för, hålls
        utanför nämnaren. Se modulens docstring."""
        return self.utfall in (TRAFF, MISS)


@dataclass(frozen=True)
class Score:
    total: int
    diskvalificerad: bool
    diskvalificerande_skal: tuple[str, ...]
    breakdown: tuple[Kriterium, ...]

    def as_dict(self) -> dict[str, Any]:
        """Formen som går till databasen och UI:t."""
        return {
            "total": self.total,
            "diskvalificerad": self.diskvalificerad,
            "diskvalificerande_skal": list(self.diskvalificerande_skal),
            "score_breakdown": [asdict(k) for k in self.breakdown],
        }


def score_prospect(prospect: "Prospect", icp: dict[str, Any]) -> Score:
    normaliserad = normalize_icp(icp)
    kriterier: list[Kriterium] = []
    skal: list[str] = []

    kriterier.append(_kriterium_uteslutna_domaner(prospect, normaliserad, skal))
    kriterier.append(_kriterium_utesluten_bransch(prospect, normaliserad, skal))
    kriterier.append(_kriterium_geo(prospect, normaliserad, skal))
    kriterier.append(_kriterium_sni(prospect, normaliserad, skal))
    kriterier.append(_kriterium_anstallda(prospect, normaliserad, skal))
    kriterier.append(_kriterium_omsattning(prospect, normaliserad, skal))
    kriterier.append(_kriterium_kontakt(prospect))

    diskvalificerad = bool(skal)

    namnare = sum(k.vikt for k in kriterier if k.raknas)
    taljare = sum(k.vikt for k in kriterier if k.utfall == TRAFF)

    # Frågan "har kunden satt några urvalskriterier alls" avgörs på ICP:t, inte
    # på nämnaren. Kontaktbarhet är en egenskap hos prospektet och räknas alltid
    # — hade den fått räknas som ett kriterium här, hade ett ICP helt utan
    # målgruppsstyrning sett konfigurerat ut.
    icp_kriterier_satta = any(
        (
            normaliserad.get("geo"),
            normaliserad.get("sni_codes"),
            normaliserad.get("exclude_sni"),
            normaliserad.get("exclude_domains"),
            any(v is not None for v in (normaliserad.get("size") or {}).values()),
        )
    )

    if diskvalificerad:
        # Poäng 0, men breakdown behålls i sin helhet. Kunden ska kunna se att
        # bolaget var en bra träff på allt UTOM det som fällde det — det är
        # den informationen som avslöjar ett ICP med ett för brett undantag.
        total = 0
    elif not icp_kriterier_satta:
        total = 0
        kriterier.append(
            Kriterium(
                nyckel="inga_kriterier",
                etikett="Inga urvalskriterier satta",
                vikt=0,
                utfall=OKAND,
                motivering=(
                    "ICP:t saknar geografi, bransch och storlek. Utan kriterier "
                    "går relevansen inte att bedöma — poängen är 0 för att den "
                    "är omätbar, inte för att bolaget är dåligt."
                ),
            )
        )
    else:
        total = round(100 * taljare / namnare) if namnare else 0

    return Score(
        total=total,
        diskvalificerad=diskvalificerad,
        diskvalificerande_skal=tuple(skal),
        breakdown=tuple(kriterier),
    )


def _kriterium_uteslutna_domaner(
    prospect: "Prospect", icp: dict[str, Any], skal: list[str]
) -> Kriterium:
    uteslutna = icp.get("exclude_domains") or []
    if not uteslutna:
        return Kriterium(
            "exclude_domains", "Uteslutna domäner", 0, EJ_SATT, "Inga domäner undantagna.", hart=True
        )

    domaner = {d for d in (_domän(prospect.website), _domän(prospect.contact_email)) if d}
    traffad = next((u for u in uteslutna if any(d == u or d.endswith("." + u) for d in domaner)), None)
    if traffad:
        skal.append(f"Domänen {traffad} står på kundens uteslutningslista.")
        return Kriterium(
            "exclude_domains",
            "Uteslutna domäner",
            0,
            MISS,
            f"{traffad} är undantagen — sannolikt en befintlig kund eller konkurrent.",
            hart=True,
        )
    return Kriterium(
        "exclude_domains",
        "Uteslutna domäner",
        0,
        TRAFF,
        f"Ingen träff mot de {len(uteslutna)} undantagna domänerna.",
        hart=True,
    )


def _kriterium_utesluten_bransch(
    prospect: "Prospect", icp: dict[str, Any], skal: list[str]
) -> Kriterium:
    uteslutna = icp.get("exclude_sni") or []
    if not uteslutna:
        return Kriterium(
            "exclude_sni", "Undantagna branscher", 0, EJ_SATT, "Inga branscher undantagna.", hart=True
        )

    kod = normalisera_kod(prospect.sni)
    if kod and any(kod == normalisera_kod(u) for u in uteslutna):
        skal.append(f"Branschkoden {beskriv_kod(kod)} är undantagen i ICP:t.")
        return Kriterium(
            "exclude_sni",
            "Undantagna branscher",
            0,
            MISS,
            f"{beskriv_kod(kod)} står på undantagslistan.",
            hart=True,
        )
    return Kriterium(
        "exclude_sni",
        "Undantagna branscher",
        0,
        TRAFF,
        f"Branschen är inte någon av de {len(uteslutna)} undantagna.",
        hart=True,
    )


def _kriterium_geo(
    prospect: "Prospect", icp: dict[str, Any], skal: list[str]
) -> Kriterium:
    regioner = icp.get("geo") or []
    if not regioner:
        return Kriterium(
            "geo", "Geografi", VIKT_GEO, EJ_SATT, "Ingen geografisk avgränsning vald.", hart=True
        )

    etiketter = "; ".join(beskriv_region(r) for r in regioner)
    plats = prospect.postnr or prospect.ort or "okänd plats"

    if matchar_region(regioner, postnr=prospect.postnr, ort=prospect.ort):
        return Kriterium(
            "geo", "Geografi", VIKT_GEO, TRAFF, f"{plats} ligger i {etiketter}.", hart=True
        )

    if not prospect.postnr and not prospect.ort:
        skal.append("Bolaget saknar både postnummer och ort — går inte att placera geografiskt.")
        return Kriterium(
            "geo",
            "Geografi",
            VIKT_GEO,
            OKAND,
            "Varken postnummer eller ort finns. Ett okänt läge uppfyller inte ett geokrav.",
            hart=True,
        )

    skal.append(f"{plats} ligger utanför {etiketter}.")
    return Kriterium("geo", "Geografi", VIKT_GEO, MISS, f"{plats} ligger utanför området.", hart=True)


def _kriterium_sni(
    prospect: "Prospect", icp: dict[str, Any], skal: list[str]
) -> Kriterium:
    koder = icp.get("sni_codes") or []
    if not koder:
        return Kriterium(
            "sni", "Branschkod", VIKT_SNI, EJ_SATT, "Ingen branschkod vald.", hart=True
        )

    onskade = "; ".join(beskriv_kod(k) for k in koder)
    kod = normalisera_kod(prospect.sni)

    if not kod:
        skal.append("Bolaget saknar SNI-kod och kan därför inte matchas mot branschkravet.")
        return Kriterium(
            "sni",
            "Branschkod",
            VIKT_SNI,
            OKAND,
            "SNI-kod saknas i källan. Ett okänt bolag uppfyller inte ett krav.",
            hart=True,
        )

    if matchar_sni(kod, inkludera=koder):
        return Kriterium(
            "sni", "Branschkod", VIKT_SNI, TRAFF, f"{beskriv_kod(kod)} är en av de sökta.", hart=True
        )

    skal.append(f"{beskriv_kod(kod)} finns inte bland de sökta branscherna ({onskade}).")
    return Kriterium(
        "sni", "Branschkod", VIKT_SNI, MISS, f"{beskriv_kod(kod)} är inte en av de sökta.", hart=True
    )


def _kriterium_anstallda(
    prospect: "Prospect", icp: dict[str, Any], skal: list[str]
) -> Kriterium:
    size = icp.get("size") or {}
    return _intervallkriterium(
        nyckel="anstallda",
        etikett="Antal anställda",
        vikt=VIKT_ANSTALLDA,
        varde=prospect.anstallda,
        lag=size.get("anstallda_min"),
        hog=size.get("anstallda_max"),
        enhet="anställda",
        skal=skal,
    )


def _kriterium_omsattning(
    prospect: "Prospect", icp: dict[str, Any], skal: list[str]
) -> Kriterium:
    size = icp.get("size") or {}
    return _intervallkriterium(
        nyckel="omsattning",
        etikett="Omsättning",
        vikt=VIKT_OMSATTNING,
        varde=prospect.omsattning,
        lag=size.get("omsattning_min"),
        hog=size.get("omsattning_max"),
        enhet="kr",
        skal=skal,
    )


def _intervallkriterium(
    *,
    nyckel: str,
    etikett: str,
    vikt: int,
    varde: int | None,
    lag: int | None,
    hog: int | None,
    enhet: str,
    skal: list[str],
) -> Kriterium:
    if lag is None and hog is None:
        return Kriterium(nyckel, etikett, vikt, EJ_SATT, f"Inget spann för {etikett.lower()} satt.")

    spann = f"{lag if lag is not None else '—'}–{hog if hog is not None else '—'} {enhet}"

    if varde is None:
        # OKÄND uppgift diskvalificerar INTE. Antal anställda och omsättning
        # saknas rutinmässigt även i bra källor — Bolagsverkets register har
        # dem inte alls. Att fälla på dem hade tömt listan på allt utom de
        # bolag som råkat ha en extra ifylld kolumn, vilket säger något om vår
        # datainsamling och ingenting om prospektet.
        return Kriterium(
            nyckel, etikett, vikt, OKAND, f"Uppgift saknas i källan. Sökt spann: {spann}.", hart=True
        )

    # KÄNT värde utanför spannet diskvalificerar. Kunden har bett om småföretag;
    # ett bolag med 240 anställda är inte ett sämre småföretag, det är inget.
    if lag is not None and varde < lag:
        skal.append(f"{etikett}: {varde} {enhet} är under det sökta spannet {spann}.")
        return Kriterium(
            nyckel, etikett, vikt, MISS, f"{varde} {enhet} är under spannet {spann}.", hart=True
        )
    if hog is not None and varde > hog:
        skal.append(f"{etikett}: {varde} {enhet} är över det sökta spannet {spann}.")
        return Kriterium(
            nyckel, etikett, vikt, MISS, f"{varde} {enhet} är över spannet {spann}.", hart=True
        )

    return Kriterium(
        nyckel, etikett, vikt, TRAFF, f"{varde} {enhet} ligger inom {spann}.", hart=True
    )


def _kriterium_kontakt(prospect: "Prospect") -> Kriterium:
    if not prospect.contact_email:
        return Kriterium(
            "kontakt",
            "Kontaktväg",
            VIKT_KONTAKT,
            MISS,
            "Ingen publik kontaktadress hittad — prospektet går inte att nå.",
        )

    if prospect.epost_ar_personlig:
        # Halv träff finns inte i modellen, och ska inte finnas: en personlig
        # adress ÄR nåbar. Att den kräver GDPR art. 14-text är send_guards
        # sak (regel 4), inte scoringens.
        return Kriterium(
            "kontakt",
            "Kontaktväg",
            VIKT_KONTAKT,
            TRAFF,
            f"{prospect.contact_email} är personlig — kräver art. 14-information i mejlet.",
        )

    return Kriterium(
        "kontakt",
        "Kontaktväg",
        VIKT_KONTAKT,
        TRAFF,
        f"{prospect.contact_email} är en funktionsadress.",
    )


def _domän(varde: str | None) -> str:
    if not varde:
        return ""
    text = varde.strip().lower()
    for prefix in ("https://", "http://"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
    text = text.split("@")[-1].split("/", 1)[0].split("?", 1)[0]
    return text[4:] if text.startswith("www.") else text
