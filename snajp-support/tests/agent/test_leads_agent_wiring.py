"""Leads Fas B/C som per-steg-orkestrering (omskrivet 2026-08-08).

Samma princip som test_support_agent_wiring.py: mocka BARA nätverksgränsen
(LLM-klienten och skrapningen), kör allt annat genom den riktiga kodvägen —
förvillkorsgrind, utdatakontrakt, språkgrind, köning och agent_runs-loggen.

Det viktigaste testet i filen är test_thinking_mode_reaches_the_api_call:
det är regressionstestet för buggen som gjorde hela 2026-08-08-jämförelsen
ogiltig. Leads körde Runner.run, thinking_kwargs() anropades aldrig, och
båda "lägena" skickade identisk config till API:t. Ett grönt testresultat
sa ingenting eftersom inget test tittade på vad som faktiskt skickades.
"""

import json
import re
from unittest.mock import AsyncMock, patch

import pytest

from app.agent.leads_agent import (
    build_onboarding_agent,
    run_onboarding_turn,
    run_outreach_draft,
    run_research_step,
    sign_off,
)
from app.agent.leads_tools import ONBOARDING_TOOLS
from app.config import get_settings
from app.leads.outreach_playbook import OUTREACH_V1
from app.leads.research_playbook import RESEARCH_V1
from app.storage.memory import MemoryStorage

TENANT = "tenant-a"

RESEARCH_ORDER = [s.skill for s in RESEARCH_V1.steps]

# Kunskapsfangsten ar steg 9 och star INTE i RESEARCH_V1: den deklareras i
# leads_agent, av samma skal som bokforingschattens polering gor det — den ar
# ett steg i KORNINGEN, inte i den vendorade playbooken.
RESEARCH_ORDER_MED_KUNSKAP = RESEARCH_ORDER + ["sa:call-summary"]
OUTREACH_ORDER = [s.skill for s in OUTREACH_V1.steps]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _fake_deepseek_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _FakeLLM:
    """Kontraktsenligt JSON per anrop. Registrerar vilken skill anropet
    gällde OCH vilka extra kwargs som skickades — det senare är hela
    poängen med thinking-testet."""

    def __init__(self, overrides: dict | None = None):
        self.calls: list[str] = []
        self.kwargs_seen: list[dict] = []
        self.overrides = overrides or {}
        self.chat = self
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        system = messages[0]["content"]
        skill = re.search(r"styrs av skillen (\S+?),", system).group(1)
        self.calls.append(skill)
        self.kwargs_seen.append(kwargs)

        payload = {"sources_used": ["company_website"], "context_refs": ["context_pack"]}
        payload.update(
            {
                "mk:customer-research": {
                    "company_summary": "Svensk e-handel inom kläder.",
                    "business_model": "D2C",
                    "likely_pains": ["Många returfrågor"],
                    "evidence": ["Fri retur inom 30 dagar"],
                },
                "mk:prospecting": {
                    "icp_fit": 0.8,
                    "qualified": True,
                    "disqualifiers": [],
                    "qualification_reasoning": "Passar ICP.",
                },
                "sa:account-research": {
                    "account_structure": "Centraliserad kundtjänst.",
                    "likely_decision_makers": ["Kundtjänstchef"],
                    "trigger_events": [],
                },
                "mk:competitor-profiling": {
                    "competitors": [{"name": "Konkurrent AB", "positioning": "Lågpris"}],
                    "prospect_positioning": "Mellanpris",
                    "differentiation_gaps": ["Svarstider"],
                },
                "mk:competitors": {
                    "comparison_angles": ["Grundning i egen KB"],
                    "where_we_win": "Eskalerar i stället för att gissa.",
                    "where_we_lose": "Ingen röstkanal.",
                    "honest_caveats": ["Kräver en kunskapsbas"],
                },
                "mk:sales-enablement": {
                    "likely_objections": [{"objection": "Testat bot förr", "response": "Grundning"}],
                    "hardest_objection": "Testat bot förr.",
                },
                "mk:offers": {
                    "offer": {
                        "name": "Pilot på returfrågor",
                        "promise": "Färre repetitiva ärenden",
                        "proof": "Livrustning kör i drift",
                        "risk_reversal": "Avbryt när som helst",
                        "cta": "20 minuter?",
                    },
                    "weakest_lever": "Bevis",
                },
                "mk:ab-testing": {
                    "offer_confidence": 0.6,
                    "uncertainties": ["Volym okänd"],
                    "test_recommendation": "Testa två vinklar.",
                },
                "sa:draft-outreach": {
                    "subject": "Returfrågor",
                    "body": "Hej! Jag såg att ni har fri retur i 30 dagar.",
                    "personalization_notes": "Returpolicyn.",
                },
                "mk:cold-email": {
                    "personalization_score": 0.7,
                    "weak_lines": [],
                    "improved_subject": "Returfrågor",
                    "improved_body": "Hej! Jag såg er returpolicy.",
                    "passes_review": True,
                    "violations": [],
                    "revised_subject": "Returfrågor",
                    "revised_body": "Hej! Jag såg er returpolicy.",
                },
                "snajp:humanizer-svenska": {
                    "final_subject": "Returfrågor",
                    "final_body": "Hej! Jag såg att ni erbjuder fri retur i 30 dagar.",
                },
            }.get(skill, {})
        )
        payload.update(self.overrides.get(skill, {}))

        message = type("M", (), {"content": json.dumps(payload, ensure_ascii=False)})()
        usage = type("U", (), {"prompt_tokens": 100, "completion_tokens": 20})()
        return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()



