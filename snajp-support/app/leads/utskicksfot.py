"""Den lagstadgade bottenraden i varje kallmejl — byggd i KOD, aldrig av modellen.

## Varför den här filen finns

`send_guard.py` BLOCKERAR ett utskick som saknar avsändaridentifikation
(regel 1), avregistreringslänk (regel 2) eller GDPR art. 14-information vid en
personlig mottagaradress (regel 4). Fram till nu fanns ingen kod som LADE DIT
den informationen. Den enda som kunde skriva den var språkmodellen, i löpande
text, om den råkade komma ihåg det.

Det är fel ansvarsfördelning på exakt samma sätt som INV-SEC-004: det som
avgör om något är lagligt får inte vara en instruktion i en prompt. En modell
som glömmer ett stycke ger inget felmeddelande — den ger ett mejl som ser
komplett ut och saknar det enda som var obligatoriskt.

Här byggs texten i stället av kod, ur data vi redan har, och läggs på efter
att modellen skrivit klart. Modellen kan inte välja bort den, kan inte skriva
om den till något vagare, och kan inte råka formulera "hämtad" som "vi hittade
er" — vilket regel 4 hade fällt.

## Varför den läggs på vid KÖNING och inte vid utskick

Vid köning är brödtexten den text en människa granskar i dashboarden. Läggs
foten på först i sändningsögonblicket granskar granskaren en annan text än den
som skickas, och då är granskningen inte en granskning.

## Vad som INTE står här

Ingenting om Snajp. Utskicket är hyreskundens, avsändaren är hyreskunden, och
en mottagare som vill invända ska nå dem — inte oss. Se send_guard regel 1.
"""

from __future__ import annotations

import re
import secrets

#: Adresser dit den som vill invända ska skriva. Faller tillbaka på
#: avsändarens egen adress om tenanten inte satt en särskild dataskyddsadress.
_FALLBACK_KONTAKT = ""


def ny_token() -> str:
    """32 hexdecimaler ur `secrets`, inte `uuid4` och inte `random`.

    Formatet är ett kontrakt med `ss_avregistreringslankar.token` (text) och
    med Next-routen som löser in den. `secrets` och inte `random` eftersom en
    gissningsbar token låter någon avregistrera någon annan.
    """
    return secrets.token_hex(16)


def avregistreringslank(bas_url: str, token: str) -> str:
    """URL:en som hamnar i mejlet.

    Sökvägen innehåller ordet `avregistrera` med flit: `send_guard`s regel 2
    letar efter just det (eller unsubscribe/optout) i en http-länk. En
    sökväg som hette `/u/<token>` hade varit kortare och blockerad.
    """
    return f"{bas_url.rstrip('/')}/avregistrera/{token}"


def bygg_fot(
    *,
    foretagsnamn: str,
    orgnr: str,
    postadress: str,
    lank: str,
    kontakt_epost: str = "",
    kalla: str = "offentliga företagsuppgifter",
) -> str:
    """Bottenraden. Fyra stycken, i den ordning en mottagare läser dem.

    Formuleringarna är inte fritt valda. `send_guard._ART14_KRAV` letar efter
    fyra saker i texten — vem som är ansvarig, varför, varifrån uppgiften kom
    och rätten att invända — och orden nedan är valda för att träffa de
    nyckelorden OCH gå att läsa av en människa. Ändras en formulering här ska
    testet i tests/leads/test_utskicksfot.py falla; gör det inte det är testet
    trasigt, inte texten.

    `orgnr` och `postadress` skrivs ordagrant. Regel 1 jämför sidfotens text
    mot tenantens sparade värden efter mellanrumsnormalisering — en
    "snyggare" formatering här (mellanslag i organisationsnumret, förkortad
    gatuadress) hade blockerat varje utskick.
    """
    kontakt = (kontakt_epost or _FALLBACK_KONTAKT).strip()
    kontaktrad = f" Du når oss på {kontakt}." if kontakt else ""

    return "\n".join(
        [
            "--",
            f"{foretagsnamn}, org.nr {orgnr}",
            postadress,
            "",
            f"Du får det här mejlet därför att din adress är hämtad ur {kalla} och "
            f"vi bedömer att erbjudandet är relevant för din verksamhet. Ändamålet "
            f"är att ta en första affärskontakt.",
            f"{foretagsnamn} är personuppgiftsansvarig för dina uppgifter. Du har "
            f"rätt att invända mot behandlingen och att få dina uppgifter "
            f"raderade.{kontaktrad}",
            "",
            f"Vill du inte höra av oss igen: {lank}",
        ]
    )


#: Samma mönster som `send_guard._OPT_OUT_MONSTER`. Duplicerat med flit — den
#: här filen ska kunna svara "finns foten redan?" utan att importera guarden
#: och därmed knyta ihop den som DÖMER med den som SKRIVER. Faller mönstren
#: isär fångas det av tests/leads/test_utskicksfot.py, som kör guarden på det
#: den här filen producerar.
_HAR_LANK = re.compile(r"https?://\S*(avregistrera|avanmal|unsubscribe|optout|opt-out)\S*", re.I)


def har_fot(brodtext: str) -> bool:
    """Om brödtexten redan bär en avregistreringslänk.

    Grunden för idempotens: en uppföljning som byggts ur ett tidigare mejl kan
    redan ha foten, och två sidfötter är värre än en. Kontrollen görs på
    LÄNKEN och inte på hela texten, eftersom länken är det enda som är unikt
    för foten — resten är prosa som en modell kan ha skrivit av sig själv.
    """
    return bool(_HAR_LANK.search(brodtext or ""))


def med_fot(brodtext: str, *, fot: str) -> str:
    """Lägger på foten om den saknas. Idempotent."""
    if har_fot(brodtext):
        return brodtext
    return f"{brodtext.rstrip()}\n\n{fot}"
