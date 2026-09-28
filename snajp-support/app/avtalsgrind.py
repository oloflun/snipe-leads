"""Avtalsgrinden: en tenant med `kraver_avtal` får ingen riktig kundtrafik
förrän avtalet är registrerat.

## Varför grinden finns

Livrustning-piloten (2026-09-19) är första gången en riktig kunds kundbas
möter agenten, och personuppgiftsbiträdesavtalet hanteras separat och
juridiskt — det får INTE antas vara signerat för att koden är deployad.
Varje publik yta (chatten, inkommande mejl, kanalerna) frågar grinden innan
någon kundtext går till modelleverantören. Det är samma princip som
`llm_provider_fault`: en spärr som saknas i koden är en spärr som glöms.

## Var statusen bor

Två befintliga fält, ingen ny sanning:

  * `ss_tenants.kraver_avtal` (migration 070) — opt-in per tenant, så att
    befintliga kunder utan registrerat avtalsdatum inte stängs av retroaktivt.
  * `ss_customer_details.avtal_signerat` (migration 053) — datumet ÄR
    statusen, registreras av admin i fliken Kunder & Data.

## Felriktning

Fail-open vid LAGRINGSFEL, fail-closed vid saknat avtal. Ett trasigt uppslag
betyder att databasen krånglar — då faller själva agentkörningen ändå, och
att dessutom svara "avtal saknas" hade varit fel diagnos till kunden. Men en
tenant som ENTYDIGT kräver avtal utan att ha ett vägras, varje gång.

Svaret cachas kort per process: chatten frågar per meddelande, och två
DB-läsningar per tangenttryckning vore att betala för samma sanning om igen.
Cachen är kort nog att ett nyregistrerat avtal slår igenom inom en minut.
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger("snajp-support.avtalsgrind")

#: Vad kunden ska läsa. Ingen juridik, ingen skuld — tjänsten är helt enkelt
#: inte öppnad ännu, och det är mellan oss och företaget.
KUNDTEXT_AVTAL = (
    "Tjänsten är inte öppnad ännu. Vi aktiverar den så snart allt är på "
    "plats med företaget — försök gärna igen senare."
)

#: Hur länge ett svar återanvänds per tenant. 60 s är valt så att admin som
#: just registrerat avtalet ser effekten inom en minut, utan omstart.
_CACHE_SEKUNDER = 60.0

#: tenant_id -> (avgörande, när). PROCESSLOKAL med samma motivering som
#: dubblettminnet i prioriterat_mejl.py: värsta utfallet av en kall cache är
#: en extra DB-läsning, aldrig ett felaktigt avgörande.
_cache: dict[str, tuple[bool, float]] = {}


def nollstall_cache() -> None:
    """Bara för tester. Utan den läcker en testfil sitt avgörande in i nästa."""
    _cache.clear()


async def avtal_saknas(storage, tenant_id: str) -> bool:
    """True om tenanten kräver avtal och inget är registrerat — då ska den
    publika ytan vägra. False i alla andra lägen, inklusive vid lagringsfel
    (se modulens docstring om felriktningen)."""
    nu = time.monotonic()
    cachad = _cache.get(tenant_id)
    if cachad and nu - cachad[1] < _CACHE_SEKUNDER:
        return cachad[0]

    try:
        tenant = await storage.get_tenant(tenant_id)
        if not (tenant or {}).get("kraver_avtal"):
            avgorande = False
        else:
            detaljer = await storage.get_customer_details(tenant_id)
            avgorande = not (detaljer or {}).get("avtal_signerat")
    except Exception as fel:  # noqa: BLE001 — fail-open vid lagringsfel, med flit
        logger.warning(
            "avtalsgrind: uppslaget för tenant %s misslyckades, släpper igenom (%s)",
            tenant_id,
            fel,
        )
        return False

    _cache[tenant_id] = (avgorande, nu)
    if avgorande:
        logger.info("avtalsgrind: tenant %s vägras — avtal är inte registrerat", tenant_id)
    return avgorande
