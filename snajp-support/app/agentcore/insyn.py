"""Insyn (plan 2026-10-06, Fas 7): allt agenten läser, visat som flöde.

## Varför modulen finns

Spårvyn kapade varje fält vid 8 000 tecken, så overlay, kundlager och
kontrakt i utkaststeget syntes aldrig, och anropen utanför stegmotorn
(bolagssökningen, profilkompileringen, Jev, webbrevisionen) lämnade inget spår
alls. De påhittade bolagen 2026-10-05 kom ur ett sådant anrop. Admin ska kunna
se ALLT underlag en agent läser och var i kedjan något brister.

## Regeln: visningen är sann

Allt här byggs ur samma objekt och funktioner som bygger prompten:
`Playbook`-objekten (banor, steg, skopor, motiveringar, radändringar,
overlays, villkor), `step_runner.bygg_systemprompt` (systemlagren),
`PlaybookStep.lasta_delar` (skillfilerna) och de lagrade körningarna
(användarmeddelandet som det faktiskt skickades). Ingenting är en parallell
beskrivning av prompten — skrivs en sådan blir den förr eller senare fel utan
att någon märker det. Kodgrindarna är kod och inte playbooksteg; de pekas ut
med den riktiga funktionen (modul + namn), så en omdöpt grind fäller testet.

## Två delar

1. Insamlingen av anrop utanför stegmotorn (`logga_anrop`, `samla_anrop`).
   Ligger först och importerar ingenting tungt: leadsmodulerna anropar den.
2. Läsmodellen för adminytan (`oversikt`, `kedja`, `skillfil`, `kb_prov`).
   Läser bara; skriver aldrig (app/api/admin.py är läsrouter).
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any

logger = logging.getLogger("snajp-support.insyn")

# ---------------------------------------------------------------------------
# 1. Anrop utanför stegmotorn
# ---------------------------------------------------------------------------

#: Den pågående insamlingen. En lista delas med uppgifter som startas inuti
#: (asyncio kopierar kontexten, listan är samma objekt), så parallella
#: anrop i en gather hamnar i samma post.
_ANROP: ContextVar[list[dict[str, Any]] | None] = ContextVar("insyn_anrop", default=None)

#: Svaret i spåret. Ett grounded sökresultat eller ett Jev-svar är några kB;
#: taket finns för att en trasig leverantör som svarar med en hel sida inte
#: ska bli en rad på en megabyte.
SVAR_TAK = 60_000


def logga_anrop(
    anrop: str,
    *,
    prompt: str,
    svar: str,
    modell: str = "",
    kallor: list[str] | None = None,
    latens_ms: int = 0,
    utfall: dict[str, Any] | None = None,
) -> None:
    """Bokför ETT anrop utanför stegmotorn i den pågående insamlingen.

    Gör ingenting när ingen insamling pågår (tester, skript): loggningen är
    bokföring och får aldrig ändra vad anropet gör. Posten har nyckeln
    "step" och inte "skill", samma form som svarscachens och integrationernas
    pseudo-steg — kvotbokföringen räknar bara "skill" som ett LLM-steg."""
    poster = _ANROP.get()
    if poster is None:
        return
    poster.append(
        {
            "step": f"anrop:{anrop}",
            "anrop": anrop,
            "model": modell,
            "latency_ms": latens_ms,
            "user_message": prompt,
            "raw_output": (svar or "")[:SVAR_TAK],
            "kallor": list(kallor or []),
            **({"utfall": utfall} if utfall else {}),
        }
    )


class Tidtagare:
    """`with Tidtagare() as t: ...; t.ms` — latensen till logga_anrop."""

    def __enter__(self) -> "Tidtagare":
        self._start = time.monotonic()
        self.ms = 0
        return self

    def __exit__(self, *_: object) -> None:
        self.ms = int((time.monotonic() - self._start) * 1000)


@asynccontextmanager
async def samla_anrop(
    storage=None,
    tenant_id: str | None = None,
    *,
    prospect_id: str | None = None,
    is_test: bool = False,
    input_text: str = "",
):
    """Samlar anropen inom blocket.

    Med `storage` skrivs de som EN agent_runs-post av typen 'leads_underlag'
    när blocket lämnas (bolagssökningen med Jev-triagen, profilkompileringen).
    Utan `storage` får anroparen listan och lägger själv in posterna i sin
    egen körnings step_log (researchen: Jev-klassningen och webbrevisionen
    hör till bolagets researchkörning, inte till en egen rad).

    Ett fel i skrivningen fäller aldrig anroparen — sökningen är jobbet,
    spåret är bokföring."""
    poster: list[dict[str, Any]] = []
    token = _ANROP.set(poster)
    try:
        yield poster
    finally:
        _ANROP.reset(token)
        if storage is not None and tenant_id and poster:
            try:
                await storage.log_agent_run(
                    tenant_id,
                    agent_type="leads_underlag",
                    pack_version="leads/underlag",
                    skills_used=[],
                    input_text=input_text,
                    output_text=", ".join(p["anrop"] for p in poster),
                    step_log=poster,
                    tokens_in=0,
                    tokens_out=0,
                    latency_ms=sum(int(p.get("latency_ms") or 0) for p in poster),
                    is_test=is_test,
                    prospect_id=prospect_id,
                )
            except Exception:  # noqa: BLE001 — se docstringen
                logger.exception("Kunde inte logga underlagsanropen.")


# ---------------------------------------------------------------------------
# 2. Läsmodellen
# ---------------------------------------------------------------------------

#: Villkoren i playbookerna i klartext. Nyckeln är `PlaybookStep.condition`
#: ordagrant; ett villkor som saknas här visas med sin nyckel (aldrig
#: tyst). Texten beskriver vad koden i support_agent.py avgör.
VILLKOR = {
    "kb_gap_or_safety_or_human_request": {
        "sv": "Körs bara vid kunskapslucka, säkerhetssignal eller när kunden ber om en människa.",
        "en": "Runs only on a knowledge gap, a safety signal or when the customer asks for a person.",
    },
    "kb_gap_or_escalation": {
        "sv": "Körs bara när kunskapsbasen saknade svaret eller ärendet eskalerades.",
        "en": "Runs only when the knowledge base lacked the answer or the ticket escalated.",
    },
    "cancellation_risk": {
        "sv": "Körs bara vid uppsägningsrisk.",
        "en": "Runs only on cancellation risk.",
    },
}

#: Förvillkor som inte är ett skillsteg utan ett underlag (requires=…).
KRAV_UNDERLAG = {"context_pack": "affarskontext"}

_REDIGERA_INSTRUKTIONER = "/admin/installningar/agentinstruktioner"


def _bana(id_: str, playbook, roll: str, agent_type: str, grundprompt: str, villkor: str = "") -> dict:
    return {
        "id": id_,
        "playbook": playbook,
        "roll": roll,
        "agent_type": agent_type,
        "grundprompt": grundprompt,
        "villkor": villkor,
    }


def _grind(id_: str, funktion) -> dict[str, Any]:
    """En kodgrind som nod. `funktion` är den riktiga funktionen: namnet
    läses ur den, inte ur en sträng som kan sluta stämma."""
    return {
        "typ": "grind",
        "id": f"grind:{id_}",
        "grind": id_,
        "kod": f"{funktion.__module__}.{funktion.__qualname__}",
    }


def banor(agent: str) -> tuple[str, list[dict[str, Any]]]:
    """(kedjeversion, banor) för agenten, ur playbook-objekten i koden.

    Varje bana är en playbook med sina steg i körordning. Iris huvudbana
    flätar in kodgrindarna mellan research- och utkastplaybookerna i den
    ordning api/leads.py och leads_research_v2.py kör dem."""
    from ..agent import leads_agent, leads_tools
    from ..config import get_settings

    if agent == "support":
        from ..agent import support_faktagrind
        from ..agent.support_playbook import SUPPORT_V1
        from ..moderation.abuse_gate import check_abuse

        support = _bana("support", SUPPORT_V1, "en svensk kundtjänst-playbook", "support", "support")
        return "support/v1", [
            {
                "id": "support",
                "noder": [_grind("pahopp", check_abuse), *_steg(support), _grind("faktagrind", support_faktagrind.kontrollera)],
            }
        ]

    from ..leads import bedomning, discovery, existens, forfilter, jev
    from ..leads.follow_up_generator import _ROLL as UPPFOLJNING_ROLL
    from ..leads.follow_up_generator import FOLLOWUP_V1
    from ..leads.grounding_gate import check_grounding
    from ..leads.grounding_playbook import GROUNDING_V1
    from ..leads.outreach_playbook import OUTREACH_V1, OUTREACH_V2
    from ..leads.research_playbook import RESEARCH_V1, RESEARCH_V2
    from ..leads.svar import _ROLL as SVAR_ROLL
    from ..leads.svar import REPLY_V1

    # Samma grenval som api/leads.py:_pipeline_fns.
    v2 = get_settings().leads_pipeline == "v2"
    research = _bana(
        "research", RESEARCH_V2 if v2 else RESEARCH_V1, leads_agent._RESEARCH_ROLE, "leads_research",
        "research" if v2 else "",
    )
    utkast = _bana(
        "utkast", OUTREACH_V2 if v2 else OUTREACH_V1, leads_agent._OUTREACH_ROLE, "leads_outreach",
        "utkast" if v2 else "",
    )
    grundning = _bana(
        "grundning", GROUNDING_V1, leads_agent._GROUNDING_ROLE, "leads_outreach", "utkast" if v2 else "",
        villkor="faktagrind",
    )
    svar = _bana("svar", REPLY_V1, SVAR_ROLL, "leads_svar", "")
    uppfoljning = _bana("uppfoljning", FOLLOWUP_V1, UPPFOLJNING_ROLL, "leads_followup", "")
    return ("v2" if v2 else "v1"), [
        {
            "id": "iris",
            "noder": [
                _grind("kalla", discovery.hitta_bolag),
                _grind("forfilter", forfilter.forfiltrera),
                _grind("existens", existens.styrk),
                _grind("jev", jev.triage),
                *_steg(research),
                _grind("bedomning", bedomning.bedom),
                _grind("kontakt", leads_agent._uppgradera_kontakt),
                *_steg(utkast),
                _grind("faktagrind", check_grounding),
                _grind("ko", leads_tools._queue_outreach_draft_impl),
            ],
        },
        {"id": "grundning", "villkor": "faktagrind", "noder": _steg(grundning)},
        {"id": "svar", "noder": _steg(svar)},
        {"id": "uppfoljning", "noder": _steg(uppfoljning)},
    ]


def _steg(bana: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"typ": "steg", "id": f"{bana['id']}:{i}", "bana": bana, "step": step, "index": i}
        for i, step in enumerate(bana["playbook"].steps)
    ]


async def _lager_for_agent(storage, tenant_id: str, agent: str, kanal: str):
    """(Instruktionslager som anroparna läser det, tenantnamn, supportinställningar)."""
    from .instruktioner import las_instruktioner

    tenant = await storage.get_tenant(tenant_id) or {}
    namn = tenant.get("name") or ""
    lager = await las_instruktioner(
        storage, tenant_id, agent_type="support" if agent == "support" else "leads", tenant_namn=namn
    )
    installningar = None
    if agent == "support":
        from ..agent import support_regler

        installningar = support_regler.normalisera(
            await storage.get_agent_settings(tenant_id, agent_type="support")
        )
    return lager, namn, installningar


def _lager_for_steg(lager, nod: dict[str, Any], namn: str, kanal: str, installningar):
    """Instruktionslagret just det här steget får — samma rendering som
    anroparen gör (leads_research_v2 / support_agent)."""
    from dataclasses import replace

    grund = nod["bana"]["grundprompt"]
    if grund in ("research", "utkast"):
        from ..agent import leads_systemprompt

        return replace(
            lager, agent_md=leads_systemprompt.rendera(foretagsnamn=namn, steg=grund, mall=lager.agent_mall or None)
        )
    if grund == "support":
        from ..agent import support_systemprompt
        from ..agent.support_agent import HELA_GRUNDPROMPTEN

        return replace(
            lager,
            agent_md=support_systemprompt.rendera(
                foretagsnamn=namn, kanal=kanal, installningar=installningar,
                mall=lager.agent_mall or None, karna=nod["step"].skill not in HELA_GRUNDPROMPTEN,
            ),
        )
    return lager


#: Vem som får ändra ett systemlager, och var.
def _vem(etikett: str, tenant_id: str) -> tuple[str, str | None]:
    return {
        "gemensamt": ("admin", _REDIGERA_INSTRUKTIONER),
        "agent": ("admin", _REDIGERA_INSTRUKTIONER),
        "kund": ("admin", f"/admin/kunder/{tenant_id}"),
        "skill": ("ingen (vendorad, INV-SKILL-005)", None),
        "overlay": ("utvecklare (agent-core/overlays)", None),
        "kontrakt": ("utvecklare (kod)", None),
    }.get(etikett, ("kunden", f"/admin/kunder/{tenant_id}"))


def _stegnod(nod: dict[str, Any], lager, tenant_id: str, texter: dict[str, str]) -> dict[str, Any]:
    from ..agent.step_runner import STANDARD_TEMPERATUR, bygg_systemprompt
    from ..config import get_settings

    settings = get_settings()
    step = nod["step"]
    segment = bygg_systemprompt(step, lager, nod["bana"]["roll"])
    poster = []
    for seg in segment:
        texter[seg.hash] = seg.text
        vem, redigera = _vem(seg.etikett, tenant_id)
        poster.append({**seg.som_post(), "vem": vem, "redigera": redigera})
    modell = settings.model
    if step.model_setting:
        modell = getattr(settings, step.model_setting, "") or settings.model
    try:
        delar = step.lasta_delar()
    except Exception as fel:  # noqa: BLE001 — visa felet i stället för att fälla vyn
        delar = [{"skill": step.skill, "fel": f"{type(fel).__name__}: {fel}"}]
    return {
        "typ": "steg",
        "id": nod["id"],
        "bana": nod["bana"]["id"],
        # Vilken agent_runs-typ stegets körningar loggas som — körningsväljaren
        # färgar kartan med den.
        "agent_type": nod["bana"]["agent_type"],
        "playbook": nod["bana"]["playbook"].name,
        "skill": step.skill,
        "laddning": "skopa" if step.scope else "hel",
        "skopa": list(step.scope),
        "motivering": step.rationale,
        "extra_skills": [{"skill": n, "skopa": list(s)} for n, s in step.extra_skills],
        "radandringar": [{"gammal": g, "ny": n, "skal": s} for g, n, s in step.radandringar],
        "overlays": list(step.overlay_names),
        "kraver": list(step.requires),
        "villkor": step.condition or (nod["bana"]["villkor"] or None),
        "villkor_text": VILLKOR.get(step.condition or ""),
        "modell": modell,
        "modell_falt": step.model_setting,
        "temperatur": step.temperature if step.temperature is not None else STANDARD_TEMPERATUR,
        "thinking": step.thinking or settings.thinking_mode,
        "lager": poster,
        "skilldelar": delar,
        "anvandare": None,
    }


async def _senaste_steg(storage, tenant_id: str, agent_type: str, limit: int = 15) -> list[dict[str, Any]]:
    """Stegposterna ur de senaste körningarna av en typ, nyast först."""
    ut: list[dict[str, Any]] = []
    for run in await storage.list_agent_runs_all(tenant_id=tenant_id, agent_type=agent_type, limit=limit):
        logg = run.get("step_log") or []
        if isinstance(logg, str):
            try:
                logg = json.loads(logg)
            except ValueError:
                logg = []
        for post in logg:
            if isinstance(post, dict) and post.get("skill") and post.get("user_message"):
                ut.append({**post, "_run_id": str(run.get("id")), "_created_at": str(run.get("created_at") or "")})
    return ut


def _anvandarlager(post: dict[str, Any]) -> list[dict[str, Any]]:
    from ..agent.step_runner import dela_anvandarmeddelande

    return [
        {**seg.som_post(), "text": seg.text}
        for seg in dela_anvandarmeddelande(str(post.get("user_message") or ""))
    ]


#: Underlagen per agent: (id, position, markörer, källa, vem). Markörerna är
#: rubrikerna anroparna sätter i användarmeddelandet (eller systemlagrets
#: etikett) — matchningen läser alltså det som faktiskt skickades.
_UNDERLAG = {
    "leads": [
        ("gemensamt", "system", ("gemensamt",), "agent_global_instructions / agent-core/AGENTS.md", "admin"),
        ("agentdokument", "system", ("agent",), "agent_global_instructions (leads) / agent-core/prompts/leads-systemprompt.md", "admin"),
        ("kundinstruktion", "system", ("kund",), "agent_configs.instructions_md", "admin"),
        ("affarskontext", "user", ("Kontextpaket: .agents/product-marketing.md",), "agent_context_docs (product_marketing)", "kunden"),
        ("kundresearch", "user", ("Kontextpaket: kundresearch",), "agent_context_docs (customer_research)", "onboarding"),
        ("malgrupp", "user", ("MÅLGRUPP (ICP)",), "agent_configs.settings.icp", "kunden"),
        ("produkter", "user", ("Kundens produkter",), "agent_configs.settings.produkter", "kunden"),
        ("profil", "user", ("IRIS-PROFIL",), "agent_configs.settings.profil", "kompileras ur affärskontext och målgrupp"),
        ("rost", "user", ("Kundens röstdokument",), "agent_context_docs (soul)", "kunden"),
        ("onskemal", "user", ("Kundens egna önskemål",), "agent_context_docs (kundonskemal_leads)", "kunden"),
    ],
    "support": [
        ("gemensamt", "system", ("gemensamt",), "agent_global_instructions / agent-core/AGENTS.md", "admin"),
        ("agentdokument", "system", ("agent",), "agent_global_instructions (support) / agent-core/prompts/support-systemprompt.md", "admin"),
        ("kundinstruktion", "system", ("kund",), "agent_configs.instructions_md", "admin"),
        ("affarskontext", "user", ("Kundens affärskontext",), "agent_context_docs (product_marketing)", "kunden"),
        ("rost", "user", ("Kundens röstdokument",), "agent_context_docs (soul)", "kunden"),
        ("kunskapsbas", "user", ("Kunskapsbas",), "kb_articles", "kunden"),
        ("onskemal", "user", ("Kundens egna önskemål",), "agent_context_docs (kundonskemal_support)", "kunden"),
    ],
}


async def _fyllnad(storage, tenant_id: str, agent: str, lager, agent_md: str) -> dict[str, int]:
    """Hur många tecken varje underlag har i dag. 0 = tomt."""

    async def _doc(kind: str) -> int:
        try:
            doc = await storage.get_latest_context_doc(tenant_id, kind=kind)
        except Exception:  # noqa: BLE001
            return 0
        return len(((doc or {}).get("content") or "").strip())

    ut = {
        "gemensamt": len(lager.global_md),
        "agentdokument": len(agent_md),
        "kundinstruktion": len(lager.kund_md),
        "affarskontext": await _doc("product_marketing"),
        "rost": await _doc("soul"),
        "onskemal": await _doc(f"kundonskemal_{agent}"),
    }
    if agent == "support":
        try:
            ut["kunskapsbas"] = sum(len(str(a.get("content") or "")) for a in await storage.list_kb(tenant_id))
        except Exception:  # noqa: BLE001
            ut["kunskapsbas"] = 0
        return ut
    from ..agent.leads_research_v2 import las_produkter
    from ..leads.icp import render_icp
    from ..leads.profil import render_profil

    installningar = await storage.get_agent_settings(tenant_id, agent_type="leads") or {}
    ut["kundresearch"] = await _doc("customer_research")
    ut["malgrupp"] = len(render_icp(installningar.get("icp"))) if installningar.get("icp") else 0
    ut["produkter"] = sum(len(p["namn"]) + len(p["nytta"]) for p in las_produkter(installningar))
    ut["profil"] = len(render_profil(installningar["profil"])) if isinstance(installningar.get("profil"), dict) else 0
    return ut


def kallmatris(
    agent: str, stegnoder: list[dict[str, Any]], fyllnad: dict[str, int]
) -> dict[str, Any]:
    """Underlag × steg. Ren funktion över stegnoderna (med sina system- och
    användarlager) och fyllnaden, så att den går att pröva utan databas.

    Rött (`dott`): ett ifyllt underlag som inget steg läser. Rött per cell
    (`saknas_i`): ett steg som kräver ett underlag som är tomt. Okänt
    (`okant`): användarunderlag när inget steg har en körning att läsa ur —
    utan körning går det inte att säga vad användarmeddelandet bär."""
    rader = []
    nagon_korning = any(n.get("anvandare") for n in stegnoder)
    for uid, position, markorer, kalla, vem in _UNDERLAG[agent]:
        celler: dict[str, dict[str, Any]] = {}
        saknas_i: list[str] = []
        for nod in stegnoder:
            if position == "system":
                traff = [p for p in nod["lager"] if p["etikett"] in markorer]
            else:
                traff = [
                    p for p in ((nod.get("anvandare") or {}).get("lager") or [])
                    if any(p["etikett"].startswith(m) for m in markorer)
                ]
            if traff:
                celler[nod["id"]] = {
                    "position": position,
                    "tecken": sum(p["tecken"] for p in traff),
                    "hash": traff[0]["hash"],
                }
            if any(KRAV_UNDERLAG.get(k) == uid for k in nod["kraver"]) and not fyllnad.get(uid):
                saknas_i.append(nod["id"])
        ifyllt = fyllnad.get(uid, 0)
        okant = position == "user" and not nagon_korning
        rader.append(
            {
                "id": uid,
                "position": position,
                "kalla": kalla,
                "vem": vem,
                "tecken": ifyllt,
                "celler": celler,
                "dott": bool(ifyllt) and not celler and not okant,
                "okant": okant,
                "saknas_i": saknas_i,
            }
        )
    return {"kolumner": [{"id": n["id"], "skill": n["skill"], "bana": n["bana"]} for n in stegnoder], "rader": rader}


async def oversikt(storage, tenant_id: str, agent: str, *, kanal: str = "chat") -> dict[str, Any]:
    """GET /api/admin/tenants/{id}/insyn: flödeskartan, lagerstapeln per steg
    och källmatrisen för en kund och en agent."""
    if agent not in ("leads", "support"):
        raise ValueError("agent måste vara leads eller support")
    kedjeversion, ritade = banor(agent)
    lager, namn, installningar = await _lager_for_agent(storage, tenant_id, agent, kanal)

    texter: dict[str, str] = {}
    senaste: dict[str, list[dict[str, Any]]] = {}
    stegnoder: list[dict[str, Any]] = []
    agent_md = ""
    for bana in ritade:
        for i, nod in enumerate(bana["noder"]):
            if nod["typ"] != "steg":
                continue
            steglager = _lager_for_steg(lager, nod, namn, kanal, installningar)
            agent_md = agent_md or steglager.agent_md
            ut = _stegnod(nod, steglager, tenant_id, texter)
            typ = nod["bana"]["agent_type"]
            if typ not in senaste:
                senaste[typ] = await _senaste_steg(storage, tenant_id, typ)
            roll = nod["bana"]["roll"]
            post = next(
                (p for p in senaste[typ] if p["skill"] == ut["skill"] and p.get("roll", roll) == roll), None
            )
            if post:
                ut["anvandare"] = {
                    "run_id": post["_run_id"],
                    "created_at": post["_created_at"],
                    "kapat": post.get("spar") != 2,
                    "lager": _anvandarlager(post),
                }
            bana["noder"][i] = ut
            stegnoder.append(ut)

    fyllnad = await _fyllnad(storage, tenant_id, agent, lager, agent_md)
    return {
        "agent": agent,
        "kedja": kedjeversion,
        "kanal": kanal if agent == "support" else None,
        "banor": ritade,
        "texter": texter,
        "matris": kallmatris(agent, stegnoder, fyllnad),
    }


def skillfil(skill: str, fil: str) -> dict[str, Any]:
    """GET /api/admin/skills/fil: hela filen och kontrollen mot manifestet.
    Läser med samma läsväg som promptbygget (registry)."""
    from .registry import fil_kontroll, load_reference, load_skill_md

    text = load_skill_md(skill) if fil == "SKILL.md" else load_reference(skill, fil)
    return {"skill": skill, "fil": fil, "text": text, "tecken": len(text), **fil_kontroll(skill, fil)}


async def kb_prov(storage, tenant_id: str, fraga: str) -> dict[str, Any]:
    """POST /api/admin/tenants/{id}/insyn/kb-prov: vilka artiklar en fråga
    hade hämtat. Samma sökning som supportagenten (support_agent._sok_kb och
    den förenklade andra frågan). Inget språkmodellanrop: triagestegets
    svenska omformulering är ett sådant och hoppas därför över, vilket
    svaret säger."""
    from ..agent.support_agent import _forenklad_fraga, _sok_kb

    forsok = ["hela frågan"]
    artiklar = await _sok_kb(storage, tenant_id, fraga)
    if not artiklar:
        bredare = _forenklad_fraga("", fraga)
        if bredare:
            artiklar = await _sok_kb(storage, tenant_id, bredare)
            forsok.append(f"förenklad fråga ({bredare!r})")
    return {
        "fraga": fraga,
        "forsok": forsok,
        "utan_omformulering": True,
        "artiklar": [
            {
                "id": str(a.get("id") or ""),
                "title": a.get("title"),
                "tecken": len(str(a.get("content") or "")),
                "utdrag": str(a.get("content") or "")[:400],
            }
            for a in artiklar
        ],
    }


# -- Kedjan för en körning ---------------------------------------------------


def _hitta(logg: list[dict[str, Any]], nyckel: str) -> dict[str, Any] | None:
    return next((p for p in logg if isinstance(p, dict) and p.get("step") == nyckel), None)


def _logg(run: dict[str, Any] | None) -> list[dict[str, Any]]:
    logg = (run or {}).get("step_log") or []
    if isinstance(logg, str):
        try:
            logg = json.loads(logg)
        except ValueError:
            logg = []
    return logg if isinstance(logg, list) else []


def bygg_kedja(
    prospect: dict[str, Any], kallor: list[str], runs: list[dict[str, Any]], ritade: list[dict[str, Any]]
) -> dict[str, Any]:
    """Iris huvudbana för ett bolag, färgad efter vad som hände. Ren funktion
    över prospektraden, dess källor och dess körningar (nyast först), så att
    "var stannade kedjan och varför" går att pröva utan databas.

    Utfall per nod: kord | slappt | falld | stoppad | hoppad | ej_nadd | okant.
    Den första noden som fäller eller stoppar blir `stannade`; allt efter den
    är ej_nadd."""
    research = next((r for r in runs if r.get("agent_type") == "leads_research"), None)
    utkast = next((r for r in runs if r.get("agent_type") == "leads_outreach"), None)
    rlogg, ulogg = _logg(research), _logg(utkast)
    jev = (prospect.get("jev") or {}) if isinstance(prospect.get("jev"), dict) else {}
    origin = prospect.get("origin")
    fran_sokning = origin == "iris" or bool(jev.get("triage"))

    huvud = next(b for b in ritade if b["id"] == "iris")
    noder: list[dict[str, Any]] = []
    stannade: dict[str, Any] | None = None

    def satt(nod: dict[str, Any], utfall: str, skal: Any = None, **mer: Any) -> None:
        nonlocal stannade
        if stannade is not None:
            utfall, skal = "ej_nadd", None
        noder.append({**nod, "utfall": utfall, "skal": skal, **mer})
        if stannade is None and utfall in ("falld", "stoppad"):
            stannade = {"nod": nod["id"], "skal": skal}

    for nod in huvud["noder"]:
        g = nod.get("grind")
        if g == "kalla":
            satt(nod, "kord", {"origin": origin}, kallor=kallor)
        elif g in ("forfilter", "existens"):
            satt(nod, "slappt" if fran_sokning else "hoppad",
                 None if fran_sokning else {"kod": "tillagd_utanfor_sokningen", "origin": origin})
        elif g == "jev":
            triage = jev.get("triage")
            if not triage:
                satt(nod, "hoppad", {"kod": "jev_av"})
            else:
                satt(nod, "falld" if triage.get("beslut") == "fall" else "slappt", None, utdata=triage)
        elif nod["typ"] == "steg" and nod["bana"] == "research":
            kallmaterial = _hitta(rlogg, "grind:kallmaterial")
            post = next((p for p in rlogg if p.get("skill") == nod["skill"]), None)
            if research is None:
                satt(nod, "ej_nadd", {"kod": "ingen_korning"})
            elif kallmaterial and kallmaterial.get("utslag") == "falld":
                satt(nod, "stoppad", {"kod": "kallmaterial_tomt", "tecken": kallmaterial.get("tecken", 0)},
                     run_id=str(research.get("id")))
            elif post:
                satt(nod, "kord", None, run_id=str(research.get("id")), post=post,
                     sidoanrop=[p for p in rlogg if str(p.get("step", "")).startswith("anrop:")])
            else:
                satt(nod, "okant", {"kod": "inget_steg_i_spåret"}, run_id=str(research.get("id")))
        elif g == "bedomning":
            b = _hitta(rlogg, "grind:bedomning")
            if b is None:
                satt(nod, "okant" if research else "ej_nadd", None)
            else:
                satt(nod, "slappt" if b.get("qualified") else "falld",
                     None if b.get("qualified") else {"kod": "ej_kvalificerad", "disqualifiers": b.get("disqualifiers")},
                     utdata=b)
        elif g == "kontakt":
            k = _hitta(rlogg, "grind:kontakt")
            if k is None:
                satt(nod, "okant" if research else "ej_nadd", None)
            else:
                satt(nod, "falld" if k.get("saknas") else "slappt",
                     {"kod": "kontakt_saknas", "text": k.get("skal")} if k.get("saknas") else None, utdata=k)
        elif nod["typ"] == "steg":
            post = next((p for p in ulogg if p.get("skill") == nod["skill"]), None)
            if utkast is None:
                satt(nod, "ej_nadd", {"kod": "ingen_korning"})
            else:
                satt(nod, "kord" if post else "hoppad", None, run_id=str(utkast.get("id")), post=post)
        elif g == "faktagrind":
            f = _hitta(ulogg, "grind:faktagrind")
            if f is None:
                satt(nod, "okant" if utkast else "ej_nadd", None)
            else:
                satt(nod, "slappt" if f.get("ok") else "falld",
                     None if f.get("ok") else {"kod": "ostodda_pastaenden", "lista": f.get("unsupported_after")},
                     utdata=f)
        elif g == "ko":
            k = _hitta(ulogg, "grind:ko")
            if k is None:
                satt(nod, "okant" if utkast else "ej_nadd", None)
            else:
                satt(nod, "slappt" if k.get("koad") else "falld",
                     None if k.get("koad") else {"kod": "ej_koad", "text": k.get("skal")}, utdata=k)
        else:
            satt(nod, "okant", None)

    skills = [
        {"steg": n["id"], "skill": n["skill"], "run_id": n.get("run_id"),
         "delar": (n.get("post") or {}).get("skilldelar") or [],
         "lager": (n.get("post") or {}).get("lager") or []}
        for n in noder if n["typ"] == "steg" and n.get("post")
    ]
    return {"noder": noder, "stannade": stannade, "skills": skills}


async def kedja(storage, tenant_id: str, prospect_id: str) -> dict[str, Any] | None:
    """GET /api/admin/prospects/{id}/kedja."""
    prospect = await storage.get_prospect(tenant_id, prospect_id)
    if not prospect:
        return None
    kedjeversion, ritade = banor("leads")
    # Stegnoderna i kartan bär sin playbookinfo; i kedjan räcker id och skill.
    for bana in ritade:
        bana["noder"] = [
            {"typ": "steg", "id": n["id"], "bana": n["bana"]["id"], "skill": n["step"].skill}
            if n["typ"] == "steg" else n
            for n in bana["noder"]
        ]
    runs = await storage.list_agent_runs_all(tenant_id=tenant_id, prospect_id=prospect_id, limit=50)
    kallor = sorted(await storage.list_prospect_source_urls(tenant_id, prospect_id))
    ut = bygg_kedja(prospect, kallor, runs, ritade)
    hashar = sorted({p["hash"] for s in ut["skills"] for p in s["lager"] if p.get("position") == "system"})
    return {
        "prospect": {
            k: prospect.get(k)
            for k in ("id", "company_name", "website", "origin", "status", "niva", "score_total")
        },
        "kedja": kedjeversion,
        "korningar": [
            {"id": str(r.get("id")), "agent_type": r.get("agent_type"), "created_at": str(r.get("created_at") or "")}
            for r in runs
        ],
        "texter": await storage.get_prompt_lager(hashar),
        **ut,
    }
