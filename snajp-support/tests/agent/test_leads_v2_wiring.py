"""V2-kedjan (kostnadsarbetet 2026-09-02): 1 research-anrop + 2 utkastanrop.

Samma princip som test_leads_agent_wiring.py: mocka BARA nätverksgränsen
(LLM-klienten och skrapningen), kör allt annat genom den riktiga kodvägen —
förvillkorsgrind, extra_skills-rendering, språkgrind, köning och
agent_runs-loggen. Det V2 lovar och det som testas här:

  1. Research är EXAKT ETT anrop och returnerar V1:s artefaktkontrakt.
  2. Utkastet är EXAKT TVÅ anrop (+ villkorad grundning), där steg 1
     injicerar BÅDE sa:draft-outreach och mk:cold-emails personaliserings-
     och granskningsdelar, och humanizern är fysiskt SIST (INV-LANG-002).
  3. Kedjevalet styrs av settings.leads_pipeline.
"""

import json
import re
from unittest.mock import AsyncMock, patch

import pytest

from app.agent.leads_research_v2 import run_outreach_draft_v2, run_research_step_v2
from app.agentcore.packs import PlaybookStep, ScopeWithoutRationaleError
from app.config import get_settings
from app.leads.outreach_playbook import OUTREACH_V2
from app.leads.research_playbook import RESEARCH_V2
from app.storage.memory import MemoryStorage

TENANT = "tenant-a"

pytestmark = pytest.mark.anyio


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


_RESEARCH_SVAR = {
    "company_summary": "Svensk e-handel inom kläder.",
    "business_model": "D2C",
    "likely_pains": ["Många returfrågor"],
    "evidence": ["Fri retur inom 30 dagar"],
    "existing_support_channels": ["mejl"],
    "has_chatbot": False,
    "contact_name": None,
    "contact_role": None,
    "contact_email": "kundservice@exempelbolaget.se",
    "icp_fit": 0.8,
    "qualified": True,
    "disqualifiers": [],
    "qualification_reasoning": "Passar ICP.",
    "missing_information": [],
    "account_structure": "Centraliserad kundtjänst.",
    "decision_makers": ["Kundtjänstchef"],
    "trigger_events": ["Rekryterar kundtjänst"],
    "open_questions": [],
    "prospect_positioning": "Mellanpris",
    "comparison_angles": ["Grundning i egen KB"],
    "honest_caveats": ["Kräver en kunskapsbas"],
    "likely_objections": [{"objection": "Testat bot förr", "response": "Grundning"}],
    "hardest_objection": "Testat bot förr.",
    "offer": {
        "name": "Pilot på returfrågor",
        "promise": "Färre repetitiva ärenden",
        "proof": "Kör i drift",
        "risk_reversal": "Avbryt när som helst",
        "cta": "20 minuter?",
    },
    "weakest_lever": "Bevis",
    "offer_confidence": 0.6,
    "uncertainties": ["Volym okänd"],
    "reveals_gap": False,
    "gap": None,
    "icp_adjustment": None,
    "kunskap_evidence": [],
}


