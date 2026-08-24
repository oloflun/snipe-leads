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

import re
import time
from typing import Any

from ..agentcore.overlays import pack_version
from ..agentcore.packs import RunLedger
from ..moderation.abuse_gate import check_abuse, ton_instruktion
from ..leads.soul import load_soul
from ..notifications.prioriterat_mejl import arendelank, skicka_prioriterat
from ..config import CATEGORY_LABELS, get_settings
from ..storage.base import Storage
from .retention_classifier import classify_cancellation_risk, is_cancellation_risk
from .step_runner import RunTrace, run_step
from .support_playbook import SUPPORT_V1
from .tools import strip_markdown
from .vision import describe_image

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


async def _render_conversation(storage, tenant_id: str, history: list) -> tuple[str, int]:
    """Tidigare turer som en läsbar utskrift, plus antalet turer.

    Utan detta fick utkaststeget bara ANTALET tidigare kontakter — en siffra,
    aldrig samtalet. Modellen kunde därför inte veta att den var mitt i ett
    samtal, och varje svar blev formellt sett ett första meddelande: "Hej" på
    varje replik och "Vänliga hälsningar," under varje.
    """
    turns: list[str] = []
    for ticket in reversed(history[:MAX_HISTORY_TICKETS]):  # äldst först
        for msg in await storage.get_messages(tenant_id, ticket["conversation_id"]):
            who = "Kunden" if msg["direction"] == "inbound" else "Du"
            content = (msg.get("content") or "").strip()
            if content:
                turns.append(f"{who}: {content}")

    if not turns:
        return "", 0
    return "## Tidigare i samtalet\n" + "\n".join(turns[-MAX_HISTORY_TURNS:]), len(turns)


def _steps_by_skill() -> dict[str, Any]:
    return {step.skill: step for step in SUPPORT_V1.steps}


