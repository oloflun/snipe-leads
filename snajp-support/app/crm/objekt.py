"""Affärer, uppgifter, anteckningar, aktiviteter och bilagor (migration 164).

Reglerna och skrivvägarna för de fem objekten bredvid bolag och personer.
Samma form som `app/crm/synk.py`: varje skrivning går hit, och varje
skrivning slutar med `handelser.logga`, så att den syns i ändringsflödet, i
postens historik och hos kundens webhooks.

## Kopplingarna

En uppgift får stå fri. En anteckning, en aktivitet och en bilaga hör alltid
till något: ett bolag, en person, en affär (och för en bilaga en anteckning).
Varje koppling som anges ska peka på en levande post hos SAMMA kund. Radskyddet
i databasen stoppar redan en främmande kunds rad, men felet ska säga vad som
var fel, inte bli ett 500 från en främmande nyckel.

## Affärens steg

En uppsättning per kund, skapad första gången kunden läser dem, med svensk
standard. Kunden byter namn, ordnar om, lägger till och tar bort. Två regler
gör att tavlan alltid går att använda: ett steg med affärer i går inte att ta
bort, och det finns alltid minst ett öppet, ett vunnet och ett förlorat steg.

`avslutad_at` sätts när en affär når ett vunnet eller förlorat steg och nollas
när den flyttas tillbaka till ett öppet. `position` är ordningen inom steget på
tavlan: ett flyttat kort får ett värde mitt emellan sina grannar, så att en
flytt skriver en rad och inte hela steget.

## Bilagor

Högst 10 MB per fil och 500 MB per kund. Typen avgörs av både filändelsen och
den angivna typen, och bara de vanliga dokument- och bildtyperna tas emot: en
html-fil eller ett skript som laddas ned från vår domän ska inte gå att ladda
upp. Filnamnet rensas från sökvägar och styrtecken.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from datetime import timezone
from typing import Any

from . import falt, handelser, lagring
from .synk import RedanTomd

__all__ = ["RedanTomd"]

OBJEKT = ("affar", "uppgift", "anteckning", "aktivitet", "bilaga")

STEGTYPER = ("oppen", "vunnen", "forlorad")
#: Svensk standard: (namn, sannolikhet i procent, typ).
STANDARDSTEG = (
    ("Ny", 10, "oppen"), ("Kvalificerad", 25, "oppen"), ("Möte bokat", 40, "oppen"),
    ("Offert skickad", 60, "oppen"), ("Förhandling", 80, "oppen"),
    ("Vunnen", 100, "vunnen"), ("Förlorad", 0, "forlorad"),
)
#: Förlustorsaken ur listan (migration 165), med API:ts namn. Fritexten
#: `forlustorsak` står kvar som reserv och får sättas med vilken kod som helst.
FORLUSTORSAKER = {"pris": "price", "konkurrent": "competitor", "tidpunkt": "timing",
                  "inget_behov": "no_need", "ingen_budget": "no_budget", "inget_svar": "no_response",
                  "annat": "other"}
_FORLUSTORSAK_IN = {**{sv: sv for sv in FORLUSTORSAKER}, **{en: sv for sv, en in FORLUSTORSAKER.items()}}
UPPGIFTSSTATUS = ("att_gora", "pagar", "klar")
AKTIVITETSTYPER = ("samtal", "mote", "mejl", "besok", "ovrigt")

MAX_BILAGA = 10 * 1024 * 1024
MAX_BILAGOR_PER_KUND = 500 * 1024 * 1024
MAX_ANTECKNING = 20_000
#: Avståndet mellan två kort på tavlan när de läggs sist.
_STEG_I_POSITION = 1024.0

#: Tillåtna filändelser och de typer en webbläsare eller ett system kan ange
#: för dem. Den första är den som sparas och lämnas ut.
TILLATNA_TYPER: dict[str, tuple[str, ...]] = {
    "pdf": ("application/pdf",),
    "png": ("image/png",),
    "jpg": ("image/jpeg", "image/jpg", "image/pjpeg"),
    "jpeg": ("image/jpeg", "image/jpg", "image/pjpeg"),
    "webp": ("image/webp",),
    "gif": ("image/gif",),
    "txt": ("text/plain",),
    # Excel på Windows anger csv som application/vnd.ms-excel.
    "csv": ("text/csv", "application/csv", "application/vnd.ms-excel", "text/plain"),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",),
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",),
    "pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation",),
}
#: Typen en del klienter anger när de inte vet. Då avgör filändelsen.
_OKAND_TYP = ("", "application/octet-stream")

_TABELL = {objekt: lagring._OBJEKTTABELL[objekt] for objekt in OBJEKT}
#: Kopplingarna varje objekt kan ha, och vilken post de ska peka på.
_KOPPLINGAR = {
    "affar": ("bolag_id", "person_id"),
    "uppgift": ("bolag_id", "person_id", "affar_id"),
    "anteckning": ("bolag_id", "person_id", "affar_id"),
    "aktivitet": ("bolag_id", "person_id", "affar_id"),
    "bilaga": ("bolag_id", "person_id", "affar_id", "anteckning_id"),
}
_MAL = {"bolag_id": ("bolag", "company_not_found"), "person_id": ("person", "person_not_found"),
        "affar_id": ("affar", "deal_not_found"), "anteckning_id": ("anteckning", "note_not_found")}
#: Objekt som inte får stå utan koppling.
_KRAVER_KOPPLING = ("anteckning", "aktivitet", "bilaga")

#: Textfält och deras längsta tillåtna längd. Radbrytningar står kvar.
_TEXTFALT = {
    "affar": {"namn": 200, "forlustorsak": 500, "ansvarig": 200},
    "uppgift": {"titel": 300, "beskrivning": 10_000, "ansvarig": 200},
    "anteckning": {"titel": 300, "text": MAX_ANTECKNING, "forfattare": 200},
    "aktivitet": {"rubrik": 300, "text": MAX_ANTECKNING, "utfall": 500, "ansvarig": 200},
}
#: Fält som inte får tömmas, och som krävs när posten skapas.
_KRAVS = {"affar": ("namn",), "uppgift": ("titel",), "aktivitet": ("rubrik",)}
#: Fält som inte nämns i händelseloggen: bokföring.
_TYSTA = ("updated_at", "raderad_at")


class ObjektFel(ValueError):
    """En regel sa nej. `kod` är API:ts stabila felkod; `falt` räknar upp
    fälten som inte gick att tolka, när det är det felet gäller."""

    def __init__(self, kod: str, falt: list[dict[str, str]] | None = None) -> None:
        super().__init__(kod)
        self.kod = kod
        self.falt = falt or []


# -- Tolkning ----------------------------------------------------------------


def _fritext(varde: Any, max_langd: int) -> str | None:
    """Text där radbrytningar betyder något. Tomt blir None."""
    if varde is None:
        return None
    ut = str(varde).replace("\r\n", "\n").strip()
    if len(ut) > max_langd:
        raise falt.FaltFel("for_lang")
    return ut or None


def _heltal(varde: Any, lagst: int, hogst: int) -> int | None:
    tal = falt.heltal(varde)
    if tal is not None and not lagst <= tal <= hogst:
        raise falt.FaltFel("utanfor_intervall")
    return tal


def _tid_utc(varde: Any) -> str | None:
    """Tidpunkt i UTC, så att strängarna sorterar som tiderna."""
    tid = falt.tidpunkt(varde)
    return lagring._tid(tid).astimezone(timezone.utc).isoformat() if tid else None


def _id(varde: Any) -> str | None:
    if varde is None:
        return None
    try:
        return str(uuid.UUID(str(varde)))
    except ValueError:
        raise falt.FaltFel("id_ogiltigt") from None


def _tolka(objekt: str, falten: dict[str, Any], *, ny: bool) -> dict[str, Any]:
    """Anropets fält (CRM:ets namn) som de ska skrivas. Höjer `ObjektFel`
    med alla fält som inte gick att tolka på en gång."""
    skriv: dict[str, Any] = {}
    fel: list[dict[str, str]] = []
    for namn, varde in falten.items():
        try:
            if namn in _TEXTFALT.get(objekt, {}):
                skriv[namn] = _fritext(varde, _TEXTFALT[objekt][namn])
            elif namn in _KOPPLINGAR[objekt] or (namn == "steg_id" and objekt == "affar"):
                skriv[namn] = _id(varde)
            elif objekt == "affar" and namn == "belopp":
                skriv[namn] = _heltal(varde, 0, 10**15)
            elif objekt == "affar" and namn == "valuta":
                valuta = (falt.text(varde, max_langd=10) or "SEK").upper()
                if not re.fullmatch(r"[A-Z]{3}", valuta):
                    raise falt.FaltFel("valuta_ogiltig")
                skriv[namn] = valuta
            elif objekt == "affar" and namn == "sannolikhet":
                skriv[namn] = _heltal(varde, 0, 100)
            elif objekt == "affar" and namn == "forvantat_avslut":
                skriv[namn] = falt.datum(varde)
            elif objekt == "affar" and namn == "forlustorsak_kod":
                if varde is None:
                    skriv[namn] = None
                else:
                    kod = _FORLUSTORSAK_IN.get(str(varde).strip().casefold())
                    if not kod:
                        raise falt.FaltFel("forlustorsak_okand")
                    skriv[namn] = kod
            elif objekt == "affar" and namn == "extra":
                if varde is not None and not isinstance(varde, dict):
                    raise falt.FaltFel("ska_vara_objekt")
                skriv[namn] = {str(k)[:60]: v for k, v in list((varde or {}).items())[:50]
                               if not isinstance(v, (dict, list))}
            elif objekt == "uppgift" and namn == "status":
                if varde not in UPPGIFTSSTATUS:
                    raise falt.FaltFel("okant_varde")
                skriv[namn] = varde
            elif (objekt, namn) in (("uppgift", "forfaller_at"), ("aktivitet", "tid")):
                skriv[namn] = _tid_utc(varde)
            elif objekt == "anteckning" and namn == "fast":
                skriv[namn] = bool(varde)
            elif objekt == "aktivitet" and namn == "typ":
                if varde not in AKTIVITETSTYPER:
                    raise falt.FaltFel("okant_varde")
                skriv[namn] = varde
            elif objekt == "aktivitet" and namn == "varaktighet_min":
                skriv[namn] = _heltal(varde, 0, 100_000)
            else:
                raise falt.FaltFel("okant_falt")
        except falt.FaltFel as orsak:
            fel.append({"falt": namn, "kod": orsak.kod})
    for namn in _KRAVS.get(objekt, ()):
        if (ny or namn in skriv) and not skriv.get(namn):
            fel.append({"falt": namn, "kod": "saknas"})
    if objekt == "anteckning" and "text" in skriv:
        skriv["text"] = skriv["text"] or ""  # kolumnen är `not null`
    if objekt == "aktivitet" and "tid" in skriv and skriv["tid"] is None:
        skriv.pop("tid")  # tiden kan inte tömmas: den är när det hände
    if fel:
        raise ObjektFel("invalid_fields", fel)
    return skriv


async def _kontrollera_kopplingar(
    storage: Any, tenant_id: str, objekt: str, skriv: dict[str, Any], post: dict[str, Any] | None
) -> None:
    for kolumn in _KOPPLINGAR[objekt]:
        if skriv.get(kolumn) is None:
            continue
        mal, kod = _MAL[kolumn]
        rad = await lagring.hamta_post(storage, tenant_id, mal, skriv[kolumn])
        if rad is None or rad.get("kalla") == lagring.GRAVSTEN:
            raise ObjektFel(kod)
    if objekt in _KRAVER_KOPPLING:
        efter = {**(post or {}), **skriv}
        if not any(efter.get(k) for k in _KOPPLINGAR[objekt]):
            raise ObjektFel("target_required")


# -- Affärens steg -----------------------------------------------------------


async def lista_steg(storage: Any, tenant_id: str) -> list[dict[str, Any]]:
    """Kundens steg i tavlans ordning. Saknas de skapas standardstegen.

    Två samtidiga första läsningar ger inte två uppsättningar: namnet är
    unikt per kund (migration 164), så den som kommer tvåa får en krock per
    steg och läser sedan den första läsningens rader.

    Stegen skrivs ett i taget, så en läsning medan den första fortfarande
    skriver kan se en del av dem. En uppsättning utan något öppet, vunnet
    eller förlorat steg finns annars aldrig (de sista av sin typ går inte att
    ta bort), så då fylls de standardsteg på som saknas."""
    steg = await lagring._valj(storage, tenant_id, "crm_affarssteg", ordning="position")
    if steg and _alla_typer_finns(steg):
        return steg
    for position, (namn, sannolikhet, typ) in enumerate(STANDARDSTEG):
        try:
            await lagring._in(storage, tenant_id, "crm_affarssteg",
                              {"namn": namn, "position": position, "sannolikhet": sannolikhet, "typ": typ})
        except lagring.FinnsRedan:
            continue
    return await lagring._valj(storage, tenant_id, "crm_affarssteg", ordning="position")


def _tolka_steg(falten: dict[str, Any], *, ny: bool) -> dict[str, Any]:
    skriv: dict[str, Any] = {}
    fel: list[dict[str, str]] = []
    for namn, varde in falten.items():
        try:
            if namn == "namn":
                skriv[namn] = falt.text(varde, max_langd=61)
                if not skriv[namn] or len(skriv[namn]) > 60:
                    raise falt.FaltFel("saknas" if not skriv[namn] else "for_lang")
            elif namn == "sannolikhet":
                skriv[namn] = _heltal(varde, 0, 100)
                if skriv[namn] is None:
                    raise falt.FaltFel("saknas")
            elif namn == "typ":
                if varde not in STEGTYPER:
                    raise falt.FaltFel("okant_varde")
                skriv[namn] = varde
            elif namn == "farg":
                skriv[namn] = falt.text(varde, max_langd=40)
            else:
                raise falt.FaltFel("okant_falt")
        except falt.FaltFel as orsak:
            fel.append({"falt": namn, "kod": orsak.kod})
    if ny and not skriv.get("namn") and not any(f["falt"] == "namn" for f in fel):
        fel.append({"falt": "namn", "kod": "saknas"})
    if fel:
        raise ObjektFel("invalid_fields", fel)
    return skriv


def _alla_typer_finns(steg: list[dict[str, Any]]) -> bool:
    return all(any(s["typ"] == typ for s in steg) for typ in STEGTYPER)


async def _steget(storage: Any, tenant_id: str, steg_id: str) -> dict[str, Any]:
    rad = next((s for s in await lista_steg(storage, tenant_id) if s["id"] == steg_id), None)
    if rad is None:
        raise ObjektFel("stage_not_found")
    return rad


async def skapa_steg(storage: Any, tenant_id: str, falten: dict[str, Any]) -> dict[str, Any]:
    """Ett nytt steg läggs sist. Höjer `lagring.FinnsRedan` om namnet finns."""
    skriv = _tolka_steg(falten, ny=True)
    steg = await lista_steg(storage, tenant_id)
    skriv["position"] = max((s["position"] for s in steg), default=-1) + 1
    return await lagring._in(storage, tenant_id, "crm_affarssteg", skriv)


async def andra_steg(storage: Any, tenant_id: str, steg_id: str, falten: dict[str, Any]) -> dict[str, Any] | None:
    steg = await lista_steg(storage, tenant_id)
    rad = next((s for s in steg if s["id"] == steg_id), None)
    if rad is None:
        return None
    skriv = {k: v for k, v in _tolka_steg(falten, ny=False).items() if rad.get(k) != v}
    if "typ" in skriv and not _alla_typer_finns([{**s, **skriv} if s["id"] == steg_id else s for s in steg]):
        raise ObjektFel("stage_required")
    return await lagring._upp(storage, tenant_id, "crm_affarssteg", steg_id, skriv)


async def ta_bort_steg(storage: Any, tenant_id: str, steg_id: str) -> bool:
    """Ett steg med affärer i, också raderade som går att återställa, står
    kvar. Det sista öppna, vunna eller förlorade steget står också kvar."""
    steg = await lista_steg(storage, tenant_id)
    if not any(s["id"] == steg_id for s in steg):
        return False
    if await lagring._valj(storage, tenant_id, "crm_affarer", lika={"steg_id": steg_id}, limit=1):
        raise ObjektFel("stage_in_use")
    if not _alla_typer_finns([s for s in steg if s["id"] != steg_id]):
        raise ObjektFel("stage_required")
    try:
        return await lagring._ta_bort(storage, tenant_id, "crm_affarssteg", steg_id)
    except Exception as fel:
        # En affär som hann läggas i steget efter kontrollen: främmande nyckeln
        # (restrict, migration 164) säger nej, och svaret ska säga varför.
        if getattr(fel, "sqlstate", None) == "23503":
            raise ObjektFel("stage_in_use") from None
        raise


async def ordna_steg(storage: Any, tenant_id: str, ids: list[str]) -> list[dict[str, Any]]:
    """Ny ordning. `ids` ska vara exakt kundens steg, vart och ett en gång."""
    steg = await lista_steg(storage, tenant_id)
    if sorted(map(str, ids)) != sorted(s["id"] for s in steg):
        raise ObjektFel("invalid_fields", [{"falt": "ids", "kod": "ska_vara_alla_steg"}])
    per_id = {s["id"]: s for s in steg}
    for position, steg_id in enumerate(map(str, ids)):
        if per_id[steg_id]["position"] != position:
            await lagring._upp(storage, tenant_id, "crm_affarssteg", steg_id, {"position": position})
    return await lista_steg(storage, tenant_id)


# -- Affärernas ordning på tavlan --------------------------------------------


def _avslut(nuvarande: str | None, typ: str) -> str | None:
    """`avslutad_at` efter en flytt till ett steg av typen `typ`."""
    if typ in ("vunnen", "forlorad"):
        return nuvarande or lagring.nu()
    return None


async def _i_steget(storage: Any, tenant_id: str, steg_id: str, utom: str | None = None) -> list[dict[str, Any]]:
    rader = await lagring._valj(storage, tenant_id, "crm_affarer", lika={"steg_id": steg_id},
                                levande=True, ordning="position")
    return [r for r in rader if r["id"] != utom]


async def _sist(storage: Any, tenant_id: str, steg_id: str, utom: str | None = None) -> float:
    grannar = await _i_steget(storage, tenant_id, steg_id, utom)
    return (grannar[-1]["position"] + _STEG_I_POSITION) if grannar else _STEG_I_POSITION


# -- Skrivvägarna ------------------------------------------------------------


async def hamta(
    storage: Any, tenant_id: str, objekt: str, rad_id: str, *, med_raderade: bool = False
) -> dict[str, Any] | None:
    return await lagring.hamta_post(storage, tenant_id, objekt, rad_id, med_raderade=med_raderade)


async def skapa(
    storage: Any, tenant_id: str, objekt: str, falten: dict[str, Any], *, kalla: str = "manuell",
    via: str = "api", aktor: str | None = None,
) -> dict[str, Any]:
    """Skapar en affär, uppgift, anteckning eller aktivitet. Bilagor går
    genom `skapa_bilaga`."""
    skriv = _tolka(objekt, falten, ny=True)
    await _kontrollera_kopplingar(storage, tenant_id, objekt, skriv, None)
    if objekt == "affar":
        steg = await lista_steg(storage, tenant_id)
        if skriv.get("steg_id"):
            stegrad = await _steget(storage, tenant_id, skriv["steg_id"])
        else:
            stegrad = next(s for s in steg if s["typ"] == "oppen")
            skriv["steg_id"] = stegrad["id"]
        skriv["position"] = await _sist(storage, tenant_id, stegrad["id"])
        skriv["avslutad_at"] = _avslut(None, stegrad["typ"])
    if objekt == "uppgift":
        skriv["klar_at"] = lagring.nu() if skriv.get("status") == "klar" else None
    if objekt == "aktivitet":
        skriv.setdefault("tid", lagring.nu())
    post = await lagring._in(storage, tenant_id, _TABELL[objekt], {**skriv, "kalla": kalla})
    await handelser.logga(storage, tenant_id, [handelser.Handelse(objekt, post["id"], "skapad", post=post)],
                          kalla=via, aktor=aktor)
    return post


async def _skriv(
    storage: Any, tenant_id: str, objekt: str, post: dict[str, Any], skriv: dict[str, Any], *,
    via: str, aktor: str | None,
) -> dict[str, Any]:
    skriv = {k: v for k, v in skriv.items() if post.get(k) != v}
    if not skriv:
        return post
    ny = await lagring._upp(storage, tenant_id, _TABELL[objekt], post["id"], skriv)
    if ny:
        await handelser.logga(storage, tenant_id, [handelser.Handelse(
            objekt, post["id"], "andrad", falt=[k for k in skriv if k not in _TYSTA], post=ny)],
            kalla=via, aktor=aktor)
    return ny or post


async def andra(
    storage: Any, tenant_id: str, objekt: str, rad_id: str, falten: dict[str, Any], *,
    via: str = "api", aktor: str | None = None,
) -> dict[str, Any] | None:
    """Ändrar de fält som skickas; `None` tömmer fältet. En affär som byter
    steg hamnar sist i det nya steget; flytt med ordning går genom `flytta`."""
    post = await hamta(storage, tenant_id, objekt, rad_id)
    if post is None:
        return None
    skriv = {k: v for k, v in _tolka(objekt, falten, ny=False).items() if post.get(k) != v}
    await _kontrollera_kopplingar(storage, tenant_id, objekt, skriv, post)
    if objekt == "affar" and "steg_id" in skriv:
        if not skriv["steg_id"]:
            raise ObjektFel("invalid_fields", [{"falt": "steg_id", "kod": "saknas"}])
        stegrad = await _steget(storage, tenant_id, skriv["steg_id"])
        skriv["position"] = await _sist(storage, tenant_id, stegrad["id"], utom=rad_id)
        skriv["avslutad_at"] = _avslut(post.get("avslutad_at"), stegrad["typ"])
    if objekt == "uppgift" and "status" in skriv:
        skriv["klar_at"] = (post.get("klar_at") or lagring.nu()) if skriv["status"] == "klar" else None
    return await _skriv(storage, tenant_id, objekt, post, skriv, via=via, aktor=aktor)


async def flytta(
    storage: Any, tenant_id: str, rad_id: str, steg_id: str, *, fore_id: str | None = None,
    efter_id: str | None = None, via: str = "api", aktor: str | None = None,
) -> dict[str, Any] | None:
    """Flyttar en affär på tavlan: till steget, före `fore_id` eller efter
    `efter_id` (eller sist, utan någon av dem). Positionen blir mitt emellan
    grannarna; är luckan förbrukad numreras steget om först."""
    post = await hamta(storage, tenant_id, "affar", rad_id)
    if post is None:
        return None
    if fore_id and efter_id:
        raise ObjektFel("invalid_fields", [{"falt": "before_id", "kod": "bara_en_av_before_och_after"}])
    stegrad = await _steget(storage, tenant_id, str(steg_id))
    for forsok in range(2):
        grannar = await _i_steget(storage, tenant_id, stegrad["id"], utom=rad_id)
        index = {g["id"]: i for i, g in enumerate(grannar)}
        granne = fore_id or efter_id
        if granne and granne not in index:
            raise ObjektFel("invalid_fields", [{"falt": "before_id" if fore_id else "after_id",
                                                "kod": "inte_i_steget"}])
        if fore_id:
            i = index[fore_id]
            lag, hog = (grannar[i - 1]["position"] if i else None), grannar[i]["position"]
        elif efter_id:
            i = index[efter_id]
            lag, hog = grannar[i]["position"], (grannar[i + 1]["position"] if i + 1 < len(grannar) else None)
        else:
            lag, hog = (grannar[-1]["position"] if grannar else None), None
        if lag is not None and hog is not None and hog - lag < 1e-6 and not forsok:
            # Luckan är slut efter många flyttar på samma ställe: jämna ut steget.
            for i, g in enumerate(grannar):
                await _skriv(storage, tenant_id, "affar", g, {"position": (i + 1) * _STEG_I_POSITION},
                             via=via, aktor=aktor)
            continue
        break
    if lag is None and hog is None:
        position = _STEG_I_POSITION
    elif lag is None:
        position = hog - _STEG_I_POSITION
    elif hog is None:
        position = lag + _STEG_I_POSITION
    else:
        position = (lag + hog) / 2
    skriv: dict[str, Any] = {"position": position}
    if stegrad["id"] != post.get("steg_id"):
        skriv["steg_id"] = stegrad["id"]
        skriv["avslutad_at"] = _avslut(post.get("avslutad_at"), stegrad["typ"])
    return await _skriv(storage, tenant_id, "affar", post, skriv, via=via, aktor=aktor)


async def tavla(storage: Any, tenant_id: str) -> list[dict[str, Any]]:
    """Stegen i ordning, var och ett med sina levande affärer i tavlans ordning."""
    steg = await lista_steg(storage, tenant_id)
    affarer = await lagring._valj(storage, tenant_id, "crm_affarer", levande=True, ordning="position")
    per_steg: dict[str, list[dict[str, Any]]] = {s["id"]: [] for s in steg}
    for affar in affarer:
        per_steg.setdefault(affar.get("steg_id"), []).append(affar)
    return [{**s, "affarer": per_steg[s["id"]]} for s in steg]


async def radera(
    storage: Any, tenant_id: str, objekt: str, rad_id: str, *, permanent: bool = False,
    via: str = "api", aktor: str | None = None,
) -> bool:
    """Mjuk radering som för bolag: 30 dagar i papperskorgen, sedan töms
    raden. `permanent` tömmer den direkt."""
    post = await hamta(storage, tenant_id, objekt, rad_id, med_raderade=permanent)
    if post is None or post.get("kalla") == lagring.GRAVSTEN:
        return False
    if permanent:
        await lagring.gor_gravsten(storage, tenant_id, objekt, rad_id, via=via, aktor=aktor)
    else:
        ny = await lagring._upp(storage, tenant_id, _TABELL[objekt], rad_id, {"raderad_at": lagring.nu()})
        await handelser.logga(storage, tenant_id, [handelser.Handelse(objekt, rad_id, "raderad", post=ny)],
                              kalla=via, aktor=aktor)
    await lagring.tom_papperskorgarna(storage, tenant_id)
    return True


async def aterstall(
    storage: Any, tenant_id: str, objekt: str, rad_id: str, *, via: str = "api", aktor: str | None = None,
) -> dict[str, Any] | None:
    """Tar tillbaka en post ur papperskorgen. Höjer `RedanTomd` för en tömd."""
    post = await hamta(storage, tenant_id, objekt, rad_id, med_raderade=True)
    if post is None or not post.get("raderad_at"):
        return post
    if post.get("kalla") == lagring.GRAVSTEN:
        raise RedanTomd()
    ny = await lagring._upp(storage, tenant_id, _TABELL[objekt], rad_id, {"raderad_at": None})
    await handelser.logga(storage, tenant_id, [handelser.Handelse(objekt, rad_id, "aterstalld", post=ny)],
                          kalla=via, aktor=aktor)
    return ny


# -- Bilagor -----------------------------------------------------------------

_STYRTECKEN = re.compile(r"[\x00-\x1f\x7f]")


def rensa_filnamn(namn: str | None) -> str:
    """Bara filens eget namn: utan katalogdelar (`..\\..\\x.pdf` blir
    `x.pdf`), utan styrtecken och osynliga formattecken, högst 200 tecken."""
    ra = re.split(r"[\\/]", str(namn or ""))[-1]
    ra = "".join(t for t in ra if unicodedata.category(t) not in ("Cc", "Cf"))
    ra = _STYRTECKEN.sub("", ra).strip().lstrip(".").strip()
    if len(ra) > 200:
        stam, _, andelse = ra.rpartition(".")
        ra = (stam[: 200 - len(andelse) - 1] + "." + andelse) if stam and len(andelse) <= 10 else ra[:200]
    return ra or "fil"


def filtyp(filnamn: str, angiven: str | None) -> str:
    """Typen som sparas. Filändelsen ska vara tillåten, och en angiven typ
    ska passa ändelsen: en html-sida döpt till .pdf tas inte emot."""
    andelse = filnamn.rpartition(".")[2].lower() if "." in filnamn else ""
    typer = TILLATNA_TYPER.get(andelse)
    angiven = (angiven or "").split(";")[0].strip().lower()
    if not typer or (angiven not in _OKAND_TYP and angiven not in typer):
        raise ObjektFel("file_type_not_allowed")
    return typer[0]


async def skapa_bilaga(
    storage: Any, tenant_id: str, *, filnamn: str | None, typ: str | None, innehall: bytes,
    kopplingar: dict[str, Any], uppladdad_av: str | None = None, kalla: str = "manuell",
    via: str = "api", aktor: str | None = None,
) -> dict[str, Any]:
    if len(innehall) > MAX_BILAGA:
        raise ObjektFel("file_too_large")
    namn = rensa_filnamn(filnamn)
    sparad_typ = filtyp(namn, typ)
    fel: list[dict[str, str]] = []
    skriv: dict[str, Any] = {}
    for kolumn in _KOPPLINGAR["bilaga"]:
        try:
            skriv[kolumn] = _id(kopplingar.get(kolumn))
        except falt.FaltFel as orsak:
            fel.append({"falt": kolumn, "kod": orsak.kod})
    if fel:
        raise ObjektFel("invalid_fields", fel)
    await _kontrollera_kopplingar(storage, tenant_id, "bilaga", skriv, None)
    # Raderade filer räknas mot kvoten tills de töms: töm de utgångna först.
    await lagring.tom_papperskorgarna(storage, tenant_id)
    if await lagring.bilagornas_storlek(storage, tenant_id) + len(innehall) > MAX_BILAGOR_PER_KUND:
        raise ObjektFel("storage_quota_exceeded")
    post = await lagring._in(storage, tenant_id, "crm_bilagor", {
        **skriv, "filnamn": namn, "typ": sparad_typ, "storlek": len(innehall), "innehall": bytes(innehall),
        "uppladdad_av": (falt.text(uppladdad_av, max_langd=200) if uppladdad_av else None), "kalla": kalla})
    await handelser.logga(storage, tenant_id, [handelser.Handelse("bilaga", post["id"], "skapad", post=post)],
                          kalla=via, aktor=aktor)
    return post
