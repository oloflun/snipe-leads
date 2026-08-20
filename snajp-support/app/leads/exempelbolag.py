"""Exempelbolag: påhittade företag som passar kundens ICP.

## Varför de finns

`POST /api/leads/runs/batch` svarar 422 med "Inga prospekt att köra på" när
tenanten är tom. Det är korrekt men obrukbart som svar på en knapp som heter
*Starta körning*: en ny kund har per definition noll prospekt, och den enda
vägen framåt var att lägga in bolag för hand innan de sett agenten göra
någonting. Det är fel ordning — man vill se produkten arbeta innan man matar
den.

Exempelbolagen är därför en väg IN i produkten, inte en produkt i sig.

## Varför de genereras utan LLM

Modulen är ren och deterministisk. Två skäl, båda praktiska:

 1. Leads-ytorna kräver annars en riktig nyckel (`_require_live_llm`), och i
    simuleringsläge — vilket dev ofta står i — hade knappen svarat 503. En
    demonstrationsfunktion som bara fungerar när allt annat redan fungerar
    demonstrerar ingenting.
 2. Ett påhittat bolagsnamn ur en språkmodell kan råka vara ett RIKTIGT bolag.
    Namnen här byggs av ett ledord ur branschen plus ett suffix ur en fast
    lista, och märks dessutom `origin='example'` i databasen.

## Varför de aldrig kan mejlas

Raden får `origin = 'example'` (migration 039) och saknar mottagaradress.
`scheduler._kor_send_guard` slår upp origin och blockerar innan provider.send()
— alltså på samma ställe som de sex spärrarna, inte i UI:t. Ett exempelbolag
som mejlas är ett mejl till en adress som inte finns, i bästa fall; i värsta
fall till ett riktigt bolag med samma namn.
"""

from __future__ import annotations

import hashlib
from typing import Any

#: Namndelar. Sammansättningarna ska låta som svenska bolag men inte träffa
#: ett verkligt: därför ett neutralt ortsled + ett branschled + bolagsform.
_LED = (
    "Nord",
    "Väst",
    "Syd",
    "Öst",
    "Bergs",
    "Sjö",
    "Ek",
    "Lund",
    "Vik",
    "Hammar",
    "Alm",
    "Gran",
)

_EFTERLED = ("vik", "berg", "strand", "haga", "backe", "näs", "lid", "sund")

_BOLAGSFORM = ("AB", "Gruppen AB", "& Partner AB", "Sverige AB")

#: Fallback när ICP:t inte säger något om bransch. Medvetet breda svenska
#: SMB-branscher — det är den kundtyp produkten säljs till.
_DEFAULT_BRANSCHER = ("Bygg", "Tillverkning", "Logistik", "Fastighet", "Installation")

_DEFAULT_ROLLER = ("VD", "Inköpschef", "Platschef", "Marknadschef")


def _tal(fro: str, mod: int) -> int:
    """Deterministiskt heltal ur en sträng. Samma ICP ger samma lista igen."""
    return int(hashlib.sha256(fro.encode("utf-8")).hexdigest()[:8], 16) % mod


def _forsta(varde: Any, fallback: tuple[str, ...], index: int) -> str:
    if isinstance(varde, list) and varde:
        return str(varde[index % len(varde)]).strip() or fallback[index % len(fallback)]
    return fallback[index % len(fallback)]


#: Signaler ett bolag kan bära. De är det agenten letar efter på riktigt —
#: nyöppning, rekrytering, ändrad tjänstesida — och exemplen ska visa formen.
_SIGNALER = (
    "har utökat med en andra anläggning i år",
    "rekryterar till produktionen — tre annonser ute",
    "har lagt om sin tjänstesida och lyfter fram service",
    "har bytt affärssystem och skriver om det på sin blogg",
    "har flyttat till större lokal",
    "söker en ny {roll} sedan i våras",
)

#: Ortsfallback när ICP:t inte säger något. Städer, inte "Sverige": ett kort
#: som säger "Sverige" under ortsrubriken ser ut som ett fält som inte fylldes i.
_DEFAULT_ORTER = ("Göteborg", "Malmö", "Jönköping", "Västerås", "Örebro", "Umeå")


def _falskt_orgnr(fro: str) -> str:
    """Ett organisationsnummer som SER rätt ut men aldrig kan vara någons.

    556 är aktiebolagens serie, så formen är trovärdig i en kolumn. Men
    kontrollsiffran är MEDVETET fel: ett nummer som klarar Luhn kan vara ett
    verkligt bolags, och då är exempelbolaget inte längre påhittat — det är ett
    riktigt företag med påhittad information om sig.

    Samma resonemang som `lib/tenants/testkund.ts`, som bär `000000-0000` av
    exakt det skälet. `lib/orgnr.ts` och `app/leads/orgnr.py` avvisar båda det
    här numret, vilket är avsikten: skulle det någonsin läcka in i ett riktigt
    flöde faller det på formatvalideringen i stället för att accepteras.
    """
    mitten = f"{_tal(fro + 'org', 1000000):06d}"
    siffror = f"556{mitten[:3]}{mitten[3:]}"  # nio siffror
    korrekt = _luhn_kontrollsiffra(siffror)
    # +5 mod 10: garanterat en annan siffra än den korrekta, alltså ogiltigt.
    return f"{siffror[:6]}-{siffror[6:]}{(korrekt + 5) % 10}"