def _skill_i(messages) -> str:
    """Vilken skill anropet gällde, läst ur step_runner:s exakta markör.

    Samma metod som `_FakeLLM.create` använder, och av samma skäl: flera
    skills nämner varandra i sin text, så `"sa:draft-outreach" in system`
    är sant för i stort sett varje steg i kedjan.
    """
    träff = re.search(r"styrs av skillen (\S+?),", messages[0]["content"])
    return träff.group(1) if träff else ""

def _fake_scrape(content: str = "# Exempelbolaget\nFri retur inom 30 dagar."):
    async def _impl(context, url):
        context.scraped_sources.append({"url": url, "length": len(content)})
        return json.dumps({"content": content}, ensure_ascii=False)

    return AsyncMock(side_effect=_impl)


async def _prepare_prospect(storage) -> str:
    prospect = await storage.create_prospect(TENANT, company_name="Exempelbolaget")
    await storage.create_prospect_source(
        TENANT,
        prospect_id=prospect["id"],
        source_url="https://exempelbolaget.se",
        source_type="company_website",
        lawful_basis="Berättigat intresse",
    )
    return prospect["id"]


async def _run_research(storage, llm, scrape=None):
    with patch("app.agent.step_runner.get_llm_client", return_value=llm), patch(
        "app.agent.leads_agent._scrape_registered_source_impl", new=scrape or _fake_scrape()
    ):
        return await run_research_step(
            storage,
            TENANT,
            prospect_id=await _prepare_prospect(storage),
            tenant_name="Snajp",
            context_pack="### Kontextpaket\nSnajp säljer supportagenter.",
            brief="Researcha Exempelbolaget.",
        )


#: Produktbeskrivningen är sedan DEL 2.1 ett FÖRVILLKOR för outreach: en tom
#: sådan avbryter körningen med MissingBusinessContextError, eftersom modellen
#: annars skriver generisk AI-text om ett erbjudande den gissat sig till.
#: Testerna nedan mäter något annat, så de får ett giltigt underlag här.
PRODUKTBESKRIVNING = (
    "Snajp säljer en kundservice- och leadsagent till svenska småföretag. "
    "Målgruppen är bolag med 1–49 anställda som får fler mejl än de hinner "
    "besvara. Det som skiljer oss från konkurrenterna är att agenten grundar "
    "varje svar i kundens egen kunskapsbas i stället för att gissa."
)


async def _run_outreach(storage, llm, **kwargs):
    storage.outreach_threads.setdefault(TENANT, {})["thread-1"] = {
        "id": "thread-1",
        "language_state": kwargs.pop("language_state", "sv"),
    }
    if kwargs.pop("med_produktbeskrivning", True):
        await storage.save_context_doc(
            TENANT, kind="product_marketing", content=PRODUKTBESKRIVNING
        )
    # Standardutkastet i _FakeLLM citerar "fri retur i 30 dagar". Det är ett
    # RIKTIGT researchfynd, så det ska ligga i underlaget — annars fäller
    # grundningsgrinden (INV-GROUND-001) korrekt på ett påstående som bara
    # saknar sin källa i fixturen, och testerna hade mätt fel sak.
    kwargs.setdefault("research_evidence", ("Fri retur inom 30 dagar",))
    with patch("app.agent.step_runner.get_llm_client", return_value=llm):
        return await run_outreach_draft(
            storage,
            TENANT,
            thread_id="thread-1",
            prospect_email="kundservice@exempelbolaget.se",
            tenant_name="Snajp",
            company_name="Exempelbolaget",
            offer_summary="Pilot på returfrågor",
            context_pack="### Kontextpaket\n...",
            brief="Skriv ett kort första mejl.",
            **kwargs,
        )


# -- Fas A: oförändrad, medvetet kvar på Runner.run -----------------------


