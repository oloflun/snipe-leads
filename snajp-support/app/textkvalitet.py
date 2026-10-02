"""Centralt textkvalitetslager — all kundsynlig agenttext passerar här.

## Varför det finns

Kunder har sett stavfel i Iris mejlutkast (rotorsaksanalys 2026-10-03):
modellen själv producerar felen, ingen prompt kräver korrekt svenska och
ingen kod kontrollerar texten efteråt. Det här lagret är svaret, i tre delar:

1. `SPRAKREGLER` — ett promptblock med språkkrav som agent-prompterna
   återanvänder, så att regeln bara finns på ETT ställe.
2. `kontrollera()` — deterministisk efterkontroll: rättar det som går att
   rätta utan risk (dubbla mellanslag, mellanslag före skiljetecken,
   hängande hälsningar efter platshållarstädning, en kurerad lista av
   entydiga felstavningar) och FLAGGAR det som inte går att rätta blint
   (ersättningstecken, kvarlämnade platshållare, engelska inslag,
   avhuggna meningar).
3. `korrekturlas_llm()` — ett kort LLM-pass som bara körs när den
   deterministiska kontrollen flaggat något allvarligt, och vars resultat
   verifieras innan det accepteras (länkar, e-postadresser, siffror och
   skyddade namn måste överleva oförändrade).

## Kontraktet mot anroparna

En text vars kontroll lämnar allvarliga anmärkningar får ALDRIG skickas
automatiskt — anroparen ska tvinga mänsklig granskning (`awaiting_review`
i leads-kön, `draft` i stället för autosvar i mejlpipelinen). Lagret
ändrar aldrig fakta, namn, siffror, länkar eller budskap: rättningarna är
antingen mekaniska (blanksteg) eller entydiga (felstavningslistan), och
LLM-passet förkastas om verifieringen fäller det.

Modulen är beroendefri (ingen import från app/agent/) så att den kan
användas från både leads-, support- och bokföringsvägarna utan cirklar.
LLM-klienten importeras lokalt inne i `korrekturlas_llm`.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger("snajp-support.textkvalitet")

#: Promptblock som agent-prompterna lägger till. Hålls kort — regeln ska
#: kosta få tokens och vara omöjlig att misstolka.
SPRAKREGLER = (
    "SPRÅKKRAV (absoluta): Korrekt, naturlig och professionell svenska — "
    "rätt stavning, grammatik, skiljetecken och meningsbyggnad. Inga "
    "påhittade ord, inga särskrivningar, inga anglicismer där ett svenskt "
    "ord finns. Blanda aldrig in engelska i en svensk text. Konsekvent "
    "tilltal rakt igenom texten (byt aldrig mellan du och ni). Läs igenom "
    "texten en sista gång innan du svarar och rätta varje språkfel."
)

#: Namn som aldrig får "rättas" — produktnamn och varumärken.
SKYDDADE_NAMN = ("Snajp", "Iris", "Snipra", "Livrustning", "TypeSafe", "JobTech")

#: Entydiga felstavningar → rättning. BARA ord där rättningen är säker
#: oavsett sammanhang. Kontextberoende fel (de/dem, var/vart) hör INTE
#: hemma här — de flaggas inte alls hellre än att rättas fel.
#: Versalvarianten hanteras av _ratta_felstavningar.
FELSTAVNINGAR: dict[str, str] = {
    "abbonemang": "abonnemang",
    "abonemang": "abonnemang",
    "aggresiv": "aggressiv",
    "aggresivt": "aggressivt",
    "annulera": "annullera",
    "defenitivt": "definitivt",
    "definitift": "definitivt",
    "egentligtvis": "egentligen",
    "epost": "e-post",
    "epostadress": "e-postadress",
    "följdaktligen": "följaktligen",
    "förmodeligen": "förmodligen",
    "iallafall": "i alla fall",
    "intresant": "intressant",
    "intresanta": "intressanta",
    "intressangt": "intressant",
    "medans": "medan",
    "nogrann": "noggrann",
    "nogrant": "noggrant",
    "orginal": "original",
    "orginell": "originell",
    "paralell": "parallell",
    "paralellt": "parallellt",
    "proffesionell": "professionell",
    "proffesionellt": "professionellt",
    "professionel": "professionell",
    "rekomendera": "rekommendera",
    "rekomenderar": "rekommenderar",
    "rekomendation": "rekommendation",
    "resturang": "restaurang",
    "sammarbete": "samarbete",
    "sammarbeta": "samarbeta",
    "sucessivt": "successivt",
    "tillsammas": "tillsammans",
    "ursprunligen": "ursprungligen",
    "överaskande": "överraskande",
    "överaskning": "överraskning",
}

# Engelska funktionsord som inte är svenska ord. Tre eller fler distinkta
# träffar i en text som ska vara svensk => flagga (inte rätta — en engelsk
# produktterm eller ett citat kan vara avsiktligt, men tre funktionsord i
# löpande text är det inte).
_ENGELSKA_ORD = re.compile(
    r"\b(the|and|your|our|with|would|should|could|please|regarding|"
    r"regards|sincerely|thanks|however|because|about|their|which)\b"
)

# Platshållare som överlevt strip_placeholders — t.ex. "[företagsnamn]".
# Rena sifferreferenser ("[1]") är legitima.
_PLATSHALLARE = re.compile(r"\[[^\[\]\n]{1,60}\]")

# Skyddsmaskering: länkar, e-postadresser och organisationsnummer plockas
# undan innan felstavningsrättningen och sätts tillbaka efteråt, så att
# inget av dem någonsin kan "rättas".
_SKYDDAT = re.compile(
    r"(https?://\S+|www\.\S+|[\w.+-]+@[\w-]+\.[\w.-]+|\b\d{6}-\d{4}\b)"
)

_MARKDOWNRESTER = re.compile(r"(\*\*|__|```|^#{1,6}\s)", re.MULTILINE)


@dataclass(frozen=True)
class Anmarkning:
    kod: str
    beskrivning: str
    allvarlig: bool = False


@dataclass
class Kontrollresultat:
    """Resultatet av `kontrollera`: den putsade texten plus anmärkningar.

    `kraver_granskning` är kontraktet mot anroparna: sant så fort någon
    allvarlig anmärkning kvarstår — då får texten inte skickas utan
    människa, oavsett autonominivå.
    """

    text: str
    anmarkningar: list[Anmarkning] = field(default_factory=list)

    @property
    def allvarliga(self) -> list[Anmarkning]:
        return [a for a in self.anmarkningar if a.allvarlig]

    @property
    def kraver_granskning(self) -> bool:
        return bool(self.allvarliga)

    def sammanfattning(self) -> str:
        return "; ".join(a.beskrivning for a in self.anmarkningar) or "ok"


def _ratta_felstavningar(text: str) -> tuple[str, list[str]]:
    """Rättar orden i FELSTAVNINGAR med ordgräns, versalbevarat.

    Returnerar (ny text, lista av 'fel→rätt'). Skyddade segment (länkar,
    adresser, orgnr) är redan bortmaskerade av anroparen.
    """
    rattade: list[str] = []

    def ersatt(match: re.Match) -> str:
        ord_ = match.group(0)
        ratt = FELSTAVNINGAR[ord_.lower()]
        if ord_[0].isupper():
            ratt = ratt[0].upper() + ratt[1:]
        rattade.append(f"{ord_}→{ratt}")
        return ratt

    monster = re.compile(
        r"\b(" + "|".join(re.escape(o) for o in FELSTAVNINGAR) + r")\b",
        re.IGNORECASE,
    )
    return monster.sub(ersatt, text), rattade


def putsa(text: str) -> tuple[str, list[Anmarkning]]:
    """Deterministiska, riskfria rättningar. Ändrar aldrig ett faktum.

    Returnerar (putsad text, anmärkningar om vad som gjordes). Anropas av
    `kontrollera`, men är användbar ensam där texten ändå ska till en
    människa (omformuleringsknapparna, chattsvar).
    """
    anmarkningar: list[Anmarkning] = []
    original = text

    # Maskera skyddade segment så att inget nedan kan röra dem.
    skyddade: list[str] = []

    def maskera(match: re.Match) -> str:
        skyddade.append(match.group(0))
        return f"\x00{len(skyddade) - 1}\x00"

    text = _SKYDDAT.sub(maskera, text)

    # Blankstegsstädning. Mellanslag före skiljetecken är aldrig korrekt
    # svenska — vanligaste resterna efter platshållarstädningen ("Hej ,").
    text = text.replace(" ", " ")
    text = re.sub(r"[ \t]+([,.!?;:])", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # "Hej ,"-fallet när namnet försvunnit: "Hej," är en korrekt hälsning.
    text = re.sub(r"^(Hej|Hejsan|Goddag|Hallå)[ \t]*,[ \t]*$", r"\1,", text, flags=re.MULTILINE)

    # Kurerade felstavningar.
    text, rattade = _ratta_felstavningar(text)
    if rattade:
        anmarkningar.append(
            Anmarkning("felstavning_rattad", "Rättade: " + ", ".join(rattade))
        )

    # Återställ skyddade segment.
    for i, segment in enumerate(skyddade):
        text = text.replace(f"\x00{i}\x00", segment)

    text = "\n".join(rad.rstrip() for rad in text.splitlines()).strip()
    if text != original.strip() and not rattade:
        anmarkningar.append(Anmarkning("blanksteg_putsat", "Blanksteg/skiljetecken putsade"))
    return text, anmarkningar


def kontrollera(text: str, *, sprak: str = "sv") -> Kontrollresultat:
    """Hela efterkontrollen: putsa + flagga det som kräver en människa.

    `sprak` är textens avsedda språk ('sv' eller 'en'). Engelska inslag
    flaggas bara när texten ska vara svensk.
    """
    text = text or ""
    putsad, anmarkningar = putsa(text)
    resultat = Kontrollresultat(text=putsad, anmarkningar=anmarkningar)

    if not putsad:
        resultat.anmarkningar.append(
            Anmarkning("tom_text", "Texten är tom efter putsning", allvarlig=True)
        )
        return resultat

    if "�" in putsad:
        resultat.anmarkningar.append(
            Anmarkning(
                "ersattningstecken",
                "Texten innehåller ersättningstecken (trasig teckenkodning)",
                allvarlig=True,
            )
        )

    # Platshållare som överlevt. Rena siffror ("[1]") är legitima referenser.
    for match in _PLATSHALLARE.finditer(putsad):
        inre = match.group(0)[1:-1].strip()
        if not inre.isdigit():
            resultat.anmarkningar.append(
                Anmarkning(
                    "platshallare",
                    f"Kvarlämnad platshållare: {match.group(0)!r}",
                    allvarlig=True,
                )
            )
            break

    if _MARKDOWNRESTER.search(putsad):
        resultat.anmarkningar.append(
            Anmarkning("markdownrester", "Markdownrester kvar i texten", allvarlig=True)
        )

    if sprak == "sv":
        traffar = {m.group(0).lower() for m in _ENGELSKA_ORD.finditer(putsad.lower())}
        if len(traffar) >= 3:
            resultat.anmarkningar.append(
                Anmarkning(
                    "engelska_inslag",
                    "Engelska inslag i svensk text: " + ", ".join(sorted(traffar)),
                    allvarlig=True,
                )
            )

    # Avhuggen text: slutar mitt i en tanke. Signatur/namn på sista raden är
    # normalt, så bara tydliga avhugg flaggas.
    if putsad.rstrip()[-1:] in {",", ":", ";", "-", "–"}:
        resultat.anmarkningar.append(
            Anmarkning("avhuggen_text", "Texten slutar mitt i en mening", allvarlig=True)
        )

    return resultat


def _verifiera_korrektur(original: str, korrigerad: str) -> bool:
    """Får LLM-korrekturen accepteras? Fakta ska ha överlevt ordagrant.

    Fail-closed: minsta tvivel => originalet behålls och ärendet går till
    mänsklig granskning i stället.
    """
    if not korrigerad.strip():
        return False
    # Längden får inte dra iväg — korrektur är inte omskrivning.
    if not (0.6 <= len(korrigerad) / max(len(original), 1) <= 1.4):
        return False
    # Varje skyddat segment (länk, adress, orgnr) måste finnas kvar.
    for segment in _SKYDDAT.findall(original):
        if segment not in korrigerad:
            return False
    # Varje tal måste finnas kvar (priser, datum, procent).
    for tal in re.findall(r"\d+(?:[.,:]\d+)*", original):
        if tal not in korrigerad:
            return False
    # Skyddade namn får inte försvinna eller stavas om.
    for namn in SKYDDADE_NAMN:
        if original.count(namn) != korrigerad.count(namn):
            return False
    return True


_KORREKTUR_PROMPT = """Du är korrekturläsare. Rätta ENBART språket i texten nedan:
stavning, grammatik, särskrivningar, skiljetecken och meningsbyggnad.

