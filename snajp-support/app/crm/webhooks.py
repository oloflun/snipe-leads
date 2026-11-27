"""Webhooks ut: CRM:et säger till när något hänt (migration 162).

Kunden registrerar en https-adress och vilka händelser den vill ha. Varje
händelse i loggen (`app/crm/handelser.py`) läggs då som en leverans i kön, och
ett bakgrundsjobb skickar den.

## Signaturen

    X-Snajp-Signature: t=1764150000,v1=<hex>

`v1` är HMAC-SHA256 över `"{t}.{kroppen}"` med webhookens hemlighet. Tiden
ingår, så att ett avlyssnat anrop inte kan spelas upp i efterhand: mottagaren
avvisar anrop äldre än fem minuter. Hemligheten visas en gång, när webhooken
skapas, och lagras Fernet-krypterad.

## Leverans och omförsök

Ett svar med status 2xx inom tio sekunder är en lyckad leverans. Allt annat
försöks igen med växande väntetid (`VANTETIDER`), sju försök över drygt ett
dygn. Sedan står leveransen som misslyckad i loggen och går att skicka om för
hand. En webhook som misslyckats tjugo leveranser i rad stängs av, och säger
det: en mottagare som är nere ska inte få kön att växa i veckor.

Mottagaren ska svara snabbt och göra arbetet efteråt, och tåla att samma
leverans kommer två gånger (`X-Snajp-Delivery` är dess id).

## Vart det får ringa

Bara publika https-adresser, genom nätvakten (`app/integrationer/natvakt.py`):
adressen skrivs av kunden och anropas av vår server.

Radskyddet gäller som i resten av CRM:et: jobbet läser kön per kund, aldrig
tvärs över kunder.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from ..integrationer import hemligheter, natvakt
from . import lagring

logger = logging.getLogger("snajp-support.crm.webhooks")

#: Händelser en webhook kan prenumerera på. `*` är alla.
HANDELSETYPER = tuple(
    f"{objekt}.{typ}" for objekt in ("company", "person", "deal", "task", "note", "activity", "attachment")
    for typ in ("created", "updated", "deleted", "restored", "purged")
) + ("suppression.created", "suppression.lifted", "sync.completed", "ping")

MAX_PER_KUND = 10
#: Sekunder före försök 2 till 7. Efter det sista står leveransen som misslyckad.
VANTETIDER = (60, 300, 1800, 7200, 21600, 86400)
MAX_FEL_I_RAD = 20
TIDSGRANS = 10.0
LOGG_DAGAR = 30
#: Så länge är en leverans reserverad åt den process som tagit den.
_RESERVATION = 120

#: Kunder med leveranser i kö, kända av den här processen. Jobbet går dessutom
#: igenom alla kunder med jämna mellanrum, för det en annan process lagt i kön
#: och för omförsök efter en omstart.
_vantande: set[str] = set()
_aktiva: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_SEKUNDER = 30.0


def nollstall() -> None:
    """Bara för tester."""
    _vantande.clear()
    _aktiva.clear()


class WebhookFel(ValueError):
    """Adressen eller händelserna går inte att använda. `kod` är stabil."""

    def __init__(self, kod: str, text: str) -> None:
        super().__init__(text)
        self.kod = kod


def signera(hemlighet: str, tid: int, kropp: bytes) -> str:
    stoff = f"{tid}.".encode() + kropp
    return hmac.new(hemlighet.encode(), stoff, hashlib.sha256).hexdigest()


def _kontrollera(url: str | None, handelser: list[str] | None) -> None:
    if url is not None:
        if len(url) > 500:
            raise WebhookFel("invalid_url", "Adressen är längre än 500 tecken.")
        try:
            natvakt.kontrollera_url(url)
        except natvakt.NatvaktError as fel:
            raise WebhookFel("invalid_url", str(fel)) from None
    if handelser is not None:
        okanda = [h for h in handelser if h != "*" and h not in HANDELSETYPER]
        if not handelser or okanda:
            raise WebhookFel("invalid_events", f"Okända händelser: {', '.join(okanda) or '(inga valda)'}.")


async def lista(storage: Any, tenant_id: str) -> list[dict[str, Any]]:
    return await lagring._valj(storage, tenant_id, "crm_webhooks")


async def hamta(storage: Any, tenant_id: str, webhook_id: str) -> dict[str, Any] | None:
    return await lagring._hamta(storage, tenant_id, "crm_webhooks", webhook_id)


async def skapa(
    storage: Any, tenant_id: str, *, url: str, handelser: list[str] | None = None,
    beskrivning: str | None = None,
) -> tuple[dict[str, Any], str]:
    """(webhooken, hemligheten i klartext). Hemligheten visas bara här."""
    handelser = handelser or ["*"]
    _kontrollera(url, handelser)
    if len(await lista(storage, tenant_id)) >= MAX_PER_KUND:
        raise WebhookFel("too_many_webhooks", f"Högst {MAX_PER_KUND} webhooks per arbetsyta.")
    hemlighet = "whsec_" + secrets.token_urlsafe(32)
    rad = await lagring._in(storage, tenant_id, "crm_webhooks", {
        "url": url, "handelser": sorted(set(handelser)), "beskrivning": (beskrivning or "").strip()[:200] or None,
        "hemlighet": hemligheter.kryptera({"hemlighet": hemlighet})})
    _aktiva.pop(str(tenant_id), None)
    return rad, hemlighet


async def andra(storage: Any, tenant_id: str, webhook_id: str, **falt: Any) -> dict[str, Any] | None:
    """Ändrar adress, händelser, beskrivning eller `aktiv`. Att slå på en
    avstängd webhook nollställer räknaren av fel i rad."""
    _kontrollera(falt.get("url"), falt.get("handelser"))
    skriv = {k: v for k, v in falt.items() if k in ("url", "handelser", "beskrivning", "aktiv") and v is not None}
    if "handelser" in skriv:
        skriv["handelser"] = sorted(set(skriv["handelser"]))
    if skriv.get("aktiv"):
        skriv.update(fel_i_rad=0, avstangd_av=None)
    rad = await lagring._upp(storage, tenant_id, "crm_webhooks", webhook_id, skriv)
    _aktiva.pop(str(tenant_id), None)
    return rad


async def ta_bort(storage: Any, tenant_id: str, webhook_id: str) -> bool:
    if not lagring._ar_postgres(storage):
        # Kaskaden i migration 162: leveranserna följer webhooken.
        leveranser = lagring._minne(storage, "crm_webhook_leveranser")
        for lid in [k for k, r in leveranser.items() if r["webhook_id"] == webhook_id]:
            del leveranser[lid]
    _aktiva.pop(str(tenant_id), None)
    return await lagring._ta_bort(storage, tenant_id, "crm_webhooks", webhook_id)


async def _aktiva_for(storage: Any, tenant_id: str) -> list[dict[str, Any]]:
    """Kundens påslagna webhooks, sparade en halv minut: `koa` körs vid varje
    skrivning, och de flesta kunder har ingen webhook alls."""
    nyckel, nu = str(tenant_id), time.monotonic()
    traff = _aktiva.get(nyckel)
    if traff and nu - traff[0] < _SEKUNDER:
        return traff[1]
    rader = [w for w in await lista(storage, tenant_id) if w["aktiv"]]
    _aktiva[nyckel] = (nu, rader)
    return rader


def _vill_ha(webhook: dict[str, Any], handelsetyp: str) -> bool:
    valda = webhook.get("handelser") or ["*"]
    return "*" in valda or handelsetyp in valda


async def koa(storage: Any, tenant_id: str, poster: list[tuple[str, dict[str, Any]]]) -> int:
    """Lägger varje händelse i kön hos de webhooks som vill ha den. Returnerar
    antalet leveranser som lades."""
    if not poster:
        return 0
    try:
        mottagare = await _aktiva_for(storage, tenant_id)
    except Exception as fel:  # noqa: BLE001
        if lagring._saknar_tabell(fel):
            return 0
        raise
    lagda = 0
    for handelsetyp, data in poster:
        for webhook in mottagare:
            if _vill_ha(webhook, handelsetyp):
                await lagring._in(storage, tenant_id, "crm_webhook_leveranser", {
                    "webhook_id": webhook["id"], "handelsetyp": handelsetyp,
                    "kropp": {"type": handelsetyp, "created_at": lagring.nu(), "data": data}})
                lagda += 1
    if lagda:
        _vantande.add(str(tenant_id))
    return lagda


async def prova(storage: Any, tenant_id: str, webhook_id: str) -> dict[str, Any] | None:
    """Lägger en `ping` i kön, så att kunden kan se att adressen svarar."""
    webhook = await hamta(storage, tenant_id, webhook_id)
    if webhook is None:
        return None
    rad = await lagring._in(storage, tenant_id, "crm_webhook_leveranser", {
        "webhook_id": webhook_id, "handelsetyp": "ping",
        "kropp": {"type": "ping", "created_at": lagring.nu(), "data": {"webhook_id": webhook_id}}})
    _vantande.add(str(tenant_id))
    return rad


async def leveranser(
    storage: Any, tenant_id: str, webhook_id: str, *, limit: int = 50
) -> list[dict[str, Any]]:
    return await lagring._valj(storage, tenant_id, "crm_webhook_leveranser", lika={"webhook_id": webhook_id},
                               ordning="created_at", fallande=True, limit=max(1, min(limit, 200)))


async def skicka_om(storage: Any, tenant_id: str, webhook_id: str, leverans_id: str) -> dict[str, Any] | None:
    rad = await lagring._hamta(storage, tenant_id, "crm_webhook_leveranser", leverans_id)
    if rad is None or rad["webhook_id"] != webhook_id:
        return None
    rad = await lagring._upp(storage, tenant_id, "crm_webhook_leveranser", leverans_id, {
        "status": "vantar", "forsok": 0, "nasta_forsok_at": lagring.nu(), "fel": None, "statuskod": None})
    _vantande.add(str(tenant_id))
    return rad


# -- Leveransen --------------------------------------------------------------


async def _ta(storage: Any, tenant_id: str, antal: int) -> list[dict[str, Any]]:
    """Reserverar de leveranser som är dags. I Postgres med `skip locked`, så
    att två processer aldrig tar samma."""
    nu = datetime.now(timezone.utc)
    reserverad_till = (nu + timedelta(seconds=_RESERVATION)).isoformat()
    if lagring._ar_postgres(storage):
        try:
            async with storage._scoped(tenant_id) as conn:
                rader = await conn.fetch(
                    "update crm_webhook_leveranser set forsok = forsok + 1, "
                    "nasta_forsok_at = $2::text::timestamptz, updated_at = now() "
                    "where id in (select id from crm_webhook_leveranser "
                    "             where tenant_id = $1::text::uuid and status = 'vantar' and nasta_forsok_at <= now() "
                    f"             order by nasta_forsok_at limit {int(antal)} for update skip locked) "
                    "returning *", tenant_id, reserverad_till)
        except Exception as fel:
            if lagring._saknar_tabell(fel):
                return []
            raise
        return [lagring._rad(r, "crm_webhook_leveranser") for r in rader]
    tagna = []
    for rad in sorted(lagring._minne(storage, "crm_webhook_leveranser").values(), key=lambda r: r["nasta_forsok_at"]):
        if len(tagna) >= antal:
            break
        if rad["tenant_id"] == tenant_id and rad["status"] == "vantar" and lagring._tid(rad["nasta_forsok_at"]) <= nu:
            rad["forsok"] += 1
            rad["nasta_forsok_at"] = reserverad_till
            tagna.append(dict(rad))
    return tagna


async def _skicka(webhook: dict[str, Any], leverans: dict[str, Any]) -> tuple[int | None, str | None]:
    """(statuskod, fel). Fel är None när leveransen gick fram."""
    kropp = json.dumps({"id": leverans["id"], **leverans["kropp"]}, ensure_ascii=False,
                       separators=(",", ":")).encode("utf-8")
    tid = int(time.time())
    try:
        hemlighet = hemligheter.dekryptera(webhook["hemlighet"]).get("hemlighet", "")
        svar = await natvakt.anropa("POST", webhook["url"], innehall=kropp, tidsgrans=TIDSGRANS, rubriker={
            "Content-Type": "application/json", "User-Agent": "Snajp-CRM-Webhooks/1",
            "X-Snajp-Event": leverans["handelsetyp"], "X-Snajp-Delivery": leverans["id"],
            "X-Snajp-Signature": f"t={tid},v1={signera(hemlighet, tid, kropp)}"})
    except Exception as fel:  # noqa: BLE001 — nätfel, tidsgräns, nätvaktens nej, oläsbar hemlighet
        return None, f"{type(fel).__name__}: {str(fel)[:200]}"
    return svar.status, None if svar.ok else f"HTTP {svar.status}"


async def leverera_for_kund(storage: Any, tenant_id: str, *, max_antal: int = 50) -> dict[str, int]:
    """Skickar kundens leveranser som är dags. Returnerar utfallet i antal."""
    utfall = {"levererade": 0, "omforsok": 0, "misslyckade": 0}
    tagna = await _ta(storage, tenant_id, max_antal)
    hakar = {w["id"]: w for w in await lista(storage, tenant_id)} if tagna else {}
    for leverans in tagna:
        webhook = hakar.get(leverans["webhook_id"])
        if webhook is None or not webhook["aktiv"]:
            await lagring._upp(storage, tenant_id, "crm_webhook_leveranser", leverans["id"], {
                "status": "misslyckad", "fel": "webhooken är avstängd"})
            utfall["misslyckade"] += 1
            continue
        statuskod, fel = await _skicka(webhook, leverans)
        nu = lagring.nu()
        if fel is None:
            await lagring._upp(storage, tenant_id, "crm_webhook_leveranser", leverans["id"], {
                "status": "levererad", "statuskod": statuskod, "fel": None, "levererad_at": nu})
            webhook = await lagring._upp(storage, tenant_id, "crm_webhooks", webhook["id"], {
                "fel_i_rad": 0, "senast_ok_at": nu}) or webhook
            utfall["levererade"] += 1
        else:
            slut = leverans["forsok"] > len(VANTETIDER)
            vanta = VANTETIDER[min(leverans["forsok"], len(VANTETIDER)) - 1]
            await lagring._upp(storage, tenant_id, "crm_webhook_leveranser", leverans["id"], {
                "status": "misslyckad" if slut else "vantar", "statuskod": statuskod, "fel": fel,
                "nasta_forsok_at": (datetime.now(timezone.utc) + timedelta(seconds=vanta)).isoformat()})
            i_rad = int(webhook.get("fel_i_rad") or 0) + 1
            andring: dict[str, Any] = {"fel_i_rad": i_rad, "senast_fel_at": nu, "senast_fel": fel}
            if i_rad >= MAX_FEL_I_RAD:
                andring.update(aktiv=False, avstangd_av="for_manga_fel")
                _aktiva.pop(str(tenant_id), None)
            webhook = await lagring._upp(storage, tenant_id, "crm_webhooks", webhook["id"], andring) or webhook
            utfall["misslyckade" if slut else "omforsok"] += 1
        hakar[webhook["id"]] = webhook
    return utfall


async def _har_ko(storage: Any, tenant_id: str) -> bool:
    return bool(await lagring._valj(storage, tenant_id, "crm_webhook_leveranser", lika={"status": "vantar"}, limit=1))


async def _gallra(storage: Any, tenant_id: str) -> None:
    """Leveransloggen sparas i trettio dagar."""
    grans = datetime.now(timezone.utc) - timedelta(days=LOGG_DAGAR)
    if lagring._ar_postgres(storage):
        try:
            async with storage._scoped(tenant_id) as conn:
                await conn.execute(
                    "delete from crm_webhook_leveranser where tenant_id = $1::text::uuid "
                    "and status <> 'vantar' and created_at < $2", tenant_id, grans)
        except Exception as fel:
            if not lagring._saknar_tabell(fel):
                raise
        return
    minne = lagring._minne(storage, "crm_webhook_leveranser")
    for lid in [k for k, r in minne.items() if r["tenant_id"] == tenant_id and r["status"] != "vantar"
                and lagring._tid(r["created_at"]) < grans]:
        del minne[lid]


async def kor_varv(storage: Any, *, alla: bool = False) -> int:
    """Ett varv av jobbet: de kunder som har något i kön. Med `alla` går det
    igenom varje kund, hittar köer en annan process lagt och gallrar loggen."""
    kunder = set(_vantande)
    if alla:
        kunder |= {str(t["id"]) for t in await storage.list_tenants()}
    skickade = 0
    for tenant_id in kunder:
        try:
            utfall = await leverera_for_kund(storage, tenant_id)
            skickade += sum(utfall.values())
            if alla:
                await _gallra(storage, tenant_id)
            if await _har_ko(storage, tenant_id):
                _vantande.add(tenant_id)
            else:
                _vantande.discard(tenant_id)
        except Exception:  # noqa: BLE001 — en kunds fel får inte stoppa de andras leveranser
            logger.exception("Webhook-leveransen föll för en kund. Fortsätter med nästa.")
    return skickade


async def run_webhookjobb(app_state: Any, *, intervall: float = 10.0, svep_var: int = 30) -> None:
    """Bakgrundsloopen. Var tionde sekund de kända köerna, var femte minut alla kunder."""
    logger.info("CRM:ets webhookjobb aktivt: var %s sekund.", intervall)
    varv = 0
    while True:
        try:
            await kor_varv(app_state.storage, alla=varv % svep_var == 0)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — jobbet får aldrig dö
            logger.exception("Oväntat fel i webhookjobbet. Fortsätter nästa varv.")
        varv += 1
        await asyncio.sleep(intervall)
