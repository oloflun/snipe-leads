"""Iris-konversationerna (Antons beställning 2026-11-22): steget, händelserna
och det som läses ur trådens text.

Kunderna köper i första hand de nya konversationerna. Det här är logiken
bakom fliken Leads › Konversationer (app/api/leads_konversationer.py): vilket
steg en konversation står i, vad som ska göras, vilka påståenden i ett
svarsutkast en människa måste kontrollera, och vilka mejl som skickats
utanför Snajp men syns i prospektets citat.

## Steget

Fem steg: Svarat, Möte bokat, Återkom (med datum), Ej intresserad och
Kontakta inte. Tre av dem är prospektets status (meeting, lost, suppressed),
som Skickat, samtalslistorna och mätningen redan läser, så att ett möte som
bokas här räknas som Möte överallt (Telecom Buddy stod på "Möte 0" fast mötet
var bokat). Svarat och Återkom har samma status ('replied') och skiljs av
trådens återkomdatum, Iris klassning ('aterkom') och det steg en människa
senast valt (outreach_threads.steg, migration 149). Ett nytt svar nollar det
manuella valet: då är det nya svaret det som gäller.

## Händelserna

Varje händelse loggas genom `logga`, som aldrig kastar: en händelselogg som
inte går att skriva får inte fälla svarshanteringen eller ett utskick.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

logger = logging.getLogger("snajp-support.leads")

STOCKHOLM = ZoneInfo("Europe/Stockholm")

#: Stegen, i den ordning de visas.
STEG = ("svarat", "mote", "aterkom", "ej_intresserad", "kontakta_inte")

#: Prospektets status för varje steg.
STATUS_FOR_STEG = {
    "svarat": "replied",
    "mote": "meeting",
    "aterkom": "replied",
    "ej_intresserad": "lost",
    "kontakta_inte": "suppressed",
}

#: Steg som avslutar leadet: inget som väntar på att skickas får gå ut efter beslutet.
AVSLUTANDE = frozenset({"mote", "ej_intresserad", "kontakta_inte"})

#: Händelser som också är notiser i Snajp.
NOTISTYPER = frozenset({"svar", "utkast", "mote", "overlamnat"})

#: En generering som inte rapporterat på så här länge räknas som avbruten.
GENERERING_TIDSGRANS = timedelta(minutes=10)


def steg(rad: dict[str, Any]) -> str:
    """Konversationens steg ur prospektets status, trådens manuella steg,
    återkomdatumet och svarsklassen."""
    status = rad.get("status")
    if status in ("meeting", "won"):
        return "mote"
    if status == "suppressed":
        return "kontakta_inte"
    if status == "lost":
        return "ej_intresserad"
    if rad.get("steg") == "svarat":
        return "svarat"
    if rad.get("steg") == "aterkom" or rad.get("aterkom_datum") or rad.get("svarsklass") == "aterkom":
        return "aterkom"
    return "svarat"


def _datum(varde: Any) -> date | None:
    if varde in (None, ""):
        return None
    if isinstance(varde, datetime):
        return varde.date()
    if isinstance(varde, date):
        return varde
    return date.fromisoformat(str(varde)[:10])


def aterkom_forfallet(rad: dict[str, Any], idag: date) -> bool:
    datum = _datum(rad.get("aterkom_datum"))
    return steg(rad) == "aterkom" and datum is not None and datum <= idag


def att_gora(rad: dict[str, Any], idag: date) -> bool:
    """Behöver konversationen en människa nu? Ett oläst svar eller en oläst
    händelse, ett utkast som väntar, eller ett återkomdatum som infallit."""
    if steg(rad) in ("ej_intresserad", "kontakta_inte"):
        return bool(rad.get("olasta"))
    return bool(rad.get("olasta") or rad.get("utkast_id") or aterkom_forfallet(rad, idag))


# -- Påstådda handlingar i ett utkast ------------------------------------------

#: Meningar där utkastet påstår att något redan är gjort. Iris kan skriva
#: "jag har skickat en inbjudan" när prospektet bett om en, utan att någon
#: skickat något (Telecom Buddy 2026-11-18). En människa ska kontrollera att
#: handlingen är gjord innan ett sådant svar går ut.
_HANDLING = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(?:jag|vi)\s+har\s+(?:nu\s+|redan\s+|precis\s+|just\s+)?"
        r"(?:skickat|bokat|lagt\s+in|lagt\s+till|bifogat|mejlat|ringt|uppdaterat|ordnat|fixat|skapat|"
        r"registrerat|reserverat|bekräftat|delat|vidarebefordrat|aktiverat|öppnat)\b[^.!?\n]*",
        # Utan subjekt ("Perfekt, har skickat en inbjudan"). Överlappet med
        # mönstret ovan rensas i handlingspastaenden.
        r"\bhar\s+(?:nu\s+|redan\s+)?(?:skickat|bokat|bifogat|lagt\s+in)\b[^.!?\n]*",
        r"\b(?:jag|vi)\s+(?:skickade|bokade|bifogade|mejlade|ringde)\b[^.!?\n]*",
        r"\b(?:inbjudan|kalenderinbjudan|bokningen|offerten|avtalet|kontot|länken)\s+(?:är|har\s+blivit)\s+"
        r"(?:nu\s+)?(?:skickad|skickat|bokad|bokat|bekräftad|skapad|skapat|aktiverad|aktiverat)\b[^.!?\n]*",
        r"\b(?:bifogar|bifogat|se\s+bifogad[e]?|i\s+bilagan|bifogad\s+fil)\b[^.!?\n]*",
        r"\b(?:I|we)(?:'ve|\s+have)\s+(?:just\s+|already\s+)?"
        r"(?:sent|booked|attached|scheduled|added|created|shared|forwarded|confirmed|set\s+up)\b[^.!?\n]*",
        r"\b(?:please\s+find\s+attached|attached\s+(?:is|you'll\s+find))\b[^.!?\n]*",
    )
]


def handlingspastaenden(text: str) -> list[str]:
    """Meningarna där texten påstår att en handling redan är gjord, i den
    ordning de står. Tom lista = inget att kontrollera."""
    traffar: list[tuple[int, str]] = []
    for monster in _HANDLING:
        for m in monster.finditer(text or ""):
            fras = " ".join(m.group(0).split()).strip(" ,;:")
            if fras and not any(start <= m.start() < start + len(f) for start, f in traffar):
                traffar.append((m.start(), fras[:160]))
    return [fras for _, fras in sorted(traffar)]


_MOTESORD = re.compile(
    r"\b(?:inbjudan|kalenderinbjudan|mötesinbjudan|bokat|bokade|bokningen|teams-?länk|meet-?länk|zoom-?länk|"
    r"invite|invitation|booked|calendar)\b",
    re.IGNORECASE,
)


def ser_ut_som_bokat_mote(texter: list[str]) -> bool:
    """Säger någon av texterna att ett möte bokats eller en inbjudan gått ut?
    Bara ett förslag till människan, aldrig ett stegbyte."""
    return any(_MOTESORD.search(t or "") for t in texter)


# -- Mejl utanför Snajp, ur citaten --------------------------------------------

#: Citathuvud med en adress: "18 nov. 2026 kl. 12:56 skrev Sebastian Bergman
#: <sebastian@snajp.se>:", "Den tis 18 nov. 2026 kl 12:56 skrev …:" och
#: "On Tue, Nov 18, 2026 at 12:56 PM Name <a@b.se> wrote:".
_HUVUD = re.compile(
    r"^[> \t]*(?P<rad>[^\n]*?<(?P<epost>[^<>\s@]+@[^<>\s]+)>[^\n]*?)[ \t]*$",
    re.MULTILINE,
)
_SKREV = re.compile(r"\b(?:skrev|wrote)\b", re.IGNORECASE)

_MANADER = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "maj": 5, "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "okt": 10, "oct": 10, "nov": 11, "dec": 12,
}


def _citattid(rad: str) -> datetime | None:
    """Tiden i ett citathuvud, svensk tid, eller None."""
    if m := re.search(r"(\d{4})-(\d{2})-(\d{2})\D{1,6}(\d{1,2})[:.](\d{2})", rad):
        a, mo, d, h, mi = map(int, m.groups())
    elif m := re.search(
        r"(\d{1,2})\s+([a-zåäö]{3})[a-zåäö]*\.?\s+(\d{4})\D{1,8}?(\d{1,2})[:.](\d{2})\s*(am|pm)?", rad, re.IGNORECASE
    ):
        d, man, a, h, mi, ampm = m.groups()
        mo = _MANADER.get(man.lower())
        if mo is None:
            return None
        d, a, h, mi = int(d), int(a), int(h), int(mi)
        h = h % 12 + (12 if ampm and ampm.lower() == "pm" else 0) if ampm else h
    elif m := re.search(
        r"\b([a-z]{3})[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})\D{1,8}?(\d{1,2})[:.](\d{2})\s*(am|pm)?", rad, re.IGNORECASE
    ):
        man, d, a, h, mi, ampm = m.groups()
        mo = _MANADER.get(man.lower())
        if mo is None:
            return None
        d, a, h, mi = int(d), int(a), int(h), int(mi)
        h = h % 12 + (12 if ampm and ampm.lower() == "pm" else 0) if ampm else h
    else:
        return None
    try:
        return datetime(a, mo, d, h, mi, tzinfo=STOCKHOLM).astimezone(timezone.utc)
    except ValueError:
        return None


def _normalisera(text: str) -> str:
    return re.sub(r"[^a-zåäö0-9]+", "", (text or "").lower())


def _utan_citattecken(text: str) -> str:
    return "\n".join(re.sub(r"^[> \t]*>[ ]?", "", rad) for rad in text.splitlines()).strip()


def _doman(epost: str) -> str:
    return epost.rsplit("@", 1)[-1].lower() if "@" in epost else ""


#: Domäner som delas av många: där räcker inte domänen för att säga vems sida
#: en adress hör till.
_ALLMANNA = frozenset({
    "gmail.com", "hotmail.com", "hotmail.se", "outlook.com", "outlook.se", "live.se", "live.com",
    "yahoo.com", "yahoo.se", "icloud.com", "me.com", "telia.com", "bredband.net", "spray.se",
})


def externa_ur_citat(
    meddelanden: list[dict[str, Any]], *, prospekt_epost: str | None
) -> list[dict[str, Any]]:
    """Mejl i prospektets citat som inte skickades via Snajp.

    Ett svar citerar oftast hela tråden. Står där ett mejl från en adress som
    inte är prospektets (sebastian@snajp.se, som svarade från sin Gmail) och
    vars text inte är något av våra skickade mejl, har det skickats utanför
    Snajp, och det är en del av konversationen. Varje sådant mejl tas med en
    gång, med tiden ur citathuvudet (annars just före svaret som citerar det).
    Inget skrivs; det här läses ur texten varje gång tråden visas."""
    prospekt = (prospekt_epost or "").strip().lower()
    prospektdoman = _doman(prospekt)
    vara = [
        _normalisera(m.get("body") or "")
        for m in meddelanden
        if m.get("direction") == "outbound" and m.get("sent_at")
    ]
    hittade: dict[str, dict[str, Any]] = {}
    for m in meddelanden:
        if m.get("direction") != "inbound":
            continue
        body = re.sub(r"<\s*\n[> \t]*", "<", m.get("body") or "")
        huvuden = [h for h in _HUVUD.finditer(body) if _SKREV.search(h.group("rad")) and h.group("rad").rstrip().endswith(":")]
        for i, huvud in enumerate(huvuden):
            epost = huvud.group("epost").strip().lower()
            if epost == prospekt or (prospektdoman and prospektdoman not in _ALLMANNA and _doman(epost) == prospektdoman):
                continue
            slut = huvuden[i + 1].start() if i + 1 < len(huvuden) else len(body)
            text = _utan_citattecken(body[huvud.end():slut])
            # Gmails nästa citat utan adress ("… skrev Snajp:") avslutar också.
            text = re.split(r"\n[^\n]*\b(?:skrev|wrote)\b[^\n]*:\s*\n", text, maxsplit=1)[0].strip()
            nyckel = _normalisera(text)[:80]
            if len(nyckel) < 4 or nyckel in hittade:
                continue
            if any(nyckel[:60] in v for v in vara):
                continue  # ett av våra egna utskick, citerat
            tid = _citattid(huvud.group("rad"))
            hittade[nyckel] = {
                "nyckel": nyckel,
                "kalla": "citat",
                "riktning": "outbound",
                "avsandare": epost,
                "text": text[:4000],
                "tid": (tid or _minus_en_sekund(m.get("sent_at") or m.get("created_at"))),
                "citerat_i": m.get("id"),
                "tid_ur_citat": tid is not None,
            }
    return sorted(hittade.values(), key=lambda e: _som_tid(e["tid"]))


def _som_tid(varde: Any) -> datetime:
    if isinstance(varde, datetime):
        return varde if varde.tzinfo else varde.replace(tzinfo=timezone.utc)
    try:
        t = datetime.fromisoformat(str(varde))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _minus_en_sekund(varde: Any) -> datetime:
    return _som_tid(varde) - timedelta(seconds=1)


# -- Loggning och stegbyten -------------------------------------------------------


async def logga(
    storage: Any,
    tenant_id: str,
    *,
    prospect_id: str | None,
    thread_id: str | None,
    typ: str,
    kalla: str = "kod",
    detalj: dict[str, Any] | None = None,
    last: bool = False,
) -> None:
    """En händelse i konversationens logg. Kastar aldrig."""
    if not prospect_id:
        return
    try:
        await storage.logga_handelse(
            tenant_id,
            prospect_id=str(prospect_id),
            thread_id=str(thread_id) if thread_id else None,
            typ=typ,
            kalla=kalla,
            detalj=detalj,
            notis=typ in NOTISTYPER,
            last=last,
        )
    except Exception:  # noqa: BLE001 — loggen får aldrig fälla flödet den beskriver
        logger.exception("Kunde inte logga händelsen %s för tråd %s", typ, thread_id)


async def satt_steg(
    storage: Any,
    tenant_id: str,
    *,
    thread: dict[str, Any],
    prospect: dict[str, Any],
    nytt: str,
    aterkom_datum: date | None = None,
    kalla: str = "manuell",
) -> dict[str, Any]:
    """Flyttar konversationen till ett steg och verkställer det: prospektets
    status, återkomdatumet, spärren för Kontakta inte, och för de avslutande
    stegen att inget väntande går ut. Ett väntande svarsutkast kasseras då,
    synligt och går att återställa i tråden. Returnerar {steg, kasserat}."""
    if nytt not in STEG:
        raise ValueError(f"Okänt steg: {nytt}")
    if nytt == "aterkom" and aterkom_datum is None:
        raise ValueError("Återkom kräver ett datum.")
    thread_id = str(thread["id"])
    prospect_id = str(prospect["id"])
    fore = steg({**thread, "status": prospect.get("status")})

    kasserat = None
    if nytt in AVSLUTANDE:
        vantande = await storage.get_pending_outreach_message(tenant_id, thread_id)
        await storage.cancel_pending_sends(tenant_id, thread_id)
        if vantande:
            kasserat = str(vantande["id"])
            await logga(
                storage, tenant_id, prospect_id=prospect_id, thread_id=thread_id, typ="utkast_kasserat",
                kalla=kalla, detalj={"message_id": kasserat, "orsak": f"steg:{nytt}"},
            )
    if nytt == "kontakta_inte" and prospect.get("contact_email"):
        await storage.add_suppression(
            tenant_id, email=prospect["contact_email"], reason="kontakta inte (konversation)"
        )

    status = STATUS_FOR_STEG[nytt]
    if not (nytt == "mote" and prospect.get("status") == "won"):
        await storage.update_prospect(tenant_id, prospect_id, status=status, status_kalla=kalla)
    await storage.satt_trad_steg(
        tenant_id, thread_id, steg=nytt, aterkom_datum=aterkom_datum if nytt == "aterkom" else None
    )
    await logga(
        storage, tenant_id, prospect_id=prospect_id, thread_id=thread_id, typ="steg", kalla=kalla,
        detalj={"fran": fore, "till": nytt, "aterkom_datum": aterkom_datum.isoformat() if aterkom_datum else None},
    )
    if nytt == "mote" and fore != "mote":
        # Notisen till resten av arbetsytan; den som bokade har redan sett det.
        await logga(
            storage, tenant_id, prospect_id=prospect_id, thread_id=thread_id, typ="mote", kalla=kalla,
            last=kalla == "manuell",
        )
    return {"steg": nytt, "kasserat": kasserat}


def generering(handelser: list[dict[str, Any]], *, nu: datetime) -> dict[str, Any]:
    """Läget för en omskrivning av svarsutkastet, ur händelseloggen: pågår
    den, och hur gick den senaste? Överlever en omladdning, eftersom det är
    loggen och inte webbläsaren som minns."""
    startad = next((h for h in reversed(handelser) if h.get("typ") == "generering_startad"), None)
    if startad is None:
        return {"pagar": False, "fel": None, "startad_at": None}
    t0 = _som_tid(startad.get("created_at"))
    efter = [
        h for h in handelser
        if h.get("typ") in ("utkast", "generering_fel") and _som_tid(h.get("created_at")) >= t0
    ]
    if efter:
        fel = efter[-1] if efter[-1].get("typ") == "generering_fel" else None
        return {
            "pagar": False,
            "fel": (fel.get("detalj") or {}).get("fel") if fel else None,
            "startad_at": startad.get("created_at"),
        }
    if nu - t0 > GENERERING_TIDSGRANS:
        return {"pagar": False, "fel": "Omskrivningen avbröts innan den blev klar. Försök igen.", "startad_at": startad.get("created_at")}
    return {"pagar": True, "fel": None, "startad_at": startad.get("created_at")}