Absoluta regler:
1. Ändra ALDRIG fakta, namn, siffror, belopp, datum, länkar,
   e-postadresser, organisationsnummer eller budskap.
2. Lägg inte till och ta inte bort innehåll — bara språkrättning.
3. Behåll styckeindelning, hälsning och avslutning exakt där de står.
4. Är texten redan korrekt: returnera den oförändrad.
5. Svara ENBART med texten — ingen kommentar, inga citattecken.

Kända fel som flaggats:
{anmarkningar}

Text:
{text}"""


async def korrekturlas_llm(
    text: str, *, anmarkningar: list[Anmarkning] | None = None
) -> tuple[str, bool]:
    """Kort LLM-korrekturpass. Returnerar (text, accepterad).

    Körs BARA när den deterministiska kontrollen flaggat något — det håller
    kostnaden på noll extra anrop för den friska majoriteten. I simulering
    (ingen nyckel) görs ingenting. Fälls verifieringen returneras
    originalet med accepterad=False, och anroparen ska då tvinga granskning.
    """
    from .config import get_settings

    settings = get_settings()
    if settings.is_simulation():
        return text, False

    from .agent.llm import get_llm_client, tankande_kwargs

    prompt = _KORREKTUR_PROMPT.format(
        anmarkningar="\n".join(f"- {a.beskrivning}" for a in (anmarkningar or []))
        or "- (inga specifika, gör en allmän korrekturläsning)",
        text=text,
    )
    try:
        response = await get_llm_client().chat.completions.create(
            model=settings.model,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
            **tankande_kwargs(),
        )
    except Exception:  # noqa: BLE001 — korrekturen får aldrig fälla flödet
        logger.exception("LLM-korrekturen misslyckades; originalet behålls")
        return text, False

    korrigerad = (response.choices[0].message.content or "").strip()
    if _verifiera_korrektur(text, korrigerad):
        return korrigerad, True
    logger.warning("LLM-korrekturen förkastades av verifieringen; originalet behålls")
    return text, False


async def sakra_utgaende_text(text: str, *, sprak: str = "sv") -> Kontrollresultat:
    """Hela kedjan för text som KAN skickas utan människa: kontrollera,
    LLM-korrektur vid behov, kontrollera igen. Kvarstår allvarliga
    anmärkningar är `kraver_granskning` sant och anroparen ska degradera
    till mänsklig granskning.
    """
    resultat = kontrollera(text, sprak=sprak)
    if not resultat.kraver_granskning:
        return resultat

    korrigerad, accepterad = await korrekturlas_llm(
        resultat.text, anmarkningar=resultat.allvarliga
    )
    if not accepterad:
        return resultat

    om_resultat = kontrollera(korrigerad, sprak=sprak)
    om_resultat.anmarkningar.append(
        Anmarkning("llm_korrektur", "LLM-korrektur utförd och verifierad")
    )
    return om_resultat
