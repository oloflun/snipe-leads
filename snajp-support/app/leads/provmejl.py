"""Provmejl: ett leadsutkast eller skickat leadsmejl skickat till kunden själv.

## Varför

Sebbe 2026-10-09: "vi vill se hur utskicken ser ut", från kundens håll.
Granskningsvyn visar texten, men inte vad mottagaren får i sin mejlklient:
HTML-delen med signaturens logotyp, avsändarnamnet och svarsadressen. Ett
provmejl går genom samma rendering som det riktiga utskicket
(scheduler._process_due_item): samma text, samma `bygg_html`, samma
avsändaridentitet.

## Det här är INTE ett utskick

- Mottagaren är alltid en av kundens EGNA adresser (`tillatna_mottagare`):
  kopplade brevlådor, signaturens e-post, faktureringsmejlet och
  sändningsdomänens svarsadress. Annars hade knappen varit en väg förbi
  sändspärrarna (send_guard), sändfönstret och spärrlistan till en
  godtycklig adress.
- Ingenting skrivs: köpostens status, meddelandets sent_at, prospektets
  status och kundens Skickat-kopia rörs inte. Utkastet kan godkännas
  efteråt som om provet aldrig skickats.
- Mejlet bär `Auto-Submitted: auto-generated`. Kundens brevlåda är ofta
  synkad till Snajps inkorg, och utan headern hade provet blivit ett ärende
  som supportagenten svarar på (klassning.py: automatutskick är aldrig ett
  ärende).

Saknar utkastet den lagstadgade foten (kundregistret saknar org.nr eller
adress) skickas provet ändå, men svaret säger det: det riktiga utskicket
stoppas av send_guard regel 1 tills uppgifterna finns.
"""

from __future__ import annotations

import inspect
import logging

from ..storage.base import Storage
from .send_provider import SendProvider
from .signatur import HALSNING, bygg_html, med_signatur_fore_fot
from .signatur import normalisera as normalisera_signatur
from .utskicksfot import har_fot

logger = logging.getLogger(__name__)

#: Headrarna som skiljer ett provmejl från ett utskick hos mottagaren.
PROVHEADRAR = {"Auto-Submitted": "auto-generated", "X-Snajp-Provmejl": "1"}


class ProvmejlFel(Exception):
    """Ett provmejl som inte gick att skicka: HTTP-status och kundens text."""

    def __init__(self, status: int, text: str) -> None:
        super().__init__(text)
        self.status = status
        self.text = text


def _adress(varde: object) -> str:
    text = str(varde or "").strip().casefold()
    return text if "@" in text and " " not in text else ""


async def tillatna_mottagare(storage: Storage, tenant_id: str) -> list[str]:
    """Kundens egna adresser, i ordningen knappen föreslår dem."""
    adresser: list[str] = []

    def lagg_till(varde: object) -> None:
        adress = _adress(varde)
        if adress and adress not in adresser:
            adresser.append(adress)

    try:
        sig = (await storage.get_agent_settings(tenant_id, agent_type="leads")).get("signatur") or {}
        if isinstance(sig, dict):
            lagg_till(sig.get("epost"))
    except Exception:  # noqa: BLE001 — en adresskälla som faller ska inte fälla de andra
        logger.exception("Signaturen kunde inte läsas för provmejl (%s)", tenant_id)
    try:
        for m in await storage.list_mailboxes(tenant_id):
            if m.get("provider") != "mock":
                lagg_till(m.get("address"))
    except Exception:  # noqa: BLE001
        logger.exception("Brevlådorna kunde inte läsas för provmejl (%s)", tenant_id)
    try:
        lagg_till(((await storage.get_customer_details(tenant_id)) or {}).get("faktureringsmejl"))
    except Exception:  # noqa: BLE001
        logger.exception("Kundregistret kunde inte läsas för provmejl (%s)", tenant_id)
    try:
        from ..sending_domains import get_config

        lagg_till(((await get_config(storage, tenant_id)) or {}).get("reply_to"))
    except Exception:  # noqa: BLE001
        logger.exception("Sändningsdomänen kunde inte läsas för provmejl (%s)", tenant_id)
    return adresser