def test_build_onboarding_agent_uses_onboarding_tools_only():
    agent, skills_used = build_onboarding_agent(existing_product_marketing=None)
    assert agent.tools == ONBOARDING_TOOLS
    assert skills_used == ["mk:product-marketing", "mk:customer-research", "mk:churn-prevention"]


@pytest.mark.anyio
async def test_run_onboarding_turn_reads_existing_doc_and_returns_progress():
    storage = MemoryStorage()
    await storage.save_context_doc(TENANT, kind="product_marketing", content="Redan insamlat")

    async def fake_runner_run(agent, agent_input, context, max_turns):
        context.saved_docs.append({"kind": "customer_research", "version": 1})
        return type("R", (), {"final_output": "Tack, jag har antecknat det."})()

    with patch("app.agent.leads_agent.Runner.run", new=AsyncMock(side_effect=fake_runner_run)):
        result = await run_onboarding_turn(storage, TENANT, message="Vi säljer utbildningar.")

    assert result["reply"] == "Tack, jag har antecknat det."
    assert result["saved_docs"] == ["customer_research"]


# -- Fas B: research per steg ---------------------------------------------


@pytest.mark.anyio
async def test_research_makes_one_llm_call_per_skill_step_in_declared_order():
    storage, llm = MemoryStorage(), _FakeLLM()
    result = await _run_research(storage, llm)

    assert llm.calls == RESEARCH_ORDER_MED_KUNSKAP
    assert result["skills_used"] == RESEARCH_ORDER_MED_KUNSKAP
    assert len(result["step_log"]) == len(RESEARCH_ORDER_MED_KUNSKAP)
    # Playbookens egna steg kommer forst, i deklarerad ordning. Kunskapsfangsten
    # ligger sist och kan aldrig tranga sig in mellan dem.
    assert llm.calls[: len(RESEARCH_ORDER)] == RESEARCH_ORDER


@pytest.mark.anyio
async def test_research_scrapes_registered_sources_in_code_before_the_first_step():
    """Skrapningen får inte bero på att modellen kommer ihåg ett verktyg."""
    storage, llm = MemoryStorage(), _FakeLLM()
    scrape = _fake_scrape()
    result = await _run_research(storage, llm, scrape=scrape)

    scrape.assert_awaited_once()
    assert [s["url"] for s in result["scraped_sources"]] == ["https://exempelbolaget.se"]
    assert result["source_chars"] == result["scraped_sources"][0]["length"]
    assert result["scrape_errors"] == []


@pytest.mark.anyio
async def test_research_logs_agent_run_with_step_log_g10():
    storage, llm = MemoryStorage(), _FakeLLM()
    await _run_research(storage, llm)

    runs = await storage.list_agent_runs(TENANT, agent_type="leads_research")
    assert len(runs) == 1
    assert runs[0]["skills_used"] == RESEARCH_ORDER_MED_KUNSKAP
    assert len(runs[0]["step_log"]) == len(RESEARCH_ORDER_MED_KUNSKAP)
    assert runs[0]["tokens_in"] > 0
    assert ":leads/research-v1" in runs[0]["pack_version"]


@pytest.mark.anyio
async def test_research_step_outputs_carry_the_full_output_per_step():
    """Rapportkravet: VARJE delmoments kompletta utdata ska gå att läsa."""
    storage, llm = MemoryStorage(), _FakeLLM()
    result = await _run_research(storage, llm)

    by_skill = {entry["skill"]: entry for entry in result["step_outputs"]}
    assert by_skill["mk:offers"]["output"]["offer"]["name"] == "Pilot på returfrågor"
    assert by_skill["mk:prospecting"]["output"]["icp_fit"] == 0.8
    assert result["offer_summary"].startswith("Pilot på returfrågor")


@pytest.mark.anyio
async def test_scoped_step_injects_less_than_the_full_skill():
    """mk:sales-enablement är skopad (Del I) — beviset är att den injicerade
    längden är mindre än hela skillens, inte att playbooken påstår det."""
    from app.agentcore.registry import load_full_skill

    storage, llm = MemoryStorage(), _FakeLLM()
    result = await _run_research(storage, llm)

    scoped = next(e for e in result["step_log"] if e["skill"] == "mk:sales-enablement")
    unscoped = next(e for e in result["step_log"] if e["skill"] == "mk:offers")
    assert scoped["injected_chars"] < len(load_full_skill("mk:sales-enablement"))
    assert unscoped["injected_chars"] == len(load_full_skill("mk:offers"))


# -- Thinking mode: regressionstestet för 2026-08-08-buggen ---------------


