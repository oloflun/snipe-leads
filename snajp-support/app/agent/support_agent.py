"""Snajp-Support: support/v1 som EN LLM-KÖRNING PER SKILL-STEG (Del C).

Tidigare version konkatenerade alla sju cs:-skills till en systemprompt och
lät en agentloop göra allt. Det gjorde läsgarantin overifierbar: man kunde
se vad som INJICERATS, aldrig vad som faktiskt använts.

Nu: varje steg är ett eget JSON-anrop med eget utdatakontrakt
(app/agent/step_runner.py), och SIDOEFFEKTERNA görs i kod här — inte av
modellen via verktyg. Modellen resonerar, koden agerar. Det gör att
- ett ärende alltid får kund/ärende/meddelanden sparade i rätt ordning,
- eskalering aldrig är beroende av att modellen kom ihåg att anropa ett verktyg,
- hela kedjan loggas till agent_runs.step_log (G10) och kan granskas i efterhand.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import re
import time
from collections.abc import Awaitable, Callable
from functools import partial
from typing import Any

from ..agentcore.instruktioner import las_instruktioner
from ..agentcore.overlays import pack_version
from ..agentcore.packs import RunLedger
from ..cache import svarscache, versioner
from ..minne import arbetsminne
from ..moderation.abuse_gate import check_abuse, ton_instruktion
from ..moderation.maskering import maskera_personnummer
from ..leads.soul import load_soul
from ..notifications.prioriterat_mejl import arendelank, skicka_prioriterat
from ..leads.untrusted_content import wrap_untrusted_content
from ..config import CATEGORY_LABELS, get_settings
from ..storage.base import Storage
from .retention_classifier import classify_cancellation_risk, is_cancellation_risk
from .step_runner import RunTrace, run_step
from .support_playbook import SUPPORT_V1
from .tools import strip_markdown
from .vision import describe_image

logger = logging.getLogger("snajp-support.support-agent")

# Sentiment under denna tröskel eskalerar oavsett vad modellen tycker
# (samma regel som tidigare låg i den handskrivna prompten).
SENTIMENT_ESCALATION_THRESHOLD = 0.3

# Hur mycket av samtalet som följer med in i prompten. Varje meddelande i
# chatten öppnar ett eget ärende, så "tidigare turer" är tidigare ärenden för
# samma kund.
MAX_HISTORY_TICKETS = 3
MAX_HISTORY_TURNS = 8

# Samma fel som i leads (_DANGLING_SIGN_OFF där): modellen skriver
# "Vänliga hälsningar," och sedan ett namn eller en platshållare som
# strip_placeholders plockar bort. I ett mejl löses det genom att sätta dit
# avsändaren; i en chatt finns ingen avsändare att sätta dit, så raden ska bort.
_DANGLING_SIGN_OFF = re.compile(
    r"\n*\s*(?:med\s+vänliga\s+hälsningar|vänliga\s+hälsningar|hälsningar|mvh|"
    r"bästa\s+hälsningar|vänligen)\s*[,.!]?\s*$",
    re.IGNORECASE,
)


def strip_dangling_sign_off(text: str) -> str:
    """Tar bort en avslutningsfras som inte följs av något.

    Grinden ligger i kod och inte bara i overlayen eftersom felet uppträdde i
    BÅDA thinking-lägena — samma resonemang som strip_placeholders. En regel som
    bara står i en instruktion är en förhoppning.
    """
    return _DANGLING_SIGN_OFF.sub("", text.rstrip()).rstrip()


async def _render_conversation(
    storage, tenant_id: str, customer_id: str, history: list
) -> tuple[str, int, str]:
    """Tidigare turer som en läsbar utskrift, antalet turer, och kundens
    SENASTE tidigare replik.

    Utan utskriften fick utkaststeget bara ANTALET tidigare kontakter — en
    siffra, aldrig samtalet. Modellen kunde därför inte veta att den var mitt
    i ett samtal, och varje svar blev formellt sett ett första meddelande:
    "Hej" på varje replik och "Vänliga hälsningar," under varje.

    Den senaste kundrepliken returneras separat för KB-sökningen: i en
    fortsättning är det nya meddelandet ofta bara ett svar på vår motfråga
    ("Ja, en Android") och bär inte ämnet — det gör den förra repliken.
    """
    turns: list[str] = []
    senaste_kundreplik = ""
    for ticket in reversed(history[:MAX_HISTORY_TICKETS]):  # äldst först
        for msg in await storage.get_messages(tenant_id, ticket["conversation_id"]):
            who = "Kunden" if msg["direction"] == "inbound" else "Du"
            content = (msg.get("content") or "").strip()
            if content:
                turns.append(f"{who}: {content}")
                if msg["direction"] == "inbound":
                    senaste_kundreplik = content

    if not turns:
        return "", 0, ""

    # Fas R3 (bd snipe-7mk, arbetsminne — app/minne/arbetsminne.py): taket
    # ovan (MAX_HISTORY_TICKETS/MAX_HISTORY_TURNS) rörs INTE — det är
    # fortfarande vad som visas när samtalet är kort ELLER inget arbetsminne
    # finns. `turns` ovan räknar bara de tre senaste ärendena, så samtalets
    # FAKTISKA totala längd räknas separat (alla_samtalsrader, hela
    # historiken) — annars kunde ett samtal på 30 ärenden aldrig passera
    # tröskeln bara för att taket redan klippt bort resten innan vi hann
    # räkna.
    alla_rader = await arbetsminne.alla_samtalsrader(storage, tenant_id, history)
    if len(alla_rader) > arbetsminne.TROSKEL_TOTALA_TURER:
        post = await arbetsminne.hamta().las(tenant_id, customer_id)
        if post and post.summering:
            block = arbetsminne.bygg_summerat_block(
                post.summering, alla_rader[-MAX_HISTORY_TURNS:]
            )
            return block, len(alla_rader), senaste_kundreplik
        # Inget arbetsminne (eller Redis nere, vilket `las` redan gjort
        # ekvivalent med "inget arbetsminne") — exakt dagens beteende nedan.

    return (
        "## Tidigare i samtalet\n" + "\n".join(turns[-MAX_HISTORY_TURNS:]),
        len(turns),
        senaste_kundreplik,
    )


def _steps_by_skill() -> dict[str, Any]:
    return {step.skill: step for step in SUPPORT_V1.steps}


#: Ämnen där en följdfråga är fel svar, oavsett hur tunt biblioteket är.
#:
#: Kontrollen görs i KOD och inte bara av `cs:customer-escalation`, av samma
#: skäl som påhoppsbedömningen: beslutet om vad som är för känsligt för att
#: agenten ska hantera det självt ska inte kunna pratas bort av innehållet i
#: meddelandet. Steget som bär juridiken kommer dessutom EFTER utkastet
#: (`requires=("skill:cs:draft-response",)`), så dess svar finns inte att
#: läsa när frågan "ska vi fråga eller lämna över?" ska avgöras.
#:
#: Listan får hellre fälla för mycket än för lite: ett fällt fall blir en
#: eskalering, alltså exakt det som hände före den här ändringen.
#: 2026-08-25: `gdpr`, `dataskydd` och `personuppgift*` togs BORT ur listan.
#: De fällde varje fråga som NÄMNDE orden — och "hur hanterar ni GDPR?" är en
#: informationsfråga vars svar står i kunskapsbasen (och på /faq och
#: /integritetspolicy). Att lämna över den till en människa är att eskalera
#: sin egen dokumentation. Det som SKA eskalera är utövandet av en rättighet —
#: radering, registerutdrag — och de mönstren står kvar nedan, breddade så att
#: de fångar "raderar alla mina uppgifter" och inte bara "radera mina data".
_KANSLIGT = re.compile(
    r"\b(arn|allmänna\s+reklamationsnämnden|konsumentverket|konsumentombudsman|"
    r"rader(?:a|ar|at|as)\s+(?:\w+\s+){0,3}?(?:uppgift\w*|data|konto\w*)|"
    r"registerutdrag|rätt(?:en)?\s+att\s+bli\s+glömd|"
    r"advokat|jurist|stämning|stämma\s+er|rättslig\w*|anmäl\w*|polisanmäl\w*|"
    r"skadestånd|återbetal\w*|kompensation|ersättning|kronofogden|inkasso|"
    r"häv(a|er|ning)\s+köpet|ångerrätt\w*|reklamation\w*)\b",
    re.IGNORECASE,
)

#: Ord som inte bär betydelse i en sökfråga. Kort lista med flit — samma
#: resonemang som abuse_gate: en lång lista fäller fel, och här kostar ett
#: felaktigt bortfilterat ord en sämre sökning.
_SOKSTOPPORD = {
    "hej", "hejsan", "tack", "mvh", "hälsningar", "jag", "min", "mitt", "mina",
    "och", "att", "det", "den", "som", "har", "för", "inte", "med", "till",
    "kan", "vad", "hur", "när", "var", "vill", "ni", "er", "från", "om", "på",
    "är", "en", "ett", "av", "men", "här", "nu", "så", "skulle", "vara", "får",
}


def _kb_block(articles: list[dict[str, Any]]) -> str:
    """KB-artiklar är kundskriven text, inte våra instruktioner — sedan Fas 5
    dessutom uppladdad textfil eller extraherad PDF, som kan ha vidarebefordrats
    utan att kunden läst varje rad. Wrappas därför som SOUL och affärskontexten
    redan är (INV-SEC-012, INV-SEC-003). Positionsgarantin (case_context är
    alltid användarposition) höll redan — det här är ramen ovanpå den."""
    if not articles:
        return "(inga träffar)"
    return wrap_untrusted_content(
        "\n\n".join(f"### {a['title']}\n{a['content']}" for a in articles),
        source="tenant:kb_article",
    )


async def _sok_kb(storage: Storage, tenant_id: str, fraga: str) -> list[dict[str, Any]]:
    """En KB-sökning, med embedding när det går och fulltext annars.

    Embeddingen räknas per FRÅGA och inte en gång per ärende: en bredare fråga
    ska sökas som den bredare frågan den är. Misslyckas embeddingen faller
    sökningen tillbaka på fulltext, precis som förut — i den här kodbasen har
    embeddings dessutom aldrig lyckats i praktiken (se `embedding_dimensions`
    i config.py), så fulltextvägen är den som faktiskt körs.
    """
    fraga = (fraga or "").strip()
    if not fraga:
        return []
    embedding = None
    try:
        from .embeddings import embed_text

        embedding = await embed_text(fraga)
    except Exception:  # noqa: BLE001 — utan embeddings används fulltext-fallback
        embedding = None
    return await storage.search_kb(tenant_id, fraga, embedding=embedding)


def _forenklad_fraga(subject: str, message: str) -> str:
    """En bredare andra sökfråga, byggd i kod.

    Ämnesraden först när den finns: den är kundens egen sammanfattning och
    nästan alltid närmare en artikelrubrik än brödtexten. Saknas den plockas
    de längsta betydelsebärande orden ur meddelandet — långa ord är i svenskan
    oftare sammansatta substantiv ("leveranstid", "delbetalning") än
    funktionsord, och det är substantiven artiklarna handlar om.

    Returnerar tom sträng när frågan inte går att förenkla meningsfullt, och då
    görs inget andra försök alls. Ett andra anrop mot databasen med samma fråga
    är bara latens.
    """
    amne = (subject or "").strip()
    text = (message or "").strip()
    # Ämnesraden duger så fort den finns OCH det fanns en brödtext att skala
    # bort. Att kräva att ämnet inte förekommer i brödtexten vore fel test:
    # första sökningen var "ämne + meddelande", så "ämne" ensamt är en annan
    # och bredare fråga även när ordet står i båda — vilket det oftast gör.
    if amne and text:
        return amne

    ord_ = [
        o
        for o in re.findall(r"[\wåäöÅÄÖ]{4,}", message or "", flags=re.UNICODE)
        if o.lower() not in _SOKSTOPPORD
    ]
    if len(ord_) < 2:
        return ""
    # De fem längsta, i den ordning de stod — ordningen spelar roll för
    # fulltextrankningen i Postgres.
    valda = sorted(sorted(set(ord_), key=ord_.index), key=len, reverse=True)[:5]
    kandidat = " ".join(sorted(valda, key=ord_.index))
    return "" if kandidat.lower() == (message or "").strip().lower() else kandidat


def _ar_kansligt(text: str) -> bool:
    """Om ärendet rör juridik, GDPR, pengar tillbaka eller myndighet."""
    return bool(_KANSLIGT.search(text or ""))


async def run_support_agent(
    storage: Storage,
    tenant_id: str,
    *,
    message: str,
    subject: str,
    channel: str,
    customer_email: str | None,
    customer_name: str | None,
    attachments: list[str],
    # --- Återupptagning efter en avbruten körning (INV-JOB-001) -----------
    # Båda None som default: OFÖRÄNDRAT beteende för varje befintlig anropare
    # (chat.py:s create_task-väg, sim-vägen, alla tester). Se
    # app/jobs/stream.py och app/api/chat.py för hela mekanismen.
    #
    # `aterta`: satt av hanteraren i chat.py när jobbposten redan bär ett
    # ticket_id/conversation_id från ett tidigare, avbrutet försök — hoppar
    # över create_ticket/save_message för det inkommande meddelandet och
    # återanvänder de givna id:na, så en omkörning inte dubblettskapar ärendet.
    #
    # `vid_arende`: anropas med (ticket_id, conversation_id) precis EFTER att
    # ärendet (eller återanvändningen av det) är klart — det ENDA stället en
    # efterföljande krasch kan återupptas ifrån.
    aterta: dict[str, str] | None = None,
    vid_arende: Callable[[str, str], Awaitable[None]] | None = None,
    # Fas 2.5 (snipe-vxq): admintester ska märkas i agent_runs, inte räknas
    # som kundvolym. Samma flagga som leads-vägen redan trådar (rad ~419).
    is_test: bool = False,
) -> dict[str, Any]:
    started = time.monotonic()
    settings = get_settings()
    config = await storage.get_channel_config(tenant_id, channel)
    taxonomy = await storage.get_agent_taxonomy(tenant_id)
    steps = _steps_by_skill()

    tenant = await storage.get_tenant(tenant_id)
    tenant_namn = (tenant or {}).get("name") or ""

    # Instruktionslagren läses EN gång och skickas till varje steg. Läste varje
    # steg själv skulle ett sparande mitt i ett ärende kunna ge triagesteget
    # andra regler än humaniseringssteget, och spårvyn hade visat en körning
    # som aldrig funnits (migration 049, agentcore/instruktioner.py).
    lager = await las_instruktioner(
        storage, tenant_id, agent_type="support", tenant_namn=tenant_namn
    )
    steg = partial(run_step, instruktioner=lager)
    agentkonfig = await storage.get_agent_config(tenant_id, agent_type="support")

    # G9: bilder beskrivs av vision-sidovagnen och kastas — aldrig lagrade.
    vision_note = ""
    if attachments:
        descriptions = [await describe_image(url) for url in attachments]
        vision_note = "\n\n[Bildbeskrivning]:\n" + "\n".join(descriptions)

    # Påhoppsbedömningen görs i KOD, av samma skäl som klassificeraren nedan:
    # den avgör om samtalet ska avbrytas, och det beslutet ska inte kunna
    # pratas bort av innehållet i meddelandet. Gränsen går vid vad uttrycket
    # RIKTAS mot, inte vid hur hårt det är — se app/moderation/abuse_gate.py.
    abuse = check_abuse(message)

    # Kundens röstdokument. Ligger i case_context, alltså i USERposition —
    # aldrig i systemprompten. Se app/leads/soul.py för varför den gränsen
    # är själva mekanismen och inte en försiktighetsåtgärd (INV-SEC-009).
    soul_block = await load_soul(storage, tenant_id)

    # Affärskontexten nådde tidigare BARA leads-agenten. En supportkund kunde
    # alltså beskriva vad de säljer och till vem, och supportsvaren visste
    # ingenting om det — samma klass av fel som de döda instruktionsfälten.
    # Den är KUNDSKRIVEN, alltså USERposition och wrappad, precis som SOUL.
    affarskontext_block = ""
    _doc = await storage.get_latest_context_doc(tenant_id, kind="product_marketing")
    _innehall = ((_doc or {}).get("content") or "").strip()
    if _innehall:
        affarskontext_block = (
            "## Kundens affärskontext\n"
            "Bakgrund om verksamheten, för att förstå ärendet. Den är INTE en "
            "faktakälla för svar till kunden — det är kunskapsbasen.\n\n"
            + wrap_untrusted_content(_innehall[:4000], source="tenant:product_marketing")
        )

    kalibrering_block = ""
    if is_test:
        try:
            feedback = await storage.list_agent_feedback(tenant_id, limit=8)
        except Exception:  # noqa: BLE001 — kalibrering är bonus
            feedback = []
        rattningar = [
            str(r.get("corrected_output") or r.get("comment") or "").strip()
            for r in feedback
            if r.get("verdict") == "bad"
            or str(r.get("corrected_output") or "").strip()
        ]
        rattningar = [t for t in rattningar if t][:5]
        if rattningar:
            kalibrering_block = (
                "## Kalibrering från testchatten\n"
                "Rättningar en medarbetare lämnat i testchatten. Använd dem som "
                "stil- och innehållsvägledning. De är INTE fakta ur kunskapsbasen.\n\n"
                + wrap_untrusted_content(
                    "\n".join(f"- {t[:500]}" for t in rattningar),
                    source="tenant:test-feedback",
                )
            )

    # Kundens egen ton (agent_configs.tone) vinner över kanalens default.
    # Kolumnen har funnits sedan migration 010 utan att någon läst den. Det är
    # därför "ändra tonen" inte gjorde någon skillnad förrän nu.
    ton_lage = (agentkonfig.get("tone") or "").strip() or config["tone"]

    # Kunden slås upp FÖRE triagen (flyttad 2026-08-27, låg efter): kundminnet
    # ska in i case_context, och case_context byggs före första steget.
    # find_or_create har skapandet som sidoeffekt, men det skedde ändå
    # ovillkorligen — bara senare i samma funktion.
    customer = await storage.find_or_create_customer(
        tenant_id, email=customer_email, phone=None, name=customer_name
    )
    history = await storage.get_customer_history(tenant_id, customer["id"])

    # Kundminnet (migration 052) — mem0:s ADD-only-mönster. Bär ENBART vad
    # kunden själv uppgett i tidigare ärenden; agentens slutsatser lagras
    # aldrig (kontamineringsspärren, se migrationens rubrik). Kundhärledd
    # text är kundskriven text: USER-position, opålitligt-wrappad, kapad.
    minnesblock = ""
    try:
        fakta = await storage.get_customer_facts(tenant_id, customer["id"])
    except Exception:  # noqa: BLE001 — ett trasigt minne får inte fälla ärendet
        fakta = []
    if fakta:
        minnesblock = (
            "## Vad kunden uppgett i tidigare ärenden\n"
            "Kundens egna uppgifter, återgivna — inte verifierade fakta. Fråga "
            "hellre igen än att bygga ett svar på en gammal uppgift som kan ha "
            "ändrats.\n\n"
            + wrap_untrusted_content("\n".join(f"- {f}" for f in fakta)[:1500], source="customer:memory")
        )

    # --- Fas R2: semantisk svarscache (INV-CACHE-001) ----------------------
    #
    # Grinden och lookupen bor i cache-modulen (app/cache/svarscache.py) —
    # anropas HÄR, EFTER kundminnesuppslaget (allt underlag för
    # behörigheten — historik, bilagor, minnesfakta, PII-maskering — finns
    # nu) och FÖRE klassificeraren nedan. Ordningen är inte kosmetisk: en
    # TRÄFF i läge "on" ska kosta NOLL LLM-anrop, och klassificeraren
    # (Del E steg 6, flyttad hit 2026-08-29) är själv ett LLM-anrop — den
    # måste alltså vänta tills vi vet att den faktiskt behövs.
    kbv = await versioner.kb_version(tenant_id)
    cfgv = await versioner.config_version(tenant_id)
    cache_kontext = svarscache.CacheKontext(behorig=False)
    # `not abuse.ska_eskalera`: ett meddelande påhoppsbedömningen redan
    # flaggat ska aldrig ens titta i cachen — eskaleringsvägen är beslutad i
    # kod och en cachad FAQ-replik vore fel svar oavsett cosinuslikhet.
    if settings.semantic_cache != "off" and not abuse.ska_eskalera:
        cache_kontext = await svarscache.forbered(
            tenant_id,
            history=history,
            attachments=attachments,
            fakta=fakta,
            message=message,
            kbv=kbv,
            cfgv=cfgv,
        )
        if cache_kontext.traff and settings.semantic_cache == "on":
            # TRÄFF, servera: hela LLM-kedjan (triage/research/utkast/
            # eskalering/kb-förslag/retention/humanizer) hoppas över, men
            # ärendet+inbound+outbound bokförs precis som en vanlig körning
            # — se svara_fran_cache för varför.
            pack = pack_version(SUPPORT_V1.name, lager.hash)
            return await svarscache.svara_fran_cache(
                storage,
                tenant_id,
                traff=cache_kontext.traff,
                message=message,
                subject=subject,
                channel=channel,
                customer=customer,
                max_length=config["max_length"],
                pack=pack,
                started=started,
                aterta=aterta,
                vid_arende=vid_arende,
                is_test=is_test,
            )
        if cache_kontext.traff and settings.semantic_cache == "shadow":
            # TRÄFF, mät men ändra ingenting — kedjan fortsätter oförändrad
            # nedanför precis som vid en miss.
            await svarscache.logga_skuggtraff(storage, tenant_id, kontext=cache_kontext)

    # Del E steg 6: klassificeraren körs i KOD före playbooken. Flyttad hit
    # (2026-08-29, Fas R2) — låg tidigare direkt efter bildbeskrivningen,
    # men det är precis den positionen en cache-TRÄFF måste undvika för att
    # "noll LLM-anrop" ska vara sant och inte bara nästan sant.
    try:
        intent, dissatisfaction = await classify_cancellation_risk(message)
    except Exception:  # noqa: BLE001 — en trasig klassificerare får inte fälla ärendet
        intent, dissatisfaction = 0.0, 0.0
    cancellation_risk = is_cancellation_risk(intent, dissatisfaction)

    case_context = (
        f"## Ärendet\nKanal: {channel} (ton: {ton_lage}, max {config['max_length']} tecken)\n"
        f"Kund: {customer_name or 'okänd'} <{customer_email or 'okänd'}>\n"
        f"Ämne: {maskera_personnummer(subject) or '(inget)'}\n\n"
        # Maskerat innan det går till modellen. Se DPIA:ns R1 och
        # app/moderation/maskering.py — originalet ligger kvar i databasen,
        # det är bara prompten som bär en maskerad kopia.
        f"Kundens meddelande:\n{maskera_personnummer(message)}{vision_note}\n\n"
        f"Giltiga kategorier för den här kunden: {', '.join(taxonomy)}"
        + (f"\n\n{affarskontext_block}" if affarskontext_block else "")
        + (f"\n\n{kalibrering_block}" if kalibrering_block else "")
        + (f"\n\n{soul_block}" if soul_block else "")
        + (f"\n\n{minnesblock}" if minnesblock else "")
    )

    # Tonläget läggs på case_context och inte på systemprompten: det är kördata
    # om DET HÄR meddelandet, inte en regel. Tom sträng när inget hänt.
    ton = ton_instruktion(abuse)
    if ton:
        case_context = f"{case_context}\n\n{ton}"

    ledger = RunLedger(satisfied={"context_pack"})
    trace = RunTrace()

    # --- Steg 1: triage ----------------------------------------------------
    #
    # Kundfakta-fältet (2026-08-27): mem0-mönstrets extraktionssteg, inbakat i
    # triagen i stället för ett eget LLM-anrop — triagen läser ändå hela
    # meddelandet. BARA vad kunden själv uppgett; modellens egna slutsatser
    # (sentiment, kategori) lagras aldrig som fakta.
    triage = await steg(
        steps["cs:ticket-triage"],
        ledger,
        trace,
        task=(
            "Klassificera ärendet. Returnera JSON med: category (exakt ett av de "
            "giltiga), priority (P1-P4), sentiment (0.0-1.0), escalate (bool), "
            "reasoning (svenska), "
            "kundfakta (lista med korta, stabila fakta kunden SJÄLV uppger i "
            "meddelandet — produkt, enhet, ordernummer, preferens. Bara det som "
            "sannolikt gäller nästa gång kunden hör av sig; tom lista annars. "
            "Aldrig dina egna bedömningar)."
        ),
        case_context=case_context,
    )
    category = triage.get("category") if triage.get("category") in taxonomy else "ovrigt"
    sentiment = max(0.0, min(1.0, float(triage.get("sentiment") or 0.5)))

    # --- Kod: kundminne, ärende, inkommande meddelande ---------------------
    nya_fakta = [str(f).strip() for f in (triage.get("kundfakta") or []) if str(f).strip()]
    if nya_fakta:
        try:
            # Kapade: en modell som en dag returnerar en uppsats ska inte
            # kunna fylla minnet med den. ADD-only med dubblettspärr i lagret.
            await storage.add_customer_facts(
                tenant_id, customer["id"], fakta=[f[:200] for f in nya_fakta[:6]]
            )
        except Exception:  # noqa: BLE001 — minnet är en bonus, svaret är jobbet
            logger.exception("Kunde inte spara kundfakta.")

    # Samtalsläget är ett VÄRDE i ärendekontexten, inte i overlayen. Overlays
    # laddas ordagrant utan .format() (se agentcore/overlays.py), så kördata hör
    # hemma här och regeln som läser den står i support-conversation.md.
    conversation_block, turn_count, senaste_kundreplik = await _render_conversation(
        storage, tenant_id, customer["id"], history
    )
    conversation_state = (
        "## Samtalsläge\n"
        + (
            "Det här är ditt FÖRSTA svar till kunden."
            if turn_count == 0
            else f"Samtalet pågår redan ({turn_count} tidigare repliker). Det här är en fortsättning."
        )
        + (f"\n\n{conversation_block}" if conversation_block else "")
    )
    case_context = f"{case_context}\n\n{conversation_state}"

    if aterta:
        # Återupptagen körning (INV-JOB-001): ärendet och det inkommande
        # meddelandet skapades redan i det avbrutna försöket — skapa dem
        # inte igen, annars fick kunden två ärenden och två inbound-rader av
        # EN chatt.
        ticket = {"id": aterta["ticket_id"], "conversation_id": aterta["conversation_id"]}
    else:
        ticket = await storage.create_ticket(
            tenant_id,
            customer_id=customer["id"],
            subject=subject or message[:80],
            category=category,
            channel=channel,
            priority="high" if triage.get("priority") in ("P1", "P2") else "normal",
            is_test=is_test,
        )
        await storage.save_message(
            tenant_id,
            conversation_id=ticket["conversation_id"],
            direction="inbound",
            content=message,
            sentiment=sentiment,
            has_image=bool(attachments),
        )
    if vid_arende:
        await vid_arende(ticket["id"], ticket["conversation_id"])

    # --- Kod: KB-sökning (underlaget cs:customer-research resonerar kring) --
    #
    # TVÅ försök, inte ett. Den första frågan är hela meddelandet, vilket är
    # rätt när det är kort och illa när det är långt: en kund som skriver fem
    # meningar ger en fråga där de betydelsebärande orden dränks. Går den tomt
    # provas en förenklad fråga innan tomheten får betyda något. Se
    # `_forenklad_fraga`.
    sokfraga = f"{subject} {message}".strip()
    # I en FORTSÄTTNING är det nya meddelandet ofta ett svar på vår motfråga
    # ("Ja, en Android.") — ensamt söker det på fel sak. Kundens förra replik
    # bär ämnet och läggs till frågan. Bara vid korta meddelanden: ett långt
    # nytt meddelande bär sitt eget ämne, och mer text späder rankningen.
    if turn_count and senaste_kundreplik and len(message) < 80:
        sokfraga = f"{sokfraga} {senaste_kundreplik}".strip()
    articles = await _sok_kb(storage, tenant_id, sokfraga)
    kb_forsok = ["hela meddelandet"]
    if not articles:
        bredare = _forenklad_fraga(subject, message)
        if bredare:
            articles = await _sok_kb(storage, tenant_id, bredare)
            kb_forsok.append(f"förenklad fråga ({bredare!r})")
    kb_block = _kb_block(articles)

    # --- Steg 2: research --------------------------------------------------
    research = await steg(
        steps["cs:customer-research"],
        ledger,
        trace,
        task=(
            "Bedöm vad kunskapsbasen faktiskt svarar på och med vilken konfidens. "
            "Returnera JSON: findings (svenska), confidence (0.0-1.0), "
            "kb_supports_answer (bool), missing_info (svenska eller null)."
        ),
        case_context=(
            f"{case_context}\n\n## Kunskapsbas (ENDA tillåtna faktakällan)\n{kb_block}\n\n"
            f"Tidigare ärenden från kunden: {len(history)}"
        ),
    )

    # TREDJE försöket, på det researchsteget själv säger saknas. Modellen har
    # nu läst frågan OCH sett vad biblioteket innehöll, så `missing_info` är en
    # bättre sökfråga än något vi kan konstruera i kod — den är formulerad i
    # bibliotekets språk, inte i kundens.
    saknas = str(research.get("missing_info") or "").strip()
    if not articles and saknas:
        articles = await _sok_kb(storage, tenant_id, saknas)
        if articles:
            kb_forsok.append(f"missing_info ({saknas[:60]!r})")
            kb_block = _kb_block(articles)

    # --- Kod: ska agenten fråga i stället för att lämna över? --------------
    #
    # Se `_ar_kansligt`. Beslutet fattas HÄR, före utkastet,
    # eftersom det ändrar vad utkastet ska vara — inte efteråt, som en
    # efterhandsredigering av en text som redan skrivits.
    kb_stodjer_svar = bool(research.get("kb_supports_answer"))
    kb_saknar_svar = not articles or not kb_stodjer_svar

    sakerhetskritiskt = bool(
        abuse.ska_eskalera
        or cancellation_risk
        or triage.get("escalate")
        or sentiment < SENTIMENT_ESCALATION_THRESHOLD
        or _ar_kansligt(f"{subject} {message}")
    )

    fragar_uppfoljning = (
        kb_saknar_svar
        and not sakerhetskritiskt
        # BARA i första turen. Har kunden redan svarat en gång och vi
        # fortfarande inte kan svara, är en andra motfråga inte omsorg utan en
        # loop — och den loopen är värre än en överlämning.
        #
        # 2026-08-25: `_kb_ar_tunn`-villkoret togs bort. Det stängde
        # följdfrågevägen så fort biblioteket hade fem artiklar — på den
        # publika demon (31 artiklar) blev varje miss en överlämning, aldrig
        # en fråga. Men en första miss på ett FULLT bibliotek betyder oftare
        # "frågan var för vag för att sökas" än "svaret finns inte": en
        # förtydligad fråga får ett andra sökvarv, och först när även det går
        # tomt (turn_count > 0) är tomheten ett besked. Loopspärren ovan är
        # den gräns som bär den skillnaden nu.
        and turn_count == 0
    )

    # --- Steg 3: utkast ----------------------------------------------------
    draft = await steg(
        steps["cs:draft-response"],
        ledger,
        trace,
        task=(
            "Kunskapsbasen räcker inte för att svara på frågan, men ärendet är "
            "varken juridiskt, säkerhetskritiskt eller en uppsägningsrisk. "
            "Lämna INTE över till en människa. Ställ i stället EN kort, öppen "
            "följdfråga som skulle göra frågan besvarbar — den mest användbara "
            "du kan komma på. Påstå ingenting om produkten eller villkoren som "
            "inte står i kunskapsbasen, och lova inte att någon återkommer. "
            "Ren text, ingen markdown. Returnera JSON: draft (svenska)."
            if fragar_uppfoljning
            else "Skriv ett svar till kunden, grundat ENBART i kunskapsbasen ovan. "
            "Ren text, ingen markdown. Returnera JSON: draft (svenska)."
        ),
        case_context=f"{case_context}\n\n## Kunskapsbas\n{kb_block}\n\n## Research\n{research.get('findings', '')}",
    )

    # --- Steg 4: eskaleringsbedömning --------------------------------------
    escalation = await steg(
        steps["cs:customer-escalation"],
        ledger,
        trace,
        task=(
            # Två varianter, för att modellens svar OR:as in i kodbeslutet:
            # står "eskalera om kunskapsbasen saknar svar" kvar i prompten
            # medan koden just valt följdfrågevägen, röstar modellen alltid
            # emot och följdfrågan eskalerar ändå.
            "Avgör om ärendet måste till en människa. Eskalera ALLTID vid: "
            "återbetalning/kompensation, juridik/ARN/Konsumentverket, "
            "GDPR-radering, avtal eller fakturering på kontonivå — eller om "
            "kunden uttryckligen ber att få prata med en människa. "
            + (
                "Kunskapsbasen saknar svar, men svaret till kunden ställer en "
                "förtydligande följdfråga — det är INTE ett skäl att eskalera "
                "i den här turen. "
                if fragar_uppfoljning
                else "Eskalera också om kunskapsbasen saknar svar och ingen "
                "följdfråga kan göra frågan besvarbar. "
            )
            + "Returnera JSON: should_escalate (bool), reason (svenska eller null)."
        ),
        case_context=(
            f"{case_context}\n\n## Research\n{research.get('findings', '')}\n"
            f"kb_supports_answer: {research.get('kb_supports_answer')}"
        ),
    )

    # Eskalering avgörs i KOD av oberoende villkor — inte av modellen ensam.
    #
    # ## Vad som ändrades 2026-08-24, och vad som INTE gjorde det
    #
    # Före: `or not articles` fällde ensamt. En tenant med sex artiklar
    # eskalerade därför nästan varje fråga som inte råkade formuleras som en
    # artikelrubrik — inte för att ärendet behövde en människa, utan för att
    # sökningen gick tom på första försöket.
    #
    # Nu: `kb_saknar_svar` väger in `kb_supports_answer` från researchsteget,
    # som tidigare bara stod som KONTEXT åt eskaleringssteget och aldrig
    # avgjorde något i kod. Den är det bättre måttet — noll träffar på ett tunt
    # bibliotek betyder något annat än noll träffar på ett fullt. Och när
    # ärendet varken är känsligt eller en fortsättning ställs en följdfråga i
    # stället för att lämna över (`fragar_uppfoljning`).
    #
    # OFÖRÄNDRADE, och avsiktligt lika lätta att utlösa som förut:
    # `abuse.ska_eskalera`, uppsägningsrisk, triageflaggan, lågt sentiment och
    # modellens egen `should_escalate` (som bär juridik/ARN/GDPR). De är rätt
    # beslut varje gång, inte agenten som ger upp.
    #
    # Och en tredje sak, i lagringslagret: `storage.search_kb` kedjar numera
    # vektorsökning -> fulltext. Vektorvägen filtrerar på
    # `embedding is not null` och gav tom lista så fort de nyaste träffarna låg
    # under likhetströskeln, även när svaret stod i en äldre artikel. Sökningen
    # är alltså bättre vid källan, inte bara mildare bedömd här.
    escalated = bool(
        escalation.get("should_escalate")
        or triage.get("escalate")
        or sentiment < SENTIMENT_ESCALATION_THRESHOLD
        or cancellation_risk
        or abuse.ska_eskalera
        or (kb_saknar_svar and not fragar_uppfoljning)
    )
    escalation_reason = (
        # Påhoppet vinner över modellens egen motivering: en människa som tar
        # över ärendet ska se VARFÖR det lämnades över, och "kunskapsbasen
        # saknade svar" är fel förklaring på ett hot.
        f"Avbrutet samtal: {abuse.niva}"
        if abuse.ska_eskalera
        else escalation.get("reason") or ("retention_risk" if cancellation_risk else None)
    )
    if escalated and not escalation_reason:
        escalation_reason = (
            f"Kunskapsbasen räckte inte ({', '.join(kb_forsok)} prövades, "
            f"kb_supports_answer={kb_stodjer_svar})"
            if kb_saknar_svar
            else "Lågt sentiment eller triageflagga"
        )

    # --- Steg 5: KB-artikel (villkorat — fångar ny kunskap tillbaka) -------
    #
    # Körs BARA när det finns något att lära: kunskapsbasen saknade svaret,
    # eller ärendet är säkerhetskritiskt. Ett ärende där KB bar svaret och
    # inget flaggade har ingen lucka att skriva om — steget kördes förut på
    # VARJE ärende och kostade ett anrop av sex för noll utbyte.
    #
    # Utdatan KASTADES dessutom förut: den fanns i step_log och ingenstans
    # annars, så samma lucka återupptäcktes från noll i varje ärende. Nu
    # sparas den som ett FÖRSLAG (agent_suggestions) som en människa
    # godkänner i admin — agenten skriver aldrig själv i kunskapsbasen
    # (INV-LEARN-001).
    if kb_saknar_svar or sakerhetskritiskt:
        kb_forslag = await steg(
            steps["cs:kb-article"],
            ledger,
            trace,
            task=(
                "Bedöm om det här ärendet avslöjar en kunskapslucka värd en KB-artikel. "
                "Returnera JSON: should_create (bool), title (svenska eller null), "
                "content (svenska eller null). I brödtexten: skriv 'kontakta oss igen', "
                "aldrig 'kontakta supporten' — kunden har redan kontaktat oss."
            ),
            case_context=f"{case_context}\n\n## Kunskapsbas\n{kb_block}",
        )
        titel = str(kb_forslag.get("title") or "").strip()
        innehall = str(kb_forslag.get("content") or "").strip()
        if kb_forslag.get("should_create") and titel and innehall:
            # Kastar aldrig: ett trasigt förslagsskrivande får inte fälla ett
            # färdigt svar. Dedupe-nyckeln är titelns normaliserade hash — tio
            # ärenden om samma lucka ska ge EN rad att granska.
            try:
                await storage.save_agent_suggestion(
                    tenant_id,
                    agent_type="support",
                    kind="kb_article",
                    title=titel[:200],
                    content={"title": titel, "content": innehall, "category": category},
                    dedupe_key=hashlib.sha256(titel.casefold().encode("utf-8")).hexdigest()[:32],
                )
            except Exception:  # noqa: BLE001 — förslaget är en bonus, svaret är jobbet
                logger.exception("Kunde inte spara KB-förslaget för ärendet.")

    # --- Steg 6: retention (villkorat) -------------------------------------
    current_draft = draft.get("draft", "")

    if cancellation_risk and not abuse.ska_eskalera:
        retention_playbook = await storage.get_latest_context_doc(
            tenant_id, kind="retention_playbook"
        )
        playbook_text = (
            retention_playbook["content"]
            if retention_playbook
            else "(INGEN retentionsplaybook finns för den här kunden — du får därför "
            "INTE erbjuda något alls. Bekräfta, fastställ, och lämna över till människa.)"
        )
        retention = await steg(
            steps["snajp:retention-conversation"],
            ledger,
            trace,
            task=(
                "Kunden signalerar uppsägning/missnöje. Skriv om utkastet enligt "
                "skillens fyra hårda regler. Erbjud ALDRIG något som inte ordagrant "
                "står i retentionsplaybooken nedan. Returnera JSON: revised_draft "
                "(svenska), offers_made (lista, tom om inga)."
            ),
            case_context=(
                f"{case_context}\n\n## Kundens retentionsplaybook\n{playbook_text}\n\n"
                f"## Nuvarande utkast\n{current_draft}"
            ),
        )
        current_draft = retention.get("revised_draft") or current_draft

    # --- Steg 7: humanizer (ALLTID sist) -----------------------------------
    humanized = await steg(
        steps["snajp:humanizer-svenska"],
        ledger,
        trace,
        task=(
            "Gör texten naturlig svenska enligt skillen. Behåll all sakinformation. "
            "Ren text, ingen markdown. Returnera JSON: final_reply (svenska)."
        ),
        case_context=f"{case_context}\n\n## Text att humanisera\n{current_draft}",
    )

    reply = strip_markdown(humanized.get("final_reply") or current_draft or "").strip()
    # Efter humaniseraren, före längdkapningen: en avslutningsfras utan namn
    # under är trasig oavsett vilket steg som skrev den.
    reply = strip_dangling_sign_off(reply)

    # Påhoppsspärren appliceras EFTER humaniseraren, och det är hela poängen.
    # Ett kontrollerat säkerhetssvar ska inte formuleras om av en modell — den
    # hade mjukat upp ett samtalsavbrott till en artighet, eller strukit det
    # helt. Lades repliken in före humaniseringen skrev steget över den, vilket
    # är exakt vad som hände innan den här raden flyttades hit.
    if abuse.ska_eskalera and abuse.replik:
        # Modellens svar kastas. Att fortsätta hjälpa som om inget hänt är att
        # lära den som hotar att det fungerar. Ärendet och det inkommande
        # meddelandet är redan sparade, så en människa ser hela förloppet.
        reply = abuse.replik
    elif abuse.replik:
        # Riktad förolämpning: påpekandet läggs FÖRE hjälpen, inte i stället
        # för den. Kunden ska fortfarande få svar på sin fråga.
        reply = f"{abuse.replik}\n\n{reply}".strip()
    if not reply:
        # Två saker med den här grenen: den lovar bara en kollega när ärendet
        # FAKTISKT eskalerats (annars är löftet en lögn — ingen människa ser
        # ett oeskalerat ärende), och den varieras så att en kund som träffar
        # den två gånger inte läser exakt samma mening två gånger.
        if escalated:
            reply = random.choice(
                [
                    "Tack för ditt meddelande! Jag har öppnat ett ärende och en "
                    "kollega återkommer så snart som möjligt.",
                    "Jag har lagt upp ett ärende av det här, så tar en kollega "
                    "det vidare och hör av sig till dig.",
                    "Det här behöver en människa titta på — jag har öppnat ett "
                    "ärende och någon av oss återkommer så snart det går.",
                ]
            )
        else:
            reply = random.choice(
                [
                    "Där fick jag inte ihop ett bra svar. Kan du beskriva vad "
                    "du är ute efter på ett annat sätt, så gör jag ett nytt försök?",
                    "Jag vill inte gissa mig till ett svar här. Berätta gärna "
                    "lite mer om vad du behöver, så tittar jag igen.",
                    "Den frågan kunde jag inte besvara ordentligt på första "
                    "försöket. Formulera den gärna på ett annat sätt så löser vi det.",
                ]
            )
    if len(reply) > config["max_length"]:
        reply = reply[: config["max_length"] - 1].rstrip() + "…"

    # --- Kod: sidoeffekter -------------------------------------------------
    if escalated:
        await storage.update_ticket(
            tenant_id,
            ticket["id"],
            status="escalated",
            priority="high",
            escalation_reason=escalation_reason,
        )
        # Mejlet går EFTER statusuppdateringen, med flit: databasen är
        # sanningen om att ärendet eskalerat, mejlet är bara en knuff. Faller
        # sändningen har ärendet ändå rätt status i adminvyn.
        #
        # ETT mejl per eskaleringshändelse. Varje meddelande i chatten öppnar
        # ett EGET ärende (se _render_conversation), så "samma ärende" i
        # kundens mening är en KUND med ett redan eskalerat ärende — inte ett
        # ticket-id. `history` hämtades före det här ärendet skapades och bär
        # alltså bara de tidigare. Har något av dem redan eskalerat är det här
        # en fortsättning på en sak en människa redan blivit tillsagd om, och
        # då ska den människan inte få ett mejl till.
        #
        # Dubblettnyckeln i prioriterat_mejl är andra linjen: den fångar ett
        # omtag av SAMMA ärende (en retry), inte ett nytt meddelande.
        if not any(t.get("status") == "escalated" for t in history):
            await skicka_prioriterat(
                f"Supportärende eskalerat — {CATEGORY_LABELS.get(category, 'Övrigt')}",
                tenant_id=tenant_id,
                vad=f"Ärende {ticket['id']} ({channel}) lämnades över till människa.",
                varfor=escalation_reason or "okänd",
                lank=arendelank(settings.publik_bas_url, ticket["id"]),
                nyckel=f"support:{tenant_id}:{ticket['id']}",
            )
    await storage.save_message(
        tenant_id,
        conversation_id=ticket["conversation_id"],
        direction="outbound",
        content=reply,
        sentiment=None,
        has_image=False,
    )
    await storage.log_metric(
        tenant_id, ticket_id=ticket["id"], metric_name="sentiment", value=sentiment
    )

    # --- Fas R2: cache-STORE (INV-CACHE-001) --------------------------------
    #
    # Bara när lookup-villkoren höll (cache_kontext.behorig — samma fråga
    # som slogs upp ovan, alltså tom historik/inga bilagor/tomt
    # kundminne/ingen PII) OCH svaret inte eskalerade OCH kategorin är en av
    # de rena faktafrågorna (svarscache.CACHEBARA_KATEGORIER). En "on"-TRÄFF
    # når aldrig hit — den grenen returnerade redan högre upp — så det här
    # är bara miss/off/shadow-vägen.
    if (
        settings.semantic_cache in ("on", "shadow")
        and cache_kontext.behorig
        and not escalated
        and category in svarscache.CACHEBARA_KATEGORIER
    ):
        await svarscache.spara(
            tenant_id,
            kbv=kbv,
            cfgv=cfgv,
            vektor=cache_kontext.vektor,
            fraga_norm=cache_kontext.fraga_norm,
            svar=reply,
            kategori=category,
        )

    # --- Fas R3: arbetsminnet uppdateras ASYNKRONT, fire-and-forget --------
    #
    # Görs sist, EFTER att svaret redan är sparat ovan och INNAN funktionen
    # returnerar — men startas som en egen task i stället för att `await`:as.
    # Det är MEDVETET: kunden har redan fått sitt svar, och att låta hen
    # vänta på ännu ett LLM-anrop bara för att uppdatera en bakgrundssummering
    # vore att sälja latens för ingenting kunden ser. Och tappas
    # uppdateringen (processen dör innan tasken hinner köra klart) är det
    # ofarligt: hela samtalet ligger redan kvar i Postgres och sammanfattas
    # på nytt så fort nästa tur passerar tröskeln igen — samma
    # "rekonstruerbart ur Postgres, ingen kunddata bor bara i Redis"-princip
    # som resten av Redis-lagret (plan §3). En förlorad uppdatering är alltså
    # en sämre prompt NÄSTA gång, aldrig en förlorad sanning.
    #
    # Historiken hämtas FÄRSK här (inte samma `history`-variabel som ovan,
    # som lästes FÖRE det här ärendet skapades) — det just sparade
    # inbound/outbound-paret måste räknas med för att turantalet ska stämma.
    historik_efter_svaret = await storage.get_customer_history(tenant_id, customer["id"])
    alla_rader_nu = await arbetsminne.alla_samtalsrader(storage, tenant_id, historik_efter_svaret)
    turantal_nu = len(alla_rader_nu)
    if turantal_nu >= arbetsminne.UPPDATERA_MIN_TOTALA_TURER:
        tidigare_post = await arbetsminne.hamta().las(tenant_id, customer["id"])
        tackta_turer = tidigare_post.tackta_turer if tidigare_post else 0
        if (turantal_nu - tackta_turer) >= arbetsminne.UPPDATERA_MIN_NYA_TURER:
            asyncio.create_task(
                arbetsminne.uppdatera_arbetsminne(
                    tenant_id,
                    customer["id"],
                    alla_rader=alla_rader_nu,
                    turantal=turantal_nu,
                )
            )

    latency_ms = int((time.monotonic() - started) * 1000)
    pack = pack_version(SUPPORT_V1.name, lager.hash)
    run = await storage.log_agent_run(
        tenant_id,
        agent_type="support",
        pack_version=pack,
        skills_used=trace.skills_used,
        input_text=message,
        output_text=reply,
        step_log=trace.as_log(),
        tokens_in=trace.total_tokens_in,
        tokens_out=trace.total_tokens_out,
        latency_ms=latency_ms,
        is_test=is_test,
        # Migration 055 — samma provider+modell som get_agent_model() faktiskt
        # skickade anropen till.
        model=f"{settings.llm_provider}:{settings.model}",
    )

    return {
        "reply": reply,
        # Fas 6.2 (Testchatt): utan körnings-id:t går feedback inte att koppla
        # — POST /api/agent/feedback tar run_id, och jobbsvaret var den enda
        # plats som inte bar det.
        "run_id": (run or {}).get("id"),
        "ticket_id": ticket["id"],
        "customer_id": customer["id"],
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, "Övrigt"),
        "sentiment": sentiment,
        "escalated": escalated,
        "escalation_reason": escalation_reason,
        "kb_sources": [{"title": a["title"], "similarity": a["similarity"]} for a in articles],
        "returning_customer": len(history) > 0,
        "simulation": False,
        "skills_used": trace.skills_used,
        "step_log": trace.as_log(),
        "cancellation_risk": cancellation_risk,
        "pack_version": pack,
    }
