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
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from functools import partial
from typing import Any

from ..agentcore.instruktioner import las_instruktioner
from ..agentcore.overlays import pack_version
from ..agentcore.packs import RunLedger
from ..cache import svarscache, versioner
from ..integrationer import handelser as integrationshandelser
from ..integrationer import uppslag as integrationsuppslag
from ..minne import arbetsminne
from . import arbetsyta_siffror
from ..moderation.abuse_gate import check_abuse, ton_instruktion
from ..moderation.maskering import maskera_personnummer
from ..leads.soul import load_soul
from ..notifications.prioriterat_mejl import arendelank, skicka_prioriterat
from ..leads.untrusted_content import wrap_untrusted_content
from ..config import CATEGORY_LABELS, get_settings
from ..storage.base import Storage
from . import support_faktagrind, support_regler, support_systemprompt, support_texter
from .retention_classifier import classify_cancellation_risk, is_cancellation_risk
from .step_runner import RunTrace, run_step
from .support_playbook import SUPPORT_V1
from .tools import strip_markdown
from .vision import describe_image

logger = logging.getLogger("snajp-support.support-agent")

# Sentiment under denna tröskel eskalerar oavsett vad modellen tycker
# (samma regel som tidigare låg i den handskrivna prompten). Sedan
# 2026-09-18 är det STANDARDVÄRDET — varje kund kan flytta gränsen
# (support_regler.Eskaleringsregler.sentimentgrans, 0–100).
SENTIMENT_ESCALATION_THRESHOLD = support_regler.STANDARD_ESKALERING["sentimentgrans"] / 100

#: Hur länge ett överlämnat samtal tillhör människan utan att något händer i
#: det. Sedan tar agenten nya meddelanden igen — en kund som återvänder efter
#: två dygn med en ny fråga ska få ett svar, inte en kvittens om ett ärende
#: ingen tittat på. Klockan är ss_chat_state.updated_at, som flyttas av varje
#: nytt meddelande i samtalet och av varje medarbetarsvar.
OVERLAMNING_GILTIG_TIMMAR = 24

#: De fasta replikerna (kvittens, överlämningsbesked, osäkerhetssvar) bor i
#: support_texter.py, på svenska och engelska — se modulen för varför de är
#: kod och inte modelltext.

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
    r"bästa\s+hälsningar|vänligen|best\s+regards|kind\s+regards|regards|"
    r"sincerely|yours\s+sincerely)\s*[,.!]?\s*$",
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
            # Migration 066: en utgående rad kan vara en MEDARBETARES svar.
            # Agenten ska veta vad en människa sagt eller lovat — inte tro att
            # den sagt det själv.
            who = (
                "Kunden"
                if msg["direction"] == "inbound"
                else "Kollegan" if msg.get("author") == "human" else "Du"
            )
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
    r"häv(a|er|ning)\s+köpet|ångerrätt\w*|reklamation\w*|"
    # Grundprompten 6.3 (2026-10-05): betalningsproblem, GDPR-rättigheter
    # utöver radering, personskada och säkerhetsrisk. Smala mönster med flit
    # — "när kommer fakturan?" är en vanlig fråga, "felaktig faktura" inte.
    r"(?:fel|felaktig\w*)\s+faktur\w*|faktur\w*\s+(?:är|var)\s+fel\w*|"
    r"dubbel\s*debiter\w*|debiterad\w*\s+(?:två|2|flera)\s+gånger|"
    r"dragit\s+(?:pengar\s+)?(?:två|2|flera)\s+gånger|återkrav\w*|chargeback|"
    r"rätta\s+(?:\w+\s+){0,2}?(?:uppgift\w*|personuppgift\w*)|"
    r"invänd\w*\s+mot\s+(?:\w+\s+){0,3}?behandling|"
    r"personskad\w*|skadade\s+mig|blev\s+skadad|elchock|brandfara|började\s+brinna|"
    r"försäkrings\w*)\b",
    re.IGNORECASE,
)

#: Kunden mår dåligt, är i kris eller i fara (grundprompten 6.3): eskalera
#: omedelbart med brådska, och svara varmt och kort. Avgörs i kod, som
#: påhoppen — det ska inte hänga på att modellen läste rätt.
_KRIS = re.compile(
    r"\b(självmord\w*|ta\s+livet\s+av\s+mig|vill\s+inte\s+leva|orkar\s+inte\s+leva|"
    r"skada\s+mig\s+själv|mår\s+(?:\w+\s+)?(?:dåligt|skit)\s+(?:psykiskt|på\s+riktigt)|"
    r"jag\s+är\s+i\s+fara|hotad\s+till\s+livet|suicid\w*|kill\s+myself)\b",
    re.IGNORECASE,
)

#: Kunden ber uttryckligen om en människa: se `support_regler.ber_om_manniska`.
#: Fram till 2026-09-18 väckte regexen bara eskaleringssteget och modellen
#: kunde rösta nej. Sedan Ebbot-researchen är begäran en TRIGGER i kod — en
#: kund som ber om en människa får en, utan övertalningsförsök.

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
    # Käll-ID:n (grundprompten avsnitt 3–4): varje påstående ska kunna spåras
    # till ett ID. Numreringen gäller den här körningen; kb_kartan översätter
    # tillbaka till rubriker för medarbetaren.
    return wrap_untrusted_content(
        "\n\n".join(
            f"### [KB-{i}] {a['title']}\n{a['content']}" for i, a in enumerate(articles, 1)
        ),
        source="tenant:kb_article",
    )


def kb_kartan(articles: list[dict[str, Any]]) -> dict[str, str]:
    """{"KB-1": rubrik, ...} i samma numrering som _kb_block."""
    return {f"KB-{i}": str(a.get("title") or "") for i, a in enumerate(articles, 1)}


_KB_ID = re.compile(r"\bKB-(\d+)\b")


def _med_rubriker(text: str, karta: dict[str, str]) -> str:
    """"KB-2" → "KB-2 «Returer»" i en intern notering. Ett körningslokalt
    ID säger ingenting för en medarbetare som läser ärendet i morgon."""

    def _byt(traff: re.Match[str]) -> str:
        rubrik = karta.get(traff.group(0))
        return f"{traff.group(0)} «{rubrik}»" if rubrik else traff.group(0)

    return _KB_ID.sub(_byt, text)


#: Grundpromptens beslut (avsnitt 5 steg 6 och avsnitt 11).
BESLUT = ("SVARA", "MOTFRÅGA", "DELVIS", "ESKALERA")


def tolka_beslut(utkast: dict[str, Any]) -> dict[str, Any]:
    """Utkaststegets avsnitt 11-fält, tolerant lästa. Kastar aldrig.

    `obesvarade` är frågorna modellen själv markerat som saknar_underlag eller
    eskalerad — grundprompten 4.4: en kollega återkommer om dem, alltså är
    ärendet DELVIS även när modellen skrev SVARA i beslutsfältet.
    """
    beslut = str(utkast.get("beslut") or "").strip().upper().replace("MOTFRAGA", "MOTFRÅGA")
    fragor = utkast.get("kundens_frågor") or utkast.get("kundens_fragor") or []
    obesvarade: list[str] = []
    if isinstance(fragor, list):
        for fraga in fragor:
            if not isinstance(fraga, dict):
                continue
            status = str(fraga.get("status") or "").strip().lower()
            if status in ("saknar_underlag", "eskalerad"):
                obesvarade.append(_text(fraga.get("fråga") or fraga.get("fraga")).strip())
    if beslut == "SVARA" and obesvarade:
        beslut = "DELVIS"
    return {
        "beslut": beslut if beslut in BESLUT else None,
        "obesvarade": [f for f in obesvarade if f],
        "brådskande": utkast.get("brådskande") is True or utkast.get("bradskande") is True,
        "intern_notering": _text(utkast.get("intern_notering")).strip(),
        "eskaleringsorsak": _text(utkast.get("eskaleringsorsak")).strip(),
    }


def _intern_motivering(
    orsak_text: str | None, beslut: dict[str, Any], karta: dict[str, str]
) -> str:
    """Ärendets eskaleringsmotivering, med utkastets interna notering (avsnitt
    11) och de obesvarade frågorna. Det är vad medarbetaren läser först."""
    delar = [str(orsak_text or "").strip()]
    if beslut["obesvarade"]:
        delar.append("Obesvarat: " + "; ".join(beslut["obesvarade"][:5]))
    if beslut["intern_notering"]:
        delar.append("Intern notering: " + beslut["intern_notering"])
    return _med_rubriker(" — ".join(d for d in delar if d), karta)[:1500]


#: Svaret säger att en kollega tar över eller återkommer. Ett sådant löfte får
#: bara stå i ett ärende som faktiskt är överlämnat — annars ser ingen
#: människa det, och löftet är en lögn (grundprompten 4.2, "Lova").
_LOVAR_KOLLEGA = re.compile(
    # Bara UTFÖRT ("har skickat vidare"). Presens är oftast ett erbjudande:
    # "svara på mejlet så skickar jag det vidare" (skarptest 2026-10-06).
    r"\b(skickat|lämnat|vidarebefordrat)\s+(\w+\s+){0,3}?vidare\b|"
    r"\bhar\s+(\w+\s+){0,2}?vidarebefordrat\b|"
    r"\b(kollega|medarbetare|handläggare)\w*\s+(\w+\s+){0,3}?"
    r"(återkommer|tar\s+över|hör\s+av\s+sig|kontaktar|svarar)\b|"
    r"\bcolleague\w*\s+(\w+\s+){0,3}?(will|get|take|reply|respond|contact)",
    re.IGNORECASE,
)

#: Käll-ID:n i kundtext: "[KB-1]", "(KB-2, KB-3)", "KB-4". Grundprompten 10.10
#: förbjuder dem mot kund; skarptest 2026-10-06 fick ändå "[KB-1]" i ett mejl.
_KALL_ID_I_TEXT = re.compile(
    r"[ \t]*[\[(]\s*(?:KB-\d+|KUND:[\w-]+)(?:\s*[,;]\s*(?:KB-\d+|KUND:[\w-]+))*\s*[\])]"
    r"|[ \t]*\b(?:KB-\d+|KUND:[\w-]+)\b"
)


