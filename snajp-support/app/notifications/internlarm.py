"""Larm till snajpsupport@gmail.com när något behöver en människa.

## Varför en egen väg och inte `send_provider`

`app/leads/send_provider.py` är kundvänd: den skickar från tenantens
avsändare, lyder `send_guard`, bär art. 14-sidfot och avregistreringslänk,
och kan i dag ändå bara logga eftersom per-tenant-SMTP inte finns modellerat.
Ett internlarm har ingen av de egenskaperna och ska inte ärva någon av dem.
Det går från ETT konto, till OSS, om att ett ärende behöver en människa.

## Vad som ALDRIG får hända

Larmet får inte fälla eller fördröja det som larmas om. Ett ärende som
eskalerar är redan ett ärende där något gått fel för kunden; att svaret också
uteblir för att Gmail hade en dålig dag vore att göra ett problem till två.
Därför:

  - varje undantag fångas och loggas, inget kastas vidare,
  - SMTP körs i en tråd (`smtplib` är blockerande — anropas den rakt av i en
    async-request stannar hela event-loopen så länge Gmail funderar),
  - och tråden har ett tak (`_TIDSTAK`). Ett larm som inte gått fram på tio
    sekunder är ett larm som får vara ogjort.

`larma()` returnerar en bool i stället för att kasta: `True` = mejlet gick
iväg, `False` = det gjorde det inte (osatt konfiguration, dubblett, eller
fel). Anroparen får ignorera värdet; testerna gör det inte.

## Vad som INTE står i mejlet

Kundens meddelandetext. Larmet bär tenant, vad som eskalerade, varför, och en
LÄNK in i adminvyn — inte ärendets innehåll. Det är dels vad som efterfrågades,
dels det som gör att larmet inte blir ännu en kopia av personuppgifter i en
Gmail-brevlåda. Den som ska agera loggar in och läser ärendet där åtkomsten
redan är reglerad. Se `docs/JURIDIK_ATGARDER.md`.

## Konfiguration — SÄTTS AV EN MÄNNISKA, i Railway

    INTERNLARM_SMTP_ANVANDARE=snajpsupport@gmail.com
    INTERNLARM_SMTP_LOSENORD=<app-lösenord, 16 tecken>

Lösenordet är INTE kontolösenordet. Ett Gmail-konto med tvåstegsverifiering
kan inte logga in på SMTP med kontolösenordet — det kräver ett
app-specifikt lösenord, som skapas under Google-kontots säkerhetsinställningar
("Appspecifika lösenord") efter att tvåstegsverifiering slagits på. Samma
klass av åtgärd som `OPENAI_API_KEY` i `docs/JURIDIK_ATGARDER.md`: konto och
lösenord är undantaget i CLAUDE.md, alltså Antons hand och inte agentens.

Saknas variablerna larmar modulen ingenting och loggar en rad. Det är rätt
utfall lokalt och i testsviten — men det betyder också att ett bortglömt steg
är TYST. `har_konfiguration()` finns för att kunna se det utan att skicka.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
import time
from dataclasses import dataclass
from email.message import EmailMessage

from ..config import get_settings

logger = logging.getLogger("snajp-support.internlarm")

#: Mottagaren. Ett internt larm har en adress, inte en adressbok.
MOTTAGARE = "snajpsupport@gmail.com"

SMTP_VARD = "smtp.gmail.com"
SMTP_PORT = 587

#: Prefixet i ämnesraden. Filter och regler i brevlådan hänger på det, så det
#: är ett kontrakt: ändras det slutar någons inkorgsregel att träffa.
PRIORITETSMARKOR = "[PRIORITERAT]"

#: Tak för hela sändningen. Se modulens docstring — ett larm som tar längre tid
#: än så kostar mer än det smakar.
_TIDSTAK_SEKUNDER = 10.0

#: Hur länge samma händelsenyckel hålls tyst. Se `_ar_dubblett`.
_DUBBLETTFONSTER_SEKUNDER = 6 * 60 * 60

#: Sedda händelsenycklar -> när de sågs.
#:
#: PROCESSLOKALT, och det är en känd begränsning: två Railway-repliker har var
#: sitt minne, och en omstart glömmer allt. Följden är i värsta fall ETT extra
#: mejl, aldrig ett uteblivet — vilket är rätt håll att falla för ett larm.
#:
#: Alternativet vore en tabell och en migration för att undvika ett
#: dubbelmejl. De ställen där dubbletter faktiskt skulle bli MÅNGA (support och
#: bokföringsperioden) dedupliceras dessutom mot databasen av anroparen; det
#: här är andra linjen, inte den enda.
_SEDDA: dict[str, float] = {}


@dataclass(frozen=True)
class Larm:
    """Ett larm, färdigt att formulera.

    `lank` är avsiktligt ett eget fält och inte inbakat i `varfor`: den som
    öppnar mejlet i telefonen ska hitta vägen in utan att läsa brödtexten.
    """

    rubrik: str
    tenant_id: str
    vad: str
    varfor: str
    lank: str = ""

    def amne(self) -> str:
        return f"{PRIORITETSMARKOR} {self.rubrik}"

    def brodtext(self) -> str:
        rader = [
            f"Tenant:  {self.tenant_id or '(okänd)'}",
            f"Vad:     {self.vad}",
            f"Varför:  {self.varfor}",
        ]
        if self.lank:
            rader.append("")
            rader.append(f"Öppna ärendet: {self.lank}")
        rader.append("")
        rader.append(
            "Det här är ett internt larm från Snajp. Ärendets innehåll står "
            "inte här — logga in och läs det i adminvyn."
        )
        return "\n".join(rader)


def _konfiguration() -> tuple[str, str] | None:
    """Användarnamn och lösenord, eller None om larmvägen inte är uppsatt.

    Läses via `Settings` och inte med `os.getenv`. Skillnaden är inte
    kosmetisk: pydantic-settings läser `snajp-support/.env` utan att exportera
    något till `os.environ`, så en direktläsning hade sett värdena i Railway
    men aldrig lokalt — och den sortens skillnad upptäcks först när någon
    undrar varför larmet är tyst på den ena maskinen.

    Halvsatt räknas som osatt. En användare utan lösenord är inte halvt
    konfigurerad, den är ett inloggningsförsök som Google avvisar.
    """
    settings = get_settings()
    anvandare = (settings.internlarm_smtp_anvandare or "").strip()
    losenord = (settings.internlarm_smtp_losenord or "").strip()
    if not anvandare or not losenord:
        return None
    return anvandare, losenord


def har_konfiguration() -> bool:
    """Om larmvägen är uppsatt. Läser inga värden ut, bara om de finns.

    Finns för hälsokontroller och för att en människa ska kunna se att steget
    i Railway är gjort — utan att skicka ett provmejl och utan att någon
    hemlighet kan hamna i en logg.
    """
    return _konfiguration() is not None


def _ar_dubblett(nyckel: str) -> bool:
    """Har vi redan larmat om exakt det här, nyligen?

    Gallrar samtidigt bort utgångna poster, så att dicten inte växer i en
    långlivad process.
    """
    nu = time.monotonic()
    for gammal, sedd in list(_SEDDA.items()):
        if nu - sedd > _DUBBLETTFONSTER_SEKUNDER:
            del _SEDDA[gammal]

    if nyckel in _SEDDA:
        return True
    _SEDDA[nyckel] = nu
    return False


def nollstall_dubblettminne() -> None:
    """Bara för tester. Utan den läcker en testfil sitt tillstånd in i nästa."""
    _SEDDA.clear()


def _skicka_blockerande(larm: Larm, anvandare: str, losenord: str) -> None:
    """Den faktiska SMTP-sessionen. Körs i en tråd, aldrig på event-loopen."""
    meddelande = EmailMessage()
    meddelande["Subject"] = larm.amne()
    meddelande["From"] = anvandare
    meddelande["To"] = MOTTAGARE
    meddelande.set_content(larm.brodtext())

    with smtplib.SMTP(SMTP_VARD, SMTP_PORT, timeout=_TIDSTAK_SEKUNDER) as server:
        server.starttls()
        server.login(anvandare, losenord)
        server.send_message(meddelande)


async def larma(
    rubrik: str,
    *,
    tenant_id: str,
    vad: str,
    varfor: str,
    lank: str = "",
    nyckel: str,
) -> bool:
    """Skicka ett internlarm. Kastar aldrig.

    Args:
        rubrik: Kort beskrivning, hamnar efter `[PRIORITERAT]` i ämnesraden.
        tenant_id: Vilken kund det gäller.
        vad: Vad som eskalerade, i en mening.
        varfor: Varför det eskalerade.
        lank: Direktlänk in i adminvyn. Tom om ingen vy finns att peka på.
        nyckel: Händelsens identitet. Två larm med samma nyckel inom
            `_DUBBLETTFONSTER_SEKUNDER` skickas EN gång. Nyckeln ska därför
            beskriva HÄNDELSEN (ärendet, tråden, perioden) och inte
            meddelandet — annars larmar varje replik i ett redan eskalerat
            ärende på nytt.

    Returns:
        True om mejlet gick iväg. False vid osatt konfiguration, dubblett
        eller fel — alla tre är samma sak för anroparen: fortsätt.
    """
    konfiguration = _konfiguration()
    if konfiguration is None:
        logger.info(
            "Internlarm hoppades över (INTERNLARM_SMTP_* inte satt): %s — %s", rubrik, vad
        )
        return False

    if _ar_dubblett(nyckel):
        logger.info("Internlarm redan skickat för %s, skickar inte igen.", nyckel)
        return False

    larm = Larm(rubrik=rubrik, tenant_id=tenant_id, vad=vad, varfor=varfor, lank=lank)
    anvandare, losenord = konfiguration
    try:
        await asyncio.wait_for(
            asyncio.to_thread(_skicka_blockerande, larm, anvandare, losenord),
            timeout=_TIDSTAK_SEKUNDER,
        )
    except Exception as fel:  # noqa: BLE001 — hela poängen: larmet får inte fälla ärendet
        # Nyckeln plockas bort igen. Misslyckas sändningen ska nästa försök få
        # gå fram — annars gör dubblettspärren ett tillfälligt fel permanent.
        _SEDDA.pop(nyckel, None)
        logger.warning("Internlarm kunde inte skickas (%s): %s — %s", type(fel).__name__, rubrik, fel)
        return False

    logger.info("Internlarm skickat: %s", larm.amne())
    return True


def arendelank(bas_url: str, ticket_id: str) -> str:
    """Direktlänken in i adminvyn för ett ärende.

    Tom bas-URL ger tom länk, inte en trasig relativ adress: en länk som inte
    går någonstans är sämre än ingen länk, eftersom den ser ut att fungera.
    Bas-URL:en är `Settings.publik_bas_url` (`PUBLIC_BASE_URL`), samma som
    avregistreringslänken använder — den pekar på Next-appen, som är den som
    renderar adminvyn.
    """
    bas = (bas_url or "").strip().rstrip("/")
    if not bas or not ticket_id:
        return ""
    return f"{bas}/admin/kunder?arende={ticket_id}"


__all__ = [
    "Larm",
    "MOTTAGARE",
    "PRIORITETSMARKOR",
    "arendelank",
    "har_konfiguration",
    "larma",
    "nollstall_dubblettminne",
]
