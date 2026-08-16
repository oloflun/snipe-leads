"""Geografiska regioner som DATA, inte som kod i pipelinen.

Hela poängen med den här filen är att `REGIONER` ska gå att utöka utan att
någon rör `leads_agent.py`, `icp.py` eller en källa. En ny region är en post i
en dict — inte ett nytt `if`.

## Varför postnumret väger tyngre än ortnamnet

Ett targetingfilter som är för generöst kostar pengar och förtroende: varje
falsk träff är ett mejl till ett bolag som aldrig var målgruppen. Ortnamn är
fritext och stavas olika ("Gbg", "Göteborg", "Västra Frölunda" — den sista är
Göteborg men heter inte så). Postnumret är strukturerat.

Därför: **finns postnummer avgör det ensamt.** Ortnamnet används bara när
postnummer saknas. Motsatt ordning hade låtit en felstavad ort släppa in ett
bolag som postnumret redan dömt ut.

## Vad prefixen faktiskt är

Postnummerserierna nedan är de TRESIFFRIGA prefixen, alltså `903` ur
`903 27`. De följer PostNords orttilldelning och är grova: en serie kan spänna
över en kommungräns, och enstaka nummer inom en serie kan höra till
grannkommunen. Det är avsiktligt dokumenterat i stället för att låtsas om en
precision som inte finns — vill man ha kommunexakt filtrering krävs ett
postnummerregister, och det har vi inte licens till.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Kommun:
    """En kommun och de postnummerprefix som hör till den."""

    namn: str
    #: Treställiga prefix, inklusive båda ändarna: (900, 907) = 900–907.
    prefix: tuple[tuple[int, int], ...]

    def innehaller_prefix(self, prefix: int) -> bool:
        return any(lag <= prefix <= hog for lag, hog in self.prefix)


@dataclass(frozen=True)
class Region:
    nyckel: str
    etikett: str
    kommuner: tuple[Kommun, ...]

    @property
    def ortnamn(self) -> frozenset[str]:
        return frozenset(k.namn.casefold() for k in self.kommuner)

    def innehaller_prefix(self, prefix: int) -> bool:
        return any(k.innehaller_prefix(prefix) for k in self.kommuner)


#: De två regioner vi börjar med. Fler läggs till här, ingen annanstans.
REGIONER: dict[str, Region] = {
    "umea": Region(
        nyckel="umea",
        etikett="Umeåområdet",
        kommuner=(
            # Umeå tätort 903–907, Holmsund 913, Hörnefors 915, Sävar 918.
            # 900 är boxadresser.
            Kommun("Umeå", ((900, 907), (913, 913), (915, 915), (918, 918))),
            Kommun("Vännäs", ((911, 911),)),
            Kommun("Nordmaling", ((914, 914),)),
            # Robertsfors delar 915-serien med Hörnefors. Båda ligger i
            # regionen, så överlappet spelar ingen roll här — det hade det
            # gjort om bara den ena varit målgrupp.
            Kommun("Robertsfors", ((915, 915),)),
        ),
    ),
    "goteborg": Region(
        nyckel="goteborg",
        etikett="Göteborgsområdet",
        kommuner=(
            Kommun("Göteborg", ((400, 426),)),
            Kommun("Mölndal", ((431, 431),)),
            Kommun("Partille", ((433, 433),)),
            # Mölnlycke 435, Landvetter och Härryda 438.
            Kommun("Härryda", ((435, 435), (438, 438))),
            # Kungsbacka 434, Åsa/Fjärås 439.
            Kommun("Kungsbacka", ((434, 434), (439, 439))),
            # Kungälv/Ytterby/Kode 442, Marstrand 440.
            Kommun("Kungälv", ((440, 440), (442, 442))),
            Kommun("Lerum", ((443, 443),)),
        ),
    ),
}


class OkandRegionError(ValueError):
    """Höjs när ett ICP pekar på en region som inte finns.

    Ett tyst bortfall hade varit värre: en kund som stavat fel hade fått en
    körning helt utan geografiskt filter, alltså hela Sverige, utan att något
    sa ifrån. Det är precis det utfall DEL 1.1 förbjuder.
    """


def kanda_regioner() -> tuple[str, ...]:
    return tuple(REGIONER)


def hamta_region(nyckel: str) -> Region:
    try:
        return REGIONER[nyckel]
    except KeyError:
        raise OkandRegionError(
            f"Okänd region {nyckel!r}. Kända regioner: {', '.join(kanda_regioner())}."
        ) from None


def _prefix_ur_postnr(postnr: object) -> int | None:
    """'903 27' och '90327' ger båda 903. Skräp ger None."""
    if postnr is None:
        return None
    siffror = "".join(tecken for tecken in str(postnr) if tecken.isdigit())
    if len(siffror) < 3:
        return None
    try:
        return int(siffror[:3])
    except ValueError:  # pragma: no cover — isdigit har redan garanterat detta
        return None


def matchar_region(
    region_nycklar: list[str] | tuple[str, ...],
    *,
    postnr: object = None,
    ort: object = None,
) -> bool:
    """Ligger prospektet i någon av regionerna?

    Tom lista av regioner betyder INGEN geografisk begränsning och ger True.
    Det är rätt default här — begränsningen ska komma från att kunden aktivt
    valt en region, och `validate_icp` är stället som kräver ett aktivt val.
    """
    if not region_nycklar:
        return True

    regioner = [hamta_region(nyckel) for nyckel in region_nycklar]

    prefix = _prefix_ur_postnr(postnr)
    if prefix is not None:
        # Postnumret finns och avgör därmed ensamt. Se modulens docstring.
        return any(region.innehaller_prefix(prefix) for region in regioner)

    if ort is None or not str(ort).strip():
        # Varken postnummer eller ort. Vi vet inte var bolaget ligger, och
        # "vet inte" får aldrig betyda "släpp igenom" i ett urvalsfilter.
        return False

    ort_normaliserad = str(ort).strip().casefold()
    return any(ort_normaliserad in region.ortnamn for region in regioner)


def beskriv_region(nyckel: str) -> str:
    """Raden UI:t visar bredvid valet."""
    region = hamta_region(nyckel)
    return f"{region.etikett} ({', '.join(k.namn for k in region.kommuner)})"