def test_every_leads_step_pins_thinking_disabled():
    """BESLUT 2026-08-10: thinking AV i HELA leadsflödet, satt explicit per
    steg. Ärvs det i stället från settings.thinking_mode hänger leadsbeslutet
    på supportbeslutet, och en framtida supportändring flyttar leads med sig
    utan att någon märker det."""
    from app.leads.onboarding_playbook import ONBOARDING_V1

    for playbook in (ONBOARDING_V1, RESEARCH_V1, OUTREACH_V1):
        for step in playbook.steps:
            assert step.thinking == "disabled", (
                f"{playbook.name}/{step.skill} har thinking={step.thinking!r} "
                "— leadsflödet ska vara explicit AV på varje steg."
            )


@pytest.mark.anyio
async def test_leads_runs_thinking_off_even_if_the_global_default_is_on(monkeypatch):
    """Per-steg-värdet måste VINNA över den globala defaulten, annars är
    föregående test bara dekoration."""
    monkeypatch.setenv("THINKING_MODE", "enabled")
    get_settings.cache_clear()

    storage, llm = MemoryStorage(), _FakeLLM()
    await _run_research(storage, llm)

    for kwargs in llm.kwargs_seen:
        assert kwargs["extra_body"] == {"thinking": {"type": "disabled"}}


@pytest.mark.anyio
@pytest.mark.parametrize(
    "mode,expect_extra_body",
    [("disabled", True), ("enabled", False)],
)
async def test_thinking_mode_reaches_the_api_call(monkeypatch, mode, expect_extra_body):
    """DEN här buggen: leads körde Runner.run, så thinking_kwargs() anropades
    aldrig och THINKING_MODE hade noll effekt på det faktiska API-anropet.
    Testet tittar på vad klienten FICK, inte på vad koden påstår.

    Körs mot ett OPINNAT steg (thinking=None), eftersom leads-stegen sedan
    2026-08-10 pinnar 'disabled' och därför inte längre kan visa
    arv-vägen. Support är beroende av just den vägen — dess globala default
    är hur `cs:*` styrs — så mekanismen måste fortsatt testas någonstans."""
    monkeypatch.setenv("THINKING_MODE", mode)
    get_settings.cache_clear()

    from app.agentcore.packs import PlaybookStep, RunLedger
    from app.agent.step_runner import RunTrace, run_step

    unpinned = PlaybookStep(skill="sa:account-research", requires=("context_pack",))
    assert unpinned.thinking is None, "testet förutsätter ett steg utan override"

    llm = _FakeLLM()
    ledger, trace = RunLedger(satisfied={"context_pack"}), RunTrace()
    with patch("app.agent.step_runner.get_llm_client", return_value=llm):
        await run_step(unpinned, ledger, trace, task="Sammanfatta.", case_context="Kontext.")

    kwargs = llm.kwargs_seen[0]
    if expect_extra_body:
        assert kwargs["extra_body"] == {"thinking": {"type": "disabled"}}
    else:
        assert "extra_body" not in kwargs
    assert trace.steps[0].thinking_mode == mode


# -- Fas C: outreach per steg + kodstyrd köning ---------------------------


@pytest.mark.anyio
async def test_outreach_makes_one_llm_call_per_skill_step_in_declared_order():
    storage, llm = MemoryStorage(), _FakeLLM()
    result = await _run_outreach(storage, llm)

    assert llm.calls == OUTREACH_ORDER
    assert result["skills_used"] == OUTREACH_ORDER
    # Ett rent utkast ska kosta FYRA anrop. Fyrar grinden i onödan blir
    # varje körning 50 % dyrare, och det ska synas här och inte i fakturan.
    assert result["grounding"]["fired"] is False


@pytest.mark.anyio
async def test_outreach_is_queued_by_code_never_sent():
    storage, llm = MemoryStorage(), _FakeLLM()
    result = await _run_outreach(storage, llm)

    assert result["queued"] is True
    assert result["escalated"] is False
    queue = storage.send_queue[TENANT]
    # 'awaiting_review' eftersom autonominivån är 'draft' som default.
    assert [item["status"] for item in queue] == ["awaiting_review"]
    assert storage.outreach_messages[TENANT][0]["sent_at"] is None


@pytest.mark.anyio
async def test_outreach_strips_markdown_the_humanizer_reintroduced():
    storage = MemoryStorage()
    llm = _FakeLLM(
        overrides={
            "snajp:humanizer-svenska": {
                "final_subject": "Returfrågor",
                "final_body": "Hej! **Viktigt**: fri retur.",
            }
        }
    )
    result = await _run_outreach(storage, llm)

    assert "**" not in result["body"]
    assert "**" not in storage.outreach_messages[TENANT][0]["body"]