async def _meddelande(
    storage: Storage, tenant_id: str, *, queue_item_id: str | None, message_id: str | None
) -> tuple[dict, dict | None]:
    """(meddelandet, tråden) för ett utkast i kön eller ett skickat mejl."""
    if queue_item_id:
        item = await storage.get_send_queue_item(tenant_id, queue_item_id)
        if item is None:
            raise ProvmejlFel(404, "Utkastet finns inte.")
        thread = await storage.get_outreach_thread(tenant_id, item["thread_id"])
        message = await storage.get_pending_outreach_message(tenant_id, item["thread_id"]) if thread else None
        if not message:
            raise ProvmejlFel(404, "Utkastet har ingen text längre.")
        return message, thread
    for rad in await storage.list_skickade(tenant_id, limit=500):
        if str(rad.get("id")) == str(message_id):
            thread = await storage.get_outreach_thread(tenant_id, rad["thread_id"])
            return rad, thread
    raise ProvmejlFel(404, "Mejlet finns inte.")


async def skicka_provmejl(
    storage: Storage,
    tenant_id: str,
    provider: SendProvider,
    *,
    till: str,
    queue_item_id: str | None = None,
    message_id: str | None = None,
) -> dict:
    """Skickar provet. Returnerar {till, saknar_fot}; kastar ProvmejlFel."""
    if bool(queue_item_id) == bool(message_id):
        raise ProvmejlFel(422, "Ange antingen ett utkast eller ett skickat mejl.")
    adress = _adress(till)
    if not adress or adress not in await tillatna_mottagare(storage, tenant_id):
        raise ProvmejlFel(
            403,
            "Provmejl går bara till era egna adresser: en kopplad brevlåda, signaturens "
            "e-post eller faktureringsmejlet.",
        )
    if not getattr(provider, "levererar", False):
        raise ProvmejlFel(503, "Utskick är inte påslagna i den här miljön, så provmejlet kan inte levereras.")

    message, thread = await _meddelande(
        storage, tenant_id, queue_item_id=queue_item_id, message_id=message_id
    )
    body = message.get("body") or ""
    sig = normalisera_signatur(
        (await storage.get_agent_settings(tenant_id, agent_type="leads")).get("signatur")
    )
    if sig and not message.get("sent_at"):
        # Ett utkast köat före signaturen får den vid godkännandet
        # (scheduler._fot_vid_godkannande); provet visar texten så som den då
        # skickas. Ett redan skickat mejl visas som det gick ut.
        sprak = "en" if (thread or {}).get("language_state") == "en_confirmed" else "sv"
        body = med_signatur_fore_fot(body, sig, halsning=HALSNING[sprak])

    params = inspect.signature(provider.send).parameters
    har_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
    extra: dict = {}
    if sig and ("html" in params or har_kwargs):
        extra["html"] = bygg_html(body, sig)
    if "reply_to" in params or har_kwargs:
        from .scheduler import _avsandaridentitet

        extra.update(await _avsandaridentitet(storage, tenant_id))
    if "headers" in params or har_kwargs:
        extra["headers"] = dict(PROVHEADRAR)

    try:
        await provider.send(to=adress, subject=message.get("subject") or "", body=body, **extra)
    except Exception as error:  # noqa: BLE001 — leverantörens fel är kundens besked
        logger.exception("Provmejl misslyckades för %s", tenant_id)
        raise ProvmejlFel(502, f"Provmejlet kunde inte skickas: {error}") from error
    logger.info("Provmejl skickat för %s (%s)", tenant_id, "utkast" if queue_item_id else "skickat mejl")
    return {"till": adress, "saknar_fot": not har_fot(body)}
