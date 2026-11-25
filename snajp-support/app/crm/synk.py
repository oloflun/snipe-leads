"""Kundsynken in: en sats poster från ett källsystem blir bolag och personer.

Tre saker avgör kvaliteten, och de står här i ordning.

## 1. Vilken post är det?

    källans id  →  organisationsnummer  →  domän  →  namn

Källans id (crm_externa_id) är det säkra: samma post i HubSpot är samma post
hos oss, också efter ett namnbyte. Organisationsnumret är nästa: det är unikt
per kund i databasen, så två källor som beskriver samma bolag hamnar på samma
rad. Domän och namn används bara för poster UTAN organisationsnummer, och bara
när exakt en post matchar. Två "Bygg AB" slås aldrig ihop på namnet.
gmail.com, telia.com och liknande är aldrig en bolagsdomän.

## 2. Vad vinner när källan och Snajp säger olika?

Avgörs fält för fält av anslutningens konfliktregel:

- `kallan_vinner`  källans värde gäller (standard: källan är kundens register).
- `snajp_vinner`   ett fält någon ändrat för hand i Snajp står kvar.
- `nyast_vinner`   det som ändrades senast gäller. Kräver att källan skickar
                   en ändringstid; annars räknas handändringen som nyast.

Ett fält källan inte skickar rörs aldrig: en sats med bara namn och telefon
tömmer inte adressen.

## 3. Vad händer med det som försvunnit ur källan?

Bara en FULL synk kan veta det. När den avslutas jämförs källans poster med
dem körningen nämnde, och anslutningens `saknade` avgör: `behall`,
`tidigare_kund` (kunden blir tidigare kund) eller `ta_bort` (mjuk radering).
En full synk utan en enda post gör ingenting: ett tomt svar från källan är
oftare ett fel än en tömd kundstock.

Synken hoppar över fält som inte går att tolka, inte posten: en kund med ett
felskrivet telefonnummer ska fortfarande bli en kund. Felen sparas på
körningen (crm_synkkorningar.fel) så att de går att rätta i källan.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from . import adaptrar, falt, lagring

#: Styr och härledda fält som inte jämförs mot källan.
_HARLEDDA = ("namnnyckel", "orgnr_nyckel", "enskild_firma", "doman")
_HOR_IHOP = {"orgnr": ("orgnr_nyckel", "enskild_firma"), "webbplats": ("doman",), "namn": ("namnnyckel",)}

#: Mappning där källans nycklar ÄR målfälten. För poster som redan har
#: CRM:ets egna fältnamn (API:t och appen), så att samma kontroller gäller.
IDENTITET = {
    objekt: {**{f: f for f in adaptrar.MALFALT[objekt]}, "externt_id": "externt_id",
             "uppdaterad": "uppdaterad", "raderad": "raderad"}
    for objekt in adaptrar.OBJEKT
}


@dataclass
class Utfall:
    status: str  # skapad | uppdaterad | oforandrad | hoppad | konflikt | raderad
    index: int
    id: str | None = None
    externt_id: str | None = None
    orsak: str | None = None
    #: Fält där Snajps värde stod kvar enligt konfliktregeln.
    behallna: list[str] = field(default_factory=list)
    fel: list[dict[str, Any]] = field(default_factory=list)

    def som_dict(self) -> dict[str, Any]:
        ut = {"index": self.index, "status": self.status, "id": self.id, "externt_id": self.externt_id}
        if self.orsak:
            ut["orsak"] = self.orsak
        if self.behallna:
            ut["behallna_falt"] = self.behallna
        if self.fel:
            ut["faltfel"] = self.fel
        return ut


def _hash(m: adaptrar.Mappad) -> str:
    stoff = json.dumps([m.falt, m.extra, m.raderad], sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(stoff.encode()).hexdigest()


def _andringar(
    post: dict[str, Any], m: adaptrar.Mappad, regel: str
) -> tuple[dict[str, Any], list[str]]:
    """(fält att skriva, fält där Snajps värde stod kvar)."""
    manuellt: dict[str, str] = dict(post.get("manuellt_andrade") or {})
    skriv: dict[str, Any] = {}
    behallna: list[str] = []
    for namn, nytt in m.falt.items():
        if namn in _HARLEDDA or namn not in lagring.TABELLER[_tabell(post)] or post.get(namn) == nytt:
            continue
        hand = manuellt.get(namn)
        if hand and regel == "snajp_vinner":
            behallna.append(namn)
            continue
        if hand and regel == "nyast_vinner" and (not m.uppdaterad or lagring._tid(hand) >= lagring._tid(m.uppdaterad)):
            behallna.append(namn)
            continue
        skriv[namn] = nytt
        for foljer in _HOR_IHOP.get(namn, ()):
            if foljer in m.falt:
                skriv[foljer] = m.falt[foljer]
        manuellt.pop(namn, None)
    extra = {**(post.get("extra") or {}), **m.extra}
    if extra != (post.get("extra") or {}):
        skriv["extra"] = extra
    if skriv and manuellt != (post.get("manuellt_andrade") or {}):
        skriv["manuellt_andrade"] = manuellt
    return skriv, behallna


def _tabell(post: dict[str, Any]) -> str:
    return "crm_bolag" if "namnnyckel" in post else "crm_personer"


async def _sparrar(storage: Any, tenant_id: str) -> tuple[set[str], set[str]]:
    """(avregistrerade adresser hos kunden, adresser med begränsad behandling).
    Kastar aldrig: utan underlag synkas posten, och utskicken har sin egen vakt."""
    try:
        return await storage.list_suppressions(tenant_id), await storage.list_begransade(tenant_id)
    except Exception:  # noqa: BLE001
        return set(), set()


async def synka_sats(
    storage: Any,
    tenant_id: str,
    anslutning: dict[str, Any],
    korning: dict[str, Any],
    objekt: str,
    poster: list[Any],
    *,
    mappning: dict[str, dict[str, Any]] | None = None,
    torrkorning: bool = False,
) -> dict[str, Any]:
    """Synkar en sats och lägger utfallet på körningen. Vid `torrkorning`
    skrivs ingenting: svaret visar vad som SKULLE hända, för att prova en
    mappning."""
    regler = mappning or adaptrar.gallande_mappning(anslutning["system"], anslutning.get("mappning"))
    mappade = [adaptrar.mappa(p, objekt, regler) for p in poster]
    avregistrerade, begransade = await _sparrar(storage, tenant_id)

    externa = await lagring.externa_for_kalla(
        storage, tenant_id, anslutning["id"], objekt, [m.externt_id for m in mappade])
    kanda = {p["id"]: p for p in await lagring.hitta_poster(
        storage, tenant_id, objekt, "id", [e["post_id"] for e in externa.values()], med_raderade=True)}

    if objekt == "bolag":
        per_orgnr = {p["orgnr_nyckel"]: p for p in await lagring.hitta_poster(
            storage, tenant_id, "bolag", "orgnr_nyckel", [m.falt.get("orgnr_nyckel") for m in mappade])}
        utan = [m for m in mappade if not m.falt.get("orgnr_nyckel")]
        per_doman = _unika(await lagring.hitta_poster(
            storage, tenant_id, "bolag", "doman",
            [m.falt.get("doman") for m in utan if not falt.doman_ar_privat(m.falt.get("doman"))]), "doman")
        per_namn = _unika(await lagring.hitta_poster(
            storage, tenant_id, "bolag", "namnnyckel",
            [falt.namnnyckel(m.falt.get("namn")) for m in utan if m.falt.get("namn")]), "namnnyckel")
        bolag_for = {}
    else:
        per_epost = {p["epost"]: p for p in await lagring.hitta_poster(
            storage, tenant_id, "person", "epost", [m.falt.get("epost") for m in mappade])}
        bolag_externa = await lagring.externa_for_kalla(
            storage, tenant_id, anslutning["id"], "bolag", [m.falt.get("bolag_externt_id") for m in mappade])
        bolag_for = {eid: rad["post_id"] for eid, rad in bolag_externa.items()}
        bolag_per_orgnr = {p["orgnr_nyckel"]: p["id"] for p in await lagring.hitta_poster(
            storage, tenant_id, "bolag", "orgnr_nyckel", [m.falt.get("bolag_orgnr_nyckel") for m in mappade])}

    utfall: list[Utfall] = []
    for index, m in enumerate(mappade):
        u = Utfall("hoppad", index, externt_id=m.externt_id, fel=m.fel)
        utfall.append(u)
        if m.hoppa_over:
            u.orsak = "hoppas_over_enligt_mappningen"
            continue
        extern = externa.get(m.externt_id) if m.externt_id else None
        post = kanda.get(extern["post_id"]) if extern else None

        if objekt == "bolag":
            nyckel = m.falt.get("orgnr_nyckel")
            pa_orgnr = per_orgnr.get(nyckel) if nyckel else None
            if post and pa_orgnr and pa_orgnr["id"] != post["id"]:
                u.status, u.id, u.orsak = "konflikt", post["id"], "orgnr_tillhor_annat_bolag"
                continue
            if post is None:
                post = pa_orgnr
            if post is None and not nyckel:
                post = (per_doman.get(m.falt.get("doman"))
                        or per_namn.get(falt.namnnyckel(m.falt.get("namn")) if m.falt.get("namn") else None))
            if m.falt.get("namn"):
                m.falt["namnnyckel"] = falt.namnnyckel(m.falt["namn"])
        else:
            adress = m.falt.get("epost")
            if adress and adress in begransade:
                u.orsak = "behandlingen_ar_begransad"
                continue
            if adress and adress in avregistrerade:
                m.falt["kontakta_inte"] = True
            if post is None and adress:
                post = per_epost.get(adress)
            bolag_id = (bolag_for.get(m.falt.pop("bolag_externt_id", None))
                        or bolag_per_orgnr.get(m.falt.pop("bolag_orgnr_nyckel", None)))
            m.falt.pop("bolag_externt_id", None)
            m.falt.pop("bolag_orgnr_nyckel", None)
            if bolag_id:
                m.falt["bolag_id"] = bolag_id

        if m.raderad:
            if post and not post.get("raderad_at"):
                u.status, u.id = "raderad", post["id"]
                if not torrkorning:
                    await lagring.uppdatera_post(storage, tenant_id, objekt, post["id"],
                                                 {"raderad_at": lagring.nu()})
                    post["raderad_at"] = lagring.nu()
            else:
                u.orsak, u.id = "redan_borta", post["id"] if post else None
            await _markera(storage, tenant_id, anslutning, korning, objekt, m, extern, post, torrkorning)
            continue

        ny_hash = _hash(m)
        if post is None:
            har_namn = m.falt.get("namn") if objekt == "bolag" else (
                m.falt.get("epost") or m.falt.get("fornamn") or m.falt.get("efternamn"))
            if not har_namn:
                u.orsak = "saknar_namn" if objekt == "bolag" else "saknar_namn_och_epost"
                continue
            u.status = "skapad"
            if torrkorning:
                continue
            ny = {**m.falt, "extra": m.extra, "kalla": "synk"}
            if objekt == "bolag":
                ny.setdefault("relation", anslutning.get("standardrelation") or "kund")
            try:
                post = await lagring.skapa_post(storage, tenant_id, objekt, ny)
            except lagring.FinnsRedan:
                # En annan sats hann före med samma orgnr eller adress.
                u.status, u.orsak = "konflikt", "finns_redan"
                continue
        else:
            u.id = post["id"]
            if extern and extern.get("innehallshash") == ny_hash and not post.get("raderad_at"):
                u.status = "oforandrad"
            else:
                skriv, u.behallna = _andringar(post, m, anslutning.get("konfliktregel") or "kallan_vinner")
                if post.get("raderad_at"):
                    skriv["raderad_at"] = None
                u.status = "uppdaterad" if skriv else "oforandrad"
                if skriv and not torrkorning:
                    try:
                        post = await lagring.uppdatera_post(storage, tenant_id, objekt, post["id"], skriv) or post
                    except lagring.FinnsRedan:
                        u.status, u.orsak = "konflikt", "finns_redan"
                        continue
        u.id = post["id"] if post else None
        # Senare poster i samma sats ska se den här: två rader för samma bolag
        # i en fil blir en post, inte en krock.
        if post and objekt == "bolag":
            if post.get("orgnr_nyckel"):
                per_orgnr[post["orgnr_nyckel"]] = post
        elif post and post.get("epost"):
            per_epost[post["epost"]] = post
        if post:
            kanda[post["id"]] = post
        ny_extern = await _markera(storage, tenant_id, anslutning, korning, objekt, m, extern, post,
                                   torrkorning, ny_hash)
        if ny_extern and m.externt_id:
            externa[m.externt_id] = ny_extern

    delta = {"totalt": len(utfall)}
    for u in utfall:
        nyckel = {"skapad": "skapade", "uppdaterad": "uppdaterade", "oforandrad": "oforandrade",
                  "hoppad": "hoppade", "konflikt": "konflikter", "raderad": "borttagna"}[u.status]
        delta[nyckel] = delta.get(nyckel, 0) + 1
    fel = [{"objekt": objekt, "index": u.index, "externt_id": u.externt_id,
            **({"orsak": u.orsak} if u.orsak else {}), **({"faltfel": u.fel} if u.fel else {})}
           for u in utfall if u.fel or u.status in ("hoppad", "konflikt")]
    if not torrkorning:
        await lagring.rakna_korning(storage, tenant_id, korning["id"], delta, fel)
    return {"summering": delta, "poster": [u.som_dict() for u in utfall]}


def _unika(poster: list[dict[str, Any]], kolumn: str) -> dict[str, dict[str, Any]]:
    """Bara värden som pekar ut exakt en post."""
    per: dict[str, list[dict[str, Any]]] = {}
    for p in poster:
        per.setdefault(p[kolumn], []).append(p)
    return {k: v[0] for k, v in per.items() if len(v) == 1}


async def _markera(storage, tenant_id, anslutning, korning, objekt, m, extern, post, torrkorning,
                   ny_hash: str | None = None):
    """Källans id sett i den här körningen. Utan id hos källan finns inget att minnas."""
    if torrkorning or not m.externt_id or not post:
        return None
    try:
        return await lagring.satt_externt_id(
            storage, tenant_id, befintlig=extern, anslutning_id=anslutning["id"], objekt=objekt,
            externt_id=m.externt_id, post_id=post["id"], senast_korning=korning["id"],
            extern_uppdaterad_at=m.uppdaterad,
            **({"innehallshash": ny_hash} if ny_hash else {}))
    except lagring.FinnsRedan:
        return None


async def slutfor(
    storage: Any, tenant_id: str, anslutning: dict[str, Any], korning: dict[str, Any]
) -> dict[str, Any]:
    """Avslutar körningen. En full synk tar hand om det som saknades i källan."""
    korning = await lagring.hamta_korning(storage, tenant_id, korning["id"]) or korning
    _, begransade = await _sparrar(storage, tenant_id)
    borttagna, fel = 0, None
    regel = anslutning.get("saknade") or "behall"
    if korning["lage"] == "full" and regel != "behall":
        if not korning["totalt"]:
            fel = "tom_full_synk"
        else:
            for objekt in adaptrar.OBJEKT:
                saknade = await lagring.externa_ej_sedda(storage, tenant_id, anslutning["id"], objekt, korning["id"])
                poster = await lagring.hitta_poster(storage, tenant_id, objekt, "id", [s["post_id"] for s in saknade])
                for post in poster:
                    if (post.get("epost") or "").casefold() in begransade:
                        continue
                    if regel == "ta_bort":
                        andring = {"raderad_at": lagring.nu()}
                    elif objekt == "bolag" and post["relation"] == "kund":
                        andring = {"relation": "tidigare_kund"}
                    else:
                        continue
                    await lagring.uppdatera_post(storage, tenant_id, objekt, post["id"], andring)
                    borttagna += 1
    for objekt in adaptrar.OBJEKT:
        await lagring.tom_papperskorg(storage, tenant_id, objekt, undanta=begransade)
    await lagring.uppdatera_anslutning(storage, tenant_id, anslutning["id"], senaste_synk_at=lagring.nu())
    return await lagring.avsluta_korning(storage, tenant_id, korning["id"],
                                         status="failed" if fel else "completed", error=fel, borttagna=borttagna)


# -- Poster som skrivs för hand (API:t och appen) ----------------------------


class OgiltigPost(ValueError):
    """Fälten gick inte att tolka. `fel` är listan API:t lämnar ut."""

    def __init__(self, fel: list[dict[str, Any]]) -> None:
        super().__init__("ogiltig post")
        self.fel = fel


def _tolka(objekt: str, falten: dict[str, Any]) -> adaptrar.Mappad:
    m = adaptrar.mappa(falten, objekt, IDENTITET)
    if m.fel:
        raise OgiltigPost(m.fel)
    if isinstance(falten.get("extra"), dict):
        m.extra = {str(k)[:60]: v for k, v in list(falten["extra"].items())[:50]
                   if not isinstance(v, (dict, list))}
    if objekt == "bolag" and m.falt.get("namn"):
        m.falt["namnnyckel"] = falt.namnnyckel(m.falt["namn"])
    if objekt == "person":
        m.falt.pop("bolag_externt_id", None)
        m.falt.pop("bolag_orgnr_nyckel", None)
        if falten.get("bolag_id"):
            m.falt["bolag_id"] = str(falten["bolag_id"])
    return m


async def skapa(storage: Any, tenant_id: str, objekt: str, falten: dict[str, Any], *, kalla: str) -> tuple[dict, bool]:
    """(posten, skapad). Ett bolag med ett organisationsnummer som redan finns,
    eller en person med en adress som redan finns, uppdateras i stället:
    ett bolag, en rad."""
    m = _tolka(objekt, falten)
    if objekt == "bolag" and not m.falt.get("namn"):
        raise OgiltigPost([{"falt": "namn", "kod": "saknas"}])
    if objekt == "person" and not (m.falt.get("epost") or m.falt.get("fornamn") or m.falt.get("efternamn")):
        raise OgiltigPost([{"falt": "epost", "kod": "saknar_namn_och_epost"}])
    kolumn, varde = (("orgnr_nyckel", m.falt.get("orgnr_nyckel")) if objekt == "bolag"
                     else ("epost", m.falt.get("epost")))
    befintlig = (await lagring.hitta_poster(storage, tenant_id, objekt, kolumn, [varde]))[:1] if varde else []
    if befintlig:
        return await andra(storage, tenant_id, objekt, befintlig[0]["id"], falten), False
    post = await lagring.skapa_post(storage, tenant_id, objekt, {**m.falt, "extra": m.extra, "kalla": kalla})
    return post, True


async def andra(storage: Any, tenant_id: str, objekt: str, rad_id: str, falten: dict[str, Any]) -> dict | None:
    """Ändrar de fält som skickas. Varje ändrat fält märks som ändrat för hand,
    så att konfliktregeln vet om det vid nästa synk. `None` tömmer fältet."""
    post = await lagring.hamta_post(storage, tenant_id, objekt, rad_id)
    if post is None:
        return None
    m = _tolka(objekt, {k: v for k, v in falten.items() if v is not None})
    skriv = {k: v for k, v in m.falt.items() if k in lagring.TABELLER[_tabell(post)] and post.get(k) != v}
    for namn, varde in falten.items():
        if varde is None and namn in adaptrar.MALFALT[objekt] and namn not in ("namn", "relation", "land"):
            if post.get(namn) is not None:
                skriv[namn] = None
            for foljer in _HOR_IHOP.get(namn, ()):
                skriv[foljer] = False if foljer == "enskild_firma" else None
    if objekt == "person" and "bolag_id" in falten and falten["bolag_id"] != post.get("bolag_id"):
        skriv["bolag_id"] = falten["bolag_id"]
    if isinstance(falten.get("extra"), dict):
        extra = {**(post.get("extra") or {}), **m.extra}
        extra = {k: v for k, v in extra.items() if falten["extra"].get(k, "") is not None}
        if extra != (post.get("extra") or {}):
            skriv["extra"] = extra
    if not skriv:
        return post
    tid = lagring.nu()
    skriv["manuellt_andrade"] = {**(post.get("manuellt_andrade") or {}),
                                 **{k: tid for k in skriv if k not in _HARLEDDA and k != "extra"}}
    return await lagring.uppdatera_post(storage, tenant_id, objekt, rad_id, skriv)


async def radera(storage: Any, tenant_id: str, objekt: str, rad_id: str, *, permanent: bool = False) -> bool:
    """Mjuk radering: posten ligger i papperskorgen i 30 dagar och går att
    återställa. `permanent` tömmer den direkt. I båda fallen finns id och
    raderingstid kvar som gravsten för den som synkar ut."""
    post = await lagring.hamta_post(storage, tenant_id, objekt, rad_id, med_raderade=permanent)
    if post is None or post.get("kalla") == lagring.GRAVSTEN:
        return False
    _, begransade = await _sparrar(storage, tenant_id)
    if permanent:
        if (post.get("epost") or "").casefold() in begransade:
            raise BegransadBehandling()
        await lagring.gor_gravsten(storage, tenant_id, objekt, rad_id)
    else:
        await lagring.uppdatera_post(storage, tenant_id, objekt, rad_id, {"raderad_at": lagring.nu()})
    await lagring.tom_papperskorg(storage, tenant_id, objekt, undanta=begransade)
    return True


class BegransadBehandling(ValueError):
    """Adressen har begränsad behandling (GDPR art. 18). Uppgifterna får
    ligga kvar i papperskorgen men inte tömmas förrän begränsningen hävts."""


class RedanTomd(ValueError):
    """Posten är permanent raderad och går inte att återställa."""


async def aterstall(storage: Any, tenant_id: str, objekt: str, rad_id: str) -> dict | None:
    """Tar tillbaka en post ur papperskorgen. Höjer `lagring.FinnsRedan` om
    organisationsnumret eller adressen hunnit tas av en annan post."""
    post = await lagring.hamta_post(storage, tenant_id, objekt, rad_id, med_raderade=True)
    if post is None or not post.get("raderad_at"):
        return post
    if post.get("kalla") == lagring.GRAVSTEN:
        raise RedanTomd()
    return await lagring.uppdatera_post(storage, tenant_id, objekt, rad_id, {"raderad_at": None})