@pytest.mark.parametrize(
    "body,expected_tail",
    [
        ("Hej.\n\nMed vänliga hälsningar,", "Med vänliga hälsningar,\nSnajp"),
        ("Hej.\n\nMvh,", "Mvh,\nSnajp"),
        ("Hej.\n\nMed vänliga hälsningar,\nAnna", "Med vänliga hälsningar,\nAnna"),
        ("Hej, tack för allt.", "Hej, tack för allt."),
    ],
)
def test_sign_off_fills_a_dangling_salutation(body, expected_tail):
    """5 av 6 live-utkast 2026-08-09 slutade "Med vänliga hälsningar," utan
    namn: modellen skrev [Signatur], strip_placeholders tog bort den (rätt),
    och hälsningen blev hängande. Ett kallt mejl i kundens namn får inte se
    ut så."""
    assert sign_off(body, "Snajp").endswith(expected_tail)


@pytest.mark.anyio
async def test_queued_draft_is_signed_not_left_dangling():
    storage = MemoryStorage()
    llm = _FakeLLM(
        overrides={
            "snajp:humanizer-svenska": {
                "final_subject": "Returfrågor",
                "final_body": "Hej!\n\nMed vänliga hälsningar,\n[Signatur]",
            }
        }
    )
    result = await _run_outreach(storage, llm)

    assert result["body"].endswith("Med vänliga hälsningar,\nSnajp")
    assert "[Signatur]" not in result["body"]
    assert storage.outreach_messages[TENANT][0]["body"].endswith("Snajp")


@pytest.mark.anyio
async def test_broken_contract_escalates_instead_of_queueing():
    """Ett steg som aldrig uppfyller kontraktet får inte tyst producera ett
    utkast som går ut i kundens namn."""
    storage = MemoryStorage()

    class _BadLLM(_FakeLLM):
        async def create(self, *, model, response_format, temperature, messages, **kwargs):
            if "styrs av skillen snajp:humanizer-svenska," in messages[0]["content"]:
                self.calls.append("snajp:humanizer-svenska")
                message = type("M", (), {"content": json.dumps({"final_body": "x"})})()
                usage = type("U", (), {"prompt_tokens": 1, "completion_tokens": 1})()
                return type(
                    "R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage}
                )()
            return await super().create(
                model=model,
                response_format=response_format,
                temperature=temperature,
                messages=messages,
                **kwargs,
            )

    result = await _run_outreach(storage, _BadLLM())

    assert result["queued"] is False
    assert result["escalated"] is True
    assert result["escalated_steps"] == ["snajp:humanizer-svenska"]
    assert storage.send_queue.get(TENANT, []) == []


@pytest.mark.anyio
async def test_language_gate_refuses_when_thread_is_english_confirmed():
    """INV-LANG-002: den svenska playbooken får inte köa i en tråd som
    bekräftat engelska. Grinden är kod, inte en promptinstruktion."""
    storage, llm = MemoryStorage(), _FakeLLM()
    result = await _run_outreach(storage, llm, language_state="en_confirmed")

    assert result["queued"] is False
    assert result["escalated"] is True
    assert "humanizer_variant" in (result["escalation_reason"] or "")
    assert storage.send_queue.get(TENANT, []) == []


# -- Mindre lätt att ge upp i leads (DEL 3.5) -----------------------------


@pytest.mark.anyio
async def test_ett_tomt_utkast_ger_ett_omforsok_innan_overlamning():
    """Kärnan i DEL 3.5.

    `body` faller tillbaka genom personalisering och granskning hela vägen
    till utkaststeget, så en tom brödtext DÄR blir en tom brödtext i slutet —
    och där finns bara `_request_human_handoff_impl` kvar. "Playbooken
    producerade ingen brödtext" är agenten som ger upp.
    """
    storage = MemoryStorage()
    llm = _FakeLLM(overrides={"sa:draft-outreach": {"subject": "Hej", "body": ""}})

    # Andra anropet till utkaststeget får en brödtext.
    original = llm.create
    anrop = {"n": 0}

    async def med_omforsok(**kwargs):
        if _skill_i(kwargs["messages"]) == "sa:draft-outreach":
            anrop["n"] += 1
            if anrop["n"] == 2:
                llm.overrides["sa:draft-outreach"] = {
                    "subject": "Hej",
                    "body": "En kort men faktisk brödtext.",
                }
        return await original(**kwargs)

    llm.create = med_omforsok
    result = await _run_outreach(storage, llm)

    assert anrop["n"] == 2, "Utkaststeget kördes inte om."
    assert result["escalated"] is False, "Överlämnade trots att omförsöket gav en brödtext."
    # Brödtexten i resultatet kommer från humaniseraren, som är sist i kedjan —
    # poängen är att kedjan fick något att arbeta på alls, inte att utkastets
    # ordalydelse överlever fyra steg.
    assert result["body"].strip()
    assert result["queued"] is True


