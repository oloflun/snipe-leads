"""Skatteverkets Beskattningsengagemang-API — F-skatt, moms, arbetsgivare.

Källa: `tjanstebeskrivning-beskattningsengagemang-v1`, dokumentversion 1.2
(2024-05-23), Skatteverkets utvecklarportal. Varje endpoint, headernamn och
felkod nedan står i det dokumentet — ingenting här är gissat.

## Varför den här modulen INTE ligger i `sources/`

`ProspectSource` svarar på "vilka bolag matchar det här ICP:t". Skatteverket
kan inte svara på den frågan: API:t slår upp EN identitet i taget och har
ingen sökning. Att pressa in det i `search(icp)` hade gjort protokollet till
en lögn — och `orgnr.py` skriver redan ut varför ett namn som lovar mer än
koden håller är hur nästa person bygger ett antagande på en kontroll som
aldrig gjordes.

Det här är alltså en VERIFIERINGS-klient för tenantens EGET orgnr vid
onboarding, inte en prospektkälla. Luckan `BolagsverketSource` och
`AllabolagSource` är stubbade för finns kvar — den kräver fortfarande ett
licensavtal för Näringslivsregistret.

## Vad ett 200-svar INTE betyder

**Ett svar betyder inte att engagemanget gäller idag.** Tjänsten returnerar
personens SENASTE registrering, och den kan enligt tjänstebeskrivningen
(4.2.2) ha ett `startdatum` i framtiden eller redan vara avslutad med ett
`slutdatum` som passerat. Ett bolag vars F-skatt drogs in för konkurs 2019
svarar alltså 200 med hela posten kvar.

Därför finns `Engagemang.ar_aktiv()`, och därför returnerar den här modulen
ALDRIG en naken boolean från HTTP-statusen. Den som bara kollar `is not None`
har byggt in "avregistrerad för konkurs" som ett godkänt svar.

404 betyder att personen aldrig haft engagemanget — ett giltigt utfall, inte
ett fel, och därför `None` och inget undantag (samma gräns som `SourceError`
drar i `sources/base.py`: "källan svarade tomt" är inte "källan kraschade").

## Varför ingen nyckel kan sättas ännu

Auktorisation sker med OAuth2 Authorization Code Grant, och den externa
användaren autentiseras med e-legitimation (avsnitt 2.6 och 5.4). Det är
BankID i en webbläsare — det finns ingen client_credentials-variant där
backenden slår upp ett godtyckligt orgnr på egen hand. Uppslaget görs för
en firmatecknare som just loggat in, eller för ett registrerat ombud med
organisationscertifikat.

Följden för koden: `access_token` är ett ARGUMENT hit, aldrig något den här
modulen skaffar själv. Inloggningsflödet hör hemma i Next-appens onboarding
och finns inte än — se `paborja_inloggning` längst ned.

API-nycklar (client_id/client_secret) delas ut av Skatteverket efter ansökan
via formulär: testnycklar mot sandboxen, produktionsnycklar först efter
tecknat avtal. Ingen av dem finns 2026-08-29, och tills de gör det
returnerar `get_skatteverket_klient()` `None` i stället för att låtsas.

## Dataskydd

Svaren bär en identifierad näringsidkares beskattningsuppgifter, och för en
enskild firma ÄR identiteten ett personnummer. Ingenting av svarskroppen
loggas därför någonstans i den här modulen — bara korrelations-id:t, som är
till för precis den spårbarheten. Samma hållning som `prioriterat_mejl.py`
har till kundens ärendetext.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from ..config import Settings, get_settings
from .orgnr import OgiltigtOrgnrError, validera_format

logger = logging.getLogger("snajp-support.skatteverket")

#: Maximal svarstid enligt tjänstebeskrivningen (3.3) är 30 sekunder för
#: testtjänsten. Vi väntar inte längre än så: onboarding är ett synkront
#: klick i ett formulär, och en användare som väntat en halv minut har redan
#: laddat om sidan.
TIDSTAK_SEKUNDER = 30.0

#: De fyra resurserna under `/engagemang/v1/<identitet>/`. `registerutdrag`
#: svarar med PDF, inte JSON, och hanteras därför inte av `_hamta`.
FSKATT = "fskatt"
MOMS = "moms"
ARBETSGIVARE = "arbetsgivarregistrerad"


class SkatteverketFel(RuntimeError):
    """Basklass — anropet gick inte att genomföra."""


class SkatteverketAuktoriseringsfel(SkatteverketFel):
    """401/403: token saknas, har gått ut, eller behörighet saknas.

    Egen typ för att den ska gå att skilja från ett driftfel i anropande kod:
    åtgärden är att logga in användaren igen, inte att försöka om."""


class SkatteverketTillfalligtFel(SkatteverketFel):
    """429/500/503/504 — enligt tjänstebeskrivningen (5.6) ska anropet göras
    om efter en minut. Ingen retry sker här: den som anropar vet om användaren
    står och väntar i ett formulär eller om det är ett bakgrundsjobb."""


@dataclass(frozen=True)
class Engagemang:
    """Ett beskattningsengagemang som det ser ut hos Skatteverket.

    Ett gemensamt fält för alla tre typerna, med det typspecifika i `extra` —
    samma skäl som `Prospect` anger: annars blir varje ny uppgift Skatteverket
    lägger till en ändring i en datastruktur alla tre delar.
    """

    typ: str
    startdatum: date | None = None
    slutdatum: date | None = None
    avslutsorsak: str | None = None
    avslutsorsak_kod: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def ar_aktiv(self, idag: date | None = None) -> bool:
        """Om engagemanget gäller den angivna dagen.

        LÄS MODULENS DOCSTRING FÖRE DU BYTER UT DEN HÄR MOT ETT NULL-TEST.
        Ett 200-svar säger bara att en registrering finns i registret, inte
        att den gäller nu — den kan ha ett startdatum i framtiden eller vara
        avslutad. Båda ändarna kontrolleras därför, och `slutdatum` jämförs
        inklusivt: sista giltighetsdagen är fortfarande en giltig dag.
        """
        dagen = idag or date.today()
        if self.startdatum is None or self.startdatum > dagen:
            return False
        return self.slutdatum is None or self.slutdatum >= dagen


def till_identitet(orgnr: str) -> str:
    """Tio siffror -> de tolv Skatteverket vill ha (`16NNNNNNNNNN`).

    Formatet står i tjänstebeskrivningen 4.2.1: tolv siffror, antingen
    `16NNNNNNNNNN` för en juridisk person eller `ÅÅÅÅMMDDNNNN` för en fysisk.

    `orgnr.normalisera()` STRIPPAR sekelprefixet — det är rätt för lagring
    och visning, men gör att ett värde därifrån aldrig kan skickas rakt in
    här. Prefixet sätts därför tillbaka.

    SEKLET LÄSES AV INNAN, INTE GISSAS EFTERÅT. En enskild firmas orgnr ÄR
    ett personnummer (se `orgnr._strip_sekel`), och ett sådant som redan bär
    `19`/`20` ska behålla just det — hade vi ersatt det med `16` pekade
    anropet på en annan identitet. Kontrollsiffran prövas i BÅDA fallen:
    `validera_format` är enda vägen ut härifrån, så ett felskrivet
    personnummer fastnar här och inte som en 400:a hos Skatteverket.
    """
    siffror = _bara_siffror(orgnr)
    sekel = siffror[:2] if len(siffror) == 12 and siffror[:2] in ("19", "20") else "16"
    return sekel + validera_format(siffror)


def _bara_siffror(text: str) -> str:
    return "".join(t for t in str(text or "") if t.isdigit())


def _datum(varde: object) -> date | None:
    """"YYYY-MM-DD" -> date. Tomt eller trasigt -> None.

    Ett oläsligt datum blir None och inte ett undantag, eftersom `ar_aktiv`
    då svarar False — alltså "vi kan inte visa att det gäller". Att kasta här
    hade fällt hela onboardingen på ett fält vi inte ens behöver för alla tre
    engagemangstyperna.
    """
    text = str(varde or "").strip()
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _till_engagemang(typ: str, kropp: dict[str, Any]) -> Engagemang:
    kant = {"startdatum", "slutdatum", "avslutsorsak", "avslutsorsakKod"}
    return Engagemang(
        typ=typ,
        startdatum=_datum(kropp.get("startdatum")),
        slutdatum=_datum(kropp.get("slutdatum")),
        avslutsorsak=(kropp.get("avslutsorsak") or None),
        avslutsorsak_kod=kropp.get("avslutsorsakKod"),
        # Allt Skatteverket skickar utöver de fyra gemensamma fälten behålls
        # — momstyp, redovisningsmetod, sasongsarbetsgivare. Att plocka ut
        # bara de vi använder idag hade tappat uppgifter tyst.
        extra={n: v for n, v in kropp.items() if n not in kant},
    )


class SkatteverketEngagemang:
    """Klient mot `/beskattning/foretag/engagemang/v1/`.

    Tar ett `access_token` per anrop och skaffar aldrig ett själv — se
    modulens docstring om varför det inte går utan en inloggad människa.
    """

    def __init__(
        self,
        *,
        bas_url: str,
        client_id: str,
        client_secret: str,
        tidstak: float = TIDSTAK_SEKUNDER,
    ) -> None:
        self.bas_url = bas_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.tidstak = tidstak

    def _url(self, identitet: str, resurs: str) -> str:
        return f"{self.bas_url}/beskattning/foretag/engagemang/v1/{identitet}/{resurs}"

    async def _hamta(
        self, *, identitet: str, resurs: str, access_token: str, ombud: str = ""
    ) -> dict[str, Any] | None:
        import httpx

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            # Tjänstebeskrivningen 2.6: varje anrop ska bära en UNIK
            # anropsidentitet, och de får inte återanvändas — Skatteverket
            # auditloggar dem i upp till fem år för att kunna utreda
            # säkerhetsincidenter. uuid4 är 36 tecken, exakt takets längd.
            "skv_client_correlation_id": str(uuid.uuid4()),
        }
        if ombud:
            headers["skv_ext_ombud"] = ombud

        async with httpx.AsyncClient(timeout=self.tidstak) as klient:
            svar = await klient.get(self._url(identitet, resurs), headers=headers)

        # Aldrig identiteten och aldrig svarskroppen i loggen — det är en
        # identifierad näringsidkares beskattningsuppgifter, och för en
        # enskild firma är identiteten ett personnummer. Korrelations-id:t
        # räcker för att följa anropet hos Skatteverket.
        logger.info(
            "Skatteverket %s: status=%s korrelation=%s",
            resurs,
            svar.status_code,
            headers["skv_client_correlation_id"],
        )

        if svar.status_code == 404:
            # "Om personen aldrig haft engagemanget returneras ingenting"
            # (4.2.2). Ett giltigt svar, inte ett fel.
            return None
        if svar.status_code in (401, 403):
            raise SkatteverketAuktoriseringsfel(
                f"Skatteverket avvisade anropet ({svar.status_code}). Tokenen har "
                f"gått ut eller saknar behörighet för identiteten — användaren "
                f"behöver logga in med e-legitimation igen."
            )
        if svar.status_code in (429, 500, 503, 504):
            raise SkatteverketTillfalligtFel(
                f"Skatteverket svarade {svar.status_code}. Enligt tjänste"
                f"beskrivningen ska anropet göras om efter en minut."
            )
        if svar.status_code >= 400:
            raise SkatteverketFel(
                f"Skatteverket svarade {svar.status_code} på {resurs}. Kontrollera "
                f"identitetsformatet (tolv siffror) och headers."
            )
        return svar.json()

    async def fskatt(
        self, orgnr: str, *, access_token: str, ombud: str = ""
    ) -> Engagemang | None:
        """Godkännande för F-skatt eller FA-skatt. None = aldrig haft det.

        `extra["skatteform"]` är "F" eller "FA".
        """
        kropp = await self._hamta(
            identitet=till_identitet(orgnr),
            resurs=FSKATT,
            access_token=access_token,
            ombud=ombud,
        )
        return _till_engagemang(FSKATT, kropp) if kropp is not None else None

    async def moms(
        self, orgnr: str, *, access_token: str, ombud: str = ""
    ) -> Engagemang | None:
        """Momsregistrering. None = aldrig varit momsregistrerad.

        `extra` bär bl.a. `momstyp` ("Kvartal den 12:e"), `redovisningsmetod`
        ("Faktureringsmetod") och `skattskyldigFROM` — det är de uppgifterna
        bookkeeping-agenten annars svarar generiskt om.
        """
        kropp = await self._hamta(
            identitet=till_identitet(orgnr),
            resurs=MOMS,
            access_token=access_token,
            ombud=ombud,
        )
        return _till_engagemang(MOMS, kropp) if kropp is not None else None

    async def arbetsgivare(
        self, orgnr: str, *, access_token: str, ombud: str = ""
    ) -> Engagemang | None:
        """Arbetsgivarregistrering. `extra["sasongsarbetsgivare"]` är bool."""
        kropp = await self._hamta(
            identitet=till_identitet(orgnr),
            resurs=ARBETSGIVARE,
            access_token=access_token,
            ombud=ombud,
        )
        return _till_engagemang(ARBETSGIVARE, kropp) if kropp is not None else None


@dataclass(frozen=True)
class SkatteverketAtkomst:
    """Vad ett uppslag kräver, satt av SERVERN — aldrig av modellen.

    ## Varför orgnr ligger här och inte i ett verktygsargument

    INV-SEC-002, samma regel som `leads_tools.py` och `bookkeeping_chat_tools.py`
    följer för tenant: ett fält modellen kan fylla i är en fråga en kund kan
    ställa om någon annan. Här är insatsen högre än vanligt, för svaret är en
    identifierad näringsidkares beskattningsuppgifter.

    ## Varför det inte ens vore möjligt att slå upp någon annan

    Tokenen är utfärdad genom BankID för EN inloggad person och gäller det
    bolag hen är huvudman för eller företräder. Skatteverket svarar 403 på en
    identitet tokenen inte täcker. Ett prospekt går alltså inte att slå upp
    ens med ett orgnr-argument — och de allmänna villkoren (§7.1) förbjuder
    det dessutom uttryckligen: API:t får bara användas "av, eller för,
    Mottagare av uppgift" för bokföring, redovisning och uppföljning.

    Läs det som två oberoende spärrar åt samma håll, och ta inte bort den ena
    för att den andra finns.
    """

    #: Tenantens EGET organisationsnummer. Aldrig ett prospekts.
    orgnr: str
    #: OAuth2-token från BankID-inloggningen. Se `paborja_inloggning`.
    access_token: str
    #: Ombudets identitet (tolv siffror). Tom vid inloggning med BankID.
    ombud: str = ""


#: De uppslag ett verktyg får be om. Modellen väljer bland dessa och inget
#: annat — samma vitlistning som `bookkeeping_chat_tools.TILLATNA_STATUS`.
TILLATNA_UPPGIFTER = (FSKATT, MOMS, ARBETSGIVARE)


async def sla_upp(
    atkomst: SkatteverketAtkomst | None,
    uppgift: str,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Ett uppslag, i en form en agent kan svara utifrån.

    Returnerar ALLTID en dict och kastar aldrig. Varje sätt att misslyckas
    blir ett `fel`-fält modellen kan agera på — samma hållning som
    `lista_underlag` har för ett ogiltigt statusfilter. Ett kast här hade
    avbrutit hela chattsvaret för något som oftast betyder "inte inloggad än".

    ## `galler_nu` är hela poängen

    Fältet räknas ut i KODEN, inte av modellen. Skatteverket returnerar
    senaste registreringen, som kan vara avslutad eller börja i framtiden —
    ett bolag vars F-skatt drogs in för konkurs 2019 svarar 200 med posten
    kvar. En modell som får rådata och ombeds "titta på datumen" kommer förr
    eller senare att svara att bolaget har F-skatt. Därför är svaret redan
    avgjort när det når modellen.
    """
    if uppgift not in TILLATNA_UPPGIFTER:
        return {
            "fel": f"Okänd uppgift: {uppgift!r}. Välj en av: "
            f"{', '.join(TILLATNA_UPPGIFTER)}."
        }

    klient = get_skatteverket_klient(settings)
    if klient is None:
        return {
            "tillgangligt": False,
            "fel": "Uppslag mot Skatteverket är inte påslaget i den här miljön "
            "(API-nycklar saknas). Svara utifrån det du vet i övrigt, och säg "
            "att den bolagsspecifika uppgiften inte gick att hämta.",
        }

    if atkomst is None or not atkomst.access_token or not atkomst.orgnr:
        return {
            "tillgangligt": False,
            "fel": "Kunden är inte inloggad med BankID mot Skatteverket, så "
            "uppgiften går inte att hämta för just det här bolaget. Be inte om "
            "organisationsnumret — uppslaget kräver inloggningen, inte numret.",
        }

    metod = {
        FSKATT: klient.fskatt,
        MOMS: klient.moms,
        ARBETSGIVARE: klient.arbetsgivare,
    }[uppgift]

    try:
        engagemang = await metod(
            atkomst.orgnr, access_token=atkomst.access_token, ombud=atkomst.ombud
        )
    except SkatteverketAuktoriseringsfel as fel:
        return {"tillgangligt": False, "fel": f"Inloggningen behöver göras om: {fel}"}
    except SkatteverketFel as fel:
        # Täcker även SkatteverketTillfalligtFel — för modellen är skillnaden
        # inte handlingsbar mitt i ett svar. Den ska säga att uppgiften inte
        # gick att hämta, inte försöka tolka en HTTP-kod.
        return {"tillgangligt": False, "fel": f"Skatteverket svarade inte: {fel}"}
    except OgiltigtOrgnrError as fel:
        return {"tillgangligt": False, "fel": f"Organisationsnumret går inte att använda: {fel}"}

    if engagemang is None:
        return {
            "tillgangligt": True,
            "uppgift": uppgift,
            "finns": False,
            "galler_nu": False,
            "beskrivning": f"Bolaget har aldrig varit registrerat för {uppgift}.",
        }

    return {
        "tillgangligt": True,
        "uppgift": uppgift,
        "finns": True,
        # Uträknad i koden. Se docstringen — modellen ska aldrig behöva
        # jämföra datum för att avgöra det här.
        "galler_nu": engagemang.ar_aktiv(),
        "startdatum": engagemang.startdatum.isoformat() if engagemang.startdatum else None,
        "slutdatum": engagemang.slutdatum.isoformat() if engagemang.slutdatum else None,
        "avslutsorsak": engagemang.avslutsorsak,
        **engagemang.extra,
    }