def utan_kall_id(text: str) -> str:
    """Kundtexten utan interna käll-ID:n. Deterministiskt, efter modellen."""
    return _KALL_ID_I_TEXT.sub("", text) if text else text


#: Svaret nämner en kollega över huvud taget — då behövs ingen överlämningsrad
#: i kod ovanpå, den hade sagt samma sak två gånger.
_NAMNER_KOLLEGA = re.compile(r"\b(kollega\w*|medarbetare\w*|colleague\w*)\b", re.IGNORECASE)


#: Namnen modellerna brukar välja när de lägger texten i ett objekt.
_TEXTNYCKLAR = ("text", "draft", "final_reply", "revised_draft", "reply", "svar", "content", "message")


def _text(varde: Any) -> str:
    """Ett stegs textfält som text, vad modellen än returnerade.

    Kontraktet säger sträng, men modellen svarar ibland med ett objekt.
    Uppmätt 2026-09-19 i development: en följdfråga på engelska fick
    `"draft": {...}`. Humaniseraren hoppas över på andra språk än svenska, så
    objektet gick rakt in i strip_markdown, som kastade TypeError, och kunden
    fick ett felmeddelande i stället för ett svar. På svenska hade
    humaniseraren dolt felet genom att skriva ny text.

    Ett objekt ger sin text under ett av de vanliga namnen, annars sitt
    längsta textvärde (inte alla ihopslagna: ett objekt per språk hade gett
    ett tvåspråkigt svar). En lista ger sina textdelar i följd.
    """
    if isinstance(varde, str):
        return varde
    if isinstance(varde, dict):
        for nyckel in _TEXTNYCKLAR:
            kandidat = varde.get(nyckel)
            if isinstance(kandidat, str) and kandidat.strip():
                return kandidat
        texter = [_text(v) for v in varde.values()]
        return max(texter, key=len, default="")
    if isinstance(varde, list):
        return "\n\n".join(t for t in (_text(v) for v in varde) if t.strip())
    return ""


#: Ord i en fältnyckel som avslöjar att fältet ÄR svarstexten, när modellen
#: döpt det själv. Kontraktsfälten (sources_used, context_refs) räknas aldrig.
_SVARSLEDTRADAR = ("draft", "utkast", "svar", "response", "reply", "text")


def _textfalt(utdata: dict[str, Any], falt: str) -> str:
    """Stegets svarstext ur `falt`, även när modellen döpt fältet själv.

    Uppmätt 2026-09-19 i development: på engelska följde cs:draft-response
    skillens eget MALLFORMAT i stället för JSON-kontraktet, alltså
    `{"To": ..., "Draft response text": "Your order A-17 ...", "Notes for You":
    {...}}` utan `draft`. Utkastet blev tomt och kunden fick reservtexten
    ("I don't want to guess ..."), trots att modellen skrivit rätt svar.
    Fältet med kontraktets namn vinner; annars det första vars namn bär en
    av _SVARSLEDTRADAR. "Notes for You" och liknande bär ingen ledtråd och
    når därför aldrig kunden.
    """
    direkt = _text(utdata.get(falt))
    if direkt.strip():
        return direkt
    for nyckel, varde in utdata.items():
        namn = str(nyckel).casefold()
        if namn in ("sources_used", "context_refs") or namn.startswith("notes"):
            continue
        if any(ledtrad in namn for ledtrad in _SVARSLEDTRADAR):
            text = _text(varde)
            if text.strip():
                return text
    return ""


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


#: Fler träffar än search_kb:s standard när flera sökfrågor slås ihop. Varje
#: artikel betalas i varje steg som läser underlaget, så taket är lågt.
KB_TAK = 5


def _artikelnyckel(artikel: dict[str, Any]) -> str:
    return str(artikel.get("id") or artikel.get("title") or "")