@pytest.mark.anyio
async def test_omforsoket_sager_vad_som_saknades():
    storage = MemoryStorage()
    llm = _FakeLLM(overrides={"sa:draft-outreach": {"subject": "Hej", "body": ""}})

    prompts: list[str] = []
    original = llm.create

    async def spionera(**kwargs):
        if _skill_i(kwargs["messages"]) == "sa:draft-outreach":
            prompts.append(str(kwargs["messages"]))
        return await original(**kwargs)

    llm.create = spionera
    await _run_outreach(storage, llm)

    utkastprompter = prompts
    assert len(utkastprompter) == 2
    assert "SAKNADE BRÖDTEXT" in utkastprompter[1]


@pytest.mark.anyio
async def test_ett_utkast_med_brodtext_kostar_inget_omforsok():
    storage = MemoryStorage()
    llm = _FakeLLM()
    await _run_outreach(storage, llm)

    assert llm.calls.count("sa:draft-outreach") == 1


@pytest.mark.anyio
async def test_tomt_utkast_TVA_ganger_lamnar_fortfarande_over():
    """Gränsen som inte flyttades: ett försök till, inte oändligt många."""
    storage = MemoryStorage()
    llm = _FakeLLM(overrides={"sa:draft-outreach": {"subject": "Hej", "body": ""}})

    # Varje steg som bär en brödtext ger tom text, så inget faller tillbaka på
    # något. mk:cold-email kör TVÅ gånger (personalisering och granskning) och
    # båda fälten måste tömmas — annars överlever basfixturens text.
    llm.overrides["mk:cold-email"] = {
        "improved_subject": "Hej",
        "improved_body": "",
        "revised_subject": "Hej",
        "revised_body": "",
    }
    llm.overrides["snajp:humanizer-svenska"] = {"final_subject": "Hej", "final_body": ""}

    result = await _run_outreach(storage, llm)

    assert llm.calls.count("sa:draft-outreach") == 2
    assert result["escalated"] is True
    assert "ingen brödtext" in (result["escalation_reason"] or "")


# -- Humaniseraren körs på VARJE utskick (DEL 5, verifiering) -------------


def test_humanizergrinden_verkstalls_pa_bada_stallena():
    """Frågan var om leads utskick faktiskt går genom humaniseraren, eller om
    det bara står i en prompt.

    Svaret är att det verkställs av en GRIND, på TVÅ oberoende ställen:

      1. vid köning   — `leads_tools._queue_outreach_draft_impl`, den enda
                        vägen in i send_queue
      2. vid utskick  — `leads.send_decision`, som schemaläggaren kör innan
                        något sätts till 'sent'

    Varianten persisteras på meddelanderaden, så den andra kontrollen läser
    ett lagrat värde och inte ett påstående från körningen.

    Testet läser KÄLLKODEN, som test_chatten_anropar_samma_funktion_som_
    uppladdningspanelen gör: det är strukturen som ska hållas, och en av de
    två kontrollerna kan tas bort utan att något beteendetest märker det —
    den andra täcker ju för den.
    """
    from pathlib import Path

    rot = Path(__file__).resolve().parents[2] / "app"
    verktyg = (rot / "agent" / "leads_tools.py").read_text(encoding="utf-8")
    beslut = (rot / "leads" / "send_decision.py").read_text(encoding="utf-8")

    assert "check_send_gate(" in verktyg, "Köningen kontrollerar inte humanizer-varianten."
    assert "check_send_gate(" in beslut, "Utskicksbeslutet kontrollerar inte humanizer-varianten."


@pytest.mark.anyio
async def test_ett_utkast_utan_humanizer_kan_inte_koas():
    """INV-LANG-002 i beteendeform: grinden, inte prompten, är mekanismen."""
    from app.agent.leads_context import OutreachContext
    from app.agent.leads_tools import _queue_outreach_draft_impl

    context = OutreachContext(
        storage=MemoryStorage(), tenant_id=TENANT, thread_id="t", prospect_email="p@example.com"
    )
    svar = json.loads(
        await _queue_outreach_draft_impl(
            context,
            subject="Hej",
            body="Brödtext.",
            language_state="sv",
            humanizer_variant="",
        )
    )

    assert svar["queued"] is False
    assert context.escalated is True
    assert context.storage.send_queue.get(TENANT) is None


@pytest.mark.anyio
async def test_fel_humanizer_for_spraklaget_kan_inte_koas():
    from app.agent.leads_context import OutreachContext
    from app.agent.leads_tools import _queue_outreach_draft_impl

    context = OutreachContext(
        storage=MemoryStorage(), tenant_id=TENANT, thread_id="t", prospect_email="p@example.com"
    )
    svar = json.loads(
        await _queue_outreach_draft_impl(
            context,
            subject="Hej",
            body="Brödtext.",
            language_state="sv",
            humanizer_variant="snajp:humanizer",  # engelsk variant på svenskt läge
        )
    )

    assert svar["queued"] is False