#: Hur många artiklar en tenant ska ha innan "ingen träff" får betyda "vi kan
#: inte svara" i stället för "sökningen hittade inget den här gången".
#:
#: FÖRSLAG, INTE FACIT — talet är valt och inte mätt, och det ska prövas mot
#: riktig data innan det stelnar. Resonemanget bakom fem: en tenant med färre
#: artiklar än så har inte ett bibliotek utan ett par anteckningar, och att
#: eskalera varje fråga som inte träffar dem är att lämna över hela
#: supportflödet till en människa under de första veckorna — alltså precis den
#: period då kunden bedömer om produkten fungerar.
#:
#: Alternativet vore en konfidenströskel (`research.confidence`) i stället för
#: ett artikelantal. Den är i teorin bättre och i praktiken svårare: den är
#: modellens självskattning, alltså samma sorts tal som `should_escalate`
#: redan bär, och att bygga en andra grind på samma osäkra signal ger inte två
#: oberoende villkor. Artikelantalet är åtminstone ett faktum.
TUNN_KB_GRANS = 5

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
_KANSLIGT = re.compile(
    r"\b(arn|allmänna\s+reklamationsnämnden|konsumentverket|konsumentombudsman|"
    r"gdpr|dataskydd|personuppgift\w*|radera\s+(mina|all[at]?)\s+(uppgift\w*|data)|"
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
    return "\n\n".join(f"### {a['title']}\n{a['content']}" for a in articles) or "(inga träffar)"


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


async def _kb_ar_tunn(storage: Storage, tenant_id: str) -> bool:
    """Om tenantens bibliotek är för litet för att tomhet ska betyda något.

    Anropas BARA när sökningen redan gått tom eller researchsteget sagt att
    biblioteket inte bär svaret — alltså sällan, och just när svaret spelar
    roll. En räkning på varje ärende hade varit en databasfråga till för att
    besvara något vi oftast inte behöver veta.
    """
    try:
        return len(await storage.list_kb(tenant_id)) < TUNN_KB_GRANS
    except Exception:  # noqa: BLE001 — en trasig räkning får inte fälla ärendet
        # Faller åt eskaleringshållet: kan vi inte se biblioteket vet vi inte
        # att det är tunt, och då gäller den gamla regeln.
        return False


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
) -> dict[str, Any]:
    started = time.monotonic()
    settings = get_settings()
    config = await storage.get_channel_config(tenant_id, channel)
    taxonomy = await storage.get_agent_taxonomy(tenant_id)
    steps = _steps_by_skill()

    # G9: bilder beskrivs av vision-sidovagnen och kastas — aldrig lagrade.
    vision_note = ""
    if attachments:
        descriptions = [await describe_image(url) for url in attachments]
        vision_note = "\n\n[Bildbeskrivning]:\n" + "\n".join(descriptions)

    # Del E steg 6: klassificeraren körs i KOD före playbooken.
    try:
        intent, dissatisfaction = await classify_cancellation_risk(message)
    except Exception:  # noqa: BLE001 — en trasig klassificerare får inte fälla ärendet
        intent, dissatisfaction = 0.0, 0.0
    cancellation_risk = is_cancellation_risk(intent, dissatisfaction)

    # Påhoppsbedömningen görs i KOD, av samma skäl som klassificeraren ovanför:
    # den avgör om samtalet ska avbrytas, och det beslutet ska inte kunna
    # pratas bort av innehållet i meddelandet. Gränsen går vid vad uttrycket
    # RIKTAS mot, inte vid hur hårt det är — se app/moderation/abuse_gate.py.
    abuse = check_abuse(message)

    # Kundens röstdokument. Ligger i case_context, alltså i USERposition —
    # aldrig i systemprompten. Se app/leads/soul.py för varför den gränsen
    # är själva mekanismen och inte en försiktighetsåtgärd (INV-SEC-009).
    soul_block = await load_soul(storage, tenant_id)

    case_context = (
        f"## Ärendet\nKanal: {channel} (ton: {config['tone']}, max {config['max_length']} tecken)\n"
        f"Kund: {customer_name or 'okänd'} <{customer_email or 'okänd'}>\n"
        f"Ämne: {subject or '(inget)'}\n\n"
        f"Kundens meddelande:\n{message}{vision_note}\n\n"
        f"Giltiga kategorier för den här kunden: {', '.join(taxonomy)}"
        + (f"\n\n{soul_block}" if soul_block else "")
    )

    # Tonläget läggs på case_context och inte på systemprompten: det är kördata
    # om DET HÄR meddelandet, inte en regel. Tom sträng när inget hänt.
    ton = ton_instruktion(abuse)
    if ton:
        case_context = f"{case_context}\n\n{ton}"

    ledger = RunLedger(satisfied={"context_pack"})
    trace = RunTrace()

    # --- Steg 1: triage ----------------------------------------------------
    triage = await run_step(
        steps["cs:ticket-triage"],
        ledger,
        trace,
        task=(
            "Klassificera ärendet. Returnera JSON med: category (exakt ett av de "
            "giltiga), priority (P1-P4), sentiment (0.0-1.0), escalate (bool), "
            "reasoning (svenska)."
        ),
        case_context=case_context,
    )
    category = triage.get("category") if triage.get("category") in taxonomy else "ovrigt"
    sentiment = max(0.0, min(1.0, float(triage.get("sentiment") or 0.5)))

    # --- Kod: kund, ärende, inkommande meddelande --------------------------
    customer = await storage.find_or_create_customer(
        tenant_id, email=customer_email, phone=None, name=customer_name
    )
    history = await storage.get_customer_history(tenant_id, customer["id"])

    # Samtalsläget är ett VÄRDE i ärendekontexten, inte i overlayen. Overlays
    # laddas ordagrant utan .format() (se agentcore/overlays.py), så kördata hör
    # hemma här och regeln som läser den står i support-conversation.md.
    conversation_block, turn_count = await _render_conversation(storage, tenant_id, history)
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

    ticket = await storage.create_ticket(
        tenant_id,
        customer_id=customer["id"],
        subject=subject or message[:80],
        category=category,
        channel=channel,
        priority="high" if triage.get("priority") in ("P1", "P2") else "normal",
    )
    await storage.save_message(
        tenant_id,
        conversation_id=ticket["conversation_id"],
        direction="inbound",
        content=message,
        sentiment=sentiment,
        has_image=bool(attachments),
    )

    # --- Kod: KB-sökning (underlaget cs:customer-research resonerar kring) --
    #
    # TVÅ försök, inte ett. Den första frågan är hela meddelandet, vilket är
    # rätt när det är kort och illa när det är långt: en kund som skriver fem
    # meningar ger en fråga där de betydelsebärande orden dränks. Går den tomt
    # provas en förenklad fråga innan tomheten får betyda något. Se
    # `_forenklad_fraga`.
    articles = await _sok_kb(storage, tenant_id, f"{subject} {message}".strip())
    kb_forsok = ["hela meddelandet"]
    if not articles:
        bredare = _forenklad_fraga(subject, message)
        if bredare:
            articles = await _sok_kb(storage, tenant_id, bredare)
            kb_forsok.append(f"förenklad fråga ({bredare!r})")
    kb_block = _kb_block(articles)

    # --- Steg 2: research --------------------------------------------------
    research = await run_step(
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
    # Se `_ar_kansligt` och TUNN_KB_GRANS. Beslutet fattas HÄR, före utkastet,
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
        and turn_count == 0
        and await _kb_ar_tunn(storage, tenant_id)
    )

    # --- Steg 3: utkast ----------------------------------------------------
    draft = await run_step(
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
    escalation = await run_step(
        steps["cs:customer-escalation"],
        ledger,
        trace,
        task=(
            "Avgör om ärendet måste till en människa. Eskalera ALLTID vid: "
            "återbetalning/kompensation, juridik/ARN/Konsumentverket, GDPR-radering, "
            "eller om kunskapsbasen saknar svar. Returnera JSON: "
            "should_escalate (bool), reason (svenska eller null)."
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

    # --- Steg 5: KB-artikel (fångar ny kunskap tillbaka) -------------------
    await run_step(
        steps["cs:kb-article"],
        ledger,
        trace,
        task=(
            "Bedöm om det här ärendet avslöjar en kunskapslucka värd en KB-artikel. "
            "Returnera JSON: should_create (bool), title (svenska eller null), "
            "content (svenska eller null)."
        ),
        case_context=f"{case_context}\n\n## Kunskapsbas\n{kb_block}",
    )

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
        retention = await run_step(
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
    humanized = await run_step(
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
        reply = (
            "Tack för ditt meddelande! Jag har öppnat ett ärende och en kollega "
            "återkommer så snart som möjligt."
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

    latency_ms = int((time.monotonic() - started) * 1000)
    pack = pack_version(SUPPORT_V1.name)
    await storage.log_agent_run(
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
    )

    return {
        "reply": reply,
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
