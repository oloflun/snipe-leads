"""Varje ifyllbart fält når prompten — och hamnar i RÄTT position.

Det här testet finns därför att motsatsen var sann i ett halvår utan att någon
märkte det: `agent_configs.instructions_md` och `.tone` fanns i schemat sedan
migration 010, ingen kodväg läste dem, och symptomet hos kunden var "jag ändrar
instruktionerna och svaren blir likadana". Ett fält utan ett test som bevisar
att det NÅR modellen är ett fält som tyst kan sluta fungera igen.

Positionen prövas lika hårt som närvaron. Att texten finns i prompten räcker
inte — SOUL i systemprompten vore en säkerhetsregression (INV-SEC-009) även om
agenten då skulle bete sig "bättre", och instruktioner i användarpositionen är
en regel modellen får förhandla om.
"""

import re
from unittest.mock import AsyncMock, patch

import pytest

from app.agent.support_agent import run_support_agent
from app.agentcore.instruktioner import las_instruktioner
from app.config import get_settings
from app.leads.soul import SOUL_KIND
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _fake_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _Spion:
    """Fångar varje (system, user)-par och svarar kontraktsenligt."""

    def __init__(self):
        self.anrop: list[tuple[str, str]] = []
        self.chat = self
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        self.anrop.append((messages[0]["content"], messages[1]["content"]))
        skill = re.search(r"styrs av skillen (\S+?),", messages[0]["content"]).group(1)
        svar = {
            "sources_used": ["Testartikel"],
            "context_refs": [],
            "category": "ovrigt",
            "priority": "P3",
            "sentiment": 0.8,
            "escalate": False,
            "findings": "ok",
            "confidence": 0.9,
            "kb_supports_answer": True,
            "missing_info": None,
            "draft": "Ett svar.",
            "should_escalate": False,
            "reason": None,
            "humanized": "Ett svar.",
            "text": "Ett svar.",
        }
        return _Svar(svar, skill)

    @property
    def system_prompts(self) -> str:
        return "\n".join(s for s, _ in self.anrop)

    @property
    def user_prompts(self) -> str:
        return "\n".join(u for _, u in self.anrop)


class _Svar:
    def __init__(self, payload: dict, skill: str):
        import json

        self.choices = [type("C", (), {"message": type("M", (), {
            "content": json.dumps(payload, ensure_ascii=False),
            "reasoning_content": None,
        })()})()]
        self.usage = None
        self.skill = skill


async def _kor(storage) -> _Spion:
    spion = _Spion()
    with patch("app.agent.step_runner.get_llm_client", return_value=spion), \
         patch("app.agent.retention_classifier.classify_cancellation_risk",
               new=AsyncMock(return_value=(0.0, 0.0))):
        await run_support_agent(
            storage,
            TENANT,
            message="Hur lång är leveranstiden?",
            subject="Leverans",
            channel="web",
            customer_email="kund@example.test",
            customer_name="Testkund",
            attachments=[],
        )
    return spion


async def _storage_med_kb() -> MemoryStorage:
    storage = MemoryStorage()
    await storage.add_kb_article(
        TENANT,
        title="Leveranstider",
        content="Standardfrakt tar 2-4 vardagar inom Sverige.",
        category="leverans",
    )
    return storage


@pytest.mark.anyio
async def test_globala_instruktioner_nar_varje_systemprompt():
    storage = await _storage_med_kb()
    await storage.save_global_instructions(
        ravtext="rått", strukturerad_md="## Format\n- Avsluta alltid med KANARIE-9931.", kalla="ai"
    )

    spion = await _kor(storage)

    # Varje steg, inte bara det första: en global regel som bara nådde triagen
    # hade sett ut att fungera i en spårvy och inte påverkat utkastet.
    assert spion.anrop, "inga LLM-anrop gjordes"
    for system, _ in spion.anrop:
        assert "KANARIE-9931" in system, "global instruktion saknades i ett steg"
        assert "SLUT GLOBALA REGLER" in system
    assert "KANARIE-9931" not in spion.user_prompts, "instruktioner hör inte hemma i userposition"


@pytest.mark.anyio
async def test_kundinstruktion_nar_systemprompten_och_kommer_efter_overlayen():
    storage = await _storage_med_kb()
    await storage.set_agent_instructions(
        TENANT,
        agent_type="support",
        instructions_md="## Ton och tilltal\n- Använd alltid ordet SPECIFIKT-8842.",
        instructions_rav="rått",
    )

    spion = await _kor(storage)

    for system, _ in spion.anrop:
        assert "SPECIFIKT-8842" in system
        # Ordningen ÄR regeln: "senare vinner vid konflikt". Kundlagret måste
        # ligga efter overlayen, annars kan en overlay tyst upphäva det som
        # skrivits för just den här kunden.
        if "SLUT TILLÄGGSINSTRUKTIONER" in system:
            assert system.index("SPECIFIKT-8842") > system.index("SLUT TILLÄGGSINSTRUKTIONER")


@pytest.mark.anyio
async def test_ton_soul_och_affarskontext_nar_userpositionen():
    storage = await _storage_med_kb()
    await storage.set_agent_instructions(
        TENANT, agent_type="support", instructions_md="", instructions_rav="", tone="rakt på sak, TONTEST-4417"
    )
    await storage.save_context_doc(
        TENANT, kind=SOUL_KIND, content="Skriv kort. RÖSTTEST-5528.", source="test"
    )
    await storage.save_context_doc(
        TENANT,
        kind="product_marketing",
        content="Vi säljer cyklar till pendlare. AFFÄRSTEST-6639.",
        source="test",
    )

    spion = await _kor(storage)

    for markor in ("TONTEST-4417", "RÖSTTEST-5528", "AFFÄRSTEST-6639"):
        assert markor in spion.user_prompts, f"{markor} nådde aldrig prompten"
        assert markor not in spion.system_prompts, (
            f"{markor} hamnade i systemposition — kundskriven text får aldrig göra det (INV-SEC-009)"
        )

    # Wrappningen är inte kosmetisk: utan den läser modellen kundens text som
    # instruktioner i stället för som uppgifter om kunden.
    assert "untrusted-data-" in spion.user_prompts


@pytest.mark.anyio
async def test_andrad_instruktion_ger_ny_pack_version():
    """En körning ska gå att härleda till den text den faktiskt läste.

    Utan hashen i pack_version pekar två körningar med olika regler på samma
    version, och spårvyn påstår något som inte är sant (INV-AUDIT-001).
    """
    storage = await _storage_med_kb()
    fore = (await las_instruktioner(storage, TENANT, agent_type="support")).hash
    await storage.save_global_instructions(
        ravtext="", strukturerad_md="## Format\n- Ny regel.", kalla="manuell"
    )
    efter = (await las_instruktioner(storage, TENANT, agent_type="support")).hash
    assert fore != efter


@pytest.mark.anyio
async def test_utan_instruktioner_faller_den_tillbaka_pa_filen():
    """Ingen aktiv rad = agent-core/AGENTS.md gäller, alltså beteendet före 049.

    Att fallbacken finns är hela skälet att `global_fran_fil` rapporteras: "ingen
    har skrivit instruktioner" och "instruktionerna nådde inte fram" ser
    likadana ut utifrån, och bara den ena är ett fel.
    """
    storage = MemoryStorage()
    lager = await las_instruktioner(storage, TENANT, agent_type="support")
    assert lager.global_fran_fil is True
    assert "Hitta aldrig på fakta" in lager.global_md
