"""Envägssynk ut till kundens externa CRM (plan del F7).

Snipra är sanningen; HubSpot eller Pipedrive får en spegel av bolaget och en
anteckning per händelse (statusbyte, anteckning). Ingenting läses tillbaka.

Kastar ALDRIG: synken körs fire-and-forget efter att ändringen redan sparats
hos oss, och ett fel hos leverantören ska synas i loggen, inte fälla kundens
klick. Nyckeln ligger krypterad i integrationen (`api_key`) och dekrypteras
först här, när anropet byggs.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from ..integrationer import lagring as integrationer

logger = logging.getLogger("snajp-support.crm-synk")

HUBSPOT = "https://api.hubapi.com"
PIPEDRIVE = "https://api.pipedrive.com/v1"
TIMEOUT_S = 10.0
#: HubSpots fördefinierade association anteckning → bolag.
_HUBSPOT_NOTE_TILL_BOLAG = 190


def _doman(website: str | None) -> str | None:
    if not website:
        return None
    url = website if "://" in website else f"https://{website}"
    host = (urlparse(url).hostname or "").removeprefix("www.")
    return host or None


def _anteckning(handelse: str, text: str | None) -> str:
    return f"Snipra: {handelse}: {text}" if text else f"Snipra: {handelse}"


async def _hubspot(client: httpx.AsyncClient, nyckel: str, prospect: dict, notis: str) -> None:
    h = {"Authorization": f"Bearer {nyckel}"}
    namn = prospect.get("company_name") or ""
    sok = await client.post(
        f"{HUBSPOT}/crm/v3/objects/companies/search",
        headers=h,
        json={
            "filterGroups": [{"filters": [{"propertyName": "name", "operator": "EQ", "value": namn}]}],
            "limit": 1,
        },
    )
    sok.raise_for_status()
    egenskaper = {
        k: v
        for k, v in {
            "name": namn,
            "domain": _doman(prospect.get("website")),
            "phone": prospect.get("contact_phone"),
        }.items()
        if v
    }
    traffar = sok.json().get("results") or []
    if traffar:
        bolag_id = str(traffar[0]["id"])
        svar = await client.patch(
            f"{HUBSPOT}/crm/v3/objects/companies/{bolag_id}", headers=h, json={"properties": egenskaper}
        )
    else:
        svar = await client.post(f"{HUBSPOT}/crm/v3/objects/companies", headers=h, json={"properties": egenskaper})
    svar.raise_for_status()
    bolag_id = str(svar.json().get("id") or (traffar[0]["id"] if traffar else ""))
    notis_svar = await client.post(
        f"{HUBSPOT}/crm/v3/objects/notes",
        headers=h,
        json={
            "properties": {
                "hs_note_body": notis,
                "hs_timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "associations": [
                {
                    "to": {"id": bolag_id},
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": _HUBSPOT_NOTE_TILL_BOLAG,
                        }
                    ],
                }
            ],
        },
    )
    notis_svar.raise_for_status()


async def _pipedrive(client: httpx.AsyncClient, nyckel: str, prospect: dict, notis: str) -> None:
    p = {"api_token": nyckel}
    namn = prospect.get("company_name") or ""
    sok = await client.get(
        f"{PIPEDRIVE}/organizations/search", params={**p, "term": namn, "exact_match": "true"}
    )
    sok.raise_for_status()
    poster = ((sok.json().get("data") or {}).get("items")) or []
    if poster:
        org_id = poster[0]["item"]["id"]
        svar = await client.put(f"{PIPEDRIVE}/organizations/{org_id}", params=p, json={"name": namn})
    else:
        svar = await client.post(f"{PIPEDRIVE}/organizations", params=p, json={"name": namn})
    svar.raise_for_status()
    org_id = (svar.json().get("data") or {}).get("id") or (poster[0]["item"]["id"] if poster else None)
    notis_svar = await client.post(f"{PIPEDRIVE}/notes", params=p, json={"content": notis, "org_id": org_id})
    notis_svar.raise_for_status()


async def synka_prospekt(
    storage, tenant_id: str, prospect: dict, *, handelse: str, text: str | None = None
) -> None:
    """Speglar bolaget och händelsen till kundens CRM. Kastar aldrig."""
    leverantor = None
    try:
        settings = await storage.get_agent_settings(tenant_id, agent_type="leads")
        val = settings.get("crm_synk") or {}
        leverantor = val.get("leverantor")
        integration_id = val.get("integration_id")
        if leverantor not in ("hubspot", "pipedrive") or not integration_id:
            return
        rad = await integrationer.hamta(storage, tenant_id, str(integration_id))
        if not rad:
            logger.warning("CRM-synk: integrationen %s finns inte hos %s.", integration_id, tenant_id)
            return
        nyckel = (integrationer.dekryptera_hemligheter(rad) or {}).get("api_key")
        if not nyckel:
            logger.warning("CRM-synk: integrationen %s saknar hemligheten api_key.", integration_id)
            return
        notis = _anteckning(handelse, text)
        async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
            if leverantor == "hubspot":
                await _hubspot(client, nyckel, prospect, notis)
            else:
                await _pipedrive(client, nyckel, prospect, notis)
    except Exception as fel:  # noqa: BLE001 — synken får aldrig fälla kundens ändring
        # Bara typen: ett httpx-fel bär URL:en, och Pipedrives URL bär nyckeln.
        logger.warning(
            "CRM-synk till %s misslyckades för %s (%s).",
            leverantor,
            prospect.get("id"),
            type(fel).__name__,
        )
