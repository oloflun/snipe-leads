"""Snajp CRM i det publika API:t: bolagsuppgifter ur SCB:s företagsregister.

Antons beslut 2026-11-27 (fråga 10: ja, bara bolagsnivå). Ett uppslag som inte
sparar något, och en berikning som fyller tomma fält på ett bolag. Registret
ger aldrig personer här (app/crm/scb.py), och en enskild firma slås inte upp.

Routern byggs av `koppla(crm_v1)` och läggs till därifrån, så grindarna
(nyckel, omfång, tillägg, tak, avtal) är desamma som för resten av API:t.

- Ett fält som redan har ett värde skrivs aldrig över, utom med
  `?overwrite=true`, och då aldrig ett fält som någon ändrat för hand
  (`manuellt_andrade`). Berikningen märker inte sina egna fält som ändrade för
  hand: registret är ingen människa.
- Registrets status står alltid i `registry_status` och skrivs varje gång.
- En reklamspärr i registret lämnas i svaret (`advertising_block`) och blir
  INTE tyst kontakta inte. Spärrlistan (`/suppressions`) är platsen för den
  när kunden vill spärra.
- SCB nere ger 502 `registry_unavailable`, aldrig 500. Utan nyckel 503
  `enrichment_not_configured`.
"""

from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from ..crm import falt, handelser, lagring, scb
from .deps import kraev_uuid

#: Kolumnerna i API:ts namn, för `filled` och `skipped` och händelseloggen.
_FALT_UT = {"namn": "name", "bolagsform": "legal_form", "sni": "sni_code", "gatuadress": "address.street",
            "co": "address.co", "postnr": "address.postal_code", "postort": "address.city",
            "registerstatus": "registry_status"}


def registret_ut(b: scb.Bolagsuppgifter) -> dict[str, Any]:
    """Registrets svar i API:ts form. Bara bolagsnivå: inga personer."""
    return {
        "org_number": b.orgnr,
        "name": b.namn,
        "legal_form": b.bolagsform,
        "legal_form_code": b.juridisk_form_kod,
        "registry_status": b.status,
        "sni_codes": b.sni,
        "registered_office": {"municipality": b.sate_kommun, "county": b.sate_lan},
        "postal_address": {"street": b.gatuadress, "co": b.co, "postal_code": b.postnr, "city": b.postort},
        "employee_class": {"code": b.anstallda_klass, "label": b.anstallda_text} if b.anstallda_klass else None,
        "advertising_block": b.reklamsparr,
        "codes": {"company_status": b.foretagsstatus_kod, "bolagsverket_status": b.bolagsverket_status_kod,
                  "advertising": b.reklamsparr_kod},
    }


def _registervarden(b: scb.Bolagsuppgifter) -> dict[str, Any]:
    """Bolagets kolumner som registret kan fylla, i den ordning de prövas.
    Antal anställda fylls inte: registret ger en storleksklass, inte ett antal."""
    return {"namn": b.namn, "bolagsform": b.bolagsform, "sni": ",".join(b.sni) or None,
            "gatuadress": b.gatuadress, "co": b.co, "postnr": b.postnr, "postort": b.postort}


def berika(post: dict[str, Any], b: scb.Bolagsuppgifter, *, overwrite: bool) -> tuple[dict[str, Any], list[str], list[str]]:
    """(det som skrivs, fyllda kolumner, hoppade kolumner).

    Hoppad är ett fält där registret har ett annat värde men bolagets eget
    stod kvar: det hade ett värde (utan `overwrite`), eller ändrades för hand."""
    manuellt = post.get("manuellt_andrade") or {}
    skriv: dict[str, Any] = {}
    fyllda: list[str] = []
    hoppade: list[str] = []
    for kolumn, varde in _registervarden(b).items():
        if varde in (None, ""):
            continue
        nu = post.get(kolumn)
        if nu == varde:
            continue
        if nu in (None, "") or (overwrite and kolumn not in manuellt):
            skriv[kolumn] = varde
            fyllda.append(kolumn)
        else:
            hoppade.append(kolumn)
    if "namn" in skriv:
        skriv["namnnyckel"] = falt.namnnyckel(skriv["namn"])
    skriv["registerstatus"] = b.status
    skriv["registret_last_at"] = lagring.nu()
    return skriv, fyllda, hoppade