def _sla_ihop(forsta: list[dict[str, Any]], andra: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Två träfflistor som en, i rangordning, utan dubbletter, högst KB_TAK."""
    ut: list[dict[str, Any]] = []
    sedda: set[str] = set()
    for artikel in [*forsta, *andra]:
        nyckel = _artikelnyckel(artikel)
        if nyckel in sedda:
            continue
        sedda.add(nyckel)
        ut.append(artikel)
    return ut[:KB_TAK]


def _korta_svar(svar: str, tak: int) -> str:
    """Svaret inom kanalens teckentak, kortat vid ett MENINGSSLUT.

    Förut kapades det på tecknet med ett "…" efter — mitt i ett ord, och
    kunden läste "så att alla får ut så mycket som mö…" (kundtest mot
    Livrustning 2026-09-19). Ett meningsslut i takets sista 40 % vinner; finns
    inget kortas det vid ett ordslut med "…".
    """
    if len(svar) <= tak:
        return svar
    utdrag = svar[:tak]
    slut = max(utdrag.rfind(t) for t in (". ", "! ", "? ", ".\n", "!\n", "?\n"))
    if slut >= int(tak * 0.6):
        return utdrag[: slut + 1].rstrip()
    return utdrag[: tak - 1].rsplit(" ", 1)[0].rstrip(" ,;:–—") + "…"


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


def _tid(varde: Any) -> datetime | None:
    """ISO-sträng (båda lagringarna ger det, se postgres._row) → datetime."""
    if not varde:
        return None
    try:
        tid = datetime.fromisoformat(str(varde))
    except ValueError:
        return None
    return tid if tid.tzinfo else tid.replace(tzinfo=timezone.utc)


def ar_overlamnat(samtal: dict[str, Any], *, nu: datetime | None = None) -> bool:
    """Äger en människa samtalet just nu?

    Överlämnat OCH aktivt inom OVERLAMNING_GILTIG_TIMMAR. Ett läge utan
    tidsstämpel räknas som aktivt — hellre en kvittens för mycket än att
    agenten tar tillbaka ett samtal en människa sitter i.
    """
    if samtal.get("lage") != "overlamnad":
        return False
    senast = _tid(samtal.get("updated_at"))
    if senast is None:
        return True
    nu = nu or datetime.now(timezone.utc)
    return nu - senast < timedelta(hours=OVERLAMNING_GILTIG_TIMMAR)


def _faktakallor(
    articles: list[dict[str, Any]],
    *,
    subject: str,
    message: str,
    conversation_block: str,
) -> list[str]:
    """Faktagrindens underlag: kunskapsbasens träffar plus det KUNDEN och en
    MEDARBETARE sagt i samtalet. Agentens egna tidigare repliker ingår inte —
    då hade en uppgift agenten hittat på i tur 2 blivit "stödd" i tur 3."""
    kallor = [f"{a.get('title') or ''}\n{a.get('content') or ''}" for a in articles]
    kallor += [subject or "", message or ""]
    for rad in (conversation_block or "").splitlines():
        if rad.startswith(("Kunden:", "Kollegan:")):
            kallor.append(rad.split(":", 1)[1])
    return kallor


async def _las_samtalslage(storage: Storage, tenant_id: str, customer_id: str) -> dict[str, Any]:
    """Samtalsläget, eller standardläget om läsningen fallerar. Ett trasigt
    läge får aldrig fälla chatten — utan det svarar agenten precis som före
    migration 066."""
    try:
        return await storage.get_chat_state(tenant_id, customer_id)
    except Exception:  # noqa: BLE001 — läget är en förbättring, svaret är jobbet
        logger.exception("Kunde inte läsa samtalsläget (tenant %s).", tenant_id)
        return {"lage": "agent", "misslyckade_i_rad": 0, "erbjod_manniska": False}


async def _spara_samtalslage(
    storage: Storage, tenant_id: str, customer_id: str, **falt: Any
) -> None:
    """Sparar läget. Samma tålighet som läsningen: kunden har redan sitt svar
    sparat, och ett fel här ska synas i loggen, inte i chattbubblan."""
    try:
        await storage.save_chat_state(tenant_id, customer_id, **falt)
    except Exception:  # noqa: BLE001
        logger.exception("Kunde inte spara samtalsläget (tenant %s).", tenant_id)


def _tonblock(installningar: support_regler.SupportInstallningar) -> str:
    """Kundens valda tonläge som en rad i ärendekontexten. Texten är VÅR
    (enumval → fast mening), men den står i case_context ändå: det är kördata
    om den här kunden, inte en regel för alla."""
    text = support_regler.TONLAGEN.get(installningar["tonlage"], "")
    return f"## Tonläge (kundens val)\n{text}" if text else ""


def _amnesblock(installningar: support_regler.SupportInstallningar) -> str:
    """Kundens egen beskrivning av vad agenten ska hjälpa till med. KUNDSKRIVEN
    text — wrappad och i user-position, samma gräns som SOUL (INV-SEC-009)."""
    amne = installningar["amnesomrade"]
    if not amne:
        return ""
    return (
        "## Agentens ämnesområde (kundens beskrivning)\n"
        "Vad agenten är till för. Använd den för att avgöra om en fråga ligger "
        "inom området — den är INTE en faktakälla för svar.\n\n"
        + wrap_untrusted_content(amne, source="tenant:amnesomrade")
    )


#: Frågeord som gör ett meddelande till en FRÅGA även utan frågetecken.
#: Fail-open åt frågehållet: hellre ett riktigt svar för mycket än en kund
#: som bara får kvitton (skärmdumpen 2026-10-05).
_FRAGEORD = frozenset(
    "vem vilka vad hur när nar var varför varfor kan finns går gar fungerar "
    "vill behöver behover what how who why can does where".split()
)


_HALSNINGSSVAR = re.compile(
    r"(hur|vad) kan jag hjälpa( dig| er)?( i ?dag)?|hej[!,. ]*$", re.IGNORECASE
)


def _ar_tomt_halsningssvar(text: str) -> bool:
    """Är utkastet bara en hälsning ("Hej, hur kan jag hjälpa dig?")?

    2.5-flash läser ibland ett meddelande som inleds med "Hej!" som ENBART
    en hälsning och svarar med en motfras — trots att frågan står i samma
    mening och researchen redan bar svaret (batteritesten 2026-10-05, ca
    var tredje körning). Ett sådant svar på en riktig fråga är alltid fel.
    """
    t = " ".join(text.split()).strip()
    return len(t) <= 70 and bool(_HALSNINGSSVAR.search(t))


def _ar_kvittensmeddelande(text: str) -> bool:
    """Är meddelandet bara en kort bekräftelse ("ok", "tack", "ja")?

    Under en överlämning kvitteras bekräftelser utan LLM-anrop — men allt
    som ser ut som en fråga eller ett nytt ärende förtjänar ett riktigt
    svar i stället för ett kvitto. Före 2026-10-05 kvitterades ALLT, och
    "vilka har grundat snajp" fick "Noterat i ärendet".
    """
    t = text.strip().lower()
    if not t:
        return True
    if "?" in t:
        return False
    ord_i_texten = re.findall(r"[a-zåäöé]+", t)
    if any(o in _FRAGEORD for o in ord_i_texten):
        return False
    if support_regler.jakande_svar(t):
        return True
    return len(ord_i_texten) <= 4 and len(t) <= 30


async def _svara_under_overlamning(
    storage: Storage,
    tenant_id: str,
    *,
    samtal: dict[str, Any],
    customer: dict[str, Any],
    message: str,
    started: float,
    aterta: dict[str, str] | None,
    vid_arende: Callable[[str, str], Awaitable[None]] | None,
    is_test: bool,
    pack: str,
) -> dict[str, Any] | None:
    """Kunden skriver i ett samtal en människa äger. Ingen LLM körs.

    Meddelandet läggs i det ÖVERLÄMNADE ärendets tråd — inte i ett nytt
    ärende — så att medarbetaren ser allt på ett ställe och kunden aldrig
    behöver börja om. Svaret är en kvittens medan ingen medarbetare svarat
    ännu, och ingenting alls när en människa redan är i samtalet.

    Returnerar None om det överlämnade ärendet inte längre finns; då tar den
    vanliga kedjan över, hellre än att meddelandet hamnar ingenstans.
    """
    ticket_id = samtal.get("overlamnad_ticket_id")
    arende = await storage.get_ticket(tenant_id, ticket_id) if ticket_id else None
    if not arende or not arende.get("conversation_id"):
        return None
    ticket = {"id": arende["id"], "conversation_id": arende["conversation_id"]}

    if not aterta:
        await storage.save_message(
            tenant_id,
            conversation_id=ticket["conversation_id"],
            direction="inbound",
            content=message,
            sentiment=None,
            has_image=False,
            author="customer",
        )
    if vid_arende:
        await vid_arende(ticket["id"], ticket["conversation_id"])

    meddelanden = await storage.get_messages(tenant_id, ticket["conversation_id"])
    manniska_i_samtalet = any(m.get("author") == "human" for m in meddelanden)
    # 2026-10-05 (Sebbes beställning): en NY FRÅGA medan kollegan ännu inte
    # svarat ska få ett riktigt svar, inte ett kvitto. Inbound är redan
    # sparad i ärendet ovan, så frågan syns för medarbetaren även om kedjan
    # skulle fälla. None släpper vidare till gästläget i run_support_agent —
    # kedjan svarar i SAMMA ärende och överlämningen hävs aldrig. När en
    # människa är i samtalet tiger agenten som förut (INV-ESC-001:s kärna).
    if not manniska_i_samtalet and not _ar_kvittensmeddelande(message):
        return None
    reply = "" if manniska_i_samtalet else support_texter.text("kvittens", samtal.get("sprak"))
    if reply:
        await storage.save_message(
            tenant_id,
            conversation_id=ticket["conversation_id"],
            direction="outbound",
            content=reply,
            sentiment=None,
            has_image=False,
            author="agent",
        )

    # Flyttar updated_at: samtalet hamnar överst i portalens Chattar-vy och
    # överlämningens giltighetstid räknas från det senaste livstecknet.
    await storage.save_chat_state(
        tenant_id,
        customer["id"],
        lage="overlamnad",
        misslyckade_i_rad=int(samtal.get("misslyckade_i_rad") or 0),
        erbjod_manniska=False,
        overlamnad_orsak=samtal.get("overlamnad_orsak"),
        overlamnad_ticket_id=ticket["id"],
        sprak=samtal.get("sprak"),
    )

    step_log = [{"step": "overlamnad", "manniska_i_samtalet": manniska_i_samtalet}]
    run = await storage.log_agent_run(
        tenant_id,
        agent_type="support",
        pack_version=pack,
        skills_used=[],
        input_text=message,
        output_text=reply,
        step_log=step_log,
        tokens_in=0,
        tokens_out=0,
        latency_ms=int((time.monotonic() - started) * 1000),
        is_test=is_test,
        # Samma skäl som svarscachens "svarscache": ingen modell kördes.
        model="overlamnad",
    )
    orsak = samtal.get("overlamnad_orsak")
    return {
        "reply": reply,
        "run_id": (run or {}).get("id"),
        "ticket_id": ticket["id"],
        "customer_id": customer["id"],
        "category": arende.get("category") or "ovrigt",
        "category_label": CATEGORY_LABELS.get(arende.get("category") or "ovrigt", "Övrigt"),
        "sentiment": None,
        "escalated": True,
        "escalation_reason": arende.get("escalation_reason"),
        "escalation_code": orsak,
        "overlamnad": True,
        "svarslage": "overlamnad",
        "faktagrind": None,
        "kb_sources": [],
        "returning_customer": True,
        "simulation": False,
        "skills_used": [],
        "step_log": step_log,
        "cancellation_risk": False,
        "pack_version": pack,
    }


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
    # Kanalerna (bd snipe-36u): en kund i WhatsApp, Messenger, Slack eller
    # Teams är redan uppslagen via ss_channel_contacts
    # (app/kanaler/mottagning.py) — ofta utan e-post, så find_or_create hade
    # skapat en ny kund per meddelande. Satt = uppslaget hoppas över.
    # `customer_phone` följer med till find_or_create och till
    # integrationernas {{kund.telefon}}. Båda None = oförändrat beteende.
    kund_id: str | None = None,
    customer_phone: str | None = None,
    # 2026-10-05: arbetsytans hjälpchatt (autentiserad testchatt) får ett
    # sifferblock med tenantens egna nyckeltal. Flaggan gated:as i Next —
    # se app/agent/arbetsyta_siffror.py för varför den aldrig får sättas
    # för en slutkund.
    arbetsyta: bool = False,
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
    agentkonfig = await storage.get_agent_config(tenant_id, agent_type="support")
    # Kundens egna regler (bd snipe-1fl): eskaleringsgränser, tonläge,
    # ämnesområde och faktakontroll. Standardvärdena är beteendet före flytten.
    installningar = support_regler.normalisera(
        await storage.get_agent_settings(tenant_id, agent_type="support")
    )
    regler = installningar["eskalering"]
    # Grundprompten (2026-10-05): kundtjänstpolicyn som ALLT kundarbete utgår
    # från, renderad för kunden och kanalen och lagd i varje steg. Ingår i
    # instruktionshashen, så pack_version visar vilken version som lästes.
    #
    # HELA prompten (~5 000 tokens) går till stegen som skriver eller bedömer
    # svaret: utkastet, eskaleringsbedömningen, retentionen och faktarättningen.
    # Övriga steg (triage, research, språkputs, artikelförslag) får KÄRNAN —
    # roll, prioritet, källor, säkerhet, skrivregler och driftregeln. Annars
    # hade kostnaden per chattmeddelande ungefär fördubblats (2026-10-06).
    renderat = partial(
        support_systemprompt.rendera,
        foretagsnamn=tenant_namn, kanal=channel, installningar=installningar,
    )
    lager_karna = replace(lager, agent_md=renderat(karna=True))
    lager = replace(lager, agent_md=renderat())
    steg = partial(run_step, instruktioner=lager_karna)
    steg_hel = partial(run_step, instruktioner=lager)

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
    if kund_id:
        customer = {"id": kund_id, "name": customer_name}
    else:
        customer = await storage.find_or_create_customer(
            tenant_id, email=customer_email, phone=customer_phone, name=customer_name
        )
    history = await storage.get_customer_history(tenant_id, customer["id"])

    # --- Samtalsläge (migration 066): äger en människa samtalet? ----------
    #
    # Kontrolleras FÖRE cachen och före varje LLM-anrop. Ett överlämnat
    # samtal ska inte få ett AI-svar som går människan i förväg — Ebbots
    # modell: när en människa tagit över är samtalet hennes tills hon lämnar
    # tillbaka det (eller det legat stilla i OVERLAMNING_GILTIG_TIMMAR).
    samtal = await _las_samtalslage(storage, tenant_id, customer["id"])
    gastlage: dict[str, str] | None = None
    if ar_overlamnat(samtal):
        under_overlamning = await _svara_under_overlamning(
            storage,
            tenant_id,
            samtal=samtal,
            customer=customer,
            message=message,
            started=started,
            aterta=aterta,
            vid_arende=vid_arende,
            is_test=is_test,
            pack=pack_version(SUPPORT_V1.name, lager.hash),
        )
        if under_overlamning is not None:
            return under_overlamning
        # None betyder två saker. Finns det överlämnade ärendet kvar är
        # meddelandet en NY FRÅGA som ska besvaras i GÄSTLÄGE: kedjan kör
        # som vanligt men i samma ärende (via aterta — inbound är redan
        # sparad av _svara_under_overlamning) och samtalsläget förblir
        # överlämnat i slutet. Är ärendet borta tar den vanliga kedjan
        # över helt, som före 2026-10-05.
        _ticket_id = samtal.get("overlamnad_ticket_id")
        _arende = await storage.get_ticket(tenant_id, _ticket_id) if _ticket_id else None
        if _arende and _arende.get("conversation_id"):
            gastlage = {
                "ticket_id": _arende["id"],
                "conversation_id": _arende["conversation_id"],
            }
            aterta = aterta or gastlage

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
    # Arbetsytans siffror (2026-10-05): bara i den autentiserade
    # hjälpchatten. Vår egen kördata, inte kundskriven text — ingen
    # wrapping. Blocket läggs också i faktagrindens källor längre ned, så
    # att siffrorna får citeras utan att grinden stryker dem.
    sifferblock = ""
    if arbetsyta:
        sifferblock = await arbetsyta_siffror.bygg_sifferblock(storage, tenant_id)
        if sifferblock:
            case_context = f"{case_context}\n\n{sifferblock}"
    # Kundens valda tonläge och ämnesområde (bd snipe-1fl). Tonläget är vår
    # text via ett enumval; ämnesområdet är kundskrivet och wrappat.
    for block in (_tonblock(installningar), _amnesblock(installningar)):
        if block:
            case_context = f"{case_context}\n\n{block}"

    # Tonläget läggs på case_context och inte på systemprompten: det är kördata
    # om DET HÄR meddelandet, inte en regel. Tom sträng när inget hänt.
    ton = ton_instruktion(abuse)
    if ton:
        case_context = f"{case_context}\n\n{ton}"

    # Samtalsläget är ett VÄRDE i ärendekontexten, inte i overlayen. Overlays
    # laddas ordagrant utan .format() (se agentcore/overlays.py), så kördata hör
    # hemma här och regeln som läser den står i support-conversation.md.
    #
    # Flyttat FÖRE triagen 2026-09-18: triagen avgör numera om kunden säger
    # att förra svaret missade ("fattar du inte?"), och det går inte att
    # avgöra utan att se förra svaret.
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
        # Förankringen (2026-10-05): historiken ligger SIST i kontexten, så
        # dess senaste fråga stod närmast modellens svar — i skarptest mot
        # dev besvarade 2.5-flash (tänkande av) konsekvent FÖRRA repliken i
        # stället för den aktuella ("vilka har grundat Snajp?" fick förra
        # frågans ärendesiffror). Den aktuella repliken upprepas därför
        # EFTER historiken, så recency pekar på rätt fråga.
        + (
            "\n\nSVARA PÅ KUNDENS AKTUELLA MEDDELANDE, inte på något tidigare "
            "i historiken ovan (den är bara bakgrund). Det aktuella "
            f"meddelandet är:\n{maskera_personnummer(message)[:400]}"
            if turn_count > 0
            else ""
        )
    )
    case_context = f"{case_context}\n\n{conversation_state}"

    ledger = RunLedger(satisfied={"context_pack"})
    trace = RunTrace()

    # --- Steg 1: triage ----------------------------------------------------
    #
    # Kundfakta-fältet (2026-08-27): mem0-mönstrets extraktionssteg, inbakat i
    # triagen i stället för ett eget LLM-anrop — triagen läser ändå hela
    # meddelandet. BARA vad kunden själv uppgett; modellens egna slutsatser
    # (sentiment, kategori) lagras aldrig som fakta.
    #
    # Tre eskaleringssignaler (2026-09-18, bd snipe-1fl), också inbakade här
    # i stället för egna anrop. Modellen LEVERERAR signalerna; beslutet att
    # lämna över fattas i kod längre ned, mot kundens egna gränser.
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
            "Aldrig dina egna bedömningar), "
            "ber_om_manniska (bool: kunden ber i DET HÄR meddelandet uttryckligen "
            "att få prata med eller bli kontaktad av en människa eller medarbetare. "
            "En fråga om du ÄR en människa eller en AI är ingen begäran), "
            "inom_amnesomradet (bool: frågan gäller verksamheten eller något "
            "agenten rimligen ska hjälpa till med. false BARA när den uppenbart "
            "ligger utanför — väder, läxhjälp, andra företags produkter), "
            "missforstadd (bool: kunden säger att förra svaret missade, att du "
            "inte förstått, eller upprepar frustrerat samma fråga), "
            "sprak (ISO 639-1-koden för språket i kundens meddelande, t.ex. "
            "\"sv\", \"en\", \"ar\". \"sv\" när du är osäker eller meddelandet är för "
            "kort för att avgöra), "
            "sokfraga_sv (kundens fråga som en kort svensk sökfråga för "
            "kunskapsbasen, ÄVEN när meddelandet redan är på svenska: kärnan i "
            "frågan med de ord en hjälpartikel troligen har i rubriken, gärna med "
            "ett synonymt ord, t.ex. \"betalningsmetoder betalsätt\" eller "
            "\"leveranstid frakt\"; tom sträng bara när meddelandet inte är en fråga)."
        ),
        case_context=case_context,
    )
    category = triage.get("category") if triage.get("category") in taxonomy else "ovrigt"
    sentiment = max(0.0, min(1.0, float(triage.get("sentiment") or 0.5)))

    # Svarsspråket (bd snipe-xtr): kundens språk om kunden (tenanten) valt
    # det, med förra turens språk som reserv och svenska i varje tveksamhet.
    # Kunskapsbasen är fortfarande svensk — därför en svensk sökfråga nedan.
    svar_sprak = support_regler.svarsprak(
        installningar, triage.get("sprak"), tidigare=samtal.get("sprak")
    )
    ar_svenska = svar_sprak == "sv"
    sprak_namn = support_regler.spraknamn(svar_sprak)

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
            author="customer",
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
    # En fråga på ett annat språk hittar ingenting i en svensk fulltext-
    # sökning. Triagens svenska omformulering tar dess plats.
    #
    # På svenska LÄGGS omformuleringen till (2026-09-19, kundtest mot dev):
    # "Vilka betalsätt har ni?" hittade inte artikeln "Betalningsmetoder vi
    # accepterar" — den svenska stemmern kopplar inte `betalsät` till
    # `betalningsmetod` — utan bara "Så gör du en retur", och den irrelevanta
    # träffen stoppade de senare sökförsöken (de körs bara på en TOM lista).
    # Kunden fick en överlämning på en FAQ. Fulltexten ORar orden och
    # rangordnar med ts_rank, så fler ord ger fler träffmöjligheter.
    sokfraga_sv = _text(triage.get("sokfraga_sv")).strip()
    kb_forsok = ["hela meddelandet"]
    if not ar_svenska and sokfraga_sv:
        sokfraga = sokfraga_sv
        kb_forsok = ["svensk sökfråga"]
    elif sokfraga_sv and sokfraga_sv.casefold() not in sokfraga.casefold():
        sokfraga = f"{sokfraga} {sokfraga_sv}"
        kb_forsok = [f"hela meddelandet + omformulering ({sokfraga_sv!r})"]
    articles = await _sok_kb(storage, tenant_id, sokfraga)
    # 2026-10-06 (Sebbe: "hitta och researcha fram svaren", men billigt): den
    # svenska omformuleringen söks OCKSÅ ensam och träffarna slås ihop. I den
    # långa frågan dränks dess ord — "dubbeldebiterad" hittade inte artikeln
    # "Dubbeldragning eller felaktig debitering" i skarptestet. Databasfrågor,
    # inga LLM-anrop.
    if sokfraga_sv and sokfraga_sv.casefold() != sokfraga.casefold():
        fler = await _sok_kb(storage, tenant_id, sokfraga_sv)
        if any(_artikelnyckel(a) not in {_artikelnyckel(b) for b in articles} for a in fler):
            articles = _sla_ihop(articles, fler)
            kb_forsok.append(f"svensk sökfråga ensam ({sokfraga_sv!r})")
    if not articles:
        bredare = _forenklad_fraga(subject, message)
        if bredare:
            articles = await _sok_kb(storage, tenant_id, bredare)
            kb_forsok.append(f"förenklad fråga ({bredare!r})")
    kb_block = _kb_block(articles)

    # --- Kod + villkorat steg: kundens egna system (bd snipe-36u) ----------
    #
    # Körs bara när kunden har aktiva integrationer (HTTP-verktyg eller
    # MCP-servrar, app/integrationer/). Modellen väljer vilka system som ska
    # frågas; koden anropar, med kundens nycklar som modellen aldrig ser och
    # med kontextvärdena (kund.email …) satta av koden, inte av meddelandet.
    # Utan integrationer: inget anrop, och kedjan är exakt densamma som förut.
    integrationskontext = integrationsuppslag.kontextvarden(
        kund_email=customer_email,
        kund_namn=customer_name,
        kund_telefon=customer_phone,
        kund_id=customer["id"],
        arende_id=ticket["id"],
        kategori=category,
        kanal=channel,
        tenant_namn=tenant_namn,
    )
    underlag = await integrationsuppslag.hamta(
        storage,
        tenant_id,
        steg=steg,
        ledger=ledger,
        trace=trace,
        case_context=f"{case_context}\n\n## Kunskapsbas\n{kb_block}",
        kontext=integrationskontext,
        is_test=is_test,
    )
    systemblock = f"\n\n{underlag.block}" if underlag else ""

    # --- Steg 2: research --------------------------------------------------
    research_uppgift = (
            "Bedöm vad kunskapsbasen faktiskt svarar på och med vilken konfidens. "
            "Returnera JSON: findings (svenska), confidence (0.0-1.0), "
            "kb_supports_answer (bool), missing_info (svenska eller null), "
            "behover_fortydligande (bool: frågan är för vag eller tvetydig för att "
            "besvaras, och en motfråga skulle göra den besvarbar. false när frågan "
            "är tydlig — även om kunskapsbasen saknar svaret. ALLTID false när "
            "findings redan innehåller svaret på frågan: att be kunden välja "
            "mellan tolkningar du redan kan besvara är en gissningsloop, inte "
            "omsorg)."
            + (integrationsuppslag.RESEARCH_TILLAGG if underlag else "")
    )
    research = await steg(
        steps["cs:customer-research"],
        ledger,
        trace,
        task=research_uppgift,
        case_context=(
            f"{case_context}\n\n"
            + (
                "## Kunskapsbas (tillåten faktakälla, liksom uppgifterna från kundens system nedan)"
                if underlag
                else "## Kunskapsbas (ENDA tillåtna faktakällan)"
            )
            + f"\n{kb_block}{systemblock}\n\n"
            f"Tidigare ärenden från kunden: {len(history)}"
        ),
    )

    # TREDJE försöket, på det researchsteget själv säger saknas. Modellen har
    # nu läst frågan OCH sett vad biblioteket innehöll, så `missing_info` är en
    # bättre sökfråga än något vi kan konstruera i kod — den är formulerad i
    # bibliotekets språk, inte i kundens.
    #
    # 2026-10-06: även när det FANNS träffar, så länge researchen säger att de
    # inte bär svaret. Hittar sökningen artiklar som inte redan låg i
    # underlaget görs research om EN gång på det bredare underlaget — ett
    # extra anrop, bara på en miss, och billigare än en människa.
    saknas = str(research.get("missing_info") or "").strip()
    if saknas and not research.get("kb_supports_answer"):
        kanda = {_artikelnyckel(a) for a in articles}
        nya = [
            a for a in await _sok_kb(storage, tenant_id, saknas)
            if _artikelnyckel(a) not in kanda
        ]
        if nya:
            kb_forsok.append(f"missing_info ({saknas[:60]!r})")
            hade_underlag = bool(articles)
            articles = _sla_ihop(articles, nya)
            kb_block = _kb_block(articles)
            if hade_underlag:
                research = await steg(
                    steps["cs:customer-research"],
                    ledger,
                    trace,
                    task=research_uppgift,
                    case_context=(
                        f"{case_context}\n\n## Kunskapsbas (bredare sökning)\n"
                        f"{kb_block}{systemblock}\n\nTidigare ärenden från kunden: {len(history)}"
                    ),
                )

    # --- Kod: vad ska svaret VARA? (bd snipe-1fl, 2026-09-18) --------------
    #
    # Beslutet fattas HÄR, före utkastet, eftersom det ändrar vad utkastet ska
    # vara — inte efteråt, som en efterhandsredigering av en text som redan
    # skrivits. Fyra lägen:
    #
    #   besvara   — kunskapsbasen bär svaret.
    #   fraga     — frågan är för vag; EN motfråga (under kundens tak).
    #   avgransa  — frågan ligger utanför ämnesområdet; säg det och erbjud en
    #               människa (kundens val "erbjud").
    #   overlamna — en människa tar över, i samma chatt.
    #
    # Eskaleringstriggerna är FASTA och avgörs i kod, i prioritetsordning.
    # Modellen levererar signalerna (triage: ber_om_manniska,
    # inom_amnesomradet, missforstadd; research: kb_supports_answer,
    # behover_fortydligande) men kan inte prata bort ett beslut: en kund som
    # ber om en människa får en, och ett träffat känsligt ord lämnas över.
    kb_stodjer_svar = bool(research.get("kb_supports_answer"))
    # Ett lyckat svar ur kundens system är underlag lika mycket som en
    # KB-träff (bd snipe-36u) — "var är min order?" står aldrig i biblioteket.
    kb_saknar_svar = (not articles and not underlag.kallor) or not kb_stodjer_svar

    sentimentgrans = regler["sentimentgrans"] / 100
    kris = bool(_KRIS.search(f"{subject} {message}"))
    sakerhetskritiskt = bool(
        abuse.ska_eskalera
        or cancellation_risk
        or kris
        or triage.get("escalate")
        or sentiment < sentimentgrans
        or _ar_kansligt(f"{subject} {message}")
    )

    # Uttrycklig begäran: ordfiltret i kod, triagens signal (fångar
    # omskrivningar), eller ett ja på agentens eget erbjudande i förra
    # repliken. Ett "ja" läses bara som en begäran när vi faktiskt erbjöd.
    # En fråga om agenten ÄR en människa ("pratar jag med en riktig
    # människa?") är ingen begäran om en (grundprompten 7.3): den besvaras
    # ärligt och med ett erbjudande. Skarptest 2026-10-06 lämnade över den.
    identitetsfraga = support_regler.fragar_om_ai(f"{subject} {message}")
    bad_om_manniska = bool(
        support_regler.ber_om_manniska(f"{subject} {message}")
        or (triage.get("ber_om_manniska") is True and not identitetsfraga)
        or (samtal.get("erbjod_manniska") and support_regler.jakande_svar(message))
    )

    # Utanför ämnesområdet kräver BÅDA: triagen säger att frågan ligger
    # utanför, och kunskapsbasen bär inget svar. En falsk "utanför" på en
    # fråga biblioteket kan besvara ska aldrig kosta kunden svaret.
    utanfor_amnet = triage.get("inom_amnesomradet") is False and kb_saknar_svar

    # Saknat fält = dagens beteende (fråga hellre än lämna över). Bara ett
    # uttryckligt false från researchsteget gör en KB-miss till "utanför
    # kunskapsbasen" — en tydlig fråga biblioteket inte kan besvara.
    behover_fortydligande = research.get("behover_fortydligande") is not False
    missforstadd = regler["frustration_raknas"] and triage.get("missforstadd") is True

    # Misslyckade rundor i FÖLJD. En runda är misslyckad när agenten måste
    # ställa en motfråga, eller när kunden säger att förra svaret missade —
    # högst EN per runda. En lyckad runda nollar räknaren. Taket är kundens
    # (`max_misslyckade`, standard 2 = två motfrågor, sedan en människa).
    #
    # Ersätter `turn_count <= 2` (2026-09-02), som räknade samtalets ALLA
    # repliker: en kund med tre besvarade frågor bakom sig fick aldrig en
    # motfråga på sin fjärde, och en kund som sa "fattar du inte?" räknades
    # inte alls — den loop Ebbots chatt fastnade i.
    tidigare_misslyckade = (
        int(samtal.get("misslyckade_i_rad") or 0) if samtal.get("lage") == "agent" else 0
    )
    vill_fraga = (
        kb_saknar_svar
        and behover_fortydligande
        and not sakerhetskritiskt
        and not bad_om_manniska
        and not utanfor_amnet
    )
    runda_misslyckad = missforstadd or vill_fraga
    misslyckade_nu = tidigare_misslyckade + 1 if runda_misslyckad else 0
    tak_nått = runda_misslyckad and misslyckade_nu > regler["max_misslyckade"]

    orsak: str | None = None
    if abuse.ska_eskalera:
        orsak = "pahopp"
    elif bad_om_manniska:
        orsak = "kund_bad_om_manniska"
    elif sakerhetskritiskt:
        orsak = "sakerhet"
    elif utanfor_amnet:
        if regler["utanfor_amnet"] == "eskalera":
            orsak = "utanfor_amnesomradet"
    elif tak_nått:
        orsak = "fortydligandetak"
    # 2026-10-05 (Sebbes beställning): en tydlig fråga utanför kunskapsbasen
    # lämnar inte längre över PER AUTOMATIK. Den gamla regeln låste samtalet —
    # "vilka har grundat Snajp?" gav lage=overlamnad och varje senare fråga
    # fick bara fasta kvitton. Nu svarar agenten ärligt på det underlaget
    # täcker och ERBJUDER en kollega (kundens "ja" blir en överlämning via
    # erbjod_manniska). Eskaleringsbedömningen (steg 4, körs redan vid varje
    # KB-miss) kan fortfarande rösta överlämning när ärendet i sig kräver en
    # människa. Grundningen är intakt: uppgiften förbjuder påhittade fakta
    # och faktagrinden kör som vanligt.
    #
    # Samma eftermiddag kom grundprompten (support_systemprompt.py): en fråga
    # utan källa skickas till en kollega (4.4, 6.3). Den överlämningen görs
    # EFTER utkastet, på utkastets eget beslut (DELVIS/ESKALERA), och tack vare
    # gästläget låser den inte samtalet — det var det låset som var felet.

    if orsak:
        svarslage = "overlamna"
    elif utanfor_amnet:
        svarslage = "avgransa"
    elif vill_fraga:
        svarslage = "fraga"
    else:
        svarslage = "besvara"
    arligt_utanfor_kb = svarslage == "besvara" and kb_saknar_svar
    # Namnet står kvar för läsbarhetens skull: det är vad eskaleringssteget
    # och testerna frågar efter ("ställer svaret en följdfråga?").
    fragar_uppfoljning = svarslage == "fraga"

    # --- Steg 3: utkast ----------------------------------------------------
    missade_rad = (
        "Kunden säger att förra svaret missade. Läs samtalet igen, svara på det "
        "kunden faktiskt frågar och upprepa inte förra svaret. "
        if missforstadd
        else ""
    )
    if svarslage == "fraga":
        uppgift = (
            missade_rad
            + "Kunskapsbasen räcker inte för att svara på frågan, men ärendet är "
            "varken juridiskt, säkerhetskritiskt eller en uppsägningsrisk. "
            "Lämna INTE över till en människa. "
            # Skarptest 2026-10-05: "Jag har information om vilka som grundat
            # Snajp. Vill du veta personerna eller ägarstrukturen?" — en
            # motfråga om något underlaget redan besvarar är gissningsloopen
            # i ny kostym.
            "MEN FÖRST: täcker researchen eller kunskapsbasen redan frågan — "
            "besvara den då direkt och ställ ingen motfråga alls. Annars: "
            "ställ EN kort, öppen "
            "följdfråga som skulle göra frågan besvarbar — den mest användbara "
            "du kan komma på. Säg gärna i en halv mening vad du uppfattat, så att "
            "kunden ser vad som saknas. Påstå ingenting om produkten eller "
            "villkoren som inte står i kunskapsbasen, och lova inte att någon "
            "återkommer. Ren text, ingen markdown. Returnera JSON: draft (svenska)."
        )
    elif svarslage == "avgransa":
        uppgift = (
            "Frågan ligger utanför det du är här för att hjälpa till med. Säg det "
            "vänligt och kort, berätta i en mening vad du KAN hjälpa till med "
            "(utifrån ämnesområdet eller kunskapsbasen), och fråga om kunden vill "
            "att du kopplar in en kollega. Svara inte på själva frågan och gissa "
            "inte. Ren text, ingen markdown. Returnera JSON: draft (svenska)."
        )
    elif svarslage == "overlamna":
        inledning = {
            # Grundprompten 6.3: varmt och kort, eskalera omedelbart. 112 är
            # allmän kunskap och läggs i faktagrindens källor längre ned.
            "kris": (
                "Kunden verkar må dåligt eller vara i fara. Svara varmt, kort och "
                "medmänskligt. Säg att du tar det på allvar och att en kollega "
                "tar över. Är kunden i akut fara: skriv att hen ska ringa 112. "
                "Försök inte lösa något annat i ärendet nu. "
            ),
            "kund_bad_om_manniska": (
                "Kunden har bett om en människa. Bekräfta kort att du kopplar in "
                "en kollega — försök inte lösa ärendet själv och försök inte "
                "övertala kunden att stanna hos dig. "
            ),
            "sakerhet": (
                "Ärendet rör något en människa måste avgöra (pengar, juridik, "
                "personuppgifter eller ett tydligt missnöje). Svara bara på det "
                "kunskapsbasen täcker om det besvarar kundens EGEN fråga — "
                "återberätta aldrig allmänt vad produkten gör. Lova ingenting om "
                "utfallet. "
            ),
        }.get(
            "kris" if kris else orsak or "",
            "Du kan inte svara säkert på det här utifrån kunskapsbasen — gissa "
            "inte, och påstå ingenting om produkten eller villkoren. ",
        )
        # Kundtest 2026-09-22: "Vår supportagent krashade, vad gör ni åt det?"
        # fick först en allmän beskrivning av agenten och sedan "jag har ingen
        # information om vad som orsakar en krasch" — som om kunden pratade om
        # något okänt. Överlämningen var rätt; svaret lät dumt. En kollega
        # behöver detaljerna ändå, så svaret ska ta in dem direkt.
        uppgift = (
            inledning
            + "Inled inte med en beskrivning av dig själv eller tjänsten, och säg "
            "aldrig att du saknar information om det kunden beskriver som om det "
            "vore något okänt. Beskriver kunden ett fel eller problem utan "
            "detaljer: bekräfta kort att du förstått och be om det en kollega "
            "behöver för att lösa det — till exempel vad som hände, ett "
            "eventuellt felmeddelande och när det började — som högst två korta "
            "frågor i samma mening. Berätta sedan att en kollega tar över HÄR i "
            "chatten, att hela samtalet följer med så att kunden inte behöver "
            "upprepa något, och att svaret kommer i samma chatt. Lova ingen tid. "
            "Håll hela svaret kort. Ren text, ingen markdown. Returnera JSON: "
            "draft (svenska)."
        )
    elif arligt_utanfor_kb:
        # Grundpromptens driftregel (support_systemprompt.DRIFTREGEL,
        # 2026-10-06): en vanlig kunskapslucka lämnas inte över. Agenten letar
        # i hela underlaget, svarar på det som har källa och ERBJUDER en
        # kollega för resten — kundens "ja" blir överlämningen.
        uppgift = (
            missade_rad
            + "Kunskapsbasen saknar helt eller delvis svar på frågan, men ärendet "
            "är varken juridiskt, säkerhetskritiskt eller en uppsägningsrisk. "
            "Läs frågan noga och leta i HELA underlaget, även i artiklar med en "
            "annan rubrik — svaret står ibland där. Svara på det du har källa för "
            "(även delvis hjälp är hjälp). För det som saknar källa: säg rakt ut "
            "att du inte har den uppgiften, utan att låta som att kundens fråga "
            "är konstig, och fråga om kunden vill att en kollega tittar på just "
            "det. Lova inte att någon återkommer — erbjud. Beslutet är DELVIS "
            "(eller SVARA om allt hade källa). Hitta ALDRIG på fakta, siffror, "
            "namn eller löften. Ren text, ingen markdown. Returnera JSON: draft (svenska)."
        )
    else:
        uppgift = (
            missade_rad
            + "Skriv ett svar till kunden, grundat ENBART i kunskapsbasen ovan. "
            "Täcker kunskapsbasen bara en del av frågan: svara på den delen och "
            "säg rakt ut vilken del du inte har någon uppgift om — gissa aldrig "
            "och fyll aldrig i luckor. Avsluta med ETT konkret nästa steg som "
            "hjälper kunden vidare (vad hen kan göra nu, eller en kort fråga om "
            "något närliggande), hämtat ur kunskapsbasen eller ärendet — inte en "
            "standardfras. Ren text, ingen markdown. Returnera JSON: draft (svenska)."
        )
    # Mallformat-spärren gäller ALLA språk (2026-10-05): den stod bara i den
    # icke-svenska varianten, och i skarptest svarade utkaststeget på svenska
    # i skillens To/Re/Notes-objekt — med fel svar i mallfältet ("kunden har
    # bara skickat en hälsning") trots att researchen bar hela svaret.
    uppgift += (
        " Fältet draft ska vara EN sträng med hela svaret till kunden — "
        "aldrig skillens mallformat (To/Re/Notes) och aldrig ett objekt. "
        "Läs HELA kundens meddelande: en inledande hälsning är inte ärendet, "
        "svara på frågan som följer efter den. Nämn aldrig kunskapsbasen, "
        "källor eller käll-ID:n för kunden — säg i stället att du inte har "
        "den uppgiften."
        # Grundprompten avsnitt 5, 10 och 11 (2026-10-05). Fälten läses av
        # koden nedan: DELVIS/ESKALERA blir en överlämning, och den interna
        # noteringen blir det medarbetaren läser på ärendet.
        " Gå igenom grundpromptens arbetsflöde (avsnitt 5) och självkontroll "
        "(avsnitt 10) innan du svarar. Lägg utöver draft till grundpromptens "
        "fält ur avsnitt 11: beslut (SVARA, MOTFRÅGA, DELVIS eller ESKALERA), "
        "känsloläge, brådskande (bool), kundens_frågor (lista med fråga, status "
        "och källor — käll-ID:n som KB-2 eller KUND:<system>), intern_notering "
        "(svenska, för en kollega) och eskaleringsorsak (regeln i 6.3 som "
        "träffade, eller null). draft är grundpromptens svarsutkast — skriv det "
        "bara en gång. Följ driftregeln sist i grundprompten: ESKALERA bara för "
        "ämnena i 6.3, aldrig för en vanlig kunskapslucka."
    )
    if underlag:
        uppgift += integrationsuppslag.UTKAST_TILLAGG
    if not ar_svenska:
        uppgift = uppgift.replace(
            "Returnera JSON: draft (svenska).",
            f"Skriv hela svaret på {sprak_namn} — kundens språk — även om "
            f"kunskapsbasen är på svenska. Returnera JSON med fältet draft: EN "
            f"sträng med hela svaret till kunden på {sprak_namn}. Inte skillens "
            f"mallformat (To/Re/Notes) och inga andra textfält.",
        )
    draft = await steg_hel(
        steps["cs:draft-response"],
        ledger,
        trace,
        task=uppgift,
        case_context=(
            f"{case_context}\n\n## Kunskapsbas\n{kb_block}{systemblock}\n\n"
            f"## Research\n{research.get('findings', '')}"
        ),
    )
    # Kodgrind mot två kända felsvar (EN omkörning med tillsägelse — samma
    # mönster som step_runnerns kontraktsbrott; en prompt går att prata
    # omkull, grinden gör det inte):
    # 1. Mallformatet: draft som objekt (skillens To/Re/Notes-mall).
    # 2. Tomt hälsningssvar på en riktig fråga ("Hej, hur kan jag hjälpa
    #    dig?" på "Hej! Vilka har grundat Snajp?").
    # Grundpromptens avsnitt 11 kallar fältet `svarsutkast`, och modellen följer
    # det även när uppgiften säger `draft`. Skarptest 2026-10-06: varje utkast
    # kördes om av formatgrinden nedan för det — ett helt extra anrop per
    # ärende för ett namnbyte. Promptens namn godtas.
    if not isinstance(draft.get("draft"), str) and isinstance(draft.get("svarsutkast"), str):
        draft["draft"] = draft["svarsutkast"]
    tillsagelse = ""
    if not isinstance(draft.get("draft"), str):
        tillsagelse = (
            "FÖRRA FÖRSÖKET bröt formatet: draft var ett objekt (skillens "
            "To/Re/Notes-mall), inte en sträng. Gör om. "
        )
    elif _ar_tomt_halsningssvar(draft["draft"]) and not _ar_kvittensmeddelande(message):
        tillsagelse = (
            "FÖRRA FÖRSÖKET svarade bara med en hälsning. Kundens meddelande "
            "innehåller en FRÅGA efter hälsningen — läs hela meddelandet och "
            "besvara frågan. "
        )
    if tillsagelse:
        draft = await steg_hel(
            steps["cs:draft-response"],
            ledger,
            trace,
            task=tillsagelse + uppgift,
            case_context=(
                f"{case_context}\n\n## Kunskapsbas\n{kb_block}{systemblock}\n\n"
                f"## Research\n{research.get('findings', '')}"
            ),
        )

    # --- Steg 4: eskaleringsbedömning (villkorat) ---------------------------
    #
    # Steget kör med thinking påslaget och är kedjans dyraste anrop. Det körs
    # när det finns något för modellen att bedöma UTÖVER kodbeslutet: en
    # kunskapslucka eller ett säkerhetskritiskt ärende, där stegets motivering
    # blir det medarbetaren läser. Hoppas över (2026-09-18) när kunden bett om
    # en människa — beslutet är redan fattat i kod och motiveringen given —
    # och när frågan ligger utanför ämnesområdet med kundens val "erbjud":
    # där hade stegets "eskalera om kunskapsbasen saknar svar" lämnat över en
    # väderfråga.
    #
    # 2026-10-06 (driftregeln, Sebbe: "sällan eskalera"): bara när ärendet är
    # säkerhetskritiskt. En kunskapslucka — i ärligt-läget, i motfrågeläget
    # eller som DELVIS — avgörs av utkastets beslut och kundens svar på
    # erbjudandet. Skarptest i dev: "Hej! Vilka har grundat Snajp?" fick en
    # felbedömd research (motfrågeläge), steget röstade över och kunden fick
    # ett överlämningsbesked på en fråga kunskapsbasen bar svaret på. Bonus:
    # kedjans dyraste anrop (thinking) körs inte längre på någon KB-miss.
    behover_eskaleringsbedomning = bool(
        sakerhetskritiskt
        and orsak != "kund_bad_om_manniska"
        and svarslage != "avgransa"
    )
    if not behover_eskaleringsbedomning:
        escalation: dict[str, Any] = {"should_escalate": False, "reason": None}
    else:
        escalation = await steg_hel(
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
                    # 2026-10-05: KB-missen ENSAM är inte längre eskaleringsskäl —
                    # svaret säger ärligt vad som saknas och erbjuder en kollega,
                    # och kundens ja blir överlämningen. Modellen ska bara fälla
                    # ärenden som i sig kräver en människa.
                    else "Kunskapsbasen saknar helt eller delvis svar, och svaret "
                    "till kunden säger det ärligt och skickar det som saknas vidare "
                    "till en kollega. Att "
                    "kunskapsbasen saknar svaret är därför INTE ensamt ett skäl "
                    "att eskalera — eskalera bara om ärendet i sig måste till en "
                    "människa enligt listan ovan, eller om svaret till kunden "
                    "vore vilseledande utan en. "
                    if arligt_utanfor_kb
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
    # `orsak` bär kodens fasta triggers; modellens egen `should_escalate`
    # (juridik/ARN/GDPR-nyansen) kan lägga till en överlämning men aldrig ta
    # bort en. Triageflaggan, lågt sentiment, uppsägningsrisk och påhopp
    # ingår i `sakerhetskritiskt` och är lika lätta att utlösa som förut.
    #
    # Grundpromptens beslut (2026-10-05) är en signal till av samma slag: ett
    # utkast som själv säger DELVIS eller ESKALERA lämnar över, och en fråga
    # det markerat som saknar_underlag gör beslutet till DELVIS (4.4). Aldrig
    # åt andra hållet — ett SVARA tar inte bort en överlämning koden beslutat.
    # Avgränsningen ("utanför ämnet", kundens val "erbjud") rörs inte.
    utkastbeslut = tolka_beslut(draft)
    # Researchen bedömde frågan som oklar, men utkastet hittade svaret och
    # besvarade den (uppgiften säger "besvara direkt om underlaget täcker
    # frågan"). Då är det ett besvarat ärende, inte en misslyckad runda —
    # annars räknar taket för motfrågor upp mot en överlämning på frågor som
    # faktiskt fick svar.
    if svarslage == "fraga" and utkastbeslut["beslut"] == "SVARA" and not missforstadd:
        svarslage = "besvara"
        misslyckade_nu = 0
    # Driftregeln (2026-10-06, Sebbe: "sällan behöva eskalera"): bara ESKALERA
    # lämnar över. DELVIS är en kunskapslucka, och den besvaras med ett
    # erbjudande — kundens "ja" blir överlämningen via erbjod_manniska.
    utkast_lamnar_over = svarslage in ("besvara", "fraga") and utkastbeslut["beslut"] == "ESKALERA"
    modellen_lamnar_over = (
        bool(escalation.get("should_escalate")) or utkast_lamnar_over
    ) and orsak is None
    if modellen_lamnar_over:
        orsak = "modellbedomning"
    # Ett MOTFRÅGA-beslut i besvara-läget är en misslyckad runda precis som
    # kodens egen motfråga — annars kunde modellen fråga i all oändlighet.
    if (
        not runda_misslyckad
        and svarslage == "besvara"
        and utkastbeslut["beslut"] == "MOTFRÅGA"
        and orsak is None
    ):
        misslyckade_nu = tidigare_misslyckade + 1
    escalated = orsak is not None
    escalation_reason = (
        # Påhoppet vinner över modellens egen motivering: en människa som tar
        # över ärendet ska se VARFÖR det lämnades över, och "kunskapsbasen
        # saknade svar" är fel förklaring på ett hot.
        f"Avbrutet samtal: {abuse.niva}"
        if abuse.ska_eskalera
        else _text(escalation.get("reason"))
        or (utkastbeslut["eskaleringsorsak"] if escalated else "")
        or ("retention_risk" if cancellation_risk else None)
    )
    if escalated and not escalation_reason:
        escalation_reason = (
            f"Kunskapsbasen räckte inte ({', '.join(kb_forsok)} prövades, "
            f"kb_supports_answer={kb_stodjer_svar})"
            if orsak in ("utanfor_kunskapsbasen", "fortydligandetak") and kb_saknar_svar
            else support_regler.ORSAKER.get(orsak or "", "Lågt sentiment eller triageflagga")
            if orsak != "sakerhet"
            else "Kunden verkar må dåligt eller vara i fara — brådskande."
            if kris
            else "Lågt sentiment eller triageflagga"
        )
    kartan = kb_kartan(articles)
    if escalated and not abuse.ska_eskalera:
        escalation_reason = _intern_motivering(escalation_reason, utkastbeslut, kartan)

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
    #
    # 2026-09-18: och bara när eskaleringssteget kördes. Steget kräver det
    # (`requires` i support_playbook.py), och de fall där det numera hoppas
    # över är inga kunskapsluckor: en väderfråga ska inte bli ett
    # artikelförslag, och en kund som ber om en människa har inte avslöjat
    # något biblioteket saknar.
    #
    # 2026-09-19: och inte när agenten ställer en motfråga. En fråga som är
    # för vag att besvara går inte att skriva en artikel om, och luckan (om
    # det finns en) fångas nästa tur när kunden förtydligat. ~5 000 tokens
    # per motfrågetur.
    if (
        (kb_saknar_svar or sakerhetskritiskt)
        # Ärligt-läget hoppar över bedömningssteget men luckan är lika
        # verklig — annars hade KB:n slutat växa ur precis de ärenden som
        # numera besvaras ärligt i stället för att eskaleras (2026-10-05).
        and (behover_eskaleringsbedomning or arligt_utanfor_kb)
        and svarslage != "fraga"
    ):
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
    current_draft = _textfalt(draft, "draft")

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
        retention = await steg_hel(
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
        current_draft = _textfalt(retention, "revised_draft") or current_draft

    # --- Steg 7: humanizer (ALLTID sist) -----------------------------------
    #
    # Bara på svenska (bd snipe-xtr). Skillen är snajp:humanizer-SVENSKA: på
    # ett annat språk hade den översatt tillbaka till svenska, alltså ångrat
    # det enda utkaststeget just gjort. Där är utkastet sista handen.
    humanized = {"final_reply": current_draft} if not ar_svenska else await steg(
        steps["snajp:humanizer-svenska"],
        ledger,
        trace,
        task=(
            "Gör texten naturlig svenska enligt skillen. Behåll all sakinformation. "
            # Grundprompten 4.2 "Utvidga" (skarptest 2026-10-06: "en butik i
            # Göteborg" blev "vår enda fysiska butik ... det går inte att
            # hämta ordrar i butik").
            "Lägg aldrig till, skärp eller generalisera ett påstående (som "
            "'enda', 'alltid', 'bara', 'går inte'), och behåll varje 'det har jag "
            "ingen uppgift om' och varje erbjudande om en kollega som det står. "
            "Ren text, ingen markdown. Korrekturläs till sist: felfri stavning, "
            "grammatik och skiljetecken. Returnera JSON: final_reply (svenska)."
        ),
        case_context=f"{case_context}\n\n## Text att humanisera\n{current_draft}",
    )

    reply = strip_markdown(_textfalt(humanized, "final_reply") or current_draft or "").strip()
    # Efter humaniseraren, före längdkapningen: en avslutningsfras utan namn
    # under är trasig oavsett vilket steg som skrev den.
    reply = strip_dangling_sign_off(reply)
    # Textkvalitetslagret (app/textkvalitet.py): deterministisk putsning av
    # blanksteg, hängande hälsningar och entydiga felstavningar. Medvetet
    # bara putsningen här — faktagrinden nedan är redan svarets grind, och
    # ett chattsvar ska inte kosta ett extra LLM-anrop.
    from ..textkvalitet import putsa as _putsa_text

    reply, _ = _putsa_text(reply)

    # --- Kod: faktagrinden (bd snipe-1fl) ----------------------------------
    #
    # Körs på den EXAKTA text kunden ska få, efter humaniseraren — samma
    # princip som INV-GROUND-001 i leads: en instruktion om att bara grunda
    # sig i kunskapsbasen är en förhoppning, grinden är en kontroll. Nivån är
    # kundens (tillatande/forsiktig/strikt, se support_faktagrind.py).
    #
    # EN reparationsrunda: humaniseraren får stryka just det som saknar stöd.
    # Fäller grinden igen kastas texten — hellre ett uttryckligt "det vet jag
    # inte" och ett erbjudande om en människa än en uppgift vi inte kan stå
    # för. Påhoppsrepliken kontrolleras inte: den är vår fasta text.
    # Ett "ja" på nästa tur blir en överlämning (rad ~1083): både när vi
    # avgränsade och när vi svarade ärligt utanför kunskapsbasen och erbjöd
    # en kollega för resten.
    # Ärligt-läget ERBJUDER inte längre en kollega (grundprompten 4.4: frågan
    # skickas vidare, se utkastets uppgift) — kvar är avgränsningen.
    # Erbjudandet om en kollega: avgränsningen, en kunskapslucka (ärligt-läget
    # eller utkastets DELVIS) och en fråga om agenten är en AI. Ett "ja" på
    # nästa tur blir en överlämning.
    erbjod_manniska = bool(
        svarslage == "avgransa"
        or (
            not escalated
            and (arligt_utanfor_kb or utkastbeslut["beslut"] == "DELVIS" or identitetsfraga)
        )
    )
    faktagrind: dict[str, Any] = {"niva": installningar["faktakontroll"], "ok": True}
    if reply and not abuse.ska_eskalera:
        kallor = _faktakallor(
            articles, subject=subject, message=message, conversation_block=conversation_block
        )
        if kris:
            # Krissvaret får hänvisa till 112 (allmän kunskap, inte en
            # företagsuppgift) utan att grinden stryker numret.
            kallor.append("Vid akut fara: ring 112.")
        # Lyckade svar ur kundens system (bd snipe-36u) är stöd precis som
        # kunskapsbasen — annars fälls ett korrekt återgivet leveransdatum.
        kallor += underlag.kallor
        # Arbetsytans siffror är vår egen kördata: ett korrekt återgivet
        # nyckeltal ska inte strykas som ostött.
        if sifferblock:
            kallor.append(sifferblock)
        dom = support_faktagrind.kontrollera(
            reply, niva=installningar["faktakontroll"], kallor=kallor, tenant_namn=tenant_namn
        )
        if not dom.ok:
            faktagrind.update(ok=False, ostodda=list(dom.ostodda), reparerad=False)
            logger.warning(
                "Faktagrinden fällde supportsvaret (tenant %s): %s", tenant_id, dom.ostodda
            )
            rattning = await steg_hel(
                steps["snajp:humanizer-svenska" if ar_svenska else "cs:draft-response"],
                ledger,
                trace,
                task=(
                    "Texten innehåller uppgifter som INTE finns i kunskapsbasen: "
                    + "; ".join(dom.ostodda)
                    + ". Skriv om texten så att de uppgifterna stryks. Där de "
                    "behövdes: säg rakt ut att du inte har den uppgiften. Hitta inte "
                    "på något nytt och ändra inget annat. Ren text, ingen markdown. "
                    + (
                        "Returnera JSON: final_reply (svenska)."
                        if ar_svenska
                        else f"Skriv på {sprak_namn}. Returnera JSON med fältet final_reply: "
                        f"EN sträng med hela den rättade texten, inte skillens "
                        f"mallformat (To/Re/Notes)."
                    )
                ),
                case_context=f"{case_context}\n\n## Kunskapsbas\n{kb_block}{systemblock}\n\n## Text att rätta\n{reply}",
            )
            kandidat = strip_dangling_sign_off(
                strip_markdown(_textfalt(rattning, "final_reply")).strip()
            )
            if kandidat and support_faktagrind.kontrollera(
                kandidat, niva=installningar["faktakontroll"], kallor=kallor, tenant_namn=tenant_namn
            ).ok:
                reply = kandidat
                faktagrind.update(ok=True, reparerad=True)
            elif escalated:
                reply = support_texter.text("overlamningssvar", svar_sprak)
            else:
                reply = support_texter.text("osakerhet", svar_sprak)
                erbjod_manniska = True

    # Modellens eskaleringsbedömning lämnade över ett samtal koden tänkt
    # besvara eller fråga i. Löftet om en människa läggs på i KOD — det får
    # bara ges när ärendet faktiskt är överlämnat, och kunden ska få veta att
    # det sker i samma chatt. En motfråga ersätts helt: "vilken telefon har
    # du? en kollega tar över" är två besked som motsäger varandra.
    if modellen_lamnar_over and not abuse.ska_eskalera:
        if svarslage == "fraga" or not reply:
            reply = support_texter.text("overlamningssvar", svar_sprak)
        elif not _NAMNER_KOLLEGA.search(reply):
            # Ett DELVIS/ESKALERA-utkast (mall 6/7) säger redan att en kollega
            # tar över — då hade raden sagt det en gång till.
            reply = f"{reply}\n\n{support_texter.text("overlamningsrad", svar_sprak)}"

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
            reply = support_texter.text("overlamningssvar", svar_sprak)
        else:
            reply = support_texter.text("tomt", svar_sprak)
    # Löftesgrinden (grundprompten 4.2): ett svar som säger att frågan skickats
    # vidare eller att en kollega återkommer, i ett ärende ingen har lämnat
    # över, lovar något ingen människa ser. Hellre att löftet blir sant än att
    # texten skrivs om — vid tveksamhet: eskalera (6.3). Utom i avgränsningen,
    # vars erbjudande är kundens val.
    if (
        not escalated
        and not abuse.ska_eskalera
        and svarslage != "avgransa"
        and _LOVAR_KOLLEGA.search(reply)
    ):
        orsak = "modellbedomning"
        escalated = True
        erbjod_manniska = False
        escalation_reason = _intern_motivering(
            "Svaret lovade att en kollega tar över, så ärendet lämnades över.",
            utkastbeslut,
            kartan,
        )
    reply = utan_kall_id(reply)
    # Krisgarantin: hänvisningen till 112 ska inte hänga på att modellen och
    # humaniseraren behöll den (skarptest 2026-10-06: den föll bort).
    if kris and "112" not in reply:
        reply = f"{reply}\n\n{support_texter.text('kris', svar_sprak)}".strip()
    reply = _korta_svar(reply, config["max_length"])

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
        author="agent",
    )
    await storage.log_metric(
        tenant_id, ticket_id=ticket["id"], metric_name="sentiment", value=sentiment
    )

    # Kundens eget ärendesystem (bd snipe-36u): en förfrågan bunden till
    # arende_eskalerat skapar ärendet där med hela samtalet. Samma villkor som
    # det prioriterade mejlet ovan — EN gång per överlämning, inte per
    # meddelande. Efter att svaret sparats, så att agentens överlämningsreplik
    # följer med i samtalet, och i bakgrunden, så att ett långsamt
    # ärendesystem aldrig blir kundens väntetid.
    if (
        escalated
        and not any(t.get("status") == "escalated" for t in history)
        and await integrationshandelser.har_handelse(storage, tenant_id, "arende_eskalerat")
    ):
        integrationshandelser.eskalering_i_bakgrunden(
            storage,
            tenant_id,
            kontext=integrationskontext,
            customer_id=customer["id"],
            orsak=escalation_reason,
            orsakskod=orsak,
            arendelank=arendelank(settings.publik_bas_url, ticket["id"]),
            is_test=is_test,
        )

    # Samtalsläget (migration 066). Vid överlämning äger en människa samtalet
    # från och med nu: nästa meddelande från kunden hamnar i DET HÄR ärendets
    # tråd och får ingen AI-replik (se _svara_under_overlamning). Annars
    # sparas räknaren för misslyckade rundor och om vi erbjöd en människa.
    if gastlage:
        # Gästläge: samtalet ägs fortfarande av en människa. Agentens
        # sidosvar häver ALDRIG överlämningen — läget, orsaken och ärendet
        # står kvar oavsett vad den här turen kom fram till (INV-ESC-001).
        await _spara_samtalslage(
            storage,
            tenant_id,
            customer["id"],
            lage="overlamnad",
            misslyckade_i_rad=0,
            erbjod_manniska=False,
            overlamnad_orsak=samtal.get("overlamnad_orsak"),
            overlamnad_ticket_id=gastlage["ticket_id"],
            sprak=svar_sprak,
        )
    else:
        await _spara_samtalslage(
            storage,
            tenant_id,
            customer["id"],
            lage="overlamnad" if escalated else "agent",
            misslyckade_i_rad=0 if escalated else misslyckade_nu,
            erbjod_manniska=False if escalated else erbjod_manniska,
            overlamnad_orsak=orsak if escalated else None,
            overlamnad_ticket_id=ticket["id"] if escalated else None,
            sprak=svar_sprak,
        )

    # --- Fas R2: cache-STORE (INV-CACHE-001) --------------------------------
    #
    # Bara när lookup-villkoren höll (cache_kontext.behorig — samma fråga
    # som slogs upp ovan, alltså tom historik/inga bilagor/tomt
    # kundminne/ingen PII) OCH svaret inte eskalerade OCH kategorin är en av
    # de rena faktafrågorna (svarscache.CACHEBARA_KATEGORIER). En "on"-TRÄFF
    # når aldrig hit — den grenen returnerade redan högre upp — så det här
    # är bara miss/off/shadow-vägen.
    #
    # 2026-09-18: dessutom bara ett BESVARANDE svar som inte erbjuder en
    # människa. En motfråga eller en avgränsning bär ett samtalsläge (räknare,
    # erbjudande) som en cacheträff aldrig sätter — ett cachat "vill du prata
    # med en kollega?" hade gjort kundens "ja" till en ny fråga.
    if (
        settings.semantic_cache in ("on", "shadow")
        and cache_kontext.behorig
        and not escalated
        and not gastlage
        and svarslage == "besvara"
        and not erbjod_manniska
        and category in svarscache.CACHEBARA_KATEGORIER
        # Ett svar byggt på uppgifter ur kundens system (bd snipe-36u) gäller
        # EN kund: "din order skickades i går" får aldrig serveras till nästa
        # som frågar "var är min order?". Ett misslyckat anrop är lika
        # personligt — det säger något om just det här ärendet.
        and not underlag
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
    steglogg = trace.as_log()
    if underlag.logg or underlag.katalogfel:
        # Pseudo-steg, samma form som svarscachens: nyckeln "step" och inte
        # "skill", så att kvotbokföringen (chat.py) inte räknar det som ett
        # LLM-anrop. Bär VAD som anropades och hur det gick, aldrig svaren.
        steglogg.append(
            {
                "step": "integrationer",
                "anrop": underlag.logg,
                "rundor": underlag.rundor,
                "katalogfel": underlag.katalogfel,
            }
        )
    run = await storage.log_agent_run(
        tenant_id,
        agent_type="support",
        pack_version=pack,
        skills_used=trace.skills_used,
        input_text=message,
        output_text=reply,
        step_log=steglogg,
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
        # bd snipe-1fl: orsakskoden (support_regler.ORSAKER), svarsläget och
        # faktagrindens utfall. `overlamnad` = en människa äger samtalet nu,
        # chattfönstret börjar hämta medarbetarens svar.
        "escalation_code": orsak,
        # Gästläget: samtalet är fortfarande överlämnat även när den här
        # turen besvarades av agenten — chattfönstret ska fortsätta hämta
        # medarbetarens svar.
        "overlamnad": escalated or bool(gastlage),
        "svarslage": svarslage,
        "faktagrind": faktagrind,
        "sprak": svar_sprak,
        "kb_sources": [{"title": a["title"], "similarity": a["similarity"]} for a in articles],
        "returning_customer": len(history) > 0,
        "simulation": False,
        "skills_used": trace.skills_used,
        "step_log": steglogg,
        "cancellation_risk": cancellation_risk,
        "pack_version": pack,
        # bd snipe-36u: vilka av kundens system som frågades (utan svarsdata).
        "integrationer": underlag.logg,
    }