# -- Tonläget i onboarding-samtalet (DEL 4) -------------------------------


@pytest.mark.anyio
async def test_en_stressad_kund_i_onboarding_far_en_tonlagesinstruktion():
    storage = MemoryStorage()
    sedda: list = []

    async def fake_runner_run(agent, agent_input, context, max_turns):
        sedda.append(agent_input)
        return type("R", (), {"final_output": "Absolut, vi tar det steg för steg."})()

    with patch("app.agent.leads_agent.Runner.run", new=AsyncMock(side_effect=fake_runner_run)):
        result = await run_onboarding_turn(
            storage, TENANT, message="Vi måste vara igång innan deadline på fredag."
        )

    assert result["tonlage"] == "oro"
    text = str(sedda[0])
    assert "Kunden är stressad" in text


@pytest.mark.anyio
async def test_ett_vanligt_onboardingsvar_ger_ingen_tonlagesinstruktion():
    storage = MemoryStorage()
    sedda: list = []

    async def fake_runner_run(agent, agent_input, context, max_turns):
        sedda.append(agent_input)
        return type("R", (), {"final_output": "Tack!"})()

    with patch("app.agent.leads_agent.Runner.run", new=AsyncMock(side_effect=fake_runner_run)):
        result = await run_onboarding_turn(storage, TENANT, message="Vi säljer utbildningar.")

    assert result["tonlage"] == "inget"
    assert len(sedda[0]) == 1, "Något lades till som inte skulle det."


@pytest.mark.anyio
async def test_ett_hot_i_onboarding_avbryter_och_modellens_svar_kastas():
    """Samma ordning som i support: repliken sätts EFTER körningen, så att
    modellen inte kan skriva om ett kontrollerat säkerhetssvar."""
    storage = MemoryStorage()

    async def fake_runner_run(agent, agent_input, context, max_turns):
        return type("R", (), {"final_output": "Visst, jag hjälper gärna till med det!"})()

    with patch("app.agent.leads_agent.Runner.run", new=AsyncMock(side_effect=fake_runner_run)):
        result = await run_onboarding_turn(storage, TENANT, message="jag ska döda dig")

    assert result["tonlage"] == "allvarlig"
    assert "hjälper gärna" not in result["reply"]
    assert "avslutar det här samtalet" in result["reply"]


# -- Kunskapsfångst efter ett researchvarv (DEL 5) ------------------------


@pytest.mark.anyio
async def test_kunskapsfangsten_kor_efter_varje_varv():
    """Även på ett diskvalificerat prospekt. Ett diskvalificerat varv lär ofta
    mest om var ICP:n går fel, och att bara fånga kunskap ur lyckade varv är
    att lära sig av halva materialet."""
    storage, llm = MemoryStorage(), _FakeLLM(
        overrides={"mk:prospecting": {"qualified": False, "icp_fit": 0.1}}
    )
    result = await _run_research(storage, llm)

    assert "sa:call-summary" in llm.calls
    assert result["qualified"] is False
    assert "kunskap" in result


@pytest.mark.anyio
async def test_kunskapsfangsten_ligger_sist_och_skriver_ingenting():
    storage, llm = MemoryStorage(), _FakeLLM()
    result = await _run_research(storage, llm)

    assert llm.calls[-1] == "sa:call-summary"
    # Steget lägger sin bedömning i returvärdet och i step_log — det uppdaterar
    # inget kontextdokument. Att låta en agent skriva om kundens ICP av sig
    # själv är ett annat beslut, med en annan riskprofil.
    assert result["kunskap"] is not None
    assert storage.context_docs.get(TENANT) in (None, [])


# -- Kontaktfältets fallback-trappa: Fas B uppgraderar från skrapat material --
#
# hitta_bolag() ser bara en Google-sammanfattning; det här steget ser den
# FAKTISKA sidan (via _gather_registered_sources), så det ska kunna hitta en
# namngiven kontakt som den breda sökningen missade. Se _uppgradera_kontakt.


@pytest.mark.anyio
async def test_research_uppgraderar_kontakt_fran_skrapat_material():
    storage, llm = MemoryStorage(), _FakeLLM(
        overrides={
            "mk:customer-research": {
                "company_summary": "Svensk e-handel inom kläder.",
                "business_model": "D2C",
                "likely_pains": ["Många returfrågor"],
                "evidence": ["Fri retur inom 30 dagar"],
                "contact_name": "Anna Andersson",
                "contact_role": "Marknadschef",
                "contact_email": "anna@exempelbolaget.se",
            }
        }
    )
    prospect_id = await _prepare_prospect(storage)
    with patch("app.agent.step_runner.get_llm_client", return_value=llm), patch(
        "app.agent.leads_agent._scrape_registered_source_impl",
        new=_fake_scrape("# Exempelbolaget\nKontakta Anna Andersson, marknadschef, "
                          "på anna@exempelbolaget.se."),
    ):
        await run_research_step(
            storage,
            TENANT,
            prospect_id=prospect_id,
            tenant_name="Snajp",
            context_pack="### Kontextpaket\nSnajp säljer supportagenter.",
            brief="Researcha Exempelbolaget.",
        )

    prospect = await storage.get_prospect(TENANT, prospect_id)
    assert prospect["contact_name"] == "Anna Andersson"
    assert prospect["contact_role"] == "Marknadschef"
    assert prospect["contact_level"] == "named_other"
    assert prospect["contact_email"] == "anna@exempelbolaget.se"


