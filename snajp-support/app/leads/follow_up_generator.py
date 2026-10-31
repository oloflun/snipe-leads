"""Uppföljningsgeneratorn — kedjan som var designad men aldrig inkopplad.

## Vad som inte fanns förrän 2026-08-26

`follow_up.py` har sedan Del H burit HELA uppföljningslogiken — spakordning,
breakup-mejl, sekvensnummer — och anropades enbart från tester (snipe-3dx).
Skickades ett första mejl hände sedan ingenting: ingen kodväg tittade på
tysta trådar, och "uppföljningar" fanns som datastruktur men inte som
beteende.

## Formen

Två halvor, medvetet isärhållna:

  * `trad_som_ar_forfallna` — REN policy, testbar utan databas och utan
    modell: vilka trådar är förfallna, givet aggregat som lagringen räknat.
  * `generate_due_follow_ups` — I/O och LLM: skriver utkast för de förfallna
    och köar dem genom SAMMA väg som första mejlet (`_queue_outreach_draft_impl`
    -> finalize, lagstadgad fot, språkgrind, autonomi). Autonominivån avgör
    status: `draft`/`first_contact` ger awaiting_review — en uppföljning går
    ALDRIG ut utan människa på de nivåerna (allowed_action, sequence > 0).

## Spakordningen (ponytail: fast ordning, se nedan)

Del H:s modell är "svagast spak först", ur mk:offers värdeekvation. Poängen
per spak persisteras dock ingenstans i dag (offers-tabellen är oanvänd av
kodvägarna), så v1 följer LEVERS kanoniska ordning och avslutar med breakup.
# ponytail: fast spakordning; byt till build_follow_up_sequence(offers.
# value_equation_scores) när offers-raderna faktiskt skrivs av researchflödet.

## Självbegränsningen

En genererad uppföljning ligger som osänt utkast/köpost i tråden, och
`has_pending_item` gör då tråden icke-förfallen — generatorn kan inte spamma
samma tråd hur ofta den än körs. Ett inkommet svar sätter `last_inbound_at`
(app/leads/svar.py) och tar tråden ur svepet permanent: svarade trådar ägs
av svarshanteringen, inte av sekvensen.

## Erbjudandet, ämnesraden och stilgrinden (Sebbe 2026-10-31)

Kedjan läste bara de tidigare mejlen, så uppföljningarna bar första mejlets
erbjudande ("svara 'pilot'", "era fem vanligaste kundfrågor") efter att
kunden bytt det, och ämnesraden med bolagets namn. Nu bär uppföljningen
kundens erbjudande för produkten (`erbjudanden.uppfoljningsblock`, villkoren
i faktagrindens underlag), ämnesraden ur kundens lista och samma stilgrind
som första mejlet, utom fynden som bara gäller ett första mejl.
`skriv_om_uppfoljning` skriver om leadets väntande uppföljning (Skapa om
utkast), och det gamla utkastet ställs in först när det nya är klart att köas.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any

from ..agent.leads_agent import sign_off
from ..agent.leads_context import OutreachContext
from ..agent.leads_research_v2 import las_produkter
from ..agent.leads_tools import _queue_outreach_draft_impl
from ..agent.step_runner import RunTrace, run_step
from ..agent.tools import strip_markdown
from ..agentcore.instruktioner import las_instruktioner
from ..agentcore.overlays import pack_version
from ..agentcore.packs import Playbook, PlaybookStep, RunLedger
from ..config import get_settings
from . import automation as automationsregler
from . import erbjudanden, sparad_research
from . import stilkontroll as stil
from .follow_up import LEVERS
from .gissnings_gate import check_gissningar
from .grounding_gate import build_permitted_facts, check_grounding
from .language_gate import last_humanizer_variant
from .signatur import dela_utkast, normalisera as normalisera_signatur
from .tilltal import amne_utan_namn, ett_bolagsnamn, fornamn, ratta_tilltal
from .vilande import namner_vilande_produkt
from .research_playbook import THINKING

logger = logging.getLogger("snajp-support.follow-up-generator")

_ROLL = "en svensk playbook för en lågmäld uppföljning i en pågående mejltråd"

#: Dagar sedan senast SKICKADE mejl innan nästa steg är förfallet, per
#: sekvensnummer (1 = första uppföljningen). Stigande avstånd: varje tyst
#: varv är ett svagare köpsignal, och tätare tryck läser som desperation.
FOLLOW_UP_DELAYS: dict[int, timedelta] = {
    1: timedelta(days=4),
    2: timedelta(days=6),
    3: timedelta(days=8),
    4: timedelta(days=10),
}

#: Max antal utgående per tråd: initialt + tre spak-uppföljningar + breakup.
MAX_OUTBOUND = len(LEVERS) + 1

#: Vinkeln per sekvensnummer. Texten går in i stegets task — modellen får
#: veta VAD uppföljningen ska trycka på, koden bestämmer VILKEN.
_VINKLAR: dict[int, str] = {
    1: (
        "Vinkel (dream_outcome): påminn kort om det utlovade utfallet — vad "
        "vardagen ser ut som när problemet är löst. Inget annat erbjudande än det "
        "under \"Erbjudandet i uppföljningen\"."
    ),
    2: (
        "Vinkel (perceived_likelihood): sänk tvivlet på att det fungerar — "
        "ett konkret, verifierbart skäl att tro på leveransen. Inga påhittade "
        "referenser eller siffror."
    ),
    3: (
        "Vinkel (time_delay): hur snabbt värdet kommer — vad som händer första "
        "veckan. Inga datumlöften som inte står i underlaget."
    ),
    4: (
        "Detta är ett BREAKUP-MEJL: sista kontakten. Kort, vänligt, inga "
        "förebråelser. Säg att du slutar höra av dig, lämna dörren öppen med "
        "ett enkelt sätt att återuppta kontakten."
    ),
}

FOLLOWUP_V1 = Playbook(
    name="leads/followup-v1",
    steps=(
        PlaybookStep(
            skill="sa:draft-outreach",
            requires=("context_pack",),
            # Komposition: hårdreglerna + uppföljningsformens egna (kort,
            # ingen förebråelse, tillför det NYA, breakup-reglerna).
            overlay=("leads-hard-rules", "leads-followup"),
            thinking=THINKING,
            temperature=0.5,
        ),
        PlaybookStep(
            skill="snajp:humanizer-svenska",
            requires=("skill:sa:draft-outreach",),
            overlay=("leads-hard-rules", "leads-followup"),
            thinking=THINKING,
            temperature=0.7,
        ),
    ),
)


#: Prospektstatusar som aldrig får en uppföljning: svarat, möte, vunnen,
#: ej intresserad och spärrad. Svaret flyttar statusen (app/leads/svar.py),
#: samtalsutfallen likaså (app/leads/samtal.py).
_AVSLUTADE = frozenset({"replied", "meeting", "won", "lost", "suppressed"})


def _tidpunkt(varde: Any) -> datetime | None:
    if isinstance(varde, datetime):
        return varde
    if isinstance(varde, str) and varde:
        try:
            return datetime.fromisoformat(varde)
        except ValueError:
            return None
    return None


def skickad_efter_spegling(thread: dict[str, Any], seedad: Any) -> bool:
    """Gick trådens FÖRSTA utskick efter speglingen? Utan spegel: alltid sant.
    Okänd tid åt det försiktiga hållet: falskt."""
    if not seedad:
        return True
    forst, grans = _tidpunkt(thread.get("first_outbound_sent_at")), _tidpunkt(seedad)
    if forst is None or grans is None:
        return False
    if forst.tzinfo is None:
        forst = forst.replace(tzinfo=grans.tzinfo)
    if grans.tzinfo is None:
        grans = grans.replace(tzinfo=forst.tzinfo)
    return forst > grans


def trad_som_ar_forfallna(
    threads: list[dict[str, Any]], *, now: datetime, automation: dict[str, Any] | None = None
) -> list[tuple[dict[str, Any], int]]:
    """Vilka trådar som är förfallna för nästa steg, och vilket steget är.

    Ren funktion över aggregaten från `storage.list_outreach_threads` —
    policyn ska gå att falsifiera i ett test utan databas.

    `automation` (app/leads/automation.py) styr väntan före FÖRSTA
    uppföljningen per lead-typ; 0 dagar = tråden får inga uppföljningar alls.
    Steg 2–4 följer FOLLOW_UP_DELAYS. None = standardreglerna.
    """
    regler = automationsregler.normalisera(automation)
    forfallna: list[tuple[dict[str, Any], int]] = []
    for thread in threads:
        if thread.get("arkiverad_at") or thread.get("prospect_status") in _AVSLUTADE:
            continue  # arkiverat, eller leadet har redan sagt sitt
        dagar = regler["per_typ"][automationsregler.typ_av(thread.get("origin"))]["uppfoljning_dagar"]
        if dagar == 0:
            continue  # kunden har stängt av uppföljningar för typen
        sent = int(thread.get("outbound_sent_count") or 0)
        if sent < 1 or sent >= MAX_OUTBOUND:
            continue  # inget initialt skickat än, eller sekvensen färdig
        if thread.get("last_inbound_at"):
            continue  # svarade trådar ägs av svarshanteringen
        if thread.get("has_pending_item"):
            continue  # nästa steg finns redan (utkast eller köpost)
        senast = thread.get("last_outbound_sent_at")
        if not senast:
            continue
        if isinstance(senast, str):
            senast = datetime.fromisoformat(senast)
        if senast.tzinfo is None:
            senast = senast.replace(tzinfo=now.tzinfo)
        vanta = timedelta(days=dagar) if sent == 1 else FOLLOW_UP_DELAYS[sent]
        if now - senast >= vanta:
            forfallna.append((thread, sent))
    return forfallna


async def generate_due_follow_ups(
    storage,
    tenant_id: str,
    *,
    now: datetime,
    tenant_name: str,
    context_pack: str,
    forst_skickad_efter: Any = None,
) -> list[dict[str, Any]]:
    """Skriver och köar uppföljningsutkast för tenantens förfallna trådar.

    Returnerar en rad per behandlad tråd. Ett trasigt utkast fäller inte de
    andra trådarna — samma princip som batchkörningen.

    `forst_skickad_efter` (spegelns seeded_at): bara trådar vars första
    utskick gick efter den tidpunkten följs upp. Se scheduler.sweep_follow_ups.
    """
    # Ett lead vars utkast skrivs om just nu (skriv_om_uppfoljning) hoppas
    # över: jobbet ställer in den gamla uppföljningen strax innan det köar den
    # nya, och svepet hade hunnit skriva en andra i samma tråd däremellan.
    skrivs = {
        pid for pid, jobb in (await storage.utkastjobb_lage(tenant_id)).items()
        if jobb.get("status") in ("queued", "processing")
    }
    threads = [
        t for t in await storage.list_outreach_threads(tenant_id)
        if skickad_efter_spegling(t, forst_skickad_efter) and str(t.get("prospect_id")) not in skrivs
    ]
    settings = await storage.get_agent_settings(tenant_id, agent_type="leads")
    forfallna = trad_som_ar_forfallna(threads, now=now, automation=settings.get("automation"))
    if not forfallna:
        return []

    lager = await las_instruktioner(storage, tenant_id, agent_type="leads", tenant_namn=tenant_name)
    resultat: list[dict[str, Any]] = []
    for thread, sekvens in forfallna:
        try:
            resultat.append(
                await _en_uppfoljning(
                    storage,
                    tenant_id,
                    thread=thread,
                    sekvens=sekvens,
                    tenant_name=tenant_name,
                    context_pack=context_pack,
                    lager=lager,
                )
            )
        except Exception as error:  # noqa: BLE001 — en tråd fäller inte svepet
            logger.exception("Uppföljning för tråd %s misslyckades.", thread.get("id"))
            resultat.append({"thread_id": thread.get("id"), "queued": False, "fel": str(error)})
    return resultat


async def uppfoljningstrad(storage, tenant_id: str, prospect_id: str) -> dict[str, Any] | None:
    """Leadets tråd i svepets form (`storage.list_outreach_threads`), eller
    None om leadet inte har fått något mejl: då är nästa utkast ett första
    mejl, inte en uppföljning."""
    trad = await storage.find_outreach_thread(tenant_id, prospect_id=prospect_id)
    if not trad:
        return None
    meddelanden = await storage.list_outreach_messages(tenant_id, str(trad["id"]))
    skickade = [m for m in meddelanden if m.get("direction") == "outbound" and m.get("sent_at")]
    if not skickade:
        return None
    prospekt = await storage.get_prospect(tenant_id, prospect_id) or {}
    svar = next((m.get("created_at") or True for m in meddelanden if m.get("direction") == "inbound"), None)
    return {
        **trad,
        "prospect_id": prospect_id,
        "company_name": prospekt.get("company_name"),
        "contact_email": prospekt.get("contact_email"),
        "origin": prospekt.get("origin"),
        "prospect_status": prospekt.get("status"),
        "arkiverad_at": prospekt.get("arkiverad_at") or trad.get("arkiverad_at"),
        "outbound_sent_count": len(skickade),
        "last_inbound_at": trad.get("last_inbound_at") or svar,
    }


async def skriv_om_uppfoljning(
    storage, tenant_id: str, thread: dict[str, Any], *, tenant_name: str, context_pack: str
) -> dict[str, Any]:
    """Skriver om leadets väntande uppföljning (Skapa om utkast, Sebbe
    2026-10-31). Det gamla utkastet ställs in först när det nya passerat
    grindarna, så ett stoppat nytt utkast lämnar det gamla kvar.

    `thread` är `uppfoljningstrad`. Ett svarat, avslutat eller arkiverat lead,
    och en tråd vars sekvens är slut, får ingen ny uppföljning."""
    sekvens = int(thread.get("outbound_sent_count") or 0)
    if thread.get("last_inbound_at") or thread.get("prospect_status") in _AVSLUTADE or thread.get("arkiverad_at"):
        return {"thread_id": str(thread["id"]), "sekvens": sekvens, "queued": False, "hoppad": "avslutad"}
    if not 1 <= sekvens < MAX_OUTBOUND:
        return {"thread_id": str(thread["id"]), "sekvens": sekvens, "queued": False, "hoppad": "sekvensen_klar"}
    lager = await las_instruktioner(storage, tenant_id, agent_type="leads", tenant_namn=tenant_name)
    return await _en_uppfoljning(
        storage,
        tenant_id,
        thread=thread,
        sekvens=sekvens,
        tenant_name=tenant_name,
        context_pack=context_pack,
        lager=lager,
        ersatt=True,
    )


#: Stilfynd som inte prövas i en uppföljning: villkoren dikterar
#: erbjudandets mening och handlingen (som i första mejlet), och
#: `agent_efter_loftet` letar efter produkten efter första mejlets ingång,
#: medan en uppföljning namnger den i första stycket (fem falska av sex i
#: provet i development 2026-10-31).
_EJ_I_UPPFOLJNING = frozenset({"lang_mening", "samma_uppmaning", "agent_efter_loftet"})

#: "Hon" först i en mening (stilkontroll: iris_hon).
_HON_FORST = re.compile(r"((?:^|[.!?]\s+))Hon\b", re.MULTILINE)


def _stilfynd(
    utkast: dict[str, Any],
    *,
    villkor: str | None,
    produkt: str | None,
    bolag: str,
    amne_i_kod: bool,
    andra: list[str],
) -> list[str]:
    """Stilgrindens fynd på en uppföljning, som text till omskrivningen.
    Samma markörer som första mejlet (app/leads/stilkontroll.py), erbjudandet
    intakt och inte byggd som de andra utkasten i kön (alla sex i provet
    började "Om ni hann se mitt förra mejl"); ämnesraden prövas bara när
    modellens rad står kvar."""
    body = str(utkast.get("body") or "")
    if not body.strip():
        return []
    fynd = (
        stil.kontrollera(body).anmarkningar
        + stil.erbjudande_fynd(body, villkor=villkor, produkt=produkt)
        + stil.mot_andra(body, andra)
    )
    if not amne_i_kod:
        fynd += stil.amne_fynd(str(utkast.get("subject") or ""), bolag=bolag, produkt=produkt)
    return [a.beskrivning for a in fynd if a.kod not in _EJ_I_UPPFOLJNING]


async def _en_uppfoljning(
    storage,
    tenant_id: str,
    *,
    thread: dict[str, Any],
    sekvens: int,
    tenant_name: str,
    context_pack: str,
    lager,
    ersatt: bool = False,
) -> dict[str, Any]:
    started = time.monotonic()
    settings = get_settings()
    thread_id = str(thread["id"])
    company_name = thread.get("company_name") or "prospektet"
    prospect_email = thread.get("prospect_email") or thread.get("contact_email") or ""

    meddelanden = await storage.list_outreach_messages(tenant_id, thread_id)
    # En tråd som sålde en vilande produkt (Kvittohanteraren sedan 2026-10-17,
    # app/leads/vilande.py) följs inte upp: uppföljningen hade sålt samma
    # produkt igen. Före modellanropen, så att svepet inte betalar för den.
    if any(
        m.get("direction") == "outbound"
        and namner_vilande_produkt(f"{m.get('subject') or ''}\n{m.get('body') or ''}")
        for m in meddelanden
    ):
        return {"thread_id": thread_id, "sekvens": sekvens, "queued": False, "hoppad": "vilande_produkt"}
    historik = "\n\n".join(
        f"{'Prospektet' if m['direction'] == 'inbound' else 'Vi'}: {(m.get('body') or '').strip()}"
        for m in meddelanden[-4:]
        if (m.get("body") or "").strip()
    )

    # Kundens erbjudande för trådens produkt: den researchen valde, annars den
    # de skickade mejlen nämner först (signaturen bortskalad, den nämner
    # kundens alla agenter).
    installningar = await storage.get_agent_settings(tenant_id, agent_type="leads")
    sig = normalisera_signatur(installningar.get("signatur"))
    skickat = "\n\n".join(
        f"{m.get('subject') or ''}\n{dela_utkast(m.get('body') or '', sig)[0]}"
        for m in meddelanden
        if m.get("direction") == "outbound" and m.get("sent_at")
    )
    prospect_id = str(thread.get("prospect_id") or "")
    prospekt = (await storage.get_prospect(tenant_id, prospect_id) or {}) if prospect_id else {}
    sparad = (await sparad_research.las(storage, tenant_id, prospect_id) or {}) if prospect_id else {}
    ur_research = sparad.get("produkt")
    vald = erbjudanden.produkt_nu(
        str((ur_research.get("namn") if isinstance(ur_research, dict) else ur_research) or "") or None,
        skickat,
        las_produkter(installningar),
    )
    produktnamn = vald["namn"] if vald else None
    erbjudande = await erbjudanden.for_trad(storage, tenant_id, thread, produktnamn)
    villkor = erbjudande.villkor if erbjudande else None
    amne_i_kod = bool(erbjudande and erbjudande.amnen)
    produkttext = f"{vald['namn']}: {vald['nytta']}" if vald else ""

    # Tilltalet som i första mejlet (leads_research_v2): kontaktens förnamn ger
    # du-form rakt igenom, annars "Hej," och ni-form.
    mottagare = prospekt.get("contact_name")
    namn = fornamn(mottagare, prospect_email) if mottagare else ""
    tilltalsblock = (
        f"## Tilltal i det här mejlet\nMottagaren är {namn}. Hälsa \"Hej {namn},\" och skriv i du-form "
        "rakt igenom, även villkoren och handlingen.\n\n"
        if namn
        else "## Tilltal i det här mejlet\nIngen namngiven mottagare. Hälsa \"Hej,\" och skriv i ni-form "
        "rakt igenom.\n\n"
    )

    base = (
        f"## Uppdrag\nDu skriver uppföljning nr {sekvens} till {company_name} åt {tenant_name}. "
        f"Prospektet har inte svarat på tidigare mejl.\n\n"
        f"{tilltalsblock}"
        + (
            f"## Produkten\n{produkttext}\nMejlet handlar bara om den här produkten, med just det namnet; "
            "nämn ingen annan av kundens produkter.\n\n"
            if produkttext else ""
        )
        + (f"{erbjudanden.uppfoljningsblock(villkor)}\n\n" if erbjudande else "")
        + (f"## Om bolaget\n{prospekt['lagesbeskrivning']}\n\n" if prospekt.get("lagesbeskrivning") else "")
        + f"{context_pack}\n\n"
        f"## Tidigare mejl i tråden (skriv INTE om dem, upprepa inte innehållet)\n{historik}\n\n"
        f"## {_VINKLAR[sekvens]}"
    )

    ledger = RunLedger(satisfied={"context_pack"})
    trace = RunTrace()
    steps = FOLLOWUP_V1.steps
    uppgift = (
        "Skriv uppföljningsmejlet enligt vinkeln ovan. KORT: högst 90 ord i brödtexten, "
        "kortare än det första mejlet; vinkeln och produkten i högst två meningar före "
        "erbjudandet. En hänvisning till att du hört av dig förut är "
        "valfri och i så fall en kort bisats med egna ord, aldrig förebrående; börja "
        "gärna direkt i vinkeln. Påstå ingenting som inte står i underlaget, och gissa "
        "aldrig hur deras vardag ser ut (ingen arbetsbelastning, inget \"fullt upp\"). Ämnesraden är två till "
        "fem ord, utan bolagets namn och utan produkten. Skriv ingen hälsningsfras sist: "
        "signaturen läggs på automatiskt. "
        "Returnera JSON: subject (svenska, ren text), body (svenska, ren text)."
    )

    draft = await run_step(
        steps[0],
        ledger,
        trace,
        task=uppgift,
        case_context=base,
        playbook_role=_ROLL,
        instruktioner=lager,
    )

    async def skriv_om(utkast: dict[str, Any], fynd: list[str]) -> dict[str, Any]:
        return await run_step(
            steps[0],
            ledger,
            trace,
            task=uppgift
            + "\n\nDITT FÖRRA UTKAST FÄLLDES AV STILGRINDEN. Skriv om uppföljningen så att varje "
            "punkt nedan är åtgärdad; erbjudandets villkor och produktens namn står kvar i sak.\n\n"
            "## Fynd att åtgärda\n"
            + "\n".join(f"- {f}" for f in fynd)
            + f"\n\n## Förra utkastet\nÄmne: {utkast.get('subject', '')}\n\n{utkast.get('body', '')}",
            case_context=base,
            playbook_role=_ROLL,
            instruktioner=lager,
        )

    async def humanisera(utkast: dict[str, Any]) -> dict[str, Any]:
        return await run_step(
            steps[1],
            ledger,
            trace,
            task=(
                "Gör texten till naturlig svenska enligt skillen. Behåll all "
                "sakinformation, erbjudandet och dess siffror, lägg inte till nya påståenden. "
                "Returnera JSON: final_subject (svenska), final_body (svenska, ren text)."
            ),
            case_context=(
                f"{base}\n\n## Text att humanisera\n"
                f"Ämne: {utkast.get('subject', '')}\n\n{utkast.get('body', '')}"
            ),
            playbook_role=_ROLL,
            instruktioner=lager,
        )

    def version(h: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
        return {"subject": h.get("final_subject") or d.get("subject"), "body": h.get("final_body") or d.get("body")}

    andra = [
        str(r.get("body") or "") for r in await storage.list_review_queue(tenant_id, limit=200)
        if r.get("thread_id") != thread_id
    ]

    def fynd_i(utkast: dict[str, Any]) -> list[str]:
        return _stilfynd(utkast, villkor=villkor, produkt=produktnamn, bolag=company_name,
                         amne_i_kod=amne_i_kod, andra=andra)

    # Stilgrinden som i första mejlet (run_outreach_draft_v2): en omskrivning
    # före humanizern, sedan högst två varv efter den, och den humaniserade
    # versionen med minst fynd köas (vid lika den senaste).
    fynd = fynd_i(draft)
    if fynd:
        draft = await skriv_om(draft, fynd)
    slutligt = version(await humanisera(draft), draft)
    kvar = fynd_i(slutligt)
    basta, basta_fynd = slutligt, kvar
    for _varv in range(2):
        if not kvar:
            break
        draft = await skriv_om(slutligt, kvar)
        slutligt = version(await humanisera(draft), draft)
        kvar = fynd_i(slutligt)
        if len(kvar) <= len(basta_fynd):
            basta, basta_fynd = slutligt, kvar

    subject = strip_markdown(basta.get("subject") or "").strip()
    body = sign_off(strip_markdown(basta.get("body") or "").strip(), tenant_name)
    body = ratta_tilltal(body, mottagare, prospect_email)
    subject, body = ett_bolagsnamn(amne_utan_namn(subject, company_name), body, company_name)
    if stil.produktslag(produktnamn):
        # Snajps agenter är aldrig "hon" (Snajps instruktion): humanizern förde
        # in det efter grinden i två av tolv i provet 2026-10-31, och i tre av
        # 382 i omskrivningen samma dag, två av dem om Supportagenten. Sista
        # nätet i kod, samma igenkänning som fyndet iris_hon.
        body = _HON_FORST.sub(lambda m: f"{m.group(1)}Den", body)

    # INV-GROUND-001 gäller uppföljningar precis som första mejlet. Villkorens
    # siffror är kundens egna och får stå i mejlet, liksom lägesbeskrivningen
    # och researchens belägg om bolaget.
    facts = build_permitted_facts(
        context_pack=context_pack,
        research_evidence=tuple(sparad.get("research_evidence") or ()),
        offer_summary=f"{produkttext}\n{villkor}" if erbjudande else produkttext,
        brief=str(prospekt.get("lagesbeskrivning") or ""),
        tenant_name=tenant_name,
        company_name=company_name,
    )
    verdict = check_grounding(f"{subject}\n\n{body}", facts)
    gissningar = check_gissningar(f"{subject}\n\n{body}")
    eskalerade = [s.skill for s in trace.steps if s.escalated]
    if erbjudande:
        # Efter faktagrinden, som i första mejlet: ämnesraden är kundens egen
        # text ("Support 24/7 för dina kunder" fälldes på 24 och 7). En rad ur
        # listan som tråden inte redan burit, i mejlets tilltal; och villkorens
        # "upp till" står kvar.
        anvanda = {str(m.get("subject") or "").strip().casefold() for m in meddelanden}
        rader = [r for r in erbjudande.amnen if r.casefold() not in anvanda and erbjudanden.till_ni(r).casefold() not in anvanda]
        subject = erbjudanden.valj_amne(
            rader, f"{tenant_id}:{prospect_id or thread_id}:uppf{sekvens}", du=stil.namngiven(body)
        ) or subject
        body = erbjudanden.behall_upp_till(body, erbjudande.villkor)

    utfall: dict[str, Any] = {
        "thread_id": thread_id,
        "sekvens": sekvens,
        "queued": False,
        "subject": subject,
        "produkt": produktnamn,
        "erbjudande": erbjudande.nyckel if erbjudande else None,
    }

    if not body or not verdict.ok or gissningar or eskalerade:
        utfall["stoppad"] = {
            "tom": not body,
            "grounding": verdict.as_report(),
            "gissningar": list(gissningar),
            "eskalerade_steg": eskalerade,
        }
    else:
        if ersatt:
            # Den gamla uppföljningen ställs in först nu, när den nya ska köas.
            await storage.cancel_pending_sends(tenant_id, thread_id)
        # sequence_index avgör autonomifrågan: uppföljningar (index > 0)
        # kräver `meeting`-nivå för att gå utan granskning (allowed_action).
        context = OutreachContext(
            storage=storage,
            tenant_id=tenant_id,
            thread_id=thread_id,
            prospect_email=prospect_email,
            sequence_index=int(thread.get("outbound_sent_count") or sekvens),
        )
        svar = json.loads(
            await _queue_outreach_draft_impl(
                context,
                subject=subject or f"Uppföljning — {company_name}",
                body=body,
                language_state=str(thread.get("language_state") or "sv"),
                humanizer_variant=last_humanizer_variant(trace.skills_used),
                # Antons regel 2026-10-07: en uppföljning är alltid ett
                # utkast som kräver godkännande, aldrig ett autonomt utskick,
                # oavsett autonominivå.
                force_review=True,
                # Kvarvarande stilfynd syns för granskaren som "Stil: …".
                stilkontroll=True,
            )
        )
        utfall["queued"] = bool(svar.get("queued"))
        utfall["status"] = "awaiting_review" if svar.get("awaiting_review") else "queued"
        utfall["queue_item_id"] = svar.get("queue_item_id")

    await storage.log_agent_run(
        tenant_id,
        agent_type="leads_followup",
        pack_version=pack_version(FOLLOWUP_V1.name, lager.hash),
        skills_used=trace.skills_used,
        input_text=f"uppföljning {sekvens} till {company_name}",
        output_text=f"{subject}\n\n{body}",
        step_log=trace.as_log(),
        prompt_lager=trace.lagertexter(),
        tokens_in=trace.total_tokens_in,
        tokens_out=trace.total_tokens_out,
        latency_ms=int((time.monotonic() - started) * 1000),
        model=f"{settings.llm_provider}:{settings.model}",
    )
    return utfall
