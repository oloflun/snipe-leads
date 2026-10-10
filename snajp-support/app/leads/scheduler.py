"""Del J / Genomförandeordning steg 11: bakgrundskö och schemaläggare.

Speglar app/email_pipeline/poller.py:s mönster exakt (samma
asyncio.create_task-loop, samma "aldrig krascha tjänsten"-princip) i
stället för att lägga till APScheduler som ett nytt beroende för samma
jobb — kodbasen har redan en beprövad periodisk bakgrundsloop.

INV-SEC-004: modellen kan bara köa. process_due_item() är den ENDA
kodvägen i hela tjänsten som får sätta ett send_queue-item till 'sent'.
Grindarna körs igen här (app/leads/send_decision.decide_send_action) —
en köad tid kan ha passerat fönstret sedan den köades.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from ..config import get_settings
from ..storage.base import Storage
from .autonomy import allowed_action, normalize
from .send_decision import decide_send_action
from .send_guard import BLOCKERA as SG_BLOCKERA
from .send_guard import GRANSKA as SG_GRANSKA
from .send_guard import KOLA_OM as SG_KOLA_OM
from .send_guard import SKICKA as SG_SKICKA
from .send_guard import (
    Avsandare,
    GuardBeslut,
    TenantHistorik,
    Utskick,
    check_send_guard,
    foretagsnyckel,
)
from .send_provider import SendProvider, get_send_provider
from .signatur import HALSNING, med_signatur_fore_fot
from .signatur import bygg_html as bygg_signatur_html
from .signatur import normalisera as normalisera_signatur

logger = logging.getLogger("snajp-support.leads-scheduler")


async def _outbound_sent_count(storage: Storage, tenant_id: str, thread_id: str) -> int:
    """Hur många utgående meddelanden som redan gått iväg i tråden.

    Det är sekvensindexet för nästa: har inget skickats är nästa nr 0, alltså
    första kontakten. Räknas ur faktiskt skickade rader i stället för ur en
    räknarkolumn — en räknare hade kunnat glida isär med verkligheten, och
    det här är fältet som avgör om ett mejl går ut utan mänsklig granskning.
    """
    thread_messages = await storage.list_outreach_messages(tenant_id, thread_id)
    return sum(
        1
        for message in thread_messages
        if message.get("direction") == "outbound" and message.get("sent_at")
    )


async def _kor_send_guard(storage, tenant_id: str, thread: dict, message: dict, *, now, direkt: bool = False):
    """Samlar ihop fakta och låter `send_guard` döma.

    Uppdelningen är avsiktlig: den här funktionen gör I/O och ingen bedömning,
    `send_guard` gör bedömning och ingen I/O. Det är därför de sex reglerna
    går att testa utan databas, klocka eller mejlserver.

    Avsändaridentiteten kommer från tenantens konfiguration. Saknas något av
    de tre fälten faller regel 1 — vilket är rätt utfall: ett utskick utan
    lagstadgad avsändarinformation ska inte gå iväg bara för att vi glömt
    fylla i kunduppgifterna.
    """
    # Spärr noll: exempelbolag och egna provkörningar lämnar aldrig huset.
    #
    # Ett exempelbolag är påhittat (`leads/exempelbolag.py`) och finns för att
    # visa hur agenten arbetar innan kunden har en egen lista. Ett prospekt
    # med origin='test' (migration 054) är på samma sätt vårt EGET provande —
    # inte kundens data — och ska aldrig kunna leda till ett utskick bara för
    # att någon glömde växla tillbaka testläget. Kontrollen sitter HÄR och
    # inte i UI:t, av samma skäl som de sex reglerna gör det: det här är den
    # enda punkt där allt är känt samtidigt, och den enda som varje utskick
    # måste passera. Ett påhittat bolagsnamn kan råka vara ett riktigt bolag
    # — då är mejlet inte ofarligt, det är fel mottagare.
    prospect_id = thread.get("prospect_id")
    if prospect_id:
        prospect = await storage.get_prospect(tenant_id, prospect_id) or {}
        origin = prospect.get("origin")
        if origin in ("example", "test"):
            return GuardBeslut(
                SG_BLOCKERA,
                "exempelbolag" if origin == "example" else "testkorning",
                "Bolaget är ett exempelbolag och kan aldrig kontaktas."
                if origin == "example"
                else "Prospektet kommer från en egen provkörning och kan aldrig kontaktas.",
            )
        # Ett bolag som Iris själv hittat får bara kontaktas när det bedömts
        # mot hämtat källmaterial och klarat bedömningen (nivå A eller B).
        # Provkörningen 2026-10-05: tre påhittade bolag hade origin='iris',
        # ett färdigt utkast och ingenting som hindrade ett godkännande från
        # att bli ett utskick. Kundens egna bolag (origin 'manual', listor)
        # berörs inte: där har kunden själv pekat ut mottagaren.
        if origin == "iris" and prospect.get("niva") not in ("A", "B"):
            return GuardBeslut(
                SG_BLOCKERA,
                "ej_styrkt",
                "Bolaget är inte bedömt mot hämtat källmaterial och kan inte kontaktas.",
            )
        # Ett avslutat eller arkiverat lead (2026-10-08): "ej intresserad",
        # "kontakta inte" (samtal eller svar) och Arkivera är beslut som ett
        # godkännande från i går inte får gå förbi. Utkasten ställs in när
        # beslutet tas; spärren här fångar det som ändå hann bli liggande.
        if prospect.get("arkiverad_at"):
            return GuardBeslut(SG_BLOCKERA, "arkiverad", "Leadet är arkiverat och kontaktas inte.")
        if prospect.get("status") in ("lost", "suppressed"):
            return GuardBeslut(
                SG_BLOCKERA,
                "avslutad",
                "Leadet har avböjt eller bett att inte bli kontaktat."
                if prospect.get("status") == "suppressed"
                else "Leadet är markerat som ej intresserat.",
            )

    tenant = await storage.get_tenant(tenant_id) or {}
    dygnets_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    nyckel = thread.get("foretagsnyckel") or foretagsnyckel(
        orgnr=thread.get("prospect_orgnr"),
        epost=thread.get("prospect_email"),
        hemsida=thread.get("prospect_website"),
    )

    historik = TenantHistorik(
        skickade_totalt=await storage.count_sent_outreach(tenant_id),
        skickade_idag=await storage.count_sent_outreach(tenant_id, since=dygnets_start),
        tenant_alder_dagar=_alder_i_dagar(tenant.get("created_at"), now),
        # Leadets egen tråd räknas inte: 90-dagarsspärren gäller ett NYTT
        # kallmejl, inte uppföljningen eller svaret i samma samtal.
        senaste_kontakt_med_foretaget=await storage.last_contact_with_company(
            tenant_id, nyckel, utom_trad=thread.get("id")
        ),
        suppressions=frozenset(await storage.list_suppressions(tenant_id)),
        # Trådens egna tidigare kontakter räknas inte som "tidigare kontaktad" —
        # det är hela poängen med en uppföljning. Regel 3 gäller nya trådar.
        tidigare_kontaktade=frozenset(),
        # Supportens kundregister ÄR kundens kundlista: den som har ett ärende
        # hos tenantens support är en befintlig kund och ska inte kallmejlas.
        # Var frozenset() fram till 2026-09-20 — spärren fanns utan data.
        egna_kunder=frozenset(await storage.list_customer_emails(tenant_id)),
    )

    return check_send_guard(
        avsandare=Avsandare(
            foretagsnamn=str(tenant.get("company_name") or tenant.get("name") or ""),
            orgnr=str(tenant.get("orgnr") or ""),
            postadress=str(tenant.get("postal_address") or ""),
        ),
        utskick=Utskick(
            mottagare=thread.get("prospect_email") or "",
            amne=message.get("subject") or "",
            brodtext=message.get("body") or "",
            foretagsnyckel=nyckel,
            personlig_adress=_ar_personlig(thread.get("prospect_email")),
            direkt=direkt,
        ),
        historik=historik,
        nu=now,
    )


def _alder_i_dagar(created_at, now) -> int:
    """Tenantens ålder styr domänuppvärmningen (regel 5c).

    Okänt skapandedatum behandlas som NY, inte som gammal. Fail-closed: en
    tenant vi inte vet åldern på ska få det försiktigare taket, inte det
    generösare.
    """
    if not created_at:
        return 0
    try:
        return max((now - created_at).days, 0)
    except TypeError:
        return 0


def _ar_personlig(epost) -> bool:
    """Samma bedömning som `Prospect.epost_ar_personlig`, mot en lös adress."""
    from .sources.base import Prospect

    return Prospect(company_name="", contact_email=epost).epost_ar_personlig


#: Ett lås per send_queue-post. "Godkänn och skicka" skickar i requesten
#: medan `run_godkand_sandare` plockar samma post (queued + approved_by=human)
#: varje minut; inget i sändvägen gör anspråk på posten atomärt, så ett varv
#: mitt i requestens Resend-anrop hade skickat mejlet en gång till. Samma sak
#: vid ett dubbelklick. Låset gäller inom processen — api kör EN replika; fler
#: repliker kräver ett delat lås (se _korningslas och Redis).
_sandlas: dict[str, asyncio.Lock] = {}

#: Statusar en post kan skickas från. Allt annat är redan hanterat.
_SANDBARA = ("queued", "awaiting_review")

#: Godkänn och skicka tar också ett stoppat utkast (2026-10-09): en spärr som
#: sa nej (sidfoten saknades, leadet kom från en provkörning) kan vara
#: åtgärdad sedan dess, och alla spärrar prövas ändå om vid sändningen. Förut
#: var 'blocked' en slutstatus och utkastet måste skrivas om från början.
_GODKANNBARA = _SANDBARA + ("blocked",)


async def _fot_vid_godkannande(storage: Storage, tenant_id: str, item: dict) -> None:
    """Lägger på den lagstadgade foten om utkastet saknar den och
    kundregistret nu har underlaget. Foten är kodens text (utskicksfot.py),
    inte en ändring av det granskaren sagt ja till."""
    from ..agent.leads_tools import lagstadgad_fot
    from .outreach_playbook import _intervallstreck, tilltala_med_ni
    from .utskicksfot import har_fot

    thread = await storage.get_outreach_thread(tenant_id, item["thread_id"])
    message = await storage.get_pending_outreach_message(tenant_id, item["thread_id"]) if thread else None
    if not message:
        return
    # Kodens textputs (tilltal, tankstreck) även på utkast skrivna innan den
    # fanns (2026-10-09: "Hej Verkstad," i redan köade utkast). Rör bara
    # hälsningen och tilltalet, aldrig innehållet granskaren sagt ja till.
    ny = _intervallstreck(tilltala_med_ni(message["body"]))
    # Signaturen även på utkast köade innan tenanten satte den (Sebbe
    # 2026-10-09: alla utkast och mejl ska bära den). Före foten, som alltid
    # är sist.
    sig = normalisera_signatur(
        (await storage.get_agent_settings(tenant_id, agent_type="leads")).get("signatur")
    )
    if sig:
        sprak = "en" if thread.get("language_state") == "en_confirmed" else "sv"
        ny = med_signatur_fore_fot(ny, sig, halsning=HALSNING[sprak])
    if not har_fot(ny):
        ny = await lagstadgad_fot(storage, tenant_id, thread.get("prospect_email"), ny)
    if ny != message["body"]:
        await storage.update_outreach_message_text(
            tenant_id, message["id"], subject=message.get("subject") or "", body=ny
        )


async def process_due_item(
    storage: Storage,
    tenant_id: str,
    item: dict,
    provider: SendProvider,
    *,
    now: datetime,
    godkant: dict | None = None,
) -> str:
    """Kör `_process_due_item` under postens sändlås, och bara om posten
    fortfarande väntar när låset är taget ('redan_hanterad' annars)."""
    nyckel = str(item.get("id"))
    # Låsen städas inte: ett lås per skickad post och process är bytes, och
    # en städning mellan släpp och nästa väntares tag hade öppnat luckan igen.
    async with _sandlas.setdefault(nyckel, asyncio.Lock()):
        farsk = await storage.get_send_queue_item(tenant_id, nyckel) if item.get("id") else None
        if farsk is not None and farsk.get("status") not in _SANDBARA:
            return "redan_hanterad"
        return await _process_due_item(storage, tenant_id, item, provider, now=now, godkant=godkant)


async def _process_due_item(
    storage: Storage,
    tenant_id: str,
    item: dict,
    provider: SendProvider,
    *,
    now: datetime,
    godkant: dict | None = None,
    direkt: bool = False,
) -> str:
    """Returnerar 'sent' | 'requeued' | 'blocked' | 'awaiting_review'.

    `direkt` (Skicka nu ur kön, Anton 2026-10-10): sändfönstret (tidsgrinden
    och regel 5a) gäller inte; språkgrinden och övriga spärrar gör det.

    `godkant` (2026-10-07): en människa har godkänt just det här utkastet i
    granskningskön. Då är autonominivån redan besvarad — det är människan
    nivån lämnar över till — men tidsgrinden (INV-TIME-001), språkgrinden
    och alla sex sändspärrarna körs som vanligt. Godkännandet följer med i
    varje statusskrivning, så att ett utkast som väntar på sändfönstret
    fortfarande är godkänt när fönstret öppnar."""

    async def satt_status(*, status: str, gate_checks: dict) -> None:
        await storage.update_send_queue_status(
            tenant_id, item["id"], status=status, gate_checks={**gate_checks, **(godkant or {})}
        )
    thread = await storage.get_outreach_thread(tenant_id, item["thread_id"])
    message = (
        await storage.get_pending_outreach_message(tenant_id, item["thread_id"]) if thread else None
    )
    decision = decide_send_action(now=now, thread=thread, message=message)
    if direkt and decision.action == "requeue":
        # Bara tidsgrinden ger requeue; språkgrinden prövas här i stället.
        from .send_decision import LanguageGateError, SendDecision, check_send_gate

        try:
            check_send_gate(
                language_state=thread.get("language_state", "sv"),
                humanizer_variant=message.get("humanizer_variant"),
            )
            decision = SendDecision("send", "Skicka nu: en människa valde att skicka utanför sändfönstret")
        except LanguageGateError as fel:
            decision = SendDecision("block", str(fel))

    # Andra anropsplatsen för autonomiregeln. Grinden vid köningen räcker inte:
    # ett item kan ha köats innan kunden sänkte sin nivå, och det som ligger i
    # kön ska då stoppas — inte skickas för att det hann bli godkänt av en
    # regel som gällde igår.
    #
    # sequence_index räknas ur trådens redan skickade utgående meddelanden.
    if decision.action == "send" and not godkant:
        sent_before = await _outbound_sent_count(storage, tenant_id, item["thread_id"])
        settings = await storage.get_agent_settings(tenant_id, agent_type="leads")
        if allowed_action(settings.get("autonomy"), sent_before) != "send":
            await satt_status(status="awaiting_review",
                gate_checks={
                    "decision": decision.reason,
                    "autonomy": normalize(settings.get("autonomy")),
                    "held": "autonominivån tillåter inte utskick av det här steget",
                },
            )
            return "awaiting_review"

    if decision.action == "send":
        # DEL 2.3: de sex spärrarna. De körs SIST, direkt före provider.send(),
        # därför att det är den enda punkt där allt är känt samtidigt —
        # mottagaren, den färdiga texten, klockan och tenantens historik.
        #
        # En guard som körts vid köningen hade dömt på gårdagens sanning: en
        # mottagare kan ha avregistrerat sig medan utkastet låg i kön.
        guard = await _kor_send_guard(storage, tenant_id, thread, message, now=now, direkt=direkt)
        # Regel 6 kräver att en människa granskar de tre första utskicken. Ett
        # godkänt utkast ÄR den granskningen; alla andra spärrar gäller.
        granskat = godkant and guard.regel == "6_granskningsko"
        if guard.atgard != SG_SKICKA and not granskat:
            status = {
                SG_BLOCKERA: "blocked",
                SG_GRANSKA: "awaiting_review",
                SG_KOLA_OM: "queued",
            }[guard.atgard]
            await satt_status(status=status,
                gate_checks={
                    "decision": decision.reason,
                    "send_guard_regel": guard.regel,
                    "send_guard_skal": guard.skal,
                },
            )
            logger.info(
                "send_guard %s stoppade %s: %s", guard.regel, item.get("id"), guard.skal
            )
            return {
                "blocked": "blocked",
                "awaiting_review": "awaiting_review",
                "queued": "requeued",
            }[status]

        # HTML-delen renderas ur den GRANSKADE texten i sändögonblicket —
        # signaturens logotyp finns bara där (app/leads/signatur.py). Mjukt
        # kontrakt som i email_pipeline/sender.py: bara providers som tar
        # `html` får den; testernas fejkproviders med smala signaturer berörs
        # inte, och textdelen är alltid exakt send_queue.body.
        import inspect

        extra: dict = {}
        params = inspect.signature(provider.send).parameters
        har_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
        sig = normalisera_signatur(
            (await storage.get_agent_settings(tenant_id, agent_type="leads")).get("signatur")
        )
        if sig and ("html" in params or har_kwargs):
            extra["html"] = bygg_signatur_html(message["body"], sig)
        # Avsändare och svarsadress (Sebbe 2026-10-07: svaren ska synas i
        # Leads › Inkorg). Förut gick utskicket från plattformens adress utan
        # Reply-To, så prospektets svar hamnade där och aldrig i kundens
        # synkade brevlåda — den inkorgen läser. Samma mjuka kontrakt som
        # email_pipeline/sender.py: bara providers som tar parametrarna.
        if "reply_to" in params or har_kwargs:
            extra.update(await _avsandaridentitet(storage, tenant_id))

        await provider.send(
            to=thread.get("prospect_email", "okänd"),
            subject=message.get("subject", ""),
            body=message["body"],
            **extra,
        )
        await storage.mark_outreach_message_sent(tenant_id, message["id"], now)
        await satt_status(status="sent", gate_checks={"decision": decision.reason}
        )
        # Ett skickat första mejl gör bolaget Kontaktat — statusen sattes förut
        # bara för hand, och fliken Kontaktad stod tom fast mejlen gått ut.
        # Bara framåt: ett bolag som redan svarat eller bokat möte flyttas inte
        # tillbaka.
        if thread.get("prospect_id"):
            prospekt = await storage.get_prospect(tenant_id, thread["prospect_id"]) or {}
            if prospekt and (prospekt.get("status") or "new") in ("new", "researching", "ready"):
                await storage.update_prospect(tenant_id, thread["prospect_id"], status="contacted")
        if getattr(provider, "levererar", False):
            # Riktiga utskick passerar aldrig kundens eget mejlkonto (Resend/
            # SMTP) — kopian är det som gör att de syns i kundens "Skickat".
            # Efter statusskrivningarna med flit: kopian får aldrig påverka
            # eller fördröja 'sent', och kopiera_till_skickat kastar aldrig.
            from ..email_pipeline import skickatkopia

            await skickatkopia.kopiera_till_skickat(
                storage,
                tenant_id,
                till=thread.get("prospect_email", ""),
                amne=message.get("subject", ""),
                brodtext=message["body"],
                fran=extra.get("from_email") or getattr(provider, "avsandare", ""),
                syfte="leads",
            )
        return "sent"

    if decision.action == "block":
        await satt_status(status="blocked", gate_checks={"decision": decision.reason}
        )
        return "blocked"

    # requeue: status förblir 'queued' — fångas upp igen nästa gång fönstret är öppet.
    await satt_status(status="queued", gate_checks={"decision": decision.reason}
    )
    return "requeued"


async def avbryt_utskick_for_prospekt(storage: Storage, tenant_id: str, prospect_id: str) -> int:
    """Ställer in leadets väntande utskick och kasserar osända utkast.

    Arkivera, ett avslutande samtalsutfall (ej intresserad, kontakta inte,
    möte) och Skapa om utkast går hit: inget som skrevs före beslutet får gå
    ut efter det. Returnerar antalet inställda köposter."""
    trad = await storage.find_outreach_thread(tenant_id, prospect_id=prospect_id)
    return await storage.cancel_pending_sends(tenant_id, trad["id"]) if trad else 0


def godkannande(item: dict) -> dict | None:
    """Godkännandet ur postens grindanteckningar, eller None."""
    gc = item.get("gate_checks") or {}
    if isinstance(gc, str):
        import json

        try:
            gc = json.loads(gc)
        except ValueError:
            return None
    if gc.get("approved_by") != "human":
        return None
    return {k: gc[k] for k in ("approved_by", "via", "godkand_at") if k in gc}


async def _avsandaridentitet(storage: Storage, tenant_id: str) -> dict:
    """from_email/from_name/reply_to för ett leadsutskick.

    Från: tenantens verifierade sändningsdomän, annars providerns standard
    (samma regel som supportsvaren, email_pipeline/sender.py). Svar till: den
    synkade brevlådan, leads-brevlådan först (migration 084), så att
    prospektets svar når kundens inkorg, klassas som lead
    (email_pipeline/klassning: avsändaren matchar prospektet) och syns i
    Leads › Inkorg. Utan synkad brevlåda: domänens egen reply_to, annars
    ingen — då går svaret till avsändaradressen som förut."""
    ut: dict = {}
    try:
        from ..sending_domains import get_config

        cfg = await get_config(storage, tenant_id)
        if cfg and cfg.get("status") == "verified":
            ut["from_email"] = f"{cfg['from_local_part']}@{cfg['sending_domain']}"
            ut["from_name"] = cfg.get("from_name") or None
            if cfg.get("reply_to"):
                ut["reply_to"] = cfg["reply_to"]
    except Exception:  # noqa: BLE001 — identiteten får aldrig fälla ett utskick
        logger.exception("Sändningsdomänen kunde inte läsas för %s", tenant_id)
    try:
        rang = {"leads": 0, "bada": 1}
        brevlador = [
            m
            for m in await storage.list_mailboxes(tenant_id)
            if m.get("status") == "active" and m.get("provider") != "mock" and m.get("address")
        ]
        if brevlador:
            basta = min(brevlador, key=lambda m: rang.get(m.get("syfte") or "support", 2))
            ut["reply_to"] = basta["address"]
    except Exception:  # noqa: BLE001
        logger.exception("Brevlådorna kunde inte läsas för %s", tenant_id)
    return ut


async def skicka_godkant(
    storage: Storage, tenant_id: str, item_id: str, provider: SendProvider, *, now: datetime,
    direkt: bool = False,
) -> tuple[str, str | None]:
    """Granskarens "Godkänn och skicka" (2026-10-07): (utfall, skäl).

    Utfall: 'sent', 'requeued' (godkänt, väntar på sändfönstret 08–16
    vardagar), 'blocked'/'awaiting_review' (en sändspärr sa nej, skälet
    följer med), 'saknas' eller 'redan_hanterad'."""
    # Hela läs-godkänn-skicka under postens sändlås: ett dubbelklick hade
    # annars läst 'awaiting_review', väntat ut det första anropet och sedan
    # skrivit tillbaka 'queued' över 'sent'.
    async with _sandlas.setdefault(str(item_id), asyncio.Lock()):
        item = await storage.get_send_queue_item(tenant_id, item_id)
        if item is None:
            return "saknas", None
        if item.get("status") not in _GODKANNBARA:
            return "redan_hanterad", None
        # Ett stoppat utkast skickas bara om det är trådens enda: finns ett
        # nyare väntande utkast är det det som gäller (sändaren tar trådens
        # senaste osända text).
        if item.get("status") == "blocked" and await storage.list_pending_sends(tenant_id, item["thread_id"]):
            return "redan_hanterad", None
        if item.get("status") == "blocked" and not await storage.get_pending_outreach_message(
            tenant_id, item["thread_id"]
        ):
            return "blocked", "Utkastet finns inte längre. Välj Skapa utkast för att skriva ett nytt."
        await _fot_vid_godkannande(storage, tenant_id, item)
        godkant = {"approved_by": "human", "via": "granskningskön", "godkand_at": now.isoformat()}
        await storage.update_send_queue_status(tenant_id, item_id, status="queued", gate_checks=godkant)
        utfall = await _process_due_item(
            storage, tenant_id, {**item, "status": "queued"}, provider, now=now, godkant=godkant, direkt=direkt
        )
    efter = await storage.get_send_queue_item(tenant_id, item_id) or {}
    gc = efter.get("gate_checks") or {}
    if isinstance(gc, str):
        import json

        gc = json.loads(gc)
    skal = gc.get("send_guard_skal") or gc.get("held") or gc.get("decision")
    return utfall, (None if utfall == "sent" else skal)


def _efter(tidpunkt, seedad: str) -> bool:
    """Ligger tidpunkten (ISO-sträng eller datetime) efter speglingen?"""
    if hasattr(tidpunkt, "isoformat"):
        tidpunkt = tidpunkt.isoformat()
    return bool(tidpunkt) and str(tidpunkt) > seedad


def tvavags(spegel: dict | None) -> bool:
    """Development i tvåvägssynk med main (scripts/railway_synk.py, Anton
    2026-10-10): main skickar, följer upp, läser inkorgarna och kör
    autopiloten, och synken för tillbaka utfallet. Development gör inget av
    det, annars skickades varje mejl två gånger och varje inkommande mejl blev
    två ärenden."""
    return bool(spegel) and (spegel or {}).get("lage") == "tvavags"


async def process_godkanda(storage: Storage, provider: SendProvider) -> list[dict]:
    """Skickar BARA utkast en människa har godkänt och som väntat på
    sändfönstret. Autonomt köade utkast rörs inte — den vägen är
    schemaläggaren (SEND_QUEUE_POLL_SECONDS), som är avstängd.

    I en spegel (development, mirror_meta) räknas bara godkännanden gjorda
    EFTER speglingen: ett godkännande som kopierats in från produktionen
    skickas av produktionen, och hade annars gått ut två gånger.

    En köpost som SKAPATS efter speglingen finns bara i spegeln, så dess
    godkännande kan inte vara produktionens (2026-10-08). Godkännanden gjorda
    före 2026-10-07 saknar godkand_at och stod annars kvar i kön för evigt,
    medan listan lovade att de skickas när fönstret öppnar."""
    now = datetime.now(timezone.utc)
    spegel = None
    try:
        spegel = await storage.spegel_info()
    except Exception:  # noqa: BLE001 — en trasig markörläsning ska fela åt det försiktiga hållet
        logger.exception("Kunde inte läsa spegelmarkören — hoppar över godkända utskick.")
        return []
    if tvavags(spegel):
        return []
    seedad = str((spegel or {}).get("seeded_at") or "")
    results: list[dict] = []
    for tenant in await storage.list_tenants():
        for item in await storage.list_due_send_queue(tenant["id"], now):
            godkant = godkannande(item)
            if not godkant:
                continue
            if spegel and not (_efter(godkant.get("godkand_at"), seedad) or _efter(item.get("created_at"), seedad)):
                continue
            try:
                outcome = await process_due_item(storage, tenant["id"], item, provider, now=now, godkant=godkant)
            except Exception:  # noqa: BLE001
                logger.exception("Godkänt utkast %s misslyckades oväntat", item.get("id"))
                outcome = "error"
            results.append({"tenant": tenant.get("slug"), "item_id": item.get("id"), "outcome": outcome})
    return results


#: Bevakningen i sändaren för godkända utkast: uppföljningssvepet körs högst
#: så här ofta. Förfallodagarna räknas i dygn, men ett svar som kommer in ska
#: inte hinna mötas av en uppföljning skriven en timme tidigare — och svepet är
#: billigt när inget är förfallet (en fråga per tenant, ingen modell).
BEVAKNING_SEKUNDER = 600


async def run_godkand_sandare(app_state) -> None:
    """Bakgrundsloopen för godkända utkast som väntar på sändfönstret.

    Sedan 2026-10-08 kör den också bevakningen: uppföljningssvepet, högst var
    tionde minut. Före det startade svepet bara med SEND_QUEUE_POLL_SECONDS>0,
    osatt i båda miljöerna, och ingen uppföljning skrevs någonsin. Svepet
    skriver BARA utkast till granskning (force_review i
    follow_up_generator), aldrig autonoma utskick."""
    import time as _time

    interval = max(get_settings().godkanda_utskick_sekunder, 30)
    provider = get_send_provider()
    logger.info("Sändare för godkända utkast aktiv: var %s sekund.", interval)
    senaste_svep = 0.0
    while True:
        try:
            for result in await process_godkanda(app_state.storage, provider):
                if result["outcome"] != "requeued":
                    logger.info("godkänt utkast %s (%s): %s", result["item_id"], result["tenant"], result["outcome"])
        except Exception:  # noqa: BLE001 — loopen får aldrig dö
            logger.exception("Oväntat fel i sändaren för godkända utkast — fortsätter nästa varv.")
        try:
            if _time.monotonic() - senaste_svep >= BEVAKNING_SEKUNDER:
                senaste_svep = _time.monotonic()
                for rad in await sweep_follow_ups(app_state.storage):
                    logger.info("uppföljning (%s): %s", rad.get("tenant"), rad)
        except Exception:  # noqa: BLE001 — svepet får inte döda sändaren
            logger.exception("Oväntat fel i bevakningen — fortsätter nästa varv.")
        await asyncio.sleep(interval)


async def process_all_due(storage: Storage, provider: SendProvider) -> list[dict]:
    now = datetime.now(timezone.utc)
    results: list[dict] = []
    for tenant in await storage.list_tenants():
        for item in await storage.list_due_send_queue(tenant["id"], now):
            try:
                outcome = await process_due_item(
                    storage, tenant["id"], item, provider, now=now, godkant=godkannande(item)
                )
            except Exception:  # noqa: BLE001 — en trasig post stoppar inte de andra
                logger.exception("send_queue-post %s misslyckades oväntat", item.get("id"))
                outcome = "error"
            results.append({"tenant": tenant["slug"], "item_id": item.get("id"), "outcome": outcome})
    return results


#: Uppföljningssvepet körs högst så här ofta. Send-loopen tickar var ~30:e
#: sekund; att LLM-generera i den takten vore fel växel — förfallodagarna
#: räknas i dygn (FOLLOW_UP_DELAYS), så en timme är gott och väl tätt nog.
FOLLOW_UP_SWEEP_SECONDS = 3600


#: Ett svep i taget per process: sändaren för godkända utkast och den gamla
#: schemaläggaren (SEND_QUEUE_POLL_SECONDS) kan båda köra det, och två svep
#: samtidigt hade hunnit skriva två uppföljningar i samma tråd innan
#: has_pending_item såg den första.
_svepslas = asyncio.Lock()


async def sweep_follow_ups(storage: Storage) -> list[dict]:
    """Ett uppföljningssvep över alla tenants. Del av schemaläggarloopen och
    av bevakningen i run_godkand_sandare.

    Hoppar över simulering (inga LLM-anrop utan modell) och tenants utan
    affärskontext (utan den finns inget att grunda ett mejl i — och inget
    initialt mejl kan ha gått ut den vägen heller). Ett trasigt tenantsvep
    fäller inte de andras, samma princip som process_all_due.

    Spegelvakten (2026-10-08): i en spegel (development, mirror_meta) får bara
    trådar vars FÖRSTA utskick gick efter speglingen följas upp. Trådarna som
    kopierats från produktionen följs upp av produktionen; development hade
    annars skrivit en andra uppföljning till samma riktiga bolag. Går
    markören inte att läsa körs inget svep alls — åt det försiktiga hållet,
    samma princip som process_godkanda.
    """
    from datetime import datetime, timezone as _tz

    from .context_pack import build_context_pack
    from .follow_up_generator import generate_due_follow_ups

    if get_settings().is_simulation():
        return []
    try:
        spegel = await storage.spegel_info()
    except Exception:  # noqa: BLE001
        logger.exception("Kunde inte läsa spegelmarkören — hoppar över uppföljningssvepet.")
        return []
    if tvavags(spegel):
        return []
    seedad = (spegel or {}).get("seeded_at")
    if spegel and not seedad:
        logger.warning("Spegel utan seeded_at — hoppar över uppföljningssvepet.")
        return []

    async with _svepslas:
        now = datetime.now(_tz.utc)
        resultat: list[dict] = []
        for tenant in await storage.list_tenants():
            try:
                context_pack, missing = await build_context_pack(storage, tenant["id"])
                if "product_marketing" in missing:
                    continue
                for rad in await generate_due_follow_ups(
                    storage,
                    tenant["id"],
                    now=now,
                    tenant_name=tenant.get("name") or tenant.get("slug") or "",
                    context_pack=context_pack,
                    forst_skickad_efter=seedad,
                ):
                    resultat.append({"tenant": tenant.get("slug"), **rad})
            except Exception:  # noqa: BLE001 — en tenant fäller inte svepet
                logger.exception("Uppföljningssvepet för %s misslyckades.", tenant.get("slug"))
        return resultat


async def run_send_scheduler(app_state) -> None:
    settings = get_settings()
    interval = max(settings.send_queue_poll_seconds, 30)
    provider = get_send_provider()
    logger.info("send_queue-schemaläggare aktiv: var %s sekund.", interval)
    senaste_svep = 0.0
    while True:
        try:
            for result in await process_all_due(app_state.storage, provider):
                if result["outcome"] != "requeued":
                    logger.info(
                        "send_queue %s (%s): %s",
                        result["item_id"],
                        result["tenant"],
                        result["outcome"],
                    )
        except Exception:  # noqa: BLE001 — schemaläggaren får aldrig dö
            logger.exception("Oväntat fel i send_queue-schemaläggaren — fortsätter nästa varv.")
        try:
            import time as _time

            if _time.monotonic() - senaste_svep >= FOLLOW_UP_SWEEP_SECONDS:
                senaste_svep = _time.monotonic()
                for rad in await sweep_follow_ups(app_state.storage):
                    logger.info("uppföljning (%s): %s", rad.get("tenant"), rad)
        except Exception:  # noqa: BLE001 — svepet får inte döda send-loopen
            logger.exception("Oväntat fel i uppföljningssvepet — fortsätter nästa varv.")
        await asyncio.sleep(interval)
