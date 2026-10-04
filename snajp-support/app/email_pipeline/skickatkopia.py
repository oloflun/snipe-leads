"""Kopia till Skickat: efter en RIKTIG sändning läggs mejlet i tenantens
kopplade inkorgs Skickat-mapp via IMAP APPEND.

## Varför

Utskicken (Iris kallmejl, supportsvaren) går över Resends HTTPS-API eller
plattformens SMTP — de passerar aldrig kundens eget mejlkonto, så Gmails
"Skickat" stod tomt och kunden undrade om något alls gått iväg
(rapporterat 2026-10-01, umeåwebdesign). Kopian ger kunden sitt vanliga
kvitto där kunden faktiskt tittar.

## Kontraktet

* Körs BARA efter en sändning som faktiskt levererat (`provider.levererar`)
  — en simulerad sändning i Skickat vore en lögn i kundens egen mejlklient.
* Kastar aldrig och får aldrig påverka sändningens status: 'sent' sattes av
  sändvägen, och en trasig kopia är en loggrad, inte ett sändfel.
* Återanvänder inkorgskopplingens uppgifter (ss_mailboxes + samma
  dekrypteringsväg som synken, poller.losenord_for). Ingen kopplad inkorg
  med lösenord = inget försök, tyst.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("snajp-support.skickatkopia")


async def kopiera_till_skickat(
    storage, tenant_id: str, *, till: str, amne: str, brodtext: str, fran: str = "",
    syfte: str = "support",
) -> str | None:
    """Lägger kopian i den synkbara inkorg vars syfte (migration 084) passar
    utskicket: samma syfte först, sedan 'bada', sist vilken som helst — en
    kund med en enda inkorg får kopian där som förut. None när kopian är
    lagd eller när det inte finns någon inkorg att lägga den i; annars ett
    felmeddelande för loggen. Kastar aldrig."""
    # Lata importer: poller drar in processorn, och den kedjan ska inte
    # betalas av moduler som bara råkar importera sändvägen.
    from .connectors import imap
    from .poller import host_for_mailbox, losenord_for

    try:
        tenant = await storage.get_tenant(tenant_id)
        slug = (tenant or {}).get("slug") or ""
        rang = {syfte: 0, "bada": 1}
        brevlador = sorted(await storage.list_mailboxes(tenant_id), key=lambda m: rang.get(m.get("syfte") or "support", 2))
        for mailbox in brevlador:
            if mailbox.get("status") != "active" or mailbox.get("provider") == "mock":
                continue
            host = host_for_mailbox(mailbox)
            losenord = losenord_for(mailbox, slug)
            if not host or not losenord:
                continue
            fel = await imap.spara_i_skickat(
                host,
                mailbox["address"],
                losenord,
                fran=fran or mailbox["address"],
                till=till,
                amne=amne,
                brodtext=brodtext,
            )
            if fel is None:
                logger.info(
                    "Kopia lagd i Skickat hos %s (till %s).", mailbox["address"], till
                )
            return fel
        return None
    except Exception as error:  # noqa: BLE001 — kopian får aldrig fälla sändvägen
        logger.exception("Skickat-kopian för tenant %s misslyckades.", tenant_id)
        return f"Kopian till Skickat misslyckades: {error}"