def get_skatteverket_klient(settings: Settings | None = None) -> SkatteverketEngagemang | None:
    """Klienten, eller None när nycklarna saknas.

    None och inte ett undantag, av samma skäl som `get_send_provider` faller
    tillbaka på `LoggingSendProvider`: en miljö utan Skatteverket-nycklar ska
    starta och fungera, bara utan verifieringen. Onboardingen fortsätter då på
    `orgnr.validera_format` ensam, precis som idag.

    Halvsatt räknas som osatt och loggas — den som satt en av två variabler
    tror sig ha en verifiering och har det inte, vilket är samma fälla som
    SMTP-konfigurationen redan trampat i.
    """
    settings = settings or get_settings()
    client_id = (settings.skatteverket_client_id or "").strip()
    client_secret = (settings.skatteverket_client_secret or "").strip()

    if not (client_id and client_secret):
        if client_id or client_secret:
            logger.warning(
                "Skatteverket-konfigurationen är halvsatt (client_id=%s, "
                "client_secret=%s) — ingen verifiering sker.",
                "satt" if client_id else "saknas",
                "satt" if client_secret else "saknas",
            )
        return None

    return SkatteverketEngagemang(
        bas_url=settings.skatteverket_api_bas_url,
        client_id=client_id,
        client_secret=client_secret,
    )