def _luhn_kontrollsiffra(siffror: str) -> int:
    summa = 0
    for index, tecken in enumerate(reversed(siffror)):
        varde = int(tecken)
        if index % 2 == 0:
            varde *= 2
            if varde > 9:
                varde -= 9
        summa += varde
    return (10 - summa % 10) % 10


def _webbplats(namn: str) -> str:
    """`.example` är reserverad (RFC 2606) och kan aldrig registreras.

    En `.se`-adress hade kunnat tillhöra någon. Domänen syns i vyn och kan
    klickas av misstag — då ska den leda ingenstans, inte till ett företag som
    undrar varför de står i vår produkt.
    """
    stam = "".join(
        tecken
        for tecken in namn.lower().replace("å", "a").replace("ä", "a").replace("ö", "o")
        if tecken.isalnum()
    )
    return f"{stam[:24]}.example"


def bygg_exempelbolag(icp: dict[str, Any] | None, *, antal: int) -> list[dict[str, Any]]:
    """Bygger `antal` exempelbolag som ligger inom ICP:t.

    Varje bolag bär samma fält som ett RIKTIGT prospekt gör efter research —
    org.nr, ort, webbplats, antal anställda, bransch, en signal och en
    motivering. Skälet är inte kosmetiskt: vyn som listar dem är samma vy som
    listar riktiga prospekt, och ett exempelbolag med bara ett namn ser ut som
    ett prospekt vars research misslyckats.

    Två fält är avsiktligt omöjliga att förväxla med verkligheten:
    organisationsnumret har fel kontrollsiffra och domänen ligger under
    `.example`. Se `_falskt_orgnr` och `_webbplats`.
    """
    icp = icp or {}
    branscher = icp.get("industries") or list(_DEFAULT_BRANSCHER)
    geografi = icp.get("geography") or []
    roller = icp.get("roles") or list(_DEFAULT_ROLLER)
    storlek = icp.get("company_size") or {}
    min_anst = storlek.get("min")
    max_anst = storlek.get("max")

    bolag: list[dict[str, Any]] = []
    for i in range(max(antal, 0)):
        bransch = _forsta(branscher, _DEFAULT_BRANSCHER, i)
        roll = _forsta(roller, _DEFAULT_ROLLER, i)
        # Ortsfältet ska bära en ORT. Saknas geografi i ICP:t väljs en svensk
        # stad — "Sverige" i en ortskolumn läser sig som ett tomt fält.
        ort = _forsta(geografi, _DEFAULT_ORTER, i)

        fro = f"{bransch}|{ort}|{i}"
        namn = (
            f"{_LED[_tal(fro + 'a', len(_LED))]}"
            f"{_EFTERLED[_tal(fro + 'b', len(_EFTERLED))]} "
            f"{bransch.split()[0].capitalize()} "
            f"{_BOLAGSFORM[_tal(fro + 'c', len(_BOLAGSFORM))]}"
        )

        # Storleken hålls inom ICP:t när det anger ett spann. Utan spann används
        # EU:s småföretagsdefinition, samma default som ICP-profilerna förifyller.
        lo = min_anst if min_anst is not None else 8
        hi = max_anst if max_anst is not None else 49
        if hi < lo:
            hi = lo
        anstallda = lo + _tal(fro + "n", max(hi - lo + 1, 1))

        signal = _SIGNALER[_tal(fro + "s", len(_SIGNALER))].format(roll=roll.lower())

        storleksrad = ""
        if min_anst is not None or max_anst is not None:
            storleksrad = f", {min_anst or 1}–{max_anst or 49} anställda"

        bolag.append(
            {
                "company_name": namn,
                "contact_name": roll,
                "orgnr": _falskt_orgnr(fro),
                "ort": ort,
                "website": _webbplats(namn),
                "anstallda": anstallda,
                "bransch": bransch,
                "signal": signal.capitalize() + ".",
                "beskrivning": (
                    f"{bransch.capitalize()} i {ort} med {anstallda} anställda. {signal.capitalize()}."
                ),
                "motivering": (
                    f"Exempelbolag: {bransch.lower()} i {ort}{storleksrad}. "
                    f"Beslutsfattaren agenten skulle leta efter är {roll.lower()}. "
                    "Bolaget är påhittat och kan aldrig kontaktas."
                ),
            }
        )
    return bolag
