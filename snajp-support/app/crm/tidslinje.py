"""Postens tidslinje: det som hänt i CRM:et och i resten av Snajp, på ett ställe.

Bolagets, personens och affärens egna ändringar, det arbete som knutits till
posten i CRM:et (anteckningar, aktiviteter, uppgifter och, på bolaget och
personen, affärerna), leadsflödet hos Iris och supportens ärenden.

Tidslinjen KOMPONERAS vid läsning ur källorna. Ingenting kopieras in i CRM:et:
ett mejl ligger kvar i konversationen, ett samtal i samtalsloggen och ett
ärende hos supporten, och gallras där det bor. Samma princip som leadets egen
tidslinje (app/api/leads_suite.py) och migration 086.

## Hur posten hittar sina källor

Ett bolag i CRM:et är samma bolag som ett lead när de delar nyckel: prospektets
`foretagsnyckel` (organisationsnumrets tio siffror, annars e-postdomänen) mot
bolagets organisationsnummer, eller mot bolagets domän när bolaget saknar
nummer. gmail.com, telia.com och liknande är aldrig en bolagsdomän. En person
hittar sina leads på exakt e-postadress.

Supportärenden knyts på exakt e-postadress: personens egen på personens
tidslinje, och bolagets personers adresser på bolagets. Aldrig på domän. Det
hade lagt en privatpersons ärende på ett bolag som råkar dela e-postleverantör.

## Vad som aldrig följer med

- Webbplatsbedömningen. Prospektet läses med en uttrycklig kolumnlista, så att
  ett nytt hemligt fält inte kan komma med av misstag.
- Osända och kasserade utkast. De är arbete, inte historik: bara det som
  faktiskt gått ut eller kommit in står på tidslinjen.
- Testärenden och exempel- och testprospekt.
- Supportens meddelandetext. Ärendet står med ämne, kanal och läge; innehållet
  läses i ärendet.

`med_text=False` (en integrations nyckel) tar dessutom bort utdragen ur mejl,
anteckningar och samtal: integrationen får veta att något hänt och var det
finns, inte vad som skrevs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..leads import upptagna
from . import falt, handelser, lagring

MAX_PROSPEKT = 20
MAX_PERSONER = 50
#: Hur många anteckningar, aktiviteter, uppgifter och affärer som läses per post och slag.
MAX_ARBETE = 200
UTDRAG = 280

#: Kolumnen som knyter en anteckning, aktivitet eller uppgift till posten.
_KOPPLING = {"bolag": "bolag_id", "person": "person_id", "affar": "affar_id"}

#: Leadshändelser som hör hemma på postens tidslinje. Resten (utkast och
#: genereringar) är arbetsdetaljer som visas i konversationen.
_LEADSHANDELSER = {"steg": "steg", "mote": "mote_bokat", "overlamnat": "overlamnat"}


def _tid(varde: Any) -> datetime:
    tid = varde if isinstance(varde, datetime) else datetime.fromisoformat(str(varde).replace("Z", "+00:00"))
    return tid if tid.tzinfo else tid.replace(tzinfo=timezone.utc)


def _post(nyckel: str, typ: str, tid: Any, kalla: str, *, rubrik: str | None = None, text: str | None = None,
          lank: tuple[str, Any] | None = None, **detalj: Any) -> dict[str, Any] | None:
    if not tid:
        return None
    return {"nyckel": nyckel, "typ": typ, "tid": _tid(tid).isoformat(), "kalla": kalla,
            "rubrik": rubrik or None, "text": (text or "")[:UTDRAG] or None,
            "lank": {"typ": lank[0], "id": str(lank[1])} if lank and lank[1] else None,
            "detalj": {k: v for k, v in detalj.items() if v is not None}}


# -- Prospekten som hör till posten -----------------------------------------


def _minnesnyckel(prospekt: dict[str, Any]) -> str | None:
    """Minneslagrets motsvarighet till den genererade kolumnen foretagsnyckel."""
    orgnr = upptagna.orgnr_nyckel(prospekt.get("orgnr"))
    if orgnr:
        return orgnr.split(":", 1)[1]
    adress = str(prospekt.get("contact_email") or "")
    return adress.rsplit("@", 1)[1].lower() if "@" in adress else None


#: Det enda som läses ur ett prospekt. Uttryckligt, så att ett nytt hemligt
#: fält på prospektet inte kan följa med av misstag.
PROSPEKTFALT = ("id", "company_name", "contact_name", "contact_email", "orgnr", "status", "origin", "created_at")


def nycklar_for_bolag(bolag: dict[str, Any]) -> list[str]:
    """Nyckeln bolaget delar med sina leads: organisationsnumret, eller domänen
    när numret saknas och domänen inte är en e-postleverantörs."""
    if bolag.get("orgnr_nyckel"):
        return [bolag["orgnr_nyckel"]]
    if bolag.get("doman") and not falt.doman_ar_privat(bolag["doman"]):
        return [bolag["doman"]]
    return []


async def prospekt_for_bolag(storage: Any, tenant_id: str, bolag: dict[str, Any]) -> list[dict[str, Any]]:
    return await _prospekt(storage, tenant_id, nycklar=nycklar_for_bolag(bolag), adresser=[])


async def _prospekt(storage: Any, tenant_id: str, *, nycklar: list[str], adresser: list[str]) -> list[dict[str, Any]]:
    nycklar = sorted({n for n in nycklar if n})
    adresser = sorted({a.lower() for a in adresser if a})
    if not nycklar and not adresser:
        return []
    if lagring._ar_postgres(storage):
        try:
            async with storage._scoped(tenant_id) as conn:
                rader = await conn.fetch(
                    # Uttrycklig kolumnlista: bedömningen av bolagets sajt ska aldrig kunna följa med.
f"select {', '.join(PROSPEKTFALT)} from prospects "
                    "where tenant_id = $1::text::uuid and coalesce(origin, '') not in ('example', 'test') "
                    "and (foretagsnyckel = any($2::text[]) or lower(contact_email) = any($3::text[])) "
                    f"order by created_at limit {MAX_PROSPEKT}", tenant_id, nycklar, adresser)
        except Exception as fel:
            if lagring._saknar_tabell(fel):
                return []
            raise
        return [{**dict(r), "id": str(r["id"])} for r in rader]
    ut = []
    for p in getattr(storage, "prospects", {}).get(tenant_id, []):
        if p.get("origin") in ("example", "test"):
            continue
        if _minnesnyckel(p) in nycklar or str(p.get("contact_email") or "").lower() in adresser:
            ut.append({k: p.get(k) for k in PROSPEKTFALT})
    return sorted(ut, key=lambda p: str(p.get("created_at") or ""))[:MAX_PROSPEKT]


async def _leads(storage: Any, tenant_id: str, prospekt: dict[str, Any]) -> list[dict[str, Any] | None]:
    pid = str(prospekt["id"])
    ut: list[dict[str, Any] | None] = [
        _post(f"p:{pid}", "lead_skapad", prospekt.get("created_at"), "iris", rubrik=prospekt.get("company_name"),
              lank=("lead", pid), ursprung=prospekt.get("origin"))]
    for rad in await storage.list_status_logg(tenant_id, prospect_id=pid):
        ut.append(_post(f"st:{rad['id']}", "status", rad["created_at"], "iris", lank=("lead", pid),
                        fran=rad.get("fran"), till=rad.get("till")))
    trad = await storage.find_outreach_thread(tenant_id, prospect_id=pid)
    if trad:
        skickade = 0
        for m in await storage.list_outreach_messages(tenant_id, str(trad["id"])):
            if m.get("direction") == "inbound":
                ut.append(_post(f"msg:{m['id']}", "svar", m.get("sent_at") or m.get("created_at"), "iris",
                                rubrik=prospekt.get("contact_name"), text=m.get("body"),
                                lank=("konversation", trad["id"]), klass=m.get("svarsklass")))
            elif m.get("sent_at") and not m.get("kasserad_at"):
                # Bara det som faktiskt gått ut: ett väntande utkast har created_at men ingen sändtid.
                ut.append(_post(f"msg:{m['id']}", "uppfoljning_skickad" if skickade else "mejl_skickat",
                                m["sent_at"], "iris", rubrik=m.get("subject"), text=m.get("body"),
                                lank=("konversation", trad["id"]), nummer=skickade or None))
                skickade += 1
        for h in await storage.list_handelser(tenant_id, thread_id=str(trad["id"])):
            typ = _LEADSHANDELSER.get(h.get("typ"))
            if typ:
                detalj = h.get("detalj") or {}
                ut.append(_post(f"h:{h['id']}", typ, h["created_at"], "iris", lank=("konversation", trad["id"]),
                                till=detalj.get("till"), fran=detalj.get("fran")))
    for rad in await storage.list_lead_samtal(tenant_id, prospect_id=pid):
        ut.append(_post(f"samtal:{rad['id']}", "samtal", rad["created_at"], "iris", text=rad.get("anteckning"),
                        lank=("lead", pid), utfall=rad.get("utfall"),
                        aterkom=str(rad["aterkom_datum"]) if rad.get("aterkom_datum") else None))
    for rad in await storage.list_lead_notes(tenant_id, pid):
        ut.append(_post(f"ant:{rad['id']}", "anteckning", rad["created_at"], "iris", text=rad.get("text"),
                        lank=("lead", pid)))
    for rad in await storage.list_lead_tasks(tenant_id, prospect_id=pid):
        ut.append(_post(f"upp:{rad['id']}", "uppgift", rad["created_at"], "iris", rubrik=rad.get("titel"),
                        lank=("lead", pid), klar=bool(rad.get("klar")),
                        forfaller=str(rad["forfaller"]) if rad.get("forfaller") else None))
    return ut


# -- Supportärendena --------------------------------------------------------


async def _arenden(storage: Any, tenant_id: str, adresser: list[str]) -> list[dict[str, Any] | None]:
    ut: list[dict[str, Any] | None] = []
    sedda: set[str] = set()
    for adress in sorted({a.lower() for a in adresser if a})[:MAX_PERSONER]:
        kund = await storage.find_customer(tenant_id, email=adress)
        if not kund or str(kund["id"]) in sedda:
            continue
        sedda.add(str(kund["id"]))
        for arende in await storage.get_customer_history(tenant_id, str(kund["id"])):
            if arende.get("is_test"):
                continue
            ut.append(_post(f"t:{arende['id']}", "supportarende", arende.get("created_at"), "support",
                            rubrik=arende.get("subject"), lank=("arende", arende["id"]),
                            kanal=arende.get("channel"), kategori=arende.get("category"),
                            status=arende.get("status"), prioritet=arende.get("priority")))
    return ut


# -- CRM:ets egna händelser -------------------------------------------------


async def _egna(storage: Any, tenant_id: str, objekt: str, post_id: str) -> list[dict[str, Any] | None]:
    return [_post(f"crm:{h['id']}", f"post_{h['typ']}", h["created_at"], "crm", lank=None,
                  falt=h.get("falt") or None, via=h.get("kalla"), aktor=h.get("aktor"))
            for h in await handelser.for_post(storage, tenant_id, objekt, post_id)]


async def _arbete(storage: Any, tenant_id: str, objekt: str, post_id: str) -> list[dict[str, Any] | None]:
    """Det som knutits till posten i CRM:et: anteckningar, aktiviteter och
    uppgifter, och på bolaget och personen deras affärer. Raderade står inte
    med: papperskorgen är inte historik."""
    kolumn = _KOPPLING[objekt]

    async def rader(tabell: str) -> list[dict[str, Any]]:
        return await lagring._valj(storage, tenant_id, tabell, lika={kolumn: post_id}, levande=True,
                                   fallande=True, limit=MAX_ARBETE)

    ut: list[dict[str, Any] | None] = []
    for rad in await rader("crm_anteckningar"):
        ut.append(_post(f"crmant:{rad['id']}", "anteckning", rad["created_at"], "crm", rubrik=rad.get("titel"),
                        text=rad.get("text"), lank=("anteckning", rad["id"]), fast=True if rad.get("fast") else None,
                        forfattare=rad.get("forfattare")))
    for rad in await rader("crm_aktiviteter"):
        ut.append(_post(f"crmakt:{rad['id']}", "aktivitet", rad.get("tid") or rad["created_at"], "crm",
                        rubrik=rad.get("rubrik"), text=rad.get("text"), lank=("aktivitet", rad["id"]),
                        slag=rad.get("typ"), resultat=rad.get("utfall"), minuter=rad.get("varaktighet_min"),
                        ansvarig=rad.get("ansvarig")))
    for rad in await rader("crm_uppgifter"):
        ut.append(_post(f"crmupp:{rad['id']}", "uppgift", rad["created_at"], "crm", rubrik=rad.get("titel"),
                        text=rad.get("beskrivning"), lank=("uppgift", rad["id"]), klar=rad.get("status") == "klar",
                        forfaller=_tid(rad["forfaller_at"]).isoformat() if rad.get("forfaller_at") else None,
                        ansvarig=rad.get("ansvarig")))
    if objekt != "affar":
        for rad in await rader("crm_affarer"):
            ut.append(_post(f"crmaff:{rad['id']}", "affar_skapad", rad["created_at"], "crm", rubrik=rad.get("namn"),
                            lank=("affar", rad["id"]), belopp=rad.get("belopp"), valuta=rad.get("valuta")))
            if rad.get("avslutad_at"):
                ut.append(_post(f"crmaff:{rad['id']}:slut", "affar_avslutad", rad["avslutad_at"], "crm",
                                rubrik=rad.get("namn"), lank=("affar", rad["id"]), belopp=rad.get("belopp"),
                                valuta=rad.get("valuta"), forlustorsak=rad.get("forlustorsak")))
    return ut


# -- Tidslinjen -------------------------------------------------------------


async def for_bolag(storage: Any, tenant_id: str, bolag: dict[str, Any], *, limit: int = 200,
                    med_text: bool = True) -> list[dict[str, Any]]:
    """Bolagets tidslinje, nyast först."""
    personer = await lagring._valj(storage, tenant_id, "crm_personer", lika={"bolag_id": bolag["id"]},
                                   levande=True, limit=MAX_PERSONER)
    adresser = [p["epost"] for p in personer if p.get("epost")] + ([bolag["epost"]] if bolag.get("epost") else [])
    poster = await _egna(storage, tenant_id, "bolag", bolag["id"])
    poster += await _arbete(storage, tenant_id, "bolag", bolag["id"])
    for prospekt in await prospekt_for_bolag(storage, tenant_id, bolag):
        poster += await _leads(storage, tenant_id, prospekt)
    poster += await _arenden(storage, tenant_id, adresser)
    return _ordna(poster, limit, med_text)


async def for_person(storage: Any, tenant_id: str, person: dict[str, Any], *, limit: int = 200,
                     med_text: bool = True) -> list[dict[str, Any]]:
    """Personens tidslinje, nyast först."""
    adresser = [person["epost"]] if person.get("epost") else []
    poster = await _egna(storage, tenant_id, "person", person["id"])
    poster += await _arbete(storage, tenant_id, "person", person["id"])
    for prospekt in await _prospekt(storage, tenant_id, nycklar=[], adresser=adresser):
        poster += await _leads(storage, tenant_id, prospekt)
    poster += await _arenden(storage, tenant_id, adresser)
    return _ordna(poster, limit, med_text)


async def for_affar(storage: Any, tenant_id: str, affar: dict[str, Any], *, limit: int = 200,
                    med_text: bool = True) -> list[dict[str, Any]]:
    """Affärens tidslinje, nyast först: dess egna ändringar och det arbete som
    knutits till den. Leads och ärenden hör till bolaget och personen."""
    poster = await _egna(storage, tenant_id, "affar", affar["id"])
    poster += await _arbete(storage, tenant_id, "affar", affar["id"])
    return _ordna(poster, limit, med_text)


def _ordna(poster: list[dict[str, Any] | None], limit: int, med_text: bool) -> list[dict[str, Any]]:
    unika: dict[str, dict[str, Any]] = {}
    for post in poster:
        if post is not None:
            unika.setdefault(post["nyckel"], post)
    ut = sorted(unika.values(), key=lambda p: (p["tid"], p["nyckel"]), reverse=True)[: max(1, min(limit, 500))]
    if not med_text:
        ut = [{**p, "text": None} for p in ut]
    return ut
