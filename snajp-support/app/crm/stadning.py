"""Papperskorgen töms av ett jobb, inte bara vid nästa skrivning.

Löftet är att en raderad post går att återställa i trettio dagar och sedan
töms (`lagring.PAPPERSKORG_DAGAR`). Förut tömdes korgen bara när kunden skrev
något igen (`lagring.tom_papperskorgarna` från skrivvägarna), så hos en kund
som slutat skriva låg raderade personer kvar hur länge som helst.

Jobbet går en gång strax efter uppstart och sedan en gång per dygn, i samma
form som webhookarbetaren (`webhooks.run_webhookjobb`):

- Kunderna tas ur `storage.list_tenants()`, systemläsningen som bara ger
  kundernas id. CRM-tabellerna läses aldrig tvärs över kunder: varje fråga
  går genom `storage._scoped(tenant_id)`, där radskyddet gäller, och bär
  `tenant_id` uttryckligen.
- En kund i taget. Ett fel hos en kund loggas och stoppar inte nästa.
- Loggen bär objektens namn och antal, aldrig innehåll.

Bolag och personer töms med kundens adresser med begränsad behandling
undantagna (GDPR art. 18), som synken gör. Går de adresserna inte att läsa
töms inga bolag eller personer hos kunden det varvet: hellre en dag för sent
än en begränsad post tömd. Av med `CRM_STADJOBB=0`.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from . import lagring

logger = logging.getLogger("snajp-support.crm.stadning")

#: Objekten med en papperskorg, i den ordning de töms. Bolag och personer
#: först: deras kaskad tömmer anteckningar, aktiviteter och bilagor som pekar
#: på dem, och de räknas då inte en gång till.
OBJEKT = ("bolag", "person", *lagring.OBJEKT_164)
#: `tom_papperskorg` tar högst så här många per anrop. Jobbet anropar igen
#: tills korgen är tom, men aldrig fler än `MAX_VARV` gånger per objekt och
#: kund, så att en enda stor kund inte håller jobbet i timmar.
_PER_ANROP = 200
MAX_VARV = 50
DYGN = 24 * 3600.0
#: Väntan efter uppstart, så att jobbet inte trängs med allt annat som startar.
FORDROJNING = 60.0


async def har_utgangna(storage: Any, tenant_id: str, *, dagar: int = lagring.PAPPERSKORG_DAGAR) -> bool:
    """Har kunden något i en papperskorg som legat längre än `dagar`? En fråga
    per tabell, inom kundens radskydd, som bara svarar ja eller nej."""
    grans = datetime.now(timezone.utc) - timedelta(days=dagar)
    for objekt in OBJEKT:
        tabell = lagring._OBJEKTTABELL[objekt]
        if lagring._ar_postgres(storage):
            try:
                async with storage._scoped(tenant_id) as conn:
                    finns = await conn.fetchval(
                        f"select exists (select 1 from {tabell} where tenant_id = $1::text::uuid "
                        "and raderad_at < $2::text::timestamptz and kalla <> $3)",
                        tenant_id, grans.isoformat(), lagring.GRAVSTEN)
            except Exception as fel:
                if lagring._saknar_tabell(fel):
                    continue
                raise
            if finns:
                return True
        elif any(r["tenant_id"] == tenant_id and r.get("raderad_at") and r["kalla"] != lagring.GRAVSTEN
                 and lagring._tid(r["raderad_at"]) < grans
                 for r in lagring._minne(storage, tabell).values()):
            return True
    return False


async def kunder_att_tomma(storage: Any) -> list[str]:
    """Kundernas id där något ska tömmas. Systemläsningen ger bara id:n; frågan
    om det finns något att tömma ställs sedan inom varje kunds radskydd."""
    ut = []
    for kund in await storage.list_tenants():
        tenant_id = str(kund["id"])
        try:
            if await har_utgangna(storage, tenant_id):
                ut.append(tenant_id)
        except Exception:  # noqa: BLE001 (en kunds fel får inte stoppa de andras)
            logger.exception("Papperskorgen gick inte att läsa för en kund. Fortsätter med nästa.")
    return ut


async def tom_for_kund(storage: Any, tenant_id: str) -> dict[str, int]:
    """Tömmer kundens utgångna poster. Returnerar antal tömda per objekt."""
    try:
        begransade: set[str] | None = await storage.list_begransade(tenant_id)
    except Exception:  # noqa: BLE001
        begransade = None
        logger.warning("crm: begränsade adresser gick inte att läsa; bolag och personer töms inte det här varvet")
    antal: dict[str, int] = {}
    for objekt in OBJEKT:
        if objekt in ("bolag", "person") and begransade is None:
            continue
        undanta = begransade if objekt in ("bolag", "person") else ()
        summa = 0
        for _ in range(MAX_VARV):
            tomda = await lagring.tom_papperskorg(storage, tenant_id, objekt, undanta=undanta or ())
            summa += tomda
            if tomda < _PER_ANROP:
                break
        if summa:
            antal[objekt] = summa
    return antal


async def kor_varv(storage: Any) -> dict[str, int]:
    """Ett varv: varje kund med något att tömma, en i taget. Returnerar antal
    tömda per objekt, summerat över kunderna."""
    totalt: dict[str, int] = {}
    kunder = await kunder_att_tomma(storage)
    for tenant_id in kunder:
        try:
            antal = await tom_for_kund(storage, tenant_id)
        except Exception:  # noqa: BLE001 (en kunds fel får inte stoppa nästa)
            logger.exception("Papperskorgen gick inte att tömma för en kund. Fortsätter med nästa.")
            continue
        for objekt, n in antal.items():
            totalt[objekt] = totalt.get(objekt, 0) + n
    if totalt:
        logger.info("crm: papperskorgen tömd hos %d kunder: %s", len(kunder),
                    ", ".join(f"{objekt} {n}" for objekt, n in sorted(totalt.items())))
    return totalt


async def run_stadjobb(
    app_state: Any, *, intervall: float = DYGN, fordrojning: float = FORDROJNING
) -> None:
    """Bakgrundsloopen: ett varv strax efter uppstart, sedan ett per dygn."""
    logger.info("CRM:ets städjobb aktivt: papperskorgen töms en gång per dygn.")
    await asyncio.sleep(fordrojning)
    while True:
        try:
            await kor_varv(app_state.storage)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 (jobbet får aldrig dö)
            logger.exception("Oväntat fel i städjobbet. Försöker igen nästa dygn.")
        await asyncio.sleep(intervall)