def koppla(v1: Any) -> APIRouter:
    """Bygger ändpunkterna med `crm_v1`s egna grindar, på en ny router."""
    router = APIRouter(prefix=v1.router.prefix, tags=v1.router.tags)
    kraev, fel = v1.kraev, v1.fel

    def _ej_konfigurerad() -> HTTPException:
        return fel(503, "enrichment_not_configured",
                   "Lookups in SCB's business register are not configured yet. Contact Snajp.",
                   "Uppslag i SCB:s företagsregister är inte konfigurerade än. Kontakta Snajp.")

    def _inte_ett_bolag() -> HTTPException:
        return fel(422, "not_a_company",
                   "A sole proprietorship or private person is not looked up: the number belongs to a person.",
                   "En enskild firma eller privatperson slås inte upp: numret hör till en person.")

    def _nere() -> HTTPException:
        return fel(502, "registry_unavailable",
                   "SCB's business register did not answer. Try again later.",
                   "SCB:s företagsregister svarade inte. Försök igen senare.")

    def _saknas() -> HTTPException:
        return fel(404, "company_not_in_registry",
                   "The organisation number is not in SCB's business register.",
                   "Organisationsnumret finns inte i SCB:s företagsregister.")

    async def _sla_upp(orgnr: str) -> scb.Bolagsuppgifter:
        try:
            uppgifter = await scb.sla_upp(orgnr)
        except falt.FaltFel as orsak:
            raise fel(422, "invalid_fields", "One or more fields could not be interpreted.",
                      "Ett eller flera fält gick inte att tolka.",
                      fields=[{"field": "org_number", "code": orsak.args[0] if orsak.args else "orgnr_ogiltigt"}]
                      ) from None
        except scb.InteEttBolag:
            raise _inte_ett_bolag() from None
        except scb.EjKonfigurerad:
            raise _ej_konfigurerad() from None
        except scb.RegistretNere:
            raise _nere() from None
        if uppgifter is None:
            raise _saknas()
        return uppgifter

    @router.get("/lookup/companies", summary="Look up a company in SCB's business register, without saving")
    async def sla_upp_bolag(request: Request, org_number: str = Query(..., max_length=40),
                            tenant: dict = Depends(kraev("crm:las"))) -> dict:
        """Company level only: name, legal form, status, SNI codes, registered
        office, postal address, employee size class and advertising block.
        Never people: no signatories, no board, no owner names. A sole
        proprietorship is not looked up (422 `not_a_company`): its number is
        the owner's personal identity number. Nothing is stored."""
        return {"data": registret_ut(await _sla_upp(org_number))}

    @router.post("/companies/{company_id}/enrich", summary="Fill a company's empty fields from SCB's business register")
    async def berika_bolag(request: Request, company_id: str,
                           overwrite: bool = Query(False, description="Also replace fields that have a value, "
                                                   "except fields someone changed by hand in Snajp."),
                           tenant: dict = Depends(kraev("crm:skriv"))) -> Response:
        """Fills `name`, `legal_form`, `sni_code` and the address where they are
        empty, and always sets `registry_status`. `filled` and `skipped` name
        the fields: skipped are fields where the register differs but the
        company's own value was kept. The employee size class is returned under
        `registry` but not written to `employees`, which is a count.

        An advertising block in the register is returned as
        `advertising_block` and does NOT mark the company do-not-contact. Add
        a suppression under `/suppressions` if you want it to block."""
        await v1._avtal(request, tenant)
        storage = request.app.state.storage
        tenant_id = tenant["tenant_id"]
        rad_id = kraev_uuid(company_id, "Posten")

        async def arbete():
            post = await lagring.hamta_post(storage, tenant_id, "bolag", rad_id)
            if post is None:
                raise fel(404, "not_found", "The record does not exist.", "Posten finns inte.")
            if post.get("privatperson") or post.get("enskild_firma") or post.get("bolagsform") == "EF":
                raise _inte_ett_bolag()
            if not post.get("orgnr"):
                raise fel(422, "org_number_required", "The company has no organisation number to look up.",
                          "Bolaget saknar organisationsnummer att slå upp.")
            uppgifter = await _sla_upp(post["orgnr"])
            skriv, fyllda, hoppade = berika(post, uppgifter, overwrite=overwrite)
            ny = await lagring.uppdatera_post(storage, tenant_id, "bolag", rad_id, skriv) or post
            andrade = [*fyllda, *(["registerstatus"] if post.get("registerstatus") != uppgifter.status else [])]
            if andrade:
                ursprung = v1._ursprung(request, tenant)
                await handelser.logga(storage, tenant_id,
                                      [handelser.Handelse("bolag", rad_id, "andrad", falt=andrade, post=ny)],
                                      kalla=ursprung["via"], aktor=ursprung["aktor"])
            return 200, {
                "company": v1.bolag_ut(ny),
                "filled": [_FALT_UT.get(k, k) for k in fyllda],
                "skipped": [_FALT_UT.get(k, k) for k in hoppade],
                "registry_status": uppgifter.status,
                "deregistered": uppgifter.avregistrerad,
                "advertising_block": uppgifter.reklamsparr,
                "registry": registret_ut(uppgifter),
            }

        kroppshash = hashlib.sha256(f"overwrite={overwrite}".encode()).hexdigest()
        return await v1._idempotent(request, tenant, arbete, kroppshash=kroppshash)

    return router
