"""Mejlkonton Kvittohanteraren kan läsa — och ingenting den kan skriva.

## Läsning, aldrig skrivning

Alla tre kopplingarna är READ-ONLY av konstruktion: Gmail begärs med scope
`gmail.readonly`, Graph med `Mail.Read`, och mocken har inga skrivmetoder.
Det finns ingen kodväg som markerar, flyttar eller besvarar ett mejl —
agenten läser, plockar ut kvittofälten och släpper mejlet.

## Var tokens bor

Samma mönster som IMAP-kopplingen i `email_pipeline/connectors/imap.py`:
refresh-token + klientuppgifter i miljön (per deployment), aldrig i
databasen, och inga access-tokens sparas någonstans — de hämtas färska per
skanning och lever i minnet under anropet. Samtycket fångas med
`scripts/kvitto_oauth.py`, som skriver ut konsent-URL:en och tar emot
refresh-token — vi kopplar åt kunden, precis som Inkorgar-inställningen
beskriver för supportens IMAP.

## Mocken är en riktig kopplingstyp, inte ett testfusk

Demon och den lokala stacken kör `KVITTO_MEJL_LEVERANTOR=mock`: en fast
inkorg med påhittade men realistiska mejl (kvitton, en dubblett, ett
nyhetsbrev, ett vanligt mejl) så att hela flödet går att köra och visa utan
att någon kopplar sin riktiga mejl. Fixturerna är märkta som påhittade och
följer samma regel som lib/demo-filerna i Next-appen: inga riktiga bolag,
inga siffror som ser ut att komma ur en körning.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Protocol

import httpx

from ..config import get_settings


@dataclass(frozen=True)
class Mejl:
    """Ett inkommande mejl, reducerat till det skanningen behöver."""

    id: str
    avsandare: str
    avsandaradress: str
    amne: str
    #: ÅÅÅÅ-MM-DD — mottagningsdagen, fallback när kvittot saknar eget datum.
    datum: str
    text: str


class Mejlkonto(Protocol):
    """En läsbar inkorg. `leverantor` och `adress` visas i gränssnittet."""

    leverantor: str
    adress: str

    async def hamta_mejl(self, *, max_antal: int = 50) -> list[Mejl]: ...


class MejlkontofelError(RuntimeError):
    """Kopplingen gick inte att använda (token, nät, scope). Meningen är
    skriven för kunden och får visas rakt av."""


# -- Mocken -----------------------------------------------------------------

#: Den påhittade inkorgen. Bolagen finns inte, beloppen är hittepå, och
#: tests/test_kvitton_tolkning.py räknar om varje siffra som sammanfattningen
#: sedan påstår. Ändras ett belopp här ska testet ändras i samma commit.
FEJKMEJL: tuple[Mejl, ...] = (
    Mejl(
        id="mock-001",
        avsandare="Nordvik Drivmedel AB",
        avsandaradress="kvitto@nordvikdrivmedel.example",
        amne="Kvitto från Nordvik Drivmedel",
        datum="2026-09-02",
        text=(
            "Tack för ditt köp!\n"
            "Station 214, Västerås\n"
            "Diesel 41,2 l\n"
            "Totalt: 623,50 kr\n"
            "Varav moms 25 %: 124,70 kr\n"
            "Betalt med kort ****1274\n"
            "Datum: 2026-09-02 07:41"
        ),
    ),
    Mejl(
        id="mock-002",
        avsandare="Bistro Linnea",
        avsandaradress="kassa@bistrolinnea.example",
        amne="Ditt kvitto från Bistro Linnea",
        datum="2026-09-04",
        text=(
            "Bistro Linnea, Uppsala\n"
            "Lunch 2 personer\n"
            "Dagens fisk 2 x 185,00\n"
            "Mineralvatten 2 x 58,00\n"
            "Totalt: 486,00 kr\n"
            "Varav moms 12 %: 52,07 kr\n"
            "Betalt med kort ****1274\n"
            "Datum: 2026-09-04 12:18"
        ),
    ),
    Mejl(
        id="mock-003",
        avsandare="Skrivbo Kontorsvaror AB",
        avsandaradress="order@skrivbo.example",
        amne="Kvitto och orderbekräftelse #48213",
        datum="2026-09-05",
        text=(
            "Tack för din order!\n"
            "Kopieringspapper A4, 5 paket\n"
            "Pärmar, 10 st\n"
            "Tonerkassett HP 207X\n"
            "Totalt: 1 245,00 kr\n"
            "Varav moms 25 %: 249,00 kr\n"
            "Betalt med kort\n"
            "Orderdatum: 2026-09-05"
        ),
    ),
    Mejl(
        id="mock-004",
        avsandare="Figmara Inc.",
        avsandaradress="receipts@figmara.example",
        amne="Your Figmara receipt",
        datum="2026-09-08",
        text=(
            "Receipt for Figmara Professional, September 2026.\n"
            "1 editor seat.\n"
            "Total: $45.00 USD\n"
            "Paid with card ending 1274.\n"
            "Date: 2026-09-08"
        ),
    ),
    Mejl(
        id="mock-005",
        avsandare="Taxi Mälardalen",
        avsandaradress="kvitto@taximalardalen.example",
        amne="Kvitto på din resa",
        datum="2026-09-09",
        text=(
            "Tack för att du åkte med oss!\n"
            "Resa: Arlanda – Stockholm City\n"
            "Totalt: 289,00 kr\n"
            "Varav moms 6 %: 16,36 kr\n"
            "Betalt med kort\n"
            "Datum: 2026-09-09 16:52"
        ),
    ),
    Mejl(
        id="mock-006",
        avsandare="Svenska Tåglinjer AB",
        avsandaradress="biljett@svensktag.example",
        amne="Kvitto — din biljett Stockholm–Göteborg",
        datum="2026-09-10",
        text=(
            "Din biljett är klar.\n"
            "Stockholm C – Göteborg C, 2 kl\n"
            "Totalt: 745,00 kr\n"
            "Varav moms 6 %: 42,17 kr\n"
            "Betalt med kort\n"
            "Datum: 2026-09-10"
        ),
    ),
    Mejl(
        id="mock-007",
        avsandare="Molnlagring Norr AB",
        avsandaradress="faktura@molnlagringnorr.example",
        amne="Kvitto på din prenumeration, september",
        datum="2026-09-11",
        text=(
            "Molnlagring Bas, 1 månad.\n"
            "Totalt: 199,00 kr\n"
            "Varav moms 25 %: 39,80 kr\n"
            "Betalt via kort, automatisk förnyelse\n"
            "Datum: 2026-09-11"
        ),
    ),
    Mejl(
        id="mock-008",
        avsandare="Stadshotellet Örebro",
        avsandaradress="reception@stadshotelletorebro.example",
        amne="Kvitto för din vistelse",
        datum="2026-09-12",
        text=(
            "Tack för din vistelse!\n"
            "Enkelrum, 1 natt inkl. frukost\n"
            "Totalt: 1 890,00 kr\n"
            "Varav moms 12 %: 202,50 kr\n"
            "Betalt med kort ****1274\n"
            "Utcheckning: 2026-09-12"
        ),
    ),
    Mejl(
        id="mock-009",
        avsandare="Parkera Nu AB",
        avsandaradress="kvitto@parkeranu.example",
        amne="Kvitto parkering, zon 314",
        datum="2026-09-13",
        text=(
            "Din parkering i zon 314 avslutades 2026-09-13 17:05.\n"
            "Beloppet dras via ditt betalkort och visas i appen."
        ),
    ),
    Mejl(
        id="mock-010",
        avsandare="Verktygsboden Nord AB",
        avsandaradress="kassa@verktygsbodennord.example",
        amne="Kvitto på ditt köp",
        datum="2026-09-15",
        text=(
            "Tack för ditt köp!\n"
            "Sladdlös borrmaskin 18V\n"
            "Bitssats 32 delar\n"
            "Totalt: 2 340,00 kr\n"
            "Varav moms 25 %: 468,00 kr\n"
            "Betalt med kort\n"
            "Datum: 2026-09-15 10:22"
        ),
    ),
    # Samma köp som mock-003, skickat igen — dubblettkontrollens demofall.
    Mejl(
        id="mock-011",
        avsandare="Skrivbo Kontorsvaror AB",
        avsandaradress="order@skrivbo.example",
        amne="Kvitto #48213 (kopia)",
        datum="2026-09-06",
        text=(
            "Här kommer ditt kvitto igen, som önskat.\n"
            "Kopieringspapper A4, 5 paket\n"
            "Pärmar, 10 st\n"
            "Tonerkassett HP 207X\n"
            "Totalt: 1 245,00 kr\n"
            "Varav moms 25 %: 249,00 kr\n"
            "Betalt med kort\n"
            "Orderdatum: 2026-09-05"
        ),
    ),
    # Inte kvitton — skanningen ska lämna dem orörda.
    Mejl(
        id="mock-012",
        avsandare="Branschnytt",
        avsandaradress="red@branschnytt.example",
        amne="Nyhetsbrev v.37: tre trender i höst",
        datum="2026-09-08",
        text=(
            "Veckans nyhetsbrev: tre trender vi ser i branschen i höst, "
            "och en intervju. Trevlig läsning!"
        ),
    ),
    Mejl(
        id="mock-013",
        avsandare="Anna Lindqvist",
        avsandaradress="anna.lindqvist@example.se",
        amne="Möte på torsdag?",
        datum="2026-09-14",
        text="Hej! Passar torsdag kl 10 för en avstämning? Hälsn. Anna",
    ),
)


class MockMejlkonto:
    """Den fasta demoinkorgen. Se modulens docstring."""

    leverantor = "mock"
    adress = "demo@snajp.example"

    async def hamta_mejl(self, *, max_antal: int = 50) -> list[Mejl]:
        return list(FEJKMEJL[:max_antal])


# -- Gmail (Google API, read-only) ------------------------------------------


async def _gmail_access_token(client: httpx.AsyncClient) -> str:
    settings = get_settings()
    svar = await client.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": settings.kvitto_oauth_client_id,
            "client_secret": settings.kvitto_oauth_client_secret,
            "refresh_token": settings.kvitto_oauth_refresh_token,
            "grant_type": "refresh_token",
        },
    )
    token = svar.json().get("access_token") if svar.status_code == 200 else None
    if not token:
        raise MejlkontofelError(
            "Gmail-kopplingen kunde inte förnyas. Koppla om kontot, eller "
            "kontakta oss så gör vi det åt dig."
        )
    return str(token)


def _gmail_text(payload: dict) -> str:
    """text/plain-delen ur Gmails MIME-träd, med html-delen som reserv."""

    def leta(del_: dict, mime: str) -> str:
        if del_.get("mimeType") == mime and del_.get("body", {}).get("data"):
            data = del_["body"]["data"]
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", "replace")
        for barn in del_.get("parts", []) or []:
            träff = leta(barn, mime)
            if träff:
                return träff
        return ""

    return leta(payload, "text/plain") or leta(payload, "text/html")


def _gmail_datum(internal_date: object) -> str:
    try:
        from datetime import UTC, datetime

        return datetime.fromtimestamp(int(str(internal_date)) / 1000, tz=UTC).date().isoformat()
    except (TypeError, ValueError):
        return ""


class GmailKonto:
    """Gmail via Gmail API. Scope: gmail.readonly — begärt i kvitto_oauth.py."""

    leverantor = "gmail"

    def __init__(self, adress: str) -> None:
        self.adress = adress

    async def hamta_mejl(self, *, max_antal: int = 50) -> list[Mejl]:
        async with httpx.AsyncClient(timeout=30) as client:
            token = await _gmail_access_token(client)
            huvud = {"Authorization": f"Bearer {token}"}
            lista = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                params={"maxResults": max_antal, "q": "in:inbox"},
                headers=huvud,
            )
            if lista.status_code != 200:
                raise MejlkontofelError(
                    "Gmail svarade inte på hämtningen. Prova igen om en stund."
                )
            mejl: list[Mejl] = []
            for post in lista.json().get("messages", []) or []:
                detalj = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{post['id']}",
                    params={"format": "full"},
                    headers=huvud,
                )
                if detalj.status_code != 200:
                    continue
                kropp = detalj.json()
                headers = {
                    h["name"].lower(): h["value"]
                    for h in kropp.get("payload", {}).get("headers", [])
                }
                fran = headers.get("from", "")
                namn, _, adress = fran.rpartition("<")
                mejl.append(
                    Mejl(
                        id=str(kropp.get("id")),
                        avsandare=(namn or fran).strip().strip('"'),
                        avsandaradress=adress.rstrip(">").strip() or fran.strip(),
                        amne=headers.get("subject", ""),
                        # internalDate (ms sedan epok), inte Date-huvudet: det
                        # senare är RFC 2822 ("Tue, 02 Sep 2026 …") och gav
                        # "Tue, 02 Se" som datum.
                        datum=_gmail_datum(kropp.get("internalDate")),
                        text=_gmail_text(kropp.get("payload", {})),
                    )
                )
            return mejl


# -- Outlook/Hotmail (Microsoft Graph, read-only) ---------------------------


class GraphKonto:
    """Outlook och Hotmail via Microsoft Graph. Scope: Mail.Read."""

    leverantor = "microsoft"

    def __init__(self, adress: str) -> None:
        self.adress = adress

    async def hamta_mejl(self, *, max_antal: int = 50) -> list[Mejl]:
        settings = get_settings()
        async with httpx.AsyncClient(timeout=30) as client:
            svar = await client.post(
                "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                data={
                    "client_id": settings.kvitto_oauth_client_id,
                    "client_secret": settings.kvitto_oauth_client_secret,
                    "refresh_token": settings.kvitto_oauth_refresh_token,
                    "grant_type": "refresh_token",
                    "scope": "https://graph.microsoft.com/Mail.Read offline_access",
                },
            )
            token = svar.json().get("access_token") if svar.status_code == 200 else None
            if not token:
                raise MejlkontofelError(
                    "Microsoft-kopplingen kunde inte förnyas. Koppla om kontot, "
                    "eller kontakta oss så gör vi det åt dig."
                )
            # Inkorgen, inte /me/messages: den senare läser ALLA mappar, och
            # skickade kundfakturor i Skickat hade lästs in som utlägg.
            # ImmutableId: annars byter ett mejl id när det flyttas, och
            # fingeravtrycket hade släppt igenom det som ett nytt kvitto.
            lista = await client.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages",
                params={
                    "$top": max_antal,
                    "$select": "id,subject,from,receivedDateTime,body",
                    "$orderby": "receivedDateTime desc",
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "Prefer": 'IdType="ImmutableId"',
                },
            )
            if lista.status_code != 200:
                raise MejlkontofelError(
                    "Microsoft Graph svarade inte på hämtningen. Prova igen om en stund."
                )
            mejl: list[Mejl] = []
            for post in lista.json().get("value", []) or []:
                fran = (post.get("from") or {}).get("emailAddress") or {}
                mejl.append(
                    Mejl(
                        id=str(post.get("id")),
                        avsandare=str(fran.get("name") or fran.get("address") or ""),
                        avsandaradress=str(fran.get("address") or ""),
                        amne=str(post.get("subject") or ""),
                        datum=str(post.get("receivedDateTime") or "")[:10],
                        text=str((post.get("body") or {}).get("content") or ""),
                    )
                )
            return mejl


# -- Valet ------------------------------------------------------------------


def valj_mejlkonto(tenant_id: str) -> Mejlkonto | None:
    """Kontot miljön pekar ut FÖR DEN HÄR TENANTEN, eller None (= inget kopplat).

    None är ett SVAR och inte ett fel: gränssnittet visar då kopplingsvyn i
    stället för en skanningsknapp.

    ## Varför tenanten är ett argument och inte valfri

    Kopplingen konfigureras per deployment, men en inkorg tillhör en kund.
    Utan kontrollen nedan hade VARJE tenant i miljön fått samma Gmail-konto
    — alltså en kunds kvittomejl i en annan kunds kvittolista. Riktiga
    leverantörer är därför fail-closed: utan `KVITTO_MEJL_TENANT` finns ingen
    koppling alls. Mocken bär bara påhittade mejl och får gälla alla när
    fältet är tomt (demo, lokal stack, testresor).
    """
    settings = get_settings()
    leverantor = (settings.kvitto_mejl_leverantor or "").strip().lower()
    agare = (settings.kvitto_mejl_tenant or "").strip()
    if agare and str(tenant_id) != agare:
        return None
    if leverantor == "mock":
        # Mocken skriver påhittade kvitton MED verifikat i tenantens bok. I en
        # miljö med riktig kunddata (main, och development som speglar den)
        # får den därför bara gälla en utpekad tenant — annars hade varje
        # kund som tryckte "Skanna" fått elva hittepåkvitton i sin period.
        if not agare and settings.har_riktig_kunddata():
            return None
        return MockMejlkonto()
    if not agare:
        return None
    if leverantor == "gmail":
        return GmailKonto(settings.kvitto_mejl_adress or "gmail-konto")
    if leverantor in ("microsoft", "outlook", "hotmail"):
        return GraphKonto(settings.kvitto_mejl_adress or "outlook-konto")
    return None
