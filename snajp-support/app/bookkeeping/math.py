"""Pengar räknas av KOD, aldrig av modellen.

En språkmodell räknar fel på pengar. Inte alltid, vilket är det farliga: den
räknar rätt på tre rader och fel på trettio, och felet ser ut som ett belopp.
Därför gör modellen ETT val här — vilken beräkning som ska göras — och den här
modulen gör den. Samma princip som `leads_tools.py`, egen implementation.

## Varför `float` inte bara undviks utan AVVISAS

0.1 + 0.2 blir inte 0.3 i binär flyttal, och 25 % moms på 1 199,50 kr blir ett
belopp som slutar på ...9999999. Att "undvika float" är en konvention någon
bryter mot vid nästa tillägg, och felet syns först som en öresdifferens i en
periodrapport ingen kan förklara. `till_decimal` KASTAR på float i stället.
Det är skillnaden mellan en regel och en grind.

## Avrundning

`ROUND_HALF_UP` i Pythons decimal betyder "halva bort från noll" — inte
"halva uppåt". Det är svensk praxis och det som gör kreditfakturan rätt:
−0,50 kr avrundas till −1 kr, inte till 0 kr. Med ROUND_HALF_EVEN (Pythons
default) hade båda blivit 0, och en kreditfaktura hade tappat en krona mot
sin egen originalfaktura.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

#: Svenska momssatser. 0 % är med: den är inte "ingen moms" utan en sats, och
#: den skiljer sig från momsfri omsättning i redovisningen.
MOMSSATSER: tuple[Decimal, ...] = (
    Decimal("0.25"),
    Decimal("0.12"),
    Decimal("0.06"),
    Decimal("0"),
)

ORE = Decimal("0.01")
KRONA = Decimal("1")


class BeloppsfelError(ValueError):
    """Ett belopp eller en momssats som inte går att räkna med.

    Kastas hellre än att tolkas: ett belopp koden inte förstår ska stoppa
    beräkningen, inte tyst bli noll.
    """


def till_decimal(varde: object, *, falt: str = "belopp") -> Decimal:
    """Enda vägen in för ett belopp. Avvisar float.

    int och str accepteras — båda är exakta. float gör det inte, och
    felmeddelandet säger vad anroparen ska göra i stället, eftersom den som
    träffar det här har ett värde som kom någonstans ifrån.
    """
    if isinstance(varde, Decimal):
        return varde
    if isinstance(varde, bool):
        # bool är en int i Python. Ett True som belopp är alltid ett programfel.
        raise BeloppsfelError(f"{falt}: bool är inte ett belopp")
    if isinstance(varde, float):
        raise BeloppsfelError(
            f"{falt}: float är inte tillåtet för pengar ({varde!r}). "
            "Skicka Decimal eller sträng."
        )
    if isinstance(varde, int):
        return Decimal(varde)
    if isinstance(varde, str):
        rensad = varde.replace(",", ".").replace(" ", "").replace("\xa0", "")
        try:
            return Decimal(rensad)
        except Exception as orsak:  # noqa: BLE001 — vi vill ha vår egen feltyp
            raise BeloppsfelError(f"{falt}: {varde!r} är inte ett belopp") from orsak
    raise BeloppsfelError(f"{falt}: {type(varde).__name__} är inte ett belopp")


def till_momssats(varde: object) -> Decimal:
    """Momssatsen som andel (0.25), inte som procent (25).

    Avvisar allt utom de fyra svenska satserna. En påhittad sats — 0.20, för
    att modellen råkade tänka på ett annat land — ska inte gå att räkna med.
    """
    sats = till_decimal(varde, falt="momssats")
    if sats not in MOMSSATSER:
        tillatna = ", ".join(str(s) for s in MOMSSATSER)
        raise BeloppsfelError(f"momssats: {sats} finns inte i Sverige (tillåtna: {tillatna})")
    return sats


def avrunda_ore(varde: object) -> Decimal:
    """Till närmaste öre. Används på delberäkningar."""
    return till_decimal(varde).quantize(ORE, rounding=ROUND_HALF_UP)


def avrunda_krona(varde: object) -> Decimal:
    """Till närmaste hela krona — svensk öresavrundning.

    Halva bort från noll: 0,50 blir 1 och −0,50 blir −1. Se modulens docstring.
    """
    return till_decimal(varde).quantize(KRONA, rounding=ROUND_HALF_UP)


def moms_fran_netto(netto: object, sats: object) -> Decimal:
    """Moms ovanpå ett nettobelopp. Avrundas till öre."""
    return avrunda_ore(till_decimal(netto, falt="netto") * till_momssats(sats))


def moms_fran_brutto(brutto: object, sats: object) -> Decimal:
    """Momsen som ligger INUTI ett bruttobelopp: brutto x sats / (1 + sats).

    Det är den här riktningen ett kvitto kräver — kvittot visar det kunden
    betalade, inte nettot.
    """
    b = till_decimal(brutto, falt="brutto")
    s = till_momssats(sats)
    return avrunda_ore(b * s / (Decimal(1) + s))


def netto_fran_brutto(brutto: object, sats: object) -> Decimal:
    """Brutto minus momsen i det.

    Räknas som en subtraktion, inte som en egen division — annars kan
    netto + moms avvika från brutto med ett öre, och den öresdifferensen dyker
    sedan upp i verifikatet som en obalans ingen kan spåra.
    """
    b = till_decimal(brutto, falt="brutto")
    return b - moms_fran_brutto(b, sats)


@dataclass(frozen=True)
class Post:
    """Ett underlag, klart att summera.

    `netto` och `moms` är POSITIVA för en normal post. Riktningen ligger i
    `riktning`, inte i tecknet — annars måste varje summering veta vilken
    konvention som gällde när posten skapades.

    En kreditfaktura är undantaget som bekräftar det: den bär negativa belopp
    med samma riktning som fakturan den krediterar.
    """

    datum: date
    riktning: str  # "intakt" | "kostnad"
    netto: Decimal
    moms: Decimal
    motpart: str = ""
    underlag_id: str = ""

    def __post_init__(self) -> None:
        if self.riktning not in ("intakt", "kostnad"):
            raise BeloppsfelError(f"riktning: {self.riktning!r} är varken intakt eller kostnad")
        object.__setattr__(self, "netto", till_decimal(self.netto, falt="netto"))
        object.__setattr__(self, "moms", till_decimal(self.moms, falt="moms"))


@dataclass(frozen=True)
class Periodsummor:
    intakter: Decimal
    kostnader: Decimal
    utgaende_moms: Decimal
    ingaende_moms: Decimal
    resultat_fore_skatt: Decimal
    moms_att_betala: Decimal
    antal_poster: int


def summera_period(poster: Sequence[Post]) -> Periodsummor:
    """Periodens fem tal, plus momsen att betala.

    Utgående moms är momsen på det vi SÅLT, ingående på det vi KÖPT — namnen
    är motsatta det intuitiva och det är därför de står utskrivna här.
    Skillnaden är det som betalas in till Skatteverket.

    Summeringen avrundas EN gång, på slutet. Att avrunda varje post och sedan
    summera ger en annan siffra, och skillnaden växer med antalet rader.
    """
    intakter = Decimal(0)
    kostnader = Decimal(0)
    utgaende = Decimal(0)
    ingaende = Decimal(0)

    for post in poster:
        if post.riktning == "intakt":
            intakter += post.netto
            utgaende += post.moms
        else:
            kostnader += post.netto
            ingaende += post.moms

    intakter = avrunda_ore(intakter)
    kostnader = avrunda_ore(kostnader)
    utgaende = avrunda_ore(utgaende)
    ingaende = avrunda_ore(ingaende)

    return Periodsummor(
        intakter=intakter,
        kostnader=kostnader,
        utgaende_moms=utgaende,
        ingaende_moms=ingaende,
        resultat_fore_skatt=intakter - kostnader,
        moms_att_betala=utgaende - ingaende,
        antal_poster=len(poster),
    )


@dataclass(frozen=True)
class Konteringsrad:
    """En rad i ett verifikat.

    Exakt en av debet/kredit är nollskild i det normala fallet, men båda
    tillåts vara satta — en kreditfaktura konteras med negativa belopp på
    samma sida som originalet, inte med sidbyte.
    """

    konto: str
    debet: Decimal = Decimal(0)
    kredit: Decimal = Decimal(0)
    text: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "debet", till_decimal(self.debet, falt="debet"))
        object.__setattr__(self, "kredit", till_decimal(self.kredit, falt="kredit"))


def balans(rader: Sequence[Konteringsrad]) -> Decimal:
    """Debet minus kredit. Noll betyder att verifikatet går ihop.

    Returnerar differensen och inte ett ja/nej: den som fått en obalans
    behöver veta hur stor den är för att se om det är ett öre (avrundning)
    eller ett fel (fel konto).
    """
    debet = sum((rad.debet for rad in rader), Decimal(0))
    kredit = sum((rad.kredit for rad in rader), Decimal(0))
    return avrunda_ore(debet - kredit)