def paborja_inloggning(*_args: object, **_kwargs: object) -> str:
    """INTE BYGGD. Här hör BankID-inloggningen hemma, och den saknas.

    Skatteverket auktoriserar med OAuth2 Authorization Code Grant, där den
    externa användaren autentiseras med e-legitimation (tjänstebeskrivningen
    2.6). Det betyder ett riktigt redirect-flöde i webbläsaren:

      1. Onboardingen skickar användaren till Skatteverkets authorize-URI.
      2. Användaren legitimerar sig med BankID och godkänner att vår
         programvara får läsa deras beskattningsengagemang.
      3. Skatteverket redirectar tillbaka med en `code`.
      4. Koden växlas mot ett `access_token` på token-URI:n.

    Steg 1 och 3 är sidor i Next-appen, inte i det här API:t, och de finns
    inte. Funktionen står här ändå — som `sources/registry.py`-stubbarna —
    för att nästa person ska möta gränsen här i stället för att bygga ett
    antagande om att backenden kan slå upp ett godtyckligt orgnr på egen hand.

    Den kan den inte. Det finns ingen client_credentials-variant av det här
    API:t: uppslaget görs alltid för en inloggad firmatecknare, eller för ett
    registrerat ombud med organisationscertifikat (en egen ansökan hos
    Skatteverket, inte en kodändring).

    De exakta authorize- och token-URI:erna publiceras under "Säkerhet och
    API:er" på skatteverket.se och delas ut med nycklarna. De är alltså inte
    kända ännu, och att gissa dem hade gett en implementation som ser färdig
    ut och faller vid första riktiga inloggningen.
    """
    raise NotImplementedError(
        "BankID-inloggningen mot Skatteverket är inte byggd. API:t kräver OAuth2 "
        "Authorization Code Grant med e-legitimation — backenden kan inte slå upp "
        "ett orgnr utan en inloggad firmatecknare. Ansök om Partner API-nycklar "
        "hos Skatteverket först; authorize- och token-URI:erna kommer med dem."
    )
