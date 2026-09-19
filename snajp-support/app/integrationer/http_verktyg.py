"""HTTP-verktyget: en konfigurerad förfrågan -> ett vaktat anrop -> ett resultat.

## Ifyllnaden är strukturell, inte textuell

Ett argument som modellen levererar är OPÅLITLIG text — den kan bära ett
citattecken, ett `&admin=true` eller en radbrytning. Därför fylls varje
platshållare i efter var den står:

  url       URL-kodad (`quote(v, safe="")`): ett `/`, `?`, `&` eller `#` i
            ett argument blir en del av VÄRDET, aldrig en ny sökvägsdel
            eller parameter. Värdnamnet kan inte röras av modellen alls
            (modell.py avvisar argument där).
  rubriker  ordagrant, men en radbrytning i resultatet avvisas — annars
            vore det rubrikinjektion.
  body      en sträng som BARA är "{{x}}" ersätts med värdet i sin typ (ett
            tal förblir ett tal, en lista en lista); en platshållare mitt i
            en längre sträng blir text. JSON-kodningen gör httpx efteråt, så
            ett citattecken i ett argument kan inte bryta sig ut ur sin sträng.

## Svaret

Samma form som Ebbots (`status`, `data`), med `responsePath` (JMESPath) för
att plocka ut rätt del av ett stort JSON-svar innan det når prompten. Allt
tvättas från kundens hemligheter innan det lämnar modulen.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib.parse import quote

import jmespath

from . import natvakt
from .hemligheter import tvatta
from .modell import HEMLIGHET_PREFIX, PLATSHALLARE, HttpForfragan, Platshallare
from .resultat import MAX_RESULTATTEXT, Verktygsresultat, kapa

logger = logging.getLogger("snajp-support.integrationer.http")

#: Ett enskilt strängargument. Längre än så är inte ett sökbegrepp eller ett
#: ordernummer, och en modell som skickar en uppsats som argument har tappat
#: tråden — det ska bli ett fel, inte en förfrågan.
MAX_ARGUMENTLANGD = 500


class ArgumentFel(ValueError):
    """Modellens argument passar inte verktygets schema. Går tillbaka till modellen."""


class SaknatVarde(ValueError):
    """Ett kontextvärde (t.ex. kund.email) finns inte i det här ärendet."""


def _tolka(p: Platshallare, varde: Any) -> Any:
    """Ett argument i sin deklarerade typ, eller ArgumentFel.

    Tolerant där tolkningen är entydig ("42" -> 42 för ett tal, "true" ->
    True), strikt där den inte är det (en lista som sträng).
    """
    typ = p.type
    if typ == "string":
        if isinstance(varde, bool) or not isinstance(varde, (str, int, float)):
            raise ArgumentFel(f"{p.key} ska vara text.")
        text = str(varde).strip()
        if len(text) > MAX_ARGUMENTLANGD:
            raise ArgumentFel(f"{p.key} är för långt ({len(text)} tecken).")
        return text
    if typ in ("number", "integer"):
        if isinstance(varde, bool):
            raise ArgumentFel(f"{p.key} ska vara ett tal.")
        tal: int | float
        if isinstance(varde, (int, float)):
            tal = varde
        else:
            text = str(varde).strip().replace(",", ".")
            try:
                # "5" ska bli 5, inte 5.0 — värdet hamnar ofta i en URL, och
                # ett API som väntar sig ?limit=5 kan avvisa ?limit=5.0.
                tal = int(text)
            except ValueError:
                try:
                    tal = float(text)
                except ValueError:
                    raise ArgumentFel(f"{p.key} ska vara ett tal.") from None
        if typ == "integer":
            if float(tal) != int(float(tal)):
                raise ArgumentFel(f"{p.key} ska vara ett heltal.")
            return int(float(tal))
        return tal
    if typ == "boolean":
        if isinstance(varde, bool):
            return varde
        if str(varde).strip().lower() in ("true", "ja", "1"):
            return True
        if str(varde).strip().lower() in ("false", "nej", "0"):
            return False
        raise ArgumentFel(f"{p.key} ska vara sant eller falskt.")
    if typ == "object":
        if not isinstance(varde, dict):
            raise ArgumentFel(f"{p.key} ska vara ett objekt.")
        return varde
    if typ == "array":
        if not isinstance(varde, list):
            raise ArgumentFel(f"{p.key} ska vara en lista.")
        return varde
    raise ArgumentFel(f"{p.key} har en okänd typ.")  # pragma: no cover


def validera_argument(
    forfragan: HttpForfragan, argument: dict[str, Any] | None, hemlighetsnamn: set[str]
) -> dict[str, Any]:
    argument = dict(argument or {})
    deklarerade = forfragan.argument(hemlighetsnamn)
    kanda = {p.key for p in deklarerade}
    okanda = sorted(set(argument) - kanda)
    if okanda:
        raise ArgumentFel(
            f"Verktyget tar inte argumenten {', '.join(okanda)}. "
            f"Giltiga: {', '.join(sorted(kanda)) or 'inga'}."
        )
    ut: dict[str, Any] = {}
    for p in deklarerade:
        varde = argument.get(p.key)
        if varde is None or (isinstance(varde, str) and not varde.strip()):
            if p.default is None:
                raise ArgumentFel(f"Argumentet {p.key} saknas.")
            varde = p.default
        varde = _tolka(p, varde)
        if p.enum and varde not in p.enum:
            raise ArgumentFel(f"{p.key} måste vara ett av: {', '.join(map(str, p.enum))}.")
        ut[p.key] = varde
    return ut


def _som_text(varde: Any) -> str:
    if isinstance(varde, str):
        return varde
    if isinstance(varde, bool):
        return "true" if varde else "false"
    if isinstance(varde, (int, float)):
        return str(varde)
    return json.dumps(varde, ensure_ascii=False)


def _sla_upp(namn: str, varden: dict[str, Any]) -> Any:
    if namn not in varden or varden[namn] is None or varden[namn] == "":
        raise SaknatVarde(namn)
    return varden[namn]


def fyll_text(mall: str, varden: dict[str, Any], *, url_koda: bool = False) -> str:
    def byt(m: Any) -> str:
        text = _som_text(_sla_upp(m.group(1), varden))
        return quote(text, safe="") if url_koda else text

    return PLATSHALLARE.sub(byt, mall)


def fyll_struktur(varde: Any, varden: dict[str, Any]) -> Any:
    if isinstance(varde, str):
        hel = PLATSHALLARE.fullmatch(varde.strip())
        if hel:
            return _sla_upp(hel.group(1), varden)
        return fyll_text(varde, varden)
    if isinstance(varde, dict):
        return {fyll_text(str(k), varden): fyll_struktur(v, varden) for k, v in varde.items()}
    if isinstance(varde, list):
        return [fyll_struktur(v, varden) for v in varde]
    return varde


def varden_for(
    *,
    argument: dict[str, Any],
    hemligheter: dict[str, str],
    kontext: dict[str, Any],
) -> dict[str, Any]:
    """Alla värden en förfrågan kan fyllas i med, i FÖRETRÄDESORDNING.

    Argumenten läggs först och skrivs över av kontext och hemligheter — en
    modell som skickar argumentet `kund.email` (eller ett argument med samma
    namn som en hemlighet) kan inte ersätta det koden satt.
    """
    varden: dict[str, Any] = dict(argument)
    varden.update({k: v for k, v in kontext.items() if v not in (None, "")})
    for namn, hemlighet in hemligheter.items():
        varden[f"{HEMLIGHET_PREFIX}{namn}"] = hemlighet
        varden[namn] = hemlighet  # Ebbot-formen {{token}}
    return varden


def bygg_anrop(
    forfragan: HttpForfragan,
    *,
    argument: dict[str, Any],
    hemligheter: dict[str, str],
    kontext: dict[str, Any],
) -> tuple[str, str, dict[str, str], Any]:
    varden = varden_for(argument=argument, hemligheter=hemligheter, kontext=kontext)
    url = fyll_text(forfragan.url, varden, url_koda=True)
    # Formen på den ifyllda adressen prövas här; DNS och varje omdirigering
    # prövas av natvakt.anropa.
    natvakt.kontrollera_url(url)
    rubriker: dict[str, str] = {}
    for namn, mall in forfragan.headers.items():
        varde = fyll_text(mall, varden)
        if "\n" in varde or "\r" in varde:
            raise ArgumentFel(f"Rubriken {namn} fick en radbrytning.")
        rubriker[fyll_text(namn, varden)] = varde
    kropp = None if forfragan.method == "GET" else fyll_struktur(forfragan.body, varden)
    return forfragan.method, url, rubriker, kropp


def _tolka_svar(svar: natvakt.Svar, svarsvag: str | None) -> Any:
    typ = svar.innehallstyp.split(";", 1)[0].strip().lower()
    if "json" in typ:
        try:
            data: Any = json.loads(svar.text) if svar.text.strip() else None
        except json.JSONDecodeError:
            return svar.text
        if svarsvag and data is not None:
            data = jmespath.search(svarsvag, data)
        return data
    return svar.text


async def kor(
    forfragan: HttpForfragan,
    *,
    argument: dict[str, Any] | None,
    hemligheter: dict[str, str],
    kontext: dict[str, Any],
    simulera: bool = False,
    tidsgrans: float = natvakt.STANDARD_TIDSGRANS,
    max_text: int = MAX_RESULTATTEXT,
) -> Verktygsresultat:
    """Kör förfrågan. Kastar aldrig — varje fel blir ett resultat med `fel`.

    Ett verktygsfel ska aldrig fälla ärendet. Modellen får beskedet och kan
    säga till kunden att uppgiften inte gick att hämta just nu.
    """
    start = time.monotonic()
    namn = forfragan.verktygsnamn
    skrivande = forfragan.ar_skrivande

    def resultat(**kw: Any) -> Verktygsresultat:
        return Verktygsresultat(
            verktyg=namn,
            skrivande=skrivande,
            latens_ms=int((time.monotonic() - start) * 1000),
            **kw,
        )

    try:
        giltiga = validera_argument(forfragan, argument, set(hemligheter))
        metod, url, rubriker, kropp = bygg_anrop(
            forfragan, argument=giltiga, hemligheter=hemligheter, kontext=kontext
        )
    except ArgumentFel as fel:
        return resultat(ok=False, fel=str(fel))
    except SaknatVarde as fel:
        falt = str(fel)
        return resultat(
            ok=False,
            fel=(
                f"Uppgiften {falt} finns inte i det här ärendet, så anropet gick inte att göra."
                if not falt.startswith(HEMLIGHET_PREFIX)
                else "Integrationen saknar en sparad nyckel. En administratör behöver lägga in den."
            ),
        )
    except natvakt.NatvaktError as fel:
        return resultat(ok=False, fel=f"Adressen är inte tillåten: {fel}")

    if simulera and skrivande:
        return resultat(ok=True, simulerad=True, data=f"{metod} {tvatta(url, hemligheter)}")

    try:
        if isinstance(kropp, str):
            svar = await natvakt.anropa(
                metod, url, rubriker=rubriker, innehall=kropp.encode("utf-8"), tidsgrans=tidsgrans
            )
        else:
            svar = await natvakt.anropa(
                metod, url, rubriker=rubriker, json_kropp=kropp, tidsgrans=tidsgrans
            )
    except natvakt.NatvaktError as fel:
        return resultat(ok=False, fel=str(fel))
    except Exception as fel:  # noqa: BLE001 — nätfel av alla slag blir ett resultat
        logger.info("HTTP-verktyget %s föll: %s", namn, type(fel).__name__)
        return resultat(ok=False, fel=f"Systemet svarade inte ({type(fel).__name__}).")

    try:
        # responsePath beskriver ett LYCKAT svar. På ett felsvar hade den
        # plockat fram ingenting ur {"error": ...} och tagit bort just det
        # besked som förklarar felet.
        data = _tolka_svar(svar, forfragan.responsePath if svar.ok else None)
    except Exception:  # noqa: BLE001 — ett trasigt responsePath får inte fälla anropet
        data = svar.text
    text = tvatta(_som_text(data) if data is not None else "", hemligheter)
    text = kapa(text, max_text)
    if not svar.ok:
        return resultat(
            ok=False,
            status=svar.status,
            data=text,
            fel=f"Systemet svarade {svar.status} {svar.status_text}".strip(),
        )
    return resultat(ok=True, status=svar.status, data=text)