class _FakeLLM:
    """Kontraktsenligt JSON per anrop, nycklad på skill (step_runners exakta
    markör i systemprompten). Sparar systemprompterna — extra_skills-testet
    behöver kunna titta på vad modellen faktiskt FICK."""

    def __init__(self, overrides: dict | None = None):
        self.calls: list[str] = []
        self.system_prompts: list[str] = []
        self.overrides = overrides or {}
        self.chat = self
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        system = messages[0]["content"]
        skill = re.search(r"styrs av skillen (\S+?),", system).group(1)
        self.calls.append(skill)
        self.system_prompts.append(system)

        payload = {"sources_used": ["company_website"], "context_refs": ["context_pack"]}
        payload.update(
            {
                "sa:account-research": dict(_RESEARCH_SVAR),
                "sa:draft-outreach": {
                    "subject": "Returfrågor",
                    "body": "Hej! Jag såg att ni har fri retur i 30 dagar.",
                    "personalization_score": 0.7,
                    "weak_lines": [],
                    "passes_review": True,
                    "violations": [],
                    "draft_reasoning": "Returpolicyn.",
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


def _fake_scrape(
    content: str = "# Exempelbolaget\nFri retur inom 30 dagar.\n"
    "Kontakta oss: kundservice@exempelbolaget.se",
):
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
        lawful_basis="berättigat intresse (B2B)",
    )
    return prospect["id"]


# --- Playbookstruktur -------------------------------------------------------


def test_research_v2_ar_ett_steg_som_kraver_context_pack():
    """INV-SKILL-004-pariteten: även V2:s (enda) steg kräver kontextpaketet."""
    assert len(RESEARCH_V2.steps) == 1
    assert "context_pack" in RESEARCH_V2.steps[0].requires
    assert RESEARCH_V2.steps[0].overlay == "leads-research-v2"
    assert RESEARCH_V2.steps[0].thinking == "disabled"


def test_outreach_v2_ar_tva_steg_med_humanizern_sist():
    """INV-LANG-002 strukturellt: humanizern är fysiskt sista deklarerade
    steget, precis som i V1 — ingen invariantändring behövs."""
    assert len(OUTREACH_V2.steps) == 2
    assert OUTREACH_V2.steps[0].skill == "sa:draft-outreach"
    assert OUTREACH_V2.steps[-1].skill == "snajp:humanizer-svenska"


def test_extra_skills_renderas_i_samma_steg():
    """Motorn injicerar mk:cold-emails personaliserings- och gransknings-
    delar i steg 1:s renderade text — modellen väljer aldrig."""
    rendered = OUTREACH_V2.steps[0].render()
    assert "Skill (i samma steg): mk:cold-email" in rendered
    # personalization.md + de två granskningssektionerna ur SKILL.md.
    assert "references/personalization.md" in rendered
    assert "Quality Check" in rendered
    assert "What to Avoid" in rendered


def test_skopad_extra_skill_utan_rationale_faller():
    with pytest.raises(ScopeWithoutRationaleError):
        PlaybookStep(
            skill="sa:draft-outreach",
            requires=("offer_selected",),
            extra_skills=(("mk:cold-email", ("references/personalization.md",)),),
        )


# --- Research V2 ------------------------------------------------------------


async def test_research_v2_ar_exakt_ett_anrop_med_v1_kontraktet():
    storage = MemoryStorage()
    prospect_id = await _prepare_prospect(storage)
    llm = _FakeLLM()

    with (
        patch("app.agent.step_runner.get_llm_client", return_value=llm),
        patch("app.agent.leads_agent._scrape_registered_source_impl", new=_fake_scrape()),
    ):
        result = await run_research_step_v2(
            storage,
            TENANT,
            prospect_id=prospect_id,
            tenant_name="Snajp",
            context_pack="## Kontextpaket\nICP: svensk e-handel.",
            brief="",
            is_test=True,
        )

    assert llm.calls == ["sa:account-research"], "V2-research ska vara EXAKT ett LLM-anrop"
    # Overlayen med destillatet måste ha nått systemprompten.
    assert "leads-research-v2" in llm.system_prompts[0]
    assert "Konsoliderad prospektresearch" in llm.system_prompts[0]

    # V1:s artefaktkontrakt — nycklarna nedströmskonsumenterna faktiskt läser.
    for nyckel in (
        "research_evidence",
        "offer_summary",
        "final_output",
        "kunskap",
        "qualified",
        "icp_fit",
        "stopped_early",
        "contact_level",
        "contact_missing",
        "contact_missing_reason",
        "contact_discovery",
        "step_log",
        "tokens_in",
        "tokens_out",
        "pack_version",
    ):
        assert nyckel in result, f"V2-returen saknar {nyckel} ur V1-kontraktet"

    # Buggfix-pariteten: toppnivåfälten batch-vägen alltid antagit fanns.
    assert result["company_summary"] == "Svensk e-handel inom kläder."
    assert result["likely_pains"] == ["Många returfrågor"]

    # Beläggen = citat + pains + triggers, som V1.
    assert "Fri retur inom 30 dagar" in result["research_evidence"]
    assert "Rekryterar kundtjänst" in result["research_evidence"]

    # agent_runs-raden skrevs med V2:s pack_version.
    runs = await storage.list_agent_runs(TENANT, agent_type="leads_research")
    assert len(runs) == 1
    assert "leads/research-v2" in runs[0]["pack_version"]
    assert runs[0]["is_test"] is True


async def test_research_v2_uppgraderar_kontakten_ur_skrapet():
    """Kontakttrappan (INV-CONTACT-001) går genom samma _uppgradera_kontakt:
    adressen står bokstavligen i materialet -> raden får arbetsmejlet."""
    storage = MemoryStorage()
    prospect_id = await _prepare_prospect(storage)
    llm = _FakeLLM()

    with (
        patch("app.agent.step_runner.get_llm_client", return_value=llm),
        patch("app.agent.leads_agent._scrape_registered_source_impl", new=_fake_scrape()),
    ):
        result = await run_research_step_v2(
            storage,
            TENANT,
            prospect_id=prospect_id,
            tenant_name="Snajp",
            context_pack="## Kontextpaket\nICP: svensk e-handel.",
            brief="",
        )

    rad = await storage.get_prospect(TENANT, prospect_id)
    assert rad["contact_email"] == "kundservice@exempelbolaget.se"
    assert result["contact_missing"] is False


async def test_research_v2_gissad_adress_forkastas():
    """En adress som INTE står i skrapet skrivs aldrig till raden — samma
    kodgrind (_verifierad_epost) som V1."""
    storage = MemoryStorage()
    prospect_id = await _prepare_prospect(storage)
    llm = _FakeLLM(
        overrides={
            "sa:account-research": {"contact_email": "vd@exempelbolaget.se"},
        }
    )

    with (
        patch("app.agent.step_runner.get_llm_client", return_value=llm),
        patch(
            "app.agent.leads_agent._scrape_registered_source_impl",
            new=_fake_scrape(content="# Exempelbolaget\nFri retur inom 30 dagar."),
        ),
    ):
        await run_research_step_v2(
            storage,
            TENANT,
            prospect_id=prospect_id,
            tenant_name="Snajp",
            context_pack="## Kontextpaket\nICP: svensk e-handel.",
            brief="",
        )

    rad = await storage.get_prospect(TENANT, prospect_id)
    assert rad.get("contact_email") != "vd@exempelbolaget.se"


# --- Outreach V2 ------------------------------------------------------------


async def _prepare_outreach(storage) -> str:
    await storage.save_context_doc(
        TENANT,
        kind="product_marketing",
        content=(
            "Vi säljer en svensk AI-supportagent till e-handlare. Den svarar på "
            "kundfrågor grundat i kundens egen kunskapsbas, eskalerar till människa "
            "när underlaget inte räcker, och skiljer sig från konkurrenterna genom "
            "att aldrig gissa. Erbjudande: pilot på returfrågor utan bindningstid."
        ),
        source="test",
    )
    prospect = await storage.create_prospect(TENANT, company_name="Exempelbolaget")
    thread = await storage.ensure_outreach_thread(TENANT, prospect_id=prospect["id"])
    return thread["id"]


async def test_outreach_v2_ar_tva_anrop_och_koar():
    storage = MemoryStorage()
    thread_id = await _prepare_outreach(storage)
    llm = _FakeLLM()

    with patch("app.agent.step_runner.get_llm_client", return_value=llm):
        result = await run_outreach_draft_v2(
            storage,
            TENANT,
            thread_id=thread_id,
            prospect_email="kundservice@exempelbolaget.se",
            tenant_name="Snajp",
            company_name="Exempelbolaget",
            offer_summary="Pilot på returfrågor · Färre repetitiva ärenden · 20 minuter?",
            context_pack="## Kontextpaket\nICP: svensk e-handel.",
            brief="",
            research_summary='{"company_summary": "Svensk e-handel."}',
            research_evidence=("Fri retur inom 30 dagar", "Många returfrågor"),
            is_test=True,
        )

    assert llm.calls == ["sa:draft-outreach", "snajp:humanizer-svenska"], (
        "V2-utkastet ska vara EXAKT två anrop när grundningen passerar"
    )
    assert result["queued"] is True
    assert result["escalated"] is False
    assert result["grounding"]["ok"] is True

    # Steg 1 fick BÅDE draft-skillen och mk:cold-emails delar.
    assert "Skill (i samma steg): mk:cold-email" in llm.system_prompts[0]
    # Humanizerns bas är minimal: varken kontextpaketet eller researchen
    # skickas med — den transformerar text, den researchar inte.
    assert "Kontextpaket" not in llm.system_prompts[1]

    # agent_runs: V2:s pack_version och mk:cold-email bokförd som injicerad.
    runs = await storage.list_agent_runs(TENANT, agent_type="leads_outreach")
    assert len(runs) == 1
    assert "leads/outreach-v2" in runs[0]["pack_version"]
    assert "mk:cold-email" in runs[0]["skills_used"]


async def test_outreach_v2_tom_body_ger_ett_omforsok():
    storage = MemoryStorage()
    thread_id = await _prepare_outreach(storage)

    class _TomForsta(_FakeLLM):
        async def create(self, **kwargs):
            svar = await super().create(**kwargs)
            if self.calls == ["sa:draft-outreach"]:
                payload = json.loads(svar.choices[0].message.content)
                payload["body"] = ""
                svar.choices[0].message.content = json.dumps(payload, ensure_ascii=False)
            return svar

    llm = _TomForsta()
    with patch("app.agent.step_runner.get_llm_client", return_value=llm):
        result = await run_outreach_draft_v2(
            storage,
            TENANT,
            thread_id=thread_id,
            prospect_email="kundservice@exempelbolaget.se",
            tenant_name="Snajp",
            company_name="Exempelbolaget",
            offer_summary="Pilot på returfrågor",
            context_pack="## Kontextpaket\nICP: svensk e-handel.",
            brief="",
            research_evidence=("Fri retur inom 30 dagar",),
        )

    assert llm.calls == [
        "sa:draft-outreach",
        "sa:draft-outreach",
        "snajp:humanizer-svenska",
    ]
    assert result["queued"] is True


# --- Kedjevalet -------------------------------------------------------------


def test_kedjevalet_styrs_av_flaggan(monkeypatch):
    from app.api.leads import _valj_leads_kedja

    monkeypatch.setenv("LEADS_PIPELINE", "v1")
    get_settings.cache_clear()
    research, draft = _valj_leads_kedja()
    assert research.__name__ == "run_research_step"
    assert draft.__name__ == "run_outreach_draft"

    monkeypatch.setenv("LEADS_PIPELINE", "v2")
    get_settings.cache_clear()
    research, draft = _valj_leads_kedja()
    assert research.__name__ == "run_research_step_v2"
    assert draft.__name__ == "run_outreach_draft_v2"
    get_settings.cache_clear()
