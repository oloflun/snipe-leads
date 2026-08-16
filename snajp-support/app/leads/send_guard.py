"""De sex spärrar varje utskick passerar innan det får lämna huset.

**Ta inte bort en regel härifrån utan att läsa varför den finns.** Varje regel
har sitt skäl skrivet på plats, och skälet är i fem fall av sex juridiskt eller
ekonomiskt, inte estetiskt. Nästa person som frestas ta bort en spärr ska möta
motivet i samma skärmbild som koden.

## Varför det här är ren logik utan I/O

Samma val som `send_decision.py` gjorde, av samma skäl: det här är exakt det
som avgör om ett mejl går till en riktig människa, och det ska gå att testa
fullständigt utan en databas, utan en klocka och utan en mejlserver. Anroparen
samlar in fakta; den här modulen dömer.

Följden är att `TenantHistorik` måste fyllas i korrekt av anroparen. Fälten
har därför inga defaults — ett glömt fält blir ett TypeError vid anropet, inte
en spärr som tyst betedde sig som om historiken var tom.

## Ordningen mellan reglerna är inte godtycklig

Först det som ALDRIG får skickas (samtycke och uteslutning), sedan det som är
fel i innehållet, sedan det som bara är fel i tiden, sist granskningskön. En
kontroll som svarar "vänta till imorgon" på ett mejl som aldrig borde skickas
hade dolt ett regelbrott bakom en fördröjning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

STOCKHOLM = ZoneInfo("Europe/Stockholm")

#: Åtgärder guarden kan besluta om.
SKICKA = "skicka"
GRANSKA = "granska"
BLOCKERA = "blockera"
KOLA_OM = "köa_om"

# -- Regel 5:s tal, samlade så att de går att läsa på ett ställe -------------

#: Domänuppvärmning. En ny avsändardomän som börjar med hundra mejl om dagen
#: hamnar i skräpposten permanent — mottagarnas filter lär sig av volymkurvan,
#: inte av innehållet. Tjugo om dagen i två veckor är den kurva en riktig
#: verksamhet har.
UPPVARMNING_DAGAR = 14
UPPVARMNING_TAK_PER_DAG = 20

#: Ett företag kontaktas högst en gång per kvartal. Det är inte en artighet:
#: upprepade kallmejl till samma bolag är den enskilt vanligaste orsaken till
#: att en avsändardomän blir spärrad, och den kunden är då förlorad för alla
#: våra tenants som delar infrastruktur.
KARENS_DAGAR_PER_FORETAG = 90

#: Kontorstid, svensk tid. Ett kallmejl klockan 03:14 läses som maskinellt
#: även när texten är bra.
TIDIGAST_TIMME = 8
SENAST_TIMME = 17

#: De tre första utskicken för en ny tenant granskas alltid av en människa.
GRANSKADE_FORSTA_UTSKICK = 3


@dataclass(frozen=True)
class Avsandare:
    """Hyreskundens identitet. Alla tre fälten är lagkrav i sidfoten."""

    foretagsnamn: str
    orgnr: str
    postadress: str


@dataclass(frozen=True)
class Utskick:
    mottagare: str
    amne: str
    brodtext: str
    #: Normaliserad företagsidentitet (org.nr om det finns, annars domänen).
    #: Används för karensregeln — inte mottagaradressen, eftersom ett bolag
    #: som byter kontaktperson annars hade fått ett nytt mejl dagen efter.
    foretagsnyckel: str
    #: True när mottagaradressen är personlig (`fornamn.efternamn@`) snarare
    #: än funktionell. Sätts av `Prospect.epost_ar_personlig`.
    personlig_adress: bool


@dataclass(frozen=True)
class TenantHistorik:
    skickade_totalt: int
    skickade_idag: int
    tenant_alder_dagar: int
    senaste_kontakt_med_foretaget: datetime | None
    #: Adresser som avregistrerat sig. Gäller HELA tenanten, inte kampanjen.
    suppressions: frozenset[str]
    #: Adresser som redan kontaktats.
    tidigare_kontaktade: frozenset[str]
    #: Kundens egen kundlista — befintliga kunder ska inte kallmejlas.
    egna_kunder: frozenset[str]


@dataclass(frozen=True)
class GuardBeslut:
    atgard: str
    regel: str | None
    skal: str

    @property
    def tillaten(self) -> bool:
        return self.atgard == SKICKA


def check_send_guard(
    *,
    avsandare: Avsandare,
    utskick: Utskick,
    historik: TenantHistorik,
    nu: datetime,
) -> GuardBeslut:
    """Kör alla sex reglerna i ordning och returnerar FÖRSTA avvikelsen."""
    for regel in (
        _regel_3_suppression,
        _regel_1_avsandaridentifikation,
        _regel_2_avregistrering,
        _regel_4_personuppgiftsflagga,
        _regel_5_volymtak,
        _regel_6_granskningsko,
    ):
        beslut = regel(avsandare=avsandare, utskick=utskick, historik=historik, nu=nu)
        if beslut is not None:
            return beslut

    return GuardBeslut(SKICKA, None, "Alla sex spärrar godkände utskicket.")


# -- Regel 1 ----------------------------------------------------------------


def _regel_1_avsandaridentifikation(*, avsandare, utskick, historik, nu) -> GuardBeslut | None:
    """Fullständigt företagsnamn, org.nr och fysisk adress i varje mejls sidfot.

    VARFÖR: marknadsföringslagen kräver att avsändaren går att identifiera, och
    e-handelslagen kräver organisationsnummer. Kravet gäller HYRESKUNDEN, inte
    Snajp — det är deras produkt som säljs, och en mottagare som vill klaga
    ska nå dem, inte oss.

    Kontrollen görs på den färdiga brödtexten och inte på en mall, eftersom
    det är brödtexten som skickas. En mall som är rätt hjälper inte om
    sammanslagningen tappade fältet.
    """
    saknas = [
        etikett
        for etikett, varde in (
            ("företagsnamn", avsandare.foretagsnamn),
            ("organisationsnummer", avsandare.orgnr),
            ("postadress", avsandare.postadress),
        )
        if not str(varde).strip() or _normaliserad(varde) not in _normaliserad(utskick.brodtext)
    ]
    if saknas:
        return GuardBeslut(
            BLOCKERA,
            "1_avsandaridentifikation",
            "Sidfoten saknar " + ", ".join(saknas) + ". Marknadsföringslagen kräver "
            "att avsändaren går att identifiera i varje utskick.",
        )
    return None


# -- Regel 2 ----------------------------------------------------------------

#: En avregistreringslänk ska vara en länk, inte en uppmaning att svara på
#: mejlet. "Svara STOPP" lägger arbetet på mottagaren och går inte att
#: verifiera maskinellt.
_OPT_OUT_MONSTER = re.compile(
    r"https?://\S*(avregistrera|avanmal|unsubscribe|optout|opt-out)\S*", re.IGNORECASE
)


def _regel_2_avregistrering(*, avsandare, utskick, historik, nu) -> GuardBeslut | None:
    """Fungerande opt-out-länk i varje mejl.

    VARFÖR: utan den finns ingen laglig väg ut ur utskicken, och en mottagare
    som inte kan avregistrera sig anmäler i stället. En klick ska skriva till
    `suppressions` och gälla OMEDELBART för hela tenanten — inte bara den
    kampanjen. Det sistnämnda är det vanliga felet: en avregistrering som
    bara gäller en kampanj betyder att samma person får nästa kampanj, och då
    är löftet i mejlet ett brutet löfte.
    """
    if not _OPT_OUT_MONSTER.search(utskick.brodtext):
        return GuardBeslut(
            BLOCKERA,
            "2_avregistrering",
            "Mejlet saknar en klickbar avregistreringslänk. En uppmaning att "
            "svara på mejlet räcker inte — den går varken att verifiera eller "
            "att åtgärda automatiskt.",
        )
    return None


# -- Regel 3 ----------------------------------------------------------------


def _regel_3_suppression(*, avsandare, utskick, historik, nu) -> GuardBeslut | None:
    """Kontroll mot suppressions, tidigare kontaktade och kundens kundlista.

    VARFÖR KONTROLLEN SKER HÄR OCH INTE VID KÖNINGEN: ett utkast kan ha legat
    i kön i dagar. Avregistrerar sig mottagaren under tiden är det den här
    kontrollen — i sändningsögonblicket — som är den enda som ser det. En
    kontroll vid köningen hade varit en kontroll mot gårdagens sanning.

    Den ligger FÖRST av alla sex regler därför att den är den enda vars brott
    är oåterkalleligt mot en person som uttryckligen bett att slippa.
    """
    adress = _normaliserad_adress(utskick.mottagare)

    if adress in {_normaliserad_adress(a) for a in historik.suppressions}:
        return GuardBeslut(
            BLOCKERA,
            "3_suppression",
            f"{utskick.mottagare} har avregistrerat sig. Avregistreringen gäller "
            "hela tenanten och är permanent.",
        )

    if adress in {_normaliserad_adress(a) for a in historik.egna_kunder}:
        return GuardBeslut(
            BLOCKERA,
            "3_suppression",
            f"{utskick.mottagare} finns i kundens egen kundlista. En befintlig "
            "kund ska inte få ett kallmejl om det de redan köpt.",
        )

    if adress in {_normaliserad_adress(a) for a in historik.tidigare_kontaktade}:
        return GuardBeslut(
            BLOCKERA,
            "3_suppression",
            f"{utskick.mottagare} har redan kontaktats i en tidigare körning.",
        )

    return None


# -- Regel 4 ----------------------------------------------------------------

#: De fyra upplysningar GDPR art. 14 kräver när uppgiften inte samlats in från
#: personen själv. Alla fyra måste finnas — en text som säger vem vi är men
#: inte varifrån uppgiften kom uppfyller inte artikeln.
_ART14_KRAV = {
    "vem som samlar in": ("personuppgiftsansvarig", "ansvarig för dina uppgifter", "vi som behandlar"),
    "varför": ("ändamål", "därför att", "syftet"),
    "varifrån uppgiften kom": ("hämtad", "hämtat", "källa", "offentlig"),
    "rätten att invända": ("invända", "motsätta", "radera dina uppgifter"),
}


def _regel_4_personuppgiftsflagga(*, avsandare, utskick, historik, nu) -> GuardBeslut | None:
    """Personlig mottagaradress kräver GDPR art. 14-information i mejlet.

    VARFÖR: `fornamn.efternamn@bolaget.se` är en personuppgift. Art. 14 gäller
    när uppgiften INTE samlats in från personen själv, vilket per definition är
    fallet vid kallmejl — och den kräver att informationen lämnas vid första
    kontakten, inte på begäran.

    `info@` och `kontakt@` är funktionsadresser och omfattas inte. Det är
    därför `Prospect.epost_ar_personlig` hellre flaggar en funktionsadress för
    mycket än missar en personlig: den här regelns kostnad vid falskt utslag
    är ett extra stycke text, och vid missat utslag ett regelbrott.
    """
    if not utskick.personlig_adress:
        return None

    text = _normaliserad(utskick.brodtext)
    saknade = [
        etikett
        for etikett, nycklar in _ART14_KRAV.items()
        if not any(nyckel in text for nyckel in nycklar)
    ]
    if saknade:
        return GuardBeslut(
            BLOCKERA,
            "4_personuppgiftsflagga",
            f"{utskick.mottagare} är en personlig adress, men mejlet saknar "
            "GDPR art. 14-information om " + ", ".join(saknade) + ".",
        )
    return None


# -- Regel 5 ----------------------------------------------------------------


def _regel_5_volymtak(*, avsandare, utskick, historik, nu) -> GuardBeslut | None:
    """Tre tak: per dag under uppvärmningen, per företag och kvartal, samt
    kontorstid.

    VARFÖR DE HÖR IHOP: alla tre skyddar samma sak — att avsändardomänen
    fortsätter nå fram. En domän som blir spärrad tar med sig varje framtida
    utskick för den kunden, och en spärrad domän går inte att överklaga.
    """
    lokal_tid = nu.astimezone(STOCKHOLM)

    # 5a. Kontorstid, vardagar. Ett kallmejl 03:14 läses som maskinellt även
    # när texten är bra. Söndag är inte en arbetsdag för mottagaren heller.
    if lokal_tid.weekday() >= 5:
        return GuardBeslut(
            KOLA_OM,
            "5_volymtak",
            f"{lokal_tid:%A} är helg. Utskick sker vardagar "
            f"{TIDIGAST_TIMME}–{SENAST_TIMME} svensk tid.",
        )
    if not (TIDIGAST_TIMME <= lokal_tid.hour < SENAST_TIMME):
        return GuardBeslut(
            KOLA_OM,
            "5_volymtak",
            f"Klockan är {lokal_tid:%H:%M} svensk tid. Utskick sker "
            f"{TIDIGAST_TIMME}–{SENAST_TIMME} på vardagar.",
        )

    # 5b. Karens per företag. Nyckeln är FÖRETAGET, inte adressen — ett bolag
    # som byter kontaktperson ska inte kunna få ett nytt mejl dagen efter.
    senaste = historik.senaste_kontakt_med_foretaget
    if senaste is not None:
        dagar_sedan = (nu - senaste).days
        if dagar_sedan < KARENS_DAGAR_PER_FORETAG:
            return GuardBeslut(
                BLOCKERA,
                "5_volymtak",
                f"{utskick.foretagsnyckel} kontaktades för {dagar_sedan} dagar sedan. "
                f"Karenstiden är {KARENS_DAGAR_PER_FORETAG} dagar per företag.",
            )

    # 5c. Domänuppvärmning de första två veckorna.
    if historik.tenant_alder_dagar < UPPVARMNING_DAGAR:
        if historik.skickade_idag >= UPPVARMNING_TAK_PER_DAG:
            return GuardBeslut(
                KOLA_OM,
                "5_volymtak",
                f"Dagens tak är nått ({historik.skickade_idag} av "
                f"{UPPVARMNING_TAK_PER_DAG}). Avsändardomänen är {historik.tenant_alder_dagar} "
                f"dagar gammal och värms upp i {UPPVARMNING_DAGAR} dagar.",
            )

    return None


# -- Regel 6 ----------------------------------------------------------------


def _regel_6_granskningsko(*, avsandare, utskick, historik, nu) -> GuardBeslut | None:
    """De tre första utskicken för en ny tenant granskas ALLTID av en människa,
    oavsett autonominivå.

    VARFÖR: det är första gången kundens produktbeskrivning, ICP och tonläge
    möter verkligheten samtidigt. Är något fel i underlaget syns det i det
    första mejlet — och då är tre mejl skadan, inte trehundra.

    Den ligger SIST därför att de tidigare reglerna ska ha sagt sitt först:
    ett mejl som bryter mot regel 2 ska blockeras, inte läggas i en
    granskningskö där en människa förväntas upptäcka samma sak.
    """
    if historik.skickade_totalt < GRANSKADE_FORSTA_UTSKICK:
        return GuardBeslut(
            GRANSKA,
            "6_granskningsko",
            f"Utskick nr {historik.skickade_totalt + 1} för den här kunden. De "
            f"{GRANSKADE_FORSTA_UTSKICK} första granskas alltid manuellt, oavsett "
            "autonominivå.",
        )
    return None


# -- Hjälpare ---------------------------------------------------------------


def _normaliserad(text: object) -> str:
    """Gemener och ihopdragna mellanrum.

    Sidfotens org.nr kan stå som '556824-9022' eller '5568249022'; adressen kan
    ha radbrytning där mallen hade mellanslag. Utan normalisering hade regel 1
    fällt korrekta mejl på formatering, och den sortens falsklarm är hur en
    spärr blir bortkommenterad.
    """
    return re.sub(r"\s+", " ", str(text or "")).strip().casefold()


def _normaliserad_adress(adress: object) -> str:
    return str(adress or "").strip().casefold()


def foretagsnyckel(*, orgnr: str | None, epost: str | None, hemsida: str | None) -> str:
    """Den identitet karensregeln räknar på.

    Org.nr först: det är den enda identifierare som överlever att bolaget
    byter domän. Domänen är näst bäst. Adressen är sista utvägen och är
    medvetet svagast — den gör karensen per person i stället för per företag,
    vilket är en lucka vi hellre ser i koden än gömmer bakom en gissning.
    """
    if orgnr and orgnr.strip():
        return re.sub(r"\D", "", orgnr)
    for kandidat in (hemsida, epost):
        if kandidat and "@" in str(kandidat):
            return str(kandidat).split("@", 1)[-1].strip().casefold()
        if kandidat and str(kandidat).strip():
            text = str(kandidat).strip().casefold()
            for prefix in ("https://", "http://"):
                if text.startswith(prefix):
                    text = text[len(prefix) :]
            text = text.split("/", 1)[0]
            return text[4:] if text.startswith("www.") else text
    return ""