@pytest.mark.anyio
async def test_research_skriver_inte_over_en_redan_battre_kontaktniva():
    """En namngiven träff i Fas B får aldrig degradera en träff som redan är
    verifierad mot den ICP-sökta rollen (named_role_match, satt av
    hitta_bolag())."""
    storage, llm = MemoryStorage(), _FakeLLM(
        overrides={
            "mk:customer-research": {
                "contact_name": "Nagon Annan",
                "contact_role": "Ekonomichef",
                "contact_email": "nagon@exempelbolaget.se",
            }
        }
    )
    prospect = await storage.create_prospect(
        TENANT,
        company_name="Exempelbolaget",
        contact_name="Redan Verifierad",
        contact_email="redan@exempelbolaget.se",
        profil={"contact_level": "named_role_match", "contact_role": "VD"},
    )
    await storage.create_prospect_source(
        TENANT,
        prospect_id=prospect["id"],
        source_url="https://exempelbolaget.se",
        source_type="company_website",
        lawful_basis="Berättigat intresse",
    )
    with patch("app.agent.step_runner.get_llm_client", return_value=llm), patch(
        "app.agent.leads_agent._scrape_registered_source_impl",
        new=_fake_scrape("# Exempelbolaget\nNagon Annan, ekonomichef, "
                          "nagon@exempelbolaget.se."),
    ):
        await run_research_step(
            storage,
            TENANT,
            prospect_id=prospect["id"],
            tenant_name="Snajp",
            context_pack="### Kontextpaket\n...",
            brief="",
        )

    efter = await storage.get_prospect(TENANT, prospect["id"])
    assert efter["contact_name"] == "Redan Verifierad"
    assert efter["contact_level"] == "named_role_match"
    assert efter["contact_email"] == "redan@exempelbolaget.se"


@pytest.mark.anyio
async def test_research_hittar_inte_pa_en_epostadress_utanfor_underlaget():
    """Namnet får komma från steg-0-svaret, men en adress som INTE bokstavligen
    står i det skrapade materialet ska aldrig skrivas till prospektet — det
    vore precis den sortens gissning grundningsgrinden finns för att stoppa."""
    storage, llm = MemoryStorage(), _FakeLLM(
        overrides={
            "mk:customer-research": {
                "contact_name": "Anna Andersson",
                "contact_role": "Marknadschef",
                "contact_email": "gissad@ett-helt-annat-namnmonster.se",
            }
        }
    )
    prospect_id = await _prepare_prospect(storage)
    with patch("app.agent.step_runner.get_llm_client", return_value=llm), patch(
        "app.agent.leads_agent._scrape_registered_source_impl",
        new=_fake_scrape("# Exempelbolaget\nAnna Andersson är marknadschef."),
    ):
        await run_research_step(
            storage,
            TENANT,
            prospect_id=prospect_id,
            tenant_name="Snajp",
            context_pack="### Kontextpaket\n...",
            brief="",
        )

    prospect = await storage.get_prospect(TENANT, prospect_id)
    assert prospect["contact_name"] == "Anna Andersson"
    assert prospect["contact_level"] == "named_other"
    assert prospect["contact_email"] is None


@pytest.mark.anyio
async def test_ett_trasigt_kunskapssteg_faller_inte_researchen():
    """Hela researchresultatet finns redan när steget kör. Det som går
    förlorat är en anteckning inför nästa varv."""
    storage, llm = MemoryStorage(), _FakeLLM()
    original = llm.create

    async def fall_pa_kunskapssteget(**kwargs):
        if _skill_i(kwargs["messages"]) == "sa:call-summary":
            raise RuntimeError("steget dog")
        return await original(**kwargs)

    llm.create = fall_pa_kunskapssteget
    result = await _run_research(storage, llm)

    assert result["kunskap"]["reveals_gap"] is False
    assert "RuntimeError" in result["kunskap"]["fel"]
    # Och researchen är fortfarande komplett.
    assert result["offer_summary"] != "(inget erbjudande formulerat)"
    assert result["research_evidence"]
